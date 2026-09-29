# -*- coding: utf-8 -*-
"""任务进度改成"屏幕中央弹窗"：
   · 执行中：中央弹窗显示 任务名 / 进度 n/N / 已用秒 + [后台运行]
   · 后台运行：弹窗收起，右下角出现小气泡「⟳ 任务运行中」，点它随时再打开看进度
   · 结束：弹窗显示 ✅ / ❌（含原因）+ [关闭]；气泡变成「✅ 完成 / ❌ 失败」，点了看结果
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- ① CSS ----------
k = h.find('</style>')
assert k > 0
h = h[:k] + """
/* ---------- 任务弹窗（屏幕中央） ---------- */
.taskmask{position:fixed;left:0;top:0;right:0;bottom:0;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;z-index:9500}
.taskmask.hide{display:none !important}
.taskcard{width:min(88vw,380px);background:#171717;border:1px solid #2e2e2e;border-radius:14px;padding:16px;box-shadow:0 12px 40px rgba(0,0,0,.6)}
.taskcard .trow{display:flex;align-items:center;gap:9px;font-size:15px;color:#f2f2f2;font-weight:600}
.taskcard .spin{width:15px;height:15px;border:2px solid #4a7ac0;border-top-color:transparent;border-radius:50%;animation:om3spin .8s linear infinite;flex:none}
.taskcard.ok .spin{display:none}
.taskcard.err .spin{display:none}
.tprog{margin-top:9px;font-size:13px;color:#bfc9d8;line-height:1.5;word-break:break-all}
.ttime{margin-top:5px;font-size:12px;color:#8b93a1}
.tbtns{display:flex;gap:9px;margin-top:14px}
.tbtns button{flex:1;padding:10px;border-radius:9px;border:1px solid #333;background:#222;color:#e6e6e6;font-size:13px}
.tbtns button.primary{background:#2b5cff;border-color:#2b5cff;color:#fff;font-weight:600}
.taskpill{position:fixed;right:12px;bottom:76px;z-index:9400;padding:9px 13px;border-radius:999px;border:1px solid #3f6ea8;background:#16233a;color:#cfe0ff;font-size:12.5px;box-shadow:0 6px 20px rgba(0,0,0,.5)}
.taskpill.hide{display:none !important}
.taskpill.ok{border-color:#2f7d4f;background:#16261c;color:#bdf0cf}
.taskpill.err{border-color:#8a3b3b;background:#2a1717;color:#ffc9c9}
""" + h[k:]

# ---------- ② DOM ----------
mB = h.rfind('</body>')
assert mB > 0
DOM = '''
<!-- 任务进度弹窗 -->
<div id="taskMask" class="taskmask hide">
  <div class="taskcard" id="taskCard">
    <div class="trow"><span class="spin"></span><b id="taskTitle">正在执行</b></div>
    <div class="tprog" id="taskProg">准备中…</div>
    <div class="ttime" id="taskTime"></div>
    <div class="tbtns">
      <button type="button" id="taskBg">后台运行</button>
      <button type="button" id="taskClose" class="primary hide">关闭</button>
    </div>
  </div>
</div>
<button type="button" id="taskPill" class="taskpill hide">⟳ <span id="taskPillTxt">任务运行中</span></button>
'''
h = h[:mB] + DOM + h[mB:]

# ---------- ③ runTask 改用弹窗 ----------
m = re.search(r"  /\* ===== 任务条：把长任务包起来[\s\S]*?\n  window\.__om3runTask = runTask;\n", h)
assert m, 'runTask block not found'
NEW = r'''  /* ===== 任务弹窗：中央显示进度；可"后台运行"隐藏，右下角气泡随时再打开 ===== */
  var _run = { busy: false, t0: 0, timer: 0, label: '', last: '', ok: null };
  function taskEl(id){ return document.getElementById(id); }
  function taskModalShow(show){
    var m = taskEl('taskMask');
    if(!m) return;
    if(show) m.classList.remove('hide'); else m.classList.add('hide');
  }
  function taskPill(state, txt){
    var p = taskEl('taskPill');
    if(!p) return;
    p.classList.remove('hide', 'ok', 'err');
    if(state) p.classList.add(state);
    var t = taskEl('taskPillTxt');
    if(t) t.textContent = txt;
  }
  function taskPillHide(){ var p = taskEl('taskPill'); if(p) p.classList.add('hide'); }
  function taskPaint(){
    var card = taskEl('taskCard');
    if(card){ card.className = 'taskcard' + (_run.ok === true ? ' ok' : (_run.ok === false ? ' err' : '')); }
    var t = taskEl('taskTitle');
    if(t) t.textContent = (_run.ok === null ? '正在执行：' : (_run.ok ? '✅ 完成：' : '❌ 失败：')) + _run.label;
    var pr = taskEl('taskProg');
    if(pr) pr.textContent = _run.last || '准备中…';
    var tm = taskEl('taskTime');
    if(tm) tm.textContent = _run.t0 ? ('已用 ' + Math.round((Date.now() - _run.t0) / 1000) + ' 秒') : '';
    var bg = taskEl('taskBg'), cl = taskEl('taskClose');
    if(bg) bg.style.display = (_run.ok === null) ? '' : 'none';
    if(cl) cl.style.display = (_run.ok === null) ? 'none' : '';
  }
  function taskSay(line, state){
    _run.last = line || _run.last;
    if(state === 'ok') _run.ok = null;
    taskPaint();
    if(_run.ok === null) taskPill(null, _run.last.slice(0, 40) || '任务运行中');
  }
  window.__om3taskSay = taskSay;
  async function runTask(label, fn){
    if(_run.busy){ toastMsg('还有一个任务在跑：' + _run.label + '（点右下角气泡看进度）'); taskModalShow(true); return false; }
    _run.busy = true; _run.t0 = Date.now(); _run.label = label; _run.last = '准备中…'; _run.ok = null;
    taskModalShow(true); taskPillHide(); taskPaint();
    clearInterval(_run.timer);
    _run.timer = setInterval(function(){
      taskPaint();
      if(_run.ok === null && taskEl('taskMask').classList.contains('hide')) taskPill(null, _run.last.slice(0, 40) || '任务运行中');
    }, 1000);
    var ok = true, msg = '';
    try{ await fn(function(step, total){ taskSay(total ? ('进度 ' + step + '/' + total) : ('步骤 ' + step), 'progress'); }); }
    catch(e){ ok = false; msg = (e && e.message) ? e.message : String(e); }
    clearInterval(_run.timer);
    _run.ok = ok;
    if(!ok) _run.last = (_run.last ? _run.last + '　' : '') + msg;
    taskPaint();
    taskPill(ok ? 'ok' : 'err', (ok ? '✅ 完成：' : '❌ 失败：') + _run.label + '（点这里看详情）');
    _run.busy = false; _run.t0 = 0;
    return ok;
  }
  window.__om3runTask = runTask;
  /* 弹窗按钮 */
  (function(){
    var bg = taskEl('taskBg'), cl = taskEl('taskClose'), pill = taskEl('taskPill');
    if(bg) bg.addEventListener('click', function(){ taskModalShow(false); taskPill(null, _run.last.slice(0, 40) || '任务运行中'); });
    if(cl) cl.addEventListener('click', function(){ taskModalShow(false); taskPillHide(); });
    if(pill) pill.addEventListener('click', function(){ taskModalShow(true); taskPaint(); });
  })();
'''
h = h[:m.start()] + NEW + h[m.end():]

open(P, 'w', encoding='utf-8', newline='').write(h)
print('任务弹窗（中央 + 后台运行 + 气泡再打开）已加（+%d 字节）' % (len(h) - n0))
