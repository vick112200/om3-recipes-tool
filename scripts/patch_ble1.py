# -*- coding: utf-8 -*-
"""BLE 实验第一步：扫描（Java 桥 + 权限 + 页面卡片 + 调试日志）"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
J = TMP + r'\apk\java\com\om3\handbook\MainActivity.java'
M = TMP + r'\apk\AndroidManifest.xml'
P = TMP + r'\app\base.html'

# ---------- Java ----------
j = open(J, encoding='utf-8').read()
if 'bleScanStart' not in j:
    anchor = "    public class Bridge {"
    assert j.count(anchor) == 1
    ADD = anchor + '''

        /* ===== 蓝牙（实验）：扫描相机广播的 BLE 设备 ===== */
        private final java.util.Map<String, String> sBle = new java.util.concurrent.ConcurrentHashMap<String, String>();
        private android.bluetooth.le.ScanCallback sBleCb = null;

        @android.webkit.JavascriptInterface
        public String blePerm() {
            try {
                if (android.os.Build.VERSION.SDK_INT >= 31) {
                    boolean a = checkSelfPermission("android.permission.BLUETOOTH_SCAN") == android.content.pm.PackageManager.PERMISSION_GRANTED;
                    boolean b = checkSelfPermission("android.permission.BLUETOOTH_CONNECT") == android.content.pm.PackageManager.PERMISSION_GRANTED;
                    if (!a || !b) return "need:android.permission.BLUETOOTH_SCAN,android.permission.BLUETOOTH_CONNECT";
                }
                return "ok";
            } catch (Throwable t) { return "err:" + t.getMessage(); }
        }

        @android.webkit.JavascriptInterface
        public void bleScanStart() {
            try {
                sBle.clear();
                final android.bluetooth.BluetoothAdapter ad = android.bluetooth.BluetoothAdapter.getDefaultAdapter();
                if (ad == null) { jsCall("window.__om3ble&&window.__om3ble('err','这台设备没有蓝牙')"); return; }
                if (!ad.isEnabled()) { jsCall("window.__om3ble&&window.__om3ble('err','蓝牙没打开')"); return; }
                android.bluetooth.le.BluetoothLeScanner sc = ad.getBluetoothLeScanner();
                if (sc == null) { jsCall("window.__om3ble&&window.__om3ble('err','拿不到扫描器')"); return; }
                android.bluetooth.le.ScanCallback cb = new android.bluetooth.le.ScanCallback() {
                    @Override public void onScanResult(int type, android.bluetooth.le.ScanResult r) {
                        try {
                            String mac = r.getDevice().getAddress();
                            String nm = r.getDevice().getName();
                            if (nm == null) nm = "";
                            int rssi = r.getRssi();
                            sBle.put(mac, nm + "#" + rssi);
                            jsCall("window.__om3ble&&window.__om3ble('found'," + jsonStr(nm) + "," + jsonStr(mac) + "," + rssi + ")");
                        } catch (Throwable t) { }
                    }
                };
                sc.startScan(cb);
                sBleCb = cb;
                jsCall("window.__om3ble&&window.__om3ble('start','')");
            } catch (Throwable t) {
                jsCall("window.__om3ble&&window.__om3ble('err'," + jsonStr("扫描失败：" + t.getMessage()) + ")");
            }
        }

        @android.webkit.JavascriptInterface
        public void bleScanStop() {
            try {
                android.bluetooth.BluetoothAdapter ad = android.bluetooth.BluetoothAdapter.getDefaultAdapter();
                if (ad != null && ad.getBluetoothLeScanner() != null && sBleCb != null) ad.getBluetoothLeScanner().stopScan(sBleCb);
            } catch (Throwable t) { }
            sBleCb = null;
        }

        @android.webkit.JavascriptInterface
        public String bleDevices() {
            StringBuilder sb = new StringBuilder("[");
            boolean first = true;
            for (java.util.Map.Entry<String, String> e : sBle.entrySet()) {
                String v = e.getValue();
                int i = v.indexOf('#');
                String nm = (i > 0) ? v.substring(0, i) : v;
                String rs = (i > 0) ? v.substring(i + 1) : "0";
                if (!first) sb.append(",");
                first = false;
                sb.append("{\\"mac\\":").append(jsonStr(e.getKey())).append(",\\"name\\":").append(jsonStr(nm)).append(",\\"rssi\\":").append(rs).append("}");
            }
            return sb.append("]").toString();
        }
'''
    j = j.replace(anchor, ADD, 1)
    open(J, 'w', encoding='utf-8', newline='').write(j)
    print('Java: BLE 扫描已加')
else:
    print('Java: 已有，跳过')

# ---------- Manifest ----------
m = open(M, encoding='utf-8').read()
if 'BLUETOOTH_SCAN' not in m:
    a2 = '<uses-permission android:name="android.permission.CAMERA"/>'
    if a2 not in m:
        a2 = '<uses-permission android:name="android.permission.CAMERA" />'
    assert a2 in m, 'CAMERA 行没找到'
    m = m.replace(a2, a2 + '\n    <uses-permission android:name="android.permission.BLUETOOTH" android:maxSdkVersion="30" />\n    <uses-permission android:name="android.permission.BLUETOOTH_ADMIN" android:maxSdkVersion="30" />\n    <uses-permission android:name="android.permission.BLUETOOTH_SCAN" android:usesPermissionFlags="neverForLocation" />\n    <uses-permission android:name="android.permission.BLUETOOTH_CONNECT" />', 1)
    open(M, 'w', encoding='utf-8', newline='').write(m)
    print('Manifest: 蓝牙权限已加')
else:
    print('Manifest: 已有，跳过')

# ---------- 页面 ----------
h = open(P, encoding='utf-8').read()
n0 = len(h)
a4 = '<!-- ============ 我的配方 ============ -->'
assert h.count(a4) == 1
CARD = '''<!-- 蓝牙（实验） -->
<div class="mpcard" id="bleCard" style="margin:10px 0">
  <h3>蓝牙（实验 · 慢慢调）</h3>
  <div style="font-size:12.5px;color:#9aa3b2">目标：像官方那样"蓝牙唤醒相机 / 自动开 Wi-Fi / 进传输态"。第一步先能扫到相机的蓝牙广播。</div>
  <div class="mprow">
    <button type="button" id="bleScan" class="mpbtn primary">扫描蓝牙设备</button>
    <button type="button" id="bleStop" class="mpbtn">停止扫描</button>
  </div>
  <div id="bleList" class="camout" style="margin-top:8px">点「扫描蓝牙设备」（相机需通电；OM-3 的蓝牙名通常带 OM-3）。扫 10 秒自动停。</div>
</div>
'''
h = h.replace(a4, CARD + a4, 1)

a5 = "  /* ===== 自绘弹窗"
assert h.count(a5) == 1
BLE = '''  /* ===== 蓝牙（实验）：扫描 + 调试日志 ===== */
  window.__om3ble = function(ev, a, b, c){
    var o = document.getElementById('bleList');
    try{
      if(ev === 'start'){ log('[BLE] 开始扫描…'); if(o) line(o, '开始扫描…'); }
      else if(ev === 'found'){ log('[BLE] 发现：' + a + '　' + b + '　RSSI ' + c);
        if(o) line(o, (a || '（无名）') + '　' + b + '　RSSI ' + c, /OM-3|OM3|OM-1|OM-5|OI/i.test(a || '') ? 'ok' : ''); }
      else if(ev === 'err'){ log('[BLE] 错误：' + a, 'err'); if(o) line(o, '错误：' + a, 'err'); }
    }catch(e){}
  };
  function bleStart(){
    var o = document.getElementById('bleList'); if(o) o.innerHTML = '';
    var N = window.OM3Native;
    if(!N || !N.bleScanStart){ log('[BLE] 这个版本没有蓝牙接口', 'err'); return; }
    var pr = ''; try{ pr = String(N.blePerm()); }catch(e){}
    if(pr.indexOf('need:') === 0){
      log('[BLE] 需要权限：' + pr.slice(5), 'warn');
      log('[BLE] 请到「设置 → 应用 → 权限 → 附近的设备/蓝牙」里允许后，再点一次扫描', 'warn');
      toastMsg('请先给蓝牙权限');
      return;
    }
    try{ N.bleScanStart(); }catch(e){ log('[BLE] 启动失败：' + e.message, 'err'); }
    setTimeout(function(){ try{ if(N && N.bleDevices) log('[BLE] 列表：' + String(N.bleDevices()).slice(0, 500)); }catch(e){} }, 4000);
    setTimeout(function(){ try{ N.bleScanStop(); log('[BLE] 扫描已停'); if(o) line(o, '—— 扫描结束 ——'); }catch(e){} }, 10000);
  }
  (function(){
    var b1 = document.getElementById('bleScan'), b2 = document.getElementById('bleStop');
    if(b1) b1.addEventListener('click', bleStart);
    if(b2) b2.addEventListener('click', function(){ try{ window.OM3Native.bleScanStop(); log('[BLE] 已停止扫描'); }catch(e){} });
  })();

''' + a5
h = h.replace(a5, BLE, 1)
open(P, 'w', encoding='utf-8', newline='').write(h)
print('页面：蓝牙实验卡 + 逻辑（+%d 字节）' % (len(h) - n0))
