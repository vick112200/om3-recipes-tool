# -*- coding: utf-8 -*-
"""底栏「写入/记录」点了没反应 —— 真因是 showStep 的守卫（未连接时 n>=2 强制退回 1）
   修法：保留守卫，但把"为什么不能进"明确告诉用户；高亮按"实际到达的步骤"显示
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

old = """    var ds = btn.getAttribute('data-dstep');
    if(ds){
      /* 派发到"已有的步骤按钮"（data-step），走原有切换逻辑；找不到再兜底 showStep */
      var tgt = document.querySelector('[data-step="' + ds + '"]');
      if(tgt && tgt !== btn){
        try{ tgt.click(); }catch(err){}
        log('已切换到：' + String(tgt.textContent || '').trim().slice(0, 14));
      } else {
        try{ showStep(Number(ds)); log('已切换到第 ' + ds + ' 步'); }
        catch(err){ log('切到第 ' + ds + ' 步失败：' + (err && err.message ? err.message : err), 'err'); }
      }
      document.querySelectorAll('#barD button[data-dstep]').forEach(function(b){ b.classList.toggle('on', b === btn); });
    }"""
assert h.count(old) == 1, h.count(old)

new = """    var ds = btn.getAttribute('data-dstep');
    if(ds){
      var n = Number(ds);
      var camOn = document.body.classList.contains('cam-on');
      var needConn = (n >= 2 && !camOn);          /* showStep 内部就是这么守的 */
      try{ showStep(n); }catch(err){ log('切换步骤出错：' + (err && err.message ? err.message : err), 'err'); }
      var actual = needConn ? 1 : n;             /* 被守卫拦下时，实际到达的是第 1 步 */
      document.querySelectorAll('#barD button[data-dstep]').forEach(function(b){
        b.classList.toggle('on', b.getAttribute('data-dstep') === String(actual));
      });
      if(needConn){
        var nm = (typeof STEPNAME !== 'undefined' && STEPNAME[n]) ? STEPNAME[n] : ('第' + n + '步');
        log('[提示] 还没连上相机 —— 「' + nm + '」需要先连接（已带你去第①步：连接）', 'warn');
        toastMsg('先连接相机才能用「' + nm + '」');
        window.__om3lastBlocked = { step: n, at: Date.now() };
      } else {
        log('已切换到：' + ((typeof STEPNAME !== 'undefined' && STEPNAME[n]) || ('第' + n + '步')));
      }
    }"""
h = h.replace(old, new, 1)

# 让"被拦下"的提示也能浮到眼前：显示在连接页顶部的一行提示（不是藏在 camGateOut 里）
anchor = "  window.__om3applyModule = applyModule;"
assert h.count(anchor) == 1
h = h.replace(anchor, anchor + """
  /* 被守卫拦下（没连相机就想备份/写入/记录）→ 在连接页顶部显示醒目提示 */
  setInterval(function(){
    try{
      var b = window.__om3lastBlocked;
      if(!b) return;
      if(Date.now() - b.at > 6000){ window.__om3lastBlocked = null; return; }
      var box = document.getElementById('camRun');
      if(box && !box.textContent.indexOf){ /* 保留原内容 */ }
      var el = document.getElementById('gStatusBar');
      if(el) el.textContent = '📷 未连接（先连相机才能' + ((typeof STEPNAME !== 'undefined' && STEPNAME[b.step]) || '继续') + '）';
    }catch(e){}
  }, 1000);""", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('守卫反馈已加（%+d 字节）' % (len(h) - n0))
