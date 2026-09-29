# -*- coding: utf-8 -*-
"""从官方 App 的 dexdump 反汇编里挖"某个类每个方法干了什么"。

用途：把 BLE 协议层（M2/b、M2/a）、连接状态机（oishare.e$*）等类的方法，
     逐条整理成「方法 → 用到的整数常量（=操作码/子码/序号）+ 字符串常量 + 调用的方法」，
     再对照 App 自己的字符串标签（電源ON / リモコンモード / パスコード認証…）还原语义。

用法：
  python official_app/oi_mine.py M2/b              # 列该类所有方法摘要
  python official_app/oi_mine.py M2/b u            # 只看某个方法（含方法体）
  python official_app/oi_mine.py --grep 電源ON     # 反查某字符串出现在哪个类/方法
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


def blocks():
    """yield (cls, meth, type, [ins_lines])"""
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


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    if args[0] == '--field':
        want = args[1]
        seen = collections.Counter()
        for cls, meth, ty, ins in blocks():
            if len(ins) == 0 and ty and want in ty and meth and len(meth) <= 2:
                seen[(cls, meth, ty)] += 1
        for (cls, f, ty), n in sorted(seen.items()):
            print('%-40s 字段 %-4s : %s' % (cls, f, ty))
        print('（共 %d 个字段）' % len(seen))
        return 0
    if args[0] == '--call':
        kw = args[1]
        hits = collections.Counter()
        for cls, meth, ty, ins in blocks():
            _, _, calls = summarize(ins)
            for c in calls:
                if kw in c:
                    hits[(cls, meth, ty or '', c)] += 1
        for (cls, meth, ty, c), n in sorted(hits.items()):
            print('%-34s %-10s %-22s → %s' % (cls, meth, ty, c))
        print('（共 %d 条调用点）' % sum(hits.values()))
        return 0
    if args[0] == '--grep':
        kw = args[1]
        hits = collections.Counter()
        for cls, meth, ty, ins in blocks():
            for s in STR_RE.findall('\n'.join(ins)):
                if kw in s:
                    hits[(cls, meth, s)] += 1
        for (cls, meth, s), n in sorted(hits.items()):
            print('%-28s %-26s %s' % (cls, meth, s[:70]))
        return 0
    target, only = args[0], (args[1] if len(args) > 1 else None)
    n = 0
    for cls, meth, ty, ins in blocks():
        if target not in cls:
            continue
        if only and meth != only:
            continue
        ints, strs, calls = summarize(ins)
        n += 1
        print('=== %s.%s%s   (%d 条指令)' % (cls, meth, ty or '', len(ins)))
        if ints:
            c = collections.Counter(ints)
            print('    整数常量: ' + ', '.join('%d(0x%02x)×%d' % (k, k & 0xff, v) for k, v in sorted(c.items())))
        if strs:
            print('    字符串: ' + ' | '.join(dict.fromkeys(strs))[:300])
        if calls:
            print('    调用: ' + ', '.join(dict.fromkeys(calls))[:400])
        if only:
            print('    ---- 指令 ----')
            for t in ins[:200]:
                print('      ', t[:150])
    print('\n（共 %d 个方法）' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
