# -*- coding: utf-8 -*-
"""导入体验：
1) 未连接 → 只给"怎么连"的导航卡；已连接 → 显示连接状态卡 + 备份/写入/导入记录
2) 配方卡上加「导入相机」按钮（连着相机才显示），点了选槽位直接写入
3) 导入记录：存本地，可查看；并据此显示 C1–C5 × 4 槽当前装的是什么配方
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
P = TMP + r'\app\base.html'
h = open(P, encoding='utf-8').read()
open(TMP + r'\app\base.before_import.html', 'w', encoding='utf-8', newline='').write(h)

# ============================================================ 1. 写相机：抽成函数（③ 和配方卡共用）
i = h.find("  document.getElementById('camWrite').addEventListener('click', async function(){")
j = h.find("  /* 配方下拉：优化版那 21 个排前面 */")
assert 0 < i < j
old = h[i:j]
assert 'buildPayload' in old and 'camReboot' in old
a = old.find('var text = buildPayload(')
d = old.find('    this.disabled = false;')
assert 0 < a < d
seq = old[a:d]
for x, y in [('log(', 'lg('), ('s.rec', 'rec'), ('s.slot', 'slot'), ('s.target', 'target'), ('s.model', 'model')]:
    seq = seq.replace(x, y)
canc = "if(!confirm('把「' + rec.n + '」写进 ' + target + ' 的 Color Profile 槽 ' + slot + '？"
if canc in seq:
    seq = seq.replace(canc, "if(!confirm('把「' + rec.n + '」写进 ' + target + ' 的 Color Profile 槽 ' + slot + '？", 1)
    seq = seq.replace("写入前请确认已经备份过（②）。')) return;", "写入前请确认已经备份过（②）。')) return {ok:false, err:'cancelled'};", 1)
NEW_WRITE = '''  /* ================= 把配方写进相机（③ 按钮 + 配方卡「导入」共用） ================= */
  async function writeRecipe(rec, slot, target, model, lg){
    lg = lg || log;
    if(!rec) return {ok:false, err:'no_recipe'};
    if(!model) return {ok:false, err:'no_model'};
    try{
''' + '\n'.join('    ' + L for L in seq.split('\n')) + '''
    }catch(e){
      lg('中断：' + e.message, 'err');
      lg('如果相机状态不对：用官方 OM Image Share 的「恢复设置」，或用 ② 的备份找我回滚。', 'warn');
      return {ok:false, err:e.message};
    }
    return {ok:true};
  }
  window.__om3writeRecipe = writeRecipe;

  document.getElementById('camWrite').addEventListener('click', async function(){
    var s = currentSel();
    if(!s.rec){ log('没选配方。','err'); return; }
    if(!s.model){ log('请先点 ① 检测相机（或手动填相机型号），型号要写进数据头部。','err'); return; }
    this.disabled = true;
    var r = await writeRecipe(s.rec, s.slot, s.target, s.model, log);
    if(r.ok){ impRecord(s.rec, s.target, s.slot); log('已记入导入记录（☰ → 导入记录）。','ok'); }
    else if(r.err === 'cancelled') log('已取消。','warn');
    this.disabled = false;
  });

'''
h = h[:i] + NEW_WRITE + h[j:]
print('① 写相机逻辑已抽成 writeRecipe()（③ 与配方卡共用）')

# ============================================================ 2. 标记 & CSS
CSS = '''
/* ---------- 导入相机：连接门控 / 配方卡导入按钮 / 记录表 ---------- */
.camgate{background:#1c1c1c;border:1px solid #2e2e2e;border-radius:12px;padding:14px 16px;margin:0 0 14px}
.camgate h3{margin:0 0 8px;font-size:16px}
.camgate ol{margin:6px 0 10px 18px;padding:0;color:#bbb;font-size:13px;line-height:1.8}
.camgate .big{background:#2f8f74;color:#fff;border:0;border-radius:9px;padding:11px 16px;font-size:14.5px;font-weight:700;font-family:inherit;cursor:pointer;margin:0 8px 8px 0}
.camgate .gho{background:#242424;border:1px solid #3a3a3a;color:#ddd;border-radius:9px;padding:10px 14px;font-size:13.5px;font-family:inherit;cursor:pointer;margin:0 8px 8px 0}
.camconn{background:#16281f;border:1px solid #2f8f74;border-radius:12px;padding:12px 15px;margin:0 0 14px;display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.camconn .dot{width:10px;height:10px;border-radius:50%;background:#39d98a;box-shadow:0 0 8px #39d98a}
.camconn b{color:#fff}
.camconn button{background:#242424;border:1px solid #3a3a3a;color:#ddd;border-radius:8px;padding:7px 12px;font-size:12.5px;font-family:inherit;cursor:pointer}
.om3imp{display:none;margin:0 0 8px;background:#2f8f74;color:#fff;border:0;border-radius:8px;padding:6px 12px;font-size:12.5px;font-weight:700;font-family:inherit;cursor:pointer}
body.cam-on .om3imp{display:inline-block}
.improw{display:flex;align-items:center;gap:10px;padding:9px 10px;border-bottom:1px solid #2a2a2a;cursor:pointer}
.improw:hover{background:#242424}
.improw .lk{flex:0 0 96px;color:#8fd8c2;font-weight:700;font-size:13px}
.improw .lv{flex:1 1 auto;color:#ddd;font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.improw .lo{color:#777;font-size:11.5px}
.recmap{width:100%;border-collapse:collapse;font-size:12.5px}
.recmap th,.recmap td{border:1px solid #2e2e2e;padding:6px 8px;text-align:left;color:#ccc}
.recmap th{background:#202020;color:#9a9a9a;font-weight:600}
.recrow{padding:7px 0;border-bottom:1px solid #242424;font-size:12.5px;color:#ccc}
.recrow b{color:#8fd8c2}
'''
k = h.find('</style>')
h = h[:k] + CSS + h[k:]

# 菜单加「导入记录」
old_menu = '      <button type="button" data-step="3">③ 写入配方</button>'
assert h.count(old_menu) == 1
h = h.replace(old_menu, old_menu + '\n      <button type="button" data-step="4">📋 导入记录</button>', 1)

# ============================================================ 3. 门控卡片 + 记录视图
anchor = '  <div class="camcard">\n    <div class="camhd">连接 / 断开</div>'
assert h.count(anchor) == 1
GATE = '''  <div class="camgate" id="camGateOff">
    <h3>还没连上相机 —— 照这个走</h3>
    <ol>
      <li>相机上：<b>MENU → Wi-Fi/蓝牙 → Wi-Fi 设置</b>（或「连接智能手机」那一屏），屏幕会出现二维码</li>
      <li>手机：点下面的「<b>扫二维码</b>」对着它扫一下（<b>只要第一次</b>）</li>
      <li>以后每次：相机 Wi-Fi 打开后，点「<b>连接相机</b>」就行，不用再扫</li>
    </ol>
    <button type="button" class="big" id="camGateScan">扫二维码</button>
    <button type="button" class="big" id="camGateConn">连接相机</button>
    <button type="button" class="gho" id="camGateManual">手动填 SSID / 密码</button>
    <div class="camout" id="camGateOut"></div>
  </div>

  <div class="camconn hide" id="camStatusCard">
    <span class="dot"></span>
    <b id="camConnSsid">已连接相机</b>
    <span id="camConnNote" style="color:#8fd8c2;font-size:12.5px">相机 HTTP 走这条连接；点「断开」回原来的 Wi-Fi</span>
    <span style="flex:1"></span>
    <button type="button" id="camConnCheck">检测相机</button>
    <button type="button" id="camConnOff">断开</button>
  </div>

'''
h = h.replace(anchor, GATE + anchor, 1)

# 记录视图：跟在 camV3 之后
i = h.find('<div class="camview hide" id="camV3">')
j = h.find('\n', h.find('</div>', i))          # 占位，稍后按结构定位
# 找 camV3 的结束：下一个 camview 或模块结束
k2 = h.find('<div class="camview hide" id="camV4">')
if k2 < 0:
    # camV3 是该区域最后一个视图：插到它后面 —— 用 paneD 的结束标记前的最后一个 </div>
    end_marker = '<!-- ============ 扫码浮层 ============ -->'
    z = h.find(end_marker, i)
    assert z > 0, '没找到 paneD 结束位置'
    INS = '''
  <div class="camview hide" id="camV4">
    <div class="camcard">
      <div class="camhd">导入记录 · 相机槽位现状</div>
      <div class="camout" id="camRecOut">还没有导入记录。用 ③ 或配方卡上的「导入相机」写一次，这里就会记下来。</div>
      <button type="button" id="camRecClear">清空记录</button>
    </div>
  </div>
'''
    h = h[:z] + INS + h[z:]
    print('② 记录视图 camV4 已插入')

# ============================================================ 4. 导入记录 + 槽位选择弹层
j = h.rfind('})();')
assert j > 0
BLOCK = '''
  /* ================= 导入记录 / 槽位现状 ================= */
  var RKEY = 'om3rec';
  function recLoad(){ try{ return JSON.parse(localStorage.getItem(RKEY) || '[]'); }catch(e){ return []; } }
  function recSave(a){ try{ localStorage.setItem(RKEY, JSON.stringify(a.slice(-300))); }catch(e){} }
  function impRecord(rec, target, slot){
    var a = recLoad();
    a.push({ t: Date.now(), slug: rec.slug, n: rec.n, au: rec.a, target: target, slot: slot });
    recSave(a);
    renderRecords();
  }
  window.__om3impRecord = impRecord;
  function slotMap(){
    var a = recLoad(), m = {};
    for(var i=0;i<a.length;i++) m[a[i].target + '|' + a[i].slot] = a[i];
    return m;
  }
  function tstr(t){
    var d = new Date(t), p = function(x){ return (x<10?'0':'') + x; };
    return (d.getMonth()+1) + '/' + d.getDate() + ' ' + p(d.getHours()) + ':' + p(d.getMinutes());
  }
  function renderRecords(){
    var box = document.getElementById('camRecOut');
    if(!box) return;
    var a = recLoad(), m = slotMap();
    if(!a.length){ box.innerHTML = '还没有导入记录。用 ③ 或配方卡上的「导入相机」写一次，这里就会记下来。'; return; }
    var out = ['<div style="margin-bottom:10px"><b>按记录，相机各档位现在的配方：</b></div>'];
    var tg = ['C1','C2','C3','C4','C5'];
    out.push('<table class="recmap"><tr><th>档位</th><th>槽1</th><th>槽2</th><th>槽3</th><th>槽4</th></tr>');
    for(var i=0;i<tg.length;i++){
      out.push('<tr><td>' + tg[i] + '</td>');
      for(var s=1;s<=4;s++){
        var r = m[tg[i] + '|' + s];
        out.push('<td>' + (r ? (r.n + '<br><span style="color:#777">' + tstr(r.t) + '</span>') : '<span style="color:#555">—</span>') + '</td>');
      }
      out.push('</tr>');
    }
    out.push('</table>');
    var cur = null;
    for(var q=a.length-1;q>=0;q--) if(a[q].target === 'current'){ cur = a[q]; break; }
    out.push('<div class="recrow" style="margin-top:10px">当前状态（不占档）：' +
      (cur ? '<b>' + cur.n + '</b> · ' + cur.au + '　' + tstr(cur.t) : '<span style="color:#777">没有记录</span>') + '</div>');
    out.push('<div style="margin:12px 0 6px"><b>导入历史（最近 40 条）</b></div>');
    var n = 0;
    for(var w=a.length-1;w>=0 && n<40;w--,n++){
      out.push('<div class="recrow">' + tstr(a[w].t) + '　' + a[w].n + ' → <b>' + (a[w].target === 'current' ? '当前状态' : a[w].target + ' · 槽' + a[w].slot) + '</b></div>');
    }
    box.innerHTML = out.join('');
  }
  window.__om3renderRecords = renderRecords;
  renderRecords();
  var rc = document.getElementById('camRecClear');
  if(rc) rc.addEventListener('click', function(){
    if(!confirm('清空所有导入记录？（只是本机的记录，相机里的配方不动）')) return;
    recSave([]); renderRecords();
  });

  /* ---------- 槽位选择弹层 ---------- */
  function openImport(rec){
    var m = slotMap();
    var box = document.getElementById('impList');
    var title = document.getElementById('impTitle');
    function row(target, slot, label, occ){
      var b = document.createElement('div');
      b.className = 'improw';
      b.innerHTML = '<span class="lk">' + label + '</span><span class="lv">' +
        (occ ? esc(occ.n + ' · ' + occ.au) : '<span style="color:#666">空 / 没记录</span>') + '</span>';
      b.addEventListener('click', function(){ doImport(rec, target, slot); });
      box.appendChild(b);
    }
    title.innerHTML = '把「<b>' + esc(rec.n) + '</b>」导入到：';
    box.innerHTML = '';
    row('current', 1, '当前状态', m['current|1']);
    var tg = ['C1','C2','C3','C4','C5'];
    for(var i=0;i<tg.length;i++)
      for(var s=1;s<=4;s++)
        row(tg[i], s, tg[i] + ' · 槽' + s, m[tg[i] + '|' + s]);
    document.getElementById('impMask').classList.remove('hide');
  }
  window.__om3openImport = openImport;
  document.getElementById('impCancel').addEventListener('click', function(){
    document.getElementById('impMask').classList.add('hide');
  });
  document.getElementById('impMask').addEventListener('click', function(e){
    if(e.target === this) this.classList.add('hide');
  });
  function modelNow(){
    var m = document.getElementById('camModel');
    return (m && m.value.trim()) || (camSaved() && '');
  }
  async function doImport(rec, target, slot){
    var lbl = (target === 'current') ? '当前状态' : (target + ' · 槽' + slot);
    if(!confirm('把「' + rec.n + '」写进相机的 ' + lbl + '？\\n\\n写之前最好先做一次 ② 备份。')) return;
    document.getElementById('impMask').classList.add('hide');
    showStep(3);
    var model = modelNow();
    if(!model){ log('缺相机型号：先到 ① 点「检测相机」（或手填型号），再导入。','err'); return; }
    log('【配方卡导入】' + rec.n + ' → ' + lbl);
    var r = await writeRecipe(rec, slot, target, model, log);
    if(r.ok){
      impRecord(rec, target, slot);
      document.getElementById('camWriteOut') && line(document.getElementById('camWriteOut'), '已导入：' + rec.n + ' → ' + lbl, 'ok');
      toastMsg('已导入：' + rec.n + ' → ' + lbl);
    } else if(r.err !== 'cancelled'){
      toastMsg('导入失败：' + r.err);
    }
  }
  function toastMsg(t){
    var d = document.createElement('div');
    d.textContent = t;
    d.style.cssText = 'position:fixed;left:50%;bottom:38px;transform:translateX(-50%);background:#2f8f74;color:#fff;padding:11px 18px;border-radius:10px;font-size:13.5px;z-index:200;box-shadow:0 6px 20px rgba(0,0,0,.5)';
    document.body.appendChild(d);
    setTimeout(function(){ d.parentNode && d.parentNode.removeChild(d); }, 2600);
  }
  /* 配方卡上的「导入相机」按钮 */
  function injectImp(){
    if(!window.__OM3_APP__) return;
    var cards = document.querySelectorAll('[id^="r-"]');
    for(var i=0;i<cards.length;i++){
      var c = cards[i];
      if(c.querySelector('.om3imp')) continue;
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'om3imp';
      b.textContent = '导入相机';
      b.setAttribute('data-slug', c.id.slice(2));
      c.insertBefore(b, c.firstChild);
    }
  }
  injectImp();
  document.addEventListener('click', function(e){
    var b = e.target && e.target.closest ? e.target.closest('.om3imp') : null;
    if(!b) return;
    e.preventDefault(); e.stopPropagation();
    var slug = b.getAttribute('data-slug'), rec = null;
    for(var i=0;i<REC.length;i++) if(REC[i].slug === slug){ rec = REC[i]; break; }
    if(!rec){ toastMsg('这条配方没有可导入的参数'); return; }
    if(!document.body.classList.contains('cam-on')){ toastMsg('先到「导入相机」把相机连上'); return; }
    openImport(rec);
  }, true);

  /* ---------- 连接状态 → 界面切换 ---------- */
  function setConn(on){
    document.body.classList.toggle('cam-on', !!on);
    var g = document.getElementById('camGateOff'), c = document.getElementById('camStatusCard');
    if(g) g.classList.toggle('hide', !!on);
    if(c) c.classList.toggle('hide', !on);
    if(on){
      var s = camSaved();
      var el = document.getElementById('camConnSsid');
      if(el) el.textContent = '已连接' + (s && s.ssid ? '：' + s.ssid : '相机');
      var cs = {};
      try{ cs = JSON.parse(Native && Native.cameraState ? (Native.cameraState() || '{}') : '{}'); }catch(err){ cs = {}; }
      if(cs.ssid && el) el.textContent = '已连接：' + cs.ssid;
      if(!document.body.classList.contains('cam-started')) showStep(2);
      renderRecords();
    }
  }
  window.__om3setConn = setConn;
  var gs = document.getElementById('camGateScan'), gc = document.getElementById('camGateConn'), gm = document.getElementById('camGateManual');
  if(gs) gs.addEventListener('click', function(){ showStep(1); var b = document.getElementById('camScan'); if(b) b.click(); });
  if(gc) gc.addEventListener('click', function(){ showStep(1); connectNow(); });
  if(gm) gm.addEventListener('click', function(){ showStep(1); showManual('把相机屏幕上写的 SSID / 密码填到下面两格，再点「记住它，以后自动连」。', 'warn'); });
  var cc = document.getElementById('camConnCheck'), co = document.getElementById('camConnOff');
  if(cc) cc.addEventListener('click', function(){ var b = document.getElementById('camCheck'); if(b) b.click(); });
  if(co) co.addEventListener('click', function(){ var b = document.getElementById('camDisconnect'); if(b) b.click(); });
  setConn(false);
'''
h = h[:j] + BLOCK + h[j:]
print('③ 导入记录 / 槽位弹层 / 配方卡按钮 / 连接门控 已加入')

# 菜单项 4 → camV4；未连接时不许跳到 ②③④
OLD_STEP = """  function showStep(n){
    for(var k=1;k<=3;k++) document.getElementById('camV'+k).classList.toggle('hide', k !== n);"""
assert h.count(OLD_STEP) == 1
h = h.replace(OLD_STEP, """  function showStep(n){
    if(n >= 2 && !document.body.classList.contains('cam-on')){
      var g = document.getElementById('camGateOut');
      if(g) g.innerHTML = '<div class="line warn">先连上相机（上面三步）——连接成功后这里会显示 备份 / 写入 / 导入记录。</div>';
      n = 1;
    }
    document.body.classList.add('cam-started');
    for(var k=1;k<=4;k++){
      var v = document.getElementById('camV'+k);
      if(v) v.classList.toggle('hide', k !== n);
    }""", 1)
OLD_NAME = "  var STEPNAME = {1:'① 连接相机', 2:'② 备份设置', 3:'③ 写入配方'};"
assert h.count(OLD_NAME) == 1
h = h.replace(OLD_NAME, "  var STEPNAME = {1:'① 连接相机', 2:'② 备份设置', 3:'③ 写入配方', 4:'📋 导入记录'};", 1)

# 连接状态回调 → setConn
OLD_CB = """  window.__om3camState = function(state){
    if(state === 'connected'){ camOut('已连上相机热点。', 'ok'); st('camStCam', '相机：已连接', 'ok'); }"""
assert h.count(OLD_CB) == 1
h = h.replace(OLD_CB, """  window.__om3camState = function(state){
    if(window.__om3setConn) window.__om3setConn(state === 'connected' || state === 'retry');
    if(state === 'connected'){ camOut('已连上相机热点。', 'ok'); st('camStCam', '相机：已连接', 'ok'); }""", 1)
OLD_CB2 = """    else if(state === 'lost'){ camOut('相机连接断了（相机休眠或走远了）。再点一次「连接相机」即可。', 'warn'); st('camStCam', '相机：已断开', 'warn'); }"""
assert h.count(OLD_CB2) == 1
h = h.replace(OLD_CB2, OLD_CB2 + """
    else if(state === 'lost' || state === 'unavailable' || state === 'denied'){ if(window.__om3setConn) window.__om3setConn(false); }""", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('完成，base.html %.1f KB' % (len(h.encode('utf-8')) / 1024))
