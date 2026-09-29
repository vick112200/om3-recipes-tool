# -*- coding: utf-8 -*-
"""把 dexdump 里的 `packed-switch` / `sparse-switch` **键值表**解出来。

为什么需要它：dalvik 的 switch 把「码值 → 分支」表放在 payload 里，
dexdump 只打一行 `packed-switch-data (N units)` 而且**列不全**（后面跟 `...`）。
于是 `oi_index.py` 里看不到任何 `#int`，肉眼看不出「34 = PASSCODE_ERROR」这类映射。
本脚本直接读 `classes.dex` 的字节解表（dexdump 行首的十六进制就是 dex 文件偏移）。

用法：
  python official_app/oi_switch.py --cls 's2/b$g;' --meth H      # 用索引里的行号区间
  python official_app/oi_switch.py --lines 1269701 1269930       # 或直接给行号
  python official_app/oi_switch.py --cls 's2/b$g;' --meth H --key 34   # 只看某个码值

输出：
  switch@0x9 size=7 first_key=0
     code 0    -> 0x185  (.OlyBleConnectListener BLE_RESULT_SUCCESS)

说明：目标地址是该 case 分支的第一条指令；表里「最近的日志字符串」用来自动标语义，
**只是提示**，判定时请对照分支体确认。
"""
import io
import json
import os
import re
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
DIS = os.path.join(HERE, 'dis.txt')
DEX = os.path.join(HERE, 'classes.dex')
IDX = os.path.join(HERE, 'oi_index.json')

INS_RE = re.compile(r'\|([0-9a-f]{4}):\s*(.+?)\s*$')


def load_lines():
    with io.open(DIS, encoding='utf-8', errors='replace') as f:
        return f.read().split('\n')


def parse_region(lines, a, b):
    """返回 (insns, payloads)：insns=[(code_addr, text, file_off)], payloads={code_addr: file_off}"""
    insns, payloads = [], {}
    for L in lines[a - 1:b]:
        m = re.match(r'^([0-9a-f]+):', L)
        if not m:
            continue
        foff = int(m.group(1), 16)
        m2 = INS_RE.search(L)
        if not m2:
            continue
        addr = int(m2.group(1), 16)
        text = m2.group(2)
        if text.startswith('packed-switch-data') or text.startswith('sparse-switch-data'):
            payloads[addr] = foff
        insns.append((addr, text, foff))
    return insns, payloads


def first_log_after(insns, addr):
    for a2, t2, _ in insns:
        if a2 >= addr and 'const-string' in t2:
            m = re.search(r'const-string\s+v\d+,\s*"(.*?)"', t2)
            if m:
                return m.group(1)
    return None


def decode(dex, insns, payloads):
    out = []
    for addr, text, _ in insns:
        m = re.match(r'(packed-switch|sparse-switch)\s+v\d+,\s*([0-9a-f]+)', text)
        if not m:
            continue
        # 操作数是 payload 的**绝对**代码地址（如 `packed-switch v6, 000001d8 // +000001cf`）
        tgt = int(m.group(2), 16)
        if tgt not in payloads:   # 兜底：有的反汇编器给的是相对偏移
            rel = tgt - addr
            tgt = addr + rel
        if tgt not in payloads:
            out.append(dict(addr=addr, kind=m.group(1), err='payload@0x%x 未在区间内' % tgt))
            continue
        f = payloads[tgt]
        _ident, size = struct.unpack_from('<HH', dex, f)
        rows = []
        if m.group(1) == 'packed-switch':
            first = struct.unpack_from('<i', dex, f + 4)[0]
            keys = [first + i for i in range(size)]
            tgts = [struct.unpack_from('<i', dex, f + 8 + 4 * i)[0] for i in range(size)]
        else:
            keys = [struct.unpack_from('<i', dex, f + 4 + 8 * i)[0] for i in range(size)]
            tgts = [struct.unpack_from('<i', dex, f + 8 + 8 * i)[0] for i in range(size)]
        for k, t in zip(keys, tgts):
            real = addr + t
            rows.append((k, real, first_log_after(insns, real)))
        out.append(dict(addr=addr, kind=m.group(1), size=size, rows=rows))
    return out


def main():
    a = sys.argv[1:]
    lo = hi = None
    want_key = None
    if '--lines' in a:
        i = a.index('--lines')
        lo, hi = int(a[i + 1]), int(a[i + 2])
    elif '--cls' in a and '--meth' in a:
        cls = a[a.index('--cls') + 1]
        meth = a[a.index('--meth') + 1]
        data = json.load(io.open(IDX, encoding='utf-8'))
        for r in data:
            if cls in r['cls'] and r['meth'] == meth:
                lo, hi = r['a'], r['b']
                break
    if '--key' in a:
        want_key = int(a[a.index('--key') + 1], 0)
    if lo is None:
        print(__doc__)
        return 1
    lines = load_lines()
    insns, payloads = parse_region(lines, lo, hi)
    sws = decode(open(DEX, 'rb').read(), insns, payloads)
    if not sws:
        print('# L%d-%d 里没有 switch 指令' % (lo, hi))
        return 0
    for sw in sws:
        if 'err' in sw:
            print('switch@0x%x  %s' % (sw['addr'], sw['err']))
            continue
        print('switch@0x%x %s size=%d' % (sw['addr'], sw['kind'], sw['size']))
        for k, real, log in sw['rows']:
            if want_key is not None and k != want_key:
                continue
            print('   code %-4d -> 0x%x  %s' % (k, real, log or ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
