# -*- coding: utf-8 -*-
"""量「写入」页（连接相机 step 3）底部页签有没有固定好、有没有压住内容。

用法：python scripts/dv_barD.py [步骤号 默认3]
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
step = sys.argv[1] if len(sys.argv) > 1 else '3'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

head = "<script>window.__OM3_APP__=1;</script>"

JS = r"""
setTimeout(function(){
  var o = [];
  /* 没有相机时 showStep(n>=2) 会被强制拉回 1，所以这里先假装"已连上" */
  document.body.classList.add('cam-on');
  document.getElementById('tabCam').click();
  setTimeout(function(){
    try{ window.__om3step ? window.__om3step(__STEP__) : null; }catch(e){}
    /* 直接用底部按钮切步骤（走的是真实交互路径） */
    var b = document.querySelector('#barD button[data-dstep="__STEP__"]');
    if(b) b.click();
    setTimeout(function(){
      function r(tag, el){
        if(!el){ o.push('  ' + tag + ' 不存在'); return null; }
        var q = el.getBoundingClientRect();
        o.push('  ' + tag + ' = top ' + Math.round(q.top) + ' bottom ' + Math.round(q.bottom)
             + ' 高 ' + Math.round(q.height) + '  left ' + Math.round(q.left) + ' right ' + Math.round(q.right));
        return q;
      }
      var iw = window.innerWidth, ih = window.innerHeight;
      o.push('视口 ' + iw + '×' + ih + '  页面高 ' + document.documentElement.scrollHeight
           + '  滚动条宽 ' + (document.documentElement.scrollWidth - iw));
      var cs = getComputedStyle(document.getElementById('barD'));
      o.push('  #barD position=' + cs.position + ' bottom=' + cs.bottom + ' z-index=' + cs.zIndex
           + ' display=' + cs.display);
      /* 两条底栏：barABC（页签切换）与 barD（相机步骤）—— 会不会同时显示、叠在屏幕底部？ */
      var aOn = 0, dOn = 0;
      document.querySelectorAll('.barABC').forEach(function(x){
        var c4 = getComputedStyle(x);
        if(c4.display !== 'none') aOn++;
        o.push('  .barABC display=' + c4.display + ' 文案=' + JSON.stringify((x.textContent || '').replace(/\s+/g, ' ').slice(0, 30)));
      });
      if(cs.display !== 'none') dOn++;
      o.push('  → 两条底栏同时显示：' + ((aOn > 0 && dOn > 0)
           ? ('★是（barABC ' + aOn + ' 条 + barD ' + dOn + ' 条会叠在屏幕底部）') : ('否（barABC ' + aOn + ' / barD ' + dOn + '）')));
      var bar = r('#barD', document.getElementById('barD'));
      /* position:fixed 会被祖先的 transform/filter/will-change/contain 变成"相对该祖先"→ 滚动时跟着跑。
         「底栏没钉住」的头号原因，逐个祖先查一遍。 */
      o.push('  #barD 的祖先链（只列会破坏 fixed 的属性）：');
      var chain = document.getElementById('barD'), depth = 0;
      while(chain && chain.nodeType === 1 && depth < 12){
        var c5 = getComputedStyle(chain), bad = [];
        if(c5.transform && c5.transform !== 'none') bad.push('transform=' + c5.transform);
        if(c5.filter && c5.filter !== 'none') bad.push('filter=' + c5.filter);
        if(c5.perspective && c5.perspective !== 'none') bad.push('perspective=' + c5.perspective);
        if(c5.willChange && c5.willChange !== 'auto') bad.push('will-change=' + c5.willChange);
        if(c5.contain && c5.contain !== 'none') bad.push('contain=' + c5.contain);
        var bf = c5.backdropFilter || c5.webkitBackdropFilter;
        if(bf && bf !== 'none') bad.push('backdrop-filter=' + bf);
        o.push('    ' + (chain.id ? ('#' + chain.id)
              : (chain.className ? ('.' + String(chain.className).split(' ').join('.')) : chain.tagName))
             + (bad.length ? ('  ★' + bad.join(' , ')) : '  （干净）'));
        chain = chain.parentElement; depth++;
      }
      r('#gateHintD', document.getElementById('gateHintD'));
      var g = getComputedStyle(document.body).paddingBottom;
      o.push('  body padding-bottom=' + g);
      var pane = document.getElementById('paneD');
      var last = null, kids = pane ? pane.querySelectorAll('div,button') : [];
      for(var i = 0; i < kids.length; i++){
        var q = kids[i].getBoundingClientRect();
        if(q.height > 0 && (!last || q.bottom > last.bottom)) last = q;
      }
      if(last && bar){
        var covered = last.bottom > bar.top && last.top < bar.bottom;
        o.push('  页面最靠下的可见块：bottom=' + Math.round(last.bottom)
             + '（' + (last.className || last.tagName) + '）');
        o.push('  它是否被 #barD 压住：' + (covered ? '★是（内容被遮）' : '否 ✓'));
      }
      if(bar){
        o.push('  底栏是否贴着视口底：' + (Math.abs(bar.bottom - ih) < 2 ? '是 ✓' : '否（差 ' + Math.round(ih - bar.bottom) + 'px）'));
        o.push('  底栏是否盖住整屏：' + (bar.top < 0 ? '★是' : '否 ✓'));
      }
      /* 往下滚一屏再量一次：底栏钉不钉住 + 滚到底时最后一屏内容有没有被压住 */
      o.push('  body overflow=' + getComputedStyle(document.body).overflow
           + '  html overflow=' + getComputedStyle(document.documentElement).overflow);
      o.push('  body.style.overflow=' + JSON.stringify(document.body.style.overflow)
           + '  scrollingElement=' + (document.scrollingElement ? document.scrollingElement.tagName : '?'));
      window.scrollTo(0, document.documentElement.scrollHeight);
      setTimeout(function(){
        o.push('  scrollTo 之后 window.scrollY=' + Math.round(window.scrollY)
             + '  documentElement.scrollTop=' + Math.round(document.documentElement.scrollTop)
             + '  body.scrollTop=' + Math.round(document.body.scrollTop));
        var b2 = document.getElementById('barD').getBoundingClientRect();
        o.push('  滚到底后 #barD top=' + Math.round(b2.top) + ' bottom=' + Math.round(b2.bottom)
             + '（应仍≈' + ih + '）' + (Math.abs(b2.bottom - ih) < 2 ? ' ✓' : ' ★没钉住'));
        /* 滚到底时，页面里最低的叶子内容 vs 底栏顶边 —— 这才是"有没有被压住" */
        var lowest = -1, who = '';
        var all = document.querySelectorAll('#paneD *');
        for(var k2 = 0; k2 < all.length; k2++){
          var el = all[k2];
          if(el.children.length) continue;                 /* 只看叶子节点 */
          var q2 = el.getBoundingClientRect();
          if(q2.height <= 0 || q2.width <= 0) continue;
          if(q2.bottom > lowest){ lowest = q2.bottom; who = (el.id || el.className || el.tagName) + ''; }
        }
        o.push('  滚到底时最低的叶子内容 bottom=' + Math.round(lowest) + '（' + who.slice(0, 40) + '）');
        o.push('  底栏顶边=' + Math.round(b2.top));
        o.push('  结论：' + (lowest > b2.top + 1
              ? ('★被压住 ' + Math.round(lowest - b2.top) + 'px')
              : '✓ 没被压住（留白 ' + Math.round(b2.top - lowest) + 'px）'));
        o.push('  页面可滚动量=' + (document.documentElement.scrollHeight - window.innerHeight)
             + '  当前 scrollY=' + Math.round(window.scrollY));
        var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
        document.body.appendChild(d);
      }, 250);
    }, 700);
  }, 800);
}, 2800);
""".replace('__STEP__', step)

tail = '<script>' + JS + '</script>'

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_barD.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\obarD'
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
