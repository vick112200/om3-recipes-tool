# -*- coding: utf-8 -*-
"""「点写入之后底栏丢了 / 只剩三个按钮」回归探针（v2.16）。

复刻用户 2026-09-24 的操作：连上相机 → 点底栏「写入」（第 3 步）→ 第 3 步内容变多 →
量 #barD 的定位/宽度/四个按钮是否都在屏幕内。

**这个探针必须先把 cam-on 打开** —— 老探针 dv_barprobe.py 没打开，
showStep(2/3/4) 被"未连接"守卫拦回第 1 步，等于从来没量过第 3 步。

用法：python scripts/dv_barstep3.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

head = ("<script>window.__OM3_APP__=1;window.__errs=[];"
        "window.addEventListener('error',function(e){window.__errs.push('ERR '+(e.message||''));});</script>")

JS = r"""
var o = [], fails = [];
function ok(c, m){ o.push((c ? '  [OK ] ' : '  [FAIL] ') + m); if(!c) fails.push(m); }
function R(e){ var r = e.getBoundingClientRect();
  return {x:Math.round(r.left),y:Math.round(r.top),w:Math.round(r.width),h:Math.round(r.height),bottom:Math.round(r.bottom)}; }
function barInfo(tag){
  var b = document.getElementById('barD');
  if(!b) return tag + ' (没有 barD)';
  var cs = getComputedStyle(b), r = R(b);
  var btns = b.querySelectorAll('button[data-dstep]'), vis = [], allIn = true;
  for(var i = 0; i < btns.length; i++){
    var br = btns[i].getBoundingClientRect();
    var inx = (Math.round(br.width) > 0 && br.right <= window.innerWidth + 1 && br.left >= -1);
    if(!inx) allIn = false;
    vis.push(btns[i].getAttribute('data-dstep') + ':' + (inx ? '可见' : ('看不见right=' + Math.round(br.right))));
  }
  return {txt: tag + ' position=' + cs.position + ' display=' + cs.display + ' overflowX=' + cs.overflowX
      + ' rect=' + JSON.stringify(r) + ' 视口=' + window.innerWidth + 'x' + window.innerHeight
      + ' 布局宽=' + document.documentElement.clientWidth
      + ' 距底=' + Math.round(window.innerHeight - r.bottom) + 'px'
      + ' 按钮=' + vis.join(' '),
    pos: cs.position, disp: cs.display, offBottom: (window.innerHeight - r.bottom), width: r.w, allIn: allIn,
    n: btns.length};
}
function flush(){
  var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
  document.body.appendChild(d);
}
function check(tag, wantVisible){
  var b = barInfo(tag);
  if(typeof b === 'string'){ o.push(b); return b; }
  o.push(b.txt);
  if(wantVisible){
    ok(b.pos === 'fixed', tag + '：底栏是 fixed（不是跟着文档跑）');
    ok(Math.abs(b.offBottom) <= 4, tag + '：底栏贴着屏幕底（距底 ' + Math.round(b.offBottom) + 'px）');
    ok(b.width <= window.innerWidth + 1, tag + '：底栏不比屏幕宽（' + Math.round(b.width) + ' ≤ ' + window.innerWidth + '）');
    ok(b.allIn && b.n === 4, tag + '：4 个按钮都在屏幕内（' + b.n + ' 个）');
  }
  return b;
}
setTimeout(function(){
  try{
    /* 1) 进「连接相机」页签，并把"已连接"开关打开（否则 showStep(2/3/4) 会被守卫拦回第 1 步） */
    try{ document.getElementById('tabCam').click(); }catch(e){ o.push('点 tabCam 报错：' + e.message); }
    setTimeout(function(){
      try{
        document.body.classList.add('cam-on');
        if(window.__om3setConn) window.__om3setConn(true);
      }catch(e){ o.push('置 cam-on 报错：' + e.message); }
      setTimeout(function(){
        try{
          check('①连接页', true);
          var h1 = document.body.scrollHeight;
          /* 2) 点底栏「写入」= 第 3 步 */
          var wb = document.querySelector('#barD button[data-dstep="3"]');
          if(wb) wb.click(); else o.push('找不到底栏「写入」按钮');
          setTimeout(function(){
            var h3a = document.body.scrollHeight;
            /* 3) 第 3 步的日志框塞满内容（复刻用户的现场：点写入后多了一堆内容） */
            var box = document.getElementById('camOut3');
            if(box){
              var t = '';
              for(var i = 0; i < 40; i++) t += '第 ' + i + ' 行：相机报 datasize=55422　实读=82614 字节　（长文本占位，模拟写入日志）\n';
              box.textContent = t;
            }
            setTimeout(function(){
              var h3b = document.body.scrollHeight;
              o.push('  页面高度：①=' + h1 + ' → ③=' + h3a + ' → ③+日志=' + h3b);
              check('③写入页(还没滚)', true);
              window.scrollTo(0, document.body.scrollHeight);
              setTimeout(function(){
                check('③滚到最底', true);
                /* 4) 人为把底栏弄歪（模拟真机上 fixed 失效 / 底栏跑到文档末尾）→
                      pinBars() 每秒兜一次，应该在 1.5 秒内自动钉回屏幕底、宽度也不超屏 */
                var bd = document.getElementById('barD');
                bd.style.setProperty('position','static','important');
                bd.style.setProperty('top','auto','important');
                bd.style.setProperty('bottom','auto','important');
                bd.style.setProperty('width','1600px','important');
                setTimeout(function(){
                  o.push('  弄歪之后：' + barInfo('').txt);
                  if(window.__om3pinBars) window.__om3pinBars();
                  setTimeout(function(){
                    check('弄歪→自愈后', true);
                    /* 5) fixed 在这台设备上"真的不生效"那种情况：直接用兜底（绝对定位 + 按滚动位置算 top）。
                         本地 Chrome 的 fixed 永远正常，所以这条分支平时跑不到 —— 这里直接调它，验**机制**。 */
                    var bd2 = document.getElementById('barD');
                    bd2.style.setProperty('position','static','important');
                    bd2.style.setProperty('top','120px','important');
                    if(window.__om3barAbsPin) window.__om3barAbsPin(bd2);
                    var ra = bd2.getBoundingClientRect();
                    o.push('  兜底(fixed 失效)：position=' + getComputedStyle(bd2).position
                           + ' 距底=' + Math.round(window.innerHeight - ra.bottom) + 'px 宽=' + Math.round(ra.width));
                    ok(getComputedStyle(bd2).position === 'absolute', '★fixed 失效时切到「绝对定位 + 跟滚动算位置」');
                    ok(Math.abs(window.innerHeight - ra.bottom) <= 4,
                       '★兜底之后贴在屏幕底（距底 ' + Math.round(window.innerHeight - ra.bottom) + 'px）');
                    ok(Math.round(ra.width) <= window.innerWidth + 1,
                       '★兜底之后宽度不超屏（' + Math.round(ra.width) + ' ≤ ' + window.innerWidth + '）');
                    window.scrollTo(0, (window.pageYOffset || 0) + 400);
                    setTimeout(function(){
                      if(window.__om3barAbsPin) window.__om3barAbsPin(bd2);
                      var rb = bd2.getBoundingClientRect();
                      o.push('  兜底 + 下滚 400px：距底=' + Math.round(window.innerHeight - rb.bottom)
                             + 'px  scrollY=' + Math.round(window.pageYOffset));
                      ok(Math.abs(window.innerHeight - rb.bottom) <= 4,
                         '★★滚动之后兜底仍然贴屏幕底（这就是"跟着滚动算位置"的意义）');
                      o.push('  #barD 父节点=' + document.getElementById('barD').parentNode.tagName
                             + ' 累计 js 报错=' + window.__errs.length + ' 失败项=' + fails.length);
                      flush();
                    }, 250);
                  }, 300);
                }, 300);
              }, 400);
            }, 400);
          }, 700);
        }catch(e){ o.push('探针异常：' + (e && e.message ? e.message : e)); flush(); }
      }, 900);
    }, 400);
  }catch(e){ o.push('探针异常(外)：' + (e && e.message ? e.message : e)); flush(); }
}, 2600);
"""
tail = '<script>' + JS + '</script>'
i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_barstep3.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\obarstep3'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=40000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
if kk > 0:
    print(dom[kk:].split('>', 1)[1].split('</pre>')[0])
else:
    open(TMP + r'\barstep3_dump.html', 'w', encoding='utf-8', newline='').write(dom)
    print('无输出 DOM=%d  DBGOUT在全文? %s' % (len(dom), 'DBGOUT' in dom))
    print('dump → ' + TMP + r'\barstep3_dump.html')
