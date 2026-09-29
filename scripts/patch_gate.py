# -*- coding: utf-8 -*-
"""把"未连接时的弹窗提示"改成"置灰不可点"：
   · 连接相机底栏：未连接时 安全备份/写入/记录 三项置灰（点不动）
   · 页内需要相机的动作按钮（读取并备份 / 用备份恢复 / 预览 / 写入）同样置灰
   · 底栏下方给一行常驻说明，说明为什么灰
   · 连上后自动恢复可点（1 秒轮询，纯本地，不做原生调用）
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# 样式
k = h.find('</style>')
assert k > 0
h = h[:k] + """
/* 未连接相机 → 相关按钮置灰、点不动（替代弹窗提示） */
.dis,.dis:active{opacity:.42;filter:grayscale(.9);pointer-events:none !important}
.gatehint{display:none;font-size:12px;color:#8b93a1;text-align:center;padding:4px 8px 2px}
.gatehint.show{display:block}
""" + h[k:]

# 底栏下面加一行说明
old_bar = '<div class="barD" id="barD">'
assert h.count(old_bar) == 1
h = h.replace(old_bar, '<div class="gatehint" id="gateHintD">连接相机后，才能用「安全备份 / 写入 / 记录」</div>\n' + old_bar, 1)

# 逻辑：置灰开关
anchor = "  window.__om3applyModule = applyModule;"
assert h.count(anchor) == 1
h = h.replace(anchor, anchor + """
  /* 未连接 → 置灰"需要相机"的按钮（不再弹窗） */
  var GATE_TEXTS = ['读取并备份', '用这份备份恢复相机', '预览', '写入相机', '写入当前配方', '写回备份'];
  function applyConnGate(){
    try{
      var on = document.body.classList.contains('cam-on');
      document.querySelectorAll('#barD button[data-dstep]').forEach(function(b){
        var n = Number(b.getAttribute('data-dstep'));
        b.classList.toggle('dis', n >= 2 && !on);
      });
      document.querySelectorAll('[data-step]').forEach(function(b){
        var n = Number(b.getAttribute('data-step'));
        if(n >= 2) b.classList.toggle('dis', !on);
      });
      var pd = document.getElementById('paneD');
      if(pd){
        pd.querySelectorAll('button').forEach(function(b){
          var t = (b.textContent || '').trim();
          var need = GATE_TEXTS.some(function(k2){ return t.indexOf(k2) >= 0; });
          if(need) b.classList.toggle('dis', !on);
        });
      }
      var gh = document.getElementById('gateHintD');
      if(gh) gh.classList.toggle('show', !on);
    }catch(e){}
  }
  window.__om3connGate = applyConnGate;
  setInterval(applyConnGate, 1000);
  setTimeout(applyConnGate, 1200);""", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('置灰机制已加（%+d 字节）' % (len(h) - n0))
