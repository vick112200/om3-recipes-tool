# -*- coding: utf-8 -*-
"""第 41 轮验收：**滑动回到最初那版**（原生拖动 + CSS 吸附），JS 不再拦滚动。
跑法：python scripts/dv_scene41.py"""
import io, json, os, re, shutil, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')
SRC = r'D:\workspace\om3-handbook'
src = io.open(SRC + r'\app\base.html', encoding='utf-8').read()
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


print('=== 静态：JS 不再拦滑动 ===')
i0 = src.find("    /* ===== 滑动：**回到最初那版**")
i1 = src.find("    window.addEventListener('resize'", i0)
blk = src[i0:i1] if i0 > 0 and i1 > i0 else ''
A(bool(blk), "① 找到「回到最初那版」的滑动段落")
A(("pager.addEventListener('touchstart'" not in src) and ("pager.addEventListener('touchmove'" not in src)
  and ("pager.addEventListener('touchend'" not in src) and ("pager.addEventListener('wheel'" not in src),
  '① 代码里**没有**触摸/滚轮手势拦截（不再跟原生拖动打架）')
A('scGo' not in src, '① 全书已无 scGo（强制落点那套删掉了）')
A('pager.scrollTo' not in src and 'if (smooth)' not in blk, '① 没有"强制落点/兜底拽回"的代码（不会顶着用户的手）')
A("pager.addEventListener('scroll'" in blk and 'upd()' in blk, '② scroll 事件只用来更新位置标签')
A("pager.scrollBy({ left: -pager.clientWidth - 12" in blk and "pager.scrollBy({ left: pager.clientWidth + 12" in blk,
  '② ‹ › 按钮回到最初那种"翻一屏"（scrollBy）')
A('.scslide{flex:0 0 100%;scroll-snap-align:start;scroll-snap-stop:always;' in src,
  '③ **纯 CSS 的"一次只停一张"**：.scslide 加了 scroll-snap-stop:always')
A('.scpager{display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;' in src,
  '③ pager 仍是原生吸附（最初那版就是这套）')

# ---------------- 运行时 ----------------
d = SRC + r'\app\images'
shutil.rmtree(d, ignore_errors=True)
os.makedirs(d)
srcimg = SRC + r'\apk\assets\images'
need = set(re.findall(r'data-im="([^"]+)"', src))
sc = re.search(r'window\.__OM3SC__\s*=\s*(\[.*?\]);\n', src, re.S)
SC = json.loads(sc.group(1)) if sc else []
for x in SC:
    for it in x['items']:
        need.add(it['f'])
for f in sorted(need):
    sp = os.path.join(srcimg, f)
    if os.path.exists(sp):
        shutil.copy(sp, os.path.join(d, f))

JS = r"""
setTimeout(function(){
  var o = [];
  function ok(c, m){ o.push((c ? '[OK ] ' : '[FAIL] ') + m); }
  var pg = document.getElementById('scpager');
  function step(){ var s = pg.querySelector('.scslide'); return s ? (s.getBoundingClientRect().width + 12) : 0; }
  function pos(){ return document.getElementById('scpos').textContent; }
  function done(){ var d2 = document.createElement('pre'); d2.id = 'DBGOUT'; d2.textContent = o.join('\n'); document.body.appendChild(d2); }
  document.querySelector('#barABC button[data-p="C"]').click();
  setTimeout(function(){
    var st = step();
    ok(st > 100, '① pager 正常布局（步长 ' + Math.round(st) + 'px）');
    var sl0 = pg.querySelector('.scslide');
    ok(getComputedStyle(sl0).scrollSnapStop === 'always', '③ 浏览器认了 scroll-snap-stop=always（一次滑动只停一张）');
    ok(getComputedStyle(pg).scrollSnapType.indexOf('x') >= 0, '③ pager 是原生吸附：' + getComputedStyle(pg).scrollSnapType);
    pg.scrollLeft = st * 3;
    pg.dispatchEvent(new Event('scroll'));
    setTimeout(function(){
      ok(Math.abs(pg.scrollLeft - st * 3) < 30, '① 滚到第 4 张后**位置被保留**（' + Math.round(pg.scrollLeft) + ' / 期望 ' + Math.round(st * 3) + '）');
      ok(pos().indexOf('4 ') === 0, '② 位置标签跟着更新（' + pos() + '）');
      pg.scrollLeft = pg.scrollWidth;
      pg.dispatchEvent(new Event('scroll'));
      setTimeout(function(){
        ok(pg.scrollLeft > st * 5, '① 甩到底仍停在末尾（' + Math.round(pg.scrollLeft) + '，不会跳回第一张）');
        var one = pg.clientWidth + 12, calls = [], origBy = pg.scrollBy;
        pg.scrollBy = function(a){ calls.push(typeof a === 'object' ? a : {left:a}); };
        document.getElementById('scnext').click();
        document.getElementById('scprev').click();
        pg.scrollBy = origBy;
        var dn = calls[0] ? Math.round(calls[0].left) : null, up = calls[1] ? Math.round(calls[1].left) : null;
        ok(dn === Math.round(one), '② 点 › 传的是"往右一屏"：left=' + dn + '（期望 ' + Math.round(one) + '）');
        ok(up === -Math.round(one), '② 点 ‹ 传的是"往左一屏"：left=' + up + '（期望 ' + (-Math.round(one)) + '）');
        var sel = document.getElementById('scsel');
        sel.value = 's:night';
        sel.dispatchEvent(new Event('change', {bubbles: true}));
        setTimeout(function(){
          var n = document.querySelectorAll('#scpager .scslide').length;
          ok(n >= 1 && n < 20, '④ 下拉切「夜景霓虹」仍生效（' + n + ' 张）');
          ok(pg.scrollLeft < 5, '④ 换场景后回到第一张（' + Math.round(pg.scrollLeft) + '）');
          ok(window.__errs.length === 0, '⑤ 全程 0 JS 报错（' + window.__errs.length + '）');
          done();
        }, 800);
      }, 600);
    }, 600);
  }, 1500);
}, 2600);
"""
k = src.find('<body')
j = src.find('>', k) + 1
head = '<script>window.__OM3_APP__=1;window.__errs=[];window.onerror=function(m,s2,l){window.__errs.push(m+" @"+l)};' \
       'window.addEventListener("unhandledrejection",function(e){window.__errs.push("rej:"+e.reason)});</script>'
out = src[:j] + head + src[j:].replace('</body>', '<script>' + JS + '</script></body>', 1)
p = SRC + r'\app\_probe_scene41.html'
io.open(p, 'w', encoding='utf-8', newline='').write(out)
ud = r'C:\Users\82302\AppData\Local\Temp\omsc41b'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--hide-scrollbars', '--user-data-dir=' + ud, '--window-size=560,900',
                    '--virtual-time-budget=40000', '--dump-dom', 'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print('=== 运行时 ===')
if kk < 0:
    print('  [FAIL] 探针没拿到输出'); F += 1
else:
    body = dom[kk:].split('>', 1)[1].split('</pre>')[0]
    print(body)
    K += body.count('['); F += body.count('[FAIL]')
shutil.rmtree(d, ignore_errors=True)
try:
    os.remove(p)
except OSError:
    pass
print()
print('===== 结论：%s（%d 项，失败 %d）=====' % ('全部通过 ✅' if F == 0 else '有 %d 项失败 ❌' % F, K, F))
sys.exit(1 if F else 0)
