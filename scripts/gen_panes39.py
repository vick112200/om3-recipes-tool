# -*- coding: utf-8 -*-
"""第 39 轮（A）：在「原版方案」和「优化版」之间插入独立页签 **本站设计（pane F）**，
并把**目录**与**搜索**接到三个页签（原版 A / 本站设计 F / 优化版 B）。

改了什么（逐条对应验收）：
 A1  `#barABC` 底栏在 A 与 B 之间插入 `<button data-p="F">本站设计</button>`
 A2  `PANES` 加 'F'（showPane 的注释就写着"要加页签只改这一行"）
 A3  `#paneA` 里那一大坨 `<!-- OM3LAB-BEGIN -->…#mode-OM3L` **整段搬进** 新建的 `#paneF > .wrap`
     （paneA 因此变短；卡片/数据/索引都不用动，锚点 `#r-om3lab_*` 照旧）
 A4  `pane` / `__om3tocSync` / `paneOfEl` / `jumpTo` 认识 'F'
 A5  目录面板从 2 份变 3 份：新增 `#toc3`（本站设计目录 + 独立搜索框）；`panelOf()` 按页签选，
     `apply()` 收掉**其余全部**面板（原来是"另一个"，三份会叠）
 A6  搜索池从 2 个变 3 个：`RIDX`(原版) / `LIDX`(本站设计) / `OIDX`(优化版)，
     `ASC` 记当前范围，`usePanel()` 三分支
 A7  **顺手修一个潜在崩点**：`#toc2` 根本没有 `#toc2q/#toc2res/#toc2browse/#noresult2`
     （注释说"后面的脚本注入"，但 `q2.addEventListener` 是无保护调用）—— 这里补齐元素 + 给三处
     监听都加存在性保护，否则"优化版搜索"会整段中断。
"""
import io, re, sys
sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
s = io.open(P, encoding='utf-8').read()
n = 0


def rep(old, new, cnt=1, must=True):
    global s, n
    c = s.count(old)
    if c == 0:
        if must:
            raise SystemExit('❌ 锚点没找到：%s' % old[:70])
        print('  ⚠ 跳过（找不到）：%s' % old[:60])
        return
    s = s.replace(old, new, cnt)
    n += 1


# ---------- A1 底栏按钮 ----------
rep('''<div class="barABC" id="barABC">
  <button type="button" data-p="A" class="on">原版方案</button>
  <button type="button" data-p="B">优化版</button>''',
    '''<div class="barABC" id="barABC">
  <button type="button" data-p="A" class="on">原版方案</button>
  <button type="button" data-p="F">本站设计</button>
  <button type="button" data-p="B">优化版</button>''')

# ---------- A2 PANES ----------
rep("var PANES = ['A', 'B', 'C', 'D', 'E'];          /* 唯一真源：要加页签只改这一行 */",
    "var PANES = ['A', 'F', 'B', 'C', 'D', 'E'];     /* 唯一真源：要加页签只改这一行（第 39 轮加 'F' 本站设计） */")

# ---------- A4 pane 变量 ----------
rep("try{ pane = (p === 'A') ? 'A' : 'B'; }catch(e0){}      /* 目录面板跟着页签走 */",
    "try{ pane = (p === 'F') ? 'F' : ((p === 'A') ? 'A' : 'B'); }catch(e0){}   /* 目录面板跟着页签走（三份：A 原版 / F 本站设计 / B 优化版） */")
rep("if(/^pane[A-E]$/.test(id))return id.slice(4);",
    "if(/^pane[A-F]$/.test(id))return id.slice(4);")
rep("    var om = el.closest ? el.closest('.omode') : null;\n"
    "    var tab = document.querySelector('.tabs button[data-p=\"' + (om ? 'B' : 'A') + '\"]');",
    "    var om = el.closest ? el.closest('.omode') : null;\n"
    "    /* 第 39 轮：本站设计的卡片在自己那个页签里（pane F），锚点是 #r-om3lab_* */\n"
    "    var pF = (el.closest && el.closest('#paneF')) ? 'F' : null;\n"
    "    var tab = document.querySelector('.tabs button[data-p=\"' + (pF ? 'F' : (om ? 'B' : 'A')) + '\"]');")

# ---------- A5 目录面板：三份 ----------
rep("""    function panelOf(){
      var want2 = false;
      try{ want2 = (String(window.__om3cur || '') === 'B'); }catch(e){ want2 = false; }
      var p1 = $('toc'), p2 = $('toc2');
      return (want2 ? (p2 || p1) : (p1 || p2));
    }
    function otherOf(p){
      var p1 = $('toc'), p2 = $('toc2');
      if(p && p2 && p === p2) return p1;
      if(p && p1 && p === p1) return p2;
      return null;
    }""",
    """    /* 第 39 轮：目录面板从 2 份变 3 份 —— A 原版 #toc / F 本站设计 #toc3 / B 优化版 #toc2 */
    function panelOf(){
      var cur = '';
      try{ cur = String(window.__om3cur || ''); }catch(e){ cur = ''; }
      var p1 = $('toc'), p2 = $('toc2'), p3 = $('toc3');
      if(cur === 'F') return (p3 || p2 || p1);
      if(cur === 'B') return (p2 || p3 || p1);
      return (p1 || p3 || p2);
    }
    function othersOf(p){
      var all = [$('toc'), $('toc2'), $('toc3')], out = [];
      for(var i = 0; i < all.length; i++) if(all[i] && all[i] !== p) out.push(all[i]);
      return out;
    }""")
rep("""      var q = otherOf(p);
      if(q && q !== p){
        try{ q.classList.remove('open'); q.style.setProperty('display','none','important'); }catch(e2){ om3err(e2, "silent"); }
      }""",
    """      var others = othersOf(p);
      for(var oi = 0; oi < others.length; oi++){
        var q = others[oi];
        try{ q.classList.remove('open'); q.style.setProperty('display','none','important'); }catch(e2){ om3err(e2, "silent"); }
      }""")

# ---------- 块02：panel() / __om3tocSync ----------
rep("function panel(){ return (curMod()==='A') ? nav : nav2; }",
    "var nav3 = document.getElementById('toc3');   /* 第 39 轮：本站设计目录 */\n"
    "  function panel(){ var m = curMod(); if(m === 'F') return (nav3 || nav2 || nav); return (m === 'A') ? (nav || nav2) : (nav2 || nav3 || nav); }")
rep("window.__om3tocSync = function(p2){ try{ pane = (String(p2||'A')==='A') ? 'A' : 'B'; }catch(e){} };",
    "window.__om3tocSync = function(p2){ try{ var q3 = String(p2||'A'); pane = (q3==='F') ? 'F' : ((q3==='A') ? 'A' : 'B'); }catch(e){} };")

# ---------- A6 搜索：三个池 ----------
rep(""" var RIDX=[],OIDX=[];                     // 按页签分开的两份索引：原版卡片 / 优化版槽位
 for(var zi=0;zi<IDX.length;zi++)(IDX[zi].h.charAt(0)==='o'?OIDX:RIDX).push(IDX[zi]);
 var ASC='A';                             // 当前搜索范围：A=原版方案，B=优化版
 function POOL(){return ASC==='B'?OIDX:RIDX;}
 function usePanel(inp){AQ=inp;if(inp===q2){ARS=res2;ABR=browse2;AEM=empty2El();ASC='B';}else{ARS=res;ABR=browse;AEM=empty;ASC='A';}}""",
    """ var RIDX=[],OIDX=[],LIDX=[];             // 按页签分开的三份索引：原版卡片 / 优化版槽位 / 本站设计
 /* 第 39 轮加第三份：本站设计 = 原版页里那 12 张自设计卡片(#r-om3lab_*) + 优化版 LAB 槽位(#oLAB-*)。
    分类按锚点前缀：'o' 开头=优化版；'r-om3lab_'=本站设计；其余=原版。 */
 for(var zi=0;zi<IDX.length;zi++){
   var hz=String(IDX[zi].h||'');
   if(hz.charAt(0)==='o')OIDX.push(IDX[zi]);
   else if(hz.indexOf('r-om3lab_')===0)LIDX.push(IDX[zi]);
   else RIDX.push(IDX[zi]);
 }
 var ASC='A';                             // 当前搜索范围：A=原版方案，F=本站设计，B=优化版
 function POOL(){return ASC==='B'?OIDX:(ASC==='F'?LIDX:RIDX);}
 function usePanel(inp){
   AQ=inp;
   if(inp&&inp===q2){ARS=res2;ABR=browse2;AEM=empty2El();ASC='B';}
   else if(inp&&inp===q3){ARS=res3;ABR=browse3;AEM=empty3El();ASC='F';}
   else {ARS=res;ABR=browse;AEM=empty;ASC='A';}
 }""")

# 取第三份元素 + 兜底取元素函数
rep(" function empty2El(){ return empty2 || (empty2 = document.getElementById('noresult2')); }",
    " function empty2El(){ return empty2 || (empty2 = document.getElementById('noresult2')); }\n"
    " /* 第三份：本站设计（#toc3 里的搜索框） */\n"
    " var q3=document.getElementById('toc3q'),res3=document.getElementById('toc3res'),\n"
    "     browse3=document.getElementById('toc3browse'),empty3=document.getElementById('noresult3');\n"
    " function empty3El(){ return empty3 || (empty3 = document.getElementById('noresult3')); }")

# 监听加保护（原来 q2 是无保护调用，元素不存在就整段中断）
rep(" q.addEventListener('input',function(){run(q);});\n"
    " q.addEventListener('search',function(){run(q);});\n"
    " q2.addEventListener('input',function(){run(q2);});\n"
    " q2.addEventListener('search',function(){run(q2);});",
    " /* 第 39 轮：三处监听全部加存在性保护（元素缺一个也不能让整段搜索逻辑中断） */\n"
    " if(q){ q.addEventListener('input',function(){run(q);}); q.addEventListener('search',function(){run(q);}); }\n"
    " if(q2){ q2.addEventListener('input',function(){run(q2);}); q2.addEventListener('search',function(){run(q2);}); }\n"
    " if(q3){ q3.addEventListener('input',function(){run(q3);}); q3.addEventListener('search',function(){run(q3);}); }")

# ---------- A7 给 #toc2 补齐它缺的一组搜索元素 ----------
i2 = s.find('<nav id="toc2">')
j2 = s.find('</nav>', i2)
assert i2 > 0 and j2 > i2
blk2 = s[i2:j2 + 6]
if 'id="toc2q"' not in blk2:
    head_end = blk2.find('</div>', blk2.find('t2head')) + 6
    inject = ('\n<input id="toc2q" class="tocsearch" type="search" '
              'placeholder="只在优化版里搜：档位 / 槽位 / 配方名 / 作者，如 C1、夜景、Portra…" autocomplete="off">\n'
              '<div class="chips"><button type="button" data-q="人像">人像</button>'
              '<button type="button" data-q="街拍">街拍</button><button type="button" data-q="风光">风光</button>'
              '<button type="button" data-q="夜景">夜景</button><button type="button" data-q="胶片">胶片</button>'
              '<button type="button" data-q="黑白">黑白</button></div>\n'
              '<div id="toc2res" class="hide"></div>\n'
              '<div id="noresult2" class="hide">没有匹配项 —— 换个词，或直接点下面的目录。</div>\n')
    new_blk = blk2[:head_end] + inject + '<div id="toc2browse">' + blk2[head_end:] + '</div>'
    new_blk = new_blk.replace('</nav>', '</nav>', 1)
    s = s[:i2] + new_blk + s[j2 + 6:]
    n += 1
    print('  已给 #toc2 补齐搜索元素（#toc2q/#toc2res/#toc2browse/#noresult2）')

# ---------- A3 搬走 OM3LAB 段 → 新页签 #paneF ----------
ib = s.find('<!-- OM3LAB-BEGIN -->')
ie = s.find('<!-- OM3LAB-END -->')
assert ib > 0 and ie > ib
lab = s[ib:ie + len('<!-- OM3LAB-END -->')]
s = s[:ib] + s[ie + len('<!-- OM3LAB-END -->'):]
paneF = ('\n<!-- ===== 第 39 轮：本站设计独立页签（pane F）===== -->\n'
         '<div id="paneF" class="pane hide">\n<div class="wrap">\n'
         '<h1>本站设计</h1>\n'
         '<p class="sub">12 条配方是我们自己照现有 58 条的设计思路推的 —— <b>没有相机实拍样片</b>，'
         '卡片里那张是<b>模拟预览</b>。数值可直接加入我的方案 / 写入相机；相机上只有 C1–C5，'
         '写入时在弹窗里选目标档位。</p>\n'
         + lab + '\n</div>\n</div>\n')
ip = s.find('<div id="paneB"')
assert ip > 0
s = s[:ip] + paneF + s[ip:]
n += 1

# ---------- A5 新建 #toc3（本站设计目录）----------
objs = re.findall(r'<div class="card" id="(r-om3lab_[a-z0-9\-]+)"><div class="chd"><span class="cname">([^<]+)</span>', s)
assert len(objs) == 12, '本站设计卡片不是 12 张：%d' % len(objs)
links = ''.join('<a class="lv3" href="#%s">%d. %s</a>' % (h, i + 1, nm) for i, (h, nm) in enumerate(objs))
toc3 = ('\n<nav id="toc3">\n'
        '<div class="t2head">本站设计 · 搜索 / 目录</div>\n'
        '<input id="toc3q" class="tocsearch" type="search" '
        'placeholder="只在本站设计里搜：配方名 / 场景 / 感觉，如 肤色、晚霞、食物、通透…" autocomplete="off">\n'
        '<div class="chips"><button type="button" data-q="肤色">肤色</button>'
        '<button type="button" data-q="食物">食物</button><button type="button" data-q="夜景">夜景</button>'
        '<button type="button" data-q="晚霞">晚霞</button><button type="button" data-q="绿意">绿意</button>'
        '<button type="button" data-q="雪">雪</button><button type="button" data-q="通透">通透</button></div>\n'
        '<div id="toc3res" class="hide"></div>\n'
        '<div id="noresult3" class="hide">没有匹配项 —— 换个词，或直接点下面的目录。</div>\n'
        '<div id="toc3browse">\n'
        '<div class="tg"><div class="tgh">说明</div>\n'
        '<a class="lv2" href="#mode-OM3L">本站设计（12 条）· 这 12 条是怎么来的</a>\n'
        '<a class="lv2" href="#oLAB">优化版里的第 6 档 · LAB 本站设计</a>\n'
        '</div>\n'
        '<div class="tg"><div class="tgh">12 条配方</div>\n' + links + '\n</div>\n'
        '</div>\n</nav>\n')
i2b = s.find('<nav id="toc2">')
j2b = s.find('</nav>', i2b) + 6
s = s[:j2b] + toc3 + s[j2b:]
n += 1

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('✅ 第 39 轮（A）已改 %d 处：#paneF + 底栏按钮 + PANES + 三份目录 + 三份搜索池' % n)
print('   本站设计卡片 %d 张已搬进 #paneF；#toc3 目录 %d 条' % (len(objs), len(objs)))
