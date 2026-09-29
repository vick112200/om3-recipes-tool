# -*- coding: utf-8 -*-
"""第 71 轮验收：搜索"留着一个字的搜索记录"根治 + 面板输入框不再吸附（SPEC-round71.md）。

A. **无头浏览器真点**（步骤队列）：
   A1 打开面板搜「人」→ 结果出来
   A2 **关掉面板 → 输入框被清空 + 结果收掉**（本轮核心：原来关掉后那个字和结果都还留着）
   A3 再打开 → 仍是空的（"不留上次的搜索记录"）
   A4 面板里的输入框 `position` 不再是 sticky（需求方："进入搜索功能，输入框还固定不太合理"）
   A5 面板开着时页面那条搜索入口条不显示；关掉后恢复
   A6 关掉面板后 `#row2` 仍然是 sticky（第 70 轮的固顶没丢）
   A7 看门狗：**只改值不派发事件**（模拟原生 ✕）也能把结果收掉 —— 并且是在"另一个面板搜过之后"（r70 的守卫漏洞）
   A8 点自绘 ✕ → 清空 + 结果收掉
   A9 全程 0 运行错误 / 0 个 om3 错误
B. **静态**：原生 ✕ 已隐藏、`panelOpen` 用 computedStyle（钉住这轮的坑）、多事件齐全、
   复位与关闭挂钩在、**老 id 一个不少 + 本轮没有新增 id**。

跑法：python scripts/dv_r71.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r71.html')
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


print('=== A. 无头浏览器真点 ===')
STEPS = [
    ("g('tocbtn').click();", 350),
    ("window.__q=g('tocq');window.__res=g('tocres');"
     "o.push('A0 面板开着=' + (getComputedStyle(g('toc')).display!=='none')"
     " + ' 入口条显示=' + getComputedStyle(g('row2')).display);"
     "window.__q.value='人';window.__q.dispatchEvent(new Event('input',{bubbles:true}));", 350),
    ("o.push('A1 搜\"人\"后 框=[' + window.__q.value + '] 结果可见=' + !window.__res.classList.contains('hide'));"
     "o.push('A4 面板输入框 position=' + getComputedStyle(document.querySelector('#toc .tocsearchrow')).position);"
     "g('tocbtn').click();", 600),                                   # ← 关面板
    ("o.push('A2 关面板后 框=[' + window.__q.value + '] 结果可见=' + !window.__res.classList.contains('hide')"
     " + ' 入口条恢复=' + getComputedStyle(g('row2')).display"
     " + ' 入口条position=' + getComputedStyle(g('row2')).position);"
     "g('tocbtn').click();", 350),                                   # ← 再打开
    ("o.push('A3 再打开 框=[' + window.__q.value + '] 结果可见=' + !window.__res.classList.contains('hide'));"
     "g('tocbtn').click();", 400),
    # A7：先在档位推荐面板搜（把 ASC 变成 B），再回配方合集面板搜、然后"只改值"清空
    ("g('tabB').click();", 350),
    ("g('tocbtn').click();", 350),
    ("var q2=g('toc2q');q2.value='人';q2.dispatchEvent(new Event('input',{bubbles:true}));", 350),
    ("o.push('A7准备 B面板结果可见=' + !g('toc2res').classList.contains('hide'));g('tocbtn').click();", 400),
    ("g('tabBuiltin').click();", 350),
    ("g('tocbtn').click();", 350),
    ("g('tocq').value='人';g('tocq').dispatchEvent(new Event('input',{bubbles:true}));", 350),
    ("o.push('A7准备 A面板结果可见=' + !g('tocres').classList.contains('hide'));"
     "g('tocq').value='';", 900),                                   # ← 只改值、不派发事件（原生 ✕ 的行为）
    ("o.push('A7 只改值清空+900ms 结果隐藏=' + g('tocres').classList.contains('hide'));"
     "g('tocq').value='人像';g('tocq').dispatchEvent(new Event('input',{bubbles:true}));", 350),
    ("g('tocqc').click();", 350),
    ("o.push('A8 点自绘✕ 框=[' + g('tocq').value + '] 结果隐藏=' + g('tocres').classList.contains('hide'));"
     "o.push('A9 运行错误=' + (window.__errs?window.__errs.length:0) + ' om3errs=' + (window.__om3errs||0));", 0),
]
tail = ('<script>\nvar o=[],STEPS=' + json.dumps([[s, d] for s, d in STEPS], ensure_ascii=False) + ',si=0;\n'
        'function g(i){return document.getElementById(i);}\n'
        'function finish(){var d=document.createElement("div");d.id=\'R71OUT\';'
        'd.textContent=o.join(" ;; ");document.body.appendChild(d);}\n'
        'function next(){if(si>=STEPS.length){finish();return;}var st=STEPS[si++];'
        'try{(new Function(st[0]))();}catch(e){o.push("STEP-ERR@"+si+": "+e.message);}setTimeout(next,st[1]);}\n'
        'setTimeout(next,2500);\n</script>')
i0 = page.find('<body')
j0 = page.find('>', i0) + 1
out = (page[:j0] + '<script>window.__OM3_APP__=1;window.__errs=[];'
       "window.addEventListener('error',function(e){window.__errs.push((e.message||'')+' @'+(e.lineno||0));});"
       "window.addEventListener('unhandledrejection',function(e){window.__errs.push('REJ '+String(e.reason));});"
       '</script>' + page[j0:].replace('</body>', tail + '</body>', 1))
hp = os.path.join(TMP, 'dv_r71.html')
io.open(hp, 'w', encoding='utf-8', newline='').write(out)
ud = os.path.join(TMP, 'o71')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,800',
                    '--virtual-time-budget=40000', '--dump-dom',
                    'file:///' + hp.replace(os.sep, '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
k = dom.find('id="R71OUT"')
if k < 0:
    A(False, '无头浏览器没拿到输出（DOM %d 字节）' % len(dom))
    got = ''
else:
    got = dom[k:].split('>', 1)[1].split('</div>')[0]
    got = got.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    for seg in got.split(' ;; '):
        print('  · ' + seg)
    A('STEP-ERR' not in got, 'A/A0 步骤队列全程没有抛错')
    # ⚠ 第 72 轮把这条决定**撤回了**（需求方："本来这个搜索按钮上面有字，点进去就没了"）——
    #    面板打开时不再藏入口条，所以这里改成钉"入口条**还在**（display 不是 none）"。
    #    判据方向变了但同样是硬断言（理由见 SPEC-round72 §5）。
    A(re.search(r'A0 面板开着=true 入口条显示=(?!none)\w+', got) is not None,
      'A5 面板开着时：页面上那条搜索入口条**仍然在**（第 72 轮已撤回"藏起来"那笔改动）')
    A(re.search(r'A1 搜"人"后 框=\[人\] 结果可见=true', got) is not None, 'A1 搜「人」→ 结果出来')
    A('A4 面板输入框 position=relative' in got,
      'A4 面板里的输入框不再是 sticky（改为随内容滚动）')
    A(re.search(r'A2 关面板后 框=\[\] 结果可见=false', got) is not None,
      'A2 **关掉面板 → 输入框被清空 + 结果收掉**（本轮核心修复）')
    A('入口条恢复=flex' in got and '入口条position=sticky' in got,
      'A5/A6 关掉面板后入口条恢复显示、而且仍然是 sticky（第 70 轮固顶没丢）')
    A(re.search(r'A3 再打开 框=\[\] 结果可见=false', got) is not None,
      'A3 再打开时仍是空的 —— 不再留"上次那个字"的搜索记录')
    A('A7准备 B面板结果可见=true' in got and 'A7准备 A面板结果可见=true' in got,
      'A7 前置：A/B 两个面板都各自搜出了结果')
    A('A7 只改值清空+900ms 结果隐藏=true' in got,
      'A7 看门狗：只改值不派发事件也能把结果收掉（"另一个面板搜过"之后也成立 —— r70 的守卫漏洞已修）')
    A(re.search(r'A8 点自绘✕ 框=\[\] 结果隐藏=true', got) is not None, 'A8 点自绘 ✕ → 清空 + 结果收掉')
    A('A9 运行错误=0 om3errs=0' in got, 'A9 全程 0 运行错误 / 0 个 om3 错误')

print('=== B. 静态 ===')
A('::-webkit-search-cancel-button' in page and 'display:none' in page,
  'B1 已隐藏 WebView 自带的 type=search ✕（只留自绘的那个）')
A('getComputedStyle(el)' in page and "cs.display === 'none'" in page,
  'B2 panelOpen 用 computedStyle 判断（**钉住本轮的坑**：不能靠 hide 类）')
for ev in ['input', 'search', 'change', 'keyup', 'compositionend', 'paste', 'cut', 'blur']:
    A("'%s'" % ev in page or '"%s"' % ev in page, 'B3 多事件兜底里有 %s' % ev)
A('window.__om3searchReset = reset;' in page, 'B4 复位函数挂上了')
A('window.__om3tocClose = (function(orig){' in page, 'B4 关面板挂钩（点 ✕/点结果跳转那条路）在')
A('r71：搜索复位' in page, 'B5 r71 标记在（生成脚本幂等判据）')
# ⚠ 第 72 轮已把"面板开着时藏入口条"撤回（需求方要的是"上面有字"）→ 这里改钉"那笔藏起来没了"。
#   注意：#row2 的 display 在**按页签显隐**那儿本来就有（第 70 轮之前就在），所以只钉 r71 那笔的写法。
A("nowOpen ? 'none'" not in page, 'B6 面板开着时不再藏入口条（第 72 轮已撤回那笔改动）')
A('.tocsearchrow{position:relative' in page, 'B7 .tocsearchrow 已是 relative（不吸附）')
si, so = ids(page), ids(old)
A(not (so - si), 'B8 老 id 一个都没少（少的：%s）' % (sorted(so - si) or '无'))
A(not (si - so), 'B9 本轮**没有新增 id**（多的是：%s）' % (sorted(si - so) or '无'))

print()
print('第 71 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
