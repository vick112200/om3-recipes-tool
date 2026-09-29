# -*- coding: utf-8 -*-
"""用假的原生桥验证：异步 HTTP 桥（含"回调比注册快"的抢占场景）+ 点击不阻塞。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'

MOCK = '''<script>
window.__calls = [];
window.OM3Native = {
  startWatch: function(){ window.__calls.push('startWatch'); },
  wifiState: function(){ return '{"wifi":true,"ssid":"HomeNet"}'; },
  cameraState: function(){ return '{"connected":false}'; },
  permState: function(){ return '{"camera":true,"fine":true,"nearby":true,"sdk":34}'; },
  dropCamera: function(){ return 'ok'; },
  forgetWifi: function(){ return 'ok'; },
  ensureCamera: function(){ return 'ok'; },
  connectCamera: function(){ return 'dialog'; },
  disconnectCamera: function(){ return 'ok'; },
  joinWifi: function(){ return 'ok'; },
  openWifiSettings: function(){}, openAppSettings: function(){}, toast: function(){},
  camGetAsync: function(path){
    window.__calls.push('GET ' + path);
    var id = 'r' + window.__calls.length;
    setTimeout(function(){ window.__om3http(id, JSON.stringify({s:200, t:'<caminfo><model>OM-3</model></caminfo>'})); }, 40);
    return id;
  },
  camPostAsync: function(path, b64){
    window.__calls.push('POST ' + path + ' len=' + (b64 || '').length);
    var id = 'p' + window.__calls.length;
    setTimeout(function(){ window.__om3http(id, JSON.stringify({s:200, t:'ok'})); }, 40);
    return id;
  }
};
</script>'''

PROBE = '''<script>window.__errs=[];window.onerror=function(m,s,l,c){window.__errs.push(m+'@'+l);};
var o=[];function T(f){try{return f()}catch(e){return 'ERR:'+e.message}}
function txt(id){var e=document.getElementById(id);return e?e.textContent:''}
setTimeout(function(){
 o.push('startWatch 被调用='+(window.__calls.indexOf('startWatch')>=0));
 document.getElementById('tabD').click();
 setTimeout(function(){
  var t0 = performance.now();
  T(function(){ document.getElementById('camCheck').click(); });      /* 检测相机 */
  var dt = Math.round(performance.now() - t0);
  o.push('点「检测相机」返回耗时='+dt+'ms（异步，应接近 0）');
  o.push('原生收到='+JSON.stringify(window.__calls.slice(-2)));
  setTimeout(function(){
   o.push('检测结果写进页面='+/OM-3/.test(txt('camOut1')));
   o.push('期间页面可交互='+(document.getElementById('camCheck')!==null));
   o.push('错误='+(window.__errs.length?window.__errs.slice(0,3).join('|'):'无'));
   var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');document.body.appendChild(d);
  },500);
 },600);},2500);</script>'''

h = open(TMP + r'\app\base.html', encoding='utf-8').read()
i = h.find('<body')
j = h.find('>', i) + 1
h = h[:j] + MOCK + '<script>window.__OM3_APP__=1;</script>\n' + h[j:]
open(TMP + r'\dv_async.html', 'w', encoding='utf-8', newline='').write(
    h.replace('</body>', PROBE + '</body>', 1))
print('ok')
