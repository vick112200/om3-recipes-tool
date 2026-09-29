# -*- coding: utf-8 -*-
"""回归 + 性能：加载耗时 / 轮询开销 / 各功能是否还在。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
PROBE = '''<script>window.__errs=[];window.onerror=function(m,s,l,c){window.__errs.push(m+'@'+l);};
var o=[];function T(f){try{return f()}catch(e){return 'ERR:'+e.message}}
function vis(id){var e=document.getElementById(id);return !!(e&&!e.classList.contains('hide'))}
var t0 = performance.now();
setTimeout(function(){
 o.push('页面可用耗时≈'+Math.round(performance.now())+'ms（含 2.4s 等待）');
 document.getElementById('tabD').click();
 setTimeout(function(){
  o.push('门卡='+vis('camGateOff')+' 导入按钮='+document.querySelectorAll('.om3imp').length);
  // 轮询开销测量
  var t1=performance.now(); for(var i=0;i<50;i++){ window.__om3setConn(true); window.__om3setConn(false); } var t2=performance.now();
  o.push('50 次连接状态切换耗时='+Math.round(t2-t1)+'ms');
  o.push('T(setConn)='+T(function(){window.__om3setConn(true);return 'ok'}));
  o.push('连上='+vis('camStatusCard')+' 状态条='+document.getElementById('camStCam').textContent);
  o.push('T(记录)='+T(function(){window.__om3impRecord({slug:'x',n:'T',a:'M'},'C1',1);return document.querySelectorAll('#camRecOut .recrow').length}));
  o.push('T(扫码)='+T(function(){window.__camStep(1);document.getElementById('camScan').click();return vis('scanMask')}));
  o.push('T(菜单)='+T(function(){window.__camStep(3);return vis('camV3')}));
  o.push('错误='+(window.__errs.length?window.__errs.slice(0,2).join('|'):'无'));
  var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');document.body.appendChild(d);
 },600);},2400);</script>'''
h = open(TMP + r'\app\base.html', encoding='utf-8').read()
i = h.find('<body')
j = h.find('>', i) + 1
h = h[:j] + '<script>window.__OM3_APP__=1;window.__t_start=Date.now();</script>\n' + h[j:]
open(TMP + r'\dv_perf.html', 'w', encoding='utf-8', newline='').write(
    h.replace('</body>', PROBE + '</body>', 1))
print('ok')
