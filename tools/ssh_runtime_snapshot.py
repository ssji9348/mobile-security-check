"""iOS app data dirs snapshot for runtime check (항목 18 — 삭제 안전성).

Bundle/Data Container UUID 매핑 + 키워드 기반 잔존 파일 검색.
출력은 (1) 앱 본체/데이터, (2) OS 시스템 메타, (3) 추출 부산물/사용자 파일로 자동 분류됩니다.

Usage:
    python ssh_runtime_snapshot.py <bundle_id> [keyword] \
        [--host HOST] [--port PORT] [--user USER] [--password PW]

환경변수 폴백: MSC_SSH_HOST, MSC_SSH_PORT, MSC_SSH_USER, MSC_SSH_PW
"""
import os
import argparse
import paramiko


SYSTEM_META_PATTERNS = (
    '/var/mobile/Library/Logs/CrashReporter/',
    '/Containers/Data/InternalDaemon/',
    '/Library/Caches/com.apple.LaunchServices.',
)
EXTRACT_ARTIFACT_PATTERNS = (
    '/private/var/tmp/Payload',
    '/private/var/tmp/',
    '/tmp/',
)
USER_FILE_PATTERNS = (
    '/var/mobile/Documents/',
    '/var/mobile/Library/Filza/',
    '/Containers/Data/PluginKitPlugin/',
)


def classify(line):
    if any(p in line for p in SYSTEM_META_PATTERNS):
        return 'SYSTEM-META'
    if any(p in line for p in EXTRACT_ARTIFACT_PATTERNS):
        return 'ARTIFACT'
    if any(p in line for p in USER_FILE_PATTERNS):
        return 'USER-FILE'
    if '/var/containers/Bundle/Application/' in line:
        return 'APP-BUNDLE'
    if '/var/mobile/Containers/Data/Application/' in line:
        return 'APP-DATA'
    return 'OTHER'


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('bundle_id', help='target Bundle ID')
    p.add_argument('keyword', nargs='?', help='extra keyword for /var/mobile find (default: last segment of bundle_id)')
    p.add_argument('--host', default=os.environ.get('MSC_SSH_HOST'))
    p.add_argument('--port', type=int, default=int(os.environ.get('MSC_SSH_PORT', '22')))
    p.add_argument('--user', default=os.environ.get('MSC_SSH_USER'))
    p.add_argument('--password', default=os.environ.get('MSC_SSH_PW'))
    args = p.parse_args()
    missing = [k for k in ('host', 'user', 'password') if not getattr(args, k)]
    if missing:
        p.error(f"missing SSH credentials: {missing}. provide via flags or env MSC_SSH_*")
    if not args.keyword:
        args.keyword = args.bundle_id.split('.')[-1]
    return args


def run(ssh, cmd, timeout=60):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    rc = o.channel.recv_exit_status()
    return rc, o.read().decode(errors='replace'), e.read().decode(errors='replace')


def main():
    args = parse_args()
    pw = args.password

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(args.host, port=args.port, username=args.user, password=pw, timeout=30)

    for label, root in (
        ('Data Container', '/var/mobile/Containers/Data/Application'),
        ('Bundle Container', '/var/containers/Bundle/Application'),
    ):
        print(f"=== {label} (Bundle ID: {args.bundle_id}) ===")
        cmd = (
            f"echo {pw} | sudo -S sh -c '"
            f"for d in {root}/*; do "
            f"  pl=\"$d/.com.apple.mobile_container_manager.metadata.plist\"; "
            f"  if [ -f \"$pl\" ] && grep -a -q \"{args.bundle_id}\" \"$pl\" 2>/dev/null; then echo \"$d\"; fi; "
            f"done' 2>/dev/null"
        )
        _, out, _ = run(ssh, cmd, timeout=120)
        out = out.strip()
        print(out if out else '(none)')
        print()

    print(f"=== /var/mobile search for '*{args.keyword}*' (case-insensitive) ===")
    _, out, _ = run(
        ssh,
        f"echo {pw} | sudo -S find /var/mobile -iname '*{args.keyword}*' 2>/dev/null | head -100",
        timeout=120,
    )
    classified = {'APP-BUNDLE': [], 'APP-DATA': [], 'SYSTEM-META': [], 'ARTIFACT': [], 'USER-FILE': [], 'OTHER': []}
    for line in out.replace('[sudo] password for ', '').splitlines():
        line = line.strip()
        if not line or line.endswith(':'):
            continue
        classified.setdefault(classify(line), []).append(line)
    for cat in ('APP-BUNDLE', 'APP-DATA', 'SYSTEM-META', 'ARTIFACT', 'USER-FILE', 'OTHER'):
        items = classified.get(cat, [])
        if items:
            print(f"--- [{cat}] ({len(items)})")
            for line in items:
                print(f"  {line}")
            print()

    print(f"=== /private/var/tmp + /tmp search ===")
    _, out, _ = run(
        ssh,
        f"echo {pw} | sudo -S find /private/var/tmp /tmp -iname '*{args.keyword}*' 2>/dev/null | head -50",
        timeout=60,
    )
    print(out.replace('[sudo] password for ', ''))

    ssh.close()


if __name__ == '__main__':
    main()
