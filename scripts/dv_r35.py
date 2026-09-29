# -*- coding: utf-8 -*-
"""第 35 轮（v2.22）验收探针：**帧校验和修正**（真机"发得出去、相机不理"的根因）+ 等应答 + 连接重试 + 卡片结构。

设计同 dv_r34：**JS 只记录事实，Python 做断言**。

场景：
  帧字节      连上后自动发的**第一帧必须是官方「電源ON」**：01 01 03 68 01 03 6C 00
  等应答      相机回一帧（校验正确）→ 日志出现"相机回帧…校验 OK"，进度出现"✅ 相机收下了"
  应答校验错  相机回的帧校验不对 → 日志出现"校验 ✗"（说明解码器在真算，不是硬编码"OK"）
  连接重试    第一次连接不返回 connected → 自动再试一次 → 第二次连上并继续发帧
  按钮        点「用蓝牙唤醒相机」→ 也走同一条（再发一次 01 03 03 68 01 03 6C 00）
  卡片结构    #camLinkCard 折叠外只留 1 个按钮；4 个 id 都在且都能点（0 报错）
  静态        源码 bleBuildFrame 里校验和种子必须是 ch + 1 + sub（防回归）

用法：python scripts/dv_r35.py            跑全部
      python scripts/dv_r35.py 帧字节      只跑一个
"""
import json
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

# 官方逐字节钉死的两帧（空载荷）
# 第 36 轮更正：電源ON 的真实帧 = M2/b.x() → u(0x0F,1,[0x02])，校验 0x0F+1+0x01+0x02 = 0x13
F_POWER = '01 01 04 0F 01 01 02 13 00'
# 口令认证 = M2/b.i(口令) → u(0x0C,2,UTF8('1234'))，校验 0x0C+1+0x02+0x31+0x32+0x33+0x34 = 0xD9
F_PASS1 = '01 01 07 0C 01 02 31 32 33 34 D9 00'
F_POWER2 = '01 02 04 0F 01 01 02 13 00'   # 口令认证之后那一帧（序号 +1）

SCEN = {
    '帧字节':   dict(mode='wake', perm='ok', bt='on', hotspotAfter=1, ack=None),
    '口令认证': dict(mode='wake', perm='ok', bt='on', hotspotAfter=1, ack='echo', pass_='1234', waitMs=20000),
    '等应答':   dict(mode='wake', perm='ok', bt='on', hotspotAfter=1, ack='echo'),
    '应答校验错': dict(mode='wake', perm='ok', bt='on', hotspotAfter=0, ack='badsome', waitMs=26000),
    '连接重试': dict(mode='wake', perm='ok', bt='on', hotspotAfter=1, ack='echo', connFailFirst=True,
                  waitMs=37000),
    '按钮':     dict(mode='wake_then_button', perm='ok', bt='on', hotspotAfter=1, ack='echo', waitMs=26000),
    '卡片结构': dict(mode='card', perm='ok', bt='on', hotspotAfter=1, ack=None),
    '重复唤醒': dict(mode='double_wake', perm='ok', bt='on', hotspotAfter=1, ack=None, waitMs=22000),
}

STUB_TMPL = r"""
<script>
window.__OM3_APP__=1;window.__errs=[];window.__rejs=[];
window.addEventListener('error',function(e){ try{window.__errs.push(String(e.message));}catch(x){} });
window.addEventListener('unhandledrejection',function(e){ try{window.__rejs.push(String(e.reason&&e.reason.message||e.reason));}catch(x){} });
(function(){
  var CFG = __CFG__;
  var calls=[], writes=[], hid=0, connTries=0;
  window.__calls=calls; window.__writes=writes;
  function rec(n,a){ calls.push(n + (a===undefined?'':('('+String(a).slice(0,40)+')'))); }
  function canned(p){
    if(p.indexOf('get_caminfo')>=0) return '<caminfo><model>OM-3</model><serial>BJSA21721</serial></caminfo><result>ok</result>';
    return '<result>ok</result>';
  }
  var frameCount = 0;
  function camSsidNow(){ if(!CFG.hotspotAfter) return ''; return (frameCount >= CFG.hotspotAfter) ? 'OM-3-STUB' : ''; }
  function scanList(){
    var L = [{ssid:'Home-5G', level:-60, cam:false}];
    if(camSsidNow()) L.unshift({ssid:'OM-3-STUB', level:-40, cam:true});
    return JSON.stringify(L);
  }
  /* 相机回帧：echo = 把刚发的那帧原样回（校验正确）；badsome = 故意改坏校验 */
  function replyTo(hex){
    if(!CFG.ack) return;
    var h = String(hex);
    if(CFG.ack === 'badsome'){
      var a = h.split(' ');
      a[a.length - 2] = '00';                 /* 把校验位改坏 */
      h = a.join(' ');
    }
    setTimeout(function(){
      try{ window.__om3ble('notify','05A02050-0860-4919-8ADD-9801FBA8B6ED', h, ''); }catch(e){}
    }, 150);
  }
  window.OM3Native={
    camGetAsync:function(p){ var id='h'+(++hid); setTimeout(function(){ try{window.__om3http(id,{s:200,t:canned(p||'')});}catch(e){} },40); return id; },
    camPostAsync:function(p,b){ return window.OM3Native.camGetAsync(p); },
    camGet:function(p){ return JSON.stringify({s:200,t:canned(p||'')}); },
    camPost:function(p,b){ return JSON.stringify({s:200,t:canned(p||'')}); },
    cameraState:function(){ return JSON.stringify({ssid:'OM-3-STUB',model:'OM-3',serial:'BJSA21721'}); },
    wifiState:function(){ var s=camSsidNow()||'Home-5G'; return JSON.stringify({wifi:true,ssid:s,sdk:34}); },
    wifiScanList:function(){ rec('wifiScanList'); return scanList(); },
    connectCamera:function(s,p){ rec('connectCamera'); setTimeout(function(){ try{window.__om3camState('connected');}catch(e){} },150); return 'ok'; },
    disconnectCamera:function(){ rec('disconnectCamera'); },
    joinWifi:function(s,p){ return 'ok'; }, forgetWifi:function(){ return 'ok'; },
    openWifiSettings:function(){}, dropCamera:function(){},
    blePerm:function(){ return 'ok'; },
    blePermDetail:function(){ return 'SDK=34'; },
    bleAskPerm:function(){ rec('bleAskPerm'); },
    bleState:function(){ rec('bleState'); return 'on'; },
    bleEnable:function(){ rec('bleEnable'); return 'already'; },
    openBtSettings:function(){ rec('openBtSettings'); },
    bleScanStart:function(){ return window.OM3Native.bleScanStart2(0); },
    bleScanStart2:function(onlyCam){
      rec('bleScanStart2', onlyCam);
      var f=window.__om3ble; if(!f) return;
      setTimeout(function(){ try{ f('start', onlyCam===1?'onlycam':'all'); }catch(e){} },30);
      setTimeout(function(){ try{ f('found','BJSA21721','34:90:EA:BE:07:F9',-42,1); }catch(e){} },120);
    },
    bleScanStop:function(){ rec('bleScanStop'); },
    bleDevices:function(){ return '[]'; },
    bleConnect:function(mac){
      connTries++; rec('bleConnect', mac);
      var f=window.__om3ble; if(!f) return;
      /* connFailFirst：第一次"连上但相机不回状态"（真机现象），第二次才成 */
      if(CFG.connFailFirst && connTries === 1){
        setTimeout(function(){ try{ f('connecting', mac); }catch(e){} }, 50);
        return 'ok';
      }
      setTimeout(function(){ try{ f('connected', mac, 0); }catch(e){} },80);
      setTimeout(function(){ try{ f('svc', JSON.stringify([{uuid:'ADC505F9-4E58-4B71-B8CA-983BB8C73E4F',type:0,chars:[
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
      writes.push({hex:String(d), sub:(String(d).split(' ')[5]||''), n:frameCount});
      rec('bleWrite', 'sub=' + (String(d).split(' ')[5]||'?'));
      replyTo(d);
      return 'ok';
    },
    shareText:function(t){ return 'ok'; },
    copyText:function(t){ return 'ok'; },
    pickFile:function(){ return ''; }
  };
  window.__connTries = function(){ return connTries; };
})();
</script>
"""

JS_TMPL = r"""
var SC = __SC__;
/* 第 36 轮：口令场景 —— 进页面前先把口令写进 localStorage（页面读的是 om3blepass） */
try{
  if(SC.pass_) localStorage.setItem('om3blepass', String(SC.pass_));
  else localStorage.removeItem('om3blepass');
}catch(e){}
var out = {steps:[], calls:[], writes:[], bleLog:'', linkOut2:'', errs:[], rejs:[], om3errs:0, card:null, notes:[]};
function note(s){ out.steps.push(s); }
function txt(id){ var e=document.getElementById(id); return e ? String(e.textContent||'') : ''; }
function flush(){
  out.calls = (window.__calls||[]).slice();
  out.writes = (window.__writes||[]).slice();
  out.bleLog = txt('bleList');
  out.linkOut2 = txt('camLinkOut2');
  out.linkOut = txt('camLinkOut');
  out.errs = window.__errs||[]; out.rejs = window.__rejs||[];
  out.om3errs = window.__om3errs||0;
  out.connTries = (window.__connTries ? window.__connTries() : 0);
  try{
    var c = document.getElementById('camLinkCard');
    if(c){
      var direct = c.querySelectorAll(':scope > button').length;
      var fold = c.querySelectorAll(':scope > details button').length;
      var ids = ['camLinkWake','camLinkRecheck','camLinkStop','camLinkBtSet'];
      var have = {};
      ids.forEach(function(id){ have[id] = !!document.getElementById(id); });
      out.card = {direct: direct, inFold: fold, ids: have,
                  hasPass: !!document.getElementById('blePassIn'),
                  head: (c.querySelector('.camhd')||{}).textContent || '',
                  det: c.querySelectorAll(':scope > details').length};
    }
  }catch(e){ note('卡片结构读不到：'+e.message); }
  var d = document.createElement('pre'); d.id='DBGOUT';
  d.textContent = JSON.stringify(out);
  document.body.appendChild(d);
}
function enterCam(next){
  var t = document.querySelector('.tabs.mod button[data-p=D]');
  if(t) t.click(); else note('找不到「连接相机」页签');
  setTimeout(next, 800);
}
setTimeout(function(){
  try{
    if(SC.mode === 'card'){
      /* 只读结构 + 把 4 个按钮都点一遍（0 报错就算过） */
      enterCam(function(){
        ['camLinkRecheck','camLinkStop','camLinkBtSet','camLinkWake'].forEach(function(id){
          var b = document.getElementById(id);
          if(b){ try{ b.click(); note('点了 #'+id); }catch(e){ note('点 #'+id+' 异常：'+e.message); } }
          else note('缺 #'+id);
        });
        setTimeout(function(){ flush(); }, 2500);
      });
      return;
    }
    if(SC.mode === 'double_wake'){
      /* 真机那个 bug 的回归：自动链正在唤醒时再点两次按钮 → 不能再发一遍帧 */
      enterCam(function(){
        var w = document.getElementById('camLinkWake');
        setTimeout(function(){ if(w){ w.click(); note('第 1 次点唤醒'); } }, 1200);
        setTimeout(function(){ if(w){ w.click(); note('第 2 次点唤醒'); } }, 1400);
        setTimeout(function(){ note('等自动链跑完'); flush(); }, SC.waitMs || 20000);
      });
      return;
    }
    enterCam(function(){
      setTimeout(function(){
        note('自动链跑完');
        if(SC.mode === 'wake_then_button'){
          var w = document.getElementById('camLinkWake');
          if(w){ try{ w.click(); note('点了「用蓝牙唤醒相机」'); }catch(e){ note('点唤醒异常：'+e.message); } }
          else note('找不到 #camLinkWake');
          setTimeout(function(){ note('按钮后再等 8s'); flush(); }, 8000);
          return;
        }
        flush();
      }, SC.waitMs || 10000);
    });
  }catch(e){ note('探针异常：'+(e&&e.message)); flush(); }
}, 3000);
"""


def run(name, cfg):
    head = STUB_TMPL.replace('__CFG__', json.dumps(cfg))
    js = JS_TMPL.replace('__SC__', json.dumps({'mode': cfg['mode'], 'waitMs': cfg.get('waitMs', 10000), 'pass_': cfg.get('pass_')}))
    tail = '<script>' + js + '</script>'
    i = src.find('<body')
    j = src.find('>', i) + 1
    out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
    p = TMP + r'\dv_r35.html'
    open(p, 'w', encoding='utf-8', newline='').write(out)
    ud = TMP + r'\or35_' + re.sub(r'[^A-Za-z0-9]', '_', name)
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


def hexes(t):
    return [w['hex'] for w in t['writes']]


def check_source():
    """静态：校验和种子必须是 ch + 1 + sub（防回归）。"""
    L = []
    ok = True

    def A(c, m):
        nonlocal ok
        L.append(('  [OK ] ' if c else '  [FAIL] ') + m)
        if not c:
            ok = False

    i = src.find('function bleBuildFrame')
    body = src[i:i + 700] if i >= 0 else ''
    A(i >= 0, '找到 bleBuildFrame()')
    A('(ch & 0xFF) + 1 + (sub & 0xFF)' in body, '★校验和种子 = ch + 1 + sub（官方 M2.b.u）')
    A('+ 3 + (sub' not in body, '★不再有旧的 "+ 3 +" 写法')
    A('(n + 3) & 0xFF' in body, '长度字段仍是 数据长 + 3（这条没改错）')
    return ok, L


def check(name, t):
    L = []
    ok = True

    def A(c, m):
        nonlocal ok
        L.append(('  [OK ] ' if c else '  [FAIL] ') + m)
        if not c:
            ok = False

    if t is None or '_parse_error' in t:
        return False, ['  [FAIL] 探针没拿到结果：' + json.dumps(t, ensure_ascii=False)[:200]]

    calls = t['calls']
    hx = hexes(t)
    blob = t['bleLog'] + ' ' + t['linkOut2']

    A(len(t['errs']) == 0, '整轮没有 JS 报错' + ('' if not t['errs'] else '：' + str(t['errs'][:2])))
    A(len(t['rejs']) == 0, '没有未处理的 Promise 拒绝' + ('' if not t['rejs'] else '：' + str(t['rejs'][:2])))

    if name == '帧字节':
        A(hx and hx[0] == F_POWER,
          '★第一帧就是官方「電源ON」逐字节一致：' + (hx[0] if hx else '（没发）') + '（应 ' + F_POWER + '）')
        A(len(hx) == 1, '口令没设 → 只发 電源ON 这一帧（实测 ' + str(len(hx)) + ' 帧）')
    elif name == '口令认证':
        A(hx and hx[0] == F_PASS1,
          '★第 1 帧 = パスコード認証（UTF-8 口令）逐字节一致：' + (hx[0] if hx else '（没发）') + '（应 ' + F_PASS1 + '）')
        A(len(hx) >= 2 and hx[1] == F_POWER2,
          '★第 2 帧才是 電源ON（序号 +1）：' + (hx[1] if len(hx) > 1 else '（没发）') + '（应 ' + F_POWER2 + '）')
        A('パスコード認証' in t['linkOut2'], '进度里写了"パスコード認証"')
        A('已记住相机蓝牙口令' in t['bleLog'] or '口令' in t['linkOut'], '状态/日志里提到口令已设置')
    elif name == '等应答':
        A(hx and hx[0] == F_POWER, '第一帧是電源ON')
        A('相机回帧' in blob, '★日志里有解码后的"相机回帧"')
        A('校验 OK' in blob, '★解码结果：校验 OK')
        A('相机收下了' in blob, '★进度里明确写"相机收下了"（不再只靠热点猜）')
    elif name == '应答校验错':
        A(hx and hx[0] == F_POWER, '第一帧是電源ON')
        A('校验 ✗' in blob, '★相机回帧校验不对时**如实报 ✗**（不是硬编码 OK）')
        A(len(hx) == 1, '（本轮只有 電源ON 一帧要发，实测 ' + str(len(hx)) + '）')
    elif name == '连接重试':
        n = calls.count('bleConnect(34:90:EA:BE:07:F9)')
        A(n == 2, '★第一次连接超时 → 自动重试（bleConnect 实测 ' + str(n) + ' 次）')
        A('自动再试一次' in t['linkOut2'], '★进度里写了"自动再试一次"')
        A('第 2 次' in t['linkOut2'], '进度里标了第几次连接')
        A(hx and hx[0] == F_POWER, '重试连上后照样发第一帧電源ON')
    elif name == '按钮':
        A(hx and hx[0] == F_POWER, '自动链第一帧是電源ON')
        A('点了「用蓝牙唤醒相机」' in ' '.join(t['steps']), '（已点按钮）')
        A(len(hx) >= 2, '点按钮后又发了帧（实测共 ' + str(len(hx)) + ' 帧）')
        A(all(h.endswith('04 0F 01 01 02 13 00') for h in hx[1:]),
          '★手动按钮发的也是官方電源ON帧（实测 ' + ' | '.join(hx[1:]) + '）')
    elif name == '重复唤醒':
        pw = [h for h in hx if h.endswith('04 0F 01 01 02 13 00')]
        A(len(pw) == 1, '★按钮点两次也没重复发電源ON（实测 ' + str(len(pw)) + ' 帧）')
        A('不重复发' in t['linkOut2'] or '不重复发' in t['bleLog'], '★并且明确说了唤醒已经在跑了，不重复发')
        A('第 1 次点唤醒' in ' '.join(t['steps']) and '第 2 次点唤醒' in ' '.join(t['steps']), '（两次点击确实发生了）')
    elif name == '卡片结构':
        c = t['card']
        A(bool(c), '读到 #camLinkCard')
        if c:
            A(c['direct'] == 1, '★折叠外**只剩 1 个按钮**（实测 ' + str(c['direct']) + '）')
            A(c['det'] >= 1, '有折叠（details=' + str(c['det']) + '）')
            A(c['inFold'] >= 3, '折叠里有 3 个原有按钮 + 口令那几个（实测 ' + str(c['inFold']) + '）')
            A(all(c['ids'].values()), '原 4 个 id 一个没删：' + json.dumps(c['ids'], ensure_ascii=False))
            A('蓝牙' in c['head'], '标题写清了这张卡只管蓝牙：' + c['head'])
            A(c.get('hasPass') is True, '折叠里确实有口令输入框 #blePassIn')
        A(len(t['errs']) == 0, '把按钮都点一遍 → 0 报错')
    return ok, L


def main():
    want = sys.argv[1:] or list(SCEN.keys())
    total = 0
    print('')
    print('=' * 76)
    print('静态检查：bleBuildFrame 的校验和种子')
    print('=' * 76)
    oks, Ls = check_source()
    for l in Ls:
        print(l)
    if not oks:
        total += 1
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
        if t and '_parse_error' not in t:
            print('  调用序列：' + ' → '.join(t['calls'][:14]))
            print('  发帧：' + (json.dumps(t['writes'], ensure_ascii=False) if t['writes'] else '（无）'))
            if t.get('linkOut2'):
                print('  卡上进度：' + t['linkOut2'][-260:].replace('\n', ' / '))
            print('  JS 报错=%d 未处理拒绝=%d om3errs=%s' % (len(t['errs']), len(t['rejs']), t['om3errs']))
        if not ok:
            total += 1
    print('')
    print('===== 结论：%d/%d 场景通过 =====' % (len(want) - total, len(want)))
    return 1 if total else 0


sys.exit(main())
