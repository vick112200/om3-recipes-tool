# -*- coding: utf-8 -*-
"""在官方 APK 的 dexdump 文本（dis.txt）里定位/阅读代码。

用法：
  python find_str.py <关键词> [...]          定位字符串常量（哪个类·哪个方法·第几行）
  python find_str.py --cls <类名子串>        列出该类所有方法
  python find_str.py --dump <类名子串> <方法名>   打印方法体（含行号）
"""
import os, re, sys, collections

# 优先用工程内的 official_app/dis.txt（第 58 轮已从 %TEMP% 搬进来），
# 找不到再退回临时目录（%TEMP% 会被系统清理）。
_HERE = os.path.dirname(os.path.abspath(__file__))
DIS = os.path.join(_HERE, 'dis.txt')
if not os.path.exists(DIS):
    DIS = os.path.join(os.environ.get('TEMP', ''), 'oishare', 'dis.txt')
cls_re = re.compile(r"^  Class descriptor\s+: '([^']+)'")
meth_re = re.compile(r"^\s+name\s+: '([^']+)'")
ty_re = re.compile(r"^\s+type\s+: '([^']+)'")


def walk():
    """产出行：(lineno, cls, meth, text)"""
    cur_cls = cur_meth = None
    for i, line in enumerate(open(DIS, encoding='utf-8', errors='replace'), 1):
        m = cls_re.match(line)
        if m:
            cur_cls = m.group(1); cur_meth = None
            yield i, cur_cls, '<class>', line
            continue
        m = meth_re.match(line)
        if m:
            cur_meth = m.group(1)
        yield i, cur_cls, cur_meth, line


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__); return
    if a[0] == '--cls':
        pat = a[1].lower()
        out = collections.OrderedDict()
        cur = None
        for _, cls, meth, line in walk():
            if cls and pat in cls.lower():
                if meth and meth != '<class>':
                    lst = out.setdefault(cls, [])
                    if not lst or lst[-1] != meth:
                        lst.append(meth)
        for c, ms in out.items():
            print('== %s (%d)' % (c, len(ms))); print('   ' + ', '.join(ms))
        return
    if a[0] == '--dump':
        pat, want = a[1].lower(), a[2]
        printing = False
        n = 0
        for i, cls, meth, line in walk():
            if not (cls and pat in cls.lower()):
                printing = False; continue
            if meth == want:
                printing = True
            elif meth and meth != want and printing and re.match(r'^\s+name\s+:', line):
                printing = False
            if printing:
                print('%7d %s' % (i, line.rstrip()))
                n += 1
                if n > 4000:
                    print('... (截断)'); return
        return
    keys = a
    hits = collections.OrderedDict()
    for i, cls, meth, line in walk():
        for k in keys:
            if k in line:
                hits.setdefault((cls, meth), []).append((i, line.strip()[:150]))
                break
    for (c, mm), ls in hits.items():
        print('== %s . %s   (%d 处)' % (c, mm, len(ls)))
        for ln, t in ls[:25]:
            print('   %7d  %s' % (ln, t))
        print()
    print('共 %d 个 (类,方法)' % len(hits))


main()
