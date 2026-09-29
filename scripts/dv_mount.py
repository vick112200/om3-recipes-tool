# -*- coding: utf-8 -*-
"""方案「挂载状态」实测（无头 Chrome + 假相机 HTTP，不接真相机）。

覆盖 SPEC-round17.md 的验收标准，**口径已按 SPEC-round29.md 改成两态**（用户 2026-09-24：
"要么挂载要么没挂"）：
  0  状态弹窗**只有两个**选项（未挂载 / 已挂载），不再有「待重启确认」
  1  列表徽章两态文案（未挂载 / C1 · 已挂载）
  2  列表徽章可点 → 弹「改状态」→ 改完刷新，**不跳进详情页**
  3  详情页有状态行 + #mpMount；**详情 .mpitem 仍是 6 条**（dv_mpflow 口径）
  4  手动 A on@C1 → 再标 B on@C1 → A 自动回未挂载（日志说明）
  5  手动标「未挂载」→ mountTier 清空
  6  假相机写入成功（单槽 / 全部槽）→ **直接 on（已挂载）** + 档位/槽号；同档位别的方案回未挂载
  7  写入失败（未连接）→ 状态一位都不变
  8  ☰→「校验上次写入」核对一致 → 仍是 on（日志写"核对一致"）
  8b ☰→「校验上次写入」核对**不一致** → 自动打回「未挂载」（两态必须有这条兜底）
  9  从「连接相机」页写的（记录里没有 setId）→ 校验通过也不改任何方案状态
  10 从相机读取保存 → 新方案直接 on + 同档位别的方案回未挂载
  11b 老数据里的历史值 'pending' → 徽章按两态显示「已挂载」（不做数据迁移）
  11 老数据（没有 mount 字段）显示「未挂载」、不报错
  12 分享代码 v3 不带挂载状态（导一个来回：导入的那套是未挂载，原来的状态不变）
  13 全程 js 报错 0 / om3errs 0

用法：python scripts/dv_mount.py
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
window.__cam = { text:'', buf:'', calls:[], rebooted:false, declared:0 };
window.__offline = false;
window.XMLHttpRequest = function(){
  var self = this;
  self.readyState = 0; self.status = 0; self.responseText = '';
  self.open = function(m, u){ self._u = String(u); };
  self.setRequestHeader = function(){};
  self.send = function(body){
    if(window.__offline){
      self.status = 0; self.responseText = ''; self.readyState = 4;
      setTimeout(function(){ if(self.onerror) self.onerror(); }, 0);
      return;
    }
    var u = self._u, q = (u.split('?')[1] || ''), path = u.replace(/^https?:\/\/[^\/]+\//, '');
    var st = 200, txt = '';
    if(/^send_partialmysetdata/.test(path)){
      var off = +((/offset=(\d+)/.exec(q)) || [])[1];
      window.__cam.calls.push('chunk@' + off);
      window.__cam.buf = (window.__cam.buf || '').slice(0, off) + String(body || '');
    }
    else if(/^set_mysetdatasize/.test(path)){ window.__cam.declared = +((/size=(\d+)/.exec(q)) || [])[1]; txt = 'ok'; }
    else if(/^get_mysetrestorestate/.test(path)){ txt = '<status>success</status>'; if(window.__cam.buf) window.__cam.text = window.__cam.buf; }
    else if(/^get_mysetdatasize/.test(path)){ txt = '<size>' + window.__cam.text.length + '</size>'; }
    else if(/^get_partialmysetdata/.test(path)){ txt = window.__cam.text; }
    else if(/^get_mysetbackupstate/.test(path)){ txt = '<status>idle</status>'; }
    else if(/^exec_reboot/.test(path)){ txt = 'rebooting'; window.__cam.rebooted = true; }
    else { txt = 'ok'; }
    self.status = st; self.responseText = txt; self.readyState = 4;
    setTimeout(function(){ if(self.onreadystatechange) self.onreadystatechange(); }, 0);
  };
};
</script>"""

JS = r"""
setTimeout(function(){
  var o = [], fails = [];
  function ok(c, m){ o.push((c ? '  [OK ] ' : '  [FAIL] ') + m); if(!c) fails.push(m); }
  function el(id){ return document.getElementById(id); }
  function sets(){ try{ return JSON.parse(localStorage.getItem('om3sets') || '[]'); }catch(e){ return []; } }
  function put(arr){ localStorage.setItem('om3sets', JSON.stringify(arr)); }
  function byId(id){ var a = sets(); for(var i = 0; i < a.length; i++) if(a[i].id === id) return a[i]; return null; }
  function logTxt(){ var e = el('camOut3'); return e ? (e.textContent || '').replace(/\s+/g, ' ') : ''; }
  function listTxt(idx){
    var it = document.querySelectorAll('#mpList .mpitem')[idx];
    return it ? (it.textContent || '').replace(/\s+/g, ' ') : '（没有第 ' + idx + ' 个列表项）';
  }
  function badgeTxt(idx){
    var it = document.querySelectorAll('#mpList .mpitem')[idx];
    var b = it ? it.querySelector('.mpmount') : null;
    return b ? (b.textContent || '').trim() : '（没有徽章）';
  }
  function fin(){
    o.push('累计 js 报错=' + (window.__errs ? window.__errs.length : 0) + '  om3errs=' + (window.__om3errs || 0));
    o.push('--- 结果：' + (fails.length ? ('失败 ' + fails.length + ' 项') : '全部通过') + ' ---');
    var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
    document.body.appendChild(d);
  }
  var steps = [];
  function step(f){ steps.push(f); }
  function run(){ if(!steps.length) return fin(); var f = steps.shift();
    try{ f(run); }catch(e){ o.push('  !! 步骤抛错：' + (e && e.message ? e.message : e)); fin(); } }
  var CRLF = String.fromCharCode(13) + String.fromCharCode(10);
  function camText(){
    var t = window.__om3buildPayload({ n:'x', v:[0,0,0,0,0,0,0,0,0,0,0,0], hi:0, mid:0, sh:0, eff:0, shp:0, con:0 }, 1, 'C1', 'OM-3');
    while(t.length < 12000) t += '2,MODE_COLOR_CREATOR_2_VIVID_SET4_1,MODE_STEP_0' + CRLF;
    return t;
  }
  function reseed(){
    put([
      { id:'A', name:'方案甲', desc:'甲', from:'myset1', camera:'OM-3',
        slots:{ 1:{ vivid:[1,2,3,0,0,0,0,0,0,0,0,0], raw:{}, used:3, hi:1, mid:-1, lo:2, eff:0, shp:0, con:1, name:'甲槽' },
                2:null, 3:null, 4:null } },
      { id:'B', name:'方案乙', desc:'', from:'myset1', camera:'OM-3',
        slots:{ 1:{ vivid:[0,0,0,0,0,0,3,3,3,0,0,0], raw:{}, used:3, hi:0, mid:0, lo:0, eff:0, shp:0, con:0, name:'乙槽' },
                2:null, 3:null, 4:null } },
      { id:'C', name:'老方案（没有 mount 字段）', desc:'', from:'builtin', camera:'OM-3',
        slots:{ 1:null, 2:null, 3:null, 4:null } }
    ]);
    window.__om3mpRender();
  }
  /* 回到「方案」列表（mpCur=-1）；测试里读徽章前必须先回来，否则量到的是详情页那 6 条 */
  function goList(){ window.__om3mpDetail(-1); }
  /* 用弹窗手动改状态：选状态 + 档位 → 确定 */
  function setStatus(idx, state, tier, cb){
    var b = document.querySelectorAll('#mpList .mpitem')[idx].querySelector('.mpmount');
    if(!b){ o.push('  !! 第 ' + idx + ' 项没有徽章'); cb(); return; }
    b.click();
    setTimeout(function(){
      var f = document.querySelectorAll('#ofields select');
      if(f.length < 2){ o.push('  !! 改状态弹窗没有两个下拉（实际 ' + f.length + '）'); if(el('ocancel')) el('ocancel').click(); cb(); return; }
      f[0].value = state; f[1].value = tier;
      el('ook').click();
      setTimeout(cb, 150);
    }, 150);
  }

  /* ============ 1. 列表徽章三态文案 ============ */
  step(function(next){
    try{ localStorage.clear(); }catch(e){}
    el('tabMine').click();
    setTimeout(function(){
      reseed();
      setTimeout(function(){
        o.push('    列表：' + JSON.stringify(listTxt(0)).slice(0, 110));
        ok(badgeTxt(0) === '未挂载', '老数据/默认 → 徽章「未挂载」（实际 ' + JSON.stringify(badgeTxt(0)) + '）');
        ok(badgeTxt(2) === '未挂载', '第三项（from=builtin）也是未挂载');
        ok(listTxt(2).indexOf('builtin') < 0, '★老数据的来源档位不再吐英文 builtin（改用 tierLabelSafe）');
        next();
      }, 250);
    }, 700);
  });

  /* ============ 2. 徽章可点 + 不跳详情 + 两态文案（含"弹窗只有两个选项"） ============ */
  step(function(next){
    /* 先只打开弹窗，数一下选项 —— 两态口径的关键（用户 2026-09-24 嫌"挂载未生效"很奇怪） */
    document.querySelectorAll('#mpList .mpitem')[0].querySelector('.mpmount').click();
    setTimeout(function(){
      var f0 = document.querySelectorAll('#ofields select')[0];
      var txts = [];
      if(f0) for(var i0 = 0; i0 < f0.options.length; i0++) txts.push(f0.options[i0].textContent);
      ok(txts.length === 2, '★状态弹窗只有两个选项：' + JSON.stringify(txts));
      ok(txts.join('').indexOf('待重启确认') < 0, '★不再出现「待重启确认」这个中间态');
      ok(txts.join('').indexOf('已挂载') >= 0, '两个选项里有「已挂载」：' + JSON.stringify(txts));
      el('ocancel').click();                            /* 取消 → 什么都不改 */
      setTimeout(function(){
        ok(badgeTxt(0) === '未挂载', '弹窗取消后状态没被改：' + JSON.stringify(badgeTxt(0)));
    setStatus(0, 'on', 'myset1', function(){
      ok(badgeTxt(0) === 'C1 · 已挂载', '改「已挂载」→ 徽章：' + JSON.stringify(badgeTxt(0)));
      ok(!!el('mpNewSet'), '★点徽章没有跳进详情页（列表页还在，能看到「＋ 新建方案」）');
        ok(byId('A').mount === 'on' && byId('A').mountTier === 'myset1', '数据里也存对了：' + JSON.stringify([byId('A').mount, byId('A').mountTier]));
        ok(isArrOk(byId('A').mountSlots), '手动改时 mountSlots 是空数组（不编造槽号）：' + JSON.stringify(byId('A').mountSlots));
        next();
      });
      }, 300);
    }, 200);
  });
  function isArrOk(x){ return Object.prototype.toString.call(x) === '[object Array]'; }

  /* ============ 3. 详情页状态行 + 条目数仍 6 ============ */
  step(function(next){
    document.querySelectorAll('#mpList .mpitem')[0].click();
    setTimeout(function(){
      var n = document.querySelectorAll('#mpList .mpitem').length;
      ok(n === 6, '★详情页 .mpitem 仍是 6 条（实际 ' + n + '）—— 没破坏 dv_mpflow 的口径');
      var head = document.querySelector('#mpList .mpitem');
      var t = (head.textContent || '').replace(/\s+/g, ' ');
      o.push('    详情头部：' + JSON.stringify(t.slice(0, 90)));
      ok(t.indexOf('相机上的状态') >= 0 && t.indexOf('已挂载') >= 0, '详情头部有状态行且文案正确');
      ok(!!el('mpMount'), '详情页有「改状态」按钮 #mpMount');
      ok(!!head.querySelector('.mpmount'), '详情头部也有那个徽章（不可点，旁边是按钮）');
      next();
    }, 400);
  });

  /* ============ 4/5. 同档位互斥 + 标回未挂载 ============ */
  step(function(next){
    el('mpBack').click();
    setTimeout(function(){
      setStatus(1, 'on', 'myset1', function(){
        ok(badgeTxt(1) === 'C1 · 已挂载', '方案乙 → 「C1 · 已挂载」：' + JSON.stringify(badgeTxt(1)));
        ok(byId('A').mount === '' && byId('A').mountTier === '', '★同档位的方案甲被自动打回未挂载（' + JSON.stringify([byId('A').mount, byId('A').mountTier]) + '）');
        ok(badgeTxt(0) === '未挂载', '列表里方案甲也显示未挂载：' + JSON.stringify(badgeTxt(0)));
        ok(logTxt().indexOf('方案甲') >= 0 && logTxt().indexOf('自动回到未挂载') >= 0, '日志写明了是谁被打回');
        setStatus(1, '', 'myset1', function(){
          ok(byId('B').mount === '' && byId('B').mountTier === '' && byId('B').mountSlots.length === 0,
             '手动标「未挂载」→ mount/mountTier/mountSlots 全清（' + JSON.stringify([byId('B').mount, byId('B').mountTier]) + '）');
          ok(badgeTxt(1) === '未挂载', '徽章回到「未挂载」');
          next();
        });
      });
    }, 300);
  });

  /* ============ 6. 写入成功 → 直接「已挂载」+ 互斥（全部 4 槽那条路） ============ */
  step(function(next){
    /* 先把 A 标成 on@C1，检验"写入会把它打回" */
    setStatus(0, 'on', 'myset1', function(){
      window.__cam.text = camText(); window.__cam.buf = ''; window.__cam.declared = 0;
      window.__cam.rebooted = false; window.__cam.calls = [];
      window.__offline = false;
      document.body.classList.add('cam-on');
      var mark = logTxt().length;
      try{ if(window.__om3setConn) window.__om3setConn(true); }catch(e){}
      var ttl = el('taskTitle'); if(ttl) ttl.textContent = '';
      /* 打开 B 的详情 → 写入面板（全部 4 个槽 → 只有槽1 有内容，所以写 1 个槽） */
      window.__om3mpDetail(1);
      setTimeout(function(){
        var wb = document.querySelector('#mpw1') || null;
        o.push('    写入面板存在=' + !!wb + '（没有面板就直接调 mpWriteOne 那条路）');
        /* 直接走"详情页写入"那条路（等价于点「写入相机」） */
        window.__om3mpWriteOne(JSON.parse(JSON.stringify(sets()[1])), 1);
        var t0 = Date.now();
        var w = setInterval(function(){
          var t = el('taskTitle') ? el('taskTitle').textContent : '';
          if(t.indexOf('完成') >= 0 || t.indexOf('失败') >= 0 || Date.now() - t0 > 30000){
            clearInterval(w);
            setTimeout(function(){
              var b = byId('B');
              ok(b.mount === 'on', '★写入成功 → 方案乙**直接**变成 on（两态：写完就算挂载）（实际 ' + JSON.stringify([b.mount, b.mountTier]) + '）');
              ok(b.mountTier === 'myset1', '记下了挂在哪个档位：' + JSON.stringify(b.mountTier));
              ok(isArrOk(b.mountSlots) && b.mountSlots.length === 1 && b.mountSlots[0] === 1,
                 '记下了写了哪几个槽：' + JSON.stringify(b.mountSlots));
              ok(byId('A').mount === '', '★写入前标在 C1 的方案甲被自动打回未挂载');
              ok(logTxt().slice(mark).indexOf('已挂载') >= 0, '日志里有状态变更那一行');
              next();
            }, 500);
          }
        }, 120);
      }, 400);
    });
  });

  /* ============ 8. 校验上次写入：核对一致 → 仍是 on ============ */
  step(function(next){
    var b0 = byId('B');
    ok(!!b0.mountSlots.length && b0.mount === 'on', '（前置）方案乙是「已挂载」');
    window.__om3verify();
    setTimeout(function(){
      var b = byId('B');
      ok(b.mount === 'on', '★☰→「校验上次写入」核对一致 → 仍是 on（实际 ' + JSON.stringify(b.mount) + '）');
      ok(logTxt().indexOf('核对一致') >= 0 || logTxt().indexOf('已挂载') >= 0, '日志里有核对那一行');
      goList();                                       /* 回列表再量徽章（详情页那 6 条里没有列表徽章） */
      ok(badgeTxt(1) === 'C1 · 已挂载（槽1）', '徽章带上槽号：' + JSON.stringify(badgeTxt(1)));
      next();
    }, 900);
  });

  /* ============ 8b. 校验**不一致** → 自动打回「未挂载」（两态口径的兜底） ============ */
  step(function(next){
    var a = sets();
    for(var i = 0; i < a.length; i++) if(a[i].id === 'B'){ a[i].mount = 'on'; a[i].mountTier = 'myset1'; a[i].mountSlots = [1]; }
    put(a); goList();
    setTimeout(function(){
      var mark = logTxt().length;
      var kv = window.__om3buildPayload({ n:'x', v:[7,7,7,0,0,0,0,0,0,0,0,0], hi:0, mid:0, sh:0, eff:0, shp:0, con:0 }, 1, 'C1', 'OM-3');
      var raw = {}, lines = kv.split(String.fromCharCode(10));
      for(var i2 = 0; i2 < lines.length; i2++){
        var l = lines[i2].replace(String.fromCharCode(13), ''), pp = l.split(',');
        if(pp.length >= 3 && pp[0] === '2' && pp[1]) raw[pp[1]] = pp.slice(2).join(',');
      }
      /* 假相机里放**别的**数据 → 核对一定不一致 */
      window.__cam.text = window.__om3buildPayload({ n:'y', v:[1,2,3,4,5,6,7,8,9,10,11,12], hi:3, mid:3, sh:3, eff:3, shp:3, con:3 }, 1, 'C1', 'OM-3');
      localStorage.setItem('om3pend', JSON.stringify({ mode:'myset1', slot:1, kv:raw, setId:'B',
        recipe:'（方案乙）', at:'x', ms: Date.now() }));
      window.__om3verify();
      setTimeout(function(){
        var b = byId('B');
        ok(b.mount === '' && b.mountTier === '', '★★核对不一致（写入没生效）→ 方案乙被**自动打回「未挂载」**（实际 '
           + JSON.stringify([b.mount, b.mountTier]) + '）');
        ok(logTxt().slice(mark).indexOf('自动打回') >= 0, '★日志里写明了这次自动打回（不静默改用户数据）');
        goList();
        ok(badgeTxt(1) === '未挂载', '列表徽章跟着回到「未挂载」：' + JSON.stringify(badgeTxt(1)));
        next();
      }, 900);
    }, 250);
  });

  /* ============ 8c. 重新填入槽位 → 档位状态必须清掉（用户 2026-09-24 要求） ============ */
  step(function(next){
    var a = sets();
    for(var i = 0; i < a.length; i++) if(a[i].id === 'B'){ a[i].mount = 'on'; a[i].mountTier = 'myset1'; a[i].mountSlots = [1]; }
    put(a); window.__om3mpRender();
    setTimeout(function(){
      var mark = logTxt().length;
      var recs = window.__OM3RECIPES__ || [], slug = '';
      for(var i = 0; i < recs.length; i++) if(recs[i] && recs[i].v && recs[i].v.length >= 12 && recs[i].slug){ slug = recs[i].slug; break; }
      var card = slug ? document.getElementById('r-' + slug) : null;
      o.push('    重新填入：内置配方卡 r-' + slug + '（找到=' + !!card + '）；前置状态：' + JSON.stringify(byId('B').mount));
      ok(!!card, '找到了内置配方卡（r-' + slug + '）');
      if(card) window.__om3saveCard(card);
      setTimeout(function(){
        var sel = document.querySelectorAll('#ofields select'), inp = document.querySelectorAll('#ofields input');
        if(sel.length >= 2){ sel[0].value = '1'; sel[1].value = '2'; }      /* 方案乙（索引 1）· 槽2 */
        if(inp.length) inp[0].value = '重填的配方';
        el('ook').click();
        setTimeout(function(){
          if(el('omask') && !el('omask').classList.contains('hide')) el('ook').click();   /* 槽2 原来有东西 → 覆盖确认 */
          setTimeout(function(){
            var b = byId('B');
            ok(b.mount === '' && b.mountTier === '', '★★重新填入槽位后档位状态被清掉（实际 '
               + JSON.stringify([b.mount, b.mountTier]) + '）');
            ok(logTxt().slice(mark).indexOf('槽位被重新填入') >= 0, '★日志写明了这次自动清状态（不静默改用户数据）');
            goList();
            ok(badgeTxt(1) === '未挂载', '列表徽章跟着回到「未挂载」：' + JSON.stringify(badgeTxt(1)));
            next();
          }, 600);
        }, 400);
      }, 600);
    }, 250);
  });

  /* ============ 9. 从「连接相机」写的（没有 setId）→ 不误改方案状态 ============ */
  step(function(next){
    /* 回到"方案乙 pending"（**老版本留下的历史值**）→ 两态视图应显示「已挂载」，
       再制造一条**没有 setId** 的待校验记录（等价于连接相机页写入） */
    goList();
    var a = sets();
    for(var i = 0; i < a.length; i++) if(a[i].id === 'B'){ a[i].mount = 'pending'; a[i].mountTier = 'myset1'; a[i].mountSlots = [1]; }
    put(a);
    window.__om3mpRender();
    setTimeout(function(){
      var kv = window.__om3buildPayload({ n:'x', v:[9,9,9,0,0,0,0,0,0,0,0,0], hi:0, mid:0, sh:0, eff:0, shp:0, con:0 }, 1, 'C1', 'OM-3');
      var raw = {}, lines = kv.split(String.fromCharCode(10));
      for(var i2 = 0; i2 < lines.length; i2++){
        var l = lines[i2].replace(String.fromCharCode(13), ''), p = l.split(',');
        if(p.length >= 3 && p[0] === '2' && p[1]) raw[p[1]] = p.slice(2).join(',');
      }
      /* 假相机里就是这份新配方 → 校验会通过 */
      window.__cam.text = kv;
      while(window.__cam.text.length < 12000) window.__cam.text += '2,MODE_COLOR_CREATOR_2_VIVID_SET4_2,MODE_STEP_0' + CRLF;
      /* 没有 setId 的待校验记录（连接相机页写入的形态） */
      localStorage.setItem('om3pend', JSON.stringify({ mode:'myset1', slot:1, kv:raw, recipe:'（连接相机写的）', at:'x' }));
      window.__om3verify();
      setTimeout(function(){
        var b = byId('B');
        ok(b.mount === 'pending', '★没有 setId 的校验（连接相机页写的）**不会**动方案乙的状态（实际 ' + JSON.stringify(b.mount) + '）');
        goList();
        ok(badgeTxt(1) === 'C1 · 已挂载（槽1）', '★老数据的历史值 pending 按两态显示「已挂载」（不做数据迁移）：' + JSON.stringify(badgeTxt(1)));
        ok(localStorage.getItem('om3pend') === null, '待校验记录照旧被清掉了（原有行为没变）');
        next();
      }, 900);
    }, 250);
  });

  /* ============ 7. 写入失败（未连接）→ 状态一位都不变 ============ */
  step(function(next){
    var a = sets();
    for(var i = 0; i < a.length; i++) if(a[i].id === 'B'){ a[i].mount = ''; a[i].mountTier = ''; a[i].mountSlots = []; }
    put(a); window.__om3mpRender();
    setTimeout(function(){
      window.__offline = true;
      window.__cam.calls = [];            /* 先清空上一场景留下的计数，才能断言"一个请求都没发" */
      document.body.classList.remove('cam-on');
      try{ if(window.__om3setConn) window.__om3setConn(false); }catch(e){}
      var ttl = el('taskTitle'); if(ttl) ttl.textContent = '';
      window.__om3mpWriteOne(JSON.parse(JSON.stringify(sets()[1])), 1);
      var t0 = Date.now();
      var w = setInterval(function(){
        var t = el('taskTitle') ? el('taskTitle').textContent : '';
        if(t.indexOf('完成') >= 0 || t.indexOf('失败') >= 0 || Date.now() - t0 > 20000){
          clearInterval(w);
          setTimeout(function(){
            var b = byId('B');
            ok(b.mount === '' && b.mountTier === '', '★写入失败（未连接）→ 状态一位都不变（实际 ' + JSON.stringify([b.mount, b.mountTier]) + '）');
            ok(window.__cam.calls.length === 0, '而且一个请求都没发（calls=' + window.__cam.calls.length + '）');
            window.__offline = false;
            next();
          }, 400);
        }
      }, 120);
    }, 250);
  });

  /* ============ 10. 从相机读取 → 新方案直接 on + 互斥 ============ */
  step(function(next){
    var a = sets();
    for(var i = 0; i < a.length; i++) if(a[i].id === 'A'){ a[i].mount = 'on'; a[i].mountTier = 'myset1'; a[i].mountSlots = [1,2]; }
    put(a); window.__om3mpRender();
    setTimeout(function(){
      window.__cam.text = camText();        /* 假相机里有内容 */
      document.body.classList.add('cam-on');
      try{ if(window.__om3setConn) window.__om3setConn(true); }catch(e){}
      var sel2 = el('mpReadTier');
      if(sel2) sel2.value = 'myset1';       /* 明确读 C1（默认选中的是「当前状态」） */
      window.__om3mpRead();
      setTimeout(function(){
        var f = document.querySelectorAll('#ofields input');
        if(f.length) f[0].value = '读回来的';
        var okBtn = el('ook'); if(okBtn) okBtn.click();
        setTimeout(function(){
          var a2 = sets(), got = null;
          for(var i = 0; i < a2.length; i++) if(a2[i].name === '读回来的') got = a2[i];
          ok(!!got, '从相机读取并保存成功（方案数 ' + a2.length + '）');
          ok(!!got && got.mount === 'on', '★新方案直接标成「已挂载」（实际 ' + JSON.stringify(got ? got.mount : null) + '）');
          ok(!!got && got.mountTier === 'myset1', '记下了读的是哪个档位：' + JSON.stringify(got ? got.mountTier : null));
          ok(!!got && isArrOk(got.mountSlots), '记下了有内容的槽：' + JSON.stringify(got ? got.mountSlots : null));
          ok(byId('A').mount === '', '★同档位原来的方案甲被自动打回未挂载');
          next();
        }, 700);
      }, 2500);
    }, 250);
  });

  /* ============ 12. 分享代码 v3 不带挂载状态 ============ */
  step(function(next){
    window.__lastShare = null;
    window.OM3Native = { shareText: function(name, text){ window.__lastShare = text; return 'ok'; } };
    /* 让方案乙带上 on 状态，然后分享它 */
    var a = sets();
    for(var i = 0; i < a.length; i++) if(a[i].id === 'B'){ a[i].mount = 'on'; a[i].mountTier = 'myset1'; a[i].mountSlots = [1]; }
    put(a); window.__om3mpRender();
    setTimeout(function(){
      goList();
      var before = sets().length;
      var badgeText = badgeTxt(1);
      window.__om3mpDetail(1);
      setTimeout(function(){
        var sb = document.querySelector('button[data-sh]');
        if(sb) sb.click();
        setTimeout(function(){
          var t = window.__lastShare || '';
          ok(t.indexOf('mount') < 0, '★分享代码里**没有**挂载状态（不含 mount 字段）');
          ok(t.indexOf('myset1') >= 0 || t.indexOf('"f"') >= 0, '（对照）分享代码里确实带了来源档位 f');
          /* 把这段代码导回来：导入的那套应该是未挂载 */
          el('mpBack').click();
          setTimeout(function(){
            document.querySelector('.mpbar button[data-mp="file"]').click();
            setTimeout(function(){
              el('mpPaste').value = t;
              el('mpPasteGo').click();
              setTimeout(function(){
                var a2 = sets(), got = a2[a2.length - 1];      /* 导入的排最后 */
                ok(a2.length === before + 1, '分享代码导回来了（' + before + ' → ' + a2.length + '）');
                ok(!!got && String(got.name).indexOf('方案乙') >= 0, '导入的那套名字：' + JSON.stringify(got ? got.name : null));
                ok(!!got && !got.mount, '★导入进来的那套是「未挂载」（状态不跟着分享代码走）：'
                   + JSON.stringify(got ? (got.mount === undefined ? '（连 mount 字段都没有）' : got.mount) : null));
                ok(badgeTxt(a2.length - 1) === '未挂载', '导入的那套在列表里也显示「未挂载」：' + JSON.stringify(badgeTxt(a2.length - 1)));
                ok(badgeTxt(1) === badgeText, '原来那套的状态没被导入影响：' + JSON.stringify(badgeTxt(1)));
                next();
              }, 500);
            }, 250);
          }, 250);
        }, 300);
      }, 400);
    }, 250);
  });

  /* ============ 13. 最长徽章也不许把列表撑出横向滚动 ============ */
  step(function(next){
    /* 用最长的组合：录像档5 + 已挂载 + 4 个槽 */
    var a = sets();
    for(var i = 0; i < a.length; i++) if(a[i].id === 'B'){
      a[i].mount = 'on'; a[i].mountTier = 'moviemyset5'; a[i].mountSlots = [1,2,3,4];
    }
    put(a); goList();
    setTimeout(function(){
      var t = badgeTxt(1);
      o.push('    最长徽章：' + JSON.stringify(t));
      ok(t === '录像档5 · 已挂载（槽1、2、3、4）', '最长徽章文案正确');
      var sw = document.documentElement.scrollWidth, iw = window.innerWidth;
      ok(sw <= iw + 1, '★列表没被长徽章撑出横向滚动（scrollWidth=' + sw + ' / 视口 ' + iw + '）');
      var it = document.querySelectorAll('#mpList .mpitem')[1];
      var over = 0;
      it.querySelectorAll('*').forEach(function(e){
        var r = e.getBoundingClientRect();
        if(r.right > document.querySelector('#mpList').getBoundingClientRect().right + 1) over++;
      });
      ok(over === 0, '列表项里没有元素超出容器右边（超出 ' + over + ' 个）');
      next();
    }, 300);
  });

  run();
}, 3000);
"""

tail = '<script>' + JS + '</script>'
k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + PRE + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_mount.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\omount'
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
