# -*- coding: utf-8 -*-
"""走一遍用户的真实点击路径，看「加进我的配方」之后**名字到底是什么**、以及
   「改名」入口在哪儿（用户 2026-09-23：名字还是槽1；槽配方没有改名的地方）。

打印：
  · 弹窗三个字段的预填值
  · 存进 localStorage 的 name / from / 槽
  · 我的配方列表里那一条的文字
  · 详情页头部文字、各槽位行的标题
  · 改名按钮的文字 + 它在视口下方多少像素（判断是不是"太靠下所以找不到"）

用法：python scripts/dv_mpname.py
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
  function sets(){ try{ return JSON.parse(localStorage.getItem('om3sets') || '[]'); }catch(e){ return []; } }
  function fields(){ return document.querySelectorAll('#ofields select, #ofields input, #ofields textarea'); }
  function txt(el){ return el ? (el.textContent || '').replace(/\s+/g, ' ').trim() : '(无)'; }
  function tryRun(){ try{ run(); }catch(e){ o.push('★异常：' + e.message); dump(); } }
  function dump(){ var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n'); document.body.appendChild(d); }

  function run(){
    /* ---------- 1) 配方卡 → 加入我的配方 ---------- */
    var card = document.querySelector('[id^="r-"]');
    o.push('【配方卡】id=' + (card ? card.id : '?'));
    var btn = card ? card.querySelector('.omsavebtn') : null;
    o.push('  卡片标题=' + txt(card ? card.querySelector('.chd') : null).slice(0, 80));
    if(btn) btn.click();
    setTimeout(function(){
      var f = fields();
      if(f.length >= 3){
        o.push('  弹窗预填：档位=' + JSON.stringify(f[0].value)
             + ' 槽位=' + JSON.stringify(f[1].value)
             + ' 名字=' + JSON.stringify(f[2].value));
      }else o.push('  ★弹窗字段数=' + f.length);
      document.getElementById('ook').click();
      setTimeout(function(){
        var a = sets(), s = a[a.length - 1];
        o.push('  存进去的 name=' + JSON.stringify(s ? s.name : null)
             + ' from=' + JSON.stringify(s ? s.from : null)
             + ' 有内容的槽=' + JSON.stringify(s ? Object.keys(s.slots).filter(function(k){ return s.slots[k]; }) : []));

        /* ---------- 2) 我的配方：列表 + 详情 ---------- */
        document.getElementById('tabMine').click();
        setTimeout(function(){
          var it = document.querySelector('#mpList .mpitem');
          o.push('【我的配方列表】第一条=' + JSON.stringify(txt(it).slice(0, 120)));
          if(it) it.click();
          setTimeout(function(){
            var pane = document.getElementById('mpPane') || document.getElementById('tabMinePane') || document.body;
            var items = document.querySelectorAll('#mpSub * , #paneE .mpitem');
            var head = items.length ? items[0] : null;
            /* 详情页容器：找 id=mpBack 的父级 mpitem */
            var back = document.getElementById('mpBack');
            var headEl = back ? back.parentElement : null;
            o.push('【详情页头部】' + JSON.stringify(txt(headEl).slice(0, 160)));
            var rows = document.querySelectorAll('[data-w]');
            for(var i = 0; i < rows.length && i < 4; i++){
              var r = rows[i].closest('.mpsrow') || rows[i].parentElement;
              o.push('  槽位行 ' + (i + 1) + '=' + JSON.stringify(txt(r).slice(0, 90)));
            }
            var e = document.getElementById('mpEdit');
            if(!e){ o.push('  ★没有 #mpEdit（改名）按钮'); }
            else{
              var q = e.getBoundingClientRect();
              o.push('【改名按钮】文字=' + JSON.stringify(txt(e))
                   + ' 视口高=' + window.innerHeight
                   + ' 它在页面里距顶部=' + Math.round(q.top + window.scrollY) + 'px'
                   + '（滚到它需要往下滚约 ' + Math.max(0, Math.round(q.top + window.scrollY - window.innerHeight + 60)) + 'px）');
            }
            o.push('  详情页里所有按钮文字=' + JSON.stringify([].map.call(document.querySelectorAll('#paneE button, #mpSub button'), function(b){ return txt(b).slice(0, 14); }).join(' | ')).slice(0, 400));

            /* ---------- 3) 优化版槽位卡那条路 ---------- */
            document.getElementById('tabBuiltin').click();
            setTimeout(function(){
              var osb = document.querySelector('.oslot .omsavebtn');
              if(!osb){ o.push('【优化版槽位卡】没找到保存按钮'); dump(); return; }
              var slot = osb.closest('.oslot');
              o.push('【优化版槽位卡】卡片文字=' + JSON.stringify(txt(slot).slice(0, 100)));
              osb.click();
              setTimeout(function(){
                var f2 = fields();
                if(f2.length >= 3) o.push('  弹窗预填：档位=' + JSON.stringify(f2[0].value)
                     + ' 槽位=' + JSON.stringify(f2[1].value) + ' 名字=' + JSON.stringify(f2[2].value));
                document.getElementById('ocancel').click();
                setTimeout(function(){
                  o.push('  取消后方案数=' + sets().length + '（应为 1）');
                  dump();
                }, 300);
              }, 500);
            }, 600);
          }, 700);
        }, 700);
      }, 500);
    }, 700);
  }
  tryRun();
}, 3000);
"""
tail = ('<script>window.__errs=[];'
        "window.addEventListener('error',function(e){window.__errs.push(String(e.message));});"
        '</script><script>' + JS + '</script>')

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_mpname.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\ompname'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=40000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
