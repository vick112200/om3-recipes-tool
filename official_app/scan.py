import re, collections, sys

cur = None
out = collections.defaultdict(set)
cls_re = re.compile(r': \(in (L[^;]+;[^)]*)\)')
name_re = re.compile(r"name\s+:\s+'([^']+)'")
with open('dis.txt', 'r', encoding='utf-8', errors='replace') as f:
    for line in f:
        m = cls_re.search(line)
        if m:
            cur = m.group(1)
            continue
        m = name_re.search(line)
        if m and cur:
            out[cur].add(m.group(1))

pat = sys.argv[1] if len(sys.argv) > 1 else 'myset'
for c in sorted(out):
    lc = c.lower()
    if pat in lc or ('olytools' in lc and pat == 'myset'):
        print('==', c, '(%d methods)' % len(out[c]))
        print('   ', ', '.join(sorted(out[c])))
