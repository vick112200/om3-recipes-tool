# -*- coding: utf-8 -*-
"""第 75 轮验收：「发我日志」在手机上真的能用（SPEC-round75.md）。

需求方问「不用 测试页（连接诊断）吗」→ 答：**要用**，日志按钮只在那儿。
但真机上"复制"（WebView 的 execCommand 不保证成功）和"下载"（<a download> 常被 WebView 忽略）都不稳，
所以本轮在测试页日志卡加**「分享日志（发微信 / 邮件）」**（走原生 shareText → 系统分享面板），
并如实写清"下载没反应就用前两种"。

A. **无头实测**（假原生桥，记录 shareText 被怎么调）
   A1 测试页日志卡里**有** `[data-tv="sharelog"]` 按钮，且**排在**「复制全部日志」前面（首选）
   A2 点它 → 会调 `Native.shareText(文件名, 日志全文, 'text/plain')`，文件名像 `OM3-导入相机-日志-*.txt`
   A3 分享出去的内容里**带着日志头**（App/权限/记住的相机…）且**没有相机密码**
   A4 没有原生分享时（桥里没有 shareText）→ 退回剪贴板/至少不报错、也不假装成功
B. **静态**：连接相机页那句提示提到「分享日志」；「下载」的提示写了"没反应就用分享/复制"；
   老 id 一个不少；**本轮不新增 id**（新按钮用 data-tv 选择器）。

跑法：python scripts/dv_r75.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r75.html')
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


SAVED = {"ssid": "OM-3", "pass": "SIM-PASS-1234", "model": "OM-3", "serial": "BJ8A0001", "at": 1759000000000}

BRIDGE_BASE = '''
window.__shared = [];
window.OM3Native = (function(){
  var API = {
    permState: function(){ return '{"camera":true,"fine":true,"nearby":true,"sdk":34}'; },
    wifiState: function(){ return JSON.stringify({ssid:'我家WiFi', on:true}); },
    wifiScanList: function(){ return '[]'; },
    cameraState: function(){ return '{"connected":false,"ssid":"","bssid":""}'; },
    shareText: function(name, text, mime){ window.__shared.push({n: String(name||''), t: String(text||''), m: String(mime||'')}); return 'ok'; },
    /* 让复制那条路也别炸（本探针只关心"分享"） */
    disconnectCamera: function(){ return 'ok'; }, forgetWifi: function(){ return 'ok'; }, dropCamera: function(){ return 'ok'; },
    openWifiSettings: function(){ return 'ok'; }, openAppSettings: function(){ return 'ok'; }, startWatch: function(){ return 'ok'; },
    camGet: function(){ return '{"status":0,"text":""}'; }
  };
  if(CASE_NOSHARE){ delete API.shareText; }
  return API;
})();
'''


def run_headless(tag, pre, steps, budget=40000):
    tail = ('<script>\nvar o=[],STEPS=' + json.dumps([[s, d] for s, d in steps], ensure_ascii=False) + ',si=0;\n'
            'function g(i){return document.getElementById(i);}\n'
            'function finish(){var d=document.createElement("div");d.id=\'' + tag + '\';'
            'd.textContent=o.join(" ;; ");document.body.appendChild(d);}\n'
            'function next(){if(si>=STEPS.length){finish();return;}var st=STEPS[si++];'
            'try{(new Function(st[0]))();}catch(e){o.push("STEP-ERR@"+si+": "+e.message);}setTimeout(next,st[1]);}\n'
            'setTimeout(next,1600);\n</script>')
    i0 = page.find('<body')
    j0 = page.find('>', i0) + 1
    out = (page[:j0] + '<script>window.__OM3_APP__=1;window.__errs=[];'
           "window.addEventListener('error',function(e){window.__errs.push((e.message||'')+' @'+(e.lineno||0));});"
           'try{' + pre + '}catch(e){}</script>' + page[j0:].replace('</body>', tail + '</body>', 1))
    hp = os.path.join(TMP, 'dv_r75_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o75_' + tag)
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


print('=== A. 无头实测：点「分享日志」会发生什么 ===')
PRE = ('window.CASE_NOSHARE = false;'
       "localStorage.setItem('om3cam', %s);" % json.dumps(json.dumps(SAVED))) + BRIDGE_BASE
got = run_headless('R75A', PRE, [
    # 先进测试页（点隐藏代理页签，等于 ☰ → 🔧 测试页）
    ("g('tabTest').click();", 800),
    ("var b=document.querySelector('[data-tv=\"sharelog\"]');"
     "o.push('A0 进测试页=' + (getComputedStyle(g('paneT')).display!=='none') + ' 分享按钮在=' + !!b);"
     "var bs=g('camCopyLog').parentNode.querySelectorAll('button');var order=[];"
     "for(var i=0;i<bs.length;i++) order.push(bs[i].id || bs[i].getAttribute('data-tv'));"
     "o.push('A1 按钮顺序=' + order.join(' > '));", 200),
    ("window.__om3log('探针写一行日志');", 200),
    ("document.querySelector('[data-tv=\"sharelog\"]').click();", 800),
    ("var s=(window.__shared||[])[0]||{};"
     "o.push('A2 shareText 被调=' + (window.__shared||[]).length + ' 次 文件名=' + (s.n||'(无)'));"
     "o.push('A2 mime=' + (s.m||'(无)'));"
     "o.push('A3 正文长度=' + ((s.t||'').length) + ' 含日志头=' + (/App：/.test(s.t||'') && /权限：/.test(s.t||''))"
     " + ' 含密码=' + /SIM-PASS-1234/.test(s.t||'') + ' 含探针那行=' + /探针写一行日志/.test(s.t||''));"
     "o.push('A4 运行错误=' + (window.__errs?window.__errs.length:0));", 200),
])
for seg in got.split(' ;; '):
    print('  · ' + seg)
A('A0 进测试页=true 分享按钮在=true' in got, 'A0 测试页里有「分享日志」按钮')
m = re.search(r'A1 按钮顺序=([^;]+)$', got.split(' ;; ')[0]) or re.search(r'A1 按钮顺序=([^;]+)', got)
order = (m.group(1).strip() if m else '')
A(order.startswith('sharelog > camCopyLog'), 'A1 「分享日志」排在「复制全部日志」**前面**（作为首选）：%s' % order)
A(re.search(r'A2 shareText 被调=1 次 文件名=OM3-导入相机-日志-[\d-]+\.txt', got) is not None,
  'A2 点它 → 真的调了原生 shareText，文件名像 "OM3-导入相机-日志-<时间>.txt"')
A('A2 mime=text/plain' in got, 'A2 mime 用的是 text/plain')
A(re.search(r'A3 正文长度=\d{2,} 含日志头=true 含密码=false 含探针那行=true', got) is not None,
  'A3 分享出去的正文带着日志头与最新日志，且**不含密码**')
A('A4 运行错误=0' in got, 'A4 全程 0 运行错误')

print('=== A4b. 没有原生分享时（桥里没有 shareText）不许假装成功 ===')
PRE2 = 'window.CASE_NOSHARE = true;' + BRIDGE_BASE
got = run_headless('R75B', PRE2, [
    ("g('tabTest').click();", 600),
    ("window.__om3log('第二份日志');", 200),
    ("document.querySelector('[data-tv=\"sharelog\"]').click();", 600),
    ("o.push('A4b shareText 调用数=' + (window.__shared||[]).length);"
     "var t=(g('camOut3')||{}).innerText||'';"
     "o.push('A4b 日志里说了什么=' + (/剪贴板/.test(t) ? '已放进剪贴板' : (/已打开系统分享/.test(t) ? '说成功（假）' : '没说话')));"
     "o.push('A4b 运行错误=' + (window.__errs?window.__errs.length:0));", 200),
])
for seg in got.split(' ;; '):
    print('  · ' + seg)
A('A4b shareText 调用数=0' in got, 'A4b 没有原生分享时不会去调 shareText（没假装）')
A('A4b 日志里说了什么=已放进剪贴板' in got, 'A4b 没有原生分享时改走剪贴板，并如实告诉用户')
A('A4b 运行错误=0' in got, 'A4b 这条路也不报错')

print('=== B. 静态 ===')
A('data-tv="sharelog"' in page, 'B1 新按钮用 data-tv 选择器')
A('测试页（连接诊断）</b> → 点<b>「分享日志」</b>' in page or '「分享日志」</b>（首选' in page,
  'B2 连接相机页折叠里的提示把「分享日志」写成首选')
A('请改用上面的「分享日志」或「复制全部日志」' in page, 'B3 「下载」的提示里如实写了"没反应就用分享/复制"')
A('r75：日志分享' in page, 'B4 r75 标记在（生成脚本幂等判据）')
si, so = ids(page), ids(old)
A(not (so - si), 'B5 老 id 一个都没少（少的：%s）' % (sorted(so - si) or '无'))
A(not (si - so), 'B6 本轮**没有新增 id**（多的是：%s）' % (sorted(si - so) or '无'))

print()
print('第 75 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
