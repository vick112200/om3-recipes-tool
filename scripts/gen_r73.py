# -*- coding: utf-8 -*-
"""第 73 轮：修「点『测试页』却回到配方合集」（见 SPEC-round73.md）。

需求方 2026-09-28：「点击连接相机测试页，直接回到了配方合集，看看怎么回事」。

**两个 bug 叠在一起（都用无头实测钉住了）**

① **页签转发漏了 T**（块07 第 15890 行，第 39 轮留下的嵌套三元表达式）：
       var top = $(dp === 'E' ? 'tabMine' : (dp === 'D' ? 'tabCam' : (dp === 'B' ? 'tabB'
                 : (dp === 'C' ? 'tabC' : (dp === 'F' ? 'tabF' : 'tabBuiltin')))));
   `data-p="T"`（第 68 轮加的测试页）**没有分支** → 兜底成 `tabBuiltin` → 程序化点击"配方合集"。
   实测（劫持 HTMLElement.prototype.click 记录）：
       程序化点击过的按钮 = camMenuBtn, BUTTON, tabTest, tabBuiltin      ← 点测试页却点了 tabBuiltin
   第 39 轮给 F 加过同样的分支（注释里就写着"否则会兜底到内置配方"），第 68 轮加 T 时又漏了。

② **测试页被嵌在「连接相机」页里面**（第 68 轮插入位置错）：
       实测父链：#paneT → 父元素 div#paneD → body         （应该是 div#paneT → body）
   于是"连接相机页"一被 `.hide`，测试页跟着一起没了；反过来测试页也永远不是真正独立的一页。

本轮：把 #paneT 挪成 body 的直接子元素（紧跟 #paneD 之后，只搬 DOM 节点、id 全不动）+
把页签转发改成**映射表**（以后加页签只改一行，不再会"兜底到配方合集"）。

规矩：幂等（标记 `r73：测试页搬出 paneD`）+ 每步必须真的改到东西 + 老 id 一个不少 + 本轮不新增 id。

用法：python scripts/gen_r73.py [--check]
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r73：测试页搬出 paneD'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


DIVPAT = re.compile(r'<div\b|</div\s*>')


def cut_div(html, start):
    """从 start（`<div` 的起点）开始按 <div>/</div> 配平，返回 (这一整块, 块之后的剩余)"""
    depth = 0
    pos = start
    while True:
        m = DIVPAT.search(html, pos)
        if not m:
            raise AssertionError('div 配不平（起点 %d）' % start)
        if m.group(0).startswith('</'):
            depth -= 1
            if depth == 0:
                return html[start:m.end()], html[m.end():]
        else:
            depth += 1
        pos = m.end()


# ---------------------------------------------------------------- ② 把 #paneT 挪出 #paneD
@step('② 把 #paneT 从 #paneD 里搬出来（body 的直接子元素，紧跟 #paneD 之后）')
def s_move_panet(html):
    iD = html.index('<div id="paneD"')
    dblk, after = cut_div(html, iD)
    assert dblk.count('<div id="paneT"') == 1, '#paneD 里没找到 #paneT'
    iT = dblk.index('<div id="paneT"')
    tblk, dtail = cut_div(dblk, iT)
    assert tblk.lstrip().startswith('<div id="paneT"'), '#paneT 块起点不对'
    assert 'id="tvPerm"' in tblk and '排查项' in tblk, '#paneT 块内容不对（没看到排查项卡片）'
    assert '<script' not in tblk and '<style' not in tblk, '#paneT 块里居然有 script/style —— 配平可能被带跑了'
    assert tblk.count('<div') == tblk.count('</div>'), '#paneT 块内 div 不配平'
    head = dblk[:iT].rstrip()
    tail = dtail + dblk[iT + len(tblk):] if False else dtail
    # ⚠ 有意的：把 #paneT 整块从 dblk 里切走（连带其前导空白），再拼回 #paneD 的闭合标签之后
    dd = head + dtail
    assert dd.count('<div id="paneT"') == 0
    note = ('\n<!-- %s：测试页原来被嵌在上面这个 #paneD 里面（第 68 轮插入位置错了）——\n'
            '     结果"连接相机页"一隐藏，测试页就跟着没了；点测试页又落到配方合集。\n'
            '     现在它是 body 的直接子元素，和 #paneA/#paneB/… 平级。 -->\n' % MARK)
    return html[:iD] + dd + note + tblk + after


# ---------------------------------------------------------------- ① 页签转发加 T
@step('① 页签转发（块07）改成映射表，补上 T（并让以后加页签只改一行）')
def s_tabmap(html):
    old = ("      var top = $(dp === 'E' ? 'tabMine' : (dp === 'D' ? 'tabCam' : (dp === 'B' ? 'tabB' : "
           "(dp === 'C' ? 'tabC' : (dp === 'F' ? 'tabF' : 'tabBuiltin')))));")
    assert html.count(old) == 1, '页签转发那条嵌套三元没找到'
    new = ("      /* r73：⚠ 这个映射**少写一个分支就会静默兜底到 tabBuiltin（配方合集）** ——\n"
           "         第 39 轮给 F 补过一次，第 68 轮加了 T（测试页）又漏了：点「测试页」实际点了「配方合集」。\n"
           "         改成映射表：以后加页签只改这一行。（真因与实测见 SPEC-round73.md §2） */\n"
           "      var TABP = { A:'tabBuiltin', B:'tabB', C:'tabC', D:'tabCam', E:'tabMine', F:'tabF', T:'tabTest' };\n"
           "      var top = $(TABP[dp] || 'tabBuiltin');\n"
           "      if(dp && !TABP[dp]) log('[提示] 页签转发不认识 data-p=\"' + dp + '\"，已兜底到配方合集', 'warn');")
    return html.replace(old, new, 1)


def run(html):
    changed = []
    for label, fn in STEPS:
        before = html
        try:
            html = fn(html)
        except AssertionError as e:
            raise AssertionError('第「%s」步失败：%s' % (label, e or '锚点没找到'))
        except ValueError as e:
            raise AssertionError('第「%s」步失败（找不到锚点）：%s' % (label, e))
        if html == before:
            raise AssertionError('这一步什么都没改：' + label)
        changed.append(label)
    return html, changed


def nesting(html):
    """用栈式扫描报出每个 pane 的父元素（只当结构性检查用；浏览器解析结果与本扫描一致即可）"""
    tag = re.compile(r'<(/?)(div|nav)\b([^>]*)>')
    stack = []
    out = {}
    for m in tag.finditer(html):
        close, tagname, attrs = m.group(1), m.group(2), m.group(3)
        if close:
            if stack:
                stack.pop()
            continue
        mid = re.search(r'id="([A-Za-z0-9_]+)"', attrs)
        if mid and mid.group(1).startswith('pane'):
            out[mid.group(1)] = stack[-1] if stack else '(无/body)'
        if not attrs.rstrip().endswith('/'):
            stack.append(mid.group(1) if mid else ('%s@%d' % (tagname, html[:m.start()].count('\n') + 1)))
    return out


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r73] 已经是目标状态（页面里有 "%s"）—— 不重复改。' % MARK)
        return 0
    n_div_before = html.count('<div') + html.count('</div>')
    try:
        new, changed = run(html)
    except AssertionError as e:
        print('[r73] ✗ %s —— **不写盘**' % e)
        return 1
    assert new.count('<div') + new.count('</div>') == n_div_before, '搬动过程中 div 标签数变了'
    print('[r73] 搬动前后 #paneT 的父元素：')
    for k, v in nesting(new).items():
        print('   · %s → %s' % (k, v))
    if '--check' in sys.argv:
        print('[r73] --check：%d 步都能跑通（未写盘）：' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(new)
    print('[r73] ✓ 已改 %d 步：测试页搬出连接相机页 / 页签转发补上 T' % len(changed))
    return 0


if __name__ == '__main__':
    sys.exit(main())
