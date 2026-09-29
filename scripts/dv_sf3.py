# -*- coding: utf-8 -*-
"""验证：扫码入口的失败提示现在"看得见"了吗。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
PROBE = '''<script>window.__errs=[];window.onerror=function(m,s,l,c){window.__errs.push(m+'@'+l);};
var o=[];function T(f){try{return f()}catch(e){return 'ERR:'+e.message}}
function cd(id){var e=document.getElementById(id);return e?getComputedStyle(e).display:'-'}
function txt(id){var e=document.getElementById(id);return e?e.textContent:''}
setTimeout(function(){document.getElementById('tabD').click();
 setTimeout(function(){
  T(function(){document.getElementById('camScan').click();});
  setTimeout(function(){
   o.push('正常路径: 浮层='+cd('scanMask')+' 浮层内提示='+txt('scanOut').slice(0,24));
   window.jsQR = undefined;                      /* 模拟扫码组件没加载 */
   document.getElementById('scanMask').classList.add('hide');
   T(function(){document.getElementById('camScan').click();});
   setTimeout(function(){
    o.push('无jsQR: 页面可见提示='+/扫码组件/.test(txt('camConnectOut')));
    o.push('手动卡展开='+(document.getElementById('camManualCard').style.display!=='none'));
    o.push('日志有记录='+/扫码组件/.test(txt('camOut3')));
    o.push('浮层没乱开='+cd('scanMask'));
    o.push('授权回调存在='+typeof window.__om3camGranted);
    o.push('错误='+(window.__errs.length?window.__errs.slice(0,2).join('|'):'无'));
    var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');document.body.appendChild(d);
   },600);
  },600);
 },700);},2400);</script>'''
h = open(TMP + r'\app\base.html', encoding='utf-8').read()
i = h.find('<body')
j = h.find('>', i) + 1
h = h[:j] + '<script>window.__OM3_APP__=1;</script>\n' + h[j:]
open(TMP + r'\dv_sf3.html', 'w', encoding='utf-8', newline='').write(
    h.replace('</body>', PROBE + '</body>', 1))
print('ok')
