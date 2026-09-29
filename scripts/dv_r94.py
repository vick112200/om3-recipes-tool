# -*- coding: utf-8 -*-
"""第 94 轮验收：**打赏功能"隐藏但可一键开"**

验什么：
  A. 顶栏里那个 ☕ 按钮**还在 DOM 里**（`data-tv="donate"` 一处不少），但**看不见**（`display:none` / 盒高 0）。
  B. **一键能开**：把它的 `style` 去掉（模拟"以后再做"），点一下 → 站内弹窗照常出现且只有一个"谢谢"按钮；
     没嵌收款码时如实说"还没放进来"。→ 证明"隐藏"没把功能弄坏。
  C. 收尾：探针里改的那点 DOM 不影响页面文件；`OM3_DONATE_IMG` 那行仍在（以后填图用）。
  D. 静态：id 集合没变、data-tv 集合没变（本轮**没有**新增/删除）、Java 没改、`r94：` 标记在。

跑法：python scripts/dv_r94.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r94.html')
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
OLDJ = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.before_r84.java')
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
OK, FAIL = [], []


def A(c, msg):
    (OK if c else FAIL).append(msg)
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)


page = io.open(PAGE, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()
java = io.open(JAVA, encoding='utf-8').read()
oldj = io.open(OLDJ, encoding='utf-8').read() if os.path.exists(OLDJ) else ''


def run_headless(tag, steps, budget=40000):
    tail = ('<script>\nvar o=[],STEPS=' + json.dumps([[s, d] for s, d in steps], ensure_ascii=False) + ',si=0;\n'
            'function g(i){return document.getElementById(i);}\n'
            'function q(sel){return document.querySelector(sel);}\n'
            'function finish(){var d=document.createElement("div");d.id=\'' + tag + '\';'
            'd.textContent=o.join(" ;; ");document.body.appendChild(d);}\n'
            'function next(){if(si>=STEPS.length){finish();return;}var st=STEPS[si++];'
            'try{(new Function(st[0]))();}catch(e){o.push("STEP-ERR@"+si+": "+e.message);}setTimeout(next,st[1]);}\n'
            'setTimeout(next,1200);\n</script>')
    i0 = page.find('<body')
    j0 = page.find('>', i0) + 1
    out = (page[:j0] + '<script>window.__OM3_APP__=1;window.__errs=[];'
           "window.addEventListener('error',function(e){window.__errs.push((e.message||'')+' @'+(e.lineno||0));});</script>"
           + page[j0:].replace('</body>', tail + '</body>', 1))
    hp = os.path.join(TMP, 'dv_r94_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o94_' + tag)
    subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
    r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                        '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,800',
                        '--virtual-time-budget=%d' % budget, '--dump-dom',
                        'file:///' + hp.replace(os.sep, '/')],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
    dom = r.stdout or ''
    k = dom.find('id="%s"' % tag)
    return (dom[k:].split('>', 1)[1].split('</div>')[0].replace('&lt;', '<')
            .replace('&gt;', '>').replace('&amp;', '&')) if k >= 0 else ''


print('=== A. 按钮还在，但看不见 ===')
got = run_headless('R94A', [
    (r"""var b=q('[data-tv="donate"]');
o.push('A1 在DOM='+String(!!b));
o.push('A2 内联隐藏='+String(!!b && b.style.display==='none'));
o.push('A3 渲染高='+String(b?Math.round(b.getBoundingClientRect().height):'-'));
o.push('A4 在顶栏='+String(!!(b && b.closest('.tb'))));
o.push('A5 错误='+(window.__errs||[]).length);""", 400),
])
print('  · ' + got[:300])
A('A1 在DOM=true' in got, 'A1 ☕ 按钮还在 DOM 里（代码没删，只藏起来）')
A('A2 内联隐藏=true' in got and 'A3 渲染高=0' in got, 'A2 它**看不见**（display:none，渲染高 0）—— 右上角不会出现它')
A('A5 错误=0' in got, 'A0 0 运行错误')

print()
print('=== B. 一键能开（模拟"以后再做"：去掉 style 再点） ===')
got2 = run_headless('R94B', [
    (r"""var b=q('[data-tv="donate"]'); b.style.display='';
o.push('B1 显示了='+String(b.getBoundingClientRect().height>0));
b.click();""", 600),
    (r"""var t=g('otitle'), c=g('ocancel'), okb=g('ook');
o.push('B2 弹窗标题='+(t?t.textContent:''));
o.push('B3 只有谢谢='+String(!!c && c.style.display==='none')+' 文字='+(okb?okb.textContent:''));
o.push('B4 弹窗可见='+String(!!g('omask') && g('omask').className.indexOf('hide')<0));
o.push('B5 说明没放码='+(g('obody')?String(g('obody').textContent.indexOf('收款码还没放进来')>=0):'false'));
o.push('B6 错误='+(window.__errs||[]).length);""", 300),
])
print('  · ' + got2[:300])
A('B1 显示了=true' in got2, 'B1 去掉 display:none 后按钮就出现（**一行就是开关**）')
A('B2 弹窗标题=请我喝杯咖啡' in got2 and 'B4 弹窗可见=true' in got2, 'B2 点它照常弹出"请我喝杯咖啡"弹窗')
A('B3 只有谢谢=true' in got2, 'B3 弹窗只有一个"谢谢"按钮（取消已隐藏）')
A('B5 说明没放码=true' in got2, 'B4 还没嵌图时如实说明（"收款码还没放进来"，不假装有码）')

print()
print('=== C. 静态 ===')
A("var OM3_DONATE_IMG = '';" in page, 'C1 收款码那一行留着（以后 `python scripts/set_donate.py 图.png` 就能填）')
A(os.path.exists(os.path.join(ROOT, 'scripts', 'set_donate.py')), 'C2 set_donate.py 留着（以后内嵌收款码用）')
ids_p = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', page))
ids_o = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', old))
A(ids_p == ids_o, 'C3 id 集合没变')
tv_p = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
tv_o = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
A(tv_p == tv_o, 'C4 data-tv 集合没变（本轮没有新增/删除）')
A('r94：' in page and 'STEPS_MARK' not in page, 'C5 `r94：` 标记在、占位符没漏')
A(java == oldj, 'C6 Java 一行都没改')

print()
print('第 94 轮探针：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
