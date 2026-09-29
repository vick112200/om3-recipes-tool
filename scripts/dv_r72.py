# -*- coding: utf-8 -*-
"""第 72 轮验收：「搜索按钮上面的字，点进去就没了」修复（SPEC-round72.md）。

需求方 2026-09-28：「而且本来这个搜索按钮上面有字，点进去就没了，你如果搞不定你搞个前端组件库吧」。

真因（静态就看得见，无需猜）：`#tocbtn` 现在的结构是
    <div id="tocbtn" class="searchbar"><span class="sic">🔍</span><span class="stx">搜索配方 · 作者 · 场景，或打开目录</span></div>
而老代码在开/关面板时写的是 `btn.textContent = o ? '✕' : '🔍';` / `btn.textContent='🔍';`
—— **一写就把两个 span 连同那句文字永久抹掉了**（第一次点开之后就没了，关掉也不会回来）。

A. **无头真点**：A1 初始有字 → A2 点开还有字（图标变 ✕）→ A3 关掉字回来 → A4 再来一轮字还在
                + A5/A6 第 71 轮的成果不许丢（关面板复位；不再强行藏入口条）
B. **静态**：开/关不再用 textContent 覆盖、有自愈重建兜底、老 id 一个不少、本轮不新增 id。

跑法：python scripts/dv_r72.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r72.html')
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
LABEL = '搜索配方 · 作者 · 场景，或打开目录'
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


print('=== A. 无头真点 ===')
# ⚠ 探针自己踩过的坑：把"取 span 文字"这种长长的表达式直接拼进步骤字符串，很容易少一个引号/括号
#   ——本轮就拼错过一次，结果前两步空转（STEP-ERR），什么也没测到还以为"通过了"。
#   所以统一交给 harness 里的 btnInfo()，步骤字符串只留最笨的拼接。
STEPS = [
    ("o.push('A1 初始 ' + btnInfo());", 200),
    ("g('tocbtn').click();", 400),                                          # ← 点开搜索
    ("o.push('A2 点开后 ' + btnInfo() + ' 入口条display=' + getComputedStyle(g('row2')).display);", 250),
    ("g('tocbtn').click();", 500),                                          # ← 关掉
    ("o.push('A3 关掉后 ' + btnInfo());", 250),
    ("g('tocbtn').click();", 400),                                          # ← 再开一轮
    ("g('tocbtn').click();", 500),                                          # ← 再关一轮
    ("o.push('A4 又开关一轮后 ' + btnInfo());", 250),
    # A6：第 71 轮的复位不许丢
    ("g('tocbtn').click();", 350),
    ("var q=g('tocq');q.value='人';q.dispatchEvent(new Event('input',{bubbles:true}));", 350),
    ("o.push('A6准备 搜后 框=[' + g('tocq').value + '] 结果可见=' + !g('tocres').classList.contains('hide'));"
     "g('tocbtn').click();", 600),
    ("o.push('A6 关面板后 框=[' + g('tocq').value + '] 结果可见=' + !g('tocres').classList.contains('hide')"
     " + ' 入口条display=' + getComputedStyle(g('row2')).display);", 150),
    # A7：真正的抹字路径 —— 搜出结果后**点一条结果**（跳转 + 关面板），看按钮上的字还在不在
    ("g('tocbtn').click();", 350),
    ("var q3=g('tocq');q3.value='人像';q3.dispatchEvent(new Event('input',{bubbles:true}));", 400),
    ("var a=g('tocres').querySelector('a');o.push('A7准备 结果里有链接=' + !!a);if(a)a.click();", 600),
    ("o.push('A7 点结果跳转后 ' + btnInfo());", 200),
]
tail = ('<script>\nvar o=[],STEPS=' + json.dumps([[s, d] for s, d in STEPS], ensure_ascii=False) + ',si=0;\n'
        'function g(i){return document.getElementById(i);}\n'
        "function spanText(el, cls){var x=el.querySelector(cls);return (x&&x.textContent)||'(没有)';}\n"
        "function btnInfo(){var b=g('tocbtn');return '图标=[' + spanText(b,'.sic') + '] 文字=[' + spanText(b,'.stx') + ']';}\n"
        'function finish(){var d=document.createElement("div");d.id=\'R72OUT\';'
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
hp = os.path.join(TMP, 'dv_r72.html')
io.open(hp, 'w', encoding='utf-8', newline='').write(out)
ud = os.path.join(TMP, 'o72')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,800',
                    '--virtual-time-budget=40000', '--dump-dom',
                    'file:///' + hp.replace(os.sep, '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
k = dom.find('id="R72OUT"')
if k < 0:
    A(False, '无头浏览器没拿到输出（DOM %d 字节）' % len(dom))
    got = ''
else:
    got = dom[k:].split('>', 1)[1].split('</div>')[0]
    got = got.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    for seg in got.split(' ;; '):
        print('  · ' + seg)
    A('STEP-ERR' not in got, 'A0 步骤队列全程没有抛错')
    A(('A1 初始 图标=[🔍] 文字=[%s]' % LABEL) in got, 'A1 一开始搜索按钮上有字（%s）' % LABEL)
    a2 = got.split('A2 点开后')[1].split(' ;; ')[0] if 'A2 点开后' in got else ''
    a3 = got.split('A3 关掉后')[1].split(' ;; ')[0] if 'A3 关掉后' in got else ''
    A(('文字=[%s]' % LABEL) in a2,
      'A2 **点开后按钮上仍然有字**（本轮核心：以前这里被 textContent 抹掉）')
    A('图标=[✕]' in a2, 'A2 点开后图标变成 ✕（开关状态仍然看得出来）')
    A(('文字=[%s]' % LABEL) in a3 and '图标=[🔍]' in a3,
      'A3 关掉后文字与图标都原样回来（不是只剩一个 🔍）')
    A(('A4 又开关一轮后 图标=[🔍] 文字=[%s]' % LABEL) in got, 'A4 反复开关也不会把字用没')
    A(re.search(r'A2 点开后 .*入口条display=flex', got) is not None,
      'A5 面板开着时入口条不再被强行隐藏（r71 那笔额外改动已撤回）')
    A(re.search(r'A6准备 搜后 框=\[人\] 结果可见=true', got) is not None, 'A6 前置：搜索能出结果')
    A(re.search(r'A6 关面板后 框=\[\] 结果可见=false', got) is not None,
      'A6 第 71 轮的"关面板即复位"没丢')
    a7 = got.split('A7 点结果跳转后')[1].split(' ;; ')[0] if 'A7 点结果跳转后' in got else ''
    A('A7准备 结果里有链接=true' in got, 'A7 前置：搜出结果、能点到结果里的链接')
    A(('文字=[%s]' % LABEL) in a7,
      'A7 **点搜索结果跳转之后，搜索按钮上的字还在**（这是真正抹字的那条路：close() 里写了 btn.textContent）')

print('=== B. 静态 ===')
A("btn.textContent=o?'\\u2715'" not in page and "btn.textContent = o ? '✕'" not in page,
  'B1 开面板不再用 textContent 覆盖按钮内容（就是它把文字抹掉的）')
A("btn.textContent='\\ud83d\\udd0d'" not in page and "btn.textContent='🔍'" not in page,
  'B1 关面板也不再覆盖')
A('function setTocBtn(' in page, 'B2 改成了 setTocBtn(open)：只切图标 + 切一个类')
A("btn.querySelector('.sic')" in page and "btn.querySelector('.stx')" in page, 'B2 只动 .sic/.stx 两个 span')
A("btn.innerHTML = '<span class=\"sic\">" in page, 'B3 自愈：结构万一被抹掉，会按原样重建')
A(LABEL in page, 'B4 按钮文案还在 HTML 里')
A('r71：搜索复位' in page, 'B5 第 71 轮的标记还在（没被这轮改回去）')
si, so = ids(page), ids(old)
A(not (so - si), 'B6 老 id 一个都没少（少的：%s）' % (sorted(so - si) or '无'))
A(not (si - so), 'B7 本轮**没有新增 id**（多的是：%s）' % (sorted(si - so) or '无'))

print()
print('第 72 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
