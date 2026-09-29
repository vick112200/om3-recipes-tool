# -*- coding: utf-8 -*-
"""页面侧：扫码入口重写（失败必须看得见 + 授权后自动开扫）。Java 侧已由 patch_scanfix.py 应用。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()

OLD = """  document.getElementById('camScan').addEventListener('click', function(){
    var out = document.getElementById('scanOut');
    out.innerHTML = '';
    if(!window.jsQR){ line(out, '扫码组件没加载成功（页面可能被改过）。用「手动填」也一样能连。', 'err'); return; }
    if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){
      line(out, '这个环境不给用摄像头（桌面版页面）。手机上用本 app 才能扫。', 'err'); return;
    }
    if(Native && Native.ensureCamera){
      var pr = '';
      try{ pr = String(Native.ensureCamera()); }catch(e){}
      if(pr.indexOf('need_perm') === 0){
        line(out, '请在弹出的对话框里允许「相机」权限，然后再点一次「扫二维码」。', 'warn');
        return;
      }
    }
    document.getElementById('scanMask').classList.remove('hide');
    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},
        width:{ideal:1280}, height:{ideal:720}}, audio:false})"""
assert h.count(OLD) == 1

NEW = """  /* 扫码入口：任何失败都必须"看得见"（页面提示 + 弹条 + 日志），
     否则提示写在还没打开的浮层里 = 用户以为"点了没反应" */
  var pendingScan = false;
  function scanSay(msg, cls){
    var out = document.getElementById('scanOut');
    if(out) line(out, msg, cls || 'err');
    camOut(msg, cls || 'err');
    log('扫码：' + msg, cls || 'err');
    if(cls !== 'ok') toastMsg(msg);
  }
  document.getElementById('camScan').addEventListener('click', function(){ startScanNow(); });
  function startScanNow(){
    pendingScan = false;
    if(!window.jsQR){ scanSay('扫码组件没加载成功 —— 用「手动填」一样能连。'); showManual('扫码组件没起来，直接手动填：'); return; }
    if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){
      scanSay('这个环境不给用摄像头（桌面版页面）。');
      showManual('这个环境不给用摄像头，手动填也行：');
      return;
    }
    if(Native && Native.ensureCamera){
      var pr = '';
      try{ pr = String(Native.ensureCamera()); }catch(e){}
      if(pr.indexOf('need_perm') === 0){
        pendingScan = true;
        camOut('请在系统弹窗里允许「相机」权限 —— 允许之后会**自动开始扫码**，不用再点。', 'warn');
        log('扫码：等待相机权限', 'warn');
        toastMsg('点弹窗里的「允许」，然后会自动开始扫码');
        return;
      }
    }
    var o0 = document.getElementById('scanOut');
    if(o0){ o0.innerHTML = ''; line(o0, '摄像头启动中…'); }
    log('扫码：正在打开摄像头');
    document.getElementById('scanMask').classList.remove('hide');
    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},
        width:{ideal:1280}, height:{ideal:720}}, audio:false})"""
h = h.replace(OLD, NEW, 1)

# 权限回调（相机）
anchor = "  function startScanNow(){"
assert h.count(anchor) == 1
h = h.replace(anchor, """  window.__om3camGranted = function(state){
    if(state === 'denied'){
      camOut('相机权限被拒绝了：设置 → 应用 → 权限 → 相机，允许后再点「扫二维码」。', 'warn');
      toastMsg('相机权限被拒绝');
      log('扫码：相机权限被拒绝', 'err');
      return;
    }
    if(pendingScan){ toastMsg('权限已给，开始扫码'); startScanNow(); }
  };
  window.__om3startScan = startScanNow;

""" + anchor, 1)

# 看门狗也走可见提示
old_wd = """            var so = document.getElementById('scanOut');
            so.innerHTML = '';
            line(so, '摄像头 3 秒内没有画面：这个 WebView 不给摄像头权限，或者被系统拦了。', 'err');
            line(so, '先把相机权限给到「本 app」（设置 → 应用 → 权限 → 相机）再点一次；还是不行就走「看不到二维码？手动填」——相机屏幕上的 SSID 和密码照着抄，一样能连。', 'warn');
            stopScan();"""
assert h.count(old_wd) == 1
h = h.replace(old_wd, """            stopScan();
            scanSay('摄像头没起来（3 秒没有画面）—— 也可以走「手动填」。');
            showManual('摄像头没起来：照相机屏幕把 SSID / 密码填到下面两格，一样能连。');""", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('页面：扫码入口重写完成，base.html %.1f KB' % (len(h.encode('utf-8')) / 1024))
