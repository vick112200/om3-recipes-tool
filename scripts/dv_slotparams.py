# -*- coding: utf-8 -*-
"""槽位参数显示 + 「连接相机」两种状态（用户 2026-09-24 的两个问题）。

A. 我的方案 → 槽位：高光/中间调/阴影/阴影补偿/锐度/对比 有没有显示？写进相机写了没？
   验收点：
     1 详情页每槽有**中文**参数行：高光 / 中间调 / 阴影 / 阴影补偿 / 锐度 / 对比，值正确（+1/-1 这种）
     2 有「写进相机时会写的 18 项」折叠：18 个键 + 6 个影调键名都在，值 = 显示的值（同源）
     3 只有 raw、没有 hi/mid/lo 字段的槽（从相机读回/官方 .oes 导入）→ 显示 raw 解出来的真值，
       不再显示 0，并标注"按相机原始键值算的"
     4 6 项全默认 → 明说「6 项全默认」
     5 没有色轮数据的槽 → 明说"没有数据 / 写不了"
B. 连接相机：未连接 = 向导；已连接 = "能做什么"；两种状态内容不同
     6 未连接：向导卡可见、已连接卡隐藏、连接详情折叠可见
     7 已连接：向导卡隐藏、连接详情折叠隐藏、状态行+已连接卡可见（含机型/热点信息）
     8 断开后回到未连接那套

用法：python scripts/dv_slotparams.py
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
  function sets(){ try{ return JSON.parse(localStorage.getItem('om3sets') || '[]'); }catch(e){ return []; } }
  function put(a){ localStorage.setItem('om3sets', JSON.stringify(a)); }
  function visEq(e){
    if(!e || e.classList.contains('hide')) return false;
    var s = getComputedStyle(e);
    return s.display !== 'none' && e.offsetHeight > 0;
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

  /* 三种槽：① 有字段 ② 只有 raw（模拟从相机读回/官方导入） ③ 连色轮都没有 */
  function reseed(){
    var rawOnly = {};
    rawOnly['MODE_COLOR_CREATOR_2_TONE_CONTROL_HIGH_SET2']   = 'MODE_STEP_M3';
    rawOnly['MODE_COLOR_CREATOR_2_TONE_CONTROL_MIDDLE_SET2'] = 'MODE_STEP_P2';
    rawOnly['MODE_COLOR_CREATOR_2_TONE_CONTROL_LOW_SET2']    = 'MODE_STEP_P4';
    rawOnly['MODE_COLOR_CREATOR_2_SHADING_SET2']   = 'MODE_STEP_M1';
    rawOnly['MODE_COLOR_CREATOR_2_SHARP_SET2']     = 'MODE_SHARP_M2';
    rawOnly['MODE_COLOR_CREATOR_2_CONTRAST_SET2']  = 'MODE_CONTRAST_P2';
    put([
      { id:'P', name:'参数测试', desc:'', from:'myset1', camera:'OM-3', slots:{
          1:{ vivid:[2,3,2,2,0,-1,-3,-2,-1,0,0,2], raw:{}, used:9, hi:-1, mid:2, lo:-2, eff:0, shp:0, con:1, name:'有字段' },
          2:{ vivid:[1,0,0,0,0,0,0,0,0,0,0,1], raw:rawOnly, used:2, name:'只有raw' },
          3:{ vivid:[0,0,0,0,0,0,0,0,0,0,0,0], raw:{}, used:0, hi:0, mid:0, lo:0, eff:0, shp:0, con:0, name:'全默认' },
          4:{ name:'没数据' } } }
    ]);
    window.__om3mpRender();
    window.__om3mpDetail(0);
  }

  /* ===== A. 槽位参数 ===== */
  step(function(next){
    reseed();
    var items = document.querySelectorAll('#mpList .mpitem');
    o.push('  详情页条目=' + items.length);
    var all = '';
    for(var i = 0; i < items.length; i++) all += (items[i].textContent || '') + '\n';
    all = all.replace(/\s+/g, ' ');
    ok(all.indexOf('高光') >= 0 && all.indexOf('中间调') >= 0 && all.indexOf('阴影') >= 0 &&
       all.indexOf('阴影补偿') >= 0 && all.indexOf('锐度') >= 0 && all.indexOf('对比') >= 0,
       '★参数行用的是中文名（高光 / 中间调 / 阴影 / 阴影补偿 / 锐度 / 对比）');

    /* 槽 1：字段值 → 显示值必须是 -1 / 2 / -2 / 0 / 0 / 1 */
    var t1 = (items[1].textContent || '').replace(/\s+/g, ' ');
    var m1 = /高光 ([+\-−]?\d+).*?中间调 ([+\-−]?\d+).*?阴影 ([+\-−]?\d+).*?阴影补偿 ([+\-−]?\d+).*?锐度 ([+\-−]?\d+).*?对比 ([+\-−]?\d+)/.exec(t1);
    o.push('    槽1 参数行：' + (m1 ? m1.slice(1).join(' / ') : '（没匹配到）'));
    ok(!!m1 && m1[1] === '-1' && m1[2] === '+2' && m1[3] === '-2' && m1[4] === '0' && m1[5] === '0' && m1[6] === '+1',
       '★槽1 显示的就是存的字段值（高光 -1 / 中间调 +2 / 阴影 -2 / 阴影补偿 0 / 锐度 0 / 对比 +1）');

    /* 槽 1：18 项键值折叠 */
    var det = items[1].querySelector('details');
    var kvTxt = '';
    var found = null;
    var ds = items[1].querySelectorAll('details');
    for(var q = 0; q < ds.length; q++) if(String(ds[q].textContent).indexOf('写进相机时会写的') >= 0) found = ds[q];
    ok(!!found, '★槽1 有「写进相机时会写的 N 项」折叠');
    if(found){
      kvTxt = (found.textContent || '').replace(/\s+/g, ' ');
      o.push('    折叠标题：' + kvTxt.slice(0, 60));
      var keys = ['MODE_COLOR_CREATOR_2_VIVID_SET1_1','MODE_COLOR_CREATOR_2_VIVID_SET1_12',
                  'MODE_COLOR_CREATOR_2_TONE_CONTROL_HIGH_SET1','MODE_COLOR_CREATOR_2_TONE_CONTROL_MIDDLE_SET1',
                  'MODE_COLOR_CREATOR_2_TONE_CONTROL_LOW_SET1','MODE_COLOR_CREATOR_2_SHADING_SET1',
                  'MODE_COLOR_CREATOR_2_SHARP_SET1','MODE_COLOR_CREATOR_2_CONTRAST_SET1'];
      var miss = [];
      for(var w = 0; w < keys.length; w++) if(kvTxt.indexOf(keys[w]) < 0) miss.push(keys[w]);
      ok(miss.length === 0, '★影调 6 项 + 12 轴键名都写着（缺：' + (miss.join(',') || '无') + '）');
      ok(kvTxt.indexOf('18 项') >= 0, '标题写明是 18 项');
      /* 值要和显示一致：高光 -1 → MODE_STEP_M1；对比 +1 → MODE_CONTRAST_P1 */
      ok(kvTxt.indexOf('MODE_COLOR_CREATOR_2_TONE_CONTROL_HIGH_SET1 = MODE_STEP_M1') >= 0,
         '★写进相机的高光值 = 显示的值（MODE_STEP_M1）');
      ok(kvTxt.indexOf('MODE_COLOR_CREATOR_2_CONTRAST_SET1 = MODE_CONTRAST_P1') >= 0, '对比同理（MODE_CONTRAST_P1）');
      ok(kvTxt.indexOf('MODE_COLOR_CREATOR_2_SHARP_SET1 = MODE_SHARP_0') >= 0, '锐度同理（MODE_SHARP_0）');
    }
    next();
  });

  /* 槽 2：只有 raw → 显示 raw 解出来的真值（不是 0） */
  step(function(next){
    var items = document.querySelectorAll('#mpList .mpitem');
    var t2 = (items[2].textContent || '').replace(/\s+/g, ' ');
    var m2 = /高光 ([+\-−]?\d+).*?中间调 ([+\-−]?\d+).*?阴影 ([+\-−]?\d+).*?阴影补偿 ([+\-−]?\d+).*?锐度 ([+\-−]?\d+).*?对比 ([+\-−]?\d+)/.exec(t2);
    o.push('    槽2（只有 raw）参数行：' + (m2 ? m2.slice(1).join(' / ') : '（没匹配到）'));
    ok(!!m2 && m2[1] === '-3' && m2[2] === '+2' && m2[3] === '+4' && m2[4] === '-1' && m2[5] === '-2' && m2[6] === '+2',
       '★只有 raw 的槽，显示的是 raw 解出来的真值（-3 / +2 / +4 / -1 / -2 / +2），不再是 0');
    ok(t2.indexOf('按相机原始键值算的') >= 0, '★并且标注了"这槽是按相机原始键值算的"');

    /* 槽 3：全默认 → 明说 */
    var t3 = (items[3].textContent || '').replace(/\s+/g, ' ');
    ok(t3.indexOf('6 项全默认') >= 0, '★6 项全默认时明确写出来');

    /* 槽 4：没有色轮数据 → 写不了要说清楚 */
    var t4 = (items[4].textContent || '').replace(/\s+/g, ' ');
    o.push('    槽4 文字：' + t4.slice(0, 90));
    ok(t4.indexOf('没有数据') >= 0 || t4.indexOf('写不了') >= 0, '★没数据的槽明确说"没有数据/写不了"');
    next();
  });

  /* ===== B. 连接两态 ===== */
  step(function(next){
    document.getElementById('tabCam').click();
    setTimeout(function(){
      var gate = el('camGateOff'), on = el('camOnCard'), st = el('camStatusCard'), fold = el('camV1Fold');
      o.push('  未连接：向导=' + visEq(gate) + ' 已连接卡=' + visEq(on) + ' 状态行=' + visEq(st) + ' 详情折叠=' + visEq(fold));
      ok(visEq(gate), '★未连接 → 显示向导卡');
      ok(!visEq(on), '★未连接 → 不显示"已连接"卡');
      ok(visEq(fold), '未连接 → 连接详情折叠可见（扫码/手动填/检测）');
      ok(!visEq(st), '未连接 → 不显示已连接状态行');

      /* 切到"已连接" */
      try{ localStorage.setItem('om3cam', JSON.stringify({ ssid:'OM-3-TEST', pass:'12345678', model:'OM-3', serial:'BJ0001', at:new Date().toLocaleString('zh-CN') })); }catch(e){}
      window.__om3setConn(true);
      setTimeout(function(){
        o.push('  已连接：向导=' + visEq(gate) + ' 已连接卡=' + visEq(on) + ' 状态行=' + visEq(st) + ' 详情折叠=' + visEq(fold));
        ok(!visEq(gate), '★已连接 → 向导（扫码/手动填那一套）收起来');
        ok(!visEq(fold), '★已连接 → 连接详情折叠也收起来');
        ok(visEq(st), '★已连接 → 显示"已连接：SSID"状态行');
        ok(visEq(on), '★已连接 → 显示「现在能做什么」卡');
        var info = (el('camOnInfo').textContent || '').replace(/\s+/g, ' ');
        o.push('    已连接卡信息：' + info.slice(0, 120));
        ok(info.indexOf('OM-3-TEST') >= 0 || info.indexOf('热点') >= 0, '★卡里写清了热点/机型（不是空话）');
        ok(info.indexOf('BJ0001') >= 0, '序列号也带上了');
        /* 卡片上的按钮都在 */
        var b4 = ['camOnBak','camOnWrite','camOnCheck','camOnForget'];
        var missb = [];
        for(var i = 0; i < b4.length; i++) if(!el(b4[i])) missb.push(b4[i]);
        ok(missb.length === 0, '★"能做什么"卡的 4 个按钮都在（缺：' + (missb.join(',') || '无') + '）');
        ok(visEq(el('camOnBak')) && visEq(el('camOnWrite')), '去备份 / 去写入 看得见');

        /* 「去写入」跳步骤 ③ */
        el('camOnWrite').click();
        setTimeout(function(){
          ok(visEq(el('camV3')), '★点「③ 去写入配方」→ 真的跳到写入那一步');
          /* 断开 → 回到未连接那套 */
          window.__om3setConn(false);
          setTimeout(function(){
            o.push('  断开后（还在③）：向导=' + visEq(gate) + ' 已连接卡=' + visEq(on) + ' 详情折叠=' + visEq(fold));
            ok(!visEq(on) && !visEq(st), '★断开 → 已连接卡/状态行消失');
            ok(!visEq(gate) && !visEq(fold), '★断开时人还在③ → 向导**不硬塞到这一步**（用户：别的页面不回去）');
            ok(visEq(el('camV3')), '（断开时仍停在③，步骤内容不变）');
            ok(String(el('gateHintD').className).indexOf('show') >= 0, '★③ 上出现相机还没连上提示条');
            document.getElementById('tabCam').click();
            var m1 = document.querySelector('.cammdrop button[data-step="1"]');
            if(m1) m1.click(); else if(window.showStep) window.showStep(1);
            setTimeout(function(){
              o.push('  回到①后：向导=' + visEq(gate) + ' 详情折叠=' + visEq(fold));
              ok(visEq(gate) && visEq(fold), '★回到①步（连接页面）→ 向导 + 详情折叠都在（自然回向导）');
              next();
            }, 300);
          }, 400);
        }, 400);
      }, 400);
    }, 700);
  });

  run();
}, 3000);
"""

tail = '<script>' + JS + '</script>'
k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + PRE + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_slotparams.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\oslotparams'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,1100',
                    '--virtual-time-budget=40000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
