import re, sys, collections

path = 'dis.txt'
target = sys.argv[1]
mode = sys.argv[2] if len(sys.argv) > 2 else 'strings'

hdr = re.compile(r'^\s*#\d+\s+: \(in (L[^)]+)\)\s*$')
nm = re.compile(r"^\s*name\s+:\s+'([^']+)'\s*$")
ty = re.compile(r"^\s*type\s+:\s+'([^']+)'\s*$")

blocks = []  # (class, method, type, startline, endline)
cur_cls = None
cur_name = None
cur_type = None
start = None
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    for i, line in enumerate(f, 1):
        m = hdr.match(line.rstrip('\r\n'))
        if m:
            if cur_cls is not None and start is not None:
                blocks.append((cur_cls, cur_name, cur_type, start, i - 1))
            cur_cls = m.group(1)
            cur_name = None
            cur_type = None
            start = i
            continue
        if cur_cls is None:
            continue
        m = nm.match(line.rstrip('\r\n'))
        if m and cur_name is None:
            cur_name = m.group(1)
            continue
        m = ty.match(line.rstrip('\r\n'))
        if m and cur_type is None:
            cur_type = m.group(1)
            continue
if cur_cls is not None and start is not None:
    blocks.append((cur_cls, cur_name, cur_type, start, len(open(path, encoding='utf-8', errors='replace').readlines())))

sel = [b for b in blocks if target in b[0]]
print('# %d methods in classes matching %r' % (len(sel), target))
for b in sel:
    print('%-8s %-24s %s  lines %d-%d' % ('', b[1], (b[2] or '')[:60], b[3], b[4]))
if mode == 'strings':
    strs = collections.Counter()
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    for b in sel:
        for ln in lines[b[3] - 1:b[4]]:
            for m in re.finditer(r'const-string[^\n]*?,\s*"((?:[^"\\]|\\.)*)"', ln):
                strs[m.group(1)] += 1
    print('\n# string constants:')
    for s, c in strs.most_common():
        print('  x%-3d %s' % (c, s))
