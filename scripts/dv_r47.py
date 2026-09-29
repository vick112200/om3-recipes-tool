# -*- coding: utf-8 -*-
"""第 47 轮验收：目录点项自动关 / 目录与页面同步 / 切页签滚动归零 / 整个档位存入我的配方
跑法：python scripts/dv_r47.py

为什么要这些断言（逐条对应用户那四句话）：
  ① 目录点击了不会自动关      → 运行时：点目录里一条，面板必须 display:none；且再点 🔍 还能开（状态没错位）
  ② 档位推荐的目录没同步新档位 → 目录里的档/槽 == 页面里的 .omode/.oslot（逐一对齐，含 C6–C10）
  ③ 切页签保留滚动位置        → 运行时：滚到 2600 再切页签，scrollTop 必须 0
  ④ 整个档位存入我的配方      → 走真实按钮 + 真实确认框；验名字继承、4 个槽、12 值/影调 6 项与页面逐项一致、
                               MONO 槽没进方案（且**写在确认框里**，不静默）、C6 只有 2 格、取消不建
另加一条独立交叉验：页面解析出来的 12 值 + 影调 6 项，必须等于 __OM3RECIPES__ 里那条配方（29 个槽位）。
"""
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
SRC = r'D:\workspace\om3-handbook'
TMP = r'C:\Users\82302\AppData\Local\Temp'
src = io.open(SRC + r'\app\base.html', encoding='utf-8').read()
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


# ================================================================ 静态
print('=== ① 静态：手写目录已撤、容器已在、写死的计数已清 ===')
nav = src[src.index('<nav id="toc2">'):src.index('<div class="emptytoc" id="noresult2">')]
A('五个档位' not in nav, '目录里手写的「五个档位」那一组已撤掉')
A(nav.count('href="#oC') == 0, '目录静态部分已无手写档位/槽位链接（%d 条）' % nav.count('href="#oC'))
A('id="toc2tiers"' in nav, '留了运行时生成用的容器 #toc2tiers')
A('<a class="lv2" href="#opick">' in nav, '总览组补上了第 45 轮那个 #opick（怎么挑 5 个）')
A('10 个候选档（挑 5 个）' in src, '目录里仍有「10 个候选档（挑 5 个）」这条（dv_r43 也断这条）')
for bad in ('只在档位推荐里搜（21 个槽位）', '档位推荐 21 个槽位里没找到匹配的。',
            '档位推荐只有 21 个槽位', "'<span class=\"scnoplan\">档位推荐 21 个槽位里没有这一卷</span>'"):
    A(bad not in src, '写死的旧计数已清：%s' % bad[:26])
A('window.__om3tocClose' in src and "closest('#toc, #toc2')" in src,
  '「点目录项 → 关面板」走的是唯一主控 __om3tocClose')
A("var r47sw = (window.__om3cur !== p);" in src and "behavior: 'instant'" in src,
  'switchPane 里有"页签真的变了才归零滚动"')
A("b.className = 'omtierbtn'" in src and 'injectTierBtns' in src, '「整个档位存入我的配方」按钮已注入')
A('window.__om3recFromOslot' in src, 'recFromOslot 已导出（给验收用）')
A("'<div class=\"lbnoplan\">这一卷没进档位推荐（档位推荐只有 ' + OM3SLOTN() + ' 个槽位）</div>'" in src and
  "'<span class=\"scnoplan\">档位推荐 ' + OM3SLOTN() + ' 个槽位里没有这一卷</span>'" in src,
  '图库弹层 / 场景索引里那两处槽位数也换成运行时数（OM3SLOTN）')
A('function OM3SLOTN()' in src and 'window.__om3slotN = OM3SLOTN;' in src and
  'window.__om3slotN ? window.__om3slotN()' in src,
  '槽位数只有一个定义（块03 定义 + 块08 复用），不再有第二处硬编码')

# ================================================================ 运行时
JS = r"""
setTimeout(function(){
  var o = [], F = 0;
  function ok(c, m){ o.push((c ? '[OK ] ' : '[FAIL] ') + m); if(!c) F++; }
  function info(m){ o.push('      ' + m); }
  /* CSS 里 html{scroll-behavior:smooth} —— 无头下量滚动必须先关掉它 */
  document.documentElement.style.scrollBehavior = 'auto';

  var tiers = [].slice.call(document.querySelectorAll('.omode')).map(function(m){ return m.id; })
                .filter(function(x){ return /^oC\d+$/.test(x); });
  var slots = [].slice.call(document.querySelectorAll('.oslot[id^="oC"]')).map(function(x){ return x.id; });
  var t2 = document.getElementById('toc2');
  var links = [].slice.call(t2.querySelectorAll('a')).map(function(a){ return (a.getAttribute('href') || '').replace(/^#/, ''); });
  var tl = links.filter(function(h){ return /^oC\d+$/.test(h); });
  var sl = links.filter(function(h){ return /^oC\d+-/.test(h); });

  /* ---------- ② 目录 == 页面 ---------- */
  info('页面 ' + tiers.length + ' 档 / ' + slots.length + ' 槽；目录 ' + tl.length + ' 档 / ' + sl.length + ' 槽');
  ok(tl.join(',') === tiers.join(','), '目录里的候选档 == 页面 .omode（' + tl.length + ' 个：' + tl.join(' ') + '）');
  ok(sl.join(',') === slots.join(','), '目录里的槽位 == 页面 .oslot（' + sl.length + ' 个）');
  ok(tl.indexOf('oC6') >= 0 && tl.indexOf('oC10') >= 0, '第 44 轮补的 C6–C10 已在目录里（用户②）');
  var dead = links.filter(function(h){ return h && !document.getElementById(h); });
  ok(!dead.length, '目录里没有死锚点（' + dead.length + ' 个：' + dead.slice(0, 3).join(',') + '）');
  var q2 = document.getElementById('toc2q');
  ok(!!q2 && q2.getAttribute('placeholder').indexOf(String(slots.length) + ' 个槽位') >= 0,
     '搜索框写的是真实槽位数（' + slots.length + '）');
  var nr = document.getElementById('noresult2');
  ok(!!nr && nr.textContent.indexOf(String(slots.length) + ' 个槽位') >= 0, '空结果文案也是真实槽位数');
  /* 目录里每一条都能指到真实元素（点得到） */
  var badJump = [];
  tl.concat(sl).forEach(function(h){ var e = document.getElementById(h); if(!e) badJump.push(h); });
  ok(!badJump.length, '目录里每条都指得到真实元素（' + badJump.length + ' 条指不到）');

  function disp(id){ var e = document.getElementById(id); return e ? getComputedStyle(e).display : '(无)'; }
  var tabA = document.querySelector('.tabs button[data-p="A"]');
  var tabB = document.querySelector('.tabs button[data-p="B"]');
  var tabc = document.getElementById('tocbtn');

  /* ---------- ① 点目录项 → 自动关 ---------- */
  tabB.click();
  setTimeout(function(){
    tabc.click();
    setTimeout(function(){
      ok(disp('toc2') === 'block', 'B 页签点 🔍 → #toc2 打开');
      var a1 = t2.querySelector('a[href="#oC1"]');
      if(a1) a1.click();
      setTimeout(function(){
        ok(disp('toc2') === 'none', '点目录里一条 → 面板自动关（class=“' + t2.className + '” display=' + disp('toc2') + '）');
        tabc.click();
        setTimeout(function(){
          ok(disp('toc2') === 'block', '再点一次 🔍 → 还能正常打开（开关状态没错位）');
          tabc.click();
          setTimeout(function(){
            ok(disp('toc2') === 'none', '✕ 那条路也仍然好使（再点一次就关）');
            scrollTests();
          }, 260);
        }, 320);
      }, 320);
    }, 400);
  }, 300);

  var tabAEl = document.querySelector('.tabs button[data-p="A"]');
  var tabBEl = document.querySelector('.tabs button[data-p="B"]');

  /* ---------- ③ 切页签滚动归零 ---------- */
  function scrollTests(){
    tabBEl.click();
    setTimeout(function(){
      document.documentElement.scrollTop = 2600;
      var pre = document.documentElement.scrollTop;
      info('档位推荐滚到 ' + pre + '（文档高 ' + document.documentElement.scrollHeight + '）');
      tabAEl.click();
      setTimeout(function(){
        var after = document.documentElement.scrollTop;
        ok(pre > 1000 && after === 0, '档位推荐(滚到 ' + pre + ') → 切配方合集：scrollTop = ' + after);
        document.documentElement.scrollTop = 300;
        var pre2 = document.documentElement.scrollTop;
        tabBEl.click();
        setTimeout(function(){
          var after2 = document.documentElement.scrollTop;
          ok(after2 === 0, '配方合集(滚到 ' + pre2 + ') → 切回档位推荐：scrollTop = ' + after2);
          /* 点"当前页签"不该把滚动位置拉走（只在页签真的变了时才归零） */
          document.documentElement.scrollTop = 1200;
          var pre3 = document.documentElement.scrollTop;
          tabBEl.click();
          setTimeout(function(){
            var after3 = document.documentElement.scrollTop;
            ok(pre3 > 500 && after3 === pre3, '点"当前页签"不动滚动位置（' + pre3 + ' → ' + after3 + '）');
            jumpTest();
          }, 380);
        }, 420);
      }, 420);
    }, 420);
  }

  /* ---------- ③-b 归零不能把"点目录跳过去"吃掉 ---------- */
  function jumpTest(){
    tabAEl.click();
    setTimeout(function(){
      document.documentElement.scrollTop = 0;
      document.getElementById('tocbtn').click();
      setTimeout(function(){
        var toc = document.getElementById('toc');
        var as = [].slice.call(toc.querySelectorAll('a[href^="#r-"]'));
        ok(disp('toc') === 'block' && as.length > 0, 'A 页签点 🔍 → #toc 打开（' + as.length + ' 条卡链接）');
        var a = as[as.length - 1];
        var want = 0;
        if(a){ var tgt = document.getElementById(String(a.getAttribute('href')).replace(/^#/, '')); if(tgt) want = tgt.getBoundingClientRect().top + window.pageYOffset; }
        if(a) a.click();
        setTimeout(function(){
          var st = document.documentElement.scrollTop;
          ok(disp('toc') === 'none' && st > 20,
             '点目录里那条卡链接：面板关了、页面也真的滚过去了（目标在 ' + Math.round(want) + '，scrollTop=' + Math.round(st) + '）');
          parseCrossCheck();
        }, 600);
      }, 420);
    }, 420);
  }

  /* ---------- ④-a 页面解析值 == 库里那条配方（独立数据源交叉验） ---------- */
  function parseCrossCheck(){
    var REC = window.__OM3RECIPES__ || [];
    function norm(s){ return String(s || '').replace(/[\s·・\-_/（）()]/g, '').toLowerCase(); }
    function cands(t){
      var out = [], i, n = norm(t);
      for(i = 0; i < REC.length; i++) if(norm(REC[i].n) === n) out.push(REC[i]);
      return out;
    }
    var cmp = 0, diffs = [], noLib = [];
    [].slice.call(document.querySelectorAll('.oslot[id^="oC"]')).forEach(function(el){
      if(/-m\d+$/.test(el.id)) return;                       /* MONO 槽不走色轮 */
      var sn = el.querySelector('.osname');
      var nm = sn ? String(sn.textContent).replace(/^\s+|\s+$/g, '') : '';
      var cs = cands(nm);
      if(!cs.length){ noLib.push(el.id); return; }
      var got = window.__om3recFromOslot(el);
      if(!got){ diffs.push(el.id + ':解析返回 null'); return; }
      cmp++;
      var hit = cs.some(function(r){
        if(JSON.stringify(got.v) !== JSON.stringify(r.v)) return false;
        return ['hi', 'mid', 'sh', 'eff', 'shp', 'con'].every(function(k){
          return Number(got[k]) === Number(r[k] || 0);
        });
      });
      if(!hit) diffs.push(el.id);
    });
    info('能和库里对上名的槽位 ' + cmp + ' 个；库里没有的：' + (noLib.join(',') || '无'));
    ok(cmp >= 28, '交叉验覆盖了 ' + cmp + ' 个槽位（期望 ≥28）');
    ok(!diffs.length, '页面解析出的 12 值 + 影调 6 项 == 库里那条配方（不一致 ' + diffs.length + '：' + diffs.slice(0, 3).join(',') + '）');
    ok(noLib.sort().join(',') === 'oC1-3,oC1-4', '库里没有的正是两个「白里透红」自配槽（' + noLib.join(',') + '）');
    /* 边界：解析函数对"没有色轮数据"的输入要**返回 null、不抛错**（调用方才能跳过并写日志） */
    ok(window.__om3recFromOslot(null) === null && window.__om3recFromOslot(document.createElement('div')) === null,
       'recFromOslot 遇到没有 12 格色轴值的元素 → 返回 null（不抛错）');
    ok(window.__om3recFromOslot(document.getElementById('oC1-m1')) === null,
       'MONO 槽（oC1-m1）本来就没有 12 格色轴值 → 同样返回 null（它不该进方案）');
    copyC1();
  }

  /* ---------- ④-b 整个档位存入我的配方：C1 ---------- */
  function setsRaw(){ try{ return JSON.parse(localStorage.getItem('om3sets') || '[]'); }catch(e){ return []; } }
  function clickTier(mid, cb){
    var m = document.getElementById(mid);
    var b = m ? m.querySelector('.omtierbtn') : null;
    if(!b){ ok(false, mid + ' 上有「整个档位存入我的配方」按钮'); cb(); return; }
    try{ window.__showMode(mid); }catch(e){}
    b.click();
    setTimeout(cb, 320);
  }
  function copyC1(){
    var n0 = setsRaw().length;
    clickTier('oC1', function(){
      var mask = document.getElementById('omask');
      var open1 = !!mask && mask.style.display === 'flex';
      ok(open1, '点「整个档位存入我的配方」→ 弹确认框（先问后建，用户④-a）');
      var f0 = document.getElementById('of0'), f1 = document.getElementById('of1');
      ok(!!f0 && f0.value === 'C1 人像档', '方案名预填「C1 人像档」（实测「' + (f0 && f0.value) + '」）');
      ok(!!f1 && f1.value === 'myset1', '写回档位预选 C1 / myset1（实测 ' + (f1 && f1.value) + '）');
      var body = (document.getElementById('obody') || {}).textContent || '';
      ok(body.indexOf('MONO 槽') >= 0 && body.indexOf('Ilford HP5') >= 0,
         '确认框里明说 MONO 槽（Ilford HP5）不进方案（不静默丢）');
      if(!f1){ o.push('（没有 #of1，跳过后续）'); return flush1(); }
      document.getElementById('ook').click();
      setTimeout(function(){
        var arr = setsRaw();
        ok(arr.length === n0 + 1, '确认后新建 1 套方案（' + n0 + ' → ' + arr.length + '）');
        var s = arr[arr.length - 1] || {};
        ok(s.name === 'C1 人像档', '方案名 = 继承的「C1 人像档」（实测「' + s.name + '」）');
        ok(s.from === 'myset1', '写回档位 = myset1（实测 ' + s.from + '）');
        ok(!!s.slots && [1,2,3,4].every(function(n){ return !!s.slots[n]; }), 'C1 的 4 个槽都填进去了');
        var bad = [], names = [];
        [1,2,3,4].forEach(function(n){
          var el = document.getElementById('oC1-' + n), one = s.slots && s.slots[n];
          if(!one) return;
          names.push(one.name);
          var bs = el.querySelectorAll('.osvals .ovc b'), exp = [];
          for(var i = 0; i < 12; i++) exp.push(Number(String(bs[i].textContent).replace(/[−–—]/g, '-')) || 0);
          if(JSON.stringify(one.vivid) !== JSON.stringify(exp)) bad.push('槽' + n + '.vivid ' + one.vivid + '≠' + exp);
          var prm = String((el.querySelector('.osline.prm') || {}).textContent || '').replace(/[−–—]/g, '-');
          function g(re){ var m = re.exec(prm); return m ? (Number(m[1]) || 0) : 0; }
          [['hi', /Hi\s*([+-]?\d+)/], ['mid', /Mid\s*([+-]?\d+)/], ['lo', /Sh\s*([+-]?\d+)/],
           ['eff', /(?:阴影补偿|阴影效果)\s*([+-]?\d+)/], ['shp', /锐度\s*([+-]?\d+)/],
           ['con', /对比\s*([+-]?\d+)/]].forEach(function(pair){
            if(Number(one[pair[0]]) !== g(pair[1])) bad.push('槽' + n + '.' + pair[0] + '=' + one[pair[0]] + '≠' + g(pair[1]));
          });
          if(!one.raw || Object.keys(one.raw).length !== 18) bad.push('槽' + n + '.raw 键数=' + (one.raw ? Object.keys(one.raw).length : '无'));
          if(!one.feel) bad.push('槽' + n + ' 没带过描述（richFromCard 没生效）');
        });
        ok(!bad.length, '四格的 12 色轴值 / 影调 6 项 / 写相机的 18 个键 / 描述 与页面逐项一致（不一致 ' + bad.length + '：' + bad.slice(0, 2).join(' | ') + '）');
        ok(names.indexOf('Ilford HP5') < 0, 'MONO 槽没进方案（4 个槽名：' + names.join(' / ') + '）');
        var one1 = s.slots && s.slots[1];
        ok(!!one1 && !!one1.raw['MODE_COLOR_CREATOR_2_VIVID_SET1_1'] && one1.raw['MODE_COLOR_CREATOR_2_TONE_CONTROL_HIGH_SET1'] !== undefined,
           '槽里的键名是 SET1_*（以后「整个档位写入相机」能直接吃）');
        var lg = (document.getElementById('camOut3') || {}).textContent || '';
        ok(lg.indexOf('C1 人像档') >= 0 && lg.indexOf('已把「Fuji Astia」放进方案') >= 0,
           '日志里有建方案 + 逐槽那几条');
        copyC6();
      }, 500);
    });
  }

  /* ---------- ④-c C6 只有 2 格 + 取消不建 ---------- */
  function copyC6(){
    var n0 = setsRaw().length;
    clickTier('oC6', function(){
      var body = (document.getElementById('obody') || {}).textContent || '';
      var f0 = document.getElementById('of0'), f1 = document.getElementById('of1');
      ok(f0 && f0.value === 'C6 暖调玫瑰（人像）', 'C6 名字预填「C6 暖调玫瑰（人像）」（实测「' + (f0 && f0.value) + '」）');
      ok(f1 && f1.value === 'current', 'C6 相机上没有对应档 → 预选「当前状态」（实测 ' + (f1 && f1.value) + '）');
      ok(body.indexOf('2 个槽') >= 0 && body.indexOf('剩下的槽留空') >= 0, 'C6 的确认框如实说明只有 2 格、剩下留空');
      document.getElementById('ook').click();
      setTimeout(function(){
        var arr = setsRaw(), s = arr[arr.length - 1] || {};
        var filled = 0; [1,2,3,4].forEach(function(n){ if(s.slots && s.slots[n]) filled++; });
        ok(arr.length === n0 + 1 && s.name === 'C6 暖调玫瑰（人像）' && filled === 2,
           'C6 存进去：名字继承 + 只填 2 格（实测 ' + filled + ' 格）');
        cancelTest(arr.length);
      }, 500);
    });
  }
  function cancelTest(before){
    clickTier('oC2', function(){
      var f0 = document.getElementById('of0');
      if(f0) f0.value = '不该被建的名字';
      document.getElementById('ocancel').click();
      setTimeout(function(){
        var a2 = setsRaw();
        ok(a2.length === before, '点「取消」→ 一套都不建（' + before + ' → ' + a2.length + '）');
        ok(!a2.some(function(x){ return x && x.name === '不该被建的名字'; }), '取消后没有留下半成品方案');
        ok((document.getElementById('omask') || {}).style.display === 'none', '取消后确认框已收掉');
        /* 已经有同名方案时：明说"会再建一套、不覆盖"，而不是默默建 / 默默覆盖 */
        var n3 = a2.length;
        clickTier('oC1', function(){
          var body = (document.getElementById('obody') || {}).textContent || '';
          ok(body.indexOf('已经有一套叫「C1 人像档」的方案了') >= 0 && body.indexOf('不覆盖') >= 0,
             '已有同名方案时，确认框里明说"再建一套、不覆盖它"');
          document.getElementById('ocancel').click();
          setTimeout(function(){
            ok(setsRaw().length === n3, '同名那种情况点取消 → 也不建（' + n3 + ' → ' + setsRaw().length + '）');
            var c1 = setsRaw().filter(function(x){ return x && x.name === 'C1 人像档'; })[0] || {};
            ok(!c1.mount || String(c1.mount) === '', '新建的方案是「未挂载」（没写进相机就是没挂）');
            ok(c1.from === 'myset1' && !!c1.id && ('camera' in c1) && !!c1.slots,
               '方案字段与「＋新建方案」建出来的一致：id / from / camera / slots 都在（没连相机时 camera 是空串）');
            ok(window.__errs.length === 0, '全程 0 JS 报错（' + window.__errs.length + '）');
            ok(window.__rejs.length === 0, '全程 0 未处理拒绝（' + window.__rejs.length + '）');
            ok((window.__om3errs || 0) === 0, 'om3errs = ' + (window.__om3errs || 0));
            flush();
          }, 320);
        });
      }, 320);
    });
  }
  function flush1(){ flush(); }
  function flush(){
    o.push('');
    o.push('哨兵失败数=' + F);
    var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
    document.body.appendChild(d);
  }
}, 3200);
"""

k = src.find('<body')
j = src.find('>', k) + 1
head = ("<script>window.__OM3_APP__=1;window.__errs=[];window.__rejs=[];"
        "window.addEventListener('error',function(e){window.__errs.push('ERR '+(e.message||'')+' @'+(e.lineno||0));});"
        "window.addEventListener('unhandledrejection',function(e){window.__rejs.push('REJ '+String(e.reason));});</script>")
out = src[:j] + head + src[j:].replace('</body>', '<script>' + JS + '</script></body>', 1)
p = TMP + r'\dv_r47.html'
io.open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\omr47'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--hide-scrollbars', '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=60000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=400)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
if kk < 0:
    print('  [FAIL] 探针没拿到输出（DOM %d 字符）' % len(dom))
    F += 1
else:
    body = dom[kk:].split('>', 1)[1].split('</pre>')[0]
    print(body)
    K += body.count('[')
    F += body.count('[FAIL]')
print()
print('===== 结论：%s（%d 项，失败 %d）=====' % ('全部通过 ✅' if F == 0 else '有 %d 项失败 ❌' % F, K, F))
sys.exit(1 if F else 0)
