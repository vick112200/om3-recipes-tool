# -*- coding: utf-8 -*-
"""给 lcpdoc_build.py 打补丁：模块详情、页面怎么用/坑、被谁引用、跨模块用法章节。"""
import io
import os

TARGETS = ["C:/Users/82302/AppData/Local/Temp/lcpdoc_build.py",
           "D:/workspace/github/lcp-github/docs/工具/lcpdoc_build.py"]

P = {}

P["imports"] = (
    "from lcpdoc_pagedesc import PAGE_DESC  # noqa: E402",
    "from lcpdoc_pagedesc import PAGE_DESC  # noqa: E402\n"
    "from lcpdoc_detail import MODULE_DETAIL, CROSS_USAGE  # noqa: E402\n"
    "from lcpdoc_howto import PAGE_HOWTO, PAGE_PIT  # noqa: E402"
)

P["xref_load"] = (
    'data = json.load(io.open(PAGES_JSON, encoding="utf-8"))',
    'XREF_JSON = os.environ.get("LCPDOC_XREF", "C:/Users/82302/AppData/Local/Temp/lcp-xref.json")\n'
    'xref_raw = json.load(io.open(XREF_JSON, encoding="utf-8")) if os.path.exists(XREF_JSON) else {}\n'
    'xref = {}\n'
    'for k, v in xref_raw.items():\n'
    '    seen = {}\n'
    '    for item in v:\n'
    '        seen.setdefault(item["owner"], set()).add(item["key"])\n'
    '    xref[k] = {o: sorted(ks) for o, ks in sorted(seen.items())}\n'
    'data = json.load(io.open(PAGES_JSON, encoding="utf-8"))'
)

# 模块详情要点
P["mod_detail"] = (
    """    A(f'<p class="intro">{esc(intro)}</p>')
    A('<div class="relbar">')""",
    """    A(f'<p class="intro">{esc(intro)}</p>')
    detail = MODULE_DETAIL.get(mod, [])
    if detail:
        A('<ul class="detail">')
        for d in detail:
            d = esc(d)
            d = re.sub(r'\\*\\*(.+?)\\*\\*', r'<b>\\1</b>', d)
            d = re.sub(r'`([^`]+)`', r'<code>\\1</code>', d)
            A(f'<li>{d}</li>')
        A('</ul>')
    A('<div class="relbar">')"""
)

# 页面卡片：怎么用 + 坑 + 被谁引用
P["page_howto"] = (
    """        if verbs or extras:
            A(f'<div class="caps">{verbs}{extras}</div>')""",
    """        howto = PAGE_HOWTO.get(f'{mod}/{p["resource"]}')
        if howto:
            A(f'<p class="howto"><span class="k">怎么用</span>{esc(howto)}</p>')
        if verbs or extras:
            A(f'<div class="caps">{verbs}{extras}</div>')
        pit = PAGE_PIT.get(f'{mod}/{p["resource"]}')
        if pit:
            A(f'<p class="pit"><span class="k">坑</span>{esc(pit)}</p>')
        used = xref.get(f'{mod}/{p["resource"]}')
        if used:
            chips = []
            for owner, keys in list(used.items())[:14]:
                label = MODULE_META.get(owner, (owner,))[0] if owner in MODULE_META else owner
                title = esc("、".join(keys[:6]))
                href = f'#mod-{owner}' if owner in MODULE_META else '#pages'
                chips.append(f'<a class="chip rel" href="{href}" title="{title}">{esc(label)}</a>')
            n = len(used)
            A(f'<div class="links"><span class="k">被引用</span>'
              f'<span class="hint">别处 {n} 个模块会用到它</span>' + "".join(chips) + '</div>')"""
)

# 跨模块用法章节（放在附录前）
P["cross_section"] = (
    """A('<section id="appendix" class="sec"><h2>附录</h2>')""",
    """A('<section id="crossusage" class="sec"><h2>跨模块用法：一个页面在别处怎么被用到</h2>'
  '<p class="muted">这些不是猜的，是从代码里挖出来的字段/权限引用（<code>pkg/apis</code> 里别的模块出现了这个资源的 ID 或权限码），'
  '再加上「它到底解决了什么问题」。看这一节能回答最常见的一类问题：<b>这个页面配的东西，什么时候生效？</b></p>')
A('<div class="usages">')
for a, b, note in CROSS_USAGE:
    am, ar = a.split('/')
    bm, br = b.split('/')
    A(f'<div class="usage"><div class="uhead">'
      f'<a class="pagelink" href="#{page_id(am,ar)}">{esc(page_label(am,ar))}</a>'
      f'<span class="arrow">用到</span>'
      f'<a class="pagelink" href="#{page_id(bm,br)}">{esc(page_label(bm,br))}</a></div>'
      f'<div class="unote">{esc(note)}</div></div>')
A('</div></section>')

A('<section id="appendix" class="sec"><h2>附录</h2>')"""
)

# 侧栏加入口
P["side"] = (
    """    '<a class="item" href="#map"><span>模块交接</span></a>' +""",
    """    '<a class="item" href="#crossusage"><span>跨模块用法</span></a>' +
    '<a class="item" href="#map"><span>模块交接</span></a>' +"""
)

# CSS
P["css"] = (
    """.links{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;font-size:12px;align-items:center}""",
    """.links{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;font-size:12px;align-items:center}
.links .hint{color:var(--muted);font-size:11.5px;margin-right:2px}
ul.detail{margin:6px 0 10px;padding-left:20px;font-size:13.5px}
ul.detail li{margin:3px 0}
.howto,.pit{margin:6px 0;font-size:13.5px;line-height:1.6}
.howto .k,.pit .k{display:inline-block;min-width:44px;font-size:11px;color:#fff;background:var(--accent);
  border-radius:4px;padding:0 6px;margin-right:6px;vertical-align:1px}
.pit .k{background:#c2410c}
.usages{display:grid;gap:10px}
.usage{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:var(--radius);padding:10px 14px}
.uhead{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:14px}
.uhead .arrow{color:var(--muted);font-size:12px}
.unote{color:var(--muted);font-size:13px;margin-top:4px}"""
)

for path in TARGETS:
    s = io.open(path, encoding="utf-8").read()
    for key, (old, new) in P.items():
        if old not in s:
            print("!! anchor not found in", path, "->", key)
            continue
        s = s.replace(old, new, 1)
    io.open(path, "w", encoding="utf-8", newline="\n").write(s)
    print("patched", path)
