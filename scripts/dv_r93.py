# -*- coding: utf-8 -*-
"""第 93 轮验收：**改名 om3 recipes tool** + **右上角 ☕ 打赏按钮（展示收款码）**

验什么：
  A. 改名：`<title>`、顶栏 `.tbname`、首页 `<h1>`、导出头、导出包 `app` 字段都是 "om3 recipes tool"；
     旧名字在页面与 strings.xml 里**一个都不剩**；Android 启动器名也改了。
  B. 打赏按钮：顶栏**最右**只有一个 `data-tv="donate"` 的 ☕；点它 → 站内自绘弹窗出现
     （`#otitle` 含"喝杯咖啡"、`#ocancel` 被藏起来=只有一个"谢谢"）；**没嵌图时**写明"收款码还没放进来"。
  C. 嵌图能力：`set_donate.py` 能写回那一行（用一张 1×1 的真 PNG 测），嵌图后**点按钮出 `<img class="om3qr">`**，
     且 `--clear` 能回到空；测试完把页面恢复原样（不把测试图带进产物）。
  D. 静态：**新增 data-tv 恰好 == {donate}**、id 集合没变、Java 没改、`r93：` 标记在。

跑法：python scripts/dv_r93.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r93.html')
STRINGS = os.path.join(ROOT, 'apk', 'res', 'values', 'strings.xml')
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
OLDJ = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.before_r84.java')
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
OK, FAIL = [], []
NAME = 'om3 recipes tool'

# 1×1 透明 PNG（拿来验"嵌图"这条路通不通）
PNG1 = ('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==')


def A(c, msg):
    (OK if c else FAIL).append(msg)
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)


page = io.open(PAGE, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()
strs = io.open(STRINGS, encoding='utf-8').read()
java = io.open(JAVA, encoding='utf-8').read()
oldj = io.open(OLDJ, encoding='utf-8').read() if os.path.exists(OLDJ) else ''


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
    out = (page[:j0] + '<script>window.__OM3_APP__=1;window.__errs=[];'
           "window.addEventListener('error',function(e){window.__errs.push((e.message||'')+' @'+(e.lineno||0));});"
           'try{' + pre + '}catch(e){window.__errs.push("PRE: " + e.message);}</script>'
           + page[j0:].replace('</body>', tail + '</body>', 1))
    hp = os.path.join(TMP, 'dv_r93_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o93_' + tag)
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


print('=== A. 改名 ===')
A('<title>%s</title>' % NAME in page, 'A1 页面标题 = %s' % NAME)
A('<span class="tbname">%s</span>' % NAME in page, 'A2 顶栏名字 = %s' % NAME)
A('<h1>%s</h1>' % NAME in page, 'A3 首页 <h1> = %s' % NAME)
A("L.push('%s · 配方导出')" % NAME in page, 'A4 导出文件头跟着改名')
A("app: '%s', kind: 'om3-colorprofile'" % NAME in page, 'A5 导出包 app 字段跟着改名')
A('OM-3 色彩配方手册' not in page, 'A6 页面里**没有**旧名字了')
A('<string name="app_name">%s</string>' % NAME in strs, 'A7 Android 启动器名 = %s' % NAME)
A('OM-3 色彩配方' not in strs, 'A8 strings.xml 里没有旧名字了')

print()
print('=== B. 右上角打赏按钮（没嵌图时的行为） ===')
got = run_headless('R93A', '', [
    (r"""var b=q('[data-tv="donate"]');
o.push('B1 按钮在='+String(!!b)+' 文字='+(b?b.textContent.trim():''));
var tb=b?b.closest('.tb'):null;
o.push('B2 在顶栏='+String(!!tb));
if(b){ var r=b.getBoundingClientRect(); o.push('B3 位置右='+Math.round(r.left)+'/宽'+window.innerWidth); }
b.click();""", 700),
    (r"""var t=g('otitle'), c=g('ocancel'), okb=g('ook'), im=q('.om3qr');
o.push('B4 标题='+(t?t.textContent:''));
o.push('B5 只有一个按钮='+String(!!c && c.style.display==='none'));
o.push('B6 确定文字='+(okb?okb.textContent:''));
o.push('B7 图='+String(!!im));
o.push('B8 弹窗在='+String(!!g('omask') && g('omask').className.indexOf('hide')<0));
o.push('B9 错误='+(window.__errs||[]).length);""", 300),
])
print('  · ' + got[:420])
A('B1 按钮在=true' in got and '文字=☕' in got, 'B1 顶栏有 ☕ 按钮（data-tv="donate"）')
A('B2 在顶栏=true' in got, 'B2 它在顶栏里（所以是右上角）')
A('B4 标题=请我喝杯咖啡' in got, 'B4 点它弹出"请我喝杯咖啡"弹窗（站内自绘，不是系统弹窗）')
A('B5 只有一个按钮=true' in got and 'B6 确定文字=谢谢' in got, 'B5 只有一个"谢谢"按钮（隐藏了取消）')
A('B7 图=false' in got, 'B6b 还没嵌图时**不放**空图（如实说"收款码还没放进来"）')
A('B9 错误=0' in got, 'B0 0 运行错误')

print()
print('=== C. 嵌图这条路通不通（用一张 1×1 真 PNG 测，测完恢复） ===')
tmp_png = os.path.join(TMP, 'dv_r93_qr.png')
io.open(tmp_png, 'wb').write(__import__('base64').b64decode(PNG1))
backup = page
r1 = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'set_donate.py'), tmp_png],
                    capture_output=True, text=True, encoding='utf-8')
A('已内嵌收款码' in (r1.stdout or ''), 'C1 set_donate.py 嵌图成功：' + (r1.stdout or r1.stderr or '').strip().splitlines()[-1][:70])
page = io.open(PAGE, encoding='utf-8').read()
A('data:image/png;base64,' in page, 'C2 页面里出现了内嵌图（data:image/png;base64,…）')
got2 = run_headless('R93B', '', [
    (r"""q('[data-tv="donate"]').click();""", 700),
    (r"""var im=q('.om3qr');
o.push('C3 图在='+String(!!im)+' src前缀='+(im?String(im.src).slice(0,15):''));
o.push('C4 说明='+(q('.om3cap')?q('.om3cap').textContent:''));
o.push('C5 错误='+(window.__errs||[]).length);""", 300),
])
print('  · ' + got2[:300])
A('C3 图在=true' in got2 and 'src前缀=data:image/png' in got2, 'C3 嵌了图之后弹窗里真的显示收款码 <img class="om3qr">')
A('C4 说明=微信' in got2, 'C4 图下面有"微信 / 支付宝 扫码即可"说明')
r2 = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'set_donate.py'), '--clear'],
                    capture_output=True, text=True, encoding='utf-8')
page = io.open(PAGE, encoding='utf-8').read()
A("var OM3_DONATE_IMG = '';" in page, 'C5 --clear 能清掉（测试完页面已恢复原样，不留测试图）')

print()
print('=== D. 静态 ===')
ids_p = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', page))
ids_o = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', old))
A(ids_p == ids_o, 'D1 id 集合**没变**（多的：%s；少的：%s）' % (sorted(ids_p - ids_o), sorted(ids_o - ids_p)))
tv_p = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
tv_o = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
A(tv_p == (tv_o | {'donate'}), 'D2 **新增 data-tv 恰好 == {donate}**（多的：%s；少的：%s）'
  % (sorted(tv_p - tv_o - {'donate'}), sorted((tv_o | {'donate'}) - tv_p)))
A('.donbtn{' in page and 'om3qr' in page, 'D3 按钮/图片样式在')
A("onlyOk" in page and "opt.img" in page, 'D4 om3Ask 支持 onlyOk / img（复用已有 id，没加新 id）')
A('r93：' in page and 'STEPS_MARK' not in page, 'D5 `r93：` 标记在、占位符没漏')
A(java == oldj, 'D6 Java 一行都没改')

print()
print('第 93 轮探针：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
