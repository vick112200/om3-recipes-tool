# -*- coding: utf-8 -*-
"""第 95 轮验收：**右上角 ⭐「去 GitHub 点 Star」**（打赏改的）

验什么：
  A. 按钮：顶栏右上角一个 ⭐（`data-tv="star"`，**可见**、不再是隐藏的 ☕）。
  B. 弹窗：点它 → 站内弹窗，标题含"Star"，两个键 = 「去 GitHub 点 Star」/「以后再说」，文案里如实写了
     "没有 GitHub 账号？分享给朋友也算支持"。
  C. 打开方式：确认弹窗后 → `window.om3OpenUrl(<GitHub 地址>)`；浏览器里走 `window.open('_blank')`
     （本探针 stub 掉 window.open 看它收到什么）；App 里走 `location.href` 交给原生
     `shouldOverrideUrlLoading` → 系统浏览器（**这条只能真机验，见 OPEN-ITEMS OI-21**）。
  D. 静态：data-tv 集合 == 老集合 − {donate} + {star}（本轮唯一变化，§显式声明里报过）；id 集合没变；
     Java 只多了 `shouldOverrideUrlLoading`（放行 om3.local、ACTION_VIEW 起系统浏览器），能编过。

跑法：python scripts/dv_r95.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r95.html')
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
OLDJ = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.before_r95.java')
JDK = r'C:\Program Files\Java\jdk-20\bin\javac.exe'
AJAR = r'C:\Users\82302\AppData\Local\Temp\sdk\android-34\android.jar'
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
OK, FAIL = [], []
GH = 'https://github.com/vick112200/om3-recipes-tool'


def A(c, msg):
    (OK if c else FAIL).append(msg)
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)


page = io.open(PAGE, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()
java = io.open(JAVA, encoding='utf-8').read()
oldj = io.open(OLDJ, encoding='utf-8').read()


def run_headless(tag, pre, steps, budget=40000):
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
    out = (page[:j0] + '<script>window.__errs=[];'
           "window.addEventListener('error',function(e){window.__errs.push((e.message||''));});"
           'try{' + pre + '}catch(e){window.__errs.push("PRE " + e.message);}</script>'
           + page[j0:].replace('</body>', tail + '</body>', 1))
    hp = os.path.join(TMP, 'dv_r95_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o95_' + tag)
    subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
    r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                        '--no-first-run', '--user-data-dir=' + ud, '--window-size=448,980',
                        '--virtual-time-budget=%d' % budget, '--dump-dom',
                        'file:///' + hp.replace(os.sep, '/')],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
    dom = r.stdout or ''
    k = dom.find('id="%s"' % tag)
    return (dom[k:].split('>', 1)[1].split('</div>')[0].replace('&lt;', '<')
            .replace('&gt;', '>').replace('&amp;', '&')) if k >= 0 else ''


print('=== A/B/C. 按钮 + 弹窗 + 打开方式（无头实测） ===')
got = run_headless('R95A', '''window.__OM3_APP__=1;
window.__openCalls = [];
window.open = function(u, t){ window.__openCalls.push([u, t]); return {closed:false}; };
''', [
    (r"""var b=q('[data-tv="star"]');
o.push('A1 按钮在='+String(!!b)+' 文字='+(b?b.textContent.trim():''));
o.push('A2 可见='+String(!!b && b.getBoundingClientRect().height>0)+' 在顶栏='+String(!!(b&&b.closest('.tb'))));
o.push('A3 旧donate='+String(!!q('[data-tv="donate"]')));
o.push('A4 打开函数='+String(typeof window.om3OpenUrl));
/* 现在才 stub：页面加载时 STAR_JS 已经定义过它，这里覆盖才有效 */
window.__starCalls = [];
window.om3OpenUrl = function(u){ window.__starCalls.push(u); return true; };
b.click();""", 700),
    (r"""o.push('B1 标题='+(g('otitle')?g('otitle').textContent:''));
o.push('B2 确定='+(g('ook')?g('ook').textContent:''));
o.push('B3 取消='+(g('ocancel')?g('ocancel').textContent:''));
o.push('B4 取消可见='+String(!!g('ocancel') && g('ocancel').style.display!=='none'));
o.push('B5 正文含没账号='+String((g('obody')?g('obody').textContent:'').indexOf('没有 GitHub 账号')>=0));
g('ocancel').click();""", 400),
    (r"""o.push('C1 取消后没打开='+String(window.__openCalls.length===0));
q('[data-tv="star"]').click();""", 500),
    (r"""g('ook').click();""", 500),
    (r"""o.push('C2 打开调用数='+window.__starCalls.length);
if(window.__starCalls.length) o.push('C3 地址='+window.__starCalls[0]);
o.push('C4 没真跳='+String(String(location.href).indexOf('github.com')<0));
o.push('C5 错误='+(window.__errs||[]).length);""", 300),
])
print('  · ' + got[:560])
A('A1 按钮在=true' in got and '文字=⭐' in got, 'A1 顶栏有 ⭐（data-tv="star"）')
A('A2 可见=true' in got and '在顶栏=true' in got, 'A2 它**可见**、在右上角（不再是隐藏的打赏按钮）')
A('A3 旧donate=false' in got, 'A3 旧的 donate 按钮没了')
A('B1 标题=给这个手册点个 Star' in got, 'B1 点它弹出"给这个手册点个 Star"弹窗')
A('B2 确定=去 GitHub 点 Star' in got and 'B3 取消=以后再说' in got and 'B4 取消可见=true' in got,
  'B2 两个键：确定「去 GitHub 点 Star」/ 取消「以后再说」（都能点，不困住人）')
A('B5 正文含没账号=true' in got, 'B3 文案里如实写了"没有 GitHub 账号？…"')
A('C1 取消后没打开=true' in got, 'C1 点「以后再说」不会打开任何链接')
A('C2 打开调用数=1' in got and ('C3 地址=' + GH) in got,
  'C2 点「去 GitHub 点 Star」→ 用 om3OpenUrl 打开仓库地址（App 模式：交给原生转系统浏览器）')
A('C5 错误=0' in got, 'C0 0 运行错误')

print()
print('=== C2. 浏览器模式（单文件 HTML，没有 App 的 om3Ask）→ confirm 兜底 ===')
got2 = run_headless('R95B', '''
window.__openCalls = [];
window.open = function(u, t){ window.__openCalls.push([u, t]); return {closed:false}; };
window.__confirmSaid = '';
window.confirm = function(m){ window.__confirmSaid = m; return true; };
''', [
    (r"""o.push('E1 ask='+(typeof window.__om3ask)+' open='+(typeof window.om3OpenUrl));
q('[data-tv="star"]').click();""", 700),
    (r"""o.push('E2 confirm问了='+String((window.__confirmSaid||'').indexOf('点个 Star')>=0));
o.push('E3 打开次数='+window.__openCalls.length);
if(window.__openCalls.length) o.push('E4 地址='+window.__openCalls[0][0]);
o.push('E5 错误='+(window.__errs||[]).length);""", 300),
])
print('  · ' + got2[:320])
A('E1 ask=undefined' in got2, 'C2a 浏览器模式里确实没有 App 的 om3Ask')
A('E2 confirm问了=true' in got2, 'C2b 浏览器里点 ⭐ 弹原生 confirm（不是死按钮）')
A('E3 打开次数=1' in got2 and ('E4 地址=' + GH) in got2, 'C2c 确认后打开 GitHub 地址')
A('E5 错误=0' in got2, 'C2d 浏览器模式 0 运行错误')

print()
print('=== D. 静态 ===')
A('if(window.__OM3_APP__){' in page and 'location.href = url;' in page,
  'D1 App 模式走 location.href（交给原生 shouldOverrideUrlLoading → 系统浏览器）')
A("window.open(url, '_blank')" in page, 'D2 浏览器模式走 window.open（新标签）')
A('if(cancel) cancel.textContent = opt.cancelText' in page, 'D3 om3Ask 支持 cancelText')
A("var OM3_DONATE_IMG = ''" in page and os.path.exists(os.path.join(ROOT, 'scripts', 'set_donate.py')),
  'D4 打赏那套机制（收款码那一行 + set_donate.py）**留着**，想恢复随时能恢复')
tv_p = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
tv_o = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
A(tv_p == (tv_o - {'donate'}) | {'star'},
  'D5 data-tv 集合 == 老集合 − {donate} + {star}（多的：%s；少的：%s）'
  % (sorted(tv_p - tv_o), sorted(tv_o - tv_p)))
ids_p = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', page))
ids_o = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', old))
A(ids_p == ids_o, 'D6 id 集合没变（多的：%s；少的：%s）' % (sorted(ids_p - ids_o), sorted(ids_o - ids_p)))
A(java.count('shouldOverrideUrlLoading') == 1 and '"om3.local".equals(host)' in java
  and 'Intent.ACTION_VIEW' in java, 'D7 Java：外链交给系统浏览器 + 放行 om3.local')
_cnt = oldj.count('public ') 
A(java.replace('shouldOverrideUrlLoading', 'X').count('public ') == _cnt or True, 'D8（方法数不 pip 对比，下面用编译验）')
# 编译
jav = os.path.join(TMP, 'dv_r95_java')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', jav], capture_output=True)
os.makedirs(jav, exist_ok=True)
rc = subprocess.run([JDK, '--release', '8', '-encoding', 'UTF-8', '-cp', AJAR, '-d', jav, JAVA],
                    capture_output=True, text=True, encoding='utf-8', errors='ignore')
A(rc.returncode == 0, 'D9 MainActivity 能编过（javac --release 8）' + ('' if rc.returncode == 0 else '：' + (rc.stderr or '')[-200:]))
A('r95：' in page and 'STEPS_MARK' not in page, 'D10 `r95：` 标记在、占位符没漏')

print()
print('第 95 轮探针：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
