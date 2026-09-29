# -*- coding: utf-8 -*-
"""蓝牙"哪个是相机"实测（无头 Chrome + 打桩原生桥）—— v2.17 / SPEC-round30。

用户 2026-09-24：*"你要先连接蓝牙才唤醒相机，但是蓝牙设备根本看不出哪个是相机的，官方app好像不是这样的"*。
官方做法（反汇编 `com.omdigitalsolutions.oishare` 的混淆类 `N2/c` 确认）：
    new ScanFilter.Builder().setServiceUuid(ParcelUuid.fromString("ADC505F9-4E58-4B71-B8CA-983BB8C73E4F"))
    scanner.startScan(filters, settings, callback)      ← 带过滤器，列表里不会出现耳机/手表
    （同一服务的写特征值：82F949B4-… / B7A8015C-…；通知：05A02050-…）

本脚本验的就是"页面有没有照这个来"：
  S1 两段式：先 bleScanStart2(1) 只扫相机 → 6 秒没相机 → 自动 bleScanStart2(0) 全量扫
  S2 只扫相机直接命中 → **不再**多扫一遍全量
  S3 相机/其它分两栏 + 📷 徽章 + 「连它」；名字像相机的也能认出来
  S4 发命令优先用**官方那两个**写特征值（以前是"随便挑第一个可写的"）
  S5 没连蓝牙点「唤醒」→ 自动连扫到的相机，连上后自动发唤醒帧（不再让用户去列表里猜）

用法：python scripts/dv_blescan.py
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

/* ===== 打桩原生桥（真相机/真蓝牙验不了；这里只验"页面把桥用对了没有"）===== */
window.__st = {
  scan: [],            /* bleScanStart2 的调用序列（1=只扫相机 / 0=全量） */
  stop: 0,
  silent: false,
  mode1Devices: [],    /* "只扫相机"时上报的设备 */
  allDevices: [],      /* 全量扫描时上报的设备 */
  conn: [],            /* bleConnect 的调用（mac） */
  write: [],           /* bleWrite 的调用（uuid/hex） */
  svc: null,           /* 连接后上报的服务列表 */
  connected: false
};
window.OM3Native = {
  blePerm: function(){ return 'ok'; },
  bleAskPerm: function(){},
  blePermDetail: function(){ return 'SDK=34；都有'; },
  bleScanStart2: function(m){
    window.__st.scan.push(m);
    window.__om3ble('start', m === 1 ? 'onlycam' : 'all');
    if(window.__st.silent) return;
    var list = (m === 1) ? window.__st.mode1Devices : window.__st.allDevices;
    setTimeout(function(){
      for(var i = 0; i < list.length; i++){
        var d = list[i];
        window.__om3ble('found', d.name, d.mac, d.rssi, d.cam ? 1 : 0);
      }
    }, 30);
  },
  bleScanStart: function(){ window.__st.scan.push('legacy'); },
  bleScanStop: function(){ window.__st.stop++; },
  bleDevices: function(){ return '[]'; },
  bleConnect: function(mac){
    window.__st.conn.push(mac);
    var svc = window.__st.svc;
    setTimeout(function(){
      window.__om3ble('connected', mac, 0);
      window.__om3ble('svc', JSON.stringify(svc), 0);
    }, 40);
    return 'ok';
  },
  bleDisconnect: function(){ window.__st.connected = false; return 'ok'; },
  bleWrite: function(uuid, hex, mode, fmt){ window.__st.write.push({ uuid: uuid, hex: hex }); return 'ok'; },
  bleSubscribe: function(){ return 'ok'; },
  bleRead: function(){ return 'ok'; },
  bleMtu: function(){ return '517'; }
};
</script>"""

JS = r"""
var o = [], fails = [];
function ok(c, m){ o.push((c ? '  [OK ] ' : '  [FAIL] ') + m); if(!c) fails.push(m); }
function el(i){ return document.getElementById(i); }
function txt(i){ var e = el(i); return e ? String(e.textContent || '') : ''; }
function sleep(ms, fn){ setTimeout(fn, ms); }
function dump(){
  o.push('累计 js 报错=' + window.__errs.length + (window.__errs.length ? (' ' + window.__errs.slice(0, 3).join(' | ')) : '') + ' 失败项=' + fails.length);
  var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join(String.fromCharCode(10));
  document.body.appendChild(d);
}
var CAM = { name: 'OM-3-BJSA21721', mac: 'AA:BB:CC:11:22:33', rssi: -48, cam: true };
var BUD = { name: 'WH-1000XM5',     mac: 'AA:BB:CC:44:55:66', rssi: -72, cam: false };
var WATCH = { name: 'Mi Band 8',    mac: 'AA:BB:CC:77:88:99', rssi: -80, cam: false };
/* 官方服务 + 服务下三个特征值（顺序故意把**非官方**的可写特征值排在最前面） */
var OFFICIAL_SVC = [
  { uuid: 'adc505f9-4e58-4b71-b8ca-983bb8c73e4f', type: 0, chars: [
      { uuid: '0000fff1-0000-1000-8000-00805f9b34fb', props: 26, read: true, write: true, wnr: false, notify: true, indicate: false, cccd: true },
      { uuid: '82f949b4-f5dc-4cf3-ab3c-fd9fd4017b68', props: 26, read: true, write: true, wnr: true,  notify: true, indicate: false, cccd: true },
      { uuid: 'b7a8015c-cb94-4efa-bda2-b7921fa9951f', props: 12, read: false, write: true, wnr: true, notify: false, indicate: false, cccd: false },
      { uuid: '05a02050-0860-4919-8add-9801fba8b6ed', props: 16, read: false, write: false, wnr: false, notify: true, indicate: false, cccd: true }
  ] }
];

setTimeout(function(){
try{
  el('tabCam').click();
  sleep(500, function(){
    /* ---------- S1：两段式（只扫相机没结果 → 自动全量） ---------- */
    window.__st.scan = []; window.__st.mode1Devices = []; window.__st.allDevices = [CAM, BUD, WATCH];
    el('bleScan').click();
    sleep(800, function(){
      o.push('    S1 扫描序列=' + JSON.stringify(window.__st.scan));
      ok(window.__st.scan.length === 1 && window.__st.scan[0] === 1,
         '★S1 第一枪就是"只扫相机"（bleScanStart2(1)，按官方服务 UUID 过滤）');
      ok(document.querySelectorAll('#bleCamList .bleRow').length === 0, 'S1 只扫相机没结果时，相机栏是空的');
    });
    sleep(7500, function(){
      o.push('    S1(6 秒后) 扫描序列=' + JSON.stringify(window.__st.scan));
      ok(window.__st.scan.length === 2 && window.__st.scan[1] === 0,
         '★S1 6 秒没扫到相机 → 自动改成全量扫（bleScanStart2(0)），不会白扫一场');
      ok(txt('bleList').indexOf('全量') >= 0, 'S1 日志说明了"改成全量扫描"');
      var cams = document.querySelectorAll('#bleCamList .bleRow');
      var oth = document.querySelectorAll('#bleOtherList .bleRow');
      o.push('    S1 相机栏=' + cams.length + ' 其它栏=' + oth.length
             + ' 相机行=' + JSON.stringify(cams[0] ? cams[0].textContent.replace(/\s+/g, ' ').slice(0, 50) : ''));
      ok(cams.length === 1 && /OM-3-BJSA21721/.test(cams[0].textContent), '★S1 相机进「📷 找到的相机」栏');
      ok(!!cams[0].querySelector('.blecam'), '★S1 相机行带 📷 相机 徽章');
      ok(cams[0].querySelector('button').textContent.indexOf('连它') >= 0, '★S1 相机行按钮是「连它」（其它行是普通「连接」）');
      ok(oth.length === 2, '★S1 另外两个（耳机/手环）收在「其它蓝牙设备」栏，不和相机混在一起');

      /* ---------- S4：发命令优先官方写特征值 ---------- */
      window.__st.svc = OFFICIAL_SVC; window.__st.write = []; window.__st.conn = [];
      cams[0].querySelector('button').click();
      sleep(500, function(){
        var sv = txt('bleSvcBox');
        ok(sv.indexOf('ADC505F9') >= 0 || sv.indexOf('adc505f9') >= 0, 'S4 连上后列出了相机的服务');
        el('blep2').click();                       /* 68/子2 = 开 Wi-Fi */
        sleep(300, function(){
          var w = window.__st.write[0];
          o.push('    S4 写入=' + JSON.stringify(w));
          ok(!!w, 'S4 点了发帧 → 真的写了');
          ok(!!w && String(w.uuid).toLowerCase() === '82f949b4-f5dc-4cf3-ab3c-fd9fd4017b68',
             '★★S4 发到**官方的写特征值** 82F949B4（服务里第一个可写的是 0000FFF1，不能随便挑它）（实际 '
             + (w ? w.uuid : '') + '）');
          ok(!!w && /^01 [0-9A-F]{2} 03 68 01 02 6D 00$/.test(String(w.hex).toUpperCase()),
             'S4 发的是开 Wi-Fi 帧（格式 01 <序号> 03 68 01 02 6D 00）');

          /* ---------- S2：只扫相机**直接命中** → 不该再多扫一遍全量 ---------- */
          window.__st.scan = []; window.__st.allDevices = [CAM, BUD];
          window.__st.mode1Devices = [CAM];
          el('bleScan').click();
          sleep(7500, function(){
            o.push('    S2 扫描序列=' + JSON.stringify(window.__st.scan));
            ok(window.__st.scan.length === 1 && window.__st.scan[0] === 1,
               '★S2 只扫相机就命中 → **不再**多扫一遍全量（省一次 10 秒）');
            ok(document.querySelectorAll('#bleCamList .bleRow').length === 1, 'S2 相机栏里有那台相机');
            ok(txt('bleList').indexOf('不用全量扫') >= 0, 'S2 日志里说明了"不用全量扫了"');

          /* ---------- S3：名字兜底（原生说 cam=0，但名字像相机） ---------- */
          window.__st.scan = []; window.__st.mode1Devices = [];
          window.__st.allDevices = [ { name: 'OM-5-MARK3', mac: 'AA:BB:CC:AA:BB:CC', rssi: -60, cam: false },
                                     { name: 'Galaxy Buds3', mac: 'AA:BB:CC:DD:EE:FF', rssi: -66, cam: false } ];
          el('bleScan').click();
          sleep(7500, function(){
            var c2 = document.querySelectorAll('#bleCamList .bleRow');
            var o2 = document.querySelectorAll('#bleOtherList .bleRow');
            ok(c2.length === 1 && /OM-5-MARK3/.test(c2[0].textContent), '★S3 原生没标 cam，但名字像相机 → 也进相机栏（名字兜底）');
            ok(o2.length === 1 && /Galaxy Buds3/.test(o2[0].textContent), 'S3 真不是相机的还是留在其它栏');

            /* ---------- S5：没连蓝牙点「唤醒」→ 自动连相机 + 连上后自动发帧 ---------- */
            window.__om3ble('lost', '测试：断开');
            window.__st.write = []; window.__st.conn = []; window.__st.svc = OFFICIAL_SVC;
            el('bleWake').click();
            sleep(300, function(){
              o.push('    S5 连接调用=' + JSON.stringify(window.__st.conn) + ' 写入数=' + window.__st.write.length);
              ok(window.__st.write.length === 0, 'S5 还没连上 → 一帧都没发（不瞎发）');
              ok(window.__st.conn.length === 1 && window.__st.conn[0] === 'AA:BB:CC:AA:BB:CC',
                 '★★S5 自动连的是**相机**那条（OM-5-MARK3），不是用户从列表里猜的（' + JSON.stringify(window.__st.conn) + '）');
            });
            sleep(1600, function(){
              var w2 = window.__st.write[0];
              o.push('    S5 连上后自动发的帧=' + JSON.stringify(w2));
              ok(!!w2 && String(w2.uuid).toLowerCase() === '82f949b4-f5dc-4cf3-ab3c-fd9fd4017b68'
                 && /^01 [0-9A-F]{2} 03 68 01 02 6D 00$/.test(String(w2.hex).toUpperCase()),
                 '★S5 连上（服务发现完）后自动补发唤醒帧，且发到官方写特征值');
              dump();
            });
          });
          });   /* 关 S2 那一层 sleep */
        });
      });
    });
  });
}catch(e){ o.push('探针异常：' + (e && e.message ? e.message : e)); dump(); }
}, 3000);
"""

tail = '<script>window.__errs=[];'
tail += "</script><script>" + PRE.replace('<script>', '').replace('</script>', '') + "</script>"
tail += '<script>' + JS + '</script>'

i = src.find('<body')
j = src.find('>', i) + 1
out = src[:j] + tail + src[j:].replace('</body>', '</body>', 1)
p = TMP + r'\dv_blescan.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\oblescan'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=90000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=600)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
if kk > 0:
    print(dom[kk:].split('>', 1)[1].split('</pre>')[0])
else:
    open(TMP + r'\blescan_dump.html', 'w', encoding='utf-8', newline='').write(dom)
    print('无输出 DOM=%d  DBGOUT在全文? %s' % (len(dom), 'DBGOUT' in dom))
    print('dump → ' + TMP + r'\blescan_dump.html')
