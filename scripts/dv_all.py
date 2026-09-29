# -*- coding: utf-8 -*-
"""全量回归：这一轮补齐的 7 项 + 原有流程。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
PROBE = '''<script>window.__errs=[];window.onerror=function(m,s,l,c){window.__errs.push(m+'@'+l);};
var o=[];function T(f){try{return f()}catch(e){return 'ERR:'+e.message}}
function vis(id){var e=document.getElementById(id);return !!(e&&!e.classList.contains('hide'))}
function txt(id){var e=document.getElementById(id);return e?e.textContent:''}
setTimeout(function(){
 o.push('备份信息='+txt('camBakInfo').slice(0,40));
 o.push('回滚按钮 disabled='+document.getElementById('camRestore').disabled);
 o.push('记住按钮=「'+txt('camJoin')+'」');
 o.push('优化版槽位导入按钮='+document.querySelectorAll('.oslot .om3imp').length+' 配方卡按钮='+document.querySelectorAll('.card .om3imp').length);
 o.push('uploadData='+typeof window.__om3uploadData+' restore='+typeof window.__om3restoreBackup+' write='+typeof window.__om3writeRecipe);
 o.push('菜单有检查权限='+/检查权限/.test(txt('camMenuDrop')));
 o.push('T(无备份写入)='+T(function(){ var r=window.__om3writeRecipe({n:'T',a:'M',slug:'x',t:'COLOR'},1,'C1','OM-3'); return 'promise'}));
 document.getElementById('tabD').click();
 setTimeout(function(){
  o.push('切到导入相机: 门卡='+vis('camGateOff')+' 状态条='+txt('camStBak'));
  window.__om3setConn(true);
  o.push('连上: 状态卡='+vis('camStatusCard'));
  o.push('T(记录)='+T(function(){window.__om3impRecord({slug:'x',n:'T',a:'M'},'C1',2);return document.querySelectorAll('#camRecOut .recrow').length}));
  o.push('T(槽位弹层)='+T(function(){document.querySelector('.oslot .om3imp').click();return document.querySelectorAll('#impList .improw').length}));
  document.getElementById('impCancel').click();
  o.push('T(忘掉相机)='+T(function(){document.getElementById('camForgetSaved').click();return txt('camConnectOut').slice(-24)}));
  o.push('错误='+(window.__errs.length?window.__errs.slice(0,3).join('|'):'无'));
  var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');document.body.appendChild(d);
 },700);},2500);</script>'''
h = open(TMP + r'\app\base.html', encoding='utf-8').read()
i = h.find('<body')
j = h.find('>', i) + 1
pre = ('<script>window.__OM3_APP__=1;try{'
       'localStorage.setItem("om3cam",JSON.stringify({ssid:"OM-3-P-BJSA21721",pass:"8221759294751531"}));'
       'localStorage.setItem("om3bak",JSON.stringify({t:Date.now()-60000,text:"MYSET-备份内容"}));'
       '}catch(e){}</script>')
h = h[:j] + pre + h[j:]
open(TMP + r'\dv_all.html', 'w', encoding='utf-8', newline='').write(
    h.replace('</body>', PROBE + '</body>', 1))
print('ok')
