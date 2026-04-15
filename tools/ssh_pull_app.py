"""SSH direct copy fallback for iOS .app extraction (frida-ios-dump 대체).

Bundle ID에 해당하는 .app 디렉토리를 SSH 통해 sudo + tar 후 SFTP로 다운로드 → 로컬 Payload/ 압축 해제.
plutil이 없는 환경(palera1n 등)에서는 Info.plist를 base64로 받아 plistlib으로 파싱.

Usage:
    python ssh_pull_app.py <bundle_id> <out_dir> \
        [--host HOST] [--port PORT] [--user USER] [--password PW]

환경변수 폴백:
    MSC_SSH_HOST, MSC_SSH_PORT, MSC_SSH_USER, MSC_SSH_PW

예:
    set MSC_SSH_HOST=192.168.x.x
    set MSC_SSH_USER=mobile
    set MSC_SSH_PW=*****
    python ssh_pull_app.py com.example.app "ipa_list/MyApp"
"""
import os
import sys
import argparse
import base64
import posixpath
import plistlib
import tarfile

import paramiko


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('bundle_id', help='target Bundle ID (e.g. com.example.app)')
    p.add_argument('out_dir', help='local output dir (Payload/ will be created inside)')
    p.add_argument('--host', default=os.environ.get('MSC_SSH_HOST'))
    p.add_argument('--port', type=int, default=int(os.environ.get('MSC_SSH_PORT', '22')))
    p.add_argument('--user', default=os.environ.get('MSC_SSH_USER'))
    p.add_argument('--password', default=os.environ.get('MSC_SSH_PW'))
    args = p.parse_args()
    missing = [k for k in ('host', 'user', 'password') if not getattr(args, k)]
    if missing:
        p.error(f"missing required SSH credentials: {missing}. provide via flags or env MSC_SSH_*")
    return args


def ssh_exec(ssh, cmd, timeout=120):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    rc = o.channel.recv_exit_status()
    return rc, o.read(), e.read()


def find_app_path(ssh, password, bundle_id):
    """Find .app directory matching bundle_id via plistlib (plutil-free)."""
    # list all .app candidates
    rc, out, _ = ssh_exec(
        ssh,
        f"echo {password} | sudo -S ls -d /var/containers/Bundle/Application/*/*.app 2>/dev/null",
        timeout=60,
    )
    candidates = [
        line.strip()
        for line in out.decode(errors='replace').splitlines()
        if line.strip() and line.strip().endswith('.app')
    ]
    # parse each Info.plist via base64
    for app in candidates:
        plist_path = posixpath.join(app, 'Info.plist')
        rc, out, _ = ssh_exec(
            ssh,
            f"echo {password} | sudo -S cat '{plist_path}' 2>/dev/null | base64",
            timeout=30,
        )
        b64 = out.decode(errors='replace').replace('[sudo] password for ', '').strip()
        # remove the leading "<user>: " prompt residue if any
        b64 = b64.split(':', 1)[-1].strip() if ':' in b64.splitlines()[0] else b64
        try:
            raw = base64.b64decode(b64, validate=False)
            pl = plistlib.loads(raw)
        except Exception:
            continue
        if pl.get('CFBundleIdentifier') == bundle_id:
            return app
    return None


def find_remote_tar(ssh, password):
    """Return path to a working tar binary on device."""
    for cand in ('/var/jb/usr/bin/tar', '/usr/bin/tar', 'tar'):
        rc, out, _ = ssh_exec(ssh, f"echo {password} | sudo -S {cand} --version 2>/dev/null | head -1", timeout=10)
        if rc == 0 and out.strip():
            return cand
    return 'tar'


def main():
    args = parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        args.host,
        port=args.port,
        username=args.user,
        password=args.password,
        timeout=30,
        banner_timeout=30,
        auth_timeout=30,
    )
    print(f"[+] SSH connected {args.host}:{args.port}")

    print(f"[+] Searching for Bundle ID {args.bundle_id} ...")
    app_path = find_app_path(ssh, args.password, args.bundle_id)
    if not app_path:
        print(f"[!] .app not found for Bundle ID {args.bundle_id}")
        ssh.close()
        sys.exit(2)
    app_name = posixpath.basename(app_path)
    parent = posixpath.dirname(app_path)
    print(f"[+] Found: {app_path}")

    tar_bin = find_remote_tar(ssh, args.password)
    remote_tar = f"/tmp/{args.bundle_id}.tar"
    safe_user = args.user.replace("'", "")
    tar_cmd = (
        f"echo {args.password} | sudo -S sh -c "
        f"'cd \"{parent}\" && {tar_bin} -cf {remote_tar} \"{app_name}\" "
        f"&& chmod 644 {remote_tar} && chown {safe_user}:{safe_user} {remote_tar}'"
    )
    print(f"[+] Tarring on device with {tar_bin} ...")
    rc, _, err = ssh_exec(ssh, tar_cmd, timeout=600)
    if rc != 0:
        print(f"[tar stderr] {err.decode(errors='replace')[:500]}")

    sftp = ssh.open_sftp()
    local_tar = os.path.join(args.out_dir, f"{args.bundle_id}.tar")
    print(f"[+] Downloading -> {local_tar}")
    sftp.get(remote_tar, local_tar)
    sftp.close()
    print(f"[+] Downloaded {os.path.getsize(local_tar)} bytes")

    ssh_exec(ssh, f"echo {args.password} | sudo -S rm -f {remote_tar}", timeout=30)
    ssh.close()

    payload_dir = os.path.join(args.out_dir, 'Payload')
    os.makedirs(payload_dir, exist_ok=True)
    print(f"[+] Extracting -> {payload_dir}")
    with tarfile.open(local_tar) as tf:
        try:
            tf.extractall(payload_dir, filter='data')
        except TypeError:
            tf.extractall(payload_dir)
    os.remove(local_tar)
    extracted = os.path.join(payload_dir, app_name)
    print(f"[+] Extracted: {extracted}")

    # Auto-detect FairPlay DRM (SC_Info dir)
    if os.path.isdir(os.path.join(extracted, 'SC_Info')):
        print("[!] WARNING: SC_Info detected — main binary is FairPlay-encrypted (DRM v2).")
        print("    strings-based static analysis will be limited to header/symbol regions.")


if __name__ == '__main__':
    main()
