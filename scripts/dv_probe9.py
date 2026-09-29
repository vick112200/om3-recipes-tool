# -*- coding: utf-8 -*-
"""验收：三步向导 + 扫码解析。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'

PROBE = '''<script>
window.__errs=[]; window.onerror=function(m){window.__errs.push(String(m));};
setTimeout(function(){
  var o=[];
  o.push('jsQR 载入=' + (typeof window.jsQR));
  document.getElementById('tabD').click();
  setTimeout(function(){
    o.push('步骤按钮=' + document.querySelectorAll('#camSteps button').length);
    o.push('默认显示=V' + [1,2,3].filter(function(k){return !document.getElementById('camV'+k).classList.contains('hide');}).join(','));
    document.querySelectorAll('#camSteps button')[2].click();
    o.push('点第3步后=V' + [1,2,3].filter(function(k){return !document.getElementById('camV'+k).classList.contains('hide');}).join(','));
    o.push('状态条=' + document.getElementById('camStWifi').textContent + ' / ' + document.getElementById('camStCam').textContent + ' / ' + document.getElementById('camStBak').textContent);
    var P = window.__om3parseWifi, t = [];
    function chk(name, s){
      var r = P(s);
      t.push(name + '→' + (r.ssid||'(空)') + '/' + (r.pass||'(空)'));
    }
    chk('WIFI格式', 'WIFI:T:WPA;S:OM-3-1234567;P:12345678;;');
    chk('JSON', '{"ssid":"OM-3-1234567","password":"12345678"}');
    chk('JSON大写', '{"SSID":"OM-3-7654321","PASSWORD":"87654321"}');
    chk('key=value', 'ssid=OM-3-1111111&password=11111111');
    chk('纯文本', 'OM-3-1234567 12345678');
    chk('换行', 'OM-3-1234567\\n12345678');
    o.push(t.join(' | '));
    var sl = document.getElementById('camSsid'), pl = document.getElementById('camPass');
    o.push('扫码浮层存在=' + (!!document.getElementById('scanMask')) + ' 默认隐藏=' + document.getElementById('scanMask').classList.contains('hide'));
    o.push('写入页元素=' + ['camTarget','camSlot','camRecipe','camModel','camPreview','camWrite','camReboot'].map(function(x){return document.getElementById(x)?'✓':'✗'}).join(''));
    o.push('备份页元素=' + ['camBackup','camDl','camOut2'].map(function(x){return document.getElementById(x)?'✓':'✗'}).join(''));
    o.push('配对数=' + document.getElementById('camRecipe').options.length);
    o.push('JS错误=' + (window.__errs.length ? window.__errs.join('|') : '无'));
    var d = document.createElement('div'); d.id='DBGOUT'; d.textContent = o.join(' ;; ');
    document.body.appendChild(d);
  }, 500);
}, 2200);
</script>'''

h = open(TMP + r'\app\base.html', encoding='utf-8').read()
i = h.find('<body')
j = h.find('>', i) + 1
h = h[:j] + '<script>window.__OM3_APP__=1;</script>\n' + h[j:]
open(TMP + r'\dv_scan.html', 'w', encoding='utf-8', newline='').write(h.replace('</body>', PROBE + '</body>', 1))
print('已生成 dv_scan.html')
