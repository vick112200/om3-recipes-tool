# -*- coding: utf-8 -*-
"""第 96 轮验收：给「我的方案」加**改名入口**（列表页直接改名 + 详情页第一屏）

验什么（对应 SPEC-round96.md §3）：
  A. 列表页：每条方案上有 `[data-mpren]` 按钮；点它**出弹窗、不进详情**；改名生效且**只动 name**；
     空名字拒绝并提示；取消不改；重名时弹窗如实提示。
  B. 详情页：`#mpEdit`（改名 / 描述）在**第一屏**（不滚动就看得见、且在页脚按钮之上）；
     点它照旧是 3 个字段（方案名/档位/描述），改完生效、槽位名与挂载状态不受影响。
  C. 浏览器模式（`file://` 直开、不带 `__OM3_APP__`）：本轮改动**不引入运行错误**。
     ⚠️ 口径：整个「我的配方」本来就是 App 专属（`if(!window.__OM3_APP__) return;` 那个 IIFE 里），
     浏览器模式里 `#mpList` 只有一句降级文字 —— 所以"浏览器里也能改名"**不是**本轮目标（见差异分析）。
  D. 静态：**新增 id = 0、新增 data-tv = 0**（新按钮只用属性选择器 `[data-mpren]`）；
     老 id 一个不少；`r96：` 标记在。

跑法：python scripts/dv_r96.py
"""
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
PAGE = os.path.join(ROOT, 'app', 'base.html')
OLD = os.path.join(ROOT, 'app', 'base.before_r96.html')
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
OK, FAIL = [], []


def A(c, msg):
    (OK if c else FAIL).append(msg)
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)


page = io.open(PAGE, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()


def run_headless(tag, pre, steps, budget=40000):
    tail = ('<script>\nvar o=[],STEPS=' + json.dumps([[s, d] for s, d in steps], ensure_ascii=False) + ',si=0;\n'
            'function g(i){return document.getElementById(i);}\n'
            'function q(sel){return document.querySelector(sel);}\n'
            'function dlg(){var m=g("omask");return !!(m && getComputedStyle(m).display!=="none" && !m.classList.contains("hide"));}\n'
            'function sets(){try{return JSON.parse(localStorage.getItem("om3sets")||"[]");}catch(e){return [];}}\n'
            'function finish(){var d=document.createElement("div");d.id=\'' + tag + '\';'
            'd.textContent=o.join(" ;; ");document.body.appendChild(d);}\n'
            'function next(){if(si>=STEPS.length){finish();return;}var st=STEPS[si++];'
            'try{(new Function(st[0]))();}catch(e){o.push("STEP-ERR@"+si+": "+e.message);}setTimeout(next,st[1]);}\n'
            'setTimeout(next,1400);\n</script>')
    i0 = page.find('<body')
    j0 = page.find('>', i0) + 1
    out = (page[:j0] + '<script>window.__errs=[];'
           "window.addEventListener('error',function(e){window.__errs.push((e.message||''));});"
           'try{' + pre + '}catch(e){window.__errs.push("PRE " + e.message);}</script>'
           + page[j0:].replace('</body>', tail + '</body>', 1))
    hp = os.path.join(TMP, 'dv_r96_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o96_' + tag)
    subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
    r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                        '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                        '--user-data-dir=' + ud, '--window-size=448,980',
                        '--virtual-time-budget=%d' % budget, '--dump-dom',
                        'file:///' + hp.replace(os.sep, '/')],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
    dom = r.stdout or ''
    k = dom.find('id="%s"' % tag)
    return (dom[k:].split('>', 1)[1].split('</div>')[0].replace('&lt;', '<')
            .replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"')) if k >= 0 else ''


SEED = (r"""localStorage.setItem('om3sets', JSON.stringify([
 {id:'a1',name:'人像三卷',desc:'甲描述',from:'myset1',mount:'on',mountTier:'myset1',mountSlots:[1],
  slots:{1:{used:3,vivid:[1,2,3,0,0,0,0,0,0,0,0,0],raw:{},name:'旧槽名'},2:null,3:null,4:null}},
 {id:'a2',name:'重名方案',desc:'乙描述',from:'myset2',slots:{1:null,2:null,3:null,4:null}},
 {id:'a3',name:'重名方案',desc:'丙描述',from:'myset3',slots:{1:null,2:null,3:null,4:null}}
]));
document.getElementById('tabMine').click();""")

print('=== A. 列表页直接改名（无头实测，App 模式）===')
got = run_headless('R96A', 'window.__OM3_APP__=1;\n', [
    (SEED, 700),
    (r"""var items=document.querySelectorAll('#mpList .mpitem');
var btns=document.querySelectorAll('#mpList [data-mpren]');
o.push('A1 条目='+items.length+' 改名按钮='+btns.length+' 文字='+(btns[0]?btns[0].textContent.trim():''));
o.push('A1b 是data-tv吗='+String(!!q('#mpList [data-tv]')));
btns[1].click();""", 500),
    (r"""var f=document.querySelectorAll('#ofields input,#ofields textarea');
o.push('A2 弹窗='+dlg()+' 标题='+(g('otitle')?g('otitle').textContent:''));
o.push('A2b 没进详情='+String(!g('mpBack'))+' 列表条目='+document.querySelectorAll('#mpList .mpitem').length);
o.push('A3 字段数='+f.length+' 预填='+JSON.stringify(f[0]?f[0].value:null));
o.push('A3b 正文含重名='+String((g('obody')?g('obody').textContent:'').indexOf('重名')>=0));
f[0].value='重名方案（改过）'; g('ook').click();""", 600),
    (r"""var a=sets(), s2=JSON.stringify(a[1]||{});
o.push('A4 name2='+JSON.stringify(a[1].name)+' name1='+JSON.stringify(a[0].name)+' name3='+JSON.stringify(a[2].name));
o.push('A4b 列表含新名='+String(document.getElementById('mpList').textContent.indexOf('重名方案（改过）')>=0));
o.push('A4c toast='+String(document.body.textContent.indexOf('已改名为')>=0));
o.push('A4d 日志='+String(document.body.textContent.indexOf('方案改名')>=0));
o.push('A5 其它字段='+JSON.stringify({id:a[1].id,desc:a[1].desc,from:a[1].from,slots:a[1].slots}));
o.push('A5b 没多字段='+JSON.stringify(Object.keys(a[1]).sort()));
q('#mpList [data-mpren]').click();""", 500),
    (r"""var f=document.querySelectorAll('#ofields input,#ofields textarea');
f[0].value='   '; g('ook').click();""", 600),
    (r"""var a=sets();
o.push('A6 空名后 name1='+JSON.stringify(a[0].name)+' 提示='+String(document.body.textContent.indexOf('名字不能为空')>=0));
o.push('A6b 弹窗还在吗='+dlg());
q('#mpList [data-mpren]').click();""", 500),
    (r"""var f=document.querySelectorAll('#ofields input,#ofields textarea');
f[0].value='不该生效的名字'; g('ocancel').click();""", 500),
    (r"""var a=sets();
o.push('A7 取消后 name1='+JSON.stringify(a[0].name)+' 方案数='+a.length);
document.querySelectorAll('#mpList .mpitem')[0].click();""", 600),
    (r"""var e=g('mpEdit'), x=g('mpExp'), d=g('mpDel');
o.push('B1 mpEdit在='+String(!!e)+' top='+Math.round(e.getBoundingClientRect().top)+' bottom='+Math.round(e.getBoundingClientRect().bottom)+' 视口高='+window.innerHeight+' 滚动='+Math.round(window.scrollY));
o.push('B2 在页脚之上='+String(e.getBoundingClientRect().top < Math.min(x.getBoundingClientRect().top, d.getBoundingClientRect().top)));
o.push('B2b 页脚只剩='+JSON.stringify([].map.call(document.querySelectorAll('#mpList .mpitem .r button'),function(b){return b.textContent.trim();})));
e.click();""", 500),
    (r"""var f=document.querySelectorAll('#ofields input,#ofields textarea,#ofields select');
o.push('B3 字段数='+f.length);
if(f.length>=3){ f[0].value='人像三卷（改名版）'; f[1].value='myset4'; f[2].value='新描述'; }
g('ook').click();""", 600),
    (r"""var a=sets();
o.push('B4 name='+JSON.stringify(a[0].name)+' from='+JSON.stringify(a[0].from)+' desc='+JSON.stringify(a[0].desc));
o.push('B5 槽1名='+JSON.stringify(a[0].slots['1']?a[0].slots['1'].name:null)+' 槽1色轮='+JSON.stringify(a[0].slots['1']?a[0].slots['1'].vivid:null));
o.push('B6 挂载='+JSON.stringify(String(a[0].mount||''))+'/'+JSON.stringify(String(a[0].mountTier||''))+' 错误='+(window.__errs||[]).length+' om3errs='+(window.__om3errs||0));""", 300),
])
print('  · ' + got[:1500])
A('A1 条目=3 改名按钮=3' in got and '✎ 改这个方案的名字' in got, 'A1 列表里每条方案都有一个改名按钮')
A('A1b 是data-tv吗=false' in got, 'A1b 新按钮**没有**用 data-tv（不碰 data-tv 集合）')
A('A2 弹窗=true' in got and 'A2b 没进详情=true' in got and '列表条目=3' in got, 'A2 点列表按钮 → 出弹窗，且**没有**进详情页')
A('A3 字段数=1' in got and '预填="重名方案"' in got, 'A3 弹窗只有一个字段、预填当前名字')
A('A3b 正文含重名=true' in got, 'A3b 有同名方案时，弹窗如实提示（含"重名"）')
A('A4 name2="重名方案（改过）"' in got and 'name1="人像三卷"' in got and 'name3="重名方案"' in got,
  'A4 只有被改的那一套名字变了')
A('A4b 列表含新名=true' in got, 'A4b 列表上立刻显示新名字')
A('A4c toast=true' in got and 'A4d 日志=true' in got, 'A4c 有 toast 提示 + 日志记一笔')
A('A5 其它字段={"id":"a2","desc":"乙描述","from":"myset2","slots":{"1":null,"2":null,"3":null,"4":null}}' in got,
  'A5 只动 name：id / desc / from / slots 逐字段没变')
A('A5b 没多字段=["desc","from","id","name","slots"]' in got, 'A5b 没有偷偷加新字段（数据格式不变）')
A('A6 空名后 name1="人像三卷"' in got and '提示=true' in got, 'A6 名字清空 → **拒绝改名** + 明确提示')
A('A7 取消后 name1="人像三卷"' in got and '方案数=3' in got, 'A7 点取消 → 什么都不改')
A('B1 mpEdit在=true' in got, 'B1 详情页第一屏有 #mpEdit')
_b1 = re.search(r'B1 mpEdit在=true top=(-?\d+) bottom=(-?\d+) 视口高=(\d+)', got)
A(bool(_b1) and int(_b1.group(1)) >= 0 and int(_b1.group(2)) <= int(_b1.group(3)),
  'B1b 它**不滚动就看得见**（top=%s ≥ 0 且 bottom=%s ≤ 视口 %s）' %
  ((_b1.groups() if _b1 else ('?', '?', '?'))))
A('B2 在页脚之上=true' in got, 'B2 它在页脚（导出 / 删除）**之上**（说明真的搬上来了，不是两处都有）')
A('B3 字段数=3' in got, 'B3 弹窗还是方案名 / 档位 / 描述三个字段（老口径不变）')
A('B4 name="人像三卷（改名版）" from="myset4" desc="新描述"' in got, 'B4 详情页改名 / 改档位 / 改描述都生效')
A('B5 槽1名="旧槽名"' in got, 'B5 改方案名**不影响**槽位名')
A('B6 挂载="on"/"myset1"' in got, 'B6 挂载状态没被改名碰掉')
A(re.search(r'错误=0 om3errs=0', got) is not None, 'B7 整个过程 0 运行错误')

print()
print('=== C. 浏览器模式（本轮改动不引入错误；「我的配方」本来就是 App 专属）===')
got2 = run_headless('R96C', '', [
    (r"""o.push('C1 mpTab='+typeof window.__om3mpTab+' ask='+typeof window.__om3ask);
o.push('C2 条目='+document.querySelectorAll('#mpList .mpitem').length);
o.push('C3 mpList文字='+JSON.stringify((document.getElementById('mpList').textContent||'').replace(/\s+/g,' ').slice(0,40)));
o.push('C4 错误='+(window.__errs||[]).length+' om3errs='+(window.__om3errs||0));""", 300),
], budget=20000)
print('  · ' + got2[:400])
A('C1 mpTab=undefined' in got2 and 'ask=undefined' in got2,
  'C1 浏览器模式里「我的配方」整块本来就不在（App 专属 IIFE）')
A('C2 条目=0' in got2, 'C2 所以浏览器里也没有"列表改名"入口（不是本轮引入的缺失）')
A('C4 错误=0' in got2, 'C3 本轮改动在浏览器模式 0 运行错误')

print()
print('=== D. 静态 ===')
A('r96：' in page, 'D1 `r96：` 标记在（生成脚本改过）')
A(page.count('data-mpren') == 3, 'D2 新增属性 data-mpren 恰好 3 处（渲染 / 委托 / 注释）')
A('function mpRenameDialog(setIdx){' in page and 'window.__om3mpRename = mpRenameDialog;' in page,
  'D3 改名函数在、且导出（供探针与后续轮次用）')
A(page.count('id="mpEdit"') == 1 and "id=\"mpEdit\" class=\"mpbtn\"" in page,
  'D4 #mpEdit 只有一处，且是 mpbtn 样式（第一屏那个）')
A("'<button type=\"button\" id=\"mpEdit\">改名 / 描述</button>'" not in page, 'D4b 页脚那个旧的 #mpEdit 撤干净了')
ids_p = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', page))
ids_o = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', old))
A(ids_p == ids_o, 'D5 新增 id = 0（多的：%s；少的：%s）' % (sorted(ids_p - ids_o), sorted(ids_o - ids_p)))
tv_p = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
tv_o = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
A(tv_p == tv_o, 'D6 新增 data-tv = 0（多的：%s；少的：%s）' % (sorted(tv_p - tv_o), sorted(tv_o - tv_p)))
A("data-mpren=\"' + idx + '\"" in page, 'D7 列表按钮带**方案下标**（不是"改最后一个"这种假入口）')

print()
print('第 96 轮探针：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
