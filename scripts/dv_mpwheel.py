# -*- coding: utf-8 -*-
"""「我的配方」槽位色轮渲染 —— 验收测试（先写测试，再写实现）。

判定方式：拿**页面上已烘焙好的内置配方卡色轮**当基准（它们和配方卡视觉一致），
用同一组 12 个色轴值调用新函数，逐点比较多边形顶点。

用法：python scripts/dv_mpwheel.py
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
  var o = [], fails = [];
  function ok(c, msg){ o.push((c ? '  [OK ] ' : '  [FAIL] ') + msg); if(!c) fails.push(msg); }
  function numlist(s){ return (String(s).match(/-?\d+(?:\.\d+)?/g) || []).map(Number); }

  /* ---------- 1) 从页面取基准：烘焙好的配方卡色轮 ---------- */
  var baked = [];
  var svgs = document.querySelectorAll('svg.wheel');
  for(var i = 0; i < svgs.length; i++){
    var sv = svgs[i];
    var nx = sv.nextElementSibling;
    if(!nx || !nx.classList || !nx.classList.contains('vals')) continue;
    var pm = sv.querySelector('polygon');
    if(!pm) continue;
    var vals = numlist(nx.textContent);
    var pts = pm.getAttribute('points').split(/\s+/).map(function(p){
      var xy = p.split(','); return [parseFloat(xy[0]), parseFloat(xy[1])];
    });
    if(vals.length !== 12 || pts.length !== 12) continue;
    baked.push({ vals: vals, pts: pts, el: sv });
  }
  o.push('页面里可作基准的配方卡色轮：' + baked.length + ' 个');

  /* ---------- 2) 新函数必须在 ---------- */
  var fn = window.__om3wheelSVG;
  ok(typeof fn === 'function', 'window.__om3wheelSVG 已暴露且是函数（typeof=' + (typeof fn) + '）');
  if(typeof fn !== 'function'){
    var d0 = document.createElement('pre'); d0.id = 'DBGOUT';
    d0.textContent = o.join('\n'); document.body.appendChild(d0); return;
  }

  /* ---------- 3) 逐点比对（取若干个不同的取值组合） ---------- */
  var seen = {}, samples = [];
  for(var b = 0; b < baked.length; b++){
    var key = baked[b].vals.join(',');
    if(seen[key]) continue;
    seen[key] = 1; samples.push(baked[b]);
    if(samples.length >= 10) break;
  }
  var worst = 0, worstInfo = '', compared = 0;
  for(var s = 0; s < samples.length; s++){
    var html = fn(samples[s].vals);
    var m = /points="([^"]+)"/.exec(html);
    if(!m){ o.push('  [FAIL] 生成的 SVG 里没有 polygon：vals=' + samples[s].vals.join(',')); fails.push('no polygon'); continue; }
    var mine = m[1].split(/\s+/).map(function(p){
      var xy = p.split(','); return [parseFloat(xy[0]), parseFloat(xy[1])];
    });
    if(mine.length !== 12){ ok(false, '顶点数应为 12，实际 ' + mine.length); continue; }
    var mx = 0;
    for(var k = 0; k < 12; k++){
      mx = Math.max(mx, Math.abs(mine[k][0] - samples[s].pts[k][0]), Math.abs(mine[k][1] - samples[s].pts[k][1]));
    }
    compared++;
    if(mx > worst){ worst = mx; worstInfo = samples[s].vals.join(','); }
  }
  o.push('  比对样本数=' + compared);
  ok(compared >= 5, '至少比对了 5 组不同取值（实际 ' + compared + '）');
  ok(worst < 0.15, '与配方卡色轮逐点最大偏差 ' + worst.toFixed(3) + 'px < 0.15px（最差样本 ' + worstInfo + '）');

  /* ---------- 4) 极简版：不画 1..12 数字 ---------- */
  var h1 = fn(samples[0].vals);
  ok(h1.indexOf('<text') < 0, '极简版不含 <text>（数字序号）');
  ok((h1.match(/<line/g) || []).length === 12, '12 根彩色轴线（实际 ' + (h1.match(/<line/g) || []).length + '）');
  ok(/<circle/.test(h1), '有基线圈');
  var bakedColors = [];
  var bakedLines = samples[0].el.querySelectorAll('line');
  for(var q = 0; q < bakedLines.length; q++) bakedColors.push(bakedLines[q].getAttribute('stroke'));
  var mineColors = [];
  var reCol = /<line[^>]*stroke="([^"]+)"/g, mm;
  while((mm = reCol.exec(h1))) mineColors.push(mm[1]);
  ok(JSON.stringify(mineColors) === JSON.stringify(bakedColors),
     '12 根轴颜色与配方卡逐位一致（' + mineColors.join(',') + '）');

  /* ---------- 5) 异常输入 ----------
     规格 §4「异常路径」：「vivid 缺失 / 不是数组 / 长度<12」→ 空轮；
     「元素不是有限数字」→ **该轴按 0 处理**（所以全 NaN 是"画在基线上的退化多边形"，
     属正常行为，不是空轮）。这里按规格分开断言。 */
  function tryCall(v, tag){
    try{ var r = fn(v); return { ok: true, html: r }; }
    catch(e){ return { ok: false, err: String(e && e.message ? e.message : e) }; }
  }
  var emptyCases = [
    [null, 'null'], [undefined, 'undefined'], [[], '[]'], [[1,2], '长度不足'], ['abc', '字符串']
  ];
  for(var c = 0; c < emptyCases.length; c++){
    var r = tryCall(emptyCases[c][0], emptyCases[c][1]);
    ok(r.ok, '输入 ' + emptyCases[c][1] + ' 不抛错' + (r.ok ? '' : '（' + r.err + '）'));
    if(r.ok) ok(!/points="/.test(r.html), '输入 ' + emptyCases[c][1] + ' 画空轮（无多边形）');
  }
  var rn = tryCall([NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN,NaN], '全 NaN');
  ok(rn.ok, '全 NaN 不抛错');
  if(rn.ok){
    var mn2 = /points="([^"]+)"/.exec(rn.html);
    ok(!!mn2, '全 NaN 按规格每轴当 0 → 仍有多边形（退化到基线圈上，不是空轮）');
    if(mn2){
      var ns = mn2[1].split(/\s+/).map(function(p){
        var xy = p.split(','), dx = parseFloat(xy[0]) - 130, dy = parseFloat(xy[1]) - 130;
        return Math.sqrt(dx*dx + dy*dy);
      });
      var bad2 = ns.filter(function(x){ return Math.abs(x - 49.22) > 0.15; });
      ok(bad2.length === 0, '全 NaN 的顶点半径都落在基线 49.22（实际 ' + ns[0].toFixed(2) + '…）');
    }
  }
  var big = [9,9,9,9,9,9,-9,-9,-9,-9,-9,-9];
  var rb = tryCall(big, '越界');
  ok(rb.ok, '越界输入不抛错');
  if(rb.ok){
    var mb = /points="([^"]+)"/.exec(rb.html);
    if(mb){
      var maxr = 0;
      mb[1].split(/\s+/).forEach(function(p){
        var xy = p.split(','), dx = parseFloat(xy[0]) - 130, dy = parseFloat(xy[1]) - 130;
        maxr = Math.max(maxr, Math.sqrt(dx*dx + dy*dy));
      });
      ok(maxr <= 80.2 + 0.2, '越界值没有画到轮外（最大半径 ' + maxr.toFixed(2) + '，上限 80.0）');
    } else ok(false, '越界输入应仍有多边形');
  }

  /* ---------- 6) 详情页：真渲染出来 + 尺寸 + 按钮还在 ---------- */
  try{
    localStorage.setItem('om3sets', JSON.stringify([
      { id:'w1', name:'色轮验收', desc:'d', from:'myset1', camera:'OM-3',
        slots:{ 1:{ vivid:[3,2,1,1,1,5,4,5,2,0,3,3], raw:{}, used:9 },
                2:null, 3:{ vivid:[0,0,0,0,0,0,0,0,0,0,0,0], raw:{}, used:0 }, 4:null } }
    ]));
  }catch(e){}
  document.getElementById('tabMine').click();
  setTimeout(function(){
    var first = document.querySelector('#mpList .mpitem');
    if(first) first.click();
    setTimeout(function(){
      var wheels = document.querySelectorAll('#mpList .mpwheel');
      ok(wheels.length === 4, '详情页 4 个槽位各有一个色轮（实际 ' + wheels.length + '）');
      var w0 = wheels[0];
      if(w0){
        var rr = w0.getBoundingClientRect();
        /* 2026-09-24：槽位改成上下堆叠后，色轮不再锁 100×100，而是 min(56vw,210px) 居中（见 dv_mplayout） */
        ok(Math.round(rr.width) === Math.round(rr.height) && rr.width >= 120 && rr.width <= 215,
           '色轮是正方形且尺寸合理（实际 ' + Math.round(rr.width) + '×' + Math.round(rr.height) + '，期望 ≈210）');
        o.push('  第 1 槽色轮：有多边形=' + !!w0.querySelector('polygon')
             + '  空槽(槽2)色轮：有多边形=' + (wheels[1] ? !!wheels[1].querySelector('polygon') : '?')
             + '  全 0 槽(槽3)色轮：有多边形=' + (wheels[2] ? !!wheels[2].querySelector('polygon') : '?'));
        ok(!!w0.querySelector('polygon'), '槽 1（有数据）画出多边形');
        ok(wheels[1] && !wheels[1].querySelector('polygon'), '槽 2（空）是空轮，无多边形');
      }
      /* 这套测试方案里 槽1 和 槽3 都非 null（槽3 是"全是 0"），所以各应有 1 组按钮 = 2 组 */
      var nw = document.querySelectorAll('#mpList button[data-w]').length;
      var nsh = document.querySelectorAll('#mpList button[data-sh]').length;
      var noe = document.querySelectorAll('#mpList button[data-oe]').length;
      ok(nw === 2 && nsh === 2 && noe === 2,
         '写入/分享/导出 .oes 按钮都在（两个非空槽各 1 组：' + nw + '/' + nsh + '/' + noe + '）');
      ok(!!document.getElementById('mpBack') && !!document.getElementById('mpDel'),
         '返回列表 / 删除方案 按钮仍在');

      /* 真点一下「分享这个槽」——光数个数证明不了事件还绑着（规格验收 5） */
      var sh1 = document.querySelector('#mpList button[data-sh="1"]');
      var lb = document.getElementById('camOut3');
      var len0 = lb ? (lb.textContent || '').length : 0;
      if(sh1) sh1.click();
      setTimeout(function(){
        var txt = lb ? (lb.textContent || '') : '';
        var added = txt.slice(len0);
        o.push('  调试：typeof navigator.clipboard=' + (typeof navigator.clipboard)
             + '  按钮存在=' + !!sh1 + '  日志尾部=' + JSON.stringify(txt.replace(/\s+/g, ' ').slice(-90)));
        ok(!!sh1 && added.length > 0 && /分享|剪贴板|复制/.test(added),
           '点「分享这个槽」确实有反应（新增日志：' + JSON.stringify(added.replace(/\s+/g, ' ').slice(0, 60)) + '）');
        o.push('累计 js 报错=' + window.__errs.length + '  om3errs=' + (window.__om3errs || 0));
        o.push('  报错内容=' + JSON.stringify(window.__errs));
        var d = document.createElement('pre'); d.id = 'DBGOUT';
        o.push('--- 结果：' + (fails.length ? ('失败 ' + fails.length + ' 项') : '全部通过') + ' ---');
        d.textContent = o.join('\n');
        document.body.appendChild(d);
      }, 400);
    }, 700);
  }, 700);
}, 3000);
"""
tail = ('<script>window.__errs=[];'
        "window.addEventListener('error',function(e){window.__errs.push(String(e.message));});"
        "window.addEventListener('unhandledrejection',function(e){window.__errs.push('REJ '+String(e.reason));});"
        '</script><script>' + JS + '</script>')

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_mpwheel.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\ompwheel'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=30000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
