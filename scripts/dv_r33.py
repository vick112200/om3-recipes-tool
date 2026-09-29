# -*- coding: utf-8 -*-
"""第 33 轮（v2.19）验收探针。

覆盖本轮 6 件事：
  ① 目录面板跟着页签（原版方案🔍→#toc / 优化版🔍→#toc2）
     —— 块07 在捕获阶段独占 #tocbtn，块02 的 panel() 轮不到跑；只改块02 等于没改（本探针就是照出这条的）
  ② 目录锚点跨页签跳转（jumpToPane）
  ③ 场景对比卡的小色轮（占位 data-v → mpWheelSVG 填）+ 描述默认展开
  ④ 场景对比「一次滑动只换一张」（滚动停下后夹回一屏）
  ⑤ 「两条链路」卡（蓝牙 / Wi-Fi / HTTP 六种状态 + 结论文案）
  ⑥ 底栏三级兜底（fixed → sticky → absolute）+ barFollow 跟手

说明：本地 Chrome 的 position:fixed 永远正常，所以 sticky / absolute 那两级平时跑不到 ——
本探针直接调对应机制（sticky 样式组 / window.__om3barAbsPin / window.__om3barFollow）来验。

用法：python scripts/dv_r33.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

# 原生桥的替身（真机上是 Android 注入的 OM3Native）：两条链路要能自己摆状态
head = (
    "<script>window.__OM3_APP__=1;window.__errs=[];window.__errMsg={};"
    "window.addEventListener('error',function(e){var m=(e.message||'');"
    "window.__errs.push(m+' @'+(e.lineno||0));window.__errMsg[m]=(window.__errMsg[m]||0)+1;});"
    "window.addEventListener('unhandledrejection',function(e){var m=String(e.reason);"
    "window.__errs.push('REJ '+m);window.__errMsg['REJ '+m]=(window.__errMsg['REJ '+m]||0)+1;});"
    "window.__stubBle={conn:[],paired:[]};window.__stubSsid='';"
    "window.OM3Native={"
    "  bleOsConn:function(){return JSON.stringify(window.__stubBle);},"
    "  wifiState:function(){return JSON.stringify({wifi:!!window.__stubSsid,ssid:window.__stubSsid,timeout:false});},"
    "  blePermDetail:function(){return 'SDK=34；BLUETOOTH_SCAN=有；BLUETOOTH_CONNECT=有；蓝牙开关=开';}"
    "};</script>")

JS = r"""
var o = [], fails = [];
function ok(c, m){ o.push((c ? '  [OK ] ' : '  [FAIL] ') + m); if(!c) fails.push(m); }
function sec(t){ o.push(''); o.push('== ' + t + ' =='); }
function txt(id){ var e = document.getElementById(id); return e ? (e.textContent || '') : '<无此元素>'; }
function click(id){ var e = document.getElementById(id); if(e){ e.click(); return true; } return false; }
function curVisible(){
  var ps = ['A','B','C','D','E'];
  for(var i = 0; i < ps.length; i++){ var e = document.getElementById('pane' + ps[i]); if(e && !e.classList.contains('hide')) return ps[i]; }
  return '?';
}
function paneOfEl2(el){
  var d = 0;
  while(el && el !== document && d < 30){
    var id = String(el.id || '');
    if(/^pane[A-E]$/.test(id)) return id.slice(4);
    el = el.parentElement; d++;
  }
  return '';
}
function panelState(){
  var a = document.getElementById('toc'), b = document.getElementById('toc2');
  function vis(e){ if(!e) return false; return getComputedStyle(e).display !== 'none'; }
  return { toc: vis(a), toc2: vis(b), openN: (a && a.classList.contains('open') ? 1 : 0) + (b && b.classList.contains('open') ? 1 : 0) };
}
function flush(){
  var d = document.createElement('pre'); d.id = 'DBGOUT';
  d.textContent = o.join('\n') + '\n\n失败项 ' + fails.length + ' 个' + (fails.length ? '：\n  - ' + fails.join('\n  - ') : '');
  document.body.appendChild(d);
}
function step(fns, done){                 /* 顺序执行一串 function(next)，跑完调 done */
  var i = 0;
  (function go(){
    if(i >= fns.length){ if(done) done(); return; }
    var f = fns[i++];
    try{ f(go); }catch(e){ o.push('  步骤异常：' + (e && e.message ? e.message : e)); go(); }
  })();
}
function wait(ms, fn){ setTimeout(fn, ms); }

/* ============ ① 目录面板跟着页签 ============ */
function testToc(next){
  sec('① 目录面板跟着页签（用户：原版方案的搜索目录，点开发现是优化版的）');
  o.push('  #toc 存在=' + !!document.getElementById('toc') + '  #toc2 存在=' + !!document.getElementById('toc2'));
  var tbA = document.querySelector('#barABC button[data-p="A"]');
  var tbB = document.querySelector('#barABC button[data-p="B"]');
  var snapA = null, snapB = null, snapClose = null;
  step([
    function(go){
      if(tbA) tbA.click(); else click('tabBuiltin');
      wait(350, function(){
        o.push('  切到 A：__om3cur=' + window.__om3cur + ' 可见页签=' + curVisible());
        click('tocbtn');
        wait(250, function(){
          snapA = panelState();
          o.push('  A 点🔍 → ' + JSON.stringify(snapA));
          ok(snapA.toc === true && snapA.toc2 === false, '★A（原版方案）点🔍开的是 #toc（改前：不管在哪个页签都开 #toc2）');
          ok(snapA.openN === 1, '★同一时刻只有一份面板是开的（不会两块叠在一起）');
          click('tocbtn');
          wait(220, function(){
            snapClose = panelState();
            o.push('  再点一下（关）→ ' + JSON.stringify(snapClose));
            ok(!snapClose.toc && !snapClose.toc2 && snapClose.openN === 0, '★再点一下两份都收掉');
            go();
          });
        });
      });
    },
    function(go){
      if(tbB) tbB.click();
      wait(350, function(){
        o.push('  切到 B：__om3cur=' + window.__om3cur + ' 可见页签=' + curVisible());
        click('tocbtn');
        wait(250, function(){
          snapB = panelState();
          o.push('  B 点🔍 → ' + JSON.stringify(snapB));
          ok(snapB.toc2 === true && snapB.toc === false, '★B（优化版）点🔍开的是 #toc2');
          click('tocbtn');
          wait(200, function(){ go(); });
        });
      });
    },
    function(go){
      /* ② 跨页签跳转（jumpToPane）。
         实测：两份目录的锚点**各归各的页签** —— #toc 的 87 个全指向 paneA、#toc2 的 31 个全指向 paneB，
         所以"天然"的跨页签锚点其实不存在。这里人为造一个（把 #toc 里某个锚点临时改指向 paneA 的卡片），
         验兜底逻辑本身：在 B 页签点到指向 paneA 的锚点 → 应自动切到 A。
         （#toc2 那份在块02 没有监听：`nav2` 是解析期取的，当时 #toc2 还没进 DOM → 永久 null。
           实务上无碍，因为 #toc2 的锚点全在 paneB；已记进 SPEC 的"已知遗留"。） */
      var nav = document.getElementById('toc');
      var a = nav ? nav.querySelector('a[href^="#"]') : null;
      var target = document.querySelector('#paneA .card[id^="r-"]') || document.getElementById('calib');
      if(!a || !target){ o.push('  跳过②：找不到 #toc 里的锚点或 paneA 的可跳目标'); return go(); }
      var old = a.getAttribute('href');
      a.setAttribute('href', '#' + target.id);
      if(tbB) tbB.click();
      wait(300, function(){
        var before = curVisible();
        a.click();
        wait(450, function(){
          var after = curVisible();
          o.push('  人为跨页签锚点：#toc 里指向 #' + target.id + '（paneA）｜点前可见=' + before + ' 点后可见=' + after);
          ok(before === 'B' && after === 'A', '★点到别的页签的锚点 → 自动切过去（不然点了像没反应）');
          a.setAttribute('href', old);
          go();
        });
      });
    }
  ], next);
}

/* ============ ③ 场景卡小色轮 + 描述默认展开 ============ */
function testScene(next){
  sec('③ 场景对比：小色轮 + 描述默认展开');
  click('tabC');
  wait(700, function(){
    o.push('  可见页签=' + curVisible());
    var marks = document.querySelectorAll('.scwheel');
    var filled = document.querySelectorAll('.scwheel svg');
    o.push('  .scwheel 占位=' + marks.length + '  已填 svg=' + filled.length);
    ok(marks.length > 0, '场景卡上有小色轮占位（' + marks.length + ' 个）');
    ok(marks.length > 0 && filled.length === marks.length, '★每个占位都填上了色轮（' + filled.length + '/' + marks.length + '）');
    var checked = 0, bad = 0, miss = [];
    for(var i = 0; i < marks.length; i++){
      var sl = marks[i].closest ? marks[i].closest('.scslide') : null;
      var cid = sl ? String(sl.getAttribute('data-cid') || '') : '';
      var rec = null, A = window.__OM3RECIPES__ || [];
      for(var r = 0; r < A.length; r++) if(A[r].slug === cid || ('r-' + A[r].slug) === cid) rec = A[r];
      if(!rec){ if(miss.length < 3) miss.push(cid); continue; }
      checked++;
      if(String(marks[i].getAttribute('data-v')) !== rec.v.join(',')) bad++;
    }
    o.push('  数值抽查：' + (checked - bad) + '/' + checked + ' 与 __OM3RECIPES__ 的 v 完全一致' + (miss.length ? '（查不到 slug 的例：' + miss.join(',') + '）' : ''));
    ok(checked > 0 && bad === 0, '★小色轮画的是**这个配方自己的** 12 个色轴值');
    if(window.__om3fillWheels){ window.__om3fillWheels(); window.__om3fillWheels(); }
    ok(document.querySelectorAll('.scwheel svg').length === marks.length, '重复调 __om3fillWheels 不会重复灌（幂等）');
    var det = document.querySelectorAll('details.scfold');
    var openN = document.querySelectorAll('details.scfold[open]').length;
    o.push('  场景卡 fold 明细=' + det.length + ' 默认展开=' + openN);
    ok(det.length === 0 || openN === det.length, '★场景卡描述默认展开（' + openN + '/' + det.length + '，仍可手动收起）');
    testSlide(next);
  });
}

/* ============ ④ 一次滑动只换一屏 ============ */
function testSlide(next){
  sec('④ 场景对比「一次滑动只换一屏」');
  var pg = document.getElementById('scpager');
  if(!pg){ o.push('  找不到 #scpager'); return next(); }
  var s0 = pg.querySelector('.scslide');
  var st = s0 ? (s0.getBoundingClientRect().width + 12) : 0;
  var per = st > 0 ? Math.max(1, Math.round(pg.clientWidth / st)) : 0;
  o.push('  卡片步长=' + Math.round(st) + 'px 可视宽=' + pg.clientWidth + ' 一屏=' + per + ' 张 可滚动=' + Math.round(pg.scrollWidth - pg.clientWidth));
  if(st <= 0 || pg.scrollWidth <= pg.clientWidth + 4){ o.push('  跳过（内容不够长 / 步长为 0）'); return next(); }
  var calls = [], realScrollTo = pg.scrollTo ? pg.scrollTo.bind(pg) : null;
  pg.scrollTo = function(a, b){ calls.push((a && a.left !== undefined) ? Math.round(Number(a.left)) : Math.round(Number(b))); };
  function fire(px){ pg.scrollLeft = px; pg.dispatchEvent(new Event('scroll')); }
  function fmt(){ return calls.map(function(x){ return x + 'px(第' + Math.round(x / st) + '屏)'; }).join(' , ') || '（没被夹）'; }
  fire(st * (per * 5));                       /* ① 0 → 一下滑过 5 屏 */
  wait(400, function(){
    o.push('  ① 从 0 一下滑到第 ' + (per * 5) + ' 屏：夹取目标 = ' + fmt() + '（期望第 ' + per + ' 屏）');
    ok(calls.length === 0, '★第 41 轮起：**不再有 JS 夹取**（一下滑过 5 屏时 JS 不得动 scrollLeft；实测调用 ' + calls.length + ' 次）');
    calls = [];
    fire(st * per);                           /* ② 合法：回到第 per 屏，scLast 应更新 */
    wait(400, function(){
      calls = [];
      fire(st * (per * 4));                   /* ③ 再一下滑过 4 屏 → 应夹到 scLast(per) + per */
      wait(400, function(){
        o.push('  ② 第 ' + per + ' 屏 → 一下滑到第 ' + (per * 4) + ' 屏：夹取目标 = ' + fmt() + '（期望第 ' + (per * 2) + ' 屏）');
        ok(calls.length === 0, '★同上：JS 全程不干预（调用 ' + calls.length + ' 次）');
        calls = [];
        fire(st * (per * 3) > pg.scrollWidth - pg.clientWidth ? pg.scrollWidth - pg.clientWidth : st * (per * 3));   /* ④ 只跨一屏：不该动 */
        wait(400, function(){
          o.push('  ③ 只跨一屏的正常滚动：' + fmt());
          ok(getComputedStyle(document.querySelector('#scpager .scslide')).scrollSnapStop === 'always', '★"一次只停一张"现在由 CSS scroll-snap-stop:always 保证（不再用 JS）：' + getComputedStyle(document.querySelector('#scpager .scslide')).scrollSnapStop);
          if(realScrollTo) pg.scrollTo = realScrollTo;
          next();
        });
      });
    });
  });
}

/* ============ ⑤ 两条链路 ============ */
function testLinks(next){
  sec('⑤ 「两条链路」卡：蓝牙 / Wi-Fi / HTTP');
  var card = document.getElementById('camLinkCard');
  o.push('  #camLinkCard 存在=' + !!card + '  所属页签=pane' + (card ? paneOfEl2(card) : '-'));
  ok(!!card, '「连接相机」页上有「两条链路」卡');
  ok(!!card && paneOfEl2(card) === 'D', '卡在「连接相机」页签（paneD）里');
  if(!card) return next();
  var scenes = [
    ['蓝牙连着相机 + HTTP 不通', {conn:[{name:'OM-3 8F2A',address:'AA:BB'}],paired:[]}, '', ['相机蓝牙已连', '用蓝牙唤醒']],
    ['配对过但没连',             {conn:[],paired:[{name:'OM-3 8F2A',address:'AA:BB'}]}, '', ['配对过但没连']],
    ['蓝牙列表里没有相机',        {conn:[{name:'WH-1000XM5',address:'CC:DD'}],paired:[]}, '', ['没看到相机']],
    ['一个蓝牙都没连',            {conn:[],paired:[]}, '', ['没有已连接的蓝牙设备']],
    ['连着相机热点但 HTTP 不通',  {conn:[],paired:[]}, 'OM-3-8F2A', ['这是相机热点', '没切到「Wi-Fi 传输状态」']],
    ['连着普通路由器',            {conn:[],paired:[]}, 'MyHome-5G', ['不是相机热点']]
  ];
  step(scenes.map(function(s){
    return function(go){
      window.__stubBle = s[1]; window.__stubSsid = s[2];
      document.body.classList.remove('cam-on');
      try{ window.__om3camLink(); }catch(e){ o.push('  __om3camLink 抛错：' + e.message); }
      var t = txt('camLinkOut');
      var lack = s[3].filter(function(x){ return t.indexOf(x) < 0; });
      o.push('  [' + s[0] + '] ' + t.replace(/\s+/g, ' ').slice(0, 120) + '…');
      ok(lack.length === 0, '★「' + s[0] + '」文案正确' + (lack.length ? '（缺：' + lack.join('/') + '）' : ''));
      ok(t.indexOf('**') < 0, '「' + s[0] + '」没有漏出来的 markdown 星号');
      go();
    };
  }).concat([function(go){
    /* HTTP 通 */
    window.__stubBle = {conn:[{name:'OM-3 8F2A',address:'AA:BB'}],paired:[]};
    window.__stubSsid = 'OM-3-8F2A';
    document.body.classList.add('cam-on');
    try{ window.__om3camLink(); }catch(e){}
    var t = txt('camLinkOut');
    o.push('  [HTTP 通] ' + t.replace(/\s+/g, ' ').slice(0, 120) + '…');
    ok(t.indexOf('已连接，可以备份/写入') >= 0, '★HTTP 通时明确说"已连接，可以备份/写入"');
    document.body.classList.remove('cam-on');
    go();
  }, function(go){
    /* 老原生兼容：bleOsConn 返回数组（不是 {conn,paired}）不该崩 */
    var saved = window.OM3Native.bleOsConn;
    window.OM3Native.bleOsConn = function(){ return JSON.stringify([{name:'OM-3 X',address:'11:22'}]); };
    var crashed = '';
    try{ window.__om3camLink(); }catch(e){ crashed = e.message; }
    var t = txt('camLinkOut');
    window.OM3Native.bleOsConn = saved;
    o.push('  [老原生返回数组] 崩=' + (crashed || '否') + '  文案=' + t.replace(/\s+/g, ' ').slice(0, 70) + '…');
    ok(!crashed && t.indexOf('相机蓝牙已连') >= 0, '★老原生/无原生（bleOsConn 返回 {} 或 []）都兜住、不抛错');
    go();
  }, function(go){
    /* 唤醒按钮要真的转发到既有的蓝牙唤醒按钮（不复制实现） */
    var woke = false;
    var bw = document.getElementById('bleWake');
    if(!bw){ o.push('  找不到 #bleWake'); return go(); }
    var hook = function(e){ woke = true; try{ e.stopPropagation(); e.preventDefault(); }catch(x){} };
    bw.addEventListener('click', hook, true);
    var w = document.getElementById('camLinkWake');
    if(w) w.click();
    wait(200, function(){
      bw.removeEventListener('click', hook, true);
      ok(woke, '★卡上的「用蓝牙唤醒相机」= 走既有的蓝牙唤醒流程');
      go();
    });
  }]), next);
}

/* ============ ⑥ 底栏三级兜底 ============ */
function testBar(next){
  sec('⑥ 底栏：fixed → sticky → absolute 三级兜底 + 跟手');
  var tbA = document.querySelector('#barABC button[data-p="A"]');
  if(tbA) tbA.click();
  wait(400, function(){
    var bd = document.getElementById('barABC');
    if(!bd || getComputedStyle(bd).display === 'none'){ o.push('  #barABC 不可见，跳过'); return next(); }
    o.push('  正常时：__om3barMode=' + window.__om3barMode + ' position=' + getComputedStyle(bd).position + '（本地 Chrome 的 fixed 正常）');
    ok(window.__om3barMode === 'fixed', 'fixed 正常时就用 fixed（不走兜底）');
    /* 第 2 级：sticky 分支实际写的那几条样式，在这套 DOM 里能不能贴底 */
    bd.style.setProperty('position','sticky','important');
    bd.style.setProperty('left','auto','important');
    bd.style.setProperty('top','auto','important');
    bd.style.setProperty('bottom','0','important');
    var cs = getComputedStyle(bd), r = bd.getBoundingClientRect();
    var off = Math.round(window.innerHeight - r.bottom);
    o.push('  第2级 sticky：position=' + cs.position + ' 距底=' + off + 'px 宽=' + Math.round(r.width) + ' 视口=' + window.innerWidth);
    ok(cs.position === 'sticky', 'sticky 被接受（fixed 钉不住时改用 sticky）');
    ok(Math.abs(off) <= 6, '★sticky 在这套 DOM 里也能贴底（距底 ' + off + 'px）→ fixed 失效时它能顶上');
    if(window.__om3pinBars) window.__om3pinBars();
    wait(200, function(){
      o.push('  恢复：__om3pinBars() → position=' + getComputedStyle(bd).position + ' mode=' + window.__om3barMode);
      /* 第 3 级：absolute 兜底 */
      window.__om3barMode = 'absolute';
      bd.style.setProperty('position','static','important');
      bd.style.setProperty('top','160px','important');
      if(window.__om3barAbsPin) window.__om3barAbsPin(bd);
      var r1 = bd.getBoundingClientRect();
      o.push('  第3级 absolute 兜底：position=' + getComputedStyle(bd).position + ' 距底=' + Math.round(window.innerHeight - r1.bottom) + 'px 宽=' + Math.round(r1.width));
      ok(getComputedStyle(bd).position === 'absolute', 'fixed/sticky 都钉不住 → 绝对定位兜底');
      ok(Math.abs(window.innerHeight - r1.bottom) <= 4, '★兜底后贴在屏幕底');
      ok(r1.width <= window.innerWidth + 1, '★兜底后宽度不超屏');
      /* barFollow：absolute 模式下"跟手"；fixed/sticky 模式下不乱插手 */
      var h_doc = document.documentElement.scrollHeight;
      window.scrollTo(0, (window.pageYOffset || 0) + 400);
      wait(350, function(){
        o.push('    页面高=' + h_doc + ' 视口高=' + window.innerHeight + ' 下滚 400px 后 scrollY=' + Math.round(window.pageYOffset));
        bd.style.setProperty('position','static','important');
        bd.style.setProperty('top','160px','important');
        if(window.__om3barFollow) window.__om3barFollow();
        var r2 = bd.getBoundingClientRect();
        o.push('    __om3barFollow()（mode=absolute）：position=' + getComputedStyle(bd).position + ' 距底=' + Math.round(window.innerHeight - r2.bottom) + 'px');
        ok(getComputedStyle(bd).position === 'absolute' && Math.abs(window.innerHeight - r2.bottom) <= 4,
           '★absolute 模式下 __om3barFollow() 立刻把底栏拨回贴底（滚动时最多差一帧）');
        window.__om3barMode = 'fixed';
        bd.style.setProperty('position','static','important');
        if(window.__om3barFollow) window.__om3barFollow();
        o.push('    __om3barFollow()（mode=fixed）：position=' + getComputedStyle(bd).position + '（应保持 static，交给浏览器）');
        ok(getComputedStyle(bd).position === 'static', '★fixed 模式下 __om3barFollow() 不乱插手');
        if(window.__om3pinBars) window.__om3pinBars();
        next();
      });
    });
  });
}

/* ============ 收尾 ============ */
function finish(){
  sec('⑦ 汇总');
  var errs = window.__errs || [];
  o.push('  累计 JS 报错=' + errs.length + (errs.length ? '（' + errs.slice(0, 3).join(' | ') + '）' : ''));
  o.push('  __om3errs=' + (window.__om3errs || 0));
  ok(errs.length === 0, '整轮没有 JS 运行错误');
  flush();
}
setTimeout(function(){
  try{ testToc(function(){ testScene(function(){ testLinks(function(){ testBar(finish); }); }); }); }
  catch(e){ o.push('探针异常：' + (e && e.message ? e.message : e)); flush(); }
}, 2600);
"""

tail = '<script>' + JS + '</script>'
i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_r33.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\or33'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=90000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
if kk > 0:
    print(dom[kk:].split('>', 1)[1].split('</pre>')[0])
else:
    open(TMP + r'\r33_dump.html', 'w', encoding='utf-8', newline='').write(dom)
    print('无输出 DOM=%d  DBGOUT在全文? %s' % (len(dom), 'DBGOUT' in dom))
    print('dump → ' + TMP + r'\r33_dump.html')
