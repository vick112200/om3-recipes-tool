# -*- coding: utf-8 -*-
"""按 **CGI 名**把官方 APK 的使用点抽成一张"参数表"（第 65 轮新增）。

背景：`SPEC-round61.md` §8 统计出官方有 **68 个 `.cgi`**，我们只用 15 个，**53 个没碰过**。
要做新功能（看图传图 / 遥控取景 / 固件升级 / GPS）时，第一个问题就是：
**这个 CGI 谁在调、带哪些参数**。本脚本回答它，不用再扫 130 MB 的 dis.txt。

数据来源（都在工程内，不联网、不重建）：
  · `official_app/oi_index.json`：第 58 轮建的**方法索引**（每个方法的指令区间 + 常量 + 调用目标）
  · `official_app/dis.txt`：反汇编源（只在 `--raw` / `--body` 时才按行读）

用法：
  python official_app/oi_cgi.py --list                 # 68 个 CGI 名 + 出现次数
  python official_app/oi_cgi.py --cgi get_imglist      # 某个 CGI：谁在用 + 参数键候选 + 调用目标
  python official_app/oi_cgi.py --cgi get_imglist --raw # 再加"原文 ±6 行"上下文（看 URL 怎么拼的）
  python official_app/oi_cgi.py --all                  # 53 个没用过的，一次全出（紧凑表）
  python official_app/oi_cgi.py --body 'Lc2/e;.G'      # 单看一个方法体的原文（按类名+方法名子串找）
  python official_app/oi_cgi.py --keys                 # 只看"参数键候选"频次（跨全部 CGI）
"""
import collections
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
DIS = os.path.join(HERE, 'dis.txt')
IDX = os.path.join(HERE, 'oi_index.json')

CGI_RE = re.compile(r'([a-z_0-9]+\.cgi)')
# 参数键候选：小写单词（可带下划线/数字），长度 2~24 —— 官方 CGI 的查询键都是这个形状
KEY_RE = re.compile(r'^[a-z][a-z_0-9]{1,23}$')
# 不是参数的常见字符串（版本号、格式名、错误码……），列出来但单放一栏，免得混进参数表
NOISE = {'utf-8', 'utf8', 'us-ascii', 'iso-8859-1', 'text/html', 'text/plain', 'application/json',
         'application/octet-stream', 'image/jpeg', 'jpg', 'jpeg', 'png', 'gif', 'dsc', 'avi', 'mov', 'mp4',
         'get', 'post', 'put', 'head', 'true', 'false', 'null', 'json', 'xml', 'http', 'https',
         'content-type', 'content-length', 'connection', 'close', 'keep-alive', 'user-agent', 'host',
         'auth', 'token', 'error', 'success', 'result', 'status', 'ok', 'ng'}
# 我们 app 里已经在用的 15 个（`rg -o '[a-z_0-9]+\.cgi' app/base.html | sort -u`，第 61 轮记录）
OURS = {'switch_cammode', 'request_getmysetdata', 'get_partialmysetdata', 'send_partialmysetdata',
        'set_mysetdatasize', 'request_restoremysetdata', 'get_mysetbackupstate', 'get_mysetrestorestate',
        'get_mysetdatasize', 'get_mysetdatamodekind', 'get_mysetname', 'getmysetdata', 'get_mysetdata',
        'get_caminfo', 'exec_reboot'}


def list_names():
    """流式扫 dis.txt 数出所有 CGI 名（不重建索引）。"""
    n = collections.Counter()
    with io.open(DIS, encoding='utf-8', errors='replace') as f:
        for line in f:
            for m in CGI_RE.finditer(line):
                n[m.group(1)] += 1
    return n


def load_idx():
    return json.load(io.open(IDX, encoding='utf-8'))


def find_methods(idx, name):
    """哪些方法里出现了这个 CGI 名（或用 'xxx' + '.cgi' 拼的也算：名字里带 base 词根）。"""
    base = name[:-4] if name.endswith('.cgi') else name
    hits = []
    for r in idx:
        ss = r.get('strs') or []
        if any(name in s for s in ss) or any(('.' + base) == s[:1 + len(base)] for s in ss):
            hits.append(r)
    return hits


def keys_of(r):
    out = []
    for s in (r.get('strs') or []):
        if s in NOISE:
            continue
        if KEY_RE.match(s) and not s.endswith('.cgi'):
            out.append(s)
    return list(dict.fromkeys(out))


def urls_of(r):
    return [s for s in (r.get('strs') or []) if '?' in s or '=' in s or '.cgi' in s]


def calls_of(r, cap=24):
    pref = ('Ljava/net/URL', 'HttpURLConnection', 'Lc2/', 'LJ2/', 'Landroid/net/', '.cgi')
    a = [c for c in (r.get('calls') or []) if any(p in c for p in pref)]
    return a[:cap]


def slice_body(a, b, pad=0):
    want = set(range(a - pad, b + 1 + pad))
    out = []
    with io.open(DIS, encoding='utf-8', errors='replace') as f:
        for ln, line in enumerate(f, 1):
            if ln in want:
                out.append(line.rstrip('\n'))
            if ln > b + pad:
                break
    return out


def raw_ctx(name, before=6, after=8, cap=6):
    """原文上下文：CGI 名出现在哪几行、前后怎么拼 URL/参数。"""
    chunks = []
    with io.open(DIS, encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if name in line:
            chunks.append(lines[max(0, i - before):i + after + 1][:])
            if len(chunks) >= cap:
                break
    return chunks


def print_cgi(idx, name, raw=False):
    ms = find_methods(idx, name)
    print('=== %s（%d 个方法里出现）%s' % (name, len(ms), '  ★我们已在用' if name[:-4] in OURS else ''))
    if not ms:
        print('   （索引里找不到 —— 可能是拼字符串拼出来的，试 --raw）')
        return
    for r in sorted(ms, key=lambda x: x['a']):
        print('  · %s.%s  %s   L%d-%d（%d 条指令）'
              % (r['cls'], r['meth'], r['sig'] or '', r['a'], r['b'], r['b'] - r['a']))
        u = urls_of(r)
        if u:
            for s in u[:6]:
                print('        URL/串: %s' % s[:150])
        k = keys_of(r)
        if k:
            print('        参数键候选: %s' % ', '.join(k[:40]))
        c = calls_of(r)
        if c:
            for x in c[:8]:
                print('        调用: %s' % x)
        if raw:
            for ch in raw_ctx(name):
                pass
    if raw:
        for n, ch in enumerate(raw_ctx(name), 1):
            print('  --- 原文上下文 #%d ---' % n)
            for line in ch:
                print('    ' + line.rstrip('\n')[:170])


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 1
    if a[0] == '--list':
        n = list_names()
        for k, v in sorted(n.items()):
            print('  %-30s %2d%s' % (k, v, '   ★在用' if k[:-4] in OURS else ''))
        print('（共 %d 个；其中我们没碰过的 %d 个）'
              % (len(n), len([k for k in n if k[:-4] not in OURS])))
        return 0
    idx = load_idx()
    if a[0] == '--cgi':
        print_cgi(idx, a[1] if a[1].endswith('.cgi') else a[1] + '.cgi', '--raw' in a)
        return 0
    if a[0] == '--all':
        n = list_names()
        for k in sorted(n):
            if k[:-4] in OURS:
                continue
            print_cgi(idx, k)
        return 0
    if a[0] == '--keys':
        cnt = collections.Counter()
        n = list_names()
        for k in sorted(n):
            for r in find_methods(idx, k):
                for x in keys_of(r):
                    cnt[x] += 1
        for x, c in cnt.most_common(120):
            print('  %-28s %d' % (x, c))
        return 0
    if a[0] == '--body':
        pat = a[1]
        for r in idx:
            if pat in r['cls'] and (r['b'] - r['a']) > 0 and (len(a) < 3 or a[2] in r['meth']):
                print('=== %s.%s %s  L%d-%d' % (r['cls'], r['meth'], r['sig'] or '', r['a'], r['b']))
                for line in slice_body(r['a'], r['b']):
                    print(line.rstrip('\n'))
        return 0
    print(__doc__)
    return 1


if __name__ == '__main__':
    sys.exit(main())
