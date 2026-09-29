# -*- coding: utf-8 -*-
"""II. 面板完善（小步快跑）：
   ① 修正 readMySet：读之前先确保进维护模式（否则可能 1001）
   ② 加「预览（只读）」按钮：读回目标 my-set → 显示 4 个槽占用 → 列出"要改的 19 项"
   ③ 目标下拉补上录像档（moviemyset1–5）
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- ① readMySet 先确保维护模式 ----------
old = """  async function readMySet(modeName, lg){
    lg = lg || log;
    var rq = await req('request_getmysetdata.cgi?mode=' + encodeURIComponent(modeName) + '&kind=current', {timeout: 20000});"""
assert h.count(old) == 1, h.count(old)
new = """  async function readMySet(modeName, lg){
    lg = lg || log;
    /* my-set 相关接口只在维护模式里被受理 —— 先确保进维护模式（已进则重复调用无害） */
    try{
      var rM0 = await req('switch_cammode.cgi?mode=maintenance', {timeout: 10000});
      if(rM0.status !== 200) throw new Error('相机不接受维护模式（HTTP ' + rM0.status + '）');
    }catch(e){ throw new Error('进维护模式失败：' + e.message); }
    var rq = await req('request_getmysetdata.cgi?mode=' + encodeURIComponent(modeName) + '&kind=current', {timeout: 20000});"""
h = h.replace(old, new, 1)

# ---------- ② 预览按钮（放在 ③ 写入按钮后面） ----------
old_btn = '<button type="button" id="camWrite" class="camprimary">写入相机'
assert h.count(old_btn) == 1, h.count(old_btn)
h = h.replace(old_btn, '<button type="button" id="camPreview">预览（只读，先看会改什么）</button><button type="button" id="camWrite" class="camprimary">写入相机', 1)

# ---------- ② 预览逻辑 ----------
anchor = "  /* 把界面上的\"目标\"（current / C1..C5 / 录像C1..C5）映射成相机 my-set 名 */"
assert h.count(anchor) == 1, h.count(anchor)
PREV = '''  /* 预览：只读 —— 读回目标 my-set，显示 4 个槽占用 + 列出会被改动的项 */
  async function previewSlot(modeName, N, rec){
    showStep(3);
    log('===== 预览（只读，不会写入任何东西）：' + (rec && rec.n ? rec.n : '（未选配方）') + ' → ' + modeName + ' · 槽' + N);
    if(!rec){ log('先在 ③ 里选一条配方。', 'err'); return; }
    var before;
    try{ before = await readMySet(modeName); }
    catch(e){ log('读取失败：' + e.message, 'err'); return; }
    log('① 读回 ' + modeName + '：' + before.length + ' 字节', 'ok');
    log('② 该档位 4 个槽的占用：' + om3slotSummary(before));
    var kv, pat;
    try{ kv = slotKV(rec, N); }
    catch(e){ log('这条配方不能写入：' + e.message, 'err'); return; }
    pat = patchText(before, kv);
    if(pat.missed.length){
      log('③ ⚠ 有 ' + pat.missed.length + ' 个键在这份数据里不存在，写入会被中止：', 'err');
      for(var q = 0; q < pat.missed.length && q < 12; q++) log('　　 ' + pat.missed[q], 'err');
      return;
    }
    if(!pat.changed.length){ log('③ 目标槽现在就是这条配方的值（无需改动）', 'ok'); return; }
    log('③ 会改动 ' + pat.changed.length + ' 项：');
    for(var i = 0; i < pat.changed.length && i < 24; i++) log('　　 ' + pat.changed[i]);
    log('④ 数据总长 ' + before.length + ' → ' + pat.text.length + ' 字节（差 ' + (pat.text.length - before.length) + '，属正常）');
    log('✅ 预览完成：19 项齐全、可以写入（点「写入相机」真正下发）', 'ok');
    toastMsg('预览完成，看日志');
  }
  window.__om3preview = previewSlot;

'''
h = h.replace(anchor, PREV + anchor, 1)

# 绑按钮
old_bind = "  document.getElementById('camRestore').addEventListener('click', restoreBackup);"
assert h.count(old_bind) == 1, h.count(old_bind)
h = h.replace(old_bind, """  document.getElementById('camPreview').addEventListener('click', function(){
    var s = currentSel();
    runPlainPreview(s.rec, s.slot, s.target);
  });
""" + old_bind, 1)

# 小包装：把 ③ 的 target/slot 取出来交给 previewSlot（用 try/catch，不影响其它逻辑）
old_wrap_anchor = "  /* 把界面上的\"目标\"（current / C1..C5 / 录像C1..C5）映射成相机 my-set 名 */"
assert h.count(old_wrap_anchor) == 1
h = h.replace(old_wrap_anchor, """  function runPlainPreview(rec, slot, target){
    var mode = modeForTarget(target);
    try{ previewSlot(mode, Number(slot) || 1, rec); }
    catch(e){ log('预览失败：' + e.message, 'err'); }
  }

""" + old_wrap_anchor, 1)

# ---------- ③ 录像档目标 ----------
old_opt = '      <option value="myset5">C5 自定义档</option>'
assert h.count(old_opt) == 1, h.count(old_opt)
h = h.replace(old_opt, old_opt + """
      <option value="moviemyset1">录像档 1</option><option value="moviemyset2">录像档 2</option>
      <option value="moviemyset3">录像档 3</option><option value="moviemyset4">录像档 4</option>
      <option value="moviemyset5">录像档 5</option>""", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('II 完成：预览按钮 + 维护模式修正 + 录像档选项（+%d 字节）' % (len(h) - n0))
