# -*- coding: utf-8 -*-
"""底栏"写入之后才开始跟着滚"—— 写入前后各量一次，找出写入到底改变了什么。

用户 2026-09-23 补充：底栏跟着跑是**写入之后**才出现的。
这个脚本：先用假相机真的跑一次写入，然后逐项对比写入前/后的
  ① 页面有没有横向溢出（WebView 里一旦横向溢出，就可能变成可以平移 → fixed 元素看起来跟着动）
  ② #barD 祖先链上有没有多出 transform/filter/will-change/contain
  ③ body/html 的 overflow / 尺寸 / 类名
  ④ 谁把页面撑宽了（找出右边缘超过视口的元素）

用法：python scripts/dv_barD2.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

head = r"""<script>
window.__OM3_APP__=1;
window.__errs = [];
window.addEventListener('error', function(e){ window.__errs.push('ERR ' + e.message); });
window.__cam = { text:'', buf:'', calls:[], rebooted:false, declared:0 };
window.XMLHttpRequest = function(){
  var self = this;
  self.readyState = 0; self.status = 0; self.responseText = '';
  self.open = function(m, u){ self._u = String(u); };
  self.setRequestHeader = function(){};
  self.send = function(body){
    var u = self._u, q = (u.split('?')[1] || ''), path = u.replace(/^https?:\/\/[^\/]+\//, '');
    var st = 200, txt = '';
    if(/^send_partialmysetdata/.test(path)){
      var off = +((/offset=(\d+)/.exec(q)) || [])[1];
      window.__cam.buf = (window.__cam.buf || '').slice(0, off) + String(body || '');
    }
    else if(/^set_mysetdatasize/.test(path)){ window.__cam.declared = +((/size=(\d+)/.exec(q)) || [])[1]; st = 200; txt = 'ok'; }
    else if(/^get_mysetrestorestate/.test(path)){ st = 200; txt = '<status>success</status>'; if(window.__cam.buf) window.__cam.text = window.__cam.buf; }
    else if(/^request_getmysetdata/.test(path)){ st = 200; txt = 'ok'; }
    else if(/^get_mysetbackupstate/.test(path)){ st = 200; txt = '<status>idle</status>'; }
    else if(/^get_mysetdatasize/.test(path)){ st = 200; txt = '<size>' + window.__cam.text.length + '</size>'; }
    else if(/^get_partialmysetdata/.test(path)){ st = 200; txt = window.__cam.text; }
    else if(/^exec_reboot/.test(path)){ st = 200; txt = 'rebooting'; window.__cam.rebooted = true; }
    else { st = 200; txt = path.indexOf('switch_cammode') === 0 ? 'ok' : ''; }
    self.status = st; self.responseText = txt; self.readyState = 4;
    setTimeout(function(){ if(self.onreadystatechange) self.onreadystatechange(); }, 0);
  };
};
function measure(tag){
  var o = [], iw = window.innerWidth, ih = window.innerHeight;
  var de = document.documentElement, b = document.body;
  o.push('【' + tag + '】');
  o.push('  视口 ' + iw + '×' + ih + ' · 页面 scrollWidth=' + de.scrollWidth + ' scrollHeight=' + de.scrollHeight
       + ' → 横向溢出=' + (de.scrollWidth - iw) + 'px');
  o.push('  body scrollWidth=' + b.scrollWidth + '  offsetWidth=' + b.offsetWidth
       + ' · html/body overflow=' + getComputedStyle(de).overflow + '/' + getComputedStyle(b).overflow);
  o.push('  html/body transform=' + getComputedStyle(de).transform + ' / ' + getComputedStyle(b).transform
       + ' · filter=' + getComputedStyle(de).filter + ' / ' + getComputedStyle(b).filter
       + ' · will-change=' + getComputedStyle(de).willChange + ' / ' + getComputedStyle(b).willChange);
  o.push('  body.className=' + JSON.stringify(b.className) + '  body.style=' + JSON.stringify(b.getAttribute('style') || ''));
  var bar = document.getElementById('barD');
  if(bar){
    var q2 = bar.getBoundingClientRect();
    o.push('  #barD top=' + Math.round(q2.top) + ' bottom=' + Math.round(q2.bottom)
         + '（视口底 ' + ih + '）position=' + getComputedStyle(bar).position);
    var chain = bar, depth = 0, bad = [];
    while(chain && chain.nodeType === 1 && depth < 8){
      var c = getComputedStyle(chain);
      var t = [];
      if(c.transform !== 'none') t.push('transform=' + c.transform);
      if(c.filter !== 'none') t.push('filter=' + c.filter);
      if(c.willChange !== 'auto') t.push('will-change=' + c.willChange);
      if(c.contain !== 'none') t.push('contain=' + c.contain);
      if(t.length) bad.push((chain.id ? ('#' + chain.id) : chain.tagName) + '：' + t.join(','));
      chain = chain.parentElement; depth++;
    }
    o.push('  #barD 祖先链上破坏 fixed 的属性：' + (bad.length ? ('★' + bad.join('｜')) : '无'));
  }
  /* 谁把页面撑宽了 */
  var wide = [], all = document.querySelectorAll('body *');
  for(var i = 0; i < all.length; i++){
    var el = all[i], r = el.getBoundingClientRect();
    if(r.width <= 0) continue;
    if(r.right > iw + 1){
      wide.push((el.id ? ('#' + el.id) : (el.className ? ('.' + String(el.className).split(' ')[0]) : el.tagName))
        + '(right=' + Math.round(r.right) + ')');
      if(wide.length >= 8) break;
    }
  }
  o.push('  右边缘超过视口的元素：' + (wide.length ? wide.join(' ') : '无 ✓'));
  o.push('  js 报错=' + window.__errs.length);
  return o.join('\n');
}
window.__measure = measure;
</script>"""

JS = r"""
setTimeout(function(){
  var out = [];
  /* 先连上、切到写入页（和用户报的场景一致） */
  document.body.classList.add('cam-on');
  document.getElementById('tabCam').click();
  setTimeout(function(){
    var b = document.querySelector('#barD button[data-dstep="3"]');
    if(b) b.click();
    setTimeout(function(){
      out.push(window.__measure('写入之前'));

      /* 造一套方案 + 假相机数据，然后真的跑一次「我的配方 → 写入相机」 */
      var CRLF = String.fromCharCode(13) + String.fromCharCode(10);
      var recA = { n:'甲', a:'t', v:[1,2,3,0,0,0,0,0,0,0,0,0], hi:1, mid:-1, sh:2, eff:0, shp:0, con:1 };
      var recB = { n:'乙', a:'t', v:[0,0,0,0,0,0,3,3,3,0,0,0], hi:0, mid:0, sh:0, eff:0, shp:0, con:0 };
      var raw = {}, t = window.__om3buildPayload(recA, 1, 'C1', 'OM-3');
      t.split(String.fromCharCode(10)).forEach(function(l){
        l = l.replace(String.fromCharCode(13), '');
        var p = l.split(',');
        if(p.length >= 3 && p[0] === '2' && p[1]) raw[p[1]] = p.slice(2).join(',');
      });
      var camText = window.__om3buildPayload(recB, 1, 'C1', 'OM-3');
      while(camText.length < 12000) camText += '2,MODE_COLOR_CREATOR_2_VIVID_SET4_1,MODE_STEP_0' + CRLF;
      window.__cam.text = camText; window.__cam.buf = ''; window.__cam.declared = 0; window.__cam.rebooted = false;

      var setA = { id:'t1', name:'写入测试甲', desc:'', from:'myset1', camera:'OM-3',
                   slots:{ 1:{ vivid: recA.v, raw: raw, used: 9 } } };
      window.__om3mpWriteOne(setA, 1);

      var waited = 0;
      var iv = setInterval(function(){
        waited += 300;
        if(window.__cam.rebooted || waited > 30000){
          clearInterval(iv);
          /* 关掉任务弹窗，模拟用户点完「关闭」之后的样子 */
          var cl = document.getElementById('taskClose');
          if(cl) cl.click();
          setTimeout(function(){
            out.push(window.__measure('写入之后（弹窗已关）'));
            /* 再模拟"切走再切回写入页" */
            var b1 = document.querySelector('#barD button[data-dstep="1"]');
            if(b1) b1.click();
            setTimeout(function(){
              var b3 = document.querySelector('#barD button[data-dstep="3"]');
              if(b3) b3.click();
              setTimeout(function(){
                out.push(window.__measure('切走再切回写入页'));
                var d = document.createElement('pre'); d.id = 'DBGOUT';
                d.textContent = out.join('\n');
                document.body.appendChild(d);
              }, 700);
            }, 500);
          }, 600);
        }
      }, 300);
    }, 700);
  }, 800);
}, 3000);
"""
tail = '<script>' + JS + '</script>'

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_barD2.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\obarD2'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=60000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
