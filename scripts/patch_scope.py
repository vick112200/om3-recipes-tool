# -*- coding: utf-8 -*-
"""搜索按页签分范围：原版方案页签只搜原版，优化版页签只搜优化版 21 个槽位。"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
P = BASE + r'\app\base.html'
h = open(P, encoding='utf-8').read()
open(BASE + r'\app\base.before_scope.html', 'w', encoding='utf-8', newline='').write(h)

EDITS = []

# 1) 按页签切成两份索引 + 当前范围
EDITS.append((
    """ var AQ=q,ARS=res,ABR=browse,AEM=empty;   // 当前生效的一组：原版 / 优化版
 function usePanel(inp){AQ=inp;if(inp===q2){ARS=res2;ABR=browse2;AEM=empty2;}else{ARS=res;ABR=browse;AEM=empty;}}""",
    """ var AQ=q,ARS=res,ABR=browse,AEM=empty;   // 当前生效的一组：原版 / 优化版
 var RIDX=[],OIDX=[];                     // 按页签分开的两份索引：原版卡片 / 优化版槽位
 for(var zi=0;zi<IDX.length;zi++)(IDX[zi].h.charAt(0)==='o'?OIDX:RIDX).push(IDX[zi]);
 var ASC='A';                             // 当前搜索范围：A=原版方案，B=优化版
 function POOL(){return ASC==='B'?OIDX:RIDX;}
 function usePanel(inp){AQ=inp;if(inp===q2){ARS=res2;ABR=browse2;AEM=empty2;ASC='B';}else{ARS=res;ABR=browse;AEM=empty;ASC='A';}}"""))

# 2) prime() 只在当前范围内判断词是否有主字段命中
EDITS.append((
    """     for(var j=0;j<IDX.length&&!ts[i].p;j++)
       for(var fi=0;fi<F.length;fi++)
         if(has(IDX[j],F[fi][0],ts[i].qs)){ts[i].p=true;break;}""",
    """     var P0=POOL();
     for(var j=0;j<P0.length&&!ts[i].p;j++)
       for(var fi=0;fi<F.length;fi++)
         if(has(P0[j],F[fi][0],ts[i].qs)){ts[i].p=true;break;}"""))

# 3) search() 两轮都只在当前范围内打分
EDITS.append((
    """   var i,o,strict=[];
   for(i=0;i<IDX.length;i++){o=score(IDX[i],ts,true);if(o)strict.push(o);}""",
    """   var i,o,strict=[],P=POOL();
   for(i=0;i<P.length;i++){o=score(P[i],ts,true);if(o)strict.push(o);}"""))
EDITS.append((
    """     var loose=[];
     for(i=0;i<IDX.length;i++){o=score(IDX[i],ts,false);if(o)loose.push(o);}""",
    """     var loose=[];
     for(i=0;i<P.length;i++){o=score(P[i],ts,false);if(o)loose.push(o);}"""))

# 4) 两个搜索框的提示语写明范围
EDITS.append((
    'placeholder="搜配方名 / 作者 / 场景，如 人像、夜景、Portra…"',
    'placeholder="只在原版方案里搜：配方名 / 作者 / 场景，如 人像、夜景、Portra…"'))
EDITS.append((
    'placeholder="搜配方名 / 作者 / 场景（原版 + 优化版一起搜），如 人像、夜景、Portra…"',
    'placeholder="只在优化版里搜（21 个槽位）：配方名 / 作者 / 场景，如 人像、夜景、Portra…"'))

# 5) 优化版面板的空结果提示
EDITS.append((
    '<div class="emptytoc" id="noresult2">没找到匹配的配方。试试「人像」「夜景」「复古」，或者只搜一个字。</div>',
    '<div class="emptytoc" id="noresult2">优化版 21 个槽位里没找到匹配的。试试「人像」「夜景」「复古」，或者只搜一个字；想看全站配方请到「原版方案」页签搜。</div>'))

for old, new in EDITS:
    n = h.count(old)
    assert n == 1, ('锚点命中 %d 次：%s' % (n, old[:60]))
    h = h.replace(old, new, 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('搜索已按页签分范围（%d 处），base.html %.1f KB' % (len(EDITS), len(h.encode('utf-8')) / 1024))
