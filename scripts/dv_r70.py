# -*- coding: utf-8 -*-
"""第 70 轮验收：搜索框 3 处毛病 + ☰ 菜单分层（SPEC-round70.md）。

A. **无头浏览器真点 + 几何**（布局/交互只能这么测；用"步骤队列"跑，避免深层嵌套回调）：
   ① 清空可靠：输入"人像"→ 结果出来；点自绘 ✕ → 框空 + 结果收掉
   ② 原生 ✕ 的替代场景：**直接改 value 不派发事件** → 看门狗必须在 ~800ms 内把结果收掉
   ③ #row2 固顶：滚 1200px 后它仍吸在视口顶部（position=sticky）
   ④ 面板内输入框固顶：面板滚 800px 后 #tocq 仍在面板顶部
   ⑤ 档位推荐：点搜索条 → #toc2q 在 nav#toc2 里、且在视口内（改前它 y=4518，在页面最底部）
   ⑥ 场景对比：#paneC 顶到 .scselwrap 顶的间距 = 0（改前 56px）
   ⑦ ☰ 菜单：正好 10 项（7 个排查项没了）；点测试页项能进测试页
   ⑧ 测试页：4 个新按钮在，点「检查权限」有输出且 0 运行错误
B. **静态**：menuAct 统一出口、测试页按钮接同一份实现、新增 id 完全等于规格表、老 id 一个不少。

跑法：python scripts/dv_r70.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r70.html')
SPEC = os.path.join(ROOT, 'SPEC-round70.md')
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
spec = io.open(SPEC, encoding='utf-8').read()


def ids(t):
    return set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', t))


print('=== A. 无头浏览器真点 + 几何 ===')
# 步骤队列：(JS, 跑完后等多少毫秒)
STEPS = [
    ("g('tocbtn').click();", 250),                                            # 打开搜索面板（配方合集）
    ("window.__q=g('tocq'); window.__res=g('tocres');"
     "o.push('①面板开=' + !g('toc').classList.contains('hide'));"
     "window.__q.value='人像'; window.__q.dispatchEvent(new Event('input',{bubbles:true}));", 300),
    ("o.push('①搜到结果：结果区可见=' + !window.__res.classList.contains('hide')"
     " + ' 内容长度=' + window.__res.textContent.length);"
     "g('tocqc').click();", 300),                                              # 点自绘 ✕
    ("o.push('①点✕后：值=[' + window.__q.value + '] 结果区隐藏=' + window.__res.classList.contains('hide'));"
     "window.__q.value='人像'; window.__q.dispatchEvent(new Event('input',{bubbles:true}));", 300),
    ("window.__q.value='';", 800),                                             # ← 只改值、不派发事件（原生 ✕ 的行为）
    ("o.push('②原生✕(不派发事件)+800ms：结果区隐藏=' + window.__res.classList.contains('hide'));"
     "g('toc').scrollTop=800;", 350),
    ("o.push('④面板滚800后 #tocq 的 top(相对视口)=' + Math.round(window.__q.getBoundingClientRect().top));"
     "g('toc').scrollTop=0; g('tocbtn').click();", 300),                        # 收起面板
    ("window.scrollTo(0,1200);", 350),
    ("var r2=g('row2');o.push('③滚1200后 #row2 top=' + Math.round(r2.getBoundingClientRect().top)"
     " + ' position=' + getComputedStyle(r2).position + ' display=' + getComputedStyle(r2).display);"
     "window.scrollTo(0,0);", 250),
    ("g('tabB').click();", 350),                                               # 切到档位推荐
    ("g('tocbtn').click();", 350),                                             # 打开档位推荐的面板
    # ⚠ 原来写成 while(e2=q2.parentElement){…} —— 每轮都读同一个父节点，白打印 5 次；这里逐级往上走
    ("var q2=g('toc2q'),ch=['input#toc2q'],e2=q2.parentElement,i2=0;"
     "while(e2 && i2++<4){var cl=(typeof e2.className==='string'&&e2.className.trim())?('.'+e2.className.trim().split(/\\s+/)[0]):'';"
     "ch.push(e2.tagName.toLowerCase()+(e2.id?('#'+e2.id):'')+cl);e2=e2.parentElement;}"
     "o.push('⑤档位推荐 父链=' + ch.join('<') + ' top=' + Math.round(q2.getBoundingClientRect().top)"
     " + ' 在视口内=' + (q2.getBoundingClientRect().top>0 && q2.getBoundingClientRect().top<300)"
     " + ' 清空按钮在=' + !!g('toc2qc'));g('tocbtn').click();", 300),
    ("g('tabC').click();", 350),                                               # 切到场景对比
    ("var pc=g('paneC'),sw=document.querySelector('.scselwrap');"
     "o.push('⑥场景对比 paneC顶=' + Math.round(pc.getBoundingClientRect().top)"
     " + ' 看哪个场景顶=' + Math.round(sw.getBoundingClientRect().top)"
     " + ' 间距=' + Math.round(sw.getBoundingClientRect().top-pc.getBoundingClientRect().top)"
     " + ' position=' + getComputedStyle(sw).position);", 200),
    ("g('tabCam').click();", 350),                                             # 回连接相机
    ("g('camMenuBtn').click();", 300),
    ("var bt=g('camMenuDrop').querySelectorAll('button'),acts=[];"
     "for(var i3=0;i3<bt.length;i3++)acts.push(bt[i3].getAttribute('data-act')||('step'+bt[i3].getAttribute('data-step')));"
     "o.push('⑦菜单项=' + acts.join(','));"
     "for(var i4=0;i4<bt.length;i4++) if(bt[i4].getAttribute('data-act')==='test') bt[i4].click();", 350),
    ("o.push('⑦点测试页项 paneT可见=' + !g('paneT').classList.contains('hide') + ' cur=' + window.__om3cur);"
     "o.push('⑧测试页按钮=' + ['tvPerm','tvBarDiag','tvProf','tvMap'].map(function(x){return x+'='+(!!g(x));}).join(' '));"
     "if(g('tvPerm')) g('tvPerm').click();", 400),
    ("o.push('⑧点tvPerm out字数=' + ((g('tvOut')||{}).textContent||'').length);"
     "o.push('⑧运行错误=' + (window.__errs?window.__errs.length:0) + ' om3errs=' + (window.__om3errs||0));", 0),
]
steps_js = json.dumps([[s, d] for s, d in STEPS], ensure_ascii=False)
tail = ('<script>\nvar o=[], STEPS=' + steps_js + ', si=0;\n'
        'function g(i){ return document.getElementById(i); }\n'
        # ⚠ 这里必须用**单引号**写 id：否则下面 dom.find('id="DBGOUT"') 会先命中探针自己的 JS 文本
        'function finish(){ var d=document.createElement("div"); d.id=\'DBGOUT\';'
        ' d.textContent=o.join(" ;; "); document.body.appendChild(d); }\n'
        'function nextStep(){\n'
        '  if(si>=STEPS.length){ finish(); return; }\n'
        '  var st=STEPS[si++];\n'
        '  try{ (new Function(st[0]))(); }catch(e){ o.push("STEP-ERR@"+si+": "+e.message); }\n'
        '  setTimeout(nextStep, st[1]);\n'
        '}\nsetTimeout(nextStep, 2600);\n</script>')
head = ("<script>window.__OM3_APP__=1;window.__errs=[];window.addEventListener('error',function(e){"
        "window.__errs.push((e.message||'')+' @'+(e.lineno||0));});"
        "window.addEventListener('unhandledrejection',function(e){window.__errs.push('REJ '+String(e.reason));});</script>")
i = page.find('<body')
j = page.find('>', i) + 1
out = page[:j] + head + page[j:].replace('</body>', tail + '</body>', 1)
hp = os.path.join(TMP, 'dv_r70.html')
io.open(hp, 'w', encoding='utf-8', newline='').write(out)
ud = os.path.join(TMP, 'o70')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,800',
                    '--virtual-time-budget=40000', '--dump-dom',
                    'file:///' + hp.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
if k < 0:
    A(False, '无头浏览器没拿到输出（DOM %d 字节）' % len(dom))
    got = ''
else:
    got = dom[k:].split('>', 1)[1].split('</div>')[0]
    # DOM dump 里 textContent 的 < > & 会被实体化（父链那一行就是靠这个）→ 先还原，再断言
    got = got.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    for seg in got.split(' ;; '):
        print('  · ' + seg)
    A('STEP-ERR' not in got, 'A0 步骤队列全程没有抛错')
    A('①面板开=true' in got, 'A1 打开搜索面板')
    A(re.search(r'①搜到结果：结果区可见=true 内容长度=[1-9]', got) is not None, 'A2 输入"人像"→ 结果出来')
    A('①点✕后：值=[] 结果区隐藏=true' in got, 'A3 点自绘 ✕ → 输入框清空 + 结果收掉')
    A('②原生✕(不派发事件)+800ms：结果区隐藏=true' in got,
      'A4 模拟原生 ✕（只改 value 不派发事件）→ 看门狗在 800ms 内把结果收掉 ←"清空后残留"的修复')
    m = re.search(r'④面板滚800后 #tocq 的 top\(相对视口\)=(-?\d+)', got)
    # ⚠ 第 71 轮按需求方新要求**改回了不吸附**（"进入搜索功能，这时输入框还是固定，这不太合理"）——
    #    所以这里改成钉"它会随内容滚走（top<0）"，判据方向反了但同样是硬断言（见 SPEC-round71 §5）。
    A(bool(m) and int(m.group(1)) < 0,
      'A5 面板滚 800px 后 #tocq 随内容滚走（top=%s，r71 起不再吸附）' % (m.group(1) if m else '?'))
    m2 = re.search(r'③滚1200后 #row2 top=(-?\d+) position=(\w+) display=(\w+)', got)
    A(bool(m2) and abs(int(m2.group(1)) - 49) < 8 and m2.group(2) == 'sticky' and m2.group(3) == 'flex',
      'A6 滚 1200px 后 #row2 仍吸在**顶栏下面**（top≈49 = --om3toph）—— %s' % (m2.group(0) if m2 else '没测到'))
    A(re.search(r'⑤档位推荐 父链=input#toc2q<div\.tocsearchrow<div\.toc2searchbox<nav#toc2', got) is not None,
      'A7 档位推荐的搜索框已经**在 nav#toc2 面板里**（改前它在 paneB 尾部，y=4518）')
    A(re.search(r'⑤档位推荐 .*在视口内=true.*清空按钮在=true', got) is not None,
      'A8 打开面板就看到搜索框（视口内）+ ✕ 清空按钮在')
    m3 = re.search(r'⑥场景对比 .*间距=(-?\d+) position=(\w+)', got)
    A(bool(m3) and int(m3.group(1)) == 0 and m3.group(2) == 'sticky',
      'A9 场景对比：间距 = 0（改前 56）且 sticky —— %s' % (m3.group(0) if m3 else '没测到'))
    mm = re.search(r'⑦菜单项=([^;]+)', got)
    acts = mm.group(1).strip().split(',') if mm else []
    A(acts == ['step1', 'step2', 'step3', 'step4', 'test', 'verify', 'selftest', 'direct', 'exp', 'imp'],
      'A10 ☰ 菜单正好这 10 项（7 个排查项都搬走了、也没有重复项）：%s' % acts)
    A('⑦点测试页项 paneT可见=true' in got, 'A11 点「🔧 测试页」菜单项 → 真的进了测试页')
    A('⑧测试页按钮=tvPerm=true tvBarDiag=true tvProf=true tvMap=true' in got, 'A12 测试页 4 个新按钮都在')
    A(re.search(r'⑧点tvPerm out字数=[1-9]', got) is not None, 'A13 点「检查权限」有输出')
    A('⑧运行错误=0 om3errs=0' in got, 'A14 全程 0 运行错误 / 0 个 om3 错误')

print('=== B. 静态 ===')
A('function menuAct(a){' in page and 'window.__om3menuAct = menuAct;' in page, 'B1 统一的 menuAct + 导出')
A('window.__om3menuAct(a1);' in page, 'B1 菜单点击走 menuAct（不再各写一份）')
tvjs = page[page.index('/* ================= r68：测试页'):page.index("\n  var cc = $('camConnCheck')")]
A("tvAdv('tvPerm', 'perm'" in tvjs and "tvAdv('tvBarDiag', 'bardiag'" in tvjs
  and "tvAdv('tvProf', 'prof'" in tvjs and "tvAdv('tvMap', 'map'" in tvjs,
  'B2 测试页 4 个按钮接的是同一份实现')
A('window.__om3menuAct' in tvjs, 'B2 测试页调 window.__om3menuAct（不是自己重写）')
A('TASK_MAX_MS' in page and 'window.__om3escClose' in page, 'B3 第 69 轮的修复都还在（防回归）')
A('.toc2searchbox' in page and 'nav2.insertBefore(box, nav2.firstChild)' in page,
  'B4 末尾那段"把搜索组搬进面板"的脚本在（只搬节点、id 不改）')
A('setTopH()' in page and '--om3toph' in page and '--om3rowh' in page, 'B5 顶栏高度实测 + CSS 变量')
A("if(v1 !== seen.A){ seen.A = v1; if(!panelOpen('B')) run(q); }" in page,
  'B6 搜索看门狗在（r71 版：比字符串 + 不抢另一个面板）')
si, so = ids(page), ids(old)
A(not (so - si), 'B7 老 id 一个都没少（少的：%s）' % (sorted(so - si) or '无'))
sec = spec[spec.index('### 3.1'):spec.index('## 4. ☰ 菜单逐项审计')]
declared = set()
for line in sec.splitlines():
    if not line.startswith('|') or '❌' in line:
        continue
    for mm2 in re.finditer(r'`([A-Za-z][A-Za-z0-9_]*)`', line.split('|')[1]):
        declared.add(mm2.group(1))
added = si - so
A(added == declared, 'B8 新增 id **完全等于**规格 §3.1 那张表（多：%s / 少：%s）'
  % (sorted(added - declared) or '无', sorted(declared - added) or '无'))
print('  （新增 %d 个：%s）' % (len(added), '、'.join(sorted(added))))

print()
print('第 70 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
