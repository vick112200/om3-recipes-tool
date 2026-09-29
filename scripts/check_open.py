# -*- coding: utf-8 -*-
"""`OPEN-ITEMS.md` 的守卫：让"我忘了自己列过的待验证项"变成**机器能发现**的失败。

背景（2026-09-28 需求方点破）：「你自己制定的计划怎么忘了呢」。
根因不是记性 —— 那些"待真机"的项散在各轮 `SPEC-roundNN.md` 的「遗留」里，
我每轮只读 `HANDOVER.md` 顶部，于是每轮都写成一句笼统的"真机验证"，然后被下一轮冲掉。
本脚本把规矩变成断言：

1. 表里每个 id 唯一，状态只能是 未验 / 已验 / 做不了 / 按需 / 未决
2. **未验** 的条目必须给出"在 App 里点得到"的验证入口（`data-tv="…"` 按钮）——只写文档不算
3. **已验** 的必须填「结论」（写清数据 + 据此做的决定）
4. 反向：`app/base.html` 里每个 `data-tv="uv-…"` 按钮都必须在表里有对应行（没有"没人管的按钮"）
5. 表里引用的 `SPEC-roundNN.md` 必须真的存在（出处不能是编的）
6. 打印未验 / 未决条数；退出码：有"未验却没按钮"或"孤儿按钮"等违规时 = 1

跑法：python scripts/check_open.py
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPEN = os.path.join(ROOT, 'OPEN-ITEMS.md')
PAGE = os.path.join(ROOT, 'app', 'base.html')

OK_STATUS = ('未验', '已验', '已修待复验', '未决', '做不了', '按需')
NEED_BTN = ('未验', '已修待复验')      # 这两类都只有真机能确认 → 必须有点得到的入口
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


def rows(txt):
    """把 markdown 表格行解析成 list[list[str]]（只取 6 列以上的数据行）"""
    out = []
    for ln in txt.split('\n'):
        ln = ln.strip()
        if not ln.startswith('|') or ln.startswith('|---') or '---|' in ln:
            continue
        cells = [c.strip() for c in ln.strip('|').split('|')]
        if len(cells) >= 6 and re.match(r'^OI-', cells[0]):
            out.append(cells)
    return out


def main():
    txt = io.open(OPEN, encoding='utf-8').read()
    page = io.open(PAGE, encoding='utf-8').read()
    R = rows(txt)

    print('=== OPEN-ITEMS.md：%d 条 ===' % len(R))
    for r in R:
        print('   %-7s %-8s %s' % (r[0], r[4], r[1][:60]))

    A(len(R) >= 10, 'A1 清单里至少 10 条（实测 %d 条）—— 这份文件不能被我悄悄变短' % len(R))
    ids = [r[0] for r in R]
    A(len(ids) == len(set(ids)), 'A2 id 不重复（重复的：%s）' % ([i for i in ids if ids.count(i) > 1] or '无'))

    bad_status = [r[0] for r in R if r[4] not in OK_STATUS]
    A(not bad_status, 'A3 状态只用 %s（越界的：%s）' % ('/'.join(OK_STATUS), bad_status or '无'))

    # ② 未验 / 已修待复验 必须有"能点的"入口：写 data-tv="x" 或 id="x" 都算，
    #    而且**引用必须在 app/base.html 里真的存在**（防止写了根本不存在的按钮名）
    page_tv = set(re.findall(r'data-tv="([^"]+)"', page))
    page_id = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', page))
    no_btn, bad_ref = [], []
    for r in R:
        if r[4] not in NEED_BTN:
            continue
        tvs = re.findall(r'data-tv="([^"]+)"', r[3])
        ids = re.findall(r'id="([^"]+)"', r[3])
        if not tvs and not ids:
            no_btn.append(r[0])
            continue
        for x in tvs:
            if x not in page_tv:
                bad_ref.append('%s→data-tv=%s' % (r[0], x))
        for x in ids:
            if x not in page_id:
                bad_ref.append('%s→id=%s' % (r[0], x))
    A(not no_btn,
      'A4 标「未验 / 已修待复验」的条目都有**能点的验证入口**（`data-tv=` 或 `id=`，只写在文档里不算）——缺入口的：%s'
      % (no_btn or '无'))
    A(not bad_ref, 'A4b 清单里引用的按钮/元素**在页面里真的存在**（引用失效的：%s）' % (bad_ref or '无'))

    # ③ 已验的必须填结论
    no_concl = [r[0] for r in R if r[4] == '已验' and len(r[5]) < 8]
    A(not no_concl, 'A5 标「已验」的条目都填了「结论」（缺的：%s）' % (no_concl or '无'))

    # ④ 反向：页面里每个 uv-* 按钮都要有出处
    page_btns = set(re.findall(r'data-tv="(uv-[a-z0-9\-]+)"', page))
    listed = set()
    for r in R:
        listed |= set(re.findall(r'data-tv="(uv-[a-z0-9\-]+)"', r[3]))
    A(not (page_btns - listed),
      'A6 测试页里每个 uv-* 按钮都在清单里有出处（孤儿按钮：%s）' % (sorted(page_btns - listed) or '无'))
    A('uv-cmds' in page_btns and 'uv-qr' in page_btns, 'A7 测试页里确实有这些按钮（uv-cmds / uv-qr 都在）')

    # ⑤ 出处引用的 SPEC 文件要真的存在
    miss = []
    for r in R:
        for ref in re.findall(r'(SPEC-round\d+(?:-plan)?\.md)', r[2]):
            if not os.path.exists(os.path.join(ROOT, ref)):
                miss.append((r[0], ref))
    A(not miss, 'A8 清单里引用的规格文件都存在（缺的：%s）' % (miss or '无'))

    open_n = [r[0] for r in R if r[4] in NEED_BTN]
    dec_n = [r[0] for r in R if r[4] == '未决']
    print()
    print('   · 待真机（未验 / 已修待复验）：%d 条（%s）' % (len(open_n), '、'.join(open_n) or '无'))
    print('   · 待你拍板：%d 条（%s）' % (len(dec_n), '、'.join(dec_n) or '无'))
    print('   · 做不了 / 按需：%d 条' % len([r for r in R if r[4] in ('做不了', '按需')]))

    print()
    print('待验证清单守卫：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条违规' % F))
    return 1 if F else 0


if __name__ == '__main__':
    sys.exit(main())
