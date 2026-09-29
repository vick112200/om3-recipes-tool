# -*- coding: utf-8 -*-
"""「我的配方」槽位布局 + 描述带入 + 贴底浮层，三条实测（用户 2026-09-24）。

1) 槽位布局：色轮**单独一行居中**、内容全宽 —— 不能再出现"色轮占一列、下面空一大块"
   （实测旧版：色轮 100×100 在左，右列内容 607 高 → 色轮下方空 507px）
2) 把内置配方放进我的配方时，**描述（6 行）+ 标签一起带过来**
3) 「展开全部」按钮已删掉（和回到顶部 ↑ 重叠），只留 ↑；说明按钮挪到 ↑ 上面不重叠

用法：python scripts/dv_mplayout.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

PRE = r"""<script>
window.__OM3_APP__=1;
window.__errs = [];
window.addEventListener('error', function(e){ window.__errs.push('ERR ' + e.message); });
window.addEventListener('unhandledrejection', function(e){ window.__errs.push('REJ ' + String(e.reason)); });
</script>"""

JS = r"""
setTimeout(function(){
  var o = [], fails = [];
  function ok(c, m){ o.push((c ? '  [OK ] ' : '  [FAIL] ') + m); if(!c) fails.push(m); }
  function el(id){ return document.getElementById(id); }
  function R(e){ if(!e) return null; var r = e.getBoundingClientRect();
    return { x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) }; }
  function fin(){
    o.push('累计 js 报错=' + (window.__errs ? window.__errs.length : 0) + '  om3errs=' + (window.__om3errs || 0));
    if(window.__errs && window.__errs.length) o.push('  ' + window.__errs.slice(0, 3).join(' | '));
    o.push('--- 结果：' + (fails.length ? ('失败 ' + fails.length + ' 项') : '全部通过') + ' ---');
    var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
    document.body.appendChild(d);
  }
  var steps = [];
  function step(f){ steps.push(f); }
  function run(){ if(!steps.length) return fin(); var f = steps.shift();
    try{ f(run); }catch(e){ o.push('  !! 步骤抛错：' + (e && e.message ? e.message : e)); fin(); } }

  try{ localStorage.clear(); }catch(e){}
  localStorage.setItem('om3sets', JSON.stringify([
    { id:'P', name:'布局探针', desc:'', from:'myset1', camera:'OM-3', slots:{
        1:{ vivid:[2,3,2,2,0,-1,-3,-2,-1,0,0,2], raw:{}, used:9, hi:-1, mid:2, lo:-2, eff:0, shp:0, con:1, name:'有描述的槽',
            feel:'饱和度略高、色调偏冷，画面通透清爽。', key:'往上推的是 蓝紫 +2、蓝 +2。', tone:'暗部略提（Sh +2）；高光略压（Hi -2）。',
            good:'阴天街拍、建筑、水面', bad:'想要低饱和氛围时', tip:'基本可以直接挂机用', tags:['微浓','偏冷','柔和'] },
        2:{ vivid:[1,0,0,0,0,0,0,0,0,0,0,1], raw:{'MODE_COLOR_CREATOR_2_TONE_CONTROL_HIGH_SET2':'MODE_STEP_M3'}, used:2, name:'没描述的槽' },
        3:null, 4:null } }
  ]));

  /* ===== 1. 槽位布局 ===== */
  step(function(next){
    el('tabMine').click();
    window.__om3mpRender();
    window.__om3mpDetail(0);
    setTimeout(function(){
      var rows = document.querySelectorAll('#mpList .mpsrow');
      ok(rows.length === 4, '详情页 4 个槽位行（实际 ' + rows.length + '）');
      var bad = 0;
      for(var i = 0; i < rows.length; i++){
        var row = rows[i], w = row.querySelector('svg.mpwheel'), main = row.querySelector('.mpmain');
        if(!w || !main) continue;
        var rr = R(row), wr = R(w), mr = R(main);
        var centered = Math.abs((wr.x + wr.w / 2) - (rr.x + rr.w / 2)) <= 2;
        var fullW = Math.abs(mr.w - rr.w) <= 2;
        var sideBySide = Math.abs(mr.y - wr.y) < 20;      /* 内容还在右边同一行 = 旧的"占一列" */
        var big = (wr.w >= 150);                          /* 色轮要够大（不是小缩略图） */
        if(!centered || !fullW || sideBySide || !big) bad++;
        if(i === 0){
          o.push('  第1行：row=' + JSON.stringify(rr) + ' 色轮=' + JSON.stringify(wr) + ' 内容=' + JSON.stringify(mr));
          o.push('    居中=' + centered + ' 内容全宽=' + fullW + ' 还是左右两列=' + sideBySide + ' 色轮够大=' + big);
        }
      }
      ok(bad === 0, '★4 个槽位都是"色轮单独一行居中 + 内容全宽"（不合格 ' + bad + ' 个）');
      var r0 = rows[0], w0 = r0 ? r0.querySelector('svg.mpwheel') : null, m0 = r0 ? r0.querySelector('.mpmain') : null;
      if(w0 && m0){
        var gap = Math.round(m0.getBoundingClientRect().top - w0.getBoundingClientRect().bottom);
        o.push('  色轮底 → 内容顶 间距=' + gap + 'px');
        ok(gap >= 0 && gap < 40, '★色轮下方没有大片空白（间距 ' + gap + 'px）');
      }
      next();
    }, 500);
  });

  /* ===== 2. 内置配方 → 我的配方：描述一起带过来 ===== */
  step(function(next){
    var card = document.querySelector('.card[id^="r-"]');
    ok(!!card, '页面里有内置配方卡（#' + (card && card.id) + '）');
    var richEl = card ? card.querySelector('.fold.fmine .foldbody') : null;
    var richTxt = richEl ? String(richEl.textContent || '') : '';
    ok(richTxt.indexOf('画面感觉') >= 0, '这张卡自带描述（含「画面感觉」行）');
    var ts = card ? card.querySelectorAll('.tags span') : [];
    var tags = [];
    for(var j = 0; j < ts.length; j++) tags.push(String(ts[j].textContent).trim());
    o.push('  卡片标签：' + tags.join(' '));

    var btn = card ? card.querySelector('.omsavebtn') : null;
    ok(!!btn, '卡片上有「加入我的方案」按钮');
    if(!btn){ next(); return; }

    /* 弹窗是自绘的：点选项 → 确定（可能两层：先方案/槽，再档位） */
    function choices(){ return document.querySelectorAll('#omask [data-choice]'); }
    function clickChoice(re){
      var cs = choices();
      for(var i = 0; i < cs.length; i++) if(re.test(String(cs[i].textContent))){ cs[i].click(); return true; }
      return false;
    }
    function clickOk(){
      var bs = document.querySelectorAll('#omask button');
      for(var i = 0; i < bs.length; i++) if(/确定|加进这个槽|OK|好$/.test(String(bs[i].textContent).trim())){ bs[i].click(); return true; }
      return false;
    }
    var seq = [ /布局探针|槽 1/, /槽 3/, /确定/ ];
    var li = 0;
    function after(){
      var a2 = JSON.parse(localStorage.getItem('om3sets') || '[]');
      var got = null;
      for(var i = 0; i < a2.length; i++){
        var s = a2[i];
        for(var k = 1; k <= 4; k++){
          var one = s.slots && s.slots[k];
          if(one && one.feel) got = { set: s.name, slot: k, one: one };
        }
      }
      if(got){
        o.push('  弹窗路径放进来的槽：' + got.set + ' 槽' + got.slot);
        o.push('    feel=' + String(got.one.feel).slice(0, 26) + '…');
        o.push('    good=' + String(got.one.good || '').slice(0, 20) + '  tags=' + JSON.stringify(got.one.tags || []));
      } else {
        o.push('  （弹窗路径没抓到带 feel 的槽 —— 下面用同一入口直接验）');
      }
      ok(!!got, '★走「加入我的方案」按钮 → 槽里带上了描述');
      if(got){
        ok(!!got.one.tone && !!got.one.good && !!got.one.bad, '★画面感觉/影调/适合/避开 都在');
        ok(!!(got.one.tags && got.one.tags.length), '★标签也带过来了 ' + JSON.stringify(got.one.tags || []));
      }
      /* 兜底：同一入口（richFromCard → putRecInSlot）一定带上描述 */
      try{
        var rec = (window.__OM3RECIPES__ || [])[0];
        var rich = null;
        try{ rich = window.__om3richFromCard ? window.__om3richFromCard(card) : null; }catch(e){ rich = null; }
        if(!rich || !rich.feel){
          /* 页面里没暴露 richFromCard 时，从卡片文字里手工抓（和实现同一套标签） */
          rich = { feel:'', key:'', tone:'', good:'', bad:'', tip:'', tags: [] };
          var map = { '画面感觉':'feel', '色彩重点':'key', '影调':'tone', '适合':'good', '避开':'bad', '提示':'tip' };
          var rows2 = card.querySelectorAll('.foldbody .row');
          for(var q2 = 0; q2 < rows2.length; q2++){
            var mk2 = rows2[q2].querySelector('.mk'), mv2 = rows2[q2].querySelector('.mv');
            if(mk2 && mv2){ var kk = map[String(mk2.textContent).trim()]; if(kk && !rich[kk]) rich[kk] = String(mv2.textContent).trim(); }
          }
          var tg2 = card.querySelectorAll('.tags span');
          for(var z2 = 0; z2 < tg2.length; z2++){ var x2 = String(tg2[z2].textContent).trim(); if(x2) rich.tags.push(x2); }
        }
        ok(!!rich.feel, '能取到卡片描述（richFromCard 等价物）');
        window.__om3putRec(0, 4, rec, '带描述测试', '来自内置配方', rich);
        var a3 = JSON.parse(localStorage.getItem('om3sets') || '[]');
        var one4 = a3[0] && a3[0].slots && a3[0].slots[4];
        o.push('  兜底（同一入口 putRecInSlot）：feel=' + (one4 && one4.feel ? '有' : '无')
               + ' tags=' + JSON.stringify((one4 && one4.tags) || []));
        ok(!!(one4 && one4.feel && one4.tone), '★putRecInSlot 一定会把传进来的描述写进槽');
      }catch(e){ ok(false, '兜底步骤抛错：' + (e && e.message ? e.message : e)); }

      el('tabMine').click();
      window.__om3mpRender();
      setTimeout(function(){
        var items = document.querySelectorAll('#mpList .mpitem');
        var found = false;
        for(var q = 0; q < items.length; q++) if(String(items[q].textContent).indexOf('画面感觉') >= 0) found = true;
        ok(found, '★详情页能看到带过来的描述（含「画面感觉」行）');
        next();
      }, 300);
    }
    function pump(){
      if(li >= seq.length){ setTimeout(after, 300); return; }
      setTimeout(function(){
        clickChoice(seq[li++]);
        setTimeout(function(){ clickOk(); setTimeout(pump, 380); }, 320);
      }, 380);
    }
    btn.click();
    setTimeout(pump, 450);
  });

  /* ===== 3. 贴底浮层 ===== */
  step(function(next){
    var fb = el('foldbar'), top = el('top');
    ok(!document.getElementById('foldbtn'), '★「展开全部」按钮已删掉（页面里没有 #foldbtn）');
    ok(!!top, '「回到最上」还在（#top）');
    o.push('  #foldbar 里的按钮：' + (fb ? Array.prototype.map.call(fb.querySelectorAll('button'), function(b){ return b.id || String(b.textContent).trim(); }).join(',') : '(没有)'));
    var fi = document.getElementById('foldinfo');
    if(fb){ fb.classList.add('on'); fb.style.display = 'flex'; }
    if(fi){ fi.style.display = 'inline-block'; }
    if(top){ top.classList.add('on'); top.style.display = 'block'; }
    setTimeout(function(){
      /* 两者都是 fixed + bottom: calc(var(--om3barh) + Npx) → 直接比 CSS 的 bottom 值最可靠
         （元素可能因为当前页签没有折叠而被 sync() 隐藏，量 boundingBox 会得到 0） */
      function px(v){ var m = /(-?\d+(?:\.\d+)?)px/.exec(String(v || '')); return m ? parseFloat(m[1]) : NaN; }
      var tb = px(getComputedStyle(top).bottom), fbb = px(getComputedStyle(fb).bottom);
      var th = Math.round(top.getBoundingClientRect().height) || 44;
      o.push('  CSS bottom：#top=' + tb + 'px（高 ' + th + '）  #foldbar=' + fbb + 'px');
      ok(tb === tb && fbb === fbb, '两个浮层的 bottom 都能量到（不是 auto）');
      ok(fbb >= tb + th, '★「说明」在「回到最上」上面，不重叠（说明底 ' + fbb + ' ≥ 回到最上顶 ' + (tb + th) + '）');
      next();
    }, 250);
  });

  run();
}, 2600);
"""

tail = '<script>' + JS + '</script>'
k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + PRE + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_mplayout.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\omplayout'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,1400',
                    '--virtual-time-budget=45000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
