# -*- coding: utf-8 -*-
"""第 73 轮验收：修「点『测试页』却回到配方合集」（SPEC-round73.md）。

两个 bug（都用无头实测钉住）：
 ① 页签转发（块07）是嵌套三元、**没有 T 分支** → `data-p="T"` 兜底成 `tabBuiltin` → 程序化点击"配方合集"
 ② `#paneT` 被嵌在 `#paneD` 里（第 68 轮插入位置错）→ 连接相机页一隐藏，测试页跟着没了

A. **无头真点 + 程序化点击记录**（劫持 HTMLElement.prototype.click，直接看"到底点了哪个按钮"）：
   A1 起点在配方合集；A2 点「连接相机」→ paneD
   A3 ☰ → 「🔧 测试页」→ **不许点过 tabBuiltin**；paneA/paneD 都藏、paneT 显示且高度 > 0、cur=T
   A4 从测试页点「配方合集」→ 回 A；A5 从测试页点「连接相机」→ 回 D
   A6 直接点隐藏代理 #tabTest 也照样能进测试页
B. **静态**：`TABP` 映射表（含 T）、老嵌套三元已删、#paneT 的父元素不是 #paneD、
   六个 pane 都在、老 id 一个不少、本轮不新增 id。

跑法：python scripts/dv_r73.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r73.html')
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


page = io.open(PAGE, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()


def ids(t):
    return set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', t))


def nesting(html):
    """栈式扫描：每个 pane 的父元素（只用于结构断言）"""
    tag = re.compile(r'<(/?)(div|nav)\b([^>]*)>')
    stack, out = [], {}
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


print('=== A. 无头真点 + 程序化点击记录 ===')
STEPS = [
    ("o.push('A1 起点 cur=' + (window.__om3cur || '(未设)') + ' paneA=' + cls('paneA'));", 200),
    ("g('tabCam').click();", 400),
    ("o.push('A2 点连接相机 cur=' + window.__om3cur + ' paneA=' + cls('paneA') + ' paneD=' + cls('paneD'));"
     "window.__clicks = [];", 150),
    ("g('camMenuBtn').click();", 300),
    ("var t=null, bs=g('camMenuDrop').querySelectorAll('button');"
     "for(var i=0;i<bs.length;i++) if(bs[i].getAttribute('data-act')==='test') t=bs[i];"
     "o.push('A3 菜单里有测试页项=' + !!t); if(t) t.click();", 600),
    ("o.push('A3 点测试页后 cur=' + window.__om3cur + ' paneA=' + cls('paneA') + ' paneD=' + cls('paneD')"
     " + ' paneT=' + cls('paneT') + ' paneT高=' + Math.round(g('paneT').getBoundingClientRect().height));"
     "o.push('A3 这回程序化点击过的按钮=' + (window.__clicks||[]).join(','));"
     "window.__clicks = [];", 150),
    ("g('tabBuiltin').click();", 400),
    ("o.push('A4 从测试页点配方合集 cur=' + window.__om3cur + ' paneA=' + cls('paneA') + ' paneT=' + cls('paneT'));"
     "g('tabCam').click();", 400),
    ("o.push('A5 再点连接相机 cur=' + window.__om3cur + ' paneD=' + cls('paneD') + ' paneT=' + cls('paneT'));"
     "window.__clicks = [];", 150),
    ("g('tabTest').click();", 500),
    ("o.push('A6 直接点隐藏代理 tabTest cur=' + window.__om3cur + ' paneT=' + cls('paneT')"
     " + ' 高=' + Math.round(g('paneT').getBoundingClientRect().height)"
     " + ' 期间程序化点了=' + (window.__clicks||[]).join(','));"
     "o.push('A7 运行错误=' + (window.__errs?window.__errs.length:0) + ' om3errs=' + (window.__om3errs||0));", 150),
]
tail = ('<script>\nvar o=[],STEPS=' + json.dumps([[s, d] for s, d in STEPS], ensure_ascii=False) + ',si=0;\n'
        'function g(i){return document.getElementById(i);}\n'
        "function cls(id){var e=g(id);if(!e)return '无';return e.classList.contains('hide')?'隐藏':'显示';}\n"
        "var _c=HTMLElement.prototype.click;window.__clicks=[];\n"
        "HTMLElement.prototype.click=function(){try{window.__clicks.push(this.id||this.tagName);}catch(e){}return _c.apply(this,arguments);};\n"
        'function finish(){var d=document.createElement("div");d.id=\'R73OUT\';'
        'd.textContent=o.join(" ;; ");document.body.appendChild(d);}\n'
        'function next(){if(si>=STEPS.length){finish();return;}var st=STEPS[si++];'
        'try{(new Function(st[0]))();}catch(e){o.push("STEP-ERR@"+si+": "+e.message);}setTimeout(next,st[1]);}\n'
        'setTimeout(next,2600);\n</script>')
i0 = page.find('<body')
j0 = page.find('>', i0) + 1
out = (page[:j0] + '<script>window.__OM3_APP__=1;window.__errs=[];'
       "window.addEventListener('error',function(e){window.__errs.push((e.message||'')+' @'+(e.lineno||0));});"
       "window.addEventListener('unhandledrejection',function(e){window.__errs.push('REJ '+String(e.reason));});"
       '</script>' + page[j0:].replace('</body>', tail + '</body>', 1))
hp = os.path.join(TMP, 'dv_r73.html')
io.open(hp, 'w', encoding='utf-8', newline='').write(out)
ud = os.path.join(TMP, 'o73')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,800',
                    '--virtual-time-budget=40000', '--dump-dom',
                    'file:///' + hp.replace(os.sep, '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
k = dom.find('id="R73OUT"')
if k < 0:
    A(False, '无头浏览器没拿到输出（DOM %d 字节）' % len(dom))
    got = ''
else:
    got = dom[k:].split('>', 1)[1].split('</div>')[0]
    got = got.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    for seg in got.split(' ;; '):
        print('  · ' + seg)
    A('STEP-ERR' not in got, 'A0 步骤队列全程没有抛错')
    A(re.search(r'A2 点连接相机 cur=D paneA=隐藏 paneD=显示', got) is not None,
      'A2 点「连接相机」正常进 paneD')
    A('A3 菜单里有测试页项=true' in got, 'A3 ☰ 菜单里有「测试页」项')
    a3 = got.split('A3 点测试页后')[1].split(' ;; ')[0] if 'A3 点测试页后' in got else ''
    A(re.search(r'A3 点测试页后 cur=T paneA=隐藏 paneD=隐藏 paneT=显示', got) is not None,
      'A3 **点测试页 → 真的是测试页**（配方合集/连接相机都藏起来）—— %s' % a3)
    m = re.search(r'A3 点测试页后 .*paneT高=(\d+)', got)
    A(bool(m) and int(m.group(1)) > 300, 'A3 测试页**真的占屏幕高度**（%s px，以前它被嵌在 paneD 里、高度为 0）'
      % (m.group(1) if m else '?'))
    A(re.search(r'A3 这回程序化点击过的按钮=camMenuBtn,[^;]*tabTest[^;]*$', a3) is not None
      or ('tabBuiltin' not in a3.split('A3 这回程序化点击过的按钮=')[-1]),
      'A3 这回**没有再偷偷点「配方合集」(tabBuiltin)**')
    A(re.search(r'A4 从测试页点配方合集 cur=A paneA=显示 paneT=隐藏', got) is not None,
      'A4 从测试页点「配方合集」能回来')
    A(re.search(r'A5 再点连接相机 cur=D paneD=显示 paneT=隐藏', got) is not None,
      'A5 从测试页点「连接相机」也能去')
    A(re.search(r'A6 直接点隐藏代理 tabTest cur=T paneT=显示 高=\d{3,}', got) is not None,
      'A6 直接点隐藏代理 #tabTest 照样进测试页')
    A('A7 运行错误=0 om3errs=0' in got, 'A7 全程 0 运行错误 / 0 个 om3 错误')

print('=== B. 静态 ===')
A("var TABP = { A:'tabBuiltin', B:'tabB', C:'tabC', D:'tabCam', E:'tabMine', F:'tabF', T:'tabTest' };" in page,
  'B1 页签转发改成了映射表，且**含 T**')
A("var top = $(TABP[dp] || 'tabBuiltin');" in page, 'B1 转发按表走')
A("dp === 'F' ? 'tabF' : 'tabBuiltin'" not in page, 'B1 老的嵌套三元已删（就是它兜底到配方合集的）')
nest = nesting(page)
A(nest.get('paneT') == '(无/body)', 'B2 #paneT 现在是 body 的直接子元素（不是嵌在 #paneD 里）—— 实测 %s'
  % nest.get('paneT'))
A(nest.get('paneD') == '(无/body)', 'B2 #paneD 仍是 body 的直接子元素')
for p in ['paneA', 'paneB', 'paneC', 'paneD', 'paneE', 'paneT']:
    A(p in nest, 'B3 六个 pane 都在：%s' % p)
A("T:'paneT'" in page, 'B4 applyModule 的 map 里有 T')
A("var PS = ['A','B','C','D','E','T'];" in page, 'B4 兜底 switchPane 的 PS 里有 T')
A("var PANES = ['A', 'B', 'C', 'D', 'E', 'T'];" in page, 'B4 showPane 的 PANES 里有 T')
si, so = ids(page), ids(old)
A(not (so - si), 'B5 老 id 一个都没少（少的：%s）' % (sorted(so - si) or '无'))
A(not (si - so), 'B6 本轮**没有新增 id**（多的是：%s）' % (sorted(si - so) or '无'))

print()
print('第 73 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
