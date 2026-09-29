# -*- coding: utf-8 -*-
"""第 42 轮 · 步骤 1：**删掉我设计的那 12 条「本站设计」**（用户：「你那几个本机方案我感觉不行，把那一块删掉」）
连带要删的（它们都只服务于这 12 条）：
  · `#paneF`（本站设计页签）+ 底栏按钮 + 顶栏代理 #tabF + PANES/PS 里的 'F'
  · `#toc3`（本站设计的目录）+ 搜索池 LIDX + ASC='F' 分支
  · `#mode-OM3L`（12 张卡片）+ `__OM3RECIPES__`/`IDX` 里的 12 条
  · 优化版里的 **LAB 档**（`#oLAB` + modetabs 按钮）
  · 图库里的 12 张模拟预览图 + 2 张自检图
保留：三份目录/搜索的那几个**真 bug 修复**（#toc2 元素补齐、监听保护），以及场景页/自绘下拉等第 39–41 轮的成果。
"""
import io, json, os, re, sys
P = r'D:\workspace\om3-handbook\app\base.html'
IMG = r'D:\workspace\om3-handbook\apk\assets\images'
sys.stdout.reconfigure(encoding='utf-8')
s = io.open(P, encoding='utf-8').read()
n = 0


def cut(start_mark, end_mark, label, include_end=True):
    """删掉 start_mark 到 end_mark（含）之间的内容"""
    global s, n
    i = s.find(start_mark)
    if i < 0:
        print('  ⚠ 找不到起点：%s' % label)
        return False
    j = s.find(end_mark, i + len(start_mark))
    if j < 0:
        print('  ⚠ 找不到终点：%s' % label)
        return False
    j += len(end_mark) if include_end else 0
    s = s[:i] + s[j:]
    n += 1
    print('  ✅ 删除：%s' % label)
    return True


def rep(old, new, must=True, label=''):
    global s, n
    if old not in s:
        if must:
            print('  ⚠ 没找到：%s' % (label or old[:50]))
        return
    s = s.replace(old, new, 1)
    n += 1


print('=== ① 删页签结构 ===')
# paneF 整块（到 paneB 之前）
cut('<div id="paneF" class="pane hide">', '<div id="paneB"', 'paneF 页签', include_end=False)
rep('<button type="button" data-p="F">本站设计</button>\n', '', label='底栏按钮')
rep('      <button type="button" data-p="F" id="tabF" style="display:none">本站设计</button>\n', '', label='顶栏代理')
rep("var PANES = ['A', 'F', 'B', 'C', 'D', 'E'];     /* 唯一真源：要加页签只改这一行（第 39 轮加 'F' 本站设计） */",
    "var PANES = ['A', 'B', 'C', 'D', 'E'];          /* 唯一真源：要加页签只改这一行 */", label='PANES')
rep("var PS = ['A','F','B','C','D','E'];   /* 第 39 轮：加 'F' 本站设计（另一处清单 PANES 也要加，两处都是真源） */",
    "var PS = ['A','B','C','D','E'];", label='PS')
rep("var ids = ['paneA', 'paneF', 'paneB', 'paneC', 'paneD', 'paneE'];   /* 第 39 轮：加 paneF */",
    "var ids = ['paneA', 'paneB', 'paneC', 'paneD', 'paneE'];", label='联动清单')
rep("if(/^pane[A-F]$/.test(id))return id.slice(4);", "if(/^pane[A-E]$/.test(id))return id.slice(4);", label='paneOfEl')
rep("""    /* 第 39 轮：本站设计的卡片在自己那个页签里（pane F），锚点是 #r-om3lab_* */
    var pF = (el.closest && el.closest('#paneF')) ? 'F' : null;
    var pWant = pF ? 'F' : (om ? 'B' : 'A');""",
    "    var pWant = om ? 'B' : 'A';", label='jumpTo 的 F 分支')

print('=== ② 删目录/搜索的第三份 ===')
cut('<nav id="toc3">', '</nav>', 'toc3 面板')
rep("var nav3 = document.getElementById('toc3');   /* 第 39 轮：本站设计目录 */\n"
    "  function panel(){ var m = curMod(); if(m === 'F') return (nav3 || nav2 || nav); return (m === 'A') ? (nav || nav2) : (nav2 || nav3 || nav); }",
    "function panel(){ return (curMod()==='A') ? (nav || nav2) : (nav2 || nav); }", label='panel()')
rep("window.__om3tocSync = function(p2){ try{ var q3 = String(p2||'A'); pane = (q3==='F') ? 'F' : ((q3==='A') ? 'A' : 'B'); }catch(e){} };",
    "window.__om3tocSync = function(p2){ try{ pane = (String(p2||'A')==='A') ? 'A' : 'B'; }catch(e){} };", label='__om3tocSync')
rep("""    /* 第 39 轮：目录面板从 2 份变 3 份 —— A 原版 #toc / F 本站设计 #toc3 / B 优化版 #toc2 */
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
    }""",
    """    function panelOf(){
      var want2 = false;
      try{ want2 = (String(window.__om3cur || '') === 'B'); }catch(e){ want2 = false; }
      var p1 = $('toc'), p2 = $('toc2');
      return (want2 ? (p2 || p1) : (p1 || p2));
    }
    function othersOf(p){
      var all = [$('toc'), $('toc2')], out = [];
      for(var i = 0; i < all.length; i++) if(all[i] && all[i] !== p) out.push(all[i]);
      return out;
    }""", label='panelOf/othersOf')
rep(""" var RIDX=[],OIDX=[],LIDX=[];             // 按页签分开的三份索引：原版卡片 / 优化版槽位 / 本站设计
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
 }""",
    """ var RIDX=[],OIDX=[];                     // 按页签分开的两份索引：原版卡片 / 优化版槽位
 for(var zi=0;zi<IDX.length;zi++)(IDX[zi].h.charAt(0)==='o'?OIDX:RIDX).push(IDX[zi]);
 var ASC='A';                             // 当前搜索范围：A=原版方案，B=优化版
 function POOL(){return ASC==='B'?OIDX:RIDX;}
 function usePanel(inp){AQ=inp;if(inp===q2){ARS=res2;ABR=browse2;AEM=empty2El();ASC='B';}else{ARS=res;ABR=browse;AEM=empty;ASC='A';}}""",
    label='搜索池回两份')
for frag in [" var q3=document.getElementById('toc3q'),res3=document.getElementById('toc3res'),\n"
             "     browse3=document.getElementById('toc3browse'),empty3=document.getElementById('noresult3');\n"
             " function empty3El(){ return empty3 || (empty3 = document.getElementById('noresult3')); }\n",
             " if(q3){ q3.addEventListener('input',function(){run(q3);}); q3.addEventListener('search',function(){run(q3);}); }\n"]:
    rep(frag, '', must=False, label='toc3 搜索残留')

print('=== ③ 删 12 张卡片 + 数据 + 索引 + LAB 档 ===')
cut('<!-- OM3LAB-BEGIN -->', '<!-- OM3LAB-END -->', 'OM3LAB 卡片分区')  # 若已随 paneF 一起删掉，找不到属正常
cut('<!-- OLAB-BEGIN -->', '<!-- OLAB-END -->', 'LAB 档本体')
rep('<button type="button" data-m="oLAB">LAB 本站设计</button>', '', label='modetabs LAB 按钮')
# 数据与索引里的 12 条（slug 以 om3lab_ 开头 / 锚点 oLAB-）
rec = re.search(r'window\.__OM3RECIPES__=', s)
DEC = json.JSONDecoder()
R, e1 = DEC.raw_decode(s, rec.start() + len('window.__OM3RECIPES__='))
idx = re.search(r'var IDX=', s)
I, e2 = DEC.raw_decode(s, idx.start() + len('var IDX='))
r2 = [x for x in R if not str(x.get('slug', '')).startswith('om3lab_')]
i2 = [x for x in I if not str(x.get('h', '')).startswith(('r-om3lab_', 'oLAB-'))]
print('  配方 %d → %d（删 %d）｜索引 %d → %d（删 %d）' % (len(R), len(r2), len(R) - len(r2), len(I), len(i2), len(I) - len(i2)))
s = (s[:rec.start() + len('window.__OM3RECIPES__=')] + json.dumps(r2, ensure_ascii=False, separators=(',', ':')) + s[e1:])
idx = re.search(r'var IDX=', s)
I, e2 = DEC.raw_decode(s, idx.start() + len('var IDX='))
i2 = [x for x in I if not str(x.get('h', '')).startswith(('r-om3lab_', 'oLAB-'))]
s = s[:idx.start() + len('var IDX=')] + json.dumps(i2, ensure_ascii=False, separators=(',', ':')) + s[e2:]
n += 2

io.open(P, 'w', encoding='utf-8', newline='').write(s)

# ④ 删图
k = 0
for f in sorted(os.listdir(IMG)):
    if f.startswith('om3lab_') and '__sim__' in f or f.startswith('simcheck__'):
        os.remove(os.path.join(IMG, f)); k += 1
print('=== ④ 删除模拟预览图 %d 张 ===' % k)
print('\n✅ 步骤 1 完成（共 %d 处删除/替换）。残留自查：' % n)
for kw in ('om3lab', 'oLAB', 'paneF', 'toc3', 'LIDX', "data-p=\"F\""):
    print('   %-10s 残留 %d 处' % (kw, s.count(kw)))
