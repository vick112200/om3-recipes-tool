# -*- coding: utf-8 -*-
"""补齐半成品（这一轮）：
1) 「忘掉这台相机」同时撤销系统里的热点（原来只清了本机记录）
2) 备份持久化（重开页面还在）+ 显示备份时间 + 「用这份备份恢复相机」回滚按钮
3) 「记住它」→ 合并成「记住并连接」（一次点完记住 + 连上）
4) 打开导入相机页 / 回到前台 → 强刷一次 Wi-Fi 状态（手动连上也能正确显示）
5) 优化版每个槽位也加「导入」按钮（原来只有配方卡有）
6) 没备份过就写入 → 二次确认
7) 菜单加「检查权限」：列权限状态 + 一键跳到应用设置
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'

# ============================================================ Java
p = TMP + r'\apk\java\com\om3\handbook\MainActivity.java'
j = open(p, encoding='utf-8').read()
if 'openAppSettings' not in j:
    anchor = '''        @JavascriptInterface
        public String dropCamera() { autoDrop(); return "ok"; }'''
    assert j.count(anchor) == 1
    j = j.replace(anchor, anchor + '''

        /** 权限自检：{"camera":bool,"fine":bool,"nearby":bool,"sdk":33} */
        @JavascriptInterface
        public String permState() {
            java.util.function.Function<String, Boolean> has = null;
            boolean cam = checkSelfPermission(android.Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED;
            boolean fine = checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED;
            boolean near = (Build.VERSION.SDK_INT >= 33)
                    ? checkSelfPermission(android.Manifest.permission.NEARBY_WIFI_DEVICES) == PackageManager.PERMISSION_GRANTED
                    : true;
            return "{\\"camera\\":" + cam + ",\\"fine\\":" + fine + ",\\"nearby\\":" + near + ",\\"sdk\\":" + Build.VERSION.SDK_INT + "}";
        }

        @JavascriptInterface
        public void openAppSettings() {
            runOnUiThread(new Runnable() {
                @Override public void run() {
                    try {
                        Intent it = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                        it.setData(Uri.parse("package:" + getPackageName()));
                        it.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                        startActivity(it);
                    } catch (Throwable t) {
                        try { startActivity(new Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); } catch (Throwable t2) { }
                    }
                }
            });
        }''', 1)
    open(p, 'w', encoding='utf-8', newline='').write(j)
    print('Java: permState / openAppSettings 已加')
else:
    print('Java: 已应用过，跳过')

# ============================================================ 页面
P = TMP + r'\app\base.html'
h = open(P, encoding='utf-8').read()

# ---- (1) 忘掉相机 → 撤销系统热点 ----
old_forget = """    camForget(); renderSaved();
    camOut('已忘掉这台相机（下次要重新扫或手填）。', 'ok');"""
assert h.count(old_forget) == 1
h = h.replace(old_forget, """    camForget();
    try{ if(Native && Native.forgetWifi) Native.forgetWifi(); }catch(e){}
    if(Native && Native.dropCamera){ try{ Native.dropCamera(); }catch(e){} }
    renderSaved();
    if(window.__om3setConn) window.__om3setConn(false);
    camOut('已忘掉这台相机：本机记录和系统里记住的热点都撤了（下次要重新扫或手填）。', 'ok');""", 1)

# ---- (2) 备份持久化 + 回滚 ----
old_bak = "  var backupText = '';"
assert h.count(old_bak) == 1
h = h.replace(old_bak, """  var backupText = '';
  var BKEY = 'om3bak', backupAt = 0;
  function bakSave(text){
    backupText = text; backupAt = Date.now();
    try{ localStorage.setItem(BKEY, JSON.stringify({ t: backupAt, text: text })); }catch(e){ }
    showBakInfo();
  }
  function bakLoad(){
    if(backupText) return { t: backupAt, text: backupText };
    try{
      var b = JSON.parse(localStorage.getItem(BKEY) || 'null');
      if(b && b.text){ backupText = b.text; backupAt = b.t || 0; return b; }
    }catch(e){ }
    return null;
  }
  function showBakInfo(){
    var el = document.getElementById('camBakInfo');
    if(!el) return;
    var b = bakLoad();
    var rb = document.getElementById('camRestore'), dl = document.getElementById('camDl');
    if(b && b.text){
      el.innerHTML = '上次备份：' + tstr(b.t) + '（' + Math.round(b.text.length / 1024) + ' KB）';
      if(rb) rb.disabled = false;
      if(dl) dl.disabled = false;
    } else {
      el.textContent = '还没有备份。写配方前先点「读取并备份」。';
      if(rb) rb.disabled = true;
      if(dl) dl.disabled = true;
    }
  }""", 1)

# 备份完成处写入持久化
i = h.find("document.getElementById('camDl').disabled = false;")
assert i > 0
h = h[:i] + "bakSave(backupText);\n      " + h[i:]

# ② 卡片加「恢复」按钮 + 信息行
old_dl = '<button type="button" id="camDl" disabled>下载备份文件</button>'
assert h.count(old_dl) == 1, h.count(old_dl)
h = h.replace(old_dl, old_dl + '<button type="button" id="camRestore" disabled>用这份备份恢复相机</button>', 1)
old_out2 = '<div class="camout" id="camOut2">'
assert h.count(old_out2) == 1
h = h.replace(old_out2, '<div class="camout" id="camBakInfo">还没有备份。</div>\n      <div class="camout" id="camOut2">', 1)
print('② 备份：持久化 + 回滚按钮 + 备份时间')

# ---- (2b) 抽出发送流程 uploadData，并给回滚复用 ----
i = h.find("  async function writeRecipe(rec, slot, target, model, lg){")
j = h.find("  window.__om3writeRecipe = writeRecipe;")
assert 0 < i < j
body = h[i:j]
A = body.find("var r1 = await req('request_restoremysetdata.cgi?action=restore');")
B = body.find("if(document.getElementById('camReboot').checked){")
assert 0 < A < B, (A, B)
core = body[A:B]
dedent = '\n'.join(L[2:] if L.startswith('      ') else L for L in core.split('\n'))
UPLOAD = '''  /* 把一段文本传进相机（写入配方 / 恢复备份 共用同一套：恢复模式 → 声明大小 → 分块 → 等完成） */
  async function uploadData(bytes, lg){
    lg = lg || log;
''' + dedent + '''    return true;
  }
  window.__om3uploadData = uploadData;

  async function restoreBackup(){
    var b = bakLoad();
    if(!b || !b.text){ camOut('还没有备份可用。先点「读取并备份」。', 'warn'); return; }
    var bytes = new TextEncoder().encode(b.text);
    if(!confirm('把 ' + tstr(b.t) + ' 的备份写回相机？\\n\\n这会覆盖相机当前的设置（' + bytes.length + ' 字节），需要几十秒。')) return;
    showStep(3);
    log('===== 用备份恢复相机（' + bytes.length + ' 字节，备份时间 ' + tstr(b.t) + '）');
    try{
      await uploadData(bytes, log);
      log('恢复流程跑完。到相机上确认一下档位。', 'ok');
      toastMsg('备份已写回相机');
    }catch(e){
      log('恢复中断：' + e.message, 'err');
      toastMsg('恢复失败：' + e.message);
    }
  }
  window.__om3restoreBackup = restoreBackup;

'''
# 用 uploadData 替换 writeRecipe 里的那段
newbody = body[:A] + "await uploadData(bytes, lg);\n    " + body[B:]
h = h[:i] + UPLOAD + "  async function writeRecipe(rec, slot, target, model, lg){" + newbody + h[j:]
print('抽出 uploadData；回滚 = 同一套上传流程')

# 绑定恢复按钮 + 初始化备份信息
old_bind = "  document.getElementById('camDl').addEventListener('click', function(){"
assert h.count(old_bind) == 1
h = h.replace(old_bind, """  document.getElementById('camRestore').addEventListener('click', restoreBackup);
""" + old_bind, 1)
h = h.replace("  /* ---------- 日志：复制 / 下载 / 清空 ---------- */",
              "  showBakInfo();\n\n  /* ---------- 日志：复制 / 下载 / 清空 ---------- */", 1)
# 状态条的备份提示改用持久化备份
A1 = "st('camStBak', document.getElementById('camDl').disabled ? '备份：无' : '备份：已有',"
A2 = "document.getElementById('camDl').disabled ? '' : 'ok');"
assert h.count(A1) == 1 and h.count(A2) == 1, (h.count(A1), h.count(A2))
NEW1 = "var _b = null; try{ _b = JSON.parse(localStorage.getItem(BKEY) || 'null'); }catch(e){ }" + chr(10) + "    st('camStBak', (_b && _b.text) ? ('备份：' + tstr(_b.t)) : '备份：无',"
h = h.replace(A1, NEW1, 1)
h = h.replace(A2, "(_b && _b.text) ? 'ok' : '');", 1)

# ---- (3) 记住并连接 ----
old_join_btn = '<button type="button" id="camJoin">记住它，以后自动连</button>'
if h.count(old_join_btn) == 1:
    h = h.replace(old_join_btn, '<button type="button" id="camJoin">记住并连接这台相机</button>', 1)
old_join_handler = "      joinNow(document.getElementById('camSsid').value.trim(), document.getElementById('camPass').value.trim());"
assert h.count(old_join_handler) == 1
h = h.replace(old_join_handler, """      joinNow(document.getElementById('camSsid').value.trim(), document.getElementById('camPass').value.trim());
      setTimeout(connectNow, 600);          /* 记住之后顺手连上 */""", 1)

# ---- (4) 打开页面 / 回到前台 → 强刷一次 ----
old_vis = """  document.addEventListener('visibilitychange', function(){
    if(!document.hidden){ wifiCached(true); statusTick(); }
  });"""
assert h.count(old_vis) == 1
h = h.replace(old_vis, """  document.addEventListener('visibilitychange', function(){
    if(!document.hidden){ wifiCached(true); statusTick(); }
  });
  /* 每次切到"导入相机"页签，也强刷一次（手动连上相机后状态条要能立刻对上） */
  var _tabD0 = document.getElementById('tabD');
  if(_tabD0) _tabD0.addEventListener('click', function(){ setTimeout(function(){ wifiCached(true); statusTick(); }, 250); });""", 1)

# ---- (5) 优化版槽位也加导入按钮 ----
old_inject = "  function injectImp(){\n    if(!window.__OM3_APP__) return;"
assert h.count(old_inject) == 1
h = h.replace(old_inject, """  function recByName(n){
    if(!n) return null;
    for(var i=0;i<REC.length;i++) if(REC[i].n === n) return REC[i];
    return null;
  }
  window.__om3recByName = recByName;
  function injectImp(){
    if(!window.__OM3_APP__) return;""", 1)
old_inject2 = """      c.insertBefore(b, c.firstChild);
    }
  }"""
assert h.count(old_inject2) == 1
h = h.replace(old_inject2, """      c.insertBefore(b, c.firstChild);
    }
    /* 优化版每个槽位也来一个（用槽位上的配方名找参数） */
    var slots = document.querySelectorAll('.oslot[id^="oC"]');
    for(var k=0;k<slots.length;k++){
      var s0 = slots[k];
      if(s0.querySelector('.om3imp')) continue;
      var nm = s0.querySelector('.osname');
      var r0 = recByName(nm ? nm.textContent.trim() : '');
      if(!r0) continue;
      var b2 = document.createElement('button');
      b2.type = 'button';
      b2.className = 'om3imp';
      b2.textContent = '导入到 ' + s0.id.replace('-', ' · 槽').replace('oC', 'C');
      b2.setAttribute('data-slug', r0.slug);
      s0.insertBefore(b2, s0.firstChild);
    }
  }""", 1)

# ---- (6) 没备份过就写入 → 二次确认 ----
old_wf = "  async function writeRecipe(rec, slot, target, model, lg){\n    lg = lg || log;\n    if(!rec) return {ok:false, err:'no_recipe'};"
assert h.count(old_wf) == 1
h = h.replace(old_wf, """  async function writeRecipe(rec, slot, target, model, lg){
    lg = lg || log;
    if(!rec) return {ok:false, err:'no_recipe'};
    var _bk = null; try{ _bk = JSON.parse(localStorage.getItem(BKEY) || 'null'); }catch(e){ }
    if(!(_bk && _bk.text) && !confirm('你这次还没有备份过相机的设置。\\n\\n写坏了就只能用官方 OM Image Share 的「恢复设置」救。\\n\\n仍要继续吗？')) return {ok:false, err:'no_backup'};""", 1)

# ---- (7) 菜单加「检查权限」 ----
old_item = '      <button type="button" data-act="clearlog">清空日志</button>'
assert h.count(old_item) == 1
h = h.replace(old_item, old_item + '\n      <button type="button" data-act="perm">检查权限</button>', 1)
old_act = "      else if(a === 'clearlog') document.getElementById('camClearLog').click();"
assert h.count(old_act) == 1
h = h.replace(old_act, old_act + """
      else if(a === 'perm'){
        var ps = '';
        try{ ps = String(Native && Native.permState ? Native.permState() : '{}'); }catch(e){}
        var pj = {}; try{ pj = JSON.parse(ps); }catch(e){}
        showStep(1);
        var host1 = document.getElementById('camGateOut');
        if(host1){
          host1.innerHTML = '';
          line(host1, '权限自检（安卓 ' + (pj.sdk || '?') + '）：', 'ok');
          line(host1, '· 相机（扫码）：' + (pj.camera ? '已允许' : '未允许'), pj.camera ? 'ok' : 'warn');
          line(host1, '· 位置信息（连相机热点）：' + (pj.fine ? '已允许' : '未允许'), pj.fine ? 'ok' : 'warn');
          line(host1, '· 附近的设备（安卓 13+）：' + (pj.nearby ? '已允许' : '未允许'), pj.nearby ? 'ok' : 'warn');
        }
        try{ if(Native && Native.openAppSettings && !(pj.camera && pj.fine && pj.nearby)) Native.openAppSettings(); }catch(e){}
      }""", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('页面：七项补齐完成，base.html %.1f KB' % (len(h.encode('utf-8')) / 1024))
