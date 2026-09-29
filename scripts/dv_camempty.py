# -*- coding: utf-8 -*-
"""诊断「连接相机」页签为空：把 paneD 的子树按可见性列出来，看是谁被藏了。

用法：python scripts/dv_camempty.py
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
  document.getElementById('tabCam').click();
  setTimeout(function(){
    var o = [];
    function vis(e){
      if(!e) return false;
      var s = getComputedStyle(e);
      return s.display !== 'none' && s.visibility !== 'hidden' && e.offsetHeight > 0;
    }
    try{
      var pd = document.getElementById('paneD');
      if(!pd){ o.push('找不到 paneD'); }
      else{
        o.push('paneD display=' + getComputedStyle(pd).display + ' 可见=' + vis(pd)
               + ' 高=' + pd.offsetHeight + ' 去空白文字长度=' + (pd.textContent||'').replace(/\s+/g,'').length);
        o.push('paneD 正文前 200 字：' + JSON.stringify((pd.textContent||'').replace(/\s+/g,' ').slice(0,200)));
        o.push('--- paneD 直接子元素 ---');
        for(var i=0;i<pd.children.length;i++){
          var c = pd.children[i];
          o.push('  ['+i+'] '+c.tagName+'#'+(c.id||'-')+'.'+String(c.className||'').slice(0,45)
                 +' display='+getComputedStyle(c).display+' 可见='+vis(c)+' 高='+c.offsetHeight);
        }
        o.push('--- camV1..camV4 ---');
        for(var k=1;k<=4;k++){
          var v = document.getElementById('camV'+k);
          o.push('  camV'+k+' 存在='+!!v+(v?(' class="'+String(v.className)+'" 可见='+vis(v)+' 高='+v.offsetHeight):''));
        }
        o.push('--- paneD 的祖先链（找谁把它藏了）---');
        var a = pd.parentNode, lvl = 0;
        while(a && a.nodeType === 1 && lvl < 12){
          var st = getComputedStyle(a);
          o.push('  ↑ ' + a.tagName + '#' + (a.id||'-') + '.' + String(a.className||'').slice(0,45)
                 + '  display=' + st.display + '  visibility=' + st.visibility
                 + '  opacity=' + st.opacity + '  高=' + a.offsetHeight);
          a = a.parentNode; lvl++;
        }
        o.push('--- body 直接子元素 ---');
        for(var bi=0;bi<document.body.children.length;bi++){
          var bc = document.body.children[bi];
          o.push('  body>[' + bi + '] ' + bc.tagName + '#' + (bc.id||'-') + '.' + String(bc.className||'').slice(0,40)
                 + ' display=' + getComputedStyle(bc).display + ' 高=' + bc.offsetHeight);
        }
        o.push('--- paneD 内带 data-step / .camstep 的元素 ---');
        var ss = pd.querySelectorAll('[data-step], .camstep');
        for(var q=0;q<ss.length;q++){
          var b = ss[q];
          o.push('  step='+b.getAttribute('data-step')+' tag='+b.tagName+' id='+(b.id||'-')
                 +' class="'+String(b.className).slice(0,45)+'" 可见='+vis(b)+' 高='+b.offsetHeight);
        }
        o.push('--- 底栏 button[data-dstep] ---');
        var bb = document.querySelectorAll('button[data-dstep]');
        for(var w=0;w<bb.length;w++){
          var t2 = bb[w];
          o.push('  dstep='+t2.getAttribute('data-dstep')+' 文字='+t2.textContent.trim().slice(0,16)
                 +' 可见='+vis(t2)+' 有dis='+t2.classList.contains('dis'));
        }
        o.push('--- 关键控件 ---');
        var ids = ['camScan','camWifiIn','camWifiOut','camRun','camOut3','gateHintD','gStatusBar','barD'];
        for(var z=0;z<ids.length;z++){
          var e2 = document.getElementById(ids[z]);
          o.push('  #'+ids[z]+' 存在='+!!e2+(e2?(' 可见='+vis(e2)+' 高='+e2.offsetHeight):''));
        }
        o.push('body.cam-on=' + document.body.classList.contains('cam-on'));
      }
    }catch(err){
      o.push('脚本异常: ' + (err && err.message ? err.message : err));
    }
    var d = document.createElement('pre');
    d.id = 'DBGOUT';
    d.textContent = o.join('\n');
    document.body.appendChild(d);
  }, 1000);
}, 2400);
"""
tail = '<script>' + JS + '</script>'

i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_camempty.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\ocamempty'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,1400',
                    '--virtual-time-budget=14000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=200)
dom = r.stdout or ''
k = dom.find('id="DBGOUT"')
print(dom[k:].split('>', 1)[1].split('</pre>')[0] if k > 0 else ('无输出 DOM=%d' % len(dom)))
