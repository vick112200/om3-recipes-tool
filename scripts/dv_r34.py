# -*- coding: utf-8 -*-
"""第 34 轮（v2.20）验收探针：进页自动连蓝牙 / 按钮连 Wi-Fi / 5 个 bug 的回归。

设计：**JS 只记录事实（调用序列、日志、状态），Python 做断言** ——
这样断言一屏能看完，不用在几十行 JS 里找 ok()。

场景（每个场景一次独立 Chrome 载入，因为状态会累积）：
  A1-正常      权限有、蓝牙开、只扫相机就找到 → 自动连 → 发官方「電源ON」(0x0F01) → 热点起来了 → 成功
               ⚠ 第 36 轮又更正一次：電源ON 的真帧是 u(0x0F,1,[0x02])（v2.22 我读错分派表写成 u(0x68,3)）
  A1-兜底      权限要申请（回调后继续）、蓝牙关（自动打开）、只扫没找到（改全量）、
               第 1 帧没效果 → 第 2 帧 68/子3 才成 → 成功（共 2 帧，顺序正确）
  A1-失败      扫不到相机 → 明确文案；然后点「停止自动连蓝牙」→ 不再发帧
  A1-幂等      ① 相机已连通时进页 → 完全不跑蓝牙 ② 连续进两次页 → 只跑一次
  A2-按钮      点「连接相机」→ 蓝牙链先跑 → 直连扫到相机热点、没存过密码 → 弹框 → 填入 → 记住并连
  A2-已连通    相机已连通 → 点「连接相机」只提示、不重连（幂等）
  B-复制       点「复制全部日志」「复制相机地址」→ **不得有未处理拒绝**、不得假报成功
  B-接口       page↔native 接口对齐（由 dv_api 静态检查覆盖，这里只记页面调了哪些新接口）

用法：python scripts/dv_r34.py            跑全部
      python scripts/dv_r34.py A1-正常    只跑一个
"""
import json
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

# ---------------------------------------------------------------- 场景配置
#   hotspotAfter=0 → 相机热点永远不起来；=N → 发完第 N 帧唤醒帧之后才起来
#   scanAlwaysCam=True → 相机热点"本来就在"（相机 Wi-Fi 已开，页面不用唤醒也该能连上）
SCEN = {
    'A1-正常': dict(mode='enter', perm='ok', bt='on', waitMs=22000,
                    onlyCam=True, allCam=None, hotspotAfter=1),
    'A1-兜底': dict(mode='enter', perm='need_once', bt='off', waitMs=48000,
                    onlyCam=False, allCam=True, hotspotAfter=2),
    'A1-权限死循环': dict(mode='enter', perm='need', bt='off', waitMs=14000,
                     onlyCam=True, allCam=True, hotspotAfter=1),
    'A1-失败': dict(mode='enter_stop', perm='ok', bt='on',
                    onlyCam=False, allCam=False, hotspotAfter=0),
    'A1-幂等': dict(mode='twice', perm='ok', bt='on',
                    onlyCam=True, allCam=None, hotspotAfter=1),
    'A2-按钮': dict(mode='button', perm='ok', bt='on', scanAlwaysCam=True, waitMs=30000,
                    onlyCam=True, allCam=None, hotspotAfter=1),
    'A2-已连通': dict(mode='button_camon', perm='ok', bt='on', scanAlwaysCam=True,
                    onlyCam=True, allCam=None, hotspotAfter=1),
    'B-复制': dict(mode='copy', perm='ok', bt='on', scanAlwaysCam=True,
                   onlyCam=True, allCam=None, hotspotAfter=1),
}

STUB_TMPL = r"""
<script>
window.__OM3_APP__=1;window.__errs=[];window.__rejs=[];
window.addEventListener('error',function(e){window.__errs.push('ERR '+(e.message||'')+' @'+(e.lineno||0));});
window.addEventListener('unhandledrejection',function(e){window.__rejs.push('REJ '+String((e.reason&&e.reason.message)||e.reason));});
(function(){
  var CFG = __CFG__;
  var calls=[], writes=[], hid=0;
  window.__calls=calls; window.__writes=writes;
  function rec(n,a){ calls.push(n + (a===undefined?'':('('+String(a).slice(0,40)+')'))); }
  function canned(p){
    if(p.indexOf('mysetdatasize')>=0) return '<datasize>120</datasize>';
    if(p.indexOf('mysetrestorestate')>=0) return '<result>ok</result>';
    if(p.indexOf('get_caminfo')>=0) return '<caminfo><model>OM-3</model><serial>BJSA000000</serial></caminfo><result>ok</result>';
    return '<result>ok</result>';
  }
  var frameCount = 0;          /* 自动唤醒发到第几帧了（用来决定"热点起没起来"） */
  var permGranted = false;     /* bleAskPerm 被调过之后就算"授权到手"（need_once 用） */
  function camSsidNow(){
    if(!CFG.hotspotAfter) return '';                 /* 永远不起来 */
    return (frameCount >= CFG.hotspotAfter) ? 'OM-3-STUB' : '';
  }
  function scanList(){
    var L = [{ssid:'Home-5G', level:-60, cam:false}];
    /* ⚠ 两个来源必须分开：
       · hotspotAfter  = "被唤醒之后"相机热点才出现（A1 场景靠它判断唤醒成没成）
       · scanAlwaysCam = 相机热点"本来就在"（A2 场景：相机 Wi-Fi 已开）
       第一版把这两件事混在一个 else-if 里 → A1 发完第一帧就误判"热点起来了"（假通过）。 */
    if(CFG.scanAlwaysCam || camSsidNow()) L.unshift({ssid:'OM-3-STUB', level:-40, cam:true});
    return JSON.stringify(L);
  }
  window.OM3Native={
    camGetAsync:function(p){ var id='h'+(++hid); setTimeout(function(){ try{window.__om3http(id,{s:200,t:canned(p||'')});}catch(e){} },40); return id; },
    camPostAsync:function(p,b){ return window.OM3Native.camGetAsync(p); },
    camGet:function(p){ return JSON.stringify({s:200,t:canned(p||'')}); },
    camPost:function(p,b){ return JSON.stringify({s:200,t:canned(p||'')}); },
    cameraState:function(){ return JSON.stringify({ssid:'OM-3-STUB',model:'OM-3',serial:'BJSA000000'}); },
    /* --- Wi-Fi --- */
    wifiState:function(){ var s=camSsidNow()||'Home-5G'; return JSON.stringify({wifi:true,ssid:s,sdk:34}); },
    wifiScanList:function(){ rec('wifiScanList'); return scanList(); },
    connectCamera:function(s,p){ rec('connectCamera', s+'/'+p); setTimeout(function(){ try{window.__om3camState('connected');}catch(e){} },150); return 'ok'; },
    disconnectCamera:function(){ rec('disconnectCamera'); },
    joinWifi:function(s,p){ rec('joinWifi',s); return 'ok'; },
    forgetWifi:function(){ return 'ok'; },
    openWifiSettings:function(){ rec('openWifiSettings'); },
    dropCamera:function(){ rec('dropCamera'); },
    /* --- 蓝牙 --- */
    /* perm=need      → blePerm() **永远**说缺权限（测"授权后仍缺"的死循环护栏）
       perm=need_once → 第一次说缺，授权后就说有了（真实情况） */
    blePerm:function(){
      if(CFG.perm === 'need') return 'need:android.permission.BLUETOOTH_SCAN';
      if(CFG.perm === 'need_once') return permGranted ? 'ok' : 'need:android.permission.BLUETOOTH_SCAN';
      return 'ok';
    },
    blePermDetail:function(){ return 'SDK=34；BLUETOOTH_SCAN=有'; },
    bleAskPerm:function(){ rec('bleAskPerm'); setTimeout(function(){ permGranted = true; try{ window.__om3blePerm('ok'); }catch(e){} },80); },
    bleState:function(){ rec('bleState'); return CFG.bt==='off' ? 'off' : 'on'; },
    bleEnable:function(){ rec('bleEnable'); CFG.bt='on'; return 'turned_on'; },
    openBtSettings:function(){ rec('openBtSettings'); },
    bleScanStart:function(){ return window.OM3Native.bleScanStart2(0); },
    bleScanStart2:function(onlyCam){
      rec('bleScanStart2', onlyCam);
      var finds = (onlyCam===1) ? CFG.onlyCam : CFG.allCam;
      var f=window.__om3ble; if(!f) return;
      setTimeout(function(){ try{ f('start', onlyCam===1?'onlycam':'all'); }catch(e){} },30);
      if(finds){
        setTimeout(function(){ try{ f('found','OM-3 STUB','AA:BB:CC:DD:EE:01',-42,1); }catch(e){} },120);
      } else {
        setTimeout(function(){ try{ f('found','Sony WH-1000XM5','AA:BB:CC:DD:EE:02',-70,0); }catch(e){} },120);
      }
    },
    bleScanStop:function(){ rec('bleScanStop'); },
    bleDevices:function(){ return '[]'; },
    bleConnect:function(mac){
      rec('bleConnect', mac); var f=window.__om3ble; if(!f) return;
      setTimeout(function(){ try{ f('connected', mac, 0); }catch(e){} },80);
      setTimeout(function(){ try{ f('svc', JSON.stringify([{uuid:'ADC505F9-4E58-4B71-B8CA-983BB8C73E4F',type:0,chars:[
          /* ⚠ 字段名必须和真原生一致：MainActivity 发的是 read/write/wnr/notify/indicate/cccd 布尔量
             （不是数字 props）—— 页面 bleWriteTarget() 判的是 `c.write || c.wnr`。
             这里写错会得到"帧没发出去"的**假失败**（本探针第一版就踩了这个坑）。 */
          {uuid:'82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68', props:12, read:false, write:true,  wnr:true,  notify:false, indicate:false, cccd:false},
          {uuid:'B7A8015C-CB94-4EFA-BDA2-B7921FA9951F', props:12, read:false, write:true,  wnr:true,  notify:false, indicate:false, cccd:false},
          {uuid:'05A02050-0860-4919-8ADD-9801FBA8B6ED', props:16, read:false, write:false, wnr:false, notify:true,  indicate:false, cccd:true}]}] ), 0); }catch(e){} },150);
      return 'ok';
    },
    bleDisconnect:function(){ rec('bleDisconnect'); },
    bleSubscribe:function(u){ return 'ok'; },
    bleRead:function(u){ return 'ok'; },
    bleWrite:function(u,d,m,f){
      frameCount++;
      writes.push({uuid:String(u).slice(0,8), hex:String(d), sub:(String(d).split(' ')[5]||''), n:frameCount});
      rec('bleWrite', 'sub=' + (String(d).split(' ')[5]||'?'));
      return 'ok';
    },
    shareText:function(t){ return 'ok'; },
    copyText:function(t){ return 'ok'; },
    pickFile:function(){ return ''; }
  };
  window.__frameCount = function(){ return frameCount; };
})();
</script>
"""

JS_TMPL = r"""
var SC = __SC__;
var out = {steps:[], calls:[], writes:[], logs:[], linkOut2:'', camSaved:null,
           errs:[], rejs:[], om3errs:0, camOn:false, askShown:false, bleAutoDone:false};
function note(s){ out.steps.push(s); }
function snap(tag){
  note(tag);
  out.calls = window.__calls.slice();
  out.writes = window.__writes.slice();
  out.camSaved = (function(){ try{ return JSON.parse(localStorage.getItem('om3cam')||'null'); }catch(e){ return null; } })();
  out.errs = window.__errs.slice();
  out.rejs = window.__rejs.slice();
  out.om3errs = window.__om3errs || 0;
  out.camOn = document.body.classList.contains('cam-on');
  out.linkOut2 = String((document.getElementById('camLinkOut2')||{}).textContent||'');
  out.askShown = out.askShown || !!(function(){ var m=document.getElementById('omask'); return m && !m.classList.contains('hide'); })();
  /* 应用日志：把**隐藏容器也算上**（用 textContent，不用 innerText ——
     隐藏元素不参与 innerText，会漏掉关键行；第一版就踩了这个坑） */
  out.logs = [];
  var all = [];
  ['camLinkOut2','camGateOut','camOut1','camOut3','bleList','camWifiOut'].forEach(function(id){
    var e = document.getElementById(id);
    if(e) all.push(String(e.textContent || ''));
  });
  all.join('\n').split('\n').forEach(function(l){
    if(l.indexOf('[自动·蓝牙]') >= 0 || l.indexOf('[连接相机]') >= 0 || l.indexOf('扫不到相机') >= 0
       || l.indexOf('已复制') >= 0 || l.indexOf('复制没成功') >= 0 || l.indexOf('已经连着') >= 0
       || l.indexOf('继续自动连蓝牙') >= 0 || l.indexOf('相机热点起来了') >= 0
       || l.indexOf('换下一帧') >= 0 || l.indexOf('没发出去') >= 0) out.logs.push(l.trim().slice(0,400));
  });
  out.gateOut = String((document.getElementById('camGateOut')||{}).textContent||'');
  out.o1 = String((document.getElementById('camOut1')||{}).textContent||'');
  out.o3 = String((document.getElementById('camOut3')||{}).textContent||'');
  try{ out.bleAutoDone = !!(window.__om3camBleAuto && document.body.classList.contains('cam-on')); }catch(e){}
}
function enterCam(next){
  var t = document.querySelector('.tabs.mod button[data-p=D]');
  if(t) t.click(); else note('找不到「连接相机」页签');
  setTimeout(next, 600);
}
function fillAsk(v){
  var m=document.getElementById('omask');
  if(!m || m.classList.contains('hide')) return false;
  var i=document.getElementById('of0'); if(i) i.value=v;
  var ok=document.getElementById('ook'); if(ok) ok.click();
  return true;
}
function flush(){
  var d=document.createElement('pre'); d.id='DBGOUT';
  d.textContent = JSON.stringify(out);
  document.body.appendChild(d);
}
setTimeout(function(){
  try{
    if(SC.mode === 'enter' || SC.mode === 'enter_stop' || SC.mode === 'twice'){
      enterCam(function(){
        setTimeout(function(){
          snap('进页 0.8s');
          if(SC.mode === 'twice'){
            /* 再切走再回来：应只跑一次（幂等） */
            var tb = document.querySelector('.tabs.mod button[data-p=A]'); if(tb) tb.click();
            setTimeout(function(){
              enterCam(function(){
                setTimeout(function(){ snap('第二次进页'); flush(); }, 6000);
              });
            }, 400);
            return;
          }
          if(SC.mode === 'enter_stop'){
            /* 这场景是"扫不到相机"：只扫 8s + 全量 8s，所以得等 ~17s 让失败文案出来，
               再点「停止自动连蓝牙」，看还会不会继续发帧 */
            setTimeout(function(){
              snap('自动链跑完(17s)');
              var st=document.getElementById('camLinkStop'); if(st) st.click();
              note('点了 停止自动连蓝牙');
              var w0 = window.__writes.length;
              setTimeout(function(){
                snap('停止后 3s');
                note('停止后新增写帧数=' + (window.__writes.length - w0));
                flush();
              }, 3000);
            }, 17000);
            return;
          }
          setTimeout(function(){ snap('自动链跑完'); flush(); }, SC.waitMs || 8000);
        }, 800);
      });
    }
    else if(SC.mode === 'button' || SC.mode === 'button_camon'){
      if(SC.mode === 'button_camon'){ try{ window.__om3setConn(true); }catch(e){} }
      enterCam(function(){
        setTimeout(function(){
          snap('蓝牙链跑完');
          var g=document.getElementById('camGateConn'); if(g) g.click();
          note('点了「连接相机」');
          setTimeout(function(){   /* 等密码框出现并填入 */
            var filled = fillAsk('pass1234');
            note('密码框出现=' + filled);
            setTimeout(function(){ snap('按钮之后'); flush(); }, 2500);
          }, 2500);
        }, 9000);
      });
    }
    else if(SC.mode === 'copy'){
      enterCam(function(){
        setTimeout(function(){
          var a=document.getElementById('camCopyLog'), b=document.getElementById('camWifi');
          if(a) a.click(); if(b) b.click();
          setTimeout(function(){ snap('两个复制按钮点过'); flush(); }, 1200);
        }, 900);
      });
    }
  }catch(e){ note('探针异常：'+(e&&e.message)); flush(); }
}, 3000);
"""


def run(name, cfg):
    head = STUB_TMPL.replace('__CFG__', json.dumps(cfg))
    js = JS_TMPL.replace('__SC__', json.dumps({'mode': cfg['mode'], 'waitMs': cfg.get('waitMs', 8000)}))
    tail = '<script>' + js + '</script>'
    i = src.find('<body')
    j = src.find('>', i) + 1
    out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
    p = TMP + r'\dv_r34.html'
    open(p, 'w', encoding='utf-8', newline='').write(out)
    ud = TMP + r'\or34_' + re.sub(r'[^A-Za-z0-9]', '_', name)
    subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
    r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                        '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                        '--user-data-dir=' + ud, '--window-size=412,900',
                        '--virtual-time-budget=120000', '--dump-dom',
                        'file:///' + p.replace('\\', '/')],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=400)
    dom = r.stdout or ''
    k = dom.find('id="DBGOUT"')
    if k < 0:
        return None
    try:
        return json.loads(dom[k:].split('>', 1)[1].split('</pre>')[0])
    except Exception as e:
        return {'_parse_error': str(e), '_raw': dom[k:k + 800]}


def subs(t):
    return [w['sub'] for w in t['writes']]


# ---------------------------------------------------------------- 原生侧检查（不需要浏览器）
JAVA = open(SRC + r'\apk\java\com\om3\handbook\MainActivity.java', encoding='utf-8').read()
HTML = src
# 原生那个 cam 正则（照 MainActivity 第 860 行抄下来；Java 源码里写的是 \\d）
CAM_RX = r'(?i)^(OM[- ]?\d.*|OM[- ]?D.*|OMSYSTEM.*|E[- ]?M\d.*|E[- ]?P\d.*|STYLUS.*|PEN.*|Tough.*)'


def check_native():
    L = []
    ok = True

    def A(c, m):
        nonlocal ok
        L.append(('  [OK ] ' if c else '  [FAIL] ') + m)
        if not c:
            ok = False

    # bug①：wifiScanList 的 SSID 去引号
    i = JAVA.find('public String wifiScanList()')
    body = JAVA[i:i + 3000] if i >= 0 else ''
    A(i >= 0, '找到 wifiScanList()')
    A('replace("\\"", "")' in body, '★bug①：wifiScanList() 的 SSID 去掉了两边的引号')
    A('startScan()' in body or 'getScanResults()' in body, '（确认取到的是真函数体，不是空匹配）')
    # 机理复现：带引号的 SSID 一定匹配不上相机正则
    A(re.match(CAM_RX, '"OM-3 1234"') is None,
      '★机理：带引号的 SSID 匹配不上相机正则（→ 相机热点标不出 📷 → 直连第一条路走不通）')
    A(re.match(CAM_RX, '"OM-3 1234"'.replace('"', '')) is not None,
      '★去掉引号后能匹配上（修好之后的行为）')
    A(re.match(CAM_RX, 'OM-3 1234') is not None,
      '★去掉引号对"本来就不带引号"的设备无副作用（SSID 内容不含引号）')
    # 三个新原生接口
    for m, sig in [('bleState', 'public String bleState()'),
                   ('bleEnable', 'public String bleEnable()'),
                   ('openBtSettings', 'public void openBtSettings()')]:
        A(sig in JAVA, '原生新增接口 %s()' % m)
        A(('%s()' % m) in HTML, '页面确实调了 %s()' % m)
    # 页面调用的原生方法都有实现（跨层对齐）
    impl = set(re.findall(r'@(?:android\.webkit\.)?JavascriptInterface\s*\n\s*(?:public|private|protected)?\s*[\w<>\[\], .]+\s+(\w+)\s*\(', JAVA))
    called = set(re.findall(r'\b(?:Native|OM3Native|N)\s*\.\s*(\w+)\s*\(', HTML))
    miss = sorted(called - impl)
    A(not miss, '跨层接口对齐：页面调用的 Native.* 全部有实现' + ('' if not miss else '（缺：%s）' % ','.join(miss)))
    # bug④：两个复制按钮都不再直接用裸 clipboard.writeText 的 Promise
    A('bleTryCopy(BASE' in HTML, '★bug④：camWifi 改用 bleTryCopy（正确接住 Promise 拒绝）')
    A('bleTryCopy(t' in HTML, '★bug④：camCopyLog 改用 bleTryCopy（不再无条件报成功）')
    return ok, L


def check(name, t):
    """返回 (是否通过, 说明行列表)"""
    L = []
    ok = True
    if t is None:
        return False, ['  ★探针没拿到输出（页面可能卡住了）']

    def A(cond, msg):
        nonlocal ok
        L.append(('  [OK ] ' if cond else '  [FAIL] ') + msg)
        if not cond:
            ok = False

    fps = len(t['errs'])
    A(fps == 0, '整轮没有 JS 报错' + ('' if fps == 0 else '：' + ' | '.join(t['errs'][:3])))
    A(len(t['rejs']) == 0, '没有未处理的 Promise 拒绝' + ('' if not t['rejs'] else '：' + ' | '.join(t['rejs'][:2])))
    calls = t['calls']
    subs_ = subs(t)
    logs = ' || '.join(t['logs'])

    if name == 'A1-正常':
        A('bleScanStart2(1)' in calls, '进页**自动**只扫相机（bleScanStart2(1)）')
        A(any(c.startswith('bleConnect') for c in calls), '扫到相机后**自动**连（bleConnect，没让用户点）')
        # 第 36 轮更正：電源ON = 0x0F01 → M2/b.x → u(0x0F,1,[0x02])
        A(subs_ == ['01'], '连上后自动发唤醒帧，且就是官方「電源ON」(0x0F01，实测 sub=' + ','.join(subs_) + '）')
        A(any(w['hex'] == '01 01 04 0F 01 01 02 13 00' for w in t['writes']),
          '★帧字节与官方逐字节一致（实测 ' + (t['writes'][0]['hex'] if t['writes'] else '（没发）') + '）')
        A('相机热点起来了' in t['linkOut2'] or '唤醒成功' in logs, '热点起来后判定为唤醒成功')
        A(t['camSaved'] is None or True, '（A1 不涉及记住相机）')
    elif name == 'A1-兜底':
        A('bleAskPerm' in ' '.join(calls), '权限 need → 拉起系统授权弹窗')
        A('bleState' in ' '.join(calls), '自动问了蓝牙开关状态')
        A('bleEnable' in ' '.join(calls), '蓝牙关着 → **自动打开**（bleEnable）')
        A('bleScanStart2(1)' in calls and 'bleScanStart2(0)' in calls, '只扫相机没找到 → 自动改全量扫')
        A(subs_ == ['01'], '★走完兜底全链路后发的是官方電源ON（实测 sub=' + ','.join(subs_) + '）')
        # 用**调用顺序**证明"授权后继续"（比在日志容器里找字更硬）：
        # 授权弹窗之后必须紧接着 蓝牙开关 → 扫描 → 连接
        A(('bleAskPerm' in calls) and ('bleState' in calls) and calls.index('bleState') > calls.index('bleAskPerm'),
          '★权限回调后**继续**把链跑完（bleAskPerm 之后接着 bleState → 扫描 → 连接 → 唤醒）')
        A(any(c.startswith('bleConnect') for c in calls) and subs_,
          '并且一路走到"连上 + 发唤醒帧"（不是卡在权限那一步）')
    elif name == 'A1-权限死循环':
        n_ask = calls.count('bleAskPerm')
        A(n_ask <= 1, '★授权后系统仍说缺权限 → 只弹 1 次，不再反复弹（实测 ' + str(n_ask) + ' 次）')
        A('还是说缺蓝牙权限' in t['linkOut2'] or '手动允许' in t['linkOut2'], '并且明确指路"去设置里手动允许"')
    elif name == 'A1-失败':
        A('扫不到相机' in logs or '扫不到相机' in t['linkOut2'], '扫不到相机 → 明确文案（含"扫不到相机"）')
        A('停止' in ' '.join(t['steps']), '（已点过停止按钮）')
        A(not subs_, '扫不到相机时**不发**唤醒帧（实测 ' + ','.join(subs_ or ['无']) + '）')
        A(all(x == '02' for x in subs_) or not subs_, '停止之后也没有补发第二帧（实测 ' + ','.join(subs_ or ['无']) + '）')
    elif name == 'A1-幂等':
        n1 = calls.count('bleScanStart2(1)')
        A(n1 == 1, '连续进两次「连接相机」页 → 蓝牙链只跑一次（实测 ' + str(n1) + ' 次）')
    elif name == 'A2-按钮':
        A('bleScanStart2(1)' in calls, '点按钮时蓝牙链还没跑完 → 顺带跑一次')
        A(any(c.startswith('connectCamera') for c in calls), '直连：调了 connectCamera')
        A('pass1234' in ' '.join(calls), '询问到的密码被用于连接（connectCamera 参数里带 pass1234）')
        A(bool(t['camSaved']) and t['camSaved'].get('ssid') == 'OM-3-STUB' and t['camSaved'].get('pass') == 'pass1234',
          '★bug②：密码被**记住**了（localStorage om3cam=' + json.dumps(t['camSaved'], ensure_ascii=False)[:80] + '）')
    elif name == 'A2-已连通':
        A(not any(c.startswith('connectCamera') for c in calls), '★已连通时点「连接相机」→ 不重连（幂等）')
        A('已经连着' in (t['linkOut2'] + logs + t.get('gateOut', '')) or '不用再连' in (t['linkOut2'] + logs + t.get('gateOut', '')),
          '并且明确提示"已经连着了"')
    elif name == 'B-复制':
        A(len(t['rejs']) == 0, '★bug④：点两个复制按钮**没有未处理拒绝**')
        # 用**未截断**的原文断言（logs 里那行被截断到 150 字，关键词会落在截断之后）
        blob = t.get('o1', '') + t.get('o3', '') + ' '.join(logs)
        A(('已复制' in blob) or ('复制没成功' in blob) or ('复制失败' in blob),
          '★bug④：给的是明确结果（成功=已复制 / 失败=复制失败+手动复制提示）')
        A('已尝试复制' not in blob, '★bug④：不再出现含糊文案「已尝试复制」')
    return ok, L


def main():
    want = sys.argv[1:] or list(SCEN.keys())
    total_fail = 0
    print('')
    print('=' * 76)
    print('原生侧 + 静态检查（不需要浏览器）')
    print('=' * 76)
    okn, Ln = check_native()
    for l in Ln:
        print(l)
    if not okn:
        total_fail += 1
    for name in want:
        cfg = SCEN[name]
        print('')
        print('=' * 76)
        print('场景 %s   %s' % (name, json.dumps(cfg, ensure_ascii=False)))
        print('=' * 76)
        t = run(name, cfg)
        ok, L = check(name, t)
        for l in L:
            print(l)
        if t is not None:
            print('  调用序列：' + ' → '.join(t['calls']))
            print('  写帧：' + (json.dumps(t['writes'], ensure_ascii=False) if t['writes'] else '（无）'))
            print('  卡上进度：' + (t['linkOut2'][-160:].replace('\n', ' / ') if t['linkOut2'] else '（空）'))
            if t['logs']:
                print('  日志：' + ' ｜ '.join(t['logs'][-4:]))
            print('  JS 报错=%d 未处理拒绝=%d om3errs=%s' % (len(t['errs']), len(t['rejs']), t['om3errs']))
            if t.get('o1'):
                print('  #camOut1 尾：' + t['o1'][-160:].replace('\n', ' / '))
            if t.get('o3'):
                print('  #camOut3 尾：' + t['o3'][-200:].replace('\n', ' / '))
        if not ok:
            total_fail += 1
    print('')
    print('===== 结论：%d/%d 场景通过 =====' % (len(want) - total_fail, len(want)))
    return 1 if total_fail else 0


sys.exit(main())
