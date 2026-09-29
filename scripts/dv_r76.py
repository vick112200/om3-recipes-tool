# -*- coding: utf-8 -*-
"""第 76 轮验收：把"到底怎么操作"变成第一屏就能看懂的编号清单（SPEC-round76.md）。

需求方 2026-09-28：「**看不懂，不知道具体操作步骤**」。
用 dv_rect 量出来的真问题（412×800）：
    原来第一屏是「蓝牙工具（高级）…」（y=66）→ 一堵说明（y=287~725）→ **「连接相机」按钮在 y=737**（第一屏几乎看不到）。
本轮：① 连接卡搬到最前面 ② 最上面给「第一次连，就这三步」编号清单 ③ 老说明收进折叠
      ④ 测试页日志卡也给「怎么发我，就这三步」。

A. **无头实测（含几何）**
   A1「连接相机」按钮**在第一屏**（y < 420）
   A2 三步清单在（"第一次连，就这三步" + ①（相机）/②（手机）/③ 三条都看得见）
   A3 蓝牙工具卡被挪到连接卡**下面**
   A4 老的长说明变成**折叠块**（默认收起，不占第一屏）
   A5 测试页日志卡有「怎么发我，就这三步」
   A6 全程 0 运行错误
B. **静态**：老 id 一个不少；**本轮不新增 id**；r76 标记在。

跑法：python scripts/dv_r76.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r76.html')
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


print('=== A. 无头实测（含几何）===')
STEPS = [
    ("g('tabCam').click();", 700),
    ("var c=g('camGateConn'), s=g('camGateScan'), b=g('bleCard'), gu=g('paneD')?document.querySelector('#paneD .camguide49'):null;"
     "o.push('A1 连接相机按钮 y=' + Math.round(c.getBoundingClientRect().top)"
     " + ' 扫码 y=' + Math.round(s.getBoundingClientRect().top)"
     " + ' 视口高=' + window.innerHeight);"
     "o.push('A3 蓝牙卡 y=' + Math.round(b.getBoundingClientRect().top)"
     " + ' 在三步说明下面=' + (b.getBoundingClientRect().top > c.getBoundingClientRect().top + c.getBoundingClientRect().height));"
     "o.push('A4 三步说明高=' + Math.round(gu.getBoundingClientRect().height)"
     " + ' 详细说明是折叠=' + !!document.querySelector('#paneD details summary')"
     # 第 98 轮踩的坑：Chrome 的 details 折叠用 content-visibility 实现，收起时里面元素的
     # rect 高度**仍然非 0** → 判"看不看得见"要用 checkVisibility()。
     " + ' 默认可见=' + ((typeof gu.checkVisibility === 'function') ? gu.checkVisibility() : (gu.getBoundingClientRect().height > 0)));"
     # 第 98 轮口径：那份"对号入座"清单被收进「怎么连」折叠（默认收起，首屏才短得下来）→
     # 先记一下"默认确实全收起"，再把折叠都打开，然后照旧判清单在不在。
     "var closedAll=true;"
     "document.querySelectorAll('#paneD details').forEach(function(d){ if(d.open) closedAll=false; });"
     "o.push('A2b 默认全收起=' + closedAll);"
     "document.querySelectorAll('#paneD details').forEach(function(d){ d.open=true; });"
     "var t=(g('camGateOff')||{}).innerText||'';"
     "o.push('A2 有对号入座清单=' + /先看相机屏幕上是什么|对号入座/.test(t)"
     " + ' 情况A=' + /情况 A：相机屏幕上有/.test(t) + ' 情况B=' + /情况 B：相机屏幕上只有 SSID/.test(t) + ' 情况C=' + /情况 C：你已经自己/.test(t)"
     " + ' 兜底提示=' + /测试页/.test(t) + ' 分享日志=' + /分享日志/.test(t));", 300),
    ("g('tabTest').click();", 700),
    ("var t2=(g('paneT')||{}).innerText||'';"
     "o.push('A5 日志卡三步=' + /怎么发我，就这三步/.test(t2) + ' ' + /①点「分享日志」/.test(t2)"
     " + ' 分享按钮在=' + !!document.querySelector('[data-tv=\"sharelog\"]'));"
     "o.push('A6 运行错误=' + (window.__errs?window.__errs.length:0));", 200),
]
tail = ('<script>\nvar o=[],STEPS=' + json.dumps([[s, d] for s, d in STEPS], ensure_ascii=False) + ',si=0;\n'
        'function g(i){return document.getElementById(i);}\n'
        'function finish(){var d=document.createElement("div");d.id=\'R76OUT\';'
        'd.textContent=o.join(" ;; ");document.body.appendChild(d);}\n'
        'function next(){if(si>=STEPS.length){finish();return;}var st=STEPS[si++];'
        'try{(new Function(st[0]))();}catch(e){o.push("STEP-ERR@"+si+": "+e.message);}setTimeout(next,st[1]);}\n'
        'setTimeout(next,1600);\n</script>')
i0 = page.find('<body')
j0 = page.find('>', i0) + 1
out = (page[:j0] + '<script>window.__OM3_APP__=1;window.__errs=[];'
       "window.addEventListener('error',function(e){window.__errs.push((e.message||'')+' @'+(e.lineno||0));});"
       '</script>' + page[j0:].replace('</body>', tail + '</body>', 1))
hp = os.path.join(TMP, 'dv_r76.html')
io.open(hp, 'w', encoding='utf-8', newline='').write(out)
ud = os.path.join(TMP, 'o76')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,800',
                    '--virtual-time-budget=40000', '--dump-dom',
                    'file:///' + hp.replace(os.sep, '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
k = dom.find('id="R76OUT"')
got = (dom[k:].split('>', 1)[1].split('</div>')[0].replace('&lt;', '<')
       .replace('&gt;', '>').replace('&amp;', '&')) if k >= 0 else ''
for seg in got.split(' ;; '):
    print('  · ' + seg)
A('STEP-ERR' not in got, 'A0 步骤没抛错')
m = re.search(r'A1 连接相机按钮 y=(\d+) 扫码 y=(\d+) 视口高=(\d+)', got)
# 口径修正（第 79 轮）：原来写死 y<420 —— 那段说明第 79 轮变长了（y 354→517）。
# 但**真正要守的是"按钮在第一个屏幕里完整可见"**（当初 y=737/视口 700 就是做不到这点），
# 所以改成断言"按钮底边 ≤ 视口高"：更贴目的，而且当年的问题照样会被抓到。
A(bool(m) and int(m.group(1)) + 41 <= int(m.group(3)),
  'A1 「连接相机」按钮在**第一屏内完整可见**（y=%s +41 ≤ 视口 %s；修前 y=737/视口 700 → 看不到）'
  % (m.group(1) if m else '?', m.group(3) if m else '?'))
A('A2b 默认全收起=true' in got and
  'A2 有对号入座清单=true 情况A=true 情况B=true 情况C=true 兜底提示=true 分享日志=true' in got,
  'A2 「怎么连」折叠**默认收起**，点开就是那份清单（先看相机屏幕上是什么 / 情况 A/B/C / 测试页兜底）'
  ' —— 第 98 轮把清单收进折叠后首屏才短得下来（口径按本轮更新：原来是"第一屏直接平铺清单"）')
m3 = re.search(r'A3 蓝牙卡 y=(\d+) 在三步说明下面=(\w+)', got)
# 口径修正（第 92 轮）：需求方「多余的该去掉去掉」→ 蓝牙工具卡**整块搬到测试页**（诊断用），
# 连接页上已经没有它了 → 比"挪到下面"更强的保证：断言它**不在**连接页、而在测试页。
_pd = page.index('<div id="paneD"'); _pt = page.index('<div id="paneT"')
A('id="bleCard"' not in page[_pd:_pt] and 'id="bleCard"' in page[_pt:],
  'A3 蓝牙工具卡**不在连接页**（已搬到测试页，诊断用）—— r92 之后这条比"挪到下面"更强')
m4 = re.search(r'A4 三步说明高=(\d+) 详细说明是折叠=(\w+) 默认可见=(\w+)', got)
A(bool(m4) and m4.group(2) == 'true' and m4.group(3) == 'false',
  'A4 老的长说明收进**默认收起**的折叠块（`checkVisibility()` 判默认看不见；修前整卡 438px）'
  ' —— 第 98 轮起「怎么连」清单也收进了折叠（口径用 checkVisibility，不再看 rect 高度）')
A('A5 日志卡三步=true true 分享按钮在=true' in got, 'A5 测试页日志卡也写了「怎么发我，就这三步」')
A('A6 运行错误=0' in got, 'A6 全程 0 运行错误')

print('=== B. 静态 ===')
A('r76：怎么操作' in page, 'B1 r76 标记在（生成脚本幂等判据）')
A('先看相机屏幕上是什么' in page or '第一次连，就这三步' in page, 'B2 清单在源码里（第 79 轮改成了「先看相机屏幕上是什么」）')
A('<summary>详细说明（第一次连 / 以后怎么连 / 不装官方 App）</summary>' in page, 'B3 老说明变成折叠块的 summary')
A(page.index('<div class="camgate" id="camGateOff">') < page.index('<div id="paneT"'),
  'B4 源码顺序也是「连接卡」在「蓝牙卡」前面')
si, so = ids(page), ids(old)
A(not (so - si), 'B5 老 id 一个都没少（少的：%s）' % (sorted(so - si) or '无'))
A(not (si - so), 'B6 本轮**没有新增 id**（多的是：%s）' % (sorted(si - so) or '无'))

print()
print('第 76 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
