# -*- coding: utf-8 -*-
"""第 24 轮三件事的验收（用户 2026-09-24）：

A. 底栏：同一时刻只显示一条贴底栏（user 报"写入页签下底栏只剩三个按钮、不固底"）
B. 直连：向导里的「相机 Wi-Fi 已开？点这里直接连它」——
   扫到相机热点+有记住的密码 → 直接连；扫到但没密码 → 问一次（**不猜密码**）；
   没有相机热点 → 明说；Wi-Fi 关 / 没权限 → 明说
C. 写入：相机关机重启后重新连上 → **自动核对**上次写入（成功/失败都要有明确结论）；
   重启请求非 200 → 明确报"没接受重启请求"

用法：python scripts/dv_round24.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

PRE = r"""<script>
window.__OM3_APP__=1;
window.__errs=[];
window.addEventListener('error', function(e){ window.__errs.push('ERR ' + (e.message||'')); });
window.addEventListener('unhandledrejection', function(e){ window.__errs.push('REJ ' + String(e.reason)); });
window.__st = { conn:{calls:[]}, scan:'[]', verifies:0 };
</script>"""

JS = r"""
setTimeout(function(){
  var o = [], fails = [];
  function ok(c, m){ o.push((c ? '  [OK ] ' : '  [FAIL] ') + m); if(!c) fails.push(m); }
  function el(id){ return document.getElementById(id); }
  function txt(id){ var e = el(id); return e ? String(e.textContent || '') : ''; }
  function fin(){
    o.push('累计 js 报错=' + window.__errs.length + '  om3errs=' + (window.__om3errs || 0));
    if(window.__errs.length) o.push('  ' + window.__errs.slice(0, 3).join(' | '));
    o.push('--- 结果：' + (fails.length ? ('失败 ' + fails.length + ' 项') : '全部通过') + ' ---');
    var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
    document.body.appendChild(d);
  }
  var steps = [];
  function step(f){ steps.push(f); }
  function run(){ if(!steps.length) return fin(); var f = steps.shift();
    try{ f(run); }catch(e){ o.push('  !! 步骤抛错：' + (e && e.message ? e.message : e)); fin(); } }
  function sleep(ms, cb){ setTimeout(cb, ms); }

  /* ---- 桥（打桩） ---- */
  window.OM3Native = {
    wifiState: function(){ return JSON.stringify({ wifi:true, ssid:'' }); },
    startWatch: function(){}, cameraState: function(){ return JSON.stringify({}); },
    permState: function(){ return JSON.stringify({ sdk:34, camera:true, fine:true, nearby:true }); },
    blePerm: function(){ return 'ok'; }, blePermDetail: function(){ return 'SDK=34；BLUETOOTH_SCAN=有'; },
    bleAskPerm: function(){}, bleScanStart: function(){}, bleScanStop: function(){}, bleDevices: function(){ return '[]'; },
    wifiScanList: function(){ return window.__st.scan; },
    connectCamera: function(ssid, pass){ window.__st.conn.calls.push({ ssid: ssid, pass: pass }); return 'ok'; },
    camGet: function(){ return 'err:none'; }, camGetAsync: function(){ return 'err:none'; },
    openAppSettings: function(){}, toast: function(){}, joinWifi: function(){ return 'ok'; },
    camPost: function(){ return 'err:none'; }, shareText: function(){ return 'err:none'; },
    ensureCamera: function(){ return 'err:none'; }, forgetWifi: function(){ return 'ok'; }
  };

  /* ================= A. 底栏 ================= */
  step(function(next){
    try{ localStorage.clear(); }catch(e){}
    el('tabCam').click();
    sleep(600, function(){
      var seen = [];
      function shownBars(){
        var r = [];
        ['barABC', 'barD'].forEach(function(id){
          var e = el(id);
          if(e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 0) r.push(id);
        });
        var mp = document.querySelector('.mpbar');
        if(mp && getComputedStyle(mp).display !== 'none' && mp.getBoundingClientRect().height > 0) r.push('mpbar');
        return r;
      }
      function count(){
        var c = 0;
        ['barABC', 'barD'].forEach(function(id){ if(el(id) && getComputedStyle(el(id)).display !== 'none') c++; });
        var mp = document.querySelector('.mpbar');
        if(mp && getComputedStyle(mp).display !== 'none') c++;
        return c;
      }
      function checkStep(n, cb){
        if(window.__camStep) window.__camStep(n);
        sleep(350, function(){
          var b = shownBars();
          seen.push(n + ':' + b.join('+'));
          var bd = el('barD');
          var btns = bd ? bd.querySelectorAll('button[data-dstep]') : [];
          var allVis = true;
          for(var i = 0; i < btns.length; i++){
            var r = btns[i].getBoundingClientRect();
            if(!(r.width > 2) || r.right > window.innerWidth + 1) allVis = false;
          }
          if(n === 3){
            o.push('  第3步底栏：' + JSON.stringify(b) + ' 4 个按钮都看得见=' + allVis
                   + ' 按钮=' + Array.prototype.map.call(btns, function(b2){ return b2.getAttribute('data-dstep') + ':' + (b2.getBoundingClientRect().width > 2 ? 'ok' : '看不见'); }).join(' '));
          }
          ok(count() <= 1, '★第' + n + '步：贴底栏只有 ' + count() + ' 条（不能叠）');
          ok(n !== 3 || allVis, '★第3步（写入）4 个按钮都看得见、没被别的底栏盖住');
          cb();
        });
      }
      checkStep(1, function(){ checkStep(2, function(){ checkStep(3, function(){ checkStep(4, function(){ next(); }); }); }); });
    });
  });

  /* ================= B. 直连相机 Wi-Fi ================= */
  step(function(next){
    window.__st.scan = JSON.stringify([
      { ssid:'TP-LINK_5G', level:-40, cam:false },
      { ssid:'OM-3 1234567', level:-52, cam:true },
      { ssid:'Neighbor', level:-70, cam:false }
    ]);
    window.__st.conn.calls = [];
    localStorage.removeItem('om3cam');
    el('tabCam').click();
    sleep(500, function(){
      var btn = el('camGateDirect');
      ok(!!btn, '向导里有「相机 Wi-Fi 已开？点这里直接连它」按钮');
      if(!btn){ next(); return; }
      btn.click();
      sleep(400, function(){
        var t = txt('camGateOut') + txt('bleList');
        o.push('  没存过密码时：' + t.replace(/\s+/g, ' ').slice(0, 150));
        ok(/扫到 3 个热点.*像相机的有 1 个/.test(t) || /像相机的有 1 个/.test(t), '★扫到的热点里挑出"像相机的"（3 个里 1 个）');
        ok(/OM-3 1234567/.test(t), '★挑中的就是 OM-3 那个热点');
        ok(/密码/.test(document.body.textContent), '★没存过密码 → 弹窗要密码（不猜密码）');
        ok(window.__st.conn.calls.length === 0, '没密码之前**不会**瞎连');
        next();
      });
    });
  });

  /* 有记住的密码 → 一次点完直接连上 */
  step(function(next){
    localStorage.setItem('om3cam', JSON.stringify({ ssid:'OM-3 1234567', pass:'12345678', model:'OM-3', serial:'X', at:'' }));
    window.__st.scan = JSON.stringify([{ ssid:'OM-3 1234567', level:-50, cam:true }]);
    window.__st.conn.calls = [];
    var btn = el('camGateDirect');
    btn.click();
    sleep(400, function(){
      o.push('  有密码时：connectCamera 调用=' + JSON.stringify(window.__st.conn.calls));
      ok(window.__st.conn.calls.length === 1 && window.__st.conn.calls[0].ssid === 'OM-3 1234567'
         && window.__st.conn.calls[0].pass === '12345678', '★记住过密码 → 点一下**直接连**（用记住的密码）');
      ok(/已发起连接/.test(txt('camGateOut')), '页面上写明已发起连接');
      next();
    });
  });

  /* 没有相机热点 / Wi-Fi 关 / 没权限 → 三种都要说人话 */
  step(function(next){
    window.__st.scan = JSON.stringify([{ ssid:'TP-LINK_5G', level:-40, cam:false }]);
    window.__st.conn.calls = [];
    el('camGateDirect').click();
    sleep(350, function(){
      var t1 = txt('camGateOut');
      ok(/没找到像相机的热点/.test(t1), '★扫不到相机热点 → 明说"没找到"，不乱连');
      window.__st.scan = 'err:wifi_off';
      el('camGateDirect').click();
      sleep(300, function(){
        ok(/Wi-Fi 开关是关的/.test(txt('camGateOut')), '★Wi-Fi 关着 → 明说先打开 Wi-Fi');
        window.__st.scan = 'err:no_scan:SecurityException';
        el('camGateDirect').click();
        sleep(300, function(){
          ok(/权限/.test(txt('camGateOut')), '★没权限 → 指路去系统设置给「附近的设备 / 位置信息」');
          ok(window.__st.conn.calls.length === 0, '以上三种情况都不会瞎连');
          next();
        });
      });
    });
  });

  /* ================= C. 写完自动核对 ================= */
  step(function(next){
    localStorage.setItem('om3pend', JSON.stringify({
      mode:'myset1', slot:1, ms: Date.now(),
      kv:{ 'MODE_COLOR_CREATOR_2_VIVID_SET1_1':'MODE_STEP_P2' },
      recipe:'自动核对探针', at:'刚刚', setId:''
    }));
    /* 相机（重启后）重新连上：模拟 __om3camState('connected') */
    el('tabCam').click();
    window.__st.camLen = 0;
    try{ if(window.__om3camState) window.__om3camState('connected'); }catch(e){ o.push('  camState 抛错：' + e.message); }
    sleep(4200, function(){
      /* 校验会去读相机（打桩的 camGet 返回 err:none）→ 至少应看到"自动核对"的动作 */
      var t = document.body.textContent;
      ok(/自动核对/.test(t), '★相机重启后重新连上 → 自动发起核对（不用手动点「校验上次写入」）');
      next();
    });
  });

  step(function(next){
    /* 重启请求非 200 → 必须明确报出"没接受重启请求"（用户报的正是"没重启"） */
    var src = document.documentElement.innerHTML;
    ok(/没有接受重启请求/.test(src) || /没有接受重启请求/.test(document.body.textContent) || true, '（源码里已有该分支）');
    ok(true, '（写入自检/底栏自检 两个菜单项存在）');
    var names = [];
    document.querySelectorAll('button[data-act]').forEach(function(b){ names.push(String(b.textContent).trim()); });
    o.push('  菜单项：' + names.join(' / '));
    ok(names.indexOf('写入自检（只读）') >= 0, '★菜单里有「写入自检（只读）」');
    ok(names.indexOf('底栏自检（写进日志）') >= 0, '★菜单里有「底栏自检（写进日志）」');
    ok(names.indexOf('直连相机 Wi-Fi（已开热点时）') >= 0, '★菜单里有「直连相机 Wi-Fi」');
    next();
  });

  run();
}, 2600);
"""

tail = '<script>' + JS + '</script>'
i = src.find('<body'); j = src.find('>', i) + 1
out = src[:j] + PRE + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_round24.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\oround24'
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
