# -*- coding: utf-8 -*-
"""① 加「扫二维码连相机」（内嵌 jsQR，离线可用）② 把「导入相机」页重排成三步向导"""
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
APK = TMP + r'\apk'
P = TMP + r'\app\base.html'
h = open(P, encoding='utf-8').read()
open(TMP + r'\app\base.before_scan.html', 'w', encoding='utf-8', newline='').write(h)

# ============================================================ 1. 重排 pane D
i = h.find('<div id="paneD" class="pane hide">')
j = h.find('<div id="paneC" class="pane hide">')
assert i > 0 and j > i
PANE = '''<div id="paneD" class="pane hide"><div class="wrap">
<h1>导入相机</h1>
<p class="sub">手机直连 OM-3 写配方 · 扫码连一次，以后自动连</p>

<div class="camstatus">
  <span id="camStWifi" class="cs">Wi-Fi：读取中…</span>
  <span id="camStCam" class="cs">相机：未检测</span>
  <span id="camStBak" class="cs">备份：无</span>
</div>

<div class="camsteps" id="camSteps">
  <button type="button" data-s="1" class="on">1 连接相机</button>
  <button type="button" data-s="2">2 备份设置</button>
  <button type="button" data-s="3">3 写入配方</button>
</div>

<!-- ============ 步骤 1 ============ -->
<div class="camview" id="camV1">
  <div class="camcard">
    <div class="camhd">扫相机屏幕上的二维码</div>
    <p class="camnote">相机上：<code>MENU → Wi-Fi/蓝牙 → Wi-Fi 设置</code>（或屏幕上「连接智能手机」那一屏），会出现二维码。<br>
      对着它扫一下，密码就自动填好并交给系统 —— <b>扫这一次就够：以后相机开机 Wi-Fi 打开，手机会自动连上</b>，不用再扫、也不用装官方 app。</p>
    <button type="button" id="camScan" class="camprimary">扫二维码</button>
    <button type="button" id="camScanHelp">看不到二维码？手动填</button>
    <div class="camout" id="camScanOut">还没扫。相机没显示二维码的话，点右边「手动填」也行（SSID 和密码相机屏幕上都有写）。</div>
  </div>

  <div class="camcard" id="camManualCard" style="display:none">
    <div class="camhd">手动填 SSID / 密码</div>
    <label>相机 SSID：<input type="text" id="camSsid" placeholder="例如 OM-3-1234567" style="width:190px"></label>
    <label>相机密码：<input type="text" id="camPass" placeholder="相机屏幕上那串密码" style="width:190px"></label>
    <button type="button" id="camJoin">记住它，以后自动连</button>
    <button type="button" id="camWifiSettings">打开系统 Wi-Fi 设置</button>
    <button type="button" id="camForget" class="camghost">撤销记住的热点</button>
    <div class="camout" id="camWifiOut"></div>
  </div>

  <div class="camcard">
    <div class="camhd">连上了吗？</div>
    <div class="camout" id="camWifiState">正在读当前 Wi-Fi…</div>
    <button type="button" id="camCheck">检测相机</button>
    <button type="button" id="camWifi" class="camghost">复制相机地址</button>
    <div class="camout" id="camOut1">未连接。</div>
  </div>
</div>

<!-- ============ 步骤 2 ============ -->
<div class="camview hide" id="camV2">
  <div class="camcard">
    <div class="camhd">备份相机当前设置（只读，不会改任何东西）</div>
    <p class="camnote">读一整套设置存成文件留底。写配方前先备份一份；万一写乱了，拿这份备份就能回滚（官方 app 的「恢复设置」也行）。</p>
    <button type="button" id="camBackup" class="camprimary">读取并备份</button>
    <button type="button" id="camDl" disabled>下载备份文件</button>
    <div class="camout" id="camOut2">还没备份。</div>
  </div>
</div>

<!-- ============ 步骤 3 ============ -->
<div class="camview hide" id="camV3">
  <div class="camcard">
    <div class="camhd">一次写入一个配方</div>
    <label>写入到：<select id="camTarget">
      <option value="current" selected>当前状态（立刻生效，最常用）</option>
      <option value="myset1">C1 自定义档</option>
      <option value="myset2">C2 自定义档</option>
      <option value="myset3">C3 自定义档</option>
      <option value="myset4">C4 自定义档</option>
      <option value="myset5">C5 自定义档</option>
    </select></label>
    <label>Color Profile 槽位：<select id="camSlot">
      <option value="1" selected>槽 1</option><option value="2">槽 2</option>
      <option value="3">槽 3</option><option value="4">槽 4</option>
    </select></label>
    <label>配方：<select id="camRecipe"></select></label>
    <label>相机型号：<input type="text" id="camModel" placeholder="① 检测后自动填" style="width:150px"></label>
    <details><summary>预览将要写入相机的数据</summary><pre id="camPreview"></pre></details>
    <label class="camchk"><input type="checkbox" id="camReboot"> 写完后重启相机（官方 app 也这么做，重启后设置才完全生效）</label>
    <button type="button" id="camWrite" class="camprimary">写入相机</button>
    <div class="camout" id="camOut3">选择配方和槽位，点「写入相机」。写入前会自动先备份一次。</div>
    <div class="camlogbtns">
      <button type="button" id="camCopyLog">复制全部日志</button>
      <button type="button" id="camDlLog">下载日志文件</button>
      <button type="button" id="camClearLog" class="camghost">清空日志</button>
      <span class="camloghint">三步的日志都在这里，跑完复制给我就行</span>
    </div>
  </div>
</div>

<!-- ============ 扫码浮层 ============ -->
<div class="scanmask hide" id="scanMask">
  <div class="scanbox">
    <div class="scanhd">对准相机屏幕上的二维码</div>
    <video id="scanVideo" playsinline autoplay muted></video>
    <canvas id="scanCanvas" style="display:none"></canvas>
    <div class="camout" id="scanOut">把整个二维码放进画面，不用按快门，自动识别。</div>
    <button type="button" id="scanStop">关闭</button>
  </div>
</div>
</div></div>
'''
h = h[:i] + PANE + h[j:]

# ============================================================ 2. CSS
CSS = '''
/* ---------- 导入相机：状态条 / 步骤 / 扫码 ---------- */
.camstatus{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.camstatus .cs{background:#1e1e1e;border:1px solid #2e2e2e;border-radius:20px;padding:5px 12px;font-size:12px;color:#9a9a9a}
.camstatus .cs.ok{color:#7ed3bd;border-color:#2f5f50}
.camstatus .cs.warn{color:#dcb98a;border-color:#5f4a2f}
.camsteps{display:flex;gap:6px;margin:0 0 16px}
.camsteps button{flex:1;background:#242424;border:1px solid #3a3a3a;color:#aaa;border-radius:9px;padding:10px 6px;font-size:13.5px;font-weight:600;font-family:inherit;cursor:pointer}
.camsteps button.on{background:#2f8f74;border-color:#2f8f74;color:#fff}
.camnote{font-size:13px;line-height:1.8;color:#c0c0c0;margin:0 0 12px}
.scanmask{position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:80;display:flex;align-items:center;justify-content:center;padding:16px}
.scanbox{width:100%;max-width:420px;background:#1b1b1b;border:1px solid #2e2e2e;border-radius:14px;padding:14px}
.scanhd{font-size:14px;font-weight:700;color:#fff;margin-bottom:10px}
.scanbox video{width:100%;border-radius:10px;background:#000;display:block;aspect-ratio:4/3;object-fit:cover}
.scanbox button{margin-top:10px;background:#2a2a2a;color:#e8e8e8;border:1px solid #3a3a3a;border-radius:8px;padding:9px 14px;font-size:13.5px;font-family:inherit;cursor:pointer}
'''
k = h.find('</style>')
h = h[:k] + CSS + h[k:]

# ============================================================ 3. 内嵌 jsQR
jsqr = open(TMP + r'\om3probe\jsqr.js', encoding='utf-8').read()
assert '</script>' not in jsqr.lower()
anchor = "<script>" + chr(10) + "/* ================= 导入相机（相机 Wi-Fi 直连） ================= */"
assert h.count(anchor) == 1
h = h.replace(anchor, '<script>/* jsQR 1.4.0 · MIT License · https://github.com/cozmo/jsQR */\n' + jsqr + '</script>\n' + anchor, 1)

# ============================================================ 4. JS：步骤切换 + 状态条 + 扫码
OLD_END = """  document.getElementById('camClearLog').addEventListener('click', function(){
    o1.innerHTML = ''; o2.innerHTML = ''; o3.innerHTML = '';
    ALLLOG.length = 0;
    o1.textContent = '未连接。';
    o2.textContent = '还没备份。';
    o3.textContent = '日志已清空。';
  });
})();"""
assert h.count(OLD_END) == 1
NEW = """  document.getElementById('camClearLog').addEventListener('click', function(){
    o1.innerHTML = ''; o2.innerHTML = ''; o3.innerHTML = '';
    ALLLOG.length = 0;
    o1.textContent = '未连接。';
    o2.textContent = '还没备份。';
    o3.textContent = '日志已清空。';
  });

  /* ================= 三步向导 ================= */
  var stepBtns = document.querySelectorAll('#camSteps button');
  function showStep(n){
    for(var i=0;i<stepBtns.length;i++)
      stepBtns[i].classList.toggle('on', stepBtns[i].getAttribute('data-s') === String(n));
    for(var k=1;k<=3;k++)
      document.getElementById('camV'+k).classList.toggle('hide', k !== n);
    var top = document.getElementById('camSteps').getBoundingClientRect().top + window.pageYOffset - 56;
    window.scrollTo(0, top > 0 ? top : 0);
  }
  for(var sb=0; sb<stepBtns.length; sb++)
    stepBtns[sb].addEventListener('click', function(){ showStep(+this.getAttribute('data-s')); });

  /* ================= 顶部状态条 ================= */
  function st(id, txt, cls){
    var el = document.getElementById(id);
    if(!el) return;
    el.textContent = txt;
    el.className = 'cs' + (cls ? ' ' + cls : '');
  }
  function statusTick(){
    if(Native){
      var s = {};
      try{ s = JSON.parse(Native.wifiState() || '{}'); }catch(e){}
      var ssid = s.ssid || '';
      var isCam = /OM-?3|OM-?D/i.test(ssid);
      st('camStWifi', ssid ? ('Wi-Fi：' + ssid) : (s.wifi ? 'Wi-Fi：未连热点' : 'Wi-Fi：关'),
         isCam ? 'ok' : (ssid ? 'warn' : ''));
    }
    var t1 = o1.textContent || '';
    if(/相机应答/.test(t1)) st('camStCam', '相机：已连上', 'ok');
    else if(/失败/.test(t1)) st('camStCam', '相机：连不上', 'warn');
    else st('camStCam', '相机：未检测');
    st('camStBak', document.getElementById('camDl').disabled ? '备份：无' : '备份：已有',
       document.getElementById('camDl').disabled ? '' : 'ok');
  }
  setInterval(statusTick, 2500);
  setTimeout(statusTick, 300);

  /* ================= 扫二维码连相机 ================= */
  var scanStream = null, scanRAF = null;
  function parseWifi(text){
    var s = String(text || '').trim(), o = {ssid:'', pass:'', raw:s};
    if(/^WIFI:/i.test(s)){                      /* 标准 Wi-Fi 二维码 */
      var g = function(k){
        var r = new RegExp(k + ':((?:\\\\\\\\.|[^;])*)', 'i').exec(s);
        return r ? r[1].replace(/\\\\\\\\(.)/g, '$1') : '';
      };
      o.ssid = g('S'); o.pass = g('P');
      if(o.ssid) return o;
    }
    if(s.charAt(0) === '{'){                    /* JSON 形式 */
      try{
        var j = JSON.parse(s);
        for(var key in j){
          var kk = String(key).toLowerCase();
          if(!o.ssid && /ssid|name|^s$/.test(kk)) o.ssid = String(j[key]);
          if(!o.pass && /pass|pwd|key|^p$/.test(kk)) o.pass = String(j[key]);
        }
        if(o.ssid) return o;
      }catch(e){}
    }
    var m = /ssid=([^&;\\s]+)/i.exec(s);        /* key=value 形式 */
    if(m){
      o.ssid = decodeURIComponent(m[1]);
      var m2 = /(?:password|pass|pwd|key)=([^&;\\s]+)/i.exec(s);
      o.pass = m2 ? decodeURIComponent(m2[1]) : '';
      return o;
    }
    m = /OM[-_ ]?[0-9A-Za-z]{1,4}[-_][0-9A-Za-z]{3,}/i.exec(s);   /* 兜底：认 SSID 样式 */
    if(!m) m = /(OM[0-9A-Za-z-]{4,})/i.exec(s);
    if(m) o.ssid = m[0];
    m = /\\b(\\d{8,12})\\b/.exec(s);
    if(m) o.pass = m[1];
    if(!o.ssid){
      var ws = s.split(/[\\s,;|]+/);
      for(var i=0;i<ws.length;i++) if(/^[0-9A-Za-z_.-]{6,}$/.test(ws[i])){ o.ssid = ws[i]; break; }
    }
    return o;
  }
  window.__om3parseWifi = parseWifi;

  function stopScan(){
    if(scanRAF){ cancelAnimationFrame(scanRAF); scanRAF = null; }
    if(scanStream){ try{ scanStream.getTracks().forEach(function(t){ t.stop(); }); }catch(e){} scanStream = null; }
    var v = document.getElementById('scanVideo'); if(v) v.srcObject = null;
    document.getElementById('scanMask').classList.add('hide');
  }
  document.getElementById('scanStop').addEventListener('click', stopScan);
  document.getElementById('scanMask').addEventListener('click', function(e){ if(e.target === this) stopScan(); });

  document.getElementById('camScanHelp').addEventListener('click', function(){
    var c = document.getElementById('camManualCard');
    c.style.display = (c.style.display === 'none' || !c.style.display) ? '' : 'none';
    if(c.style.display !== 'none') c.scrollIntoView({block:'center'});
  });

  document.getElementById('camScan').addEventListener('click', function(){
    var out = document.getElementById('scanOut');
    out.innerHTML = '';
    if(!window.jsQR){ line(out, '扫码组件没加载成功（页面可能被改过）。用「手动填」也一样能连。', 'err'); return; }
    if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){
      line(out, '这个环境不给用摄像头（桌面版页面）。手机上用本 app 才能扫。', 'err'); return;
    }
    if(Native && Native.ensureCamera){
      var pr = '';
      try{ pr = String(Native.ensureCamera()); }catch(e){}
      if(pr.indexOf('need_perm') === 0){
        line(out, '请在弹出的对话框里允许「相机」权限，然后再点一次「扫二维码」。', 'warn');
        return;
      }
    }
    document.getElementById('scanMask').classList.remove('hide');
    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}}, audio:false})
      .then(function(stream){
        scanStream = stream;
        var v = document.getElementById('scanVideo'), c = document.getElementById('scanCanvas');
        v.srcObject = stream;
        var p = v.play(); if(p && p.catch) p.catch(function(){});
        var ctx = c.getContext('2d');
        function tick(){
          if(!scanStream) return;
          if(v.readyState === v.HAVE_ENOUGH_DATA && v.videoWidth){
            c.width = v.videoWidth; c.height = v.videoHeight;
            ctx.drawImage(v, 0, 0, c.width, c.height);
            var found = null;
            try{
              var img = ctx.getImageData(0, 0, c.width, c.height);
              found = window.jsQR(img.data, img.width, img.height, {inversionAttempts:'dontInvert'});
            }catch(e){}
            if(found && found.data){ onScan(found.data); return; }
          }
          scanRAF = requestAnimationFrame(tick);
        }
        scanRAF = requestAnimationFrame(tick);
      }, function(err){
        document.getElementById('scanOut').innerHTML = '';
        line(out, '打不开摄像头：' + err.message, 'err');
        line(out, '检查：系统设置里给本 app 开「相机」权限；或直接用「手动填」。', 'warn');
        stopScan();
      });
  });

  function onScan(text){
    var out = document.getElementById('scanOut');
    var p = parseWifi(text);
    line(out, '扫到：' + text.slice(0, 200));
    if(!p.ssid){
      line(out, '没认出 SSID/密码 —— 把上面这行发我，我补上解析规则；也可以「手动填」。', 'warn');
      stopScan();
      return;
    }
    document.getElementById('camSsid').value = p.ssid;
    document.getElementById('camPass').value = p.pass || '';
    document.getElementById('camManualCard').style.display = '';
    line(out, '识别到 SSID：' + p.ssid + (p.pass ? '（密码已填好）' : '（没扫到密码，请手动补一下）'), 'ok');
    stopScan();
    if(p.pass && Native){
      var r = '';
      try{ r = String(Native.joinWifi(p.ssid, p.pass)); }catch(e){ r = 'error'; }
      if(r === 'ok'){
        line(out, '已交给系统记住。以后相机开机、Wi-Fi 打开时会自动连上 —— 这几步不用再做。', 'ok');
        setTimeout(statusTick, 1500);
      } else if(r.indexOf('need_perm') === 0){
        line(out, '还差一步授权（弹出的「附近的设备 / 位置信息」点允许），填的内容已留着，再点一次「记住它，以后自动连」即可。', 'warn');
      } else {
        line(out, '自动记住没成功（' + r + '），点「打开系统 Wi-Fi 设置」手动连一次也行（SSID 和密码已填在上面）。', 'warn');
      }
    }
    wifiRefresh();
  }
})();"""
h = h.replace(OLD_END, NEW, 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('页面：三步向导 + 扫码（内嵌 jsQR %d KB），base.html %.1f KB' % (len(jsqr) // 1024, len(h.encode('utf-8')) / 1024))

# ============================================================ 5. MainActivity + Manifest
p = APK + r'\java\com\om3\handbook\MainActivity.java'
j = open(p, encoding='utf-8').read()
if 'WebChromeClient' not in j:
    j = j.replace('import android.webkit.WebViewClient;',
                  'import android.webkit.PermissionRequest;\nimport android.webkit.WebChromeClient;\nimport android.webkit.WebViewClient;', 1)
    j = j.replace('''        wv.addJavascriptInterface(new Bridge(), "OM3Native");''',
                  '''        wv.addJavascriptInterface(new Bridge(), "OM3Native");
        // 让页面能用 <video> 调摄像头扫码
        wv.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(new Runnable() {
                    @Override public void run() { request.grant(request.getResources()); }
                });
            }
        });''', 1)
    j = j.replace('''        @JavascriptInterface
        public void openWifiSettings() {''',
                  '''        /** 页面要调摄像头扫码时先问这个：ok / need_perm:xxx */
        @JavascriptInterface
        public String ensureCamera() {
            if (Build.VERSION.SDK_INT >= 23
                    && checkSelfPermission(android.Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{ android.Manifest.permission.CAMERA }, 4712);
                return "need_perm:android.permission.CAMERA";
            }
            return "ok";
        }

        @JavascriptInterface
        public void openWifiSettings() {''', 1)
    open(p, 'w', encoding='utf-8', newline='').write(j)
    print('MainActivity: 已加 WebChromeClient（摄像头授权）+ ensureCamera')

p = APK + r'\AndroidManifest.xml'
m = open(p, encoding='utf-8').read()
if 'permission.CAMERA' not in m:
    m = m.replace('    <uses-sdk', '    <uses-permission android:name="android.permission.CAMERA" />\n    <uses-sdk', 1)
    open(p, 'w', encoding='utf-8', newline='').write(m)
    print('AndroidManifest: 已加 CAMERA 权限')
