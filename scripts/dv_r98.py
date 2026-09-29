# -*- coding: utf-8 -*-
"""第 98 轮验收：**连接相机页合并成一屏**（需求方 2026-09-29 从 4 个选项里选「合并成一屏（推荐）」）

对应 SPEC-round98.md §3：
  A. 一个标题、首屏短：paneD 只有一个 `h1`「连接相机」；「导入相机」不见了；
     `#camGateOff` 高度 ≤ 420px（改前 793px）；首屏可见按钮 = 连接相机 + 手动填 + 自动连接。
  B. 「怎么连」清单收进折叠（默认收起，点开可见 A/B/C）；「详细说明」与它**同级**（不嵌套）；
     `#camGateManual` 在首屏、不在任何折叠里。
  C. 去重：默认 `#camConnect` 不可见、`#camGateConn` 可见；`#camConnect` 仍在 DOM（测试页 tvSaved 还用它）。
  D. 「蓝牙唤醒」整格隐藏（节点/逻辑保留）；展开所有折叠后，paneD 的可见文本里**没有**"扫二维码"。
  E. 集合：新增 id = 0、新增 data-tv = 0；0 运行错误。

跑法：python scripts/dv_r98.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r98.html')
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
OK, FAIL = [], []


def A(c, msg):
    (OK if c else FAIL).append(msg)
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)


page = io.open(PAGE, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()

JS_A = r"""
g('tabCam').click();
setTimeout(function(){
  var o = [];
  /* ⚠️ 第 98 轮踩到的坑：新版 Chrome 用 ::details-content + content-visibility 折叠 <details>，
     收起时里面的元素 getBoundingClientRect().height **仍然非 0**（只是不渲染）→ 这种场景必须用
     checkVisibility() 判"到底看不看得见"。 */
  function cvis(e){ if(!e) return false; try{ if(typeof e.checkVisibility === 'function') return e.checkVisibility(); }catch(x){}
    var s = getComputedStyle(e); return s.display !== 'none' && e.getBoundingClientRect().height > 0; }
  function inClosedFold(e){ var n = e; while(n && n !== document.body){ if(n.tagName === 'DETAILS' && !n.open) return true; n = n.parentNode; } return false; }
  function visReal(e){ return cvis(e) && !inClosedFold(e); }
  function txt(e){ return e ? (e.textContent||'').replace(/\s+/g,' ').trim() : ''; }
  try{
    /* A1 标题 */
    var hs = document.querySelectorAll('#paneD h1');
    o.push('A1 h1数=' + hs.length + ' 文本=' + JSON.stringify(hs.length ? txt(hs[0]) : ''));
    /* A2 「导入相机」：只查**标题类**元素（正文里"配方卡上的「导入相机」"是另一个功能的按钮名，不算标题重复） */
    var pd = document.getElementById('paneD');
    var imp = 0, hh = pd.querySelectorAll('h1,h2,h3,h4,summary');
    for(var i=0;i<hh.length;i++){ if(cvis(hh[i]) && /导入相机/.test(txt(hh[i]))) imp++; }
    o.push('A2 可见标题里含「导入相机」的=' + imp);
    /* A3 首屏高度 */
    o.push('A3 camGateOff高=' + Math.round(document.getElementById('camGateOff').getBoundingClientRect().height)
         + ' wrap高=' + Math.round((document.querySelector('#paneD .wrap')||{getBoundingClientRect:function(){return {height:-1}}}).getBoundingClientRect().height));
    /* A4 首屏可见按钮 */
    var names = [], bs = document.getElementById('camGateOff').querySelectorAll('button');
    for(var k=0;k<bs.length;k++) if(visReal(bs[k])) names.push(txt(bs[k]));
    o.push('A4 首屏可见按钮=' + JSON.stringify(names));
    /* B1 手动填位置 */
    var man = document.getElementById('camGateManual'), nest = 0, up = man;
    while(up){ if(up.tagName === 'DETAILS') nest++; up = up.parentNode; }
    o.push('B1 手动填可见=' + visReal(man) + ' 祖先details数=' + nest);
    /* B2 「怎么连」折叠 */
    var g49 = document.querySelector('.camguide49');
    var chain = [], n0 = g49;
    while(n0 && n0 !== document.body && chain.length < 5){ chain.push(n0.tagName + '.' + (n0.className || '')); n0 = n0.parentNode; }
    o.push('B2a 默认可见=' + cvis(g49) + ' 默认高度=' + Math.round(g49.getBoundingClientRect().height));
    var how = null, dss = document.querySelectorAll('#paneD details');
    for(var d=0; d<dss.length; d++) if(/怎么连？/.test(txt(dss[d].querySelector('summary')))) how = dss[d];
    o.push('B2b 有「怎么连」折叠=' + !!how + ' 默认open=' + (how ? how.open : '无'));
    if(how) how.open = true;
    var t49 = txt(g49);
    o.push('B2c 展开后可见=' + cvis(g49) + ' 展开后高=' + Math.round(g49.getBoundingClientRect().height)
         + ' 含情况A=' + /情况 A：相机屏幕上有/.test(t49) + ' 含情况B=' + /情况 B：相机屏幕上只有 SSID/.test(t49)
         + ' 含情况C=' + /情况 C：你已经自己/.test(t49));
    /* B3 「详细说明」是否被套在别的 details 里 */
    var df = null;
    for(var e2=0; e2<dss.length; e2++) if(/详细说明（第一次连/.test(txt(dss[e2].querySelector('summary')))) df = dss[e2];
    var n2 = 0, up2 = df;
    while(up2){ if(up2.tagName === 'DETAILS') n2++; up2 = up2.parentNode; }
    o.push('B3b 详细说明存在=' + !!df + ' 祖先details数=' + n2);
    /* C1 去重 */
    o.push('C1 camConnect可见=' + visReal(document.getElementById('camConnect'))
         + ' camGateConn可见=' + visReal(document.getElementById('camGateConn')));
    /* D1 蓝牙唤醒 */
    o.push('D1 camLinkFold高=' + Math.round(document.getElementById('camLinkFold').getBoundingClientRect().height)
         + ' 卡在=' + !!document.getElementById('camLinkCard') + ' 口令框在=' + !!document.getElementById('blePassIn')
         + ' 结果码按钮在=' + !!document.getElementById('bleCodeBtn'));
    /* D2 展开所有折叠后还有没有"扫二维码" */
    document.querySelectorAll('#paneD details').forEach(function(x){ x.open = true; });
    var bad = [], all2 = pd.querySelectorAll('*');
    for(var z=0; z<all2.length; z++){
      var e3 = all2[z];
      if(!visReal(e3)) continue;
      var t3 = txt(e3);
      if(/扫二维码/.test(t3) && t3.length < 160) bad.push(e3.tagName + '/' + (e3.id || e3.className) + ':' + t3.slice(0, 40));
    }
    o.push('D2 残留"扫二维码"可见元素=' + bad.length + (bad.length ? (' 例如 ' + bad[0]) : ''));
    o.push('E2 错误=' + (window.__errs || []).length + ' om3errs=' + (window.__om3errs || 0));
  }catch(e){ o.push('★异常 ' + e.message); }
  var dv = document.createElement('div'); dv.id = 'R98OUT'; dv.textContent = o.join(' ;; ');
  document.body.appendChild(dv);
}, 1200);
"""

tail = ('<script>window.__errs=[];'
        "window.addEventListener('error',function(e){window.__errs.push(String(e.message));});"
        '</script><script>function g(i){return document.getElementById(i);}' + JS_A + '</script>')
k = page.find('<body')
j = page.find('>', k) + 1
out = page[:j] + '<script>window.__OM3_APP__=1;</script>' + page[j:].replace('</body>', tail + '</body>', 1)
hp = os.path.join(TMP, 'dv_r98.html')
io.open(hp, 'w', encoding='utf-8', newline='').write(out)
ud = os.path.join(TMP, 'o98')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,800',
                    '--virtual-time-budget=40000', '--dump-dom',
                    'file:///' + hp.replace(os.sep, '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="R98OUT"')
got = (dom[kk:].split('>', 1)[1].split('</div>')[0].replace('&lt;', '<')
       .replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"')) if kk >= 0 else ''
print('=== A/B/C/D 无头实测（412px 宽，App 模式）===')
for seg in got.split(' ;; '):
    print('  · ' + seg)

A('A1 h1数=1 文本="连接相机"' in got, 'A1 paneD 只有一个大标题，就是「连接相机」（改前是 h3 + 下面另一个 h1「导入相机」）')
A('A2 可见标题里含「导入相机」的=0' in got, 'A2 「导入相机」这个第二标题没了')
_m = re.search(r'A3 camGateOff高=(\d+)', got)
A(bool(_m) and int(_m.group(1)) <= 420,
  'A3 首屏块高度 ≤420px（实测 %s；改前 **793px**）—— 说明文字收进折叠后，按钮+状态条一屏看得全'
  % (_m.group(1) if _m else '?'))
A('A4 首屏可见按钮=["连接相机","手动填 SSID / 密码","开"]' in got,
  'A4 首屏可见按钮恰好是：连接相机 / 手动填 SSID / 密码 / 自动连接开关（没有重复的第二个「连接相机」）')
A('B1 手动填可见=true 祖先details数=0' in got,
  'B1 「手动填 SSID / 密码」在**首屏**、不在折叠里（扫码收起后它是第二入口）')
A('B2a 默认可见=false' in got and 'B2b 有「怎么连」折叠=true 默认open=false' in got,
  'B2 「怎么连」折叠**默认收起**（`checkVisibility()` 判：真的看不见；所以首屏才短）')
A('B2c 展开后可见=true' in got and '含情况A=true 含情况B=true 含情况C=true' in got,
  'B2b 点开就是那份对号入座清单（情况 A/B/C 都在）')
A('B3b 详细说明存在=true 祖先details数=1' in got,
  'B3 「详细说明」折叠是**同级**的（祖先 details 只有它自己 → 没有折叠套折叠）')
A('C1 camConnect可见=false camGateConn可见=true' in got,
  'C1 首屏唯一的「连接相机」是 #camGateConn；下面那个重复的 #camConnect 已隐藏')
A('D1 camLinkFold高=0' in got and '卡在=true 口令框在=true 结果码按钮在=true' in got,
  'D1 「蓝牙唤醒」整格收起（第 92 轮的口径），但节点 / id / 逻辑全在')
A('D2 残留"扫二维码"可见元素=0' in got, 'D2 展开所有折叠后，paneD 可见文本里 0 处"扫二维码"（含条件元素）')
A(re.search(r'E2 错误=0 om3errs=0', got) is not None, 'E2 全程 0 运行错误')

print()
print('=== E. 静态 ===')
A('r98：' in page, 'E0 `r98：` 标记在（生成脚本改过）')
ids_p = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', page))
ids_o = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', old))
A(ids_p == ids_o, 'E1 新增 id = 0（多的：%s；少的：%s）' % (sorted(ids_p - ids_o), sorted(ids_o - ids_p)))
tv_p = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
tv_o = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
A(tv_p == tv_o, 'E1b 新增 data-tv = 0（多的：%s；少的：%s）' % (sorted(tv_p - tv_o), sorted(tv_o - tv_p)))
A("tvBind('tvSaved'" in page and "'camConnect'" in page, 'E1c 测试页的诊断按钮 tvSaved 还在用 #camConnect（隐藏不等于删）')
A(not re.search(r'<h1>\s*导入相机', page), 'E1d 源码里也没有第二个 <h1>导入相机</h1>')
# F1（第 98 轮·全库体检顺手加的守卫）：用户硬约束「**界面上不许出现日期**」——
# 去掉 HTML 注释 / CSS 块注释 / // 行注释之后，整份页面不许再有 20xx-xx-xx。
_body = re.sub(r'<!--.*?-->', '', page, flags=re.S)
_body = re.sub(r'/\*.*?\*/', '', _body, flags=re.S)
_body = re.sub(r'//[^\n]*', '', _body)
_dates = sorted(set(re.findall(r'20\d\d-\d\d-\d\d', _body)))
A(not _dates, 'F1 非注释的页面文本里没有日期（发现：%s）' % (_dates or '无'))

print()
print('第 98 轮探针：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
