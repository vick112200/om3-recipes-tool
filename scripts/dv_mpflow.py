# -*- coding: utf-8 -*-
"""「我的配方」流程实测：列表 → 详情 → 改名弹窗 → 删除弹窗（取消后不能真删）。

用法：python scripts/dv_mpflow.py
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
  var o = [], errs = 0;
  window.addEventListener('error', function(){ errs++; });
  function n(){ return document.querySelectorAll('#mpList .mpitem').length; }
  function sets(){ try{ return JSON.parse(localStorage.getItem('om3sets')||'[]').length; }catch(e){ return -1; } }
  function dlg(){ var m=document.getElementById('omask');
    return m && getComputedStyle(m).display !== 'none' && !m.classList.contains('hide'); }
  try{ localStorage.setItem('om3sets', JSON.stringify([
    {id:'t1',name:'甲方案',desc:'描述甲',from:'myset1',camera:'OM-3',
     slots:{1:{vivid:[1,2,3,0,0,0,0,0,0,0,0,0],raw:{'MODE_COLOR_CREATOR_2_VIVID_SET1_1':'MODE_STEP_P1'},used:3},
            2:null,3:null,4:null}}])); }catch(e){}
  document.getElementById('tabMine').click();
  setTimeout(function(){
    o.push('列表：条目=' + n() + '  文字=' + JSON.stringify((document.getElementById('mpList').textContent||'').replace(/\s+/g,' ').slice(0,40)));
    var first = document.querySelector('#mpList .mpitem');
    if(first) first.click();
    setTimeout(function(){
      var txt = (document.getElementById('mpList').textContent||'').replace(/\s+/g,' ');
      o.push('详情：条目=' + n() + '（应为 6：返回+头+4槽+底）');
      o.push('  有返回按钮=' + !!document.getElementById('mpBack')
           + ' 有改名=' + !!document.getElementById('mpEdit')
           + ' 有导出整套=' + !!document.getElementById('mpExp')
           + ' 有删除=' + !!document.getElementById('mpDel'));
      o.push('  槽位写入按钮数=' + document.querySelectorAll('#mpList button[data-w]').length
           + ' 分享=' + document.querySelectorAll('#mpList button[data-sh]').length
           + ' 导出oes=' + document.querySelectorAll('#mpList button[data-oe]').length);
      o.push('  正文=' + JSON.stringify(txt.slice(0,70)));

      var e = document.getElementById('mpEdit');
      if(e) e.click();
      setTimeout(function(){
        o.push('改名弹窗：出现=' + dlg() + ' 标题=' + JSON.stringify(((document.getElementById('otitle')||{}).textContent)||'')
             + ' 输入框数=' + document.querySelectorAll('#ofields input,#ofields textarea').length);
        document.getElementById('ocancel').click();
        setTimeout(function(){
          o.push('  取消后弹窗=' + dlg() + '  方案数=' + sets());
          var d = document.getElementById('mpDel');
          if(d) d.click();
          setTimeout(function(){
            o.push('删除弹窗：出现=' + dlg() + ' 标题=' + JSON.stringify(((document.getElementById('otitle')||{}).textContent)||''));
            document.getElementById('ocancel').click();
            setTimeout(function(){
              o.push('  取消后弹窗=' + dlg() + '  方案数=' + sets() + '（必须仍是 1，取消不能真删）');
              var back = document.getElementById('mpBack');
              if(back) back.click();
              setTimeout(function(){
                o.push('返回列表：条目=' + n() + '（应为 1）');
                o.push('累计 js 报错=' + errs + '  om3errs=' + (window.__om3errs||0));
                var p=document.createElement('pre');p.id='DBGOUT';p.textContent=o.join('\n');
                document.body.appendChild(p);
              }, 350);
            }, 350);
          }, 350);
        }, 350);
      }, 400);
    }, 500);
  }, 700);
}, 2800);
"""
tail = '<script>' + JS + '</script>'

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_mpflow.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\ompflow'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=22000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=220)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
