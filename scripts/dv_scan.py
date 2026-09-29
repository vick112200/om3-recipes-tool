# -*- coding: utf-8 -*-
"""第 48 轮验收：扫码（识别率 + 全屏界面 + 诊断可见性）
跑法：python scripts/dv_scan.py

为什么要这些断言（逐条对应用户那两句话）：
  ① 「扫描二维码一直扫不出」+ 追问答复「浮层开了、有画面、帧在涨、识别尝试也在涨，就是不认出来」
     → 逐条验：
        · 取景分辨率要了 1280x720（原来只要 640x480）
        · **解码必须省 CPU**（第 48 轮把取景提到 1280x720 + 裁剪放大 ×2/×3 + 原分辨率整帧 → 真机卡顿，第 49 轮撤销）
          ⇒ 断言：取景只要 640x480；每次读的画布**不超过取景尺寸**（不放大）；每轮最多两遍
        · 认出来 → SSID/密码自动填好 → 浮层关 → 轨道 stop
  ② 「参考下世面上的扫码界面…放大一点画面」
     → 逐条验：浮层 == 视口、video 覆盖视口、取景窗在视口内且 ≥60vmin、三个按钮真手指点得到
  ③ 第 49 轮：**扫码入口隐藏**（用户：「先把扫码隐藏一下」）+ 首屏给「怎么连相机」指引
     → 断言：三个入口 .hid49 隐藏且点不到；指引块在位（第一次用官方 App / 以后直接点连接相机 / 手动填兜底）；
       底栏第①步不再偷偷启动扫码；手动填那两格直接可见
     扫码流程本身**代码没删**，所以下面这些场景改成用 window.__om3startScan() 驱动（入口已隐藏），继续守着它。

  ③ 顺带把两个「静默失败」钉死（没画面 / 一直认不出）：都必须**有可见文字**且**循环继续**
  ④ 回归：等权限 / 打不开摄像头两条老路径仍然可见、0 未处理拒绝（r46 修过的那条）
"""
import io
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
SRC = r'D:\workspace\om3-handbook'
TMP = r'C:\Users\82302\AppData\Local\Temp'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
src = io.open(SRC + r'\app\base.html', encoding='utf-8').read()
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


# ================================================================ 静态
print('=== ①-a 静态：扫码入口已隐藏 + 「怎么连相机」指引在位（第 49 轮）===')
A('.hid49{display:none !important}' in src, 'CSS：.hid49（隐藏扫码入口）在')
for _i in ['camGateScan', 'camScan', 'camScanHelp']:
    import re as _re
    _m = _re.search(r'<button[^>]*id="%s"[^>]*>' % _i, src)
    A(bool(_m) and 'hid49' in _m.group(0), '入口 #%s 带 .hid49（隐藏，元素保留）' % _i)
A('<div class="camguide49">' in src, '首屏新增「怎么连相机」指引块 .camguide49')
A('官方 App' in src and 'OM Image Share' in src, '指引里写了：第一次用**官方 App** 连一次')
A('手机就记住了这台相机的 Wi-Fi' in src, '指引里写了：连过一次手机就记住了')
A('直接点下面的「<b>连接相机</b>」' in src, '指引里写了：以后直接点「连接相机」')
A('手动填 SSID / 密码' in src, '指引里留了「不想装官方 App → 手动填 SSID/密码」的兜底')
A("if(gs) gs.addEventListener('click', function(){ showStep(1); });" in src,
  '底栏第①步不再偷偷启动扫码（原来会 camScan.click()）')
A('<div class="camcard" id="camManualCard">' in src, '手动填卡片直接可见（不再靠「看不到二维码？手动填」展开）')

print('\n=== ①-b 静态：解码回到省 CPU 的两遍（撤掉第 48 轮的高清/放大方案）===')
A('width:{ideal:640}, height:{ideal:480}}' in src, '取景回到 640x480')
A('ideal:1280' not in src and 'ideal:720' not in src, '没有 leftover 的 1280/720 取景')
A('Math.min(1, targetW / Math.max(sw, sh))' in src, 'tryDecode 回到 sc ≤ 1（只缩不放）')
A('upMax' not in src and 'MAXNATIVE' not in src, '放大/原分辨率那几遍的代码已撤掉')
A('stat.p1++; if(tryDecode(0, 0, VW, VH, MAXW)) return true;' in src, '每轮第①遍：整帧')
A('if(stat.round % 2 === 0){' in src, '每轮第②遍：隔一轮做一次中心 60% 裁剪')
A("stat.warnNoFrame" in src and "stat.warnSlow" in src, '第 48 轮加的两个失败提示**保留**（它们不吃 CPU）')

print('\n=== ①-c 静态：全屏取景的样式/标记在，旧 id 一个不少 ===')
A('.scanbox video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover' in src,
  'CSS：video 铺满（原来 100% 宽 + aspect-ratio:4/3 的小卡片）')
A('.scanwin{position:absolute' in src and 'box-shadow:0 0 0 100vmax' in src, 'CSS：取景窗 + 窗外压暗')
A(src.count('<i></i>') == 4, '取景窗四个角标（%d 个）' % src.count('<i></i>'))
A('.scantop{' in src and '.scanbot{' in src and '.scanbtns button' in src, 'CSS：顶部说明 / 底部信息 / 按钮行')
A(all(('id="%s"' % i) in src for i in ['scanMask', 'scanVideo', 'scanCanvas', 'scanOut', 'scanStat', 'scanStop']),
  '旧 id 全保留（block07/08、dv_*、verify_all、check_app 都按它们抓）')
A('id="scanManual"' in src and 'id="scanDiag"' in src, '新增 #scanManual（手动填）/ #scanDiag（复制诊断）')
A('window.__om3scanStat' in src and 'window.__om3scanDiag' in src, '诊断取值/诊断文本都导出了（测试与复制按钮共用）')

# ================================================================ 运行时脚手架
STUB = r"""
<script>
window.__OM3_APP__=1;window.__errs=[];window.__rejs=[];window.__copied=[];
window.addEventListener('error',function(e){window.__errs.push('ERR '+(e.message||'')+' @'+(e.lineno||0));});
window.addEventListener('unhandledrejection',function(e){window.__rejs.push('REJ '+String(e.reason&&e.reason.message||e.reason));});
(function(){
  function canned(p){ return p.indexOf('mysetdatasize')>=0 ? '<datasize>120</datasize>' : '<result>ok</result>'; }
  window.OM3Native={
    ensureCamera:function(){ return window.__om3Ensure || 'ok'; },
    camGetAsync:function(p){ var id='h'+Math.random(); setTimeout(function(){ try{window.__om3http(id,{s:200,t:canned(p||'')});}catch(e){} },60); return id; },
    camPostAsync:function(p,b){ return 'h'; }, camGet:function(p){ return JSON.stringify({s:200,t:canned(p)}); },
    camPost:function(p,b){ return JSON.stringify({s:200,t:canned(p)}); },
    cameraState:function(){ return '{}'; }, wifiState:function(){ return JSON.stringify({wifi:true,ssid:'x',sdk:34}); },
    wifiScanList:function(){ return '[]'; }, connectCamera:function(){ return 'ok'; }, joinWifi:function(){ return 'ok'; },
    disconnectCamera:function(){}, dropCamera:function(){}, openWifiSettings:function(){},
    blePerm:function(){ return 'ok'; }, blePermDetail:function(){ return ''; }, bleAskPerm:function(){},
    bleEnable:function(){ return 'ok'; }, bleScanStart2:function(){}, bleScanStop:function(){}, bleDevices:function(){ return '[]'; },
    shareText:function(){ return 'ok'; }, copyText:function(){ return 'ok'; }, toast:function(){ return 'ok'; },
    pickFile:function(){ return ''; }, version:function(){ return 'stub'; }
  };
})();
</script>
"""

# 假摄像头脚手架：真 MediaStream（假对象赋给 video.srcObject 会抛 TypeError）+ 假 canvas + 假 jsQR
FAKE = r"""
function fakeCam(o){
  o = o || {};
  window.__gum = 0; window.__stopped = 0; window.__sizes = []; window.__jc = 0;
  var st = new MediaStream();
  st.getTracks = function(){ return [{ stop: function(){ window.__stopped++; } }]; };
  Object.defineProperty(navigator, 'mediaDevices', {configurable:true, value:{
    getUserMedia: function(c){
      window.__gum++; window.__con = c;
      if(o.reject) return Promise.reject(new Error('NotAllowedError: 没有相机权限'));
      return Promise.resolve(st);
    }}});
  HTMLMediaElement.prototype.play = function(){ return Promise.resolve(); };
  var orig = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function(kind){
    if(kind !== '2d') return orig.apply(this, arguments);
    return { drawImage: function(){},
             getImageData: function(x,y,w,h){ window.__sizes.push([w,h]); return { data: new Uint8ClampedArray(w*h*4), width: w, height: h }; } };
  };
  window.jsQR = function(){ window.__jc++; if(o.hitAt && window.__jc >= o.hitAt) return { data: 'WIFI:S:OM-3-TEST;T:WPA;P:12345678;;' }; return null; };
  var v = document.getElementById('scanVideo');
  ['readyState','videoWidth','videoHeight'].forEach(function(k){
    var val = (k === 'readyState') ? 4 : (k === 'videoWidth' ? (o.vw || 0) : (o.vh || 0));
    try{ Object.defineProperty(v, k, {configurable:true, get:function(){ return val; }}); }catch(e){}
  });
}
function mkOut(o, F){
  o.push(''); o.push('哨兵失败数=' + F);
  var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
  document.body.appendChild(d);
}
/* 真手指：拿 elementFromPoint 命中的那个元素再点（不是绕过命中测试直接 .click()） */
function tap(id, label, ok){
  var el = document.getElementById(id);
  if(!el){ ok(false, label + '：元素不存在'); return false; }
  var r = el.getBoundingClientRect();
  if(r.width < 2 || r.height < 2){ ok(false, label + '：尺寸 0'); return false; }
  var x = Math.round(r.left + r.width/2), y = Math.round(r.top + r.height/2);
  var top = document.elementFromPoint(x, y);
  var good = !!top && (top === el || el.contains(top));
  ok(good, label + '：真手指点得到（选中 ' + ((top && (top.tagName.toLowerCase() + (top.id ? ('#' + top.id) : ''))) || 'null') + '）');
  if(!good) return false;
  if(top !== el && top.click) top.click(); else el.click();
  return true;
}
"""


def run(name, js, budget=25000):
    k = src.find('<body')
    j = src.find('>', k) + 1
    out = src[:j] + STUB + src[j:].replace('</body>', '<script>' + FAKE + js + '</script></body>', 1)
    p = TMP + '\\dv_scan_' + name + '.html'
    io.open(p, 'w', encoding='utf-8', newline='').write(out)
    ud = TMP + '\\dv_scan_dir_' + name
    subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
    r = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                        '--user-data-dir=' + ud, '--window-size=412,900',
                        '--virtual-time-budget=%d' % budget, '--dump-dom',
                        'file:///' + p.replace('\\', '/')],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=400)
    dom = r.stdout or ''
    kk = dom.find('id="DBGOUT"')
    if kk < 0:
        A(False, '[%s] 探针没拿到输出（DOM %d 字符）' % (name, len(dom)))
        return
    body = dom[kk:].split('>', 1)[1].split('</pre>')[0]
    print(body)
    global K, F
    K += body.count('[')
    F += body.count('[FAIL]')


# ================================================================ ①-d 第 49 轮：扫码隐藏 + 指引 + 底栏不启动扫码
print('\n=== ② 扫码已隐藏：入口点不到、指引看得见、底栏第①步不再启动它 ===')
run('hidden', r"""
setTimeout(function(){
  var o=[], F=0;
  function ok(c,m){ o.push((c?'[OK ] ':'[FAIL] ')+m); if(!c) F++; }
  function info(m){ o.push('      '+m); }
  var gum = 0;
  Object.defineProperty(navigator, 'mediaDevices', {configurable:true, value:{
    getUserMedia: function(){ gum++; return Promise.reject(new Error('不该被调用')); } }});
  document.getElementById('tabCam').click();
  setTimeout(function(){
    /* 三个入口：都隐藏、都点不到 */
    ['camGateScan','camScan','camScanHelp'].forEach(function(id){
      var el = document.getElementById(id);
      var vis = el ? getComputedStyle(el).display : 'missing';
      ok(!!el && vis === 'none', '入口 #' + id + ' 隐藏（display=' + vis + '）');
    });
    /* 首屏两个真按钮仍然点得到；指引看得见 */
    tap('camGateConn', '首屏「连接相机」', ok);
    var fold = document.querySelector('#camGateOff details');
    ok(!!fold, '首屏有「连不上？更多方式」折叠（手动填在里面）');
    if(fold){
      ok(fold.querySelector('summary').textContent.indexOf('手动填 SSID') >= 0,
         '折叠标题里写了「手动填 SSID/密码」（用户找得到）');
      fold.open = true;                 /* 用户路径：点开这一格 */
    }
    tap('camGateManual', '「连不上？更多方式」里的手动填', ok);
    var gt = document.querySelector('.camguide49');
    ok(!!gt && gt.getBoundingClientRect().height > 30, '首屏「怎么连相机」指引可见（' +
       Math.round(gt ? gt.getBoundingClientRect().height : 0) + 'px）');
    /* 底栏第①步：以前会顺手启动扫码，现在只切步骤 */
    var s1 = document.querySelector('#barD button[data-dstep="1"]') || document.querySelector('#barD button');
    if(s1) s1.click();
    setTimeout(function(){
      var mk = document.getElementById('scanMask');
      ok(mk.classList.contains('hide'), '点底栏第①步 → 扫码浮层**不开**（原来会 camScan.click()）');
      ok(gum === 0, '点底栏第①步 → getUserMedia 一次都没调（' + gum + '）');
      /* 手动填那两格直接可见（不再需要先点「看不到二维码？手动填」） */
      var mc = document.getElementById('camManualCard');
      ok(!!mc && mc.offsetParent !== null, '手动填那两格直接可见（不用先点按钮展开）');
      ok(window.__errs.length === 0, '0 JS 报错（' + window.__errs.length + '）' + (window.__errs[0] || ''));
      o.push(''); o.push('失败数='+F); mkOut(o, F);
    }, 600);
  }, 1200);
}, 2600);
""")

# ================================================================ ② 全屏界面（真手指）
print('\n=== ② 全屏取景：浮层 == 视口、video 覆盖视口、取景窗够大、三个按钮点得到 ===')
run('layout', r"""
setTimeout(function(){
  var o=[], F=0;
  function ok(c,m){ o.push((c?'[OK ] ':'[FAIL] ')+m); if(!c) F++; }
  function info(m){ o.push('      '+m); }
  document.getElementById('tabCam').click();
  setTimeout(function(){
    /* 第 49 轮：入口已隐藏 → 不能点它；改从首屏「连接相机」按钮确认指引 + 用官方导出的入口驱动扫码流程 */
    var gs = document.getElementById('camGateScan');
    ok(!!gs && getComputedStyle(gs).display === 'none', '首屏「扫二维码（第一次）」已隐藏（display:none）');
    var gt = document.querySelector('.camguide49');
    ok(!!gt && gt.getBoundingClientRect().height > 30, '首屏「怎么连相机」指引可见');
    var gtx = gt ? gt.textContent : '';
    ok(gtx.indexOf('官方 App') >= 0 && gtx.indexOf('连接相机') >= 0 && gtx.indexOf('手动填') >= 0,
       '指引里三件事都在：第一次用官方 App / 以后点连接相机 / 手动填兜底');
    tap('camGateConn', '首屏「连接相机」', ok);
    ok(getComputedStyle(document.getElementById('camGateScan')).display === 'none',
       '（已隐藏的）「扫二维码（第一次）」点不到：display:none');
    window.__om3startScan();          /* 入口隐藏了，直接用导出的入口驱动同一段代码 */
    setTimeout(function(){
      var mk = document.getElementById('scanMask');
      var r = mk.getBoundingClientRect();
      ok(!mk.classList.contains('hide'), '浮层已开');
      ok(Math.abs(r.width - innerWidth) <= 2 && Math.abs(r.height - innerHeight) <= 2,
         '浮层盒 == 视口（' + Math.round(r.width) + 'x' + Math.round(r.height) + ' vs ' + innerWidth + 'x' + innerHeight + '）');
      var v = document.getElementById('scanVideo'), vr = v.getBoundingClientRect();
      ok(vr.width >= innerWidth - 2 && vr.height >= innerHeight - 2,
         'video 覆盖整个视口（' + Math.round(vr.width) + 'x' + Math.round(vr.height) + '，原来只有约 390x293）');
      info('video 面积占比 ' + Math.round(vr.width * vr.height * 100 / (innerWidth * innerHeight)) + '%');
      var w = document.querySelector('.scanwin'), wr = w.getBoundingClientRect();
      var vmin = Math.min(innerWidth, innerHeight);
      ok(wr.width >= vmin * 0.6 && wr.left >= 0 && wr.top >= 0 && wr.right <= innerWidth + 1,
         '取景窗在视口内且 ≥60vmin（' + Math.round(wr.width) + ' vs ' + Math.round(vmin * 0.6) + '）');
      ok(getComputedStyle(w).pointerEvents === 'none', '取景窗不吃点击（pointer-events:none）');
      var zk = Number(getComputedStyle(mk).zIndex || 0), zb = Number(getComputedStyle(document.getElementById('barD')).zIndex || 0);
      ok(zk > zb, '浮层层高在底栏之上（' + zk + ' > ' + zb + '）—— 改前是 80，全屏后按钮会被底栏盖住（命中测试抓出来的）');
      tap('scanManual', '底部「手动填」', ok);
      setTimeout(function(){
        var mc = document.getElementById('camManualCard');
        ok(mc && mc.getBoundingClientRect().height > 0, '点「手动填」→ 手动填那两格展开了（关掉浮层直达）');
        o.push(''); o.push('失败数='+F); mkOut(o, F);
      }, 500);
    }, 800);
  }, 1200);
}, 2600);
""")
run('buttons', r"""
setTimeout(function(){
  var o=[], F=0;
  function ok(c,m){ o.push((c?'[OK ] ':'[FAIL] ')+m); if(!c) F++; }
  document.getElementById('tabCam').click();
  setTimeout(function(){
    fakeCam({vw:1280, vh:720});
    window.__om3startScan();   /* 入口已隐藏（r49），直接驱动同一段扫码代码 */
    setTimeout(function(){
      tap('scanDiag', '底部「复制诊断」', ok);
      tap('scanStop', '底部「✕ 关闭」', ok);
      setTimeout(function(){
        var mk = document.getElementById('scanMask');
        ok(mk.classList.contains('hide'), '点「✕ 关闭」→ 浮层关掉');
        ok(window.__errs.length === 0, '0 JS 报错（' + window.__errs.length + '）' + (window.__errs[0] || ''));
        o.push(''); o.push('失败数='+F); mkOut(o, F);
      }, 500);
    }, 700);
  }, 900);
}, 2600);
""")

# ================================================================ ③ 识别率
print('\n=== ③ 识别率：640x480 取景 → 两遍省 CPU 解码 → 认出来（第 49 轮口径）===')
run('decode', r"""
setTimeout(function(){
  var o=[], F=0;
  function ok(c,m){ o.push((c?'[OK ] ':'[FAIL] ')+m); if(!c) F++; }
  function info(m){ o.push('      '+m); }
  document.getElementById('tabCam').click();
  setTimeout(function(){
    fakeCam({vw:640, vh:480, hitAt:3});
    window.__om3startScan();   /* 入口已隐藏（r49），直接驱动同一段扫码代码 */
    setTimeout(function(){
      var con = window.__con && window.__con.video;
      ok(!!con && con.width && con.width.ideal === 640 && con.height.ideal === 480,
         'getUserMedia 只要 640x480（第 48 轮的 1280x720 已撤销；实测 ' + JSON.stringify(con) + '）');
      setTimeout(function(){
        var sz = window.__sizes, mx = 0, mh = 0;
        for(var i=0;i<sz.length;i++){
          if(sz[i][0] > mx) mx = sz[i][0];
          if(sz[i][1] > mh) mh = sz[i][1];
        }
        info('读到的画布尺寸（前 10 个）：' + JSON.stringify(sz.slice(0,10)));
        /* 第 48 轮就是在这里翻车的：放大 + 原分辨率整帧 → 真机卡顿。这条护栏防止再犯。 */
        ok(mx <= 640 && mh <= 480,
           '省 CPU 护栏：每次读的画布都不超过取景 640x480（实测最大 ' + mx + 'x' + mh + '，不放大、不跑原分辨率那遍）');
        var rd = Number(((window.__om3scanStat()||'').match(/轮 (\d+)/)||[0,0])[1]);
        ok(rd > 0 && sz.length <= rd * 2, '每轮最多两遍（轮 ' + rd + ' 次 / 读 ' + sz.length + ' 次）');
        ok(Number((window.__om3scanStat()||'').match(/识别尝试 (\d+)/)[1]) > 0, '识别确实在跑');
        ok(!!document.getElementById('scanMask').classList.contains('hide'), '认出来 → 浮层自动关');
        ok((document.getElementById('camSsid')||{}).value === 'OM-3-TEST', 'SSID 自动填好（实测「' + ((document.getElementById('camSsid')||{}).value) + '」）');
        ok((document.getElementById('camPass')||{}).value === '12345678', '密码自动填好');
        ok(window.__stopped > 0, '摄像头轨道已 stop（' + window.__stopped + '）');
        ok(window.__errs.length === 0, '0 JS 报错（' + window.__errs.length + '）' + (window.__errs[0] || ''));
        ok(window.__rejs.length === 0, '0 未处理拒绝（' + window.__rejs.length + '）');
        o.push(''); o.push('失败数='+F); mkOut(o, F);
      }, 3000);
    }, 900);
  }, 900);
}, 2600);
""")
run('small', r"""
setTimeout(function(){
  var o=[], F=0;
  function ok(c,m){ o.push((c?'[OK ] ':'[FAIL] ')+m); if(!c) F++; }
  function info(m){ o.push('      '+m); }
  document.getElementById('tabCam').click();
  setTimeout(function(){
    fakeCam({vw:640, vh:480, hitAt:2});
    window.__om3startScan();   /* 入口已隐藏（r49），直接驱动同一段扫码代码 */
    setTimeout(function(){
      info('640x480 取景时的画布尺寸：' + JSON.stringify(window.__sizes.slice(0,6)));
      ok(document.getElementById('scanMask').classList.contains('hide'), '640x480 取景也能认出来 → 浮层关');
      var st = window.__om3scanStat ? window.__om3scanStat() : '';
      ok(st.indexOf('（整帧 ') >= 0 && st.indexOf(' / 裁剪 ') >= 0, '诊断行只说两遍：整帧 / 裁剪（stat=' + st + '）');
      var big = 0;
      (window.__sizes||[]).forEach(function(s){ if(s[0] > 640 || s[1] > 480) big++; });
      ok(big === 0, '没有任何一次读 超过取景尺寸的画布（不放大：' + big + ' 次越界）');
      ok(window.__errs.length === 0, '0 JS 报错（' + window.__errs.length + '）');
      o.push(''); o.push('失败数='+F); mkOut(o, F);
    }, 1500);
  }, 900);
}, 2600);
""")

# ================================================================ ④ 两个静默失败模式现在都要说话
print('\n=== ④ 静默失败模式：没画面 / 一直认不出，都要有可见文字且不停循环 ===')
run('noframes', r"""
setTimeout(function(){
  var o=[], F=0;
  function ok(c,m){ o.push((c?'[OK ] ':'[FAIL] ')+m); if(!c) F++; }
  function info(m){ o.push('      '+m); }
  document.getElementById('tabCam').click();
  setTimeout(function(){
    fakeCam({vw:0, vh:0});                      /* 流有了，但一直没有画面（videoWidth=0） */
    window.__om3startScan();   /* 入口已隐藏（r49），直接驱动同一段扫码代码 */
    var f5=0, f7=0;
    setTimeout(function(){ f5 = (window.__om3scanStat()||'').match(/帧 (\d+)/); }, 5000);
    setTimeout(function(){
      var st = window.__om3scanStat() || '';
      info('stat=' + st);
      var so = (document.getElementById('scanOut')||{}).textContent || '';
      ok(so.indexOf('没画面') >= 0, '开了 4.5 秒还没画面 → 浮层里明确说了（「' + so.slice(0,60) + '…」）');
      ok((document.getElementById('camOut3')||{}).textContent.indexOf('没画面') >= 0, '这句也进了日志（☰→复制日志能看到）');
      var n5 = f5 ? Number(f5[1]) : -1, n7 = Number((st.match(/帧 (\d+)/)||[0,0])[1]);
      ok(n5 > 0 && n7 > n5, '提示之后**继续在扫**（帧 ' + n5 + ' → ' + n7 + '，没有自己停）');
      ok(st.indexOf('画面 还没来') >= 0, '诊断行写的是「画面 还没来」（卡在哪一步一眼看出来）');
      ok(window.__errs.length === 0, '0 JS 报错（' + window.__errs.length + '）');
      o.push(''); o.push('失败数='+F); mkOut(o, F);
    }, 7000);
  }, 900);
}, 2600);
""", budget=30000)
run('nodetect', r"""
setTimeout(function(){
  var o=[], F=0;
  function ok(c,m){ o.push((c?'[OK ] ':'[FAIL] ')+m); if(!c) F++; }
  function info(m){ o.push('      '+m); }
  document.getElementById('tabCam').click();
  setTimeout(function(){
    fakeCam({vw:1280, vh:720});                 /* 有画面、每轮都在识别，但永远认不出 */
    window.__om3startScan();   /* 入口已隐藏（r49），直接驱动同一段扫码代码 */
    var f10 = 0;
    setTimeout(function(){ f10 = Number(((window.__om3scanStat()||'').match(/帧 (\d+)/)||[0,0])[1]); }, 10000);
    setTimeout(function(){
      var st = window.__om3scanStat() || '';
      var so = (document.getElementById('scanOut')||{}).textContent || '';
      info('stat=' + st);
      ok(so.indexOf('还没认出来') >= 0, '扫 15 秒还没认出来 → 给了可操作提示（「' + so.slice(0,50) + '…」）');
      ok(st.indexOf('画面 1280x720') >= 0, '诊断行写了画面尺寸（' + st.slice(0,40) + '）');
      ok(Number((st.match(/帧 (\d+)/)||[0,0])[1]) > f10, '提示之后**继续在扫**（帧 ' + f10 + ' → ' + st.match(/帧 (\d+)/)[1] + '）');
      var lg = (document.getElementById('camOut3')||{}).textContent || '';
      ok(lg.indexOf('[扫码] 帧') >= 0, '诊断行每 2 秒进日志（☰→复制日志能带出来）');
      /* 「复制诊断」按钮：点了要有反馈，且文本内容齐全 */
      var d = window.__om3scanDiag ? window.__om3scanDiag() : '';
      ok(d.indexOf('识别尝试') >= 0 && d.indexOf('画面') >= 0 && d.indexOf('裁剪') >= 0
         && d.indexOf('轨道') >= 0 && d.indexOf('整帧') >= 0,
         '「复制诊断」文本里有 帧/识别尝试/画面/整帧/裁剪/轨道');
      tap('scanDiag', '「复制诊断」', ok);
      setTimeout(function(){
        var bt = (document.getElementById('scanDiag')||{}).textContent || '';
        ok(bt === '已复制 ✓' || bt === '复制失败', '点完有明确反馈（实测「' + bt + '」）');
        ok(window.__errs.length === 0, '0 JS 报错（' + window.__errs.length + '）');
        o.push(''); o.push('失败数='+F); mkOut(o, F);
      }, 600);
    }, 16000);
  }, 900);
}, 2600);
""", budget=40000)

# ================================================================ ⑤ 老路径回归
print('\n=== ⑤ 老路径回归：等权限 / 打不开摄像头（r46 修的那条） ===')
run('perm', r"""
setTimeout(function(){
  var o=[], F=0;
  function ok(c,m){ o.push((c?'[OK ] ':'[FAIL] ')+m); if(!c) F++; }
  window.__om3Ensure = 'need_perm:android.permission.CAMERA';
  document.getElementById('tabCam').click();
  setTimeout(function(){
    fakeCam({vw:640, vh:480});        /* 故意不喂命中：浮层要一直开着，才验得出"自己开始扫" */
    window.__om3startScan();   /* 入口已隐藏（r49），直接驱动同一段扫码代码 */
    setTimeout(function(){
      var mk = document.getElementById('scanMask');
      ok(mk.classList.contains('hide'), '还没给权限 → 浮层不打开（不假装在扫）');
      var st = (document.getElementById('scanStat')||{}).textContent || '';
      ok(st.indexOf('等相机权限') >= 0, '诊断行写「等相机权限…」（实测「' + st + '」）');
      ok(window.__gum === 0, '没给权限前不调 getUserMedia（' + window.__gum + ' 次）');
      window.__om3Ensure = 'ok';               /* 真机上：批了权限之后 checkSelfPermission 就是 GRANTED */
      window.__om3camGranted('ok');            /* 用户在系统弹窗里点了「允许」 */
      setTimeout(function(){
        ok(!document.getElementById('scanMask').classList.contains('hide'), '给了权限 → **自己**开始扫（浮层开了）');
        ok(window.__gum === 1, 'getUserMedia 调了 1 次（' + window.__gum + '）');
        ok(window.__errs.length === 0, '0 JS 报错（' + window.__errs.length + '）');
        o.push(''); o.push('失败数='+F); mkOut(o, F);
      }, 1200);
    }, 900);
  }, 900);
}, 2600);
""")
run('gumfail', r"""
setTimeout(function(){
  var o=[], F=0;
  function ok(c,m){ o.push((c?'[OK ] ':'[FAIL] ')+m); if(!c) F++; }
  document.getElementById('tabCam').click();
  setTimeout(function(){
    fakeCam({reject:true});
    window.__om3startScan();   /* 入口已隐藏（r49），直接驱动同一段扫码代码 */
    setTimeout(function(){
      var so = (document.getElementById('scanOut')||{}).textContent || '';
      var lg = (document.getElementById('camOut3')||{}).textContent || '';
      ok(so.indexOf('打不开摄像头') >= 0, '打不开摄像头 → 浮层里明确写了原因（「' + so.slice(0,50) + '…」）');
      ok(lg.indexOf('打不开摄像头') >= 0, '这句也进了日志');
      ok(document.getElementById('scanMask').classList.contains('hide'), '失败后浮层收掉（不留个黑屏在那儿）');
      ok(window.__rejs.length === 0, '0 未处理拒绝（r46 修过的那条：' + window.__rejs.length + '）' + (window.__rejs[0] || ''));
      ok(window.__errs.length === 0, '0 JS 报错（' + window.__errs.length + '）');
      var st = (document.getElementById('scanStat')||{}).textContent || '';
      ok(st.indexOf('打不开摄像头') >= 0, '诊断行也留了一份（「' + st.slice(0, 40) + '…」）');
      o.push(''); o.push('失败数='+F); mkOut(o, F);
    }, 900);
  }, 900);
}, 2600);
""")

print()
print('===== 结论：%s（%d 项，失败 %d）=====' % ('全部通过 ✅' if F == 0 else '有 %d 项失败 ❌' % F, K, F))
sys.exit(1 if F else 0)
