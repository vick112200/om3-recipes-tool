# -*- coding: utf-8 -*-
"""把官方 App dexdump 反汇编里「某个/某几个类」的方法逐条整理出来，专门用来还原协议。

与 oi_mine.py 的分工：
  - oi_mine.py  ：按类列方法摘要 / 看单个方法体 / 反查字符串
  - oi_graph.py ：把一批类的**所有方法**一次列全（方法 → 整数常量 → 字符串 → 调用），
                  并把"十六进制像 opcode 的整数"单独拎出来，方便直接对着命令表核对。

用法：
  python official_app/oi_graph.py 'M2/b'                # 列该类所有方法摘要
  python official_app/oi_graph.py 'M2/b' --ops          # 只列"带 opcode 形态常量"的方法
  python official_app/oi_graph.py 'M2/b' --body u       # 打某个方法体（原始指令行）
  python official_app/oi_graph.py 'oishare' --cls       # 列匹配类的清单
"""
import io
import os
import re
import sys
import collections

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
DIS = os.path.join(HERE, 'dis.txt')
if not os.path.exists(DIS):
    DIS = os.path.join(os.environ.get('TEMP', ''), 'oishare', 'dis.txt')

CLS_RE = re.compile(r"Class descriptor\s*:\s*'(L[^']+)'")
METH_RE = re.compile(r"^\s*name\s*:\s*'([^']+)'\s*$")
TYPE_RE = re.compile(r"^\s*type\s*:\s*'([^']+)'\s*$")
INS_RE = re.compile(r"\|\s*([0-9a-f]{4}):\s*(.+?)\s*$")
INT_RE = re.compile(r"#int\s+(-?\d+)")
STR_RE = re.compile(r"""const-string\s+v\d+,\s*(?:"([^"]*)"|'([^']*)')""")
INV_RE = re.compile(r"invoke-\w+\s+\{[^}]*\},\s*(L[^;]+;|\[?L[^;]+;)\.([^:]+):(\([^)]*\)[^ ]*)")
# 「像 opcode」的常量：0x01xx~0xffxx 且低字节非 0，或 0x0f01 / 0x400f 这类协议里的序号
OPLIKE = re.compile(r"#int\s+(2662[4-9]|266[3-9]\d|267\d\d|268[0-9]\d|269\d\d|27\d\d\d|28\d\d\d)")


def blocks():
    """yield (cls, meth, ty, [ins_lines])"""
    cls = meth = ty = None
    body = []
    with io.open(DIS, encoding='utf-8', errors='replace') as f:
        for line in f:
            m = CLS_RE.search(line)
            if m:
                if cls and meth:
                    yield cls, meth, ty, body
                cls, meth, ty, body = m.group(1), None, None, []
                continue
            m = METH_RE.match(line)
            if m and cls:
                if meth:
                    yield cls, meth, ty, body
                meth, ty, body = m.group(1), None, []
                continue
            m = TYPE_RE.match(line)
            if m and meth and ty is None:
                ty = m.group(1)
                continue
            m = INS_RE.search(line)
            if m and meth:
                body.append(m.group(2))
    if cls and meth:
        yield cls, meth, ty, body


def summarize(ins):
    ints, strs, calls = [], [], []
    for t in ins:
        ints += [int(x) for x in INT_RE.findall(t)]
        for m in STR_RE.finditer(t):
            strs.append(next(g for g in m.groups() if g is not None))
        for c, mn, sig in INV_RE.findall(t):
            calls.append('%s.%s%s' % (c.split('/')[-1].rstrip(';'), mn, sig))
    return ints, strs, calls


def hexlike(ints):
    """筛出像协议常量（16 位，高字节非 0）的整数"""
    out = []
    for v in ints:
        if v <= 0 or v > 0xffff:
            continue
        hi = (v >> 8) & 0xff
        lo = v & 0xff
        if hi and lo and (hi >= 0x01):
            out.append(v)
    return out


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    target = args[0]
    mode = args[1] if len(args) > 1 else None
    if mode == '--cls':
        seen = collections.OrderedDict()
        for cls, meth, ty, ins in blocks():
            if ty is None and meth is None:
                pass
        # 简化：直接扫类名行
        cls_re = re.compile(r"Class descriptor\s*:\s*'(L[^']+)'")
        for line in io.open(DIS, encoding='utf-8', errors='replace'):
            m = cls_re.search(line)
            if m and target.lower() in m.group(1).lower():
                seen[m.group(1)] = 1
        for c in seen:
            print(c)
        print('（共 %d 个类）' % len(seen))
        return 0
    if mode == '--body':
        want = args[2]
        n = 0
        for cls, meth, ty, ins in blocks():
            if target not in cls or meth != want:
                continue
            n += 1
            print('=== %s.%s%s   (%d 条指令)' % (cls, meth, ty or '', len(ins)))
            for t in ins:
                print('   ', t[:160])
        print('（共 %d 个方法）' % n)
        return 0
    only_ops = (mode == '--ops')
    n = 0
    for cls, meth, ty, ins in blocks():
        if target not in cls:
            continue
        ints, strs, calls = summarize(ins)
        ops = hexlike(ints)
        if only_ops and not ops:
            continue
        n += 1
        print('=== %s.%s%s   (%d 条指令)' % (cls, meth, ty or '', len(ins)))
        if ops:
            print('    协议常量: ' + ', '.join('%d(0x%04x)' % (v, v) for v in sorted(set(ops))))
        if ints:
            c = collections.Counter(ints)
            print('    整数: ' + ', '.join('%d(0x%02x)×%d' % (k, k & 0xff, v) for k, v in sorted(c.items())))
        if strs:
            print('    字符串: ' + ' | '.join(dict.fromkeys(strs))[:300])
        if calls:
            print('    调用: ' + ', '.join(dict.fromkeys(calls))[:400])
    print('\n（共 %d 个方法）' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
