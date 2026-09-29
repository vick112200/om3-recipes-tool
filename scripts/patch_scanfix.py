# -*- coding: utf-8 -*-
"""扫码按钮"没反应"的根因修复：
原来所有失败分支（没有 jsQR / 没有摄像头 / 缺相机权限）都把提示写进 #scanOut ——
那个元素在**还没打开的浮层里**，所以用户什么都看不到 = "点了没反应"。
现在：所有失败都在页面上显示 + 弹提示 + 写日志；缺权限时授权后自动开始扫码。
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'

# ---------------- Java：相机权限授权回调 ----------------
p = TMP + r'\apk\java\com\om3\handbook\MainActivity.java'
j = open(p, encoding='utf-8').read()
old = """        if (code != 4713) return;"""
assert j.count(old) == 1
j = j.replace(old, """        if (code == 4712) {
            boolean cam = res.length > 0 && res[0] == PackageManager.PERMISSION_GRANTED;
            jscall(cam ? "window.__om3camGranted&&window.__om3camGranted('ok')"
                       : "window.__om3camGranted&&window.__om3camGranted('denied')");
            return;
        }
        if (code != 4713) return;""", 1)
open(p, 'w', encoding='utf-8', newline='').write(j)
print('Java: 相机权限回调 → 通知页面')

# ---------------- 页面：扫码入口重写 ----------------
P = TMP + r'\app\base.html'
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
NEW = """  /* 扫码入口：所有失败都要"看得见"（写页面 + 弹提示 + 记日志），否则用户只看到"没反应" */
  var pendingScan = false;
  function scanSay(msg, cls){
    var out = document.getElementById('scanOut');
    if(out) line(out, msg, cls || 'err');
    camOut(msg, cls || 'err');
    log('扫码：' + msg, cls || 'err');
    if(cls !== 'ok') toastMsg(msg);
  }
  function startScanNow(){
    pendingScan = false;
    if(!window.jsQR){ scanSay('扫码组件没加载成功（用「手动填」一样能连）。'); showManual('扫码组件没起来，直接手动填：'); return; }
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
        toastMsg('请点弹窗里的「允许」，然后会自动开始扫码');
        return;
      }
    }
    var out0 = document.getElementById('scanOut');
    if(out0){ out0.innerHTML = ''; line(out0, '摄像头启动中…'); }
    log('扫码：正在打开摄像头');
    document.getElementById('scanMask').classList.remove('hide');
    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},
        width:{ideal:1280}, height:{ideal:720}}, audio:false})"""
h = h.replace(OLD, NEW, 1)

# 点击入口 + 权限回调
OLD2 = """  document.getElementById('camScan').addEventListener('click', function(){"""
assert h.count(OLD2) == 1
# 上面的替换已经把这一行换成 startScanNow 定义，这里补一个入口绑定
h = h.replace("""  var pendingScan = false;""",
              """  var pendingScan = false;
  window.__om3camGranted = function(state){
    if(state === 'denied'){
      camOut('相机权限被拒绝了：设置 → 应用 → 权限 → 相机，允许后再点「扫二维码」。', 'warn');
      toastMsg('相机权限被拒绝');
      log('扫码：相机权限被拒绝', 'err');
      return;
    }
    if(pendingScan){ toastMsg('权限已给，开始扫码'); startScanNow(); }
  };""", 1)
h = h.replace("""  function startScanNow(){
    pendingScan = false;""",
              """  function bindScanBtn(){ }
  function startScanNow(){
    pendingScan = false;""", 1)
open(P, 'w', encoding='utf-8', newline='').write(h)
print('页面：扫码入口重写完成')
