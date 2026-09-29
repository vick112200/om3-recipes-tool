# -*- coding: utf-8 -*-
"""第 97 轮验收：把「扫码连接」收起来（+ 顺手修两个"可能让它扫不出"的点）

对应 SPEC-round97.md §3：
  A. 入口：`#camGateScan` / `#camScan` / `#camScanHelp` **看不见**，但节点都在（style 里就一行 display:none）
     → **一键能开**：把 style 去掉就可见、点 `#camScan` 真的会启动扫码（日志里有"扫码：…"那套话）。
  B. 文案：页面上**可见文本**里不再有"点扫码连接/点扫二维码"这种指向看不见按钮的祈使句；
     首屏改口成「手动填 SSID / 密码」；扫码卡的输出区也改口。
  C. 代码没删：jsQR / `__om3startScan` / `#scanMask` / `#scanStat` / 测试页 ⑨ 自检都还在。
  D. Java：`setMediaPlaybackRequiresUserGesture(false)` 在，且 `javac --release 8` 能编过
     （第 95 轮那段 shouldOverrideUrlLoading 不许被动）；`play()` 失败不再静默。
  E. 集合：新增 id = 0、新增 data-tv = 0；0 运行错误。

跑法：python scripts/dv_r97.py
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
OLD = os.path.join(ROOT, 'app', 'base.before_r97.html')
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
JDK = r'C:\Program Files\Java\jdk-20\bin\javac.exe'
AJAR = r'C:\Users\82302\AppData\Local\Temp\sdk\android-34\android.jar'
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
OK, FAIL = [], []


def A(c, msg):
    (OK if c else FAIL).append(msg)
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)


page = io.open(PAGE, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()
java = io.open(JAVA, encoding='utf-8').read()


def run_headless(tag, pre, steps, budget=40000):
    tail = ('<script>\nvar o=[],STEPS=' + json.dumps([[s, d] for s, d in steps], ensure_ascii=False) + ',si=0;\n'
            'function g(i){return document.getElementById(i);}\n'
            'function q(s2){return document.querySelector(s2);}\n'
            'function vis(id){var e=g(id); if(!e) return "没有"; return (e.getBoundingClientRect().height>0)?"显示":"隐藏";}\n'
            'function lg(){try{return window.__om3logText?window.__om3logText():(g("camLog")?g("camLog").textContent:"");}catch(e){return "";}}\n'
            'function finish(){var d=document.createElement("div");d.id=\'' + tag + '\';'
            'd.textContent=o.join(" ;; ");document.body.appendChild(d);}\n'
            'function next(){if(si>=STEPS.length){finish();return;}var st=STEPS[si++];'
            'try{(new Function(st[0]))();}catch(e){o.push("STEP-ERR@"+si+": "+e.message);}setTimeout(next,st[1]);}\n'
            'setTimeout(next,1400);\n</script>')
    i0 = page.find('<body')
    j0 = page.find('>', i0) + 1
    out = (page[:j0] + '<script>window.__errs=[];'
           "window.addEventListener('error',function(e){window.__errs.push((e.message||''));});"
           'try{' + pre + '}catch(e){window.__errs.push("PRE " + e.message);}</script>'
           + page[j0:].replace('</body>', tail + '</body>', 1))
    hp = os.path.join(TMP, 'dv_r97_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o97_' + tag)
    subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
    r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                        '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                        '--user-data-dir=' + ud, '--window-size=448,980',
                        '--virtual-time-budget=%d' % budget, '--dump-dom',
                        'file:///' + hp.replace(os.sep, '/')],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
    dom = r.stdout or ''
    k = dom.find('id="%s"' % tag)
    return (dom[k:].split('>', 1)[1].split('</div>')[0].replace('&lt;', '<')
            .replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"')) if k >= 0 else ''


print('=== A/B/C. 入口收起来 + 一键能开 + 文案（无头实测，App 模式）===')
got = run_headless('R97A', 'window.__OM3_APP__=1;\n', [
    ("g('tabCam').click();", 800),
    (r"""o.push('A1 camGateScan='+vis('camGateScan')+' camScan='+vis('camScan')+' camScanHelp='+vis('camScanHelp')+' camGateConn='+vis('camGateConn'));
o.push('A2 style=' + ['camGateScan','camScan','camScanHelp'].map(function(id){
  var e=g(id); return (e && /display\s*:\s*none/.test(e.getAttribute('style')||'')) ? 'ok' : '没有'; }).join('/'));
var bad=[], all=document.querySelectorAll('#paneD *');
for(var i=0;i<all.length;i++){
  var e=all[i];
  if(e.offsetHeight===0 || e.offsetWidth===0) continue;
  var t=(e.textContent||'');
  if(/点「扫码连接」|点下面「扫码连接」|点扫二维码|点上面①「扫二维码」/.test(t)) bad.push(e.tagName+':'+t.replace(/\s+/g,' ').slice(0,26));
}
o.push('B1 可见文本里的扫码祈使句='+(bad.length?(bad.length+' 处：'+bad.slice(0,2).join('|')):'无'));
var gate=g('camGateOff')?g('camGateOff').textContent:'';
o.push('B2 首屏含手动填='+String(gate.indexOf('手动填 SSID / 密码')>=0));
o.push('B3 camScanOut='+JSON.stringify((g('camScanOut')?g('camScanOut').textContent:'').slice(0,64)));
o.push('B3b summary='+JSON.stringify((q('#camV1Fold summary')||{}).textContent||''));
o.push('C1 jsQR='+typeof window.jsQR+' 驱动='+typeof window.__om3startScan+' 浮层='+String(!!g('scanMask'))+' 诊断行='+String(!!g('scanStat'))+' 测试页自检='+String(!!q('[data-tv="uv-qr"]')));
o.push('C2 统计函数='+typeof window.__om3scanDiag);
/* 一键能开：把 3 处 style 去掉 → 应该立刻可见（这就是"想开就删 style"的开关） */
['camGateScan','camScan','camScanHelp'].forEach(function(id){ g(id).style.display=''; });
o.push('A3 去掉style后='+vis('camGateScan')+'/'+vis('camScan')+'/'+vis('camScanHelp'));
g('camScan').click();""", 900),
    (r"""var t=lg();
o.push('A4 扫码被启动='+String(/扫码：(正在打开摄像头|等待相机权限|扫码组件没加载成功|这个环境不给用摄像头)/.test(t)));
o.push('A4b 浮层开了='+String(!!g('scanMask') && !g('scanMask').classList.contains('hide'))+' 日志尾='+JSON.stringify(t.slice(-60)));
o.push('A5 错误='+(window.__errs||[]).length+' om3errs='+(window.__om3errs||0));""", 300),
])
print('  · ' + got[:1300])
A('A1 camGateScan=隐藏 camScan=隐藏 camScanHelp=隐藏 camGateConn=显示' in got,
  'A1 三个扫码入口**都看不见**了（「连接相机」照旧在）')
A('A2 style=ok/ok/ok' in got, 'A2 三个都是 style[display:none]（class/节点没动，所以是"一行开关"）')
A('A3 去掉style后=显示/显示/显示' in got, 'A3 **一键能开**：把 style 去掉立刻可见')
A('A4 扫码被启动=true' in got and 'A4b 浮层开了=true' in got,
  'A3b 打开后点「扫二维码」**真的启动扫码**（日志有"扫码：…" 且浮层打开）')
A('B1 可见文本里的扫码祈使句=无' in got, 'B1 页面上可见的地方**没有**"点扫码连接/点扫二维码"这种指向看不见按钮的话')
A('B2 首屏含手动填=true' in got, 'B2 首屏改口成「手动填 SSID / 密码」')
A('B3 camScanOut="扫码这版先收起来了' in got and '手动填 SSID / 密码' in got,
  'B3 扫码卡的输出区也改口（说清为什么收起来 + 指到手动填）')
_b3 = re.search(r'B3b summary="([^"]*)"', got)
A(bool(_b3) and '扫码' not in _b3.group(1), 'B3b 折叠标题不再写「扫码」（%s）' % (_b3.group(1) if _b3 else '?'))
A('C1 jsQR=function' in got and '驱动=function' in got and '浮层=true' in got and '诊断行=true' in got
  and '测试页自检=true' in got and 'C2 统计函数=function' in got,
  'C1 解码器 / 驱动入口 / 浮层 / 诊断行 / 测试页 ⑨ 自检 **一条没删**（只是入口藏了）')
A('A5 错误=0 om3errs=0' in got, 'A5 全程 0 运行错误')

print()
print('=== D2. play() 失败不再静默（无头：喂一个空 MediaStream 让它播不出来）===')
got2 = run_headless('R97B', '''window.__OM3_APP__=1;
try{ window.__fakeStream = new MediaStream(); }catch(e){ window.__fakeErr = e.message; }
''', [
    (r"""g('tabCam').click();""", 600),
    (r"""o.push('D0 空流可用='+String(!!window.__fakeStream)+' 异常='+(window.__fakeErr||'无'));
try{ navigator.mediaDevices.getUserMedia = function(){ return Promise.resolve(window.__fakeStream); }; }catch(e){}
g('camScan').click();""", 1200),
    (r"""var t=lg();
o.push('D2 日志含播不出来='+String(t.indexOf('画面播不出来')>=0));
o.push('D2b 浮层里写了='+String((g('scanOut')?g('scanOut').textContent:'').indexOf('画面播不出来')>=0));
o.push('D2c 错误='+(window.__errs||[]).length);""", 300),
], budget=25000)
print('  · ' + got2[:500])
A('D0 空流可用=true' in got2, 'D2a 能造出空 MediaStream（前置；不行就看下面 D2b）')
if 'D2 日志含播不出来=true' in got2:
    A('D2 日志含播不出来=true' in got2 and 'D2b 浮层里写了=true' in got2,
      'D2 `play()` 播不出来时**写日志 + 浮层提示**（以前是 catch(function(){}) 什么都不留）')
else:
    A('catch(function(e2){' in page and "log('[扫码] 画面播不出来" in page and 'scanSay(\'摄像头起来了但画面播不出来' in page,
      'D2（无头里空流没触发 play 的 reject）→ 改按**静态**验：catch 里确实写了日志 + 浮层提示')
A('D2c 错误=0' in got2, 'D2d 这一路 0 运行错误')

print()
print('=== D1/E. 静态：Java 那行 + 集合 + 编译 ===')
A(java.count('setMediaPlaybackRequiresUserGesture(false);') == 1,
  'D1 Java：setMediaPlaybackRequiresUserGesture(false) 在（摄像头流不再受"必须有用户手势"限制）')
A(java.count('shouldOverrideUrlLoading') == 1 and '"om3.local".equals(host)' in java,
  'D1b 第 95 轮那段外链处理没被动')
jav = os.path.join(TMP, 'dv_r97_java')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', jav], capture_output=True)
os.makedirs(jav, exist_ok=True)
rc = subprocess.run([JDK, '--release', '8', '-encoding', 'UTF-8', '-cp', AJAR, '-d', jav, JAVA],
                    capture_output=True, text=True, encoding='utf-8', errors='ignore')
A(rc.returncode == 0, 'D1c MainActivity 能编过（javac --release 8）'
  + ('' if rc.returncode == 0 else '：' + (rc.stderr or '')[-200:]))
A('r97：' in page, 'E0 `r97：` 标记在（生成脚本幂等判据）')
ids_p = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', page))
ids_o = set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', old))
A(ids_p == ids_o, 'E1 新增 id = 0（多的：%s；少的：%s）' % (sorted(ids_p - ids_o), sorted(ids_o - ids_p)))
tv_p = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', page))
tv_o = set(re.findall(r'<[^<>\n]*\bdata-tv="([^"]+)"', old))
A(tv_p == tv_o, 'E2 新增 data-tv = 0（多的：%s；少的：%s）' % (sorted(tv_p - tv_o), sorted(tv_o - tv_p)))
A(page.count('style="display:none"') >= 3 and "id=\"camGateScan\" style=\"display:none\"" in page
  and "id=\"camScan\" class=\"camprimary\" style=\"display:none\"" in page
  and "id=\"camScanHelp\" style=\"display:none\"" in page,
  'E3 开关就是这 3 处 style（写进注释了，删掉即可恢复）')

print()
print('第 97 轮探针：%d/%d 通过%s' % (len(OK), len(OK) + len(FAIL), '' if not FAIL else '  ← 有 %d 条没过' % len(FAIL)))
sys.exit(1 if FAIL else 0)
