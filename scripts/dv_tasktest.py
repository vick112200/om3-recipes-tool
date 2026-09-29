# -*- coding: utf-8 -*-
"""实测任务弹窗：「后台运行」「关闭」「右下角气泡」三个按钮到底有没有反应。

用页面自己暴露的 window.__om3runTask 起一个 2 秒的任务，然后逐个点按钮看状态变化。
用法：python scripts/dv_tasktest.py
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
  var o = [];
  function hid(id){ var e = document.getElementById(id);
    return e ? e.classList.contains('hide') : '无元素'; }
  function st(tag){
    o.push(tag + '  → 弹窗隐藏=' + hid('taskMask') + '  气泡隐藏=' + hid('taskPill'));
  }
  if(typeof window.__om3runTask !== 'function'){ o.push('!! __om3runTask 未暴露'); }
  else{
    window.__om3runTask('自检任务', function(done){
      return new Promise(function(res){
        var n = 0;
        var iv = setInterval(function(){
          n++; try{ done(n, 4); }catch(e){}
          if(n >= 5){ clearInterval(iv); res(); }
        }, 300);
      });
    });
  }
  setTimeout(function(){
    st('① 任务进行中');
    var bg = document.getElementById('taskBg');
    o.push('   后台运行按钮 存在=' + !!bg + ' 可见=' + (bg ? getComputedStyle(bg).display !== 'none' : ''));
    if(bg) bg.click();
    setTimeout(function(){
      st('② 点了「后台运行」（期望 弹窗隐藏=true、气泡隐藏=false）');
      var pill = document.getElementById('taskPill');
      if(pill) pill.click();
      setTimeout(function(){
        st('③ 点了右下角气泡（期望 弹窗隐藏=false）');
        setTimeout(function(){
          st('④ 等任务跑完');
          var cl = document.getElementById('taskClose');
          o.push('   关闭按钮 存在=' + !!cl + ' 可见=' + (cl ? getComputedStyle(cl).display !== 'none' : ''));
          if(cl) cl.click();
          setTimeout(function(){
            st('⑤ 点了「关闭」（期望 弹窗隐藏=true）');
            var d=document.createElement('pre');d.id='DBGOUT';d.textContent=o.join('\n');
            document.body.appendChild(d);
          }, 350);
        }, 1400);
      }, 350);
    }, 350);
  }, 700);
}, 2800);
"""
tail = '<script>' + JS + '</script>'

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_tasktest.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\otasktest'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=20000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=220)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
