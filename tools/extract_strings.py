"""Python equivalent of `strings` command for binary analysis."""
import sys, re

def extract(path, min_len=4):
    with open(path, 'rb') as f:
        data = f.read()
    # ASCII printable strings
    pattern = re.compile(rb'[\x20-\x7e]{%d,}' % min_len)
    for m in pattern.finditer(data):
        yield m.group().decode('ascii', errors='ignore')
    # UTF-16LE strings (common in iOS binaries / Swift)
    pattern16 = re.compile(rb'(?:[\x20-\x7e]\x00){%d,}' % min_len)
    for m in pattern16.finditer(data):
        try:
            s = m.group().decode('utf-16-le', errors='ignore').rstrip('\x00')
            if s:
                yield s
        except Exception:
            pass

if __name__ == '__main__':
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    out = open(dst, 'w', encoding='utf-8') if dst else sys.stdout
    for s in extract(src):
        out.write(s + '\n')
    if dst:
        out.close()
