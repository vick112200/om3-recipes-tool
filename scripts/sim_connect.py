# -*- coding: utf-8 -*-
"""连接流程"推演器"：用一个**假的原生桥**把「连接相机」整条链在无头浏览器里跑一遍，
把用户会看到的每一句话、每一步状态按顺序打出来 —— 不用真机就能先看清流程对不对。

⚠ 它只推演**页面侧**的分支/文案/顺序（Java 那半边是假的）：真机结论仍以 `TEST-camera.md` 为准。

可选的场景（--case）：
  first   第一次连（什么都没记住）→ 看它怎么引导你
  saved   已经连过一次（localStorage 里有记录）→ 应该直接连
  nocam   手机热点扫不到相机（相机 Wi-Fi 没开）→ 应该给"蓝牙唤醒/手动填"
用法：python scripts/sim_connect.py [first|saved|nocam]
"""
import io
import json
import os
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
CASE = sys.argv[1] if len(sys.argv) > 1 else 'first'

CAM_AP = {"ssid": "OM-3", "bssid": "AA:BB:CC:DD:EE:FF", "level": -42, "cam": True}
OTHER = {"ssid": "我家WiFi", "bssid": "11:22:33:44:55:66", "level": -55, "cam": False}
CAMINFO_XML = '<caminfo><Model>OM-3</Model><camera_name>OM-3</camera_name><Serial>BJ8A0001</Serial></caminfo>'

# 假桥：行为跟 MainActivity 那几个同步方法对齐（返回值格式相同）
BRIDGE = '''
  /* 假的原生桥用到的两串"扫到的热点" */
  var CAM_LIST = [{ssid:'OM-3',bssid:'AA:BB:CC:DD:EE:FF',level:-42,cam:true},
                  {ssid:'我家WiFi',bssid:'11:22:33:44:55:66',level:-55,cam:false}];
  var OTHER_LIST = [{ssid:'我家WiFi',bssid:'11:22:33:44:55:66',level:-55,cam:false}];
window.OM3Native = (function(){
  var CASE = %(case)s;
  window.__calls = [];
  function rec(n, a){ window.__calls.push(n + '(' + Array.prototype.slice.call(a).join(',') + ')'); }
  var connected = false, lastSsid = '';
  var API = {
    permState: function(){ rec('permState', arguments); return '{"camera":true,"fine":true,"nearby":true,"sdk":34}'; },
    wifiState: function(){ rec('wifiState', arguments); return JSON.stringify({ssid: connected ? 'OM-3' : '我家WiFi', on: true}); },
    wifiScanList: function(){
      rec('wifiScanList', arguments);
      return JSON.stringify((CASE === 'nocam') ? OTHER_LIST : CAM_LIST);
    },
    connectCamera:  function(s, p){ rec('connectCamera', arguments); lastSsid = s; connected = true; return 'asking'; },
    connectCamera2: function(s, p, b){ rec('connectCamera2', arguments); lastSsid = s; connected = true; return 'asking@bssid'; },
    cameraState: function(){ rec('cameraState', arguments);
      return JSON.stringify({connected: connected, ssid: connected ? (lastSsid || 'OM-3') : '', bssid: connected ? 'AA:BB:CC:DD:EE:FF' : ''}); },
    disconnectCamera: function(){ rec('disconnectCamera', arguments); connected = false; return 'ok'; },
    forgetWifi: function(){ rec('forgetWifi', arguments); return 'ok'; },
    dropCamera: function(){ rec('dropCamera', arguments); return 'ok'; },
    ensureCamera: function(){ rec('ensureCamera', arguments); return CASE === 'nocam' ? 'no_cam_ap' : 'asking'; },
    startWatch: function(){ rec('startWatch', arguments); return 'ok'; },
    camGet: function(u){ rec('camGet', arguments); return '{"status":200,"text":' + JSON.stringify(%(cam)s) + '}'; },
    camGetAsync: function(u){ rec('camGetAsync', arguments); return 'sim-async-1'; },
    camPost: function(u, b){ rec('camPost', arguments); return '{"status":200,"text":""}'; },
    camPostAsync: function(u, b){ rec('camPostAsync', arguments); return 'sim-async-2'; },
    bleScanStop: function(){ rec('bleScanStop', arguments); return 'ok'; },
    bleDisconnect: function(){ rec('bleDisconnect', arguments); return 'ok'; },
    blePermDetail: function(){ rec('blePermDetail', arguments); return '{}'; },
    /* 蓝牙那半边的桩：让"进页面自动跑蓝牙链"这条真路也能走（不看结果，只看页面会怎么说） */
    bleScan: function(){ rec('bleScan', arguments); return 'ok'; },
    bleScanCam: function(){ rec('bleScanCam', arguments); return 'ok'; },
    bleConnect: function(m){ rec('bleConnect', arguments); return 'ok'; },
    bleCmd: function(){ rec('bleCmd', arguments); return 'ok'; },
    bleWrite: function(){ rec('bleWrite', arguments); return 'ok'; },
    bleAskPerm: function(){ rec('bleAskPerm', arguments); return 'ok'; },
    openWifiSettings: function(){ rec('openWifiSettings', arguments); return 'ok'; },
    openAppSettings: function(){ rec('openAppSettings', arguments); return 'ok'; },
    joinWifi: function(s, p, b){ rec('joinWifi', arguments); connected = true; return 'ok'; },
    shareText: function(t){ rec('shareText', arguments); return 'ok'; }
  };
  /* noble：模拟"这个版本没有蓝牙接口"（老包 / 蓝牙被系统关掉）—— 用来验证"别白等 10 秒" */
  if(CASE === 'noble'){
    ['bleScan','bleScanCam','bleConnect','bleCmd','bleWrite','bleScanStop','bleDisconnect','blePermDetail','bleAskPerm']
      .forEach(function(k){ try{ delete API[k]; }catch(e){} });
  }
  return API;
})();
''' % {'case': json.dumps(CASE), 'cam': json.dumps(CAMINFO_XML)}

SAVED = {"ssid": "OM-3", "pass": "SIM-PASS-1234", "model": "OM-3", "serial": "BJ8A0001", "at": 1759000000000}

TL = []
STEPS = [
    ("window.__tl=[];var _ol=window.__om3log;window.__om3log=function(m,c){try{window.__tl.push('+'+(Date.now()-window.__t0)+'ms '+(c||'')+' '+m);}catch(e){}return _ol.apply(null,arguments);};window.__t0=Date.now();o.push('① 进页面时（自动跑蓝牙链）—— 页面主提示：' + txt('camGateOut'));", 3000),
    ("o.push('② 点「连接相机」');g('camGateConn').click();", 12000),
    ("o.push('③ 点完主提示：' + txt('camGateOut'));"
     "o.push('③ cam-on=' + document.body.classList.contains('cam-on') + ' ; 步骤=' + step());"
     "o.push('③ 可见的按钮（没藏起来的）：' + ['camGateScan','camGateConn','camGateDirect','camGateManual','camScan']"
     ".filter(function(id){var e=g(id);return e && e.checkVisibility && e.checkVisibility();}).join(','));", 500),
    ("o.push('④ 手填面板开着吗=' + (g('camManualCard') ? g('camManualCard').checkVisibility() : '无此元素')"
     " + ' ; SSID框=' + (g('camSsid') ? g('camSsid').value : '无') + ' ; 光标在=' + (document.activeElement||{}).id);", 200),
    ("o.push('⑤ 时间线（页面自己说过的话，带 +ms）：' + '\\n  ' + (window.__tl||[]).join('\\n  '));"
     "o.push('⑤ 日志尾部：' + (g('camOut3') ? g('camOut3').innerText.replace(/\\n/g,' | ').slice(-700) : '无'));", 200),
    ("o.push('⑥ 原生方法调用顺序：' + (window.__calls||[]).join(' → '));", 200),
]
tail = ('<script>\nvar o=[],STEPS=' + json.dumps([[s, d] for s, d in STEPS], ensure_ascii=False) + ',si=0;\n'
        'function g(i){return document.getElementById(i);}\n'
        "function txt(id){var e=g(id);return e?e.innerText.replace(/\\n/g,' / ').slice(0,300):'无';}\n"
        "function step(){var on=document.querySelector('#barD button.on');return on?on.textContent.trim():'?';}\n"
        'function finish(){var d=document.createElement("div");d.id=\'SIMOUT\';'
        'd.textContent=o.join("\\n");document.body.appendChild(d);}\n'
        'function next(){if(si>=STEPS.length){finish();return;}var st=STEPS[si++];'
        'try{(new Function(st[0]))();}catch(e){o.push("STEP-ERR@"+si+": "+e.message);}setTimeout(next,st[1]);}\n'
        'setTimeout(next,2500);\n</script>')

page = io.open(os.path.join(ROOT, 'app', 'base.html'), encoding='utf-8').read()
i0 = page.find('<body')
j0 = page.find('>', i0) + 1
pre = ('<script>window.__OM3_APP__=1;try{localStorage.clear();%s}catch(e){}%s</script>'
       % (("localStorage.setItem('om3cam', %s);" % json.dumps(json.dumps(SAVED))) if CASE == 'saved' else '', BRIDGE))
out = page[:j0] + pre + page[j0:].replace('</body>', tail + '</body>', 1)
hp = os.path.join(TMP, 'sim_connect.html')
io.open(hp, 'w', encoding='utf-8', newline='').write(out)
ud = os.path.join(TMP, 'osim')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,800',
                    '--virtual-time-budget=60000', '--dump-dom', 'file:///' + hp.replace(os.sep, '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
k = dom.find('id="SIMOUT"')
print('===== 推演场景：%s =====' % CASE)
print(dom[k:].split('>', 1)[1].split('</div>')[0]
      .replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
      if k >= 0 else '没拿到输出（DOM %d 字节）' % len(dom))
