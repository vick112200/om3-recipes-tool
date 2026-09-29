# -*- coding: utf-8 -*-
"""III. 任务条 + 跨重启验收 + 重启提示
   ① 任务条：面板顶部显示"正在执行什么 / 进度 n/N / 已用秒 / ✅❌"，长任务期间拒绝重复点击
   ② 写入流程：结束后写"待校验记录"（目标 my-set + 期望键值）
   ③ 新增菜单「校验上次写入」：重启后重连一点，读回目标 my-set 逐项核对 → ✅/⚠ + 差异清单
   ④ 重启调用后，日志明确提示"相机会断开；若没重启请手动关机再开机"
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- ① CSS + 任务条 DOM ----------
k = h.find('</style>')
assert k > 0
h = h[:k] + """
/* ---------- 任务条：在跑什么、跑到哪、跑完没 ---------- */
.camrun{display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:8px;background:#1b2130;border:1px solid #2b3a55;color:#cfe0ff;font-size:12.5px;margin:6px 0}
.camrun.hide{display:none}
.camrun.busy{border-color:#3f6ea8;background:#16233a}
.camrun.ok{border-color:#2f7d4f;background:#16261c;color:#bdf0cf}
.camrun.err{border-color:#8a3b3b;background:#2a1717;color:#ffc9c9}
.camrun .spin{width:12px;height:12px;border:2px solid #4a7ac0;border-top-color:transparent;border-radius:50%;animation:om3spin .8s linear infinite;flex:none}
@keyframes om3spin{to{transform:rotate(360deg)}}
.camrun .t{margin-left:auto;opacity:.75;flex:none}
""" + h[k:]

import re as _re
mD = _re.search(r'id="paneD"[^>]*>', h)
assert mD, 'paneD not found'
BANNER = ('\n    <div class="camrun hide" id="camRun"><span class="spin"></span>'
          '<span id="camRunTxt">待机</span><span class="t" id="camRunTime"></span></div>')
h = h[:mD.end()] + BANNER + h[mD.end():]

# ---------- ① runTask 实现（挂在 writeSlotRecipe 前面） ----------
anchor = "  /* 把界面上的\"目标\"（current / C1..C5 / 录像C1..C5）映射成相机 my-set 名 */"
assert h.count(anchor) == 1, h.count(anchor)
RUN = '''  /* ===== 任务条：把长任务包起来，随时看得见"跑到哪、跑完没" ===== */
  var _run = { busy: false, t0: 0, timer: 0 };
  function om3banner(state, txt){
    var el = document.getElementById('camRun');
    if(!el) return;
    el.classList.remove('hide', 'busy', 'ok', 'err');
    el.classList.add(state);
    document.getElementById('camRunTxt').textContent = txt;
    var sp = el.querySelector('.spin');
    if(sp) sp.style.display = (state === 'busy') ? '' : 'none';
  }
  async function runTask(label, fn){
    if(_run.busy){ toastMsg('还有一个任务在跑，等它跑完再点'); return false; }
    _run.busy = true; _run.t0 = Date.now();
    om3banner('busy', '正在执行：' + label);
    clearInterval(_run.timer);
    _run.timer = setInterval(function(){
      var tm = document.getElementById('camRunTime');
      if(tm) tm.textContent = '已用 ' + Math.round((Date.now() - _run.t0) / 1000) + ' 秒';
    }, 1000);
    var ok = true, msg = '';
    try{ await fn(); }
    catch(e){ ok = false; msg = (e && e.message) ? e.message : String(e); }
    clearInterval(_run.timer);
    var sec = Math.round((Date.now() - _run.t0) / 1000);
    om3banner(ok ? 'ok' : 'err', (ok ? '✅ 完成：' : '❌ 失败：') + label + '（用时 ' + sec + ' 秒）' + (ok ? '' : '　' + msg));
    _run.busy = false; _run.t0 = 0;
    return ok;
  }
  window.__om3runTask = runTask;

  /* ===== 待校验记录：写入后存下"应该是什么"，重启重连后一键核对 ===== */
  var PENDKEY = 'om3pend';
  function pendSave(o){ try{ localStorage.setItem(PENDKEY, JSON.stringify(o)); }catch(e){} }
  function pendLoad(){ try{ return JSON.parse(localStorage.getItem(PENDKEY) || 'null'); }catch(e){ return null; } }
  async function verifyPending(){
    var p = pendLoad();
    showStep(3);
    if(!p){ log('没有待校验的写入记录。', 'warn'); return; }
    log('===== 校验上次写入：' + (p.recipe || '') + ' → ' + p.mode + ' · 槽' + p.slot + '（' + p.at + '）');
    var back;
    try{ back = await readMySet(p.mode); }
    catch(e){ log('读取失败：' + e.message + '（相机连上了吗？）', 'err'); return; }
    var bm = om3map(back), bad = [], k;
    for(k in p.kv){
      if(!Object.prototype.hasOwnProperty.call(p.kv, k)) continue;
      if(bm[k] !== p.kv[k]) bad.push(k + '：期望 ' + p.kv[k] + '，相机里 ' + (bm[k] === undefined ? '（无此项）' : bm[k]));
    }
    if(!bad.length){
      log('✅ 全部 ' + Object.keys(p.kv).length + ' 项与配方一致 —— 写入已真正生效', 'ok');
      try{ localStorage.removeItem(PENDKEY); }catch(e){}
      log('（已清除待校验记录）', 'ok');
    } else {
      log('⚠ 有 ' + bad.length + ' 项不一致：', 'warn');
      for(var i = 0; i < bad.length && i < 15; i++) log('　　 ' + bad[i], 'warn');
      log('说明：可能相机没重启（数据没应用），或目标槽不是这个。', 'warn');
    }
    log('===== 校验结束', 'ok');
    toastMsg('校验完成，看日志');
  }
  window.__om3verify = verifyPending;

'''
h = h.replace(anchor, RUN + anchor, 1)

# ---------- ② 写入末尾：存待校验记录 + 重启提示 ----------
old_tail = "    lg('⑪ 已请求相机重启（退出维护模式）：HTTP ' + r9.status, 'ok');"
assert h.count(old_tail) == 1, h.count(old_tail)
new_tail = """    try{ pendSave({ mode: modeName, slot: slotN, kv: kv, recipe: rec.n, at: new Date().toLocaleString('zh-CN') }); }catch(e){}
    lg('⑪ 已请求相机重启：HTTP ' + r9.status + '　（相机会断开 Wi-Fi，等 20–30 秒）', 'ok');
    lg('　　⚠ 如果相机没有重启：请手动关机再开机 —— 不重启数据可能不会应用。', 'warn');
    lg('　　✅ 重连之后点 ☰ →「校验上次写入」，会自动读回并逐项核对（已存好待校验记录）。', 'ok');"""
h = h.replace(old_tail, new_tail, 1)

# ---------- ③ 菜单项 ----------
old_m = '      <button type="button" data-act="w_c1s1">写入 C1 · 槽1（用③选的配方）</button>'
assert h.count(old_m) == 1, h.count(old_m)
h = h.replace(old_m, old_m + '\n      <button type="button" data-act="verify">校验上次写入（重启后点我）</button>', 1)
old_a = "      else if(a === 'w_c1s1'){"
assert h.count(old_a) == 1, h.count(old_a)
h = h.replace(old_a, """      else if(a === 'verify'){ runTask('校验上次写入', function(){ return verifyPending(); }); }
""" + old_a, 1)

# ---------- ④ 新写入入口 + 预览 走任务条 ----------
old_call = "      await writeSlotRecipe(mode, Number(slot) || 1, rec);"
assert h.count(old_call) == 1, h.count(old_call)
h = h.replace(old_call, "      await runTask('写入 ' + mode + ' · 槽' + (Number(slot) || 1) + ' ← ' + rec.n, function(){ return writeSlotRecipe(mode, Number(slot) || 1, rec); });", 1)
old_prev = "    try{ previewSlot(mode, Number(slot) || 1, rec); }"
assert h.count(old_prev) == 1, h.count(old_prev)
h = h.replace(old_prev, "    try{ runTask('预览（只读）', function(){ return previewSlot(mode, Number(slot) || 1, rec); }); }", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('III 完成：任务条 + 待校验记录 + 校验入口 + 重启提示（+%d 字节）' % (len(h) - n0))
