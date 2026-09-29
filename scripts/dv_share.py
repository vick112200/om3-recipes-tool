# -*- coding: utf-8 -*-
"""「分享」子页 + v3 分享格式实测（无头 Chrome，不接真相机）。

覆盖 SPEC-round16.md：
  UC-R16-02 「文件」子页 → 「分享」：粘贴框 / 解析并导入 / 清空 / 复制成一段代码 / 保留原有 4 个按钮
  UC-R16-03 导出：**单行** / 短键 / **不带 18 个长 raw 键** / **带描述**（画面感觉·适合·避开·提示·标签）
  UC-R16-04 导入：v3 / v2 多套 / v1 单槽 / 官方 .oes / 坏内容 / 空内容，**文件和粘贴共用一份解析**
  UC-R16-05 槽位没有名字时要显示「（还没起名）」，且不再拿整套方案名冒充槽位名

用法：python scripts/dv_share.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

head = ("<script>window.__OM3_APP__=1;"
        "window.__errs=[];"
        "window.addEventListener('error',function(e){window.__errs.push('ERR '+(e.message||''));});"
        "window.addEventListener('unhandledrejection',function(e){window.__errs.push('REJ '+String(e.reason));});"
        "</script>")

JS = r"""
setTimeout(function(){
  var o = [], fails = [];
  function ok(c, m){ o.push((c ? '  [OK ] ' : '  [FAIL] ') + m); if(!c) fails.push(m); }
  function sets(){ try{ return JSON.parse(localStorage.getItem('om3sets') || '[]'); }catch(e){ return []; } }
  function el(id){ return document.getElementById(id); }
  function logTxt(){ var e = el('camOut3'); return e ? (e.textContent || '').replace(/\s+/g, ' ') : ''; }
  function fin(){
    o.push('累计 js 报错=' + (window.__errs ? window.__errs.length : 0) + '  om3errs=' + (window.__om3errs || 0));
    o.push('--- 结果：' + (fails.length ? ('失败 ' + fails.length + ' 项') : '全部通过') + ' ---');
    var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
    document.body.appendChild(d);
  }
  var steps = [];
  function step(f){ steps.push(f); }
  function run(){
    if(!steps.length) return fin();
    var f = steps.shift();
    try{ f(run); }catch(e){ o.push('  !! 步骤抛错：' + (e && e.message ? e.message : e)); fin(); }
  }
  function click(id){ var b = el(id); if(b) b.click(); else o.push('  !! 找不到按钮 #' + id); }

  /* ---------- 造一套方案：槽1 有完整描述；raw 故意为空（新格式/官方导入都是这样） ---------- */
  function seed(extra){
    var S = [{ id:'s1', name:'测试方案甲', desc:'甲描述', from:'myset2', camera:'OM-3',
      slots:{ 1:{ vivid:[1,2,3,0,0,0,0,0,0,0,0,0], raw:{}, used:3, hi:1, mid:-1, lo:2, eff:0, shp:0, con:1,
                  name:'配方甲', d:'一句话描述', feel:'画面感觉文案', key:'色彩重点文案', tone:'影调文案',
                  good:'适合人像', bad:'避开夜景', tip:'曝光-0.3', tags:['微浓','偏冷'] },
              2:null, 3:null, 4:null } }];
    if(extra) S = S.concat(extra);
    localStorage.setItem('om3sets', JSON.stringify(S));
    try{ window.__om3mpRender(); }catch(e){}
  }
  function copyCodeText(){
    var p = document.querySelector('#mpFileOut .mppre');
    return p ? String(p.textContent || '') : '';
  }
  function paste(text){
    el('mpPaste').value = text;
    click('mpPasteGo');
  }

  /* ============ 1. 「分享」子页存在 + 底部按钮改名 ============ */
  step(function(next){
    try{ localStorage.removeItem('om3sets'); }catch(e){}
    el('tabMine').click();
    setTimeout(function(){
      var names = [];
      document.querySelectorAll('.mpbar button[data-mp]').forEach(function(b){ names.push(b.getAttribute('data-mp') + '=' + (b.textContent || '').trim()); });
      o.push('底栏按钮：' + JSON.stringify(names));
      ok(names.indexOf('file=分享') >= 0, '第 4 个子页按钮已从「文件」改成「分享」');
      document.querySelector('.mpbar button[data-mp="file"]').click();
      setTimeout(function(){
        var sec = el('mpsub-file');
        ok(!!sec && getComputedStyle(sec).display !== 'none', '「分享」子页可见');
        ['mpPaste','mpPasteGo','mpPasteClear','mpCopyCode','mpShareAll','mpExportAll','mpImportFile','mpImpSlot','mpFileOut'].forEach(function(id){
          ok(!!el(id), '有 #' + id);
        });
        next();
      }, 120);
    }, 700);
  });

  /* ============ 2. 复制成一段代码：单行 / 无 raw / 带描述 / 比旧格式小 ============ */
  var CODE = '';
  step(function(next){
    seed();
    setTimeout(function(){ click('mpCopyCode'); }, 60);
    setTimeout(function(){
      CODE = copyCodeText();
      ok(CODE.length > 40, '「复制成一段代码」把代码显示出来了（' + CODE.length + ' 字符）');
      ok(CODE.indexOf('\n') < 0 && CODE.indexOf('\r') < 0, '★分享代码是**单行**的（没有换行符）');
      ok(CODE.indexOf('MODE_COLOR_CREATOR_2_') < 0, '★不含那 18 个长 raw 键');
      var obj = null;
      try{ obj = JSON.parse(CODE); }catch(e){}
      ok(!!obj && obj.k === 'OM3CP' && obj.v === 3, '顶层是 {"k":"OM3CP","v":3}');
      var s0 = obj && obj.st && obj.st[0];
      ok(!!s0 && s0.n === '测试方案甲' && s0.f === 'myset2', '方案名/档位在（' + (s0 ? (s0.n + ' / ' + s0.f) : '') + '）');
      var sl = s0 && s0.s && s0.s[0];
      ok(!!sl && sl.length === 27, '槽数组 27 项（实际 ' + (sl ? sl.length : 'null') + '）');
      ok(!!sl && sl[18] === '配方甲', '槽名带上了：' + JSON.stringify(sl ? sl[18] : null));
      var want = { 19:'一句话描述', 20:'画面感觉文案', 21:'色彩重点文案', 22:'影调文案', 23:'适合人像', 24:'避开夜景', 25:'曝光-0.3', 26:'微浓,偏冷' };
      var bad = [];
      for(var k in want) if(!sl || sl[k] !== want[k]) bad.push(k + '≠' + JSON.stringify(sl ? sl[k] : null));
      ok(bad.length === 0, '★描述字段**全都跟着走了**（一句话/画面感觉/色彩重点/影调/适合/避开/提示/标签）' + (bad.length ? '，缺：' + bad.join(' ') : ''));
      ok(!sl || (sl[12] === 1 && sl[13] === -1 && sl[14] === 2 && sl[17] === 1), '影调 6 项也在（hi/mid/lo/con 对不对：' + (sl ? [sl[12],sl[13],sl[14],sl[15],sl[16],sl[17]].join(',') : '') + '）');
      ok(obj && obj.st[0].s[1] === null && obj.st[0].s[2] === null && obj.st[0].s[3] === null, '空槽写成 null');
      /* 和旧格式（v2 缩进 + 18 个长 raw 键）比体积 */
      var raw = {}, i;
      for(i = 1; i <= 12; i++) raw['MODE_COLOR_CREATOR_2_VIVID_SET1_' + i] = 'MODE_STEP_0';
      ['TONE_CONTROL_HIGH_SET','TONE_CONTROL_MIDDLE_SET','TONE_CONTROL_LOW_SET','SHADING_SET','SHARP_SET','CONTRAST_SET'].forEach(function(x){ raw['MODE_COLOR_CREATOR_2_' + x + '1'] = 'MODE_STEP_0'; });
      var oldPack = { app:'OM-3 色彩配方手册', kind:'om3-colorprofile', version:2, name:'测试方案甲', desc:'甲描述', from:'myset2', camera:'OM-3',
                      slots:{ 1:{ vivid:[1,2,3,0,0,0,0,0,0,0,0,0], raw:raw, used:3, name:'配方甲' }, 2:null, 3:null, 4:null } };
      var oldLen = JSON.stringify(oldPack, null, 1).length;
      o.push('    体积：旧格式 ' + oldLen + ' 字符 → v3 ' + CODE.length + ' 字符（约 ' + Math.round(CODE.length / oldLen * 100) + '%）');
      ok(CODE.length < oldLen * 0.6, '★v3 明显比旧格式小');
      next();
    }, 600);
  });

  /* ============ 2b. 「只有名字没参数」的槽 → 跳过时必须**报出来**（不能静默丢） ============ */
  step(function(next){
    localStorage.setItem('om3sets', JSON.stringify([
      { id:'s2', name:'仅名字测试', desc:'', from:'myset1', camera:'OM-3',
        slots:{ 1:{ vivid:null, raw:{}, used:0, name:'只有名字的槽' },
                2:{ vivid:[2,0,0,0,0,0,0,0,0,0,0,0], raw:{}, used:1, hi:0, mid:0, lo:0, eff:0, shp:0, con:0, name:'有参数的槽' },
                3:null, 4:null } } ]));
    window.__om3mpRender();
    setTimeout(function(){
      var mark = logTxt().length;
      click('mpCopyCode');
      setTimeout(function(){
        var t = copyCodeText(), obj = null;
        try{ obj = JSON.parse(t); }catch(e){}
        ok(!!obj && obj.st[0].s[0] === null && obj.st[0].s[1] !== null,
           '只有名字的槽被写成 null，有参数的槽照旧在');
        ok(logTxt().slice(mark).indexOf('只有名字') >= 0,
           '★日志**明确报出**"有槽只有名字、没带进分享代码"（不静默丢）');
        /* 把环境恢复成第 3 步需要的状态 */
        seed();
        setTimeout(next, 120);
      }, 500);
    }, 200);
  });

  /* ============ 3. 粘贴导入：+1、描述齐全、名字加（导入） ============ */
  var before2 = 0;
  step(function(next){
    before2 = sets().length;
    paste(CODE);
    setTimeout(function(){
      var a = sets();
      o.push('    粘贴导入：' + before2 + ' → ' + a.length);
      ok(a.length === before2 + 1, '★粘贴一段代码 → 方案数 +1');
      var s = a[a.length - 1];
      ok(s.name === '测试方案甲（导入）', '重名自动加后缀：' + JSON.stringify(s.name));
      var one = s.slots && s.slots[1];
      ok(!!one, '导入后槽1 有内容');
      ok(!!one && one.feel === '画面感觉文案' && one.good === '适合人像' && one.bad === '避开夜景' && one.tip === '曝光-0.3',
         '★导入后描述**看得见**（feel/good/bad/tip 都在）');
      ok(!!one && personTagsOk(one), '标签也导进来了：' + JSON.stringify(one ? one.tags : null));
      ok(!!one && one.raw && Object.keys(one.raw).length === 0, '导入的槽 raw 是空的（写入时现算 —— 由 dv_mpwrite.py 场景 D 验证能写）');
      ok(!!one && one.name === '配方甲', '槽名 = 配方甲');
      ok(el('mpPaste').value === '', '导入成功后粘贴框被清空');
      next();
    }, 500);
  });
  function personTagsOk(one){
    return one && one.tags && one.tags.length === 2 && one.tags[0] === '微浓' && one.tags[1] === '偏冷';
  }

  /* ============ 4. 同一段代码再贴一次：还能再导（不幂等，和老行为一致） ============ */
  step(function(next){
    var b = sets().length;
    paste(CODE);
    setTimeout(function(){
      var a = sets();
      ok(a.length === b + 1, '同一段代码再贴一次：' + b + ' → ' + a.length + '（期望再 +1）');
      ok(a[a.length - 1].name === '测试方案甲（导入2）', '第二次重名后缀递增：' + JSON.stringify(a[a.length - 1].name));
      next();
    }, 450);
  });

  /* ============ 5. 详情页里「分享这个槽」也是 v3 单行 ============ */
  step(function(next){
    window.__lastShare = null;
    window.OM3Native = { shareText: function(name, text, mime){ window.__lastShare = { name:name, text:text, mime:mime }; return 'ok'; } };
    var it = document.querySelector('#mpList .mpitem');
    if(it) it.click();
    setTimeout(function(){
      var b = document.querySelector('button[data-sh]');
      ok(!!b, '详情页有「分享这个槽」');
      if(b) b.click();
      setTimeout(function(){
        var sh = window.__lastShare;
        ok(!!sh, '走了系统分享（OM3Native.shareText 被调用）');
        var t = sh ? sh.text : '';
        ok(t.indexOf('\n') < 0 && t.indexOf('MODE_COLOR_CREATOR_2_') < 0, '★单槽分享也是 v3 单行、不含 raw');
        var obj = null; try{ obj = JSON.parse(t); }catch(e){}
        ok(!!obj && obj.v === 3 && obj.st[0].s[0] !== null && obj.st[0].s[1] === null
           && obj.st[0].s[2] === null && obj.st[0].s[3] === null,
           '点的槽1 → 只有第 1 个槽有内容，其余是 null');
        var sl = obj && obj.st[0].s[0];
        ok(!!sl && sl[20] === '画面感觉文案', '单槽分享也带着描述');
        ok(!!sh && /槽1/.test(sh.name), '分享标题带槽位号：' + JSON.stringify(sh ? sh.name : null));
        next();
      }, 350);
    }, 500);
  });

  /* ============ 6. 坏内容 / 空内容 → 不导入、不报错、说清原因 ============ */
  step(function(next){
    click('mpBack');
    setTimeout(function(){
      var b = sets().length, mark = logTxt().length;
      paste('{"hello":"world"}');
      setTimeout(function(){
        ok(sets().length === b, '坏 JSON：方案数不变（' + b + '）');
        ok(logTxt().slice(mark).indexOf('不认识') >= 0, '坏 JSON：日志说清了原因');
        ok(el('mpPaste').value.length > 0, '失败时粘贴框内容**保留**（方便改）');
        el('mpPaste').value = '';
        click('mpPasteGo');
        setTimeout(function(){
          ok(sets().length === b, '空内容：方案数不变');
          ok(logTxt().slice(mark).indexOf('内容是空的') >= 0, '空内容：明确说"内容是空的"');
          /* 结构对但字段类型是坏的（字符串也有 length → 不判数组就会造出一堆全 0 的假槽） */
          var bads = [
            ['{"k":"OM3CP","v":3,"st":"abc"}', 'st 不是方案数组'],
            ['{"k":"OM3CP","v":3,"st":[{"n":"x","s":"abc"}]}', '没有槽位内容'],
            ['{"kind":"om3-colorprofile","sets":"abc"}', '没有方案数据']
          ];
          var i = 0;
          (function one(){
            if(i >= bads.length){
              ok(window.__errs.length === 0 && (window.__om3errs || 0) === 0,
                 '★以上坏内容都没产生未捕获异常（js 报错 ' + window.__errs.length + ' / om3errs ' + (window.__om3errs || 0) + '）');
              next(); return;
            }
            var pair = bads[i++], m2 = logTxt().length;
            paste(pair[0]);
            setTimeout(function(){
              ok(sets().length === b, '坏结构「' + pair[0].slice(0, 34) + '…」：方案数不变');
              ok(logTxt().slice(m2).indexOf(pair[1]) >= 0,
                 '坏结构：日志出现「' + pair[1] + '」');
              one();
            }, 300);
          })();
        }, 300);
      }, 400);
    }, 400);
  });

  /* ============ 7. 老格式兼容：v2 多套 / v1 单槽 / 官方 .oes ============ */
  step(function(next){
    var b = sets().length;
    var V2 = { app:'OM-3 色彩配方手册', kind:'om3-colorprofile', version:2, count:2,
               sets:[ { name:'老甲', desc:'d甲', from:'myset1', camera:'OM-3',
                        slots:{ 1:{ vivid:[1,2,3,0,0,0,0,0,0,0,0,0], raw:{'X':1}, used:3, name:'n甲' }, 2:null,3:null,4:null } },
                      { name:'老乙', desc:'d乙', from:'myset2', camera:'OM-3', slots:{ 1:null,2:null,3:null,4:null } } ] };
    paste(JSON.stringify(V2));
    setTimeout(function(){
      ok(sets().length === b + 2, 'v2 多套：' + b + ' → ' + sets().length + '（期望 +2）');
      var b2 = sets().length;
      var V1 = { app:'OM-3 色彩配方手册', kind:'om3-colorprofile', version:1, name:'老单槽', desc:'d', from:'myset3',
                 slots:{ 1:null, 2:{ vivid:[0,0,0,0,0,1,1,1,0,0,0,0], raw:{'Y':2}, used:3 }, 3:null, 4:null } };
      paste(JSON.stringify(V1));
      setTimeout(function(){
        ok(sets().length === b2 + 1, 'v1 单槽（没有 sets）：' + b2 + ' → ' + sets().length + '（期望 +1）');
        var b3 = sets().length;
        el('mpImpSlot').value = '3';
        var OES = '<?xml version="1.0"?><ImageProcessing Version="1.0">'
                + '<ColorCreater2 SatValue="1,2,3,0,0,0,0,0,0,0,0,0"/>'
                + '<ToneControl Bright="-1" Mid="1" Dark="2"/><Sharpness Value="0"/><Contrast Value="1"/></ImageProcessing>';
        paste(OES);
        setTimeout(function(){
          var a = sets();
          ok(a.length === b3 + 1, '官方 .oes 粘贴导入：' + b3 + ' → ' + a.length + '（期望 +1）');
          var s = a[a.length - 1];
          ok(!!s.slots[3] && s.slots[3].vivid[0] === 1, '落点在「导入到」选的槽 3');
          ok(s.from === 'imported', '官方导入的档位记成 imported（详情页会显示"档位未定"）');
          ok(s.name === '官方 .oes 配置', '官方 .oes 粘贴导入用了兜底名：' + JSON.stringify(s.name));
          next();
        }, 450);
      }, 450);
    }, 450);
  });

  /* ============ 8. 文件导入也走同一解析（#mpFile 的 change） ============ */
  step(function(next){
    click('mpImportFile');                     /* 建出隐藏的 #mpFile */
    setTimeout(function(){
      var inp = el('mpFile');
      ok(!!inp, '#mpFile 被创建（不是绑在占位对象上）');
      var b = sets().length;
      try{
        var dt = new DataTransfer();
        dt.items.add(new File([CODE], 'shared.json', { type: 'application/json' }));
        inp.files = dt.files;
        inp.dispatchEvent(new Event('change', { bubbles: true }));
      }catch(e){ o.push('  !! 派发失败：' + e.message); }
      setTimeout(function(){
        ok(sets().length === b + 1, '★文件导入和粘贴导入走同一份解析：' + b + ' → ' + sets().length + '（期望 +1）');
        next();
      }, 500);
    }, 400);
  });

  /* ============ 9. UC-R16-05：相机读回来的无名槽要显示「（还没起名）」 ============ */
  step(function(next){
    localStorage.setItem('om3sets', JSON.stringify([
      { id:'r1', name:'从相机读的', desc:'', from:'myset1', camera:'OM-3',
        slots:{ 1:{ vivid:[1,1,0,0,0,0,0,0,0,0,0,0], raw:{'a':1}, used:2 },       /* 有内容、没名字 */
                2:{ vivid:[0,0,0,0,0,0,0,0,0,0,0,0], raw:{'a':0}, used:0, name:'起过名的槽' },  /* 有名字 */
                3:null, 4:null } } ]));
    window.__om3mpDetail(0);
    setTimeout(function(){
      var rows = document.querySelectorAll('#mpList .mpsrow');
      ok(rows.length >= 4, '详情页有 4 行槽位（实际 ' + rows.length + '）');
      var t1 = rows[0] ? (rows[0].textContent || '').replace(/\s+/g, ' ') : '';
      var t2 = rows[1] ? (rows[1].textContent || '').replace(/\s+/g, ' ') : '';
      var t3 = rows[2] ? (rows[2].textContent || '').replace(/\s+/g, ' ') : '';
      o.push('    槽1行：' + JSON.stringify(t1.slice(0, 70)));
      o.push('    槽2行：' + JSON.stringify(t2.slice(0, 70)));
      ok(t1.indexOf('还没起名') >= 0, '★没名字的槽显示「（还没起名）」');
      ok(t1.indexOf('从相机读的') < 0, '★没有拿整套方案名冒充槽位名');
      ok(t2.indexOf('起过名的槽') >= 0 && t2.indexOf('还没起名') < 0, '有名字的槽照旧显示名字、不显示提示');
      ok(t3.indexOf('还没起名') < 0, '空槽不显示「还没起名」（那是噪音）');
      /* 未连接相机时，「写入相机」应该是灰的（.dis = 半透明 + pointer-events:none）。
         这条本来由块 08 的 1 秒循环负责，这里盯住它别退化（SPEC §6 第 7 项）。 */
      var wb = document.querySelector('#mpList button[data-w]');
      ok(!!wb, '详情页有「写入相机」按钮');
      document.body.classList.remove('cam-on');          /* 明确"未连接" */
      setTimeout(function(){
        ok(!!wb && wb.classList.contains('dis'), '★未连接相机时「写入相机」是灰的（点了没反应、不弹窗）');
        /* 「分享」子页排版：粘贴框不该撑出横向滚动（412 视口） */
        document.querySelector('.mpbar button[data-mp="file"]').click();
        setTimeout(function(){
          var ta = el('mpPaste'), sec = el('mpsub-file');
          var over = ta ? (ta.scrollWidth - ta.clientWidth) : -1;
          o.push('    #mpPaste 宽=' + (ta ? ta.clientWidth : '?') + ' 超出=' + over + 'px；页面 scrollWidth=' + document.documentElement.scrollWidth + ' / 视口 ' + window.innerWidth);
          ok(!!ta && over <= 1, '粘贴框没有横向溢出');
          ok(document.documentElement.scrollWidth <= window.innerWidth + 1, '「分享」子页没有把页面撑出横向滚动');
          ok(!!sec && sec.offsetHeight > 0, '「分享」子页有内容（高 ' + (sec ? sec.offsetHeight : '?') + 'px）');
          next();
        }, 200);
      }, 1300);
    }, 500);
  });

  run();
}, 2800);
"""

tail = '<script>' + JS + '</script>'
k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_share.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\oshare'
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
