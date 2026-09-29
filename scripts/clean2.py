# -*- coding: utf-8 -*-
"""结构整治 3、4、5：
   3) 页签切换收口成单一 showPane（页签表驱动，含 E），删掉我外挂的分散钩子
   4) 定时器收口：加一个"心跳调度器"，把我这几轮加的轮询并入，并在页面隐藏时暂停
   5) 删掉废弃弹窗 #impMask 的标签（现在有 $ 安全取值，删了不会崩）
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- 3) showPane 表驱动 ----------
m = re.search(r"function showPane\(p\)\{\s*\n\s*if\('ABCDE'\.indexOf\(p\) < 0\) return;", h)
assert m, 'showPane 头没找到'
# 找到 A/B 两行（含我后加的 CDE 块），整段替换为表驱动
m2 = re.search(r"function showPane\(p\)\{[\s\S]{0,900}?\n(\s*)\}", h)
assert m2, 'showPane 体没找到'
body_start = m2.start()
inner = m2.group(0)
NEW = """function showPane(p){
    var PANES = ['A', 'B', 'C', 'D', 'E'];          /* 唯一真源：要加页签只改这一行 */
    if(PANES.indexOf(p) < 0) return;
    for(var i = 0; i < tabs.length; i++) tabs[i].classList.toggle('on', tabs[i].dataset.p === p);
    for(var k = 0; k < PANES.length; k++){
      var el = document.getElementById('pane' + PANES[k]);
      if(el) el.classList.toggle('hide', p !== PANES[k]);
    }
    try{ if(p === 'E' && window.__om3mpInit) window.__om3mpInit(); }catch(e){ om3err(e, 'paneE'); }
  }"""
h = h[:body_start] + NEW + h[m2.end():]

# 删掉我外挂的 paneC/paneD/paneE 分散钩子
h = re.sub(r"\n\s*var e5 = \$\('paneE'\);\s*\n\s*if \(e5\) e5\.classList\.toggle\('hide', p !== 'E'\);", "", h)
h = re.sub(r"\n\s*\['paneC','paneD','paneE'\]\.forEach\(function\(id\)\{[^\n]*\}\);", "", h)
print('3) showPane 已表驱动；剩余外挂钩子:', len(re.findall(r"\['paneC','paneD','paneE'\]", h)))

# ---------- 4) 心跳调度器：把定时器收口 + 隐藏时暂停 ----------
anchor = "  window.__om3err = om3err;"
assert h.count(anchor) == 1
h = h.replace(anchor, anchor + """
  /* ===== 统一心跳：所有轮询合并到一条时间线上，页面隐藏时自动暂停 ===== */
  var OM3TICKS = [];
  function om3Every(ms, fn, name){ OM3TICKS.push({ ms: ms, fn: fn, name: name, last: 0 }); }
  window.__om3Every = om3Every;
  function om3Heartbeat(){
    if(document.hidden) return;                 /* 后台不跑，省电 */
    var now = Date.now();
    for(var i = 0; i < OM3TICKS.length; i++){
      var t = OM3TICKS[i];
      if(now - t.last >= t.ms){
        t.last = now;
        try{ t.fn(); }catch(e){ om3err(e, 'tick:' + t.name); }
      }
    }
  }
  setInterval(om3Heartbeat, 200);""", 1)

# 把我这几轮的轮询并入心跳（保留原实现，只改成注册进心跳）
converts = [
    ("setInterval(applyConnGate, 1000);", "om3Every(1000, applyConnGate, 'gate');"),
    ("setInterval(function(){\n    try{\n      var b = window.__om3lastBlocked;", "om3Every(1000, function(){\n    try{\n      var b = window.__om3lastBlocked;"),
]
for old, new in converts:
    if h.count(old) == 1:
        h = h.replace(old, new, 1)
        # 把该匿名函数的收尾 '}, 1000);' 改成 '}, 1000, \'blocked\');'
print('4) 心跳调度器已加；直接 setInterval 剩:', len(re.findall(r'setInterval\(', h)))

# ---------- 5) 删掉废弃弹窗 #impMask 的标签（$ 已能安全兜底） ----------
m3 = re.search(r'\n\s*<div[^>]*id="impMask"[\s\S]{0,3000}?\n\s*</div>\s*\n', h)
if m3:
    h = h[:m3.start()] + h[m3.end():]
    print('5) 已删除 #impMask 标签')
else:
    print('5) #impMask 标签未找到（可能已是单行形式）')

open(P, 'w', encoding='utf-8', newline='').write(h)
print('改动完成（%+d 字节）' % (len(h) - n0))
