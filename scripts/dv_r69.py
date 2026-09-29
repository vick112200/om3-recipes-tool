# -*- coding: utf-8 -*-
"""第 69 轮验收：连接流程「弹窗 / 浮层」隐患（SPEC-round69.md §2 审计清单）。

A. **无头浏览器真点**（这是本轮的重点 —— 弹窗类问题只能在真 DOM 里点出来）：
   ① `om3Ask` 串行化：A、B 两次调用 → A 立刻拿到 null（不再永挂）；B 点取消也拿到 null；浮层关闭
   ② 返回键/浮层收口：弹窗 / 扫码浮层 / 任务弹窗 / ☰菜单 各开一次 → `__handleBack()` 必须返回 true 且收掉
   ③ 任务总超时：`window.__om3taskMaxMs=700` + 跑一个**永不结束**的任务 → 700ms 后标题/进度写"超时未完成"、
      气泡带「超时」、`#taskClose` **可点**（运行中也放出来了）
   ④ 点任务弹窗的框外 = 收起（气泡出现）
   ⑤ 气泡上的 ✕ = 清掉气泡（不打开弹窗）
   ⑥ 蓝牙面板「结果码对照」按钮：点它不再用 window.prompt，而是自绘弹窗（`#omask` 打开）
B. **静态**：页面里 0 个 `alert/confirm/prompt`；`dialog:` 分支在；`__om3escClose` 被返回键与 Esc 共用；
   `om3Ask` 有 `_askCancel` 登记/注销；不新增 id。
C. 审计清单在位：规格 §2 的表里逐个列出所有浮层 id（防止以后新增浮层漏登记）。

跑法：python scripts/dv_r69.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r69.html')
SPEC = os.path.join(ROOT, 'SPEC-round69.md')
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


print('=== A. 无头浏览器真点（弹窗只能这么测） ===')
probe = []
probe.append("setTimeout(function(){var o=[];var g=function(id){return document.getElementById(id);};")
# ── ① om3Ask 串行化
probe.append("var got=[];")
probe.append("window.__om3ask({title:'A',body:'第一个',fields:[{label:'x',value:'1'}]}).then(function(v){got.push('A='+v);});")
probe.append("setTimeout(function(){")
probe.append("window.__om3ask({title:'B',body:'第二个',fields:[{label:'y',value:'2'}]}).then(function(v){got.push('B='+v);});")
probe.append("setTimeout(function(){")
probe.append("o.push('并发：' + got.join(',') + ' 弹窗开着=' + !g('omask').classList.contains('hide') + ' 标题=' + g('otitle').textContent);")
probe.append("g('ocancel').click();")           # 点取消关掉 B
probe.append("setTimeout(function(){")
probe.append("o.push('取消后：' + got.join(',') + ' 弹窗关=' + g('omask').classList.contains('hide'));")
# ── ② 返回键收浮层：弹窗
probe.append("window.__om3ask({title:'C',body:'第三个'}).then(function(v){got.push('C='+v);});")
probe.append("setTimeout(function(){")
probe.append("var r1=window.__handleBack();")
# ⚠ Promise 的 .then 是**微任务**：调完 __handleBack() 立刻读 got 会读到旧值 → 放到下一个 tick 再断言
probe.append("setTimeout(function(){")
probe.append("o.push('返回键收弹窗：ret=' + r1 + ' 关=' + g('omask').classList.contains('hide') + ' ' + got[got.length-1]);")
probe.append("},0);")
# ── ② 扫码浮层
probe.append("g('scanMask').classList.remove('hide');")
probe.append("var r2=window.__handleBack();")
probe.append("o.push('返回键收扫码：ret=' + r2 + ' 关=' + g('scanMask').classList.contains('hide'));")
# ── ② ☰菜单
probe.append("g('camMenuDrop').classList.remove('hide');")
probe.append("var r3=window.__handleBack();")
probe.append("o.push('返回键收菜单：ret=' + r3 + ' 关=' + g('camMenuDrop').classList.contains('hide'));")
# ── ③ 任务总超时（永不 resolve 的任务）
probe.append("window.__om3taskMaxMs=700;")
probe.append("window.__om3runTask('探针假任务', function(){ return new Promise(function(){}); });")
# 运行中（超时前）先看一眼：「关闭」按钮是否已经放出来、文案是否是"收起（任务继续跑）"
probe.append("setTimeout(function(){")
probe.append("o.push('运行中：关闭可见=' + !g('taskClose').classList.contains('hide') + ' 关闭文案=' + g('taskClose').textContent + ' 后台按钮文案=' + g('taskBg').textContent);")
probe.append("},300);")
probe.append("setTimeout(function(){")
probe.append("o.push('超时后：标题=' + g('taskTitle').textContent + ' 进度=' + g('taskProg').textContent.slice(0,26) + ' 关闭可见=' + !g('taskClose').classList.contains('hide') + ' 关闭文案=' + g('taskClose').textContent + ' 气泡=' + g('taskPillTxt').textContent);")
# ── ④ 点框外 = 收起
probe.append("g('taskMask').click();")
probe.append("setTimeout(function(){")
probe.append("o.push('点框外：卡片关=' + g('taskMask').classList.contains('hide') + ' 气泡可见=' + !g('taskPill').classList.contains('hide'));")
# ── ⑤ 气泡 ✕ = 清掉
probe.append("var x=g('taskPill').querySelector('[data-task=clear]'); o.push('气泡✕在=' + !!x);")
probe.append("if(x) x.click();")
probe.append("setTimeout(function(){")
probe.append("o.push('点✕后：气泡关=' + g('taskPill').classList.contains('hide') + ' 任务卡还是关的=' + g('taskMask').classList.contains('hide'));")
# ── ⑥ 结果码对照：点它应出自绘弹窗
probe.append("var card=g('bleCard'); if(card){ var d=card.querySelector('details'); if(d) d.open=true; }")
probe.append("var cb=g('bleCodeBtn');")
probe.append("if(cb) cb.click();")
probe.append("setTimeout(function(){")
probe.append("o.push('结果码按钮：弹窗开=' + (cb ? !g('omask').classList.contains('hide') : 'no-button') + ' 标题=' + g('otitle').textContent);")
probe.append("window.__om3askCancel();")
probe.append("o.push('运行错误=' + (window.__errs?window.__errs.length:0) + ' om3errs=' + (window.__om3errs||0));")
probe.append("var d2=document.createElement('div');d2.id='DBGOUT';d2.textContent=o.join(' ;; ');document.body.appendChild(d2);")
probe.append("},250);},250);},250);},900);},150);},150);},150);},150);},2600);")
head = ("<script>window.__OM3_APP__=1;window.__errs=[];window.addEventListener('error',function(e){"
        "window.__errs.push((e.message||'')+' @'+(e.lineno||0));});"
        "window.addEventListener('unhandledrejection',function(e){window.__errs.push('REJ '+String(e.reason));});</script>")
tail = '<script>' + ''.join(probe) + '</script>'
i = page.find('<body')
j = page.find('>', i) + 1
out = page[:j] + head + page[j:].replace('</body>', tail + '</body>', 1)
hp = os.path.join(TMP, 'dv_r69.html')
io.open(hp, 'w', encoding='utf-8', newline='').write(out)
ud = os.path.join(TMP, 'o69')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=20000', '--dump-dom',
                    'file:///' + hp.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=260)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
if k < 0:
    A(False, '无头浏览器没拿到输出（DOM %d 字节）' % len(dom))
else:
    got = dom[k:].split('>', 1)[1].split('</div>')[0]
    print('  （实测输出）' + got)
    A('并发：A=null' in got, '① 并发调用：第一个弹窗被按"取消"收掉（拿到 null）—— 不再永挂')
    A('B=null' in got and '弹窗关=true' in got, '① 第二个弹窗点取消后也正常返回 + 浮层真的关了')
    A('标题=B' in got, '① 后一个弹窗真的显示出来了（标题=B）')
    # 说明：C 是"只有正文、没有输入框"的弹窗 → 取消语义就是 false（有输入框的才是 null，
    #      见 om3Ask 里 hasInput 的约定）—— 这里钉的正是这个约定没被改掉。
    A('返回键收弹窗：ret=true 关=true C=false' in got,
      '② 弹窗开着按返回键 → 等价于点「取消」（无输入框的弹窗取消值=false，与既有约定一致），且页面接管（不会退出 App）')
    A('返回键收扫码：ret=true 关=true' in got, '② 扫码浮层开着按返回键 → 关掉浮层')
    A('返回键收菜单：ret=true 关=true' in got, '② ☰菜单开着按返回键 → 关掉菜单')
    A('超时未完成' in got and '超时' in got, '③ 任务永不结束 → 到点自己收尾并写明"超时未完成"')
    A('运行中：关闭可见=true' in got and '关闭文案=收起（任务继续跑）' in got
      and '后台按钮文案=收起到后台（任务继续跑）' in got,
      '③④ **运行中**「关闭」按钮就在（文案"收起（任务继续跑）"），后台按钮文案也直白（不再是"后台运行"四个字）')
    A('点框外：卡片关=true 气泡可见=true' in got, '④ 点任务弹窗框外 → 收起成气泡（原来点外面毫无反应）')
    A('气泡✕在=true' in got and '点✕后：气泡关=true' in got, '⑤ 气泡上的 ✕ 能清掉气泡')
    A('任务卡还是关的=true' in got, '⑤ 清气泡不等于打开任务弹窗（点 ✕ 没误触发）')
    A('结果码按钮：弹窗开=true' in got and '标题=结果码对照' in got,
      '⑥ 蓝牙「结果码对照」→ 出自绘弹窗（不再是 window.prompt）')
    A('运行错误=0' in got and 'om3errs=0' in got, '整个过程 0 运行错误（含 0 个未处理的 Promise 拒绝）')

print('=== B. 静态 ===')
A(not re.search(r'\balert\(', page), '页面里没有 alert(')
A(not re.search(r'(?<![.\w])confirm\(', page), '页面里没有 confirm(')
A('window.prompt(' not in page and not re.search(r'(?<![.\w])prompt\(', page)
  and 'window.__om3bleCodeAll' in page,
  '页面里**一个** window.prompt 调用都没有了（注释里提到名字不算；结果码查询仍在）')
A('window.__om3ask({' in page and "'查一下'" in page, '结果码对照改走 om3Ask')
A('_askCancel = function(){ done(hasInput ? null : false); };' in page, '② om3Ask 登记"当前弹窗的取消"')
A('if(_askCancel){ try{ _askCancel(); }catch(e){ om3err(e, "silent"); } }' in page, '② 新弹窗先把旧的按取消收掉')
A('if(doneOnce) return;' in page and 'window.__om3askCancel' in page, '② done 只收一次 + 对外出口')
A("inputmode" in page and 'f.numeric' in page, '② 数值字段给数字键盘')
A('window.__om3escClose = function(){' in page, '③ 浮层统一收口函数在')
back = page[page.index('window.__handleBack = function'):page.index('window.__handleBack = function') + 900]
A('window.__om3escClose && window.__om3escClose()' in back, '③ 返回键先调它')
A('window.__om3escClose&&window.__om3escClose()' in page, '③ Esc 也调它（同一份逻辑）')
A('TASK_MAX_MS = 180000' in page and 'window.__om3taskMaxMs' in page, '④ 任务总超时 180 秒（可覆盖）')
A('_run.timedOut' in page and "clearTimeout(_run.to)" in page, '④ 超时收尾 + 迟到返回只写日志')
A('window.__om3taskBg' in page and 'window.__om3taskClose' in page, '④ 收起/关闭只写一份实现')
A("t.id === 'taskMask'" in page, '④ 点遮罩=收起 的委托在')
A("data-task\" === 'clear'" in page or "data-task=" in page, '⑤ 气泡 ✕ 用 data-task 标记（不新增 id）')
gd = page[page.index('function camDirectConnect('):page.index('window.__om3direct = camDirectConnect;')]
A("r.indexOf('dialog') === 0" in gd and '添加网络' in gd and '回到本 App' in gd, '⑥ 直连的 dialog: 分支（说清是系统页面）')
si, so = ids(page), ids(old)
A(not (so - si), '老 id 一个都没少（少的：%s）' % (sorted(so - si) or '无'))
# 第 70 轮加了 7 个 id（搜索清空按钮 + 测试页排查项）——所以这里不再钉"本轮没新增 id"。
# 判据没放松：上面那条"第 69 轮当时那些 id 一个都不少"照样是少一个就红；
# 新增的那些由**当轮探针**按各自规格表断言（见 dv_r70 B8）。

print('=== C. 审计清单在位（SPEC-round69 §2） ===')
for x in ('omask', 'taskMask', 'taskPill', 'scanMask', 'camMenuDrop', 'toc', 'foldtip', 'lb'):
    A(x in spec, '§2 清单里登记了 %s' % x)
A('window.prompt' in spec and 'WebView' in spec, '§2.2 写清了"原生 prompt 为什么丑/不可控"')
A('Toast' in spec and '保留' in spec, '§2.3 写清了 Java 侧那两处 Toast 为什么保留')
A('## 2. 审计清单' in spec, '审计清单这一节在（下次可直接复跑 §2.4 的方法）')

print()
print('第 69 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
