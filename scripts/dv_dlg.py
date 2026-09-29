# -*- coding: utf-8 -*-
"""量选槽位弹窗的几何：卡片/选项按钮/「建议」标签有没有超出屏幕被裁掉。

用法：python scripts/dv_dlg.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

head = "<script>window.__OM3_APP__=1;</script>"

JS = r"""
setTimeout(function(){
  document.querySelector('.card[id^=r-] .omsavebtn').click();
  setTimeout(function(){
    var o = [];
    function R(e){ if(!e) return '无'; var r=e.getBoundingClientRect();
      return Math.round(r.left)+'~'+Math.round(r.right)+' ('+Math.round(r.width)+' 宽)'; }
    var vw = document.documentElement.clientWidth;
    o.push('视口宽=' + vw);
    var mask = document.getElementById('omask'), card = document.querySelector('.ocard');
    o.push('#omask  ' + R(mask) + '  display=' + getComputedStyle(mask).display);
    o.push('.ocard  ' + R(card) + '  css宽度=' + getComputedStyle(card).width
           + '  box-sizing=' + getComputedStyle(card).boxSizing + '  padding=' + getComputedStyle(card).padding);
    var fields = document.getElementById('ofields');
    o.push('#ofields ' + R(fields));
    var chs = document.querySelectorAll('#ofields .om3choice');
    for(var i=0;i<chs.length;i++){
      var hs = chs[i].querySelector('.om3chint');
      o.push('  choice' + (i+1) + ' ' + R(chs[i]) + '  文字=' + JSON.stringify(chs[i].textContent)
             + '  建议标签 ' + R(hs));
      if(hs){
        var cr = card.getBoundingClientRect(), hr = hs.getBoundingClientRect();
        o.push('     建议标签右缘=' + Math.round(hr.right) + '  卡片右缘=' + Math.round(cr.right)
               + '  视口右缘=' + vw + '  → ' + ((hr.right > cr.right) ? '!! 超出卡片' : '在卡片内')
               + ' / ' + ((hr.right > vw) ? '!! 超出屏幕' : '在屏幕内'));
      }
    }
    o.push('.obtns   ' + R(document.querySelector('.obtns')));
    o.push('取消     ' + R(document.getElementById('ocancel')) + '   确定 ' + R(document.getElementById('ook')));
    var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
    document.body.appendChild(d);
  }, 500);
}, 2600);
"""
tail = '<script>' + JS + '</script>'

i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_dlg.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\odlg'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=14000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=200)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
print(dom[k:].split('>', 1)[1].split('</pre>')[0] if k > 0 else ('无输出 DOM=%d' % len(dom)))
