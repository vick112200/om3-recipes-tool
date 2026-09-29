# -*- coding: utf-8 -*-
"""全站破坏性扫描：把每个页签里的**每个按钮都点一遍**，抓运行时异常 / 未处理拒绝 / 卡住的弹窗。

为什么这么做：用户口径"再检查下有没有 bug" —— 静态审计（audit_all / audit_code）只能看结构，
真正"点了就炸"的问题只有点一遍才现形。本脚本就是干这个的。

原生桥用**替身**（照 MainActivity 真实接口签名造），并且：
 · 任何 HTTP 请求都自动回一份 canned 应答 → 流程能一路走完，不会卡在超时；
 · bleScanStart2 会**模拟一次完整扫描+连接**（found → connected → svc），把蓝牙那条链也点过一遍。

用法：python scripts/dv_clickall.py [--all]     （--all = 连"已连接"状态下的按钮也点一遍）
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

STUB = r"""
<script>
window.__OM3_APP__=1;window.__errs=[];window.__rejs=[];
window.addEventListener('error',function(e){window.__errs.push('ERR '+(e.message||'')+' @'+(e.lineno||0));});
window.addEventListener('unhandledrejection',function(e){window.__rejs.push('REJ '+String(e.reason&&e.reason.message||e.reason));});
/* ---- 原生替身：照 MainActivity 的真实 @JavascriptInterface 接口造 ---- */
(function(){
  var hid=0, calls=[];
  window.__calls=calls;
  function log(name,args){ calls.push(name+'('+String(args||'').slice(0,60)+')'); }
  function canned(p){
    if(p.indexOf('mysetdatasize')>=0) return '<datasize>120</datasize>';
    if(p.indexOf('mysetrestorestate')>=0) return '<result>ok</result>';
    if(p.indexOf('mysetbackupstate')>=0) return '<result>ok</result><status>ok</status>';
    if(p.indexOf('mysetdatamodekind')>=0) return '<mode>current|myset1</mode><kind>current|factory</kind>';
    if(p.indexOf('mysetname')>=0) return '<mysetname>port A</mysetname>';
    if(p.indexOf('get_caminfo')>=0) return '<caminfo><model>OM-3</model><serial>BJSA000000</serial></caminfo><result>ok</result>';
    if(p.indexOf('mysetdata')>=0) return '1,OM-3,1100,BJSA000000,Current\nMODE_COLOR_CREATOR_2_VIVID_SET1_1,MODE_STEP_P1\n';
    return '<result>ok</result>';
  }
  window.OM3Native={
    /* --- HTTP --- */
    camGetAsync:function(p){ var id='h'+(++hid); setTimeout(function(){ try{window.__om3http(id,{s:200,t:canned(p||'')});}catch(e){} },60); return id; },
    camPostAsync:function(p,b){ return window.OM3Native.camGetAsync(p); },
    camGet:function(p){ return JSON.stringify({s:200,t:canned(p||'')}); },
    camPost:function(p,b){ return JSON.stringify({s:200,t:canned(p||'')}); },
    cameraState:function(){ return JSON.stringify({ssid:'OM-3-STUB',model:'OM-3',serial:'BJSA000000'}); },
    /* --- Wi-Fi --- */
    wifiState:function(){ return JSON.stringify({wifi:true,ssid:'OM-3-STUB',sdk:34}); },
    wifiScanList:function(){ return JSON.stringify([{ssid:'OM-3-STUB',level:-40,cam:true},{ssid:'Home-5G',level:-60,cam:false}]); },
    connectCamera:function(s,p){ log('connectCamera',s); setTimeout(function(){ try{window.__om3camState('connected');}catch(e){} },200); return 'ok'; },
    disconnectCamera:function(){ log('disconnectCamera'); },
    joinWifi:function(s,p){ log('joinWifi',s); return 'ok'; },
    forgetWifi:function(){ return 'ok'; },
    openWifiSettings:function(){ log('openWifiSettings'); },
    dropCamera:function(){ log('dropCamera'); },
    /* --- 蓝牙（带完整模拟：扫描 → 发现相机 → 连接 → 服务发现） --- */
    blePerm:function(){ return 'ok'; },
    blePermDetail:function(){ return 'SDK=34；BLUETOOTH_SCAN=有；BLUETOOTH_CONNECT=有；蓝牙开关=开'; },
    bleAskPerm:function(){ setTimeout(function(){ try{window.__om3blePerm('ok');}catch(e){} },50); },
    bleEnable:function(){ log('bleEnable'); return 'ok'; },          /* 本轮要新增的接口 */
    bleScanStart:function(){ return window.OM3Native.bleScanStart2(0); },
    bleScanStart2:function(onlyCam){
      log('bleScanStart2',onlyCam);
      var f=window.__om3ble; if(!f) return;
      setTimeout(function(){ try{ f('start', onlyCam===1?'onlycam':'all'); }catch(e){ window.__errs.push('BLE-start '+e.message); } },40);
      setTimeout(function(){ try{ f('found','OM-3 STUB','AA:BB:CC:DD:EE:01',-42,1); }catch(e){ window.__errs.push('BLE-found '+e.message); } },120);
      setTimeout(function(){ try{ f('found','Sony WH-1000XM5','AA:BB:CC:DD:EE:02',-70,0); }catch(e){} },160);
      if(onlyCam===1) return;
    },
    bleScanStop:function(){ log('bleScanStop'); },
    bleDevices:function(){ return '[{"mac":"AA:BB:CC:DD:EE:01","name":"OM-3 STUB","rssi":-42}]'; },
    bleConnect:function(mac){
      log('bleConnect',mac); var f=window.__om3ble; if(!f) return;
      setTimeout(function(){ try{ f('connected', mac, 0); }catch(e){} },80);
      setTimeout(function(){ try{ window.__om3ble('mtu', 517, 0); }catch(e){} },120);
      setTimeout(function(){ try{ f('svc', JSON.stringify([{uuid:'ADC505F9-4E58-4B71-B8CA-983BB8C73E4F',type:0,chars:[
              {uuid:'82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68',props:12},
              {uuid:'B7A8015C-CB94-4EFA-BDA2-B7921FA9951F',props:12},
              {uuid:'05A02050-0860-4919-8ADD-9801FBA8B6ED',props:16}]}] ), 0); }catch(e){} },160);
      return 'ok';
    },
    bleDisconnect:function(){ log('bleDisconnect'); },
    bleSubscribe:function(u){ log('bleSubscribe',u); return 'ok'; },
    bleRead:function(u){ return 'ok'; },
    bleWrite:function(u,d,m,f){ log('bleWrite',u); var g=window.__om3ble;
      setTimeout(function(){ try{ g('wrote', u, d, (d||'').length/2); g('notify', u, '0102', ''); }catch(e){} },40); return 'ok'; },
    /* --- 其它 --- */
    shareText:function(t){ log('shareText',String(t||'').length); return 'ok'; },
    copyText:function(t){ return 'ok'; },
    toast:function(t){ log('toast'); return 'ok'; },
    pickFile:function(){ return ''; },
    openUrl:function(u){ log('openUrl'); },
    version:function(){ return 'stub'; }
  };
})();
</script>
"""

JS = r"""
var o=[], errs0=0, rej0=0;
function flush(){
  var d=document.createElement('pre'); d.id='DBGOUT';
  d.textContent=o.join('\n');
  document.body.appendChild(d);
}
function paneName(p){ return 'pane'+p; }
function fp(){                       /* 指纹：有没有"发生点什么" */
  var l=document.body.innerText.length;
  var m=0; ['omask','taskMask','scanMask'].forEach(function(id){ var e=document.getElementById(id); if(e&&!e.classList.contains('hide')) m++; });
  var ls=0; try{ ls=(localStorage.getItem('om3sets')||'').length+(localStorage.getItem('om3cam')||'').length; }catch(e){}
  return l+'|'+document.body.className+'|'+m+'|'+ls;
}
function masksOpen(){
  var L=[]; ['omask','taskMask','scanMask'].forEach(function(id){ var e=document.getElementById(id); if(e&&!e.classList.contains('hide')) L.push(id); });
  return L;
}
function dismiss(){                  /* 收掉一切弹窗/遮罩，避免下一个按钮点不到 */
  try{ var c=document.getElementById('ocancel'); if(c && masksOpen().indexOf('omask')>=0) c.click(); }catch(e){}
  try{ var t=document.getElementById('taskClose'); if(t && !t.classList.contains('hide')) t.click(); }catch(e){}
  try{ var s=document.getElementById('scanStop'); if(s && masksOpen().indexOf('scanMask')>=0) s.click(); }catch(e){}
  try{ document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'})); }catch(e){}
  var lb=document.getElementById('lbclose'); if(lb) try{ lb.click(); }catch(e){}
}
function run(){
  var panes=['A','B','C','D','E'];
  var tasks=[];
  panes.forEach(function(p){
    var tab=document.querySelector('.tabs.mod button[data-p="'+p+'"]');
    if(!tab) return;
    /* paneB/C 的代理按钮是隐藏的，用底部那条栏上的等价按钮 */
    var alt=document.querySelector('#barABC button[data-p="'+p+'"]');
    tasks.push(function(next){
      dismiss();
      try{ (alt||tab).click(); }catch(e){}
      setTimeout(function(){
        var pane=document.getElementById(paneName(p));
        if(!pane){ o.push('[pane'+p+'] 不存在'); return next(); }
        var btns=[].slice.call(pane.querySelectorAll('button')).filter(function(b){ return b.offsetParent!==null || b.id; });
        o.push('');
        o.push('=========== pane'+p+'（'+btns.length+' 个按钮）===========');
        var i=0;
        (function one(){
          if(i>=btns.length) return next();
          var b=btns[i++];
          var id=b.id||('(无id:'+String(b.textContent||'').trim().slice(0,14)+')');
          var before=fp(), e0=window.__errs.length, r0=window.__rejs.length;
          var thrown='';
          try{ b.click(); }catch(e){ thrown=(e&&e.message)||String(e); }
          setTimeout(function(){
            var e1=window.__errs.length, r1=window.__rejs.length;
            var tag='ok', extra='';
            if(thrown){ tag='★抛错'; extra=' ' + thrown; }
            else if(e1>e0){ tag='★运行错误'; extra=' ' + window.__errs.slice(e0,e1).join(' | ').slice(0,110); }
            else if(r1>r0){ tag='★未处理拒绝'; extra=' ' + window.__rejs.slice(r0,r1).join(' | ').slice(0,110); }
            else if(fp()===before){ tag='·无反应'; }
            var mk=masksOpen();
            o.push('  [' + tag + '] ' + id + extra + (mk.length?('  弹层='+mk.join(',')):''));
            if(mk.length){ dismiss(); }
            one();
          }, 170);
        })();
      }, 420);
    });
  });
  /* 第二遍：已连接状态（覆盖 ②备份 / ③写入 / ④记录 那些按钮） */
  if(window.__ALL){
    tasks.push(function(next){
      dismiss();
      try{ if(window.__om3setConn) window.__om3setConn(true); }catch(e){ o.push('setConn 抛错：'+e.message); }
      setTimeout(function(){
        o.push(''); o.push('=========== 已连接状态下再点一遍（②③④ 的按钮）===========');
        var btns=[];
        ['paneD','paneE'].forEach(function(pid){
          var pane=document.getElementById(pid); if(!pane) return;
          [].slice.call(pane.querySelectorAll('button')).forEach(function(b){ btns.push(b); });
        });
        var i=0;
        (function one(){
          if(i>=btns.length) return next();
          var b=btns[i++];
          var id=b.id||('(无id:'+String(b.textContent||'').trim().slice(0,14)+')');
          var e0=window.__errs.length, thrown='';
          try{ b.click(); }catch(e){ thrown=(e&&e.message)||String(e); }
          setTimeout(function(){
            var e1=window.__errs.length, tag='ok', extra='';
            if(thrown){ tag='★抛错'; extra=' '+thrown; }
            else if(e1>e0){ tag='★运行错误'; extra=' '+window.__errs.slice(e0,e1).join(' | ').slice(0,110); }
            o.push('  ['+tag+'] '+id+extra);
            if(masksOpen().length) dismiss();
            one();
          }, 150);
        })();
      }, 700);
    });
  }
  var n=0;
  (function go(){
    if(n>=tasks.length){
      o.push('');
      o.push('===== 汇总 =====');
      o.push('累计 JS 报错 ' + window.__errs.length + ' 个');
      window.__errs.forEach(function(e){ o.push('   ' + e.slice(0,150)); });
      o.push('累计未处理拒绝 ' + window.__rejs.length + ' 个');
      window.__rejs.forEach(function(e){ o.push('   ' + e.slice(0,150)); });
      o.push('__om3errs=' + (window.__om3errs||0));
      o.push('原生调用 ' + window.__calls.length + ' 次：' + window.__calls.slice(0,40).join(' , '));
      return flush();
    }
    tasks[n++](go);
  })();
}
setTimeout(run, 3000);
"""

ALL = '--all' in sys.argv
head = STUB + ('<script>window.__ALL=1;</script>' if ALL else '')
tail = '<script>' + JS + '</script>'
i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_clickall.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\oclickall'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=300000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=600)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
if kk > 0:
    print(dom[kk:].split('>', 1)[1].split('</pre>')[0])
else:
    open(TMP + r'\clickall_dump.html', 'w', encoding='utf-8', newline='').write(dom)
    print('无输出 DOM=%d  → %s' % (len(dom), TMP + r'\clickall_dump.html'))
