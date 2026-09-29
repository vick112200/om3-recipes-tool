# -*- coding: utf-8 -*-
"""让「优化版」也能搜：
1) IDX 索引里补上 21 个优化版槽位（点结果直接跳到优化版的对应槽位并高亮）
2) 优化版自己的目录面板 (#toc2) 加上搜索框 + 热门词 + 结果区
3) 搜索 JS 参数化成「两套面板共用一套逻辑」
"""
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
P = BASE + r'\app\base.html'
h = open(P, encoding='utf-8').read()
open(BASE + r'\app\base.before_search.html', 'w', encoding='utf-8', newline='').write(h)


def strip_tags(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s or '')).strip()


# ============================================================
# 一、IDX 补上优化版槽位
# ============================================================
i = h.find('var IDX=')
IDX, idx_end = json.JSONDecoder().raw_decode(h, i + len('var IDX='))
bykey = {}
for e in IDX:
    bykey.setdefault((e['n'].strip().lower(), e['a'].strip().lower()), e)

mode_titles = {}
for m in re.finditer(r'<div class="omode" id="(oC\d)">', h):
    t = re.search(r'<span class="omtitle">(.*?)</span>', h[m.start():m.start() + 3000])
    mode_titles[m.group(1)] = strip_tags(t.group(1)) if t else m.group(1)

slots = list(re.finditer(r'<div class="oslot" id="(oC\d)-([a-z0-9]+)">', h))
assert len(slots) == 21, len(slots)
added = []
for k, m in enumerate(slots):
    mid, num = m.group(1), m.group(2)
    end = slots[k + 1].start() if k + 1 < len(slots) else h.find('<div class="omode"', m.end())
    blk = h[m.start():end]
    nm = strip_tags(re.search(r'<span class="osname">(.*?)</span>', blk).group(1))
    numlab = strip_tags(re.search(r'<span class="osnum">(.*?)</span>', blk).group(1)) or ('槽 ' + num)
    au = strip_tags(re.search(r'<span class="osauth">(.*?)</span>', blk).group(1))
    st = re.search(r'<div class="osline style">(.*?)</div>', blk, re.S)
    style = strip_tags(st.group(1)) if st else ''
    rows = dict((strip_tags(a), strip_tags(b)) for a, b in
                re.findall(r'<span class="mk">(.*?)</span><span class="mv[^"]*">(.*?)</span>', blk, re.S))
    src = bykey.get((nm.lower(), au.lower())) or {}
    mt = mode_titles.get(mid, mid)
    added.append({
        'h': '%s-%s' % (mid, num),
        'n': nm,
        'a': au,
        'sl': '优化版 %s · %s' % (mid[1:], numlab),
        't': src.get('t') or rows.get('画面感觉', style)[:38],
        'g': src.get('g') or rows.get('适合', ''),
        'v': src.get('v') or rows.get('避开', ''),
        'f': (src.get('f') or rows.get('画面感觉', '')) + ' ｜ 优化版 %s %s：%s' % (mt, numlab, style),
    })
h = h[:i + len('var IDX=')] + json.dumps(IDX + added, ensure_ascii=False, separators=(',', ':')) + h[idx_end:]
print('IDX 增加优化版条目 %d 条（总 %d）' % (len(added), len(IDX) + len(added)))

# ============================================================
# 二、优化版面板加搜索框
# ============================================================
CHIPS = ''.join('<button type="button" data-q="%s">%s</button>' % (w, w) for w in
                ['人像', '街拍', '风光', '夜景', '日落', '复古', '黑白', '冷调', '暖调', '阴天'])
old_head = '<div class="t2head">优化版 · 目录</div>'
assert h.count(old_head) == 1
new_head = ('<div class="t2head">优化版 · 目录 / 搜配方</div>\n'
            '<input id="toc2q" class="tocsearch" type="search" placeholder="搜配方名 / 作者 / 场景（原版 + 优化版一起搜），如 人像、夜景、Portra…" autocomplete="off">\n'
            '<div class="chips" id="toc2chips">%s</div>\n'
            '<div id="toc2res" class="hide"></div>\n'
            '<div id="toc2browse">' % CHIPS)
h = h.replace(old_head, new_head, 1)

old_end = '</nav>\n<div id="paneC" class="pane hide">'
assert h.count(old_end) == 1
h = h.replace(old_end, '</div>\n<div class="emptytoc" id="noresult2">没找到匹配的配方。试试「人像」「夜景」「复古」，或者只搜一个字。</div>\n</nav>\n<div id="paneC" class="pane hide">', 1)

for a, b in [('<a class="lv2" href="#oC4">C4 夜景弱光档</a>', '<a class="lv2" href="#oC4">C4 夜景 / 混光档</a>'),
             ('<a class="lv3" href="#oC4-1">1. Paul Clark recipe</a>', '<a class="lv3" href="#oC4-1">1. Cool Spring</a>'),
             ('<a class="lv3" href="#oC4-2">2. Portra 160</a>', '<a class="lv3" href="#oC4-2">2. PNW</a>')]:
    assert h.count(a) == 1, a
    h = h.replace(a, b, 1)

# 搜索结果样式：给 #tocres 的规则补上 #toc2res
n_css = h.count('#tocres')
h = h.replace('#tocres', '#tocres,#toc2res')
print('搜索结果样式选择器扩展到 #toc2res（原 #tocres 出现 %d 处）' % n_css)

# ============================================================
# 三、搜索 JS 参数化
# ============================================================
JS = [
    (""" var q=document.getElementById('tocq'),res=document.getElementById('tocres'),
     browse=document.getElementById('tocbrowse'),empty=document.getElementById('noresult');""",
     """ var q=document.getElementById('tocq'),res=document.getElementById('tocres'),
     browse=document.getElementById('tocbrowse'),empty=document.getElementById('noresult');
 var q2=document.getElementById('toc2q'),res2=document.getElementById('toc2res'),
     browse2=document.getElementById('toc2browse'),empty2=document.getElementById('noresult2');
 var AQ=q,ARS=res,ABR=browse,AEM=empty;   // 当前生效的一组：原版 / 优化版
 function usePanel(inp){AQ=inp;if(inp===q2){ARS=res2;ABR=browse2;AEM=empty2;}else{ARS=res;ABR=browse;AEM=empty;}}"""),

    ("   return q.value.trim().toLowerCase()", "   return AQ.value.trim().toLowerCase()"),

    ("   if(!R){res.className='hide';browse.className='';empty.style.display='none';return;}",
     "   if(!R){ARS.className='hide';ABR.className='';AEM.style.display='none';return;}"),
    ("   browse.className='hide';res.className='';", "   ABR.className='hide';ARS.className='';"),
    ("   if(!list.length){res.innerHTML='';empty.style.display='block';return;}",
     "   if(!list.length){ARS.innerHTML='';AEM.style.display='block';return;}"),
    ("   empty.style.display='none';", "   AEM.style.display='none';"),
    ("   res.innerHTML=h;", "   ARS.innerHTML=h;"),

    (" if(r.sl.charAt(0)==='C')total+=5;   // 已排进 C1–C5 的配方优先，能直接上手",
     " if(r.sl.charAt(0)==='C'||r.h.charAt(0)==='o')total+=5;   // 已排进 C1–C5 或优化版槽位的，能直接上手，排前面"),

    (" function run(){var ts=terms();render(search(ts),ts);}\n q.addEventListener('input',run);\n q.addEventListener('search',run);",
     """ function run(inp){if(inp)usePanel(inp);var ts=terms();render(search(ts),ts);}
 q.addEventListener('input',function(){run(q);});
 q.addEventListener('search',function(){run(q);});
 q2.addEventListener('input',function(){run(q2);});
 q2.addEventListener('search',function(){run(q2);});"""),

    ("   chips[ci].addEventListener('click',function(){q.value=this.dataset.q;run();});",
     """   chips[ci].addEventListener('click',function(){q.value=this.dataset.q;run(q);});
 }
 var chips2=document.querySelectorAll('#toc2chips button');
 for(var c2=0;c2<chips2.length;c2++){
   chips2[c2].addEventListener('click',function(){q2.value=this.dataset.q;run(q2);});"""),

    (" /* ---------- 回到顶部 ---------- */",
     """ /* ---------- 搜索结果里点优化版条目 → 跳到优化版对应槽位 ---------- */
 function jumpHook(box){
   box.addEventListener('click',function(e){
     var a=e.target.closest?e.target.closest('a'):null;
     if(!a)return;
     var hh=(a.getAttribute('href')||'').replace(/^#/,'');
     if(hh.charAt(0)==='o'&&window.__jumpTo){e.preventDefault();close();window.__jumpTo(hh);}
   });
 }
 jumpHook(res);jumpHook(res2);

 /* ---------- 回到顶部 ---------- */"""),
]
for old, new in JS:
    n = h.count(old)
    assert n == 1, ('JS 锚点命中 %d 次：%s' % (n, old[:60]))
    h = h.replace(old, new, 1)
print('搜索 JS 参数化完成（%d 处）' % len(JS))

open(P, 'w', encoding='utf-8', newline='').write(h)
print('base.html %.1f KB' % (len(h.encode('utf-8')) / 1024))
