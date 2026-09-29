# -*- coding: utf-8 -*-
"""把官方 APK 的 dexdump 文本建成**可检索的结构索引**，供还原协议用。

解决的问题：dis.txt 有 13 万行，肉眼看不动、grep 又不知道上下文属于哪个类/方法。
本脚本把每个「类 → 方法」的**指令区间 + 关键要素**抽成一张表，落盘成 JSON/TSV，
以后查任何东西都先查索引，而不是重扫 130 MB。

抽取的要素（每个方法一行）：
  cls        类描述符（如 Lcom/omdigitalshare/oishare/e;）
  meth       方法名
  sig        方法签名
  a          指令起止行号（dis.txt 的 1-based 行）
  ints       方法体里所有 #int 常量（去重排序）
  strs       方法体里所有 const-string 常量（去重）
  calls      方法体里所有 invoke 目标（去重）

用法：
  python official_app/oi_index.py --build          # 建索引（约 1~2 分钟），写 oi_index.json
  python official_app/oi_index.py --stats          # 看统计
  python official_app/oi_index.py --cls e          # 按类名子串列方法（含行号区间）
  python official_app/oi_index.py --str 0x6801     # 反查"哪个类/方法用了这个常量"
  python official_app/oi_index.py --call s0(      # 反查"谁调用了带这个子串的方法"
  python official_app/oi_index.py --greps 關鍵字   # 反查"哪个类/方法里有这个字符串常量"
  python official_app/oi_index.py --big 200        # 列指令数最多的方法（找状态机/大流程）
"""
import io
import os
import re
import sys
import json
import collections

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
DIS = os.path.join(HERE, 'dis.txt')
if not os.path.exists(DIS):
    DIS = os.path.join(os.environ.get('TEMP', ''), 'oishare', 'dis.txt')
IDX = os.path.join(HERE, 'oi_index.json')

CLS_RE = re.compile(r"Class descriptor\s*:\s*'(L[^']+)'")
NAME_RE = re.compile(r"^\s*name\s*:\s*'([^']+)'\s*$")
TYPE_RE = re.compile(r"^\s*type\s*:\s*'([^']+)'\s*$")
INS_RE = re.compile(r"\|\s*([0-9a-f]{4}):\s*(.+?)\s*$")
INT_RE = re.compile(r"#int\s+(-?\d+)")
# dexdump 用双引号包字符串常量（如 const-string v1, "xxx" // string@903a）；也兼容单引号
STR_RE = re.compile(r"""const-string\s+v\d+,\s*(?:"(.*?)"|'(.*?)')\s*//\s*string@""")
# 上面两个分组只有一个命中，取值时用 next(x for x in m.groups() if x is not None)
STR_G = re.compile(r"""const-string\s+v\d+,\s*(?:"(.*?)"|'(.*?)')""")
INV_RE = re.compile(r"invoke-\w+\s+\{[^}]*\},\s*(L[^;]+;|\[?L[^;]+;)\.([^:]+):(\([^)]*\)[^ ]*)")


def build():
    out = []
    cls = None
    cur = None  # [cls, meth, sig, startline]
    def flush(endline):
        if cur and cur[1]:
            out.append(dict(cls=cur[0], meth=cur[1], sig=cur[2],
                            a=cur[3], b=endline, ints=cur[4], strs=cur[5], calls=cur[6]))
    with io.open(DIS, encoding='utf-8', errors='replace') as f:
        for ln, line in enumerate(f, 1):
            m = CLS_RE.search(line)
            if m:
                flush(ln - 1)
                cur = None
                cls = m.group(1)
                continue
            m = NAME_RE.match(line.rstrip('\n'))
            if m and cls:
                flush(ln - 1)
                cur = [cls, m.group(1), None, ln, [], [], []]
                continue
            m = TYPE_RE.match(line.rstrip('\n'))
            if m and cur and cur[2] is None:
                cur[2] = m.group(1)
                continue
            if cur is None:
                continue
            if INS_RE.search(line):
                for x in INT_RE.findall(line):
                    cur[4].append(int(x))
                for m2 in STR_G.finditer(line):
                    cur[5].append(next(g for g in m2.groups() if g is not None))
                for c, mn, sig in INV_RE.findall(line):
                    cur[6].append('%s.%s%s' % (c.rstrip(';'), mn, sig))
        flush(ln)
    # 去重排序
    for r in out:
        r['ints'] = sorted(set(r['ints']))
        r['strs'] = list(dict.fromkeys(r['strs']))
        r['calls'] = list(dict.fromkeys(r['calls']))
    io.open(IDX, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False))
    print('已写 %s：%d 个方法' % (IDX, len(out)))


def load():
    return json.load(io.open(IDX, encoding='utf-8'))


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return 1
    if a[0] == '--build':
        build(); return 0
    data = load()
    if a[0] == '--stats':
        cl = collections.Counter(r['cls'] for r in data)
        print('类 %d 个，方法 %d 个' % (len(cl), len(data)))
        print('方法数最多的 15 个类：')
        for c, n in cl.most_common(15):
            print('  %5d  %s' % (n, c))
        return 0
    if a[0] == '--cls':
        pat = a[1]
        n = 0
        for r in data:
            if pat in r['cls']:
                n += 1
                print('%-58s %-26s %-28s L%d-%d' % (r['cls'], r['meth'], r['sig'] or '', r['a'], r['b']))
        print('（共 %d 个方法）' % n)
        return 0
    if a[0] == '--str':
        want = int(a[1], 0)
        n = 0
        for r in data:
            if want in r['ints']:
                n += 1
                print('%-58s %-26s %s' % (r['cls'], r['meth'], r['sig'] or ''))
        print('（共 %d 个方法用了 %s）' % (n, a[1]))
        return 0
    if a[0] == '--find':
        # --find 0x69 ：列出"用到 0x6900~0x69ff 常量"的类/方法（按类分组）
        pre = int(a[1], 0)
        lo, hi = pre << 8, (pre << 8) | 0xff
        hits = collections.defaultdict(list)
        for r in data:
            vs = [v for v in r['ints'] if lo <= v <= hi]
            if vs:
                hits[r['cls']].append((r['meth'], r['sig'] or '', sorted(set(vs))))
        for cls, ms in sorted(hits.items()):
            print('== %s' % cls)
            for meth, sig, vs in ms:
                print('    %-22s %-30s %s' % (meth, sig, ', '.join('0x%04x' % v for v in vs)))
        print('（共 %d 个类 / %d 个方法）' % (len(hits), sum(len(v) for v in hits.values())))
        return 0
    if a[0] == '--call':
        pat = a[1]
        n = 0
        for r in data:
            for c in r['calls']:
                if pat in c:
                    n += 1
                    print('%-50s %-22s → %s' % (r['cls'], r['meth'], c))
                    break
        print('（共 %d 个方法调用了带 %r 的方法）' % (n, pat))
        return 0
    if a[0] == '--greps':
        pat = a[1]
        n = 0
        for r in data:
            for s in r['strs']:
                if pat in s:
                    n += 1
                    print('%-46s %-20s %s' % (r['cls'], r['meth'], s[:90]))
                    break
        print('（共 %d 个方法含字符串 %r）' % (n, pat))
        return 0
    if a[0] == '--big':
        k = int(a[1]) if len(a) > 1 else 60
        rows = sorted(data, key=lambda r: r['b'] - r['a'], reverse=True)[:k]
        for r in rows:
            print('%6d  %-52s %-24s %s' % (r['b'] - r['a'], r['cls'], r['meth'], r['sig'] or ''))
        return 0
    print(__doc__); return 1


if __name__ == '__main__':
    sys.exit(main())
