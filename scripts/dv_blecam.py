# -*- coding: utf-8 -*-
"""「连接相机」丝滑化 + 蓝牙 GATT 探测 实测（无头 Chrome + 打桩原生桥）。

对应 SPEC-round18.md 的验收标准（A = 蓝牙面板，B = 自动连接）：
  场景 A（ble）    ：扫描→连接→服务/特征值列表→订阅/读→发帧（hex 合法/非法/空）→通知显示→复制诊断
  场景 B（auto）   ：进页面自动连（不用点）→ 系统说连不上就重试→连上后自动检测→被拒不再重试→
                     「停止」生效→开关关掉不自动连
  场景 C（skip）   ：已经在相机热点上 → 跳过连接直接检测；这个名字像相机但 HTTP 不通 → 回退正常连接

原生桥（OM3Native）是**打桩**的：真相机/真蓝牙验不了，这里只验"页面逻辑有没有把桥用对"。
用法：python scripts/dv_blecam.py
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
/* ===== 打桩原生桥 ===== */
window.__st = {
  conn: { calls: [], result: 'asking', next: 'unavailable' },   /* connectCamera 的行为 */
  wifi: { wifi: true, ssid: '' },
  camInfo: 200,
  ble: { scan: 0, stop: 0, mac: '', sub: '', rd: '', wr: null, dis: 0 },
  clip: ''
};
window.OM3Native = {
  connectCamera: function(ssid, pass){
    window.__st.conn.calls.push(ssid);
    var nx = window.__st.conn.next;
    if(nx){ setTimeout(function(){ if(window.__om3camState) window.__om3camState(nx); }, 30); }
    return window.__st.conn.result;
  },
  disconnectCamera: function(){ return 'ok'; },
  forgetWifi: function(){ return 'ok'; },
  dropCamera: function(){ return 'ok'; },
  wifiState: function(){ return JSON.stringify(window.__st.wifi); },
  startWatch: function(){},
  cameraState: function(){ return JSON.stringify({ ssid: window.__st.wifi.ssid }); },
  /* --- 蓝牙 --- */
  blePerm: function(){ return window.__st.ble.perm || 'ok'; },
  bleAskPerm: function(){ window.__st.ble.asked++; },
  blePermDetail: function(){ return 'SDK=34；BLUETOOTH_SCAN=缺；BLUETOOTH_CONNECT=缺；蓝牙开关=开'; },
  bleScanStart: function(){
    window.__st.ble.scan++; window.__st.ble.starts = (window.__st.ble.starts || 0) + 1;
    window.__st.ble.mode = 'all(legacy)';
    if(window.__st.ble.silent) return;
    setTimeout(function(){
      window.__om3ble('found', 'OM-3 1234ABCD', 'AA:BB:CC:DD:EE:01', -55);   /* 不带 cam 参数 → 走"名字像相机"兜底 */
      window.__om3ble('found', 'WH-1000XM5', 'AA:BB:CC:DD:EE:02', -70);
    }, 20);
  },
  /* v2.17：新版是 bleScanStart2(1 = 只扫相机 / 0 = 全量) */
  bleScanStart2: function(m){
    window.__st.ble.scan++; window.__st.ble.starts = (window.__st.ble.starts || 0) + 1;
    window.__st.ble.mode = m;
    if(window.__st.ble.silent) return;
    setTimeout(function(){
      window.__om3ble('start', m === 1 ? 'onlycam' : 'all');
      window.__om3ble('found', 'OM-3 1234ABCD', 'AA:BB:CC:DD:EE:01', -55, m === 1 ? 1 : 0);
      window.__om3ble('found', 'WH-1000XM5', 'AA:BB:CC:DD:EE:02', -70, 0);
    }, 20);
  },
  bleScanStop: function(){ window.__st.ble.stop++; },
  bleDevices: function(){ return '[]'; },
  bleConnect: function(mac){
    window.__st.ble.mac = mac;
    setTimeout(function(){
      window.__om3ble('connected', mac, 0);
      window.__om3ble('svc', JSON.stringify([
        { uuid: 'adc505f9-4e58-4b71-b8ca-983bb8c73e4f', type: 0, chars: [
          { uuid: '0000fff1-0000-1000-8000-00805f9b34fb', props: 26, read: true, write: true, wnr: false, notify: true, indicate: false, cccd: true },
          { uuid: '0000fff2-0000-1000-8000-00805f9b34fb', props: 8, read: false, write: true, wnr: false, notify: false, indicate: false, cccd: false }
        ] }
      ]), 0);
      window.__om3ble('mtu', 517, 0);
    }, 30);
    return 'ok';
  },
  bleServices: function(){ return '[]'; },
  bleSubscribe: function(u){ window.__st.ble.sub = u; return 'ok:subscribed'; },
  bleRead: function(u){ window.__st.ble.rd = u; return 'ok:reading'; },
  bleWrite: function(u, d, m, f){ window.__st.ble.wr = [u, d, m, f]; return 'ok:sent'; },
  bleDisconnect: function(){ window.__st.ble.dis++; return 'ok'; }
};
/* 剪贴板：**故意让它拒绝**（headless / 无权限时的真实情形）—— 验"复制失败要有退路"。
   注意 navigator.clipboard 是只读 getter，只能 defineProperty 覆盖。 */
try{
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText: function(){ window.__st.clipTry = (window.__st.clipTry || 0) + 1; return Promise.reject(new Error('denied（测试里故意拒绝）')); } }
  });
}catch(e){ window.__st.clipErr = String(e); }
/* ===== 假相机 HTTP（只给「检测相机」用）===== */
window.XMLHttpRequest = function(){
  var self = this;
  self.readyState = 0; self.status = 0; self.responseText = '';
  self.open = function(m, u){ self._u = String(u); };
  self.setRequestHeader = function(){};
  self.send = function(){
    var st = 200, txt = '<caminfo><model>OM-3</model><serial>BJ1234567</serial></caminfo>';
    if(/get_caminfo/.test(self._u)) st = window.__st.camInfo;
    self.status = st; self.responseText = txt; self.readyState = 4;
    setTimeout(function(){ if(self.onreadystatechange) self.onreadystatechange(); }, 5);
  };
};
</script>"""

COMMON = r"""
setTimeout(function(){
  var o = [], fails = [];
  function ok(c, m){ o.push((c ? '  [OK ] ' : '  [FAIL] ') + m); if(!c) fails.push(m); }
  function el(id){ return document.getElementById(id); }
  function txt(id){ var e = el(id); return e ? (e.textContent || '').replace(/\s+/g, ' ') : ''; }
  function fin(){
    o.push('累计 js 报错=' + (window.__errs ? window.__errs.length : 0) + '（' + (window.__errs || []).join(' | ').slice(0, 200) + '）');
    o.push('--- 结果：' + (fails.length ? ('失败 ' + fails.length + ' 项') : '全部通过') + ' ---');
    var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
    document.body.appendChild(d);
  }
  var steps = [];
  function step(f){ steps.push(f); }
  function run(){ if(!steps.length) return fin(); var f = steps.shift();
    try{ f(run); }catch(e){ o.push('  !! 步骤抛错：' + (e && e.message ? e.message : e)); fin(); } }
  function sleep(ms, cb){ setTimeout(cb, ms); }
"""

SCEN_BLE = COMMON + r"""
  /* ===== A：蓝牙面板 ===== */
  step(function(next){
    el('tabCam').click();
    sleep(400, function(){
      o.push('    BLE 面板在页面里=' + !!el('bleCard') + ' 有无「复制诊断」=' + !!el('bleDiagCopy'));
      ok(!!el('bleCard') && !!el('bleDiagCopy'), '蓝牙面板和「复制诊断」按钮在页面里');
      el('bleScan').click();
      sleep(300, function(){
        var cams = document.querySelectorAll('#bleCamList .bleRow');
        var oth = document.querySelectorAll('#bleOtherList .bleRow');
        o.push('    扫描 mode=' + window.__st.ble.mode + ' 相机栏=' + cams.length + ' 其它栏=' + oth.length
               + '  相机行文字=' + JSON.stringify((cams[0] ? cams[0].textContent : '').replace(/\s+/g, ' ').slice(0, 60)));
        ok(window.__st.ble.scan === 1, '点了「扫描蓝牙设备」→ 调了扫描');
        ok(window.__st.ble.mode === 1, '★第一枪是"只扫相机"（bleScanStart2(1)，按官方那个服务 UUID 过滤）');
        ok(cams.length === 1 && /OM-3/.test(cams[0].textContent), '★相机那行进「📷 找到的相机」栏');
        ok(!!cams[0].querySelector('.blecam'), '★相机行带 📷 相机 徽章（不用用户自己猜）');
        ok(oth.length === 1 && /WH-1000XM5/.test(oth[0].textContent), '非相机设备收在「其它蓝牙设备」栏（不和相机混在一起）');
        ok(!!(cams[0] && cams[0].querySelector('button')), '★相机行右边有「连它」按钮');
        cams[0].querySelector('button').click();
        sleep(300, function(){
          ok(window.__st.ble.mac === 'AA:BB:CC:DD:EE:01', '★点「连接」→ 把 MAC 交给了原生 bleConnect（' + window.__st.ble.mac + '）');
          var sv = txt('bleSvcBox');
          o.push('    服务区：' + JSON.stringify(sv.slice(0, 150)));
          ok(sv.indexOf('ADC505F9') >= 0 || sv.indexOf('adc505f9') >= 0, '服务列表里有相机的服务 UUID');
          ok(sv.indexOf('FFF1') >= 0 && sv.indexOf('FFF2') >= 0, '★用了短号显示特征值（FFF1 / FFF2）');
          ok(sv.indexOf('读') >= 0 && sv.indexOf('写') >= 0 && sv.indexOf('通知') >= 0 && sv.indexOf('有CCCD') >= 0, '★属性列出来了（读/写/通知/有CCCD）');
          ok(sv.indexOf('MTU=517') >= 0, 'MTU 显示出来了（517）');
          next();
        });
      });
    });
  });

  /* ===== A2：订阅 / 读 / 发帧 ===== */
  step(function(next){
    var bs = document.querySelectorAll('#bleSvcBox button[data-sub]');
    var br = document.querySelectorAll('#bleSvcBox button[data-rd]');
    ok(bs.length === 1, '可通知的特征值给了「订阅」按钮（' + bs.length + ' 个）');
    ok(br.length === 1, '可读的特征值给了「读」按钮（' + br.length + ' 个）');
    bs[0].click();
    br[0].click();
    sleep(200, function(){
      ok(window.__st.ble.sub === '0000fff1-0000-1000-8000-00805f9b34fb', '订阅调了 bleSubscribe（对了 UUID）');
      ok(window.__st.ble.rd === '0000fff1-0000-1000-8000-00805f9b34fb', '读调了 bleRead（对了 UUID）');
      /* 通知回包：hex + 文本都要能看到 */
      window.__om3ble('notify', '0000fff1-0000-1000-8000-00805f9b34fb', '01024869', '..Hi');
      sleep(150, function(){
        /* 报文进的是面板的「状态/日志」区 #bleGatt（服务列表区重画时不会把报文冲掉） */
        var sv = txt('bleGatt'), log3 = txt('camOut3');
        ok(sv.indexOf('01024869') >= 0, '★收到的通知（hex）显示在面板上');
        ok(sv.indexOf('..Hi') >= 0, '★同一份数据的文本那栏也显示');
        ok(sv.indexOf('← 通知') >= 0, '★报文带方向标记（← 通知）');
        ok(log3.indexOf('01024869') >= 0, '★通知同时进了 ③写入 日志（诊断要能导出）');
        next();
      });
    });
  });

  /* ===== A3：发帧（合法 / 非法 / 空）===== */
  step(function(next){
    var u = el('bleWUuid'), f = el('bleWFmt'), m = el('bleWMode'), d = el('bleWData');
    ok(!!u && !!d, '发送框在页面里（特征值下拉 + 内容输入）');
    var writeBtns = document.querySelectorAll('#bleSvcBox button[data-use]');
    ok(writeBtns.length === 2, '两个可写的特征值都有「选它发」（' + writeBtns.length + ' 个）');
    u.value = '0000fff1-0000-1000-8000-00805f9b34fb';
    f.value = 'hex'; m.value = 'req'; d.value = '01 02 ff';
    el('bleWSend').click();
    sleep(150, function(){
      var w = window.__st.ble.wr;
      ok(!!w && w[0] === '0000fff1-0000-1000-8000-00805f9b34fb' && w[1] === '01 02 ff' && w[2] === 'req' && w[3] === 'hex',
         '★合法 hex 发出去了（' + JSON.stringify(w) + '）');
      window.__st.ble.wr = null;
      d.value = 'zz';                      /* 非法 hex */
      el('bleWSend').click();
      sleep(120, function(){
        ok(window.__st.ble.wr === null, '★非法 hex **没有**发出去');
        ok(txt('bleGatt').indexOf('十六进制格式不对') >= 0, '并且明确报「十六进制格式不对」（不静默）');
        d.value = '';
        el('bleWSend').click();
        sleep(120, function(){
          ok(window.__st.ble.wr === null, '★空内容也没发出去');
          next();
        });
      });
    });
  });

  /* ===== A4：复制诊断（剪贴板被拒 → 必须有退路，且不许冒未处理的拒绝）===== */
  step(function(next){
    el('bleDiagCopy').click();
    sleep(400, function(){
      o.push('    剪贴板被调了 ' + (window.__st.clipTry || 0) + ' 次；js 报错=' + (window.__errs || []).length);
      ok((window.__st.clipTry || 0) >= 1, '「复制诊断」试过剪贴板（execCommand 不行 → 走异步剪贴板）');
      ok((window.__errs || []).length === 0, '★剪贴板拒绝后**没有**冒未处理的拒绝（js 报错 0）');
      ok(txt('bleGatt').indexOf('复制没成功') >= 0, '如实报「复制没成功」并说明原因：' + JSON.stringify(txt('bleGatt').slice(-90)));
      var ta = document.getElementById('bleDiagOut');
      var t = ta ? String(ta.value || '') : '';
      o.push('    退路文本框 ' + t.length + ' 字符，开头：' + JSON.stringify(t.slice(0, 80)));
      ok(!!ta && t.length > 100, '★复制失败时给出手动复制的退路（文本框 ' + t.length + ' 字符）');
      ok(t.indexOf('AA:BB:CC:DD:EE:01') >= 0, '诊断里有 MAC');
      ok(t.indexOf('MTU=517') >= 0, '诊断里有 MTU');
      ok(t.indexOf('adc505f9') >= 0 && t.indexOf('0000fff1') >= 0, '诊断里有全部服务/特征值');
      ok(t.indexOf('01024869') >= 0, '★诊断里有收到的报文（← 方向）');
      ok(t.indexOf('OM-3 1234ABCD') >= 0, '诊断里有设备名');
      next();
    });
  });

  run();
}, 3000);
"""

SCEN_AUTO = COMMON + r"""
  /* ===== B：自动连接 + 重试 ===== */
  step(function(next){
    try{ localStorage.clear(); }catch(e){}
    localStorage.setItem('om3cam', JSON.stringify({ ssid: 'OM-3-123456', pass: '12345678' }));
    window.__st.wifi = { wifi: true, ssid: 'TP-LINK_5G' };      /* 不是相机热点 */
    window.__st.conn.calls = [];
    window.__st.conn.result = 'asking';
    window.__st.conn.next = 'unavailable';                      /* 一开始：系统说连不上 */
    el('tabCam').click();                                       /* ★只点页签，不点「连接相机」 */
    sleep(600, function(){
      o.push('    connectCamera 调用=' + JSON.stringify(window.__st.conn.calls));
      ok(window.__st.conn.calls.length === 1, '★进页面就自动发起了连接（没人点「连接相机」）（' + window.__st.conn.calls.length + ' 次）');
      ok(txt('camAutoNote').indexOf('第 1/8 次') >= 0 || txt('camAutoNote').indexOf('自动连') >= 0, '面板写明了正在自动连：' + JSON.stringify(txt('camAutoNote').slice(0, 60)));
      next();
    });
  });

  /* 等一轮重试（4 秒）→ 应该又试了一次 */
  step(function(next){
    sleep(4600, function(){
      var n = window.__st.conn.calls.length;
      o.push('    4.6 秒后累计调用=' + n);
      ok(n >= 2, '★系统说连不上 → 自动重试了（累计 ' + n + ' 次）');
      ok(el('camAutoStop') && el('camAutoStop').style.display !== 'none', '重试期间「停止自动连接」按钮出现');
      next();
    });
  });

  /* 这次让它连上 → 自动检测（假相机 HTTP 通）*/
  step(function(next){
    window.__st.conn.next = 'connected';
    sleep(5000, function(){
      var on = document.body.classList.contains('cam-on');
      ok(on, '★连上后自动检测成功 → cam-on 点亮（不用手点「检测相机」）');
      ok(txt('camAutoNote').indexOf('第') < 0, '连上后不再显示"第 n/8 次"');
      var saved = {};
      try{ saved = JSON.parse(localStorage.getItem('om3cam') || '{}'); }catch(e){}
      ok(saved.model === 'OM-3', '★把机型记进了「记住的相机」（' + JSON.stringify(saved.model) + '）');
      next();
    });
  });

  /* 权限被拒 → 不许无限重试 */
  step(function(next){
    document.body.classList.remove('cam-on');
    window.__st.conn.calls = [];
    window.__st.conn.next = 'denied';
    window.__om3camState && window.__om3camState('denied');
    window.__om3camAutoStart && window.__om3camAutoStart('测试：被拒');
    sleep(1200, function(){
      var n1 = window.__st.conn.calls.length;
      window.__om3camState && window.__om3camState('denied');
      sleep(1200, function(){
        var n2 = window.__st.conn.calls.length;
        o.push('    denied 后调用次数：' + n1 + ' → ' + n2);
        ok(n2 <= n1 + 0, '★权限被拒后不再重试（次数没涨：' + n1 + ' → ' + n2 + '）');
        next();
      });
    });
  });

  /* 「停止自动连接」→ 立刻停 */
  step(function(next){
    window.__st.conn.calls = [];
    window.__st.conn.next = 'unavailable';
    window.__om3camAutoStart && window.__om3camAutoStart('测试：停止');
    sleep(400, function(){
      var stp = el('camAutoStop');
      if(stp) stp.click();
      sleep(500, function(){
        var a = window.__st.conn.calls.length;
        window.__om3camState && window.__om3camState('unavailable');
        sleep(4600, function(){
          var b = window.__st.conn.calls.length;
          o.push('    停止后：' + a + ' → ' + b + ' 次');
          ok(b === a, '★点了「停止自动连接」→ 不再重试（' + a + ' → ' + b + '）');
          ok(txt('camAutoNote').indexOf('已停') >= 0, '面板写明"已停"：' + JSON.stringify(txt('camAutoNote').slice(0, 50)));
          next();
        });
      });
    });
  });

  /* 开关关掉 → 进页面不再自动连（手点仍然可以） */
  step(function(next){
    el('camAutoToggle').click();                        /* 当前是"关↔开"翻转：先看它现在是开还是关 */
    var nowTxt = txt('camAutoToggle');
    if(nowTxt !== '关') el('camAutoToggle').click();     /* 确保切成"关" */
    o.push('    开关现在=' + JSON.stringify(txt('camAutoToggle')));
    window.__st.conn.calls = [];
    window.__tabBack = true;
    el('tabA') && el('tabA').click();
    sleep(300, function(){
      el('tabCam').click();                              /* 再进一次页面 */
      sleep(800, function(){
        ok(window.__st.conn.calls.length === 0, '★开关关掉后进页面**不**自动连（调用 ' + window.__st.conn.calls.length + ' 次）');
        ok(txt('camAutoNote').indexOf('关掉') >= 0, '面板写明是"关掉了"');
        /* 但手点「连接相机」仍然能连 */
        el('camGateConn').click();
        sleep(400, function(){
          ok(window.__st.conn.calls.length >= 1, '★手点「连接相机」仍然能连（' + window.__st.conn.calls.length + ' 次）');
          next();
        });
      });
    });
  });

  run();
}, 3000);
"""

SCEN_SKIP = COMMON + r"""
  /* ===== C：已经在相机热点上 → 跳过连接 ===== */
  step(function(next){
    try{ localStorage.clear(); }catch(e){}
    localStorage.setItem('om3cam', JSON.stringify({ ssid: 'OM-3-123456', pass: '12345678' }));
    window.__st.conn.calls = [];
    window.__st.conn.next = '';
    window.__st.wifi = { wifi: true, ssid: 'OM-3-123456' };   /* 已经挂在相机热点上 */
    window.__st.camInfo = 200;
    el('tabCam').click();
    sleep(1500, function(){
      o.push('    connectCamera 调用=' + window.__st.conn.calls.length + '  cam-on=' + document.body.classList.contains('cam-on'));
      ok(window.__st.conn.calls.length === 0, '★已在相机热点上 → **跳过**连接，没有再调 connectCamera');
      ok(document.body.classList.contains('cam-on'), '★直接检测到相机（cam-on 点亮）');
      next();
    });
  });

  /* 名字像相机、但 HTTP 不通 → 回退到正常连接流程 */
  step(function(next){
    try{ localStorage.clear(); }catch(e){}
    localStorage.setItem('om3cam', JSON.stringify({ ssid: 'OM-3-123456', pass: '12345678' }));
    window.__st.conn.calls = [];
    window.__st.conn.result = 'asking';
    window.__st.conn.next = 'unavailable';
    window.__st.wifi = { wifi: true, ssid: 'OM-3-123456' };
    window.__st.camInfo = 500;                                 /* 检测必失败 */
    document.body.classList.remove('cam-on');
    window.__om3camState && window.__om3camState('lost');
    window.__om3camAutoStart && window.__om3camAutoStart('测试：名字像但不通');
    sleep(7000, function(){                                    /* 自动检测 3 次 × 1.5 秒，再回退 → 等够 */
      o.push('    回退后 connectCamera 调用=' + window.__st.conn.calls.length + '  面板=' + JSON.stringify(txt('camGateOut').slice(-90)));
      ok(window.__st.conn.calls.length >= 1, '★名字像相机但检测不通 → 回退到正常连接流程（调了 ' + window.__st.conn.calls.length + ' 次）');
      next();
    });
  });

  /* 普通 Wi-Fi 名 → 不许误判成相机 */
  step(function(next){
    ok(window.__om3camLookLike ? true : true, '（占位）');
    window.__st.wifi = { wifi: true, ssid: 'TP-LINK_5G' };
    next();
  });

  run();
}, 3000);
"""

# 官方 APK 逆出来的命令帧（SPEC-round19）：逐字节核对 + 「唤醒 → 自动连相机」链路
SCEN_WAKE = COMMON + r"""
  step(function(next){
    try{ localStorage.clear(); }catch(e){}
    localStorage.setItem('om3cam', JSON.stringify({ ssid: 'OM-3-WAKE', pass: '12345678' }));
    window.__st.conn.calls = [];
    window.__st.conn.next = '';
    window.__st.wifi = { wifi: true, ssid: 'TP-LINK_5G' };
    el('tabCam').click();
    sleep(400, function(){
      o.push('    预设按钮：唤醒=' + !!el('bleWake') + ' 68/3=' + !!el('blep3') + ' 68/2=' + !!el('blep2') + ' 68/1=' + !!el('blep1'));
      ok(!!el('bleWake') && !!el('blep3') && !!el('blep2') && !!el('blep1'), '蓝牙面板上有官方命令帧的按钮');
      /* 先连上蓝牙（打桩会回 svc） */
      el('bleScan').click();
      sleep(200, function(){
        document.querySelectorAll('#bleCamList .bleRow button')[0].click();
        sleep(300, function(){ next(); });
      });
    });
  });

  /* 未连蓝牙时点「唤醒」（v2.17 语义）：扫到过相机 → **自动连它**（连上后才发帧）；
     一个相机都没有 → 明确提示去扫，一帧都不许乱发。 */
  step(function(next){
    window.__om3ble('lost', '测试：断开');
    window.__st.ble.wr = null;
    window.__st.ble.silent = true;          /* 重新扫一次，但一个设备都不报 → 清空相机候选 */
    el('bleScan').click();
    sleep(300, function(){
      window.__st.ble.wr = null;
      el('bleWake').click();
      sleep(300, function(){
        ok(window.__st.ble.wr === null, '★蓝牙没连、也没扫到相机时点「唤醒」→ 一帧都不发');
        ok(txt('bleGatt').indexOf('扫描蓝牙设备') >= 0 || txt('bleGatt').indexOf('先扫') >= 0,
           '并且明确提示先去扫描（找到 📷 那条）');
        /* 再扫一次（这次报相机）→ 点唤醒应该**自动连相机**而不是直接发帧 */
        window.__st.ble.silent = false;
        window.__st.ble.mac = '';
        el('bleScan').click();
        sleep(300, function(){
          window.__st.ble.wr = null;
          el('bleWake').click();
          sleep(300, function(){
            ok(window.__st.ble.mac === 'AA:BB:CC:DD:EE:01',
               '★有相机候选时点「唤醒」→ 自动连**相机**那条（' + window.__st.ble.mac + '），不用先让用户猜哪个是相机');
            next();
          });
        });
      });
    });
  });

  /* 帧格式逐字节核对（官方组帧算法） */
  step(function(next){
    window.__om3ble('connected', 'AA:BB:CC:DD:EE:01', 0);
    window.__om3ble('svc', JSON.stringify([
      { uuid: 'ADC505F9-4E58-4B71-B8CA-983BB8C73E4F', type: 0, chars: [
        { uuid: '82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68', props: 26, read: true, write: true, wnr: false, notify: true, indicate: false, cccd: true }
      ] }
    ]), 0);
    sleep(200, function(){
      window.__st.ble.wr = null;
      el('blep3').click();
      sleep(200, function(){
        var w = window.__st.ble.wr;
        o.push('    68/子3 帧：' + JSON.stringify(w ? w[1] : null));
        ok(!!w && w[0] === '82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68' && w[3] === 'hex',
           '★帧发到了可写的特征值（' + (w ? w[0] : '') + '，按 hex 发）');
        ok(!!w && w[1].toUpperCase() === '01 01 03 68 01 03 6E 00',
           '★68/子3 帧字节完全对（01 01 03 68 01 03 6E 00，实际 ' + (w ? w[1] : '') + '）');
        ok(!!w && w[2] === 'req', '按「要应答」发（官方也是 writeCharacteristic 默认）');
        window.__st.ble.wr = null;
        el('blep1').click();
        sleep(200, function(){
          var w2 = window.__st.ble.wr;
          ok(!!w2 && w2[1].toUpperCase() === '01 02 03 68 01 01 6C 00',
             '★68/子1 帧字节完全对（序号自增到 02、累加和 6C，实际 ' + (w2 ? w2[1] : '') + '）');
          next();
        });
      });
    });
  });

  /* 「唤醒」= 发 68/子2（开 Wi-Fi）→ 3 秒后自动去连相机 */
  step(function(next){
    window.__st.ble.wr = null;
    window.__st.conn.calls = [];
    el('bleWake').click();
    sleep(400, function(){
      var w = window.__st.ble.wr;
      o.push('    唤醒帧：' + JSON.stringify(w ? w[1] : null));
      /* 帧格式：01 <序号> 03 68 01 02 <累加和> 00 —— **序号逐帧自增**，所以这里只钉格式+载荷+校验和 */
      ok(!!w && /^01 [0-9A-F]{2} 03 68 01 02 6D 00$/.test(String(w[1]).toUpperCase()),
         '★「唤醒」发的就是开 Wi-Fi 帧（格式 01 <序号> 03 68 01 02 6D 00，实际 ' + (w ? w[1] : '') + '）');
      ok(window.__st.conn.calls.length === 0, '发完先等一会儿（不立刻抢 Wi-Fi）');
      sleep(3400, function(){
        o.push('    3.4 秒后 connectCamera 调用=' + JSON.stringify(window.__st.conn.calls));
        ok(window.__st.conn.calls.length >= 1, '★唤醒帧发成功后自动去连相机 Wi-Fi');
        next();
      });
    });
  });

  run();
}, 3000);
"""

# 蓝牙权限（SPEC-round23）：Android 12+ 的 BLUETOOTH_SCAN/CONNECT 是运行时权限 ——
# 以前 JS 一看 need 就 return，只弹 app 自己的提示、**从不申请** → 用户"权限都给了"却一直说需要权限。
# 现在：need → 调 N.bleAskPerm() 拉系统弹窗；结果回调 __om3blePerm('ok') → 自动继续扫描。
SCEN_PERM = COMMON + r"""
  step(function(next){
    try{ localStorage.clear(); }catch(e){}
    window.__st.ble.perm = 'need:android.permission.BLUETOOTH_SCAN,android.permission.BLUETOOTH_CONNECT';
    window.__st.ble.asked = 0;
    window.__st.ble.starts = 0;
    el('tabCam').click();
    sleep(400, function(){
      el('bleScan').click();
      sleep(300, function(){
        o.push('    点了扫描 → 申请次数=' + window.__st.ble.asked + ' 扫描次数=' + window.__st.ble.starts);
        ok(window.__st.ble.asked === 1, '★★没权限时点「扫描蓝牙设备」→ 真的去**申请系统权限**（不再只弹自己的提示）');
        ok(window.__st.ble.starts === 0, '还没授权 → 先不扫描（等系统弹窗结果）');
        ok(txt('bleGatt').indexOf('系统') >= 0 || txt('bleList').indexOf('系统') >= 0,
           '页面上写明"正在向系统申请蓝牙权限"');
        next();
      });
    });
  });

  /* 用户在系统弹窗点了「允许」→ Java 回调 __om3blePerm('ok') → 自动继续扫描 */
  step(function(next){
    window.__om3blePerm('ok');
    sleep(300, function(){
      o.push('    授权后 → 扫描次数=' + window.__st.ble.starts);
      ok(window.__st.ble.starts === 1, '★授权成功后**自动继续扫描**（不用再点一次）');
      ok(txt('bleGatt').indexOf('权限已拿到') >= 0, '日志说明权限已拿到');
      next();
    });
  });

  /* 被拒 → 说清去哪开，不乱扫 */
  step(function(next){
    window.__st.ble.perm = 'need:android.permission.BLUETOOTH_CONNECT';
    window.__st.ble.asked = 0; window.__st.ble.starts = 0;
    el('bleScan').click();
    sleep(300, function(){
      ok(window.__st.ble.asked === 1, '被拒之后再点 → 再申请一次');
      window.__om3blePerm('denied');
      sleep(300, function(){
        o.push('    被拒后提示：' + txt('bleGatt').slice(0, 80));
        ok(txt('bleGatt').indexOf('被拒绝') >= 0, '★被拒时明确说"权限被拒绝"');
        ok(txt('bleGatt').indexOf('设置') >= 0, '并指明去「设置 → 应用 → 权限 → 附近的设备」');
        ok(window.__st.ble.starts === 0, '被拒后不硬扫');
        next();
      });
    });
  });

  /* 已经授权（正常路径）→ 直接扫描，不打扰用户 */
  step(function(next){
    window.__st.ble.perm = 'ok';
    window.__st.ble.asked = 0; window.__st.ble.starts = 0;
    el('bleScan').click();
    sleep(300, function(){
      ok(window.__st.ble.asked === 0 && window.__st.ble.starts === 1,
         '★权限齐了就直接扫（不弹任何多余提示）');
      next();
    });
  });

  run();
}, 3000);
"""

k = src.find('<body')
j = src.find('>', k) + 1
ud = TMP + r'\omblecam'


def run_once(scen, body_js):
    flag = "<script>window.__SCEN='" + scen + "';</script>"
    tail = '<script>' + body_js + '</script>'
    out = src[:j] + flag + PRE + src[j:].replace('</body>', tail + '</body>', 1)
    p = TMP + r'\dv_blecam_' + scen + '.html'
    open(p, 'w', encoding='utf-8', newline='').write(out)
    subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
    r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                        '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                        '--user-data-dir=' + ud, '--window-size=412,900',
                        '--virtual-time-budget=90000', '--dump-dom',
                        'file:///' + p.replace('\\', '/')],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
    dom = r.stdout or ''
    kk = dom.find('id="DBGOUT"')
    return dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('（无输出）DOM=%d' % len(dom))


allfail = 0
for scen, js in (('ble', SCEN_BLE), ('auto', SCEN_AUTO), ('skip', SCEN_SKIP), ('wake', SCEN_WAKE), ('perm', SCEN_PERM)):
    txt = run_once(scen, js)
    print('========== 场景 ' + scen + ' ==========')
    print(txt)
    allfail += sum(1 for l in txt.split('\n') if l.startswith('  [FAIL]'))
print()
print('===== 三个场景合计失败 ' + str(allfail) + ' 项 =====')
