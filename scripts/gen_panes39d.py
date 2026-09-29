# -*- coding: utf-8 -*-
"""第 39 轮（A4）：把「本站设计」的搜索框放到**与优化版同样的位置**（页面顶部、搜索脚本之前），
并撤掉 A7 那次多余的注入（它造成 #toc2q/#toc2browse/#noresult2 **重复 id**）。

背景（实测）：
 · 优化版的搜索框 `#toc2q` 其实在 **#paneB 里**（@726179，位于搜索脚本 @799708 之前 → q2 取得到）；
 · 而浮动面板 `#toc2`（@1909177）只有目录链接 —— 所以 A7 那次"补齐"注入=重复 id，得撤掉；
 · 我建的 `#toc3` 面板在 @1911433（**脚本之后**）→ `q3` 在脚本执行时是 null → 面板里打字没反应。
修法：搜索框搬到 `#paneF` 顶部（脚本之前），浮动面板 `#toc3` 只留目录链接。
"""
import io, re, sys
sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
s = io.open(P, encoding='utf-8').read()
n = 0

# ---------- 1) 撤掉 A7 注入到 #toc2 面板里的那一段（还原成"只有目录链接"）----------
i2 = s.find('<nav id="toc2">')
j2 = s.find('</nav>', i2)
assert i2 > 0 and j2 > i2
blk = s[i2:j2]
if 'id="toc2q"' in blk:
    k1 = blk.find('\n<input id="toc2q"')
    k2 = blk.find('<div id="toc2browse">')
    assert k1 > 0 and k2 > k1, '注入段定位失败'
    inner = blk[k2 + len('<div id="toc2browse">'):]
    # 去掉我加的那层 <div id="toc2browse"> ... </div>（末尾多一个 </div>）
    if inner.rstrip().endswith('</div>'):
        inner = inner.rstrip()[:-len('</div>')]
    blk2 = blk[:k1] + inner
    s = s[:i2] + blk2 + s[j2:]
    n += 1
    print('  ① 已撤掉 #toc2 面板里的重复注入（还原为纯目录）')

# 自查：这些 id 全书只应出现一次
for _id in ('toc2q', 'toc2res', 'toc2browse', 'noresult2', 'toc3q', 'toc3res', 'toc3browse', 'noresult3'):
    c = s.count('id="%s"' % _id)
    print('     #%-11s 出现 %d 次%s' % (_id, c, '' if c <= 1 else '  ⚠ 重复！'))

# ---------- 2) 在 #paneF 顶部装搜索框（和优化版同款位置）----------
ipf = s.find('<div id="paneF" class="pane hide">')
assert ipf > 0
wrap = s.find('<div class="wrap">', ipf)
assert wrap > ipf
ins_at = wrap + len('<div class="wrap">')
if 'id="toc3q"' not in s[:ins_at]:
    box = ('\n<input id="toc3q" class="tocsearch" type="search" '
           'placeholder="只在本站设计里搜：配方名 / 场景 / 感觉，如 肤色、晚霞、食物、通透…" autocomplete="off">\n'
           '<div class="chips" id="toc3chips"><button type="button" data-q="肤色">肤色</button>'
           '<button type="button" data-q="食物">食物</button><button type="button" data-q="夜景">夜景</button>'
           '<button type="button" data-q="晚霞">晚霞</button><button type="button" data-q="绿意">绿意</button>'
           '<button type="button" data-q="雪">雪</button><button type="button" data-q="通透">通透</button></div>\n'
           '<div id="toc3res" class="hide"></div>\n'
           '<div id="noresult3" class="hide">没有匹配项 —— 换个词，或点右上角的 🔍 打开目录。</div>\n'
           '<div id="toc3browse">\n')
    s = s[:ins_at] + box + s[ins_at:]
    # 关掉 #toc3browse：放在 12 张卡片之后、#paneF 收尾之前
    ipb2 = s.find('<div id="paneB"')
    tail = s.rfind('</div>\n</div>\n', ipf, ipb2)
    assert tail > ipf, '#paneF 收尾定位失败'
    s = s[:tail] + '</div>\n' + s[tail:]
    n += 1
    print('  ② 已在 #paneF 顶部装搜索框 + 结果区 + browse 包裹')

# ---------- 3) 浮动面板 #toc3 只保留目录链接（去掉重复的搜索框/chips/结果区）----------
i3 = s.find('<nav id="toc3">')
j3 = s.find('</nav>', i3)
if i3 > 0:
    blk3 = s[i3:j3]
    # 面板里若还留着输入框/结果区，就删掉（搜索框现在在页面上）
    for frag in ['<input id="toc3q"', '<div class="chips"><button type="button" data-q="肤色"', '<div id="toc3res"', '<div id="noresult3"']:
        k = blk3.find(frag)
        if k > 0:
            e = blk3.find('</div>', k) if frag.startswith('<div') else blk3.find('>\n', k)
            if frag.startswith('<input'):
                e = blk3.find('>', k) + 1
            blk3 = blk3[:k] + blk3[e + 1:]
    s = s[:i3] + blk3 + s[j3:]
    n += 1
    print('  ③ 浮动面板 #toc3 已改为纯目录')

# ---------- 4) jumpTo 切页签要能找到底栏上的 F 按钮 ----------
old = "    var tab = document.querySelector('.tabs button[data-p=\"' + (pF ? 'F' : (om ? 'B' : 'A')) + '\"]');"
new = ("    var pWant = pF ? 'F' : (om ? 'B' : 'A');\n"
       "    var tab = document.querySelector('#barABC button[data-p=\"' + pWant + '\"]') ||\n"
       "              document.querySelector('.tabs button[data-p=\"' + pWant + '\"]');")
assert s.count(old) == 1, 'jumpTo 锚点不唯一：%d' % s.count(old)
s = s.replace(old, new, 1)
n += 1

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('✅ A4 完成，共改 %d 处' % n)
