# -*- coding: utf-8 -*-
"""骨架重构：
   顶层三大模块（内置配方 / 我的配方 / 连接相机）
   · 内置配方：第二行放搜索按钮；底部三切换（原版方案/优化版/场景对比）
   · 我的配方：已有底部四切换（保持）
   · 连接相机：底部四切换（连接/安全备份/写入/记录）→ 对应原有 4 步
   · 常驻相机状态条（顶栏下方）
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- ① 顶栏：改成三大模块 ----------
m = re.search(r'<div class="topbar">.*?</div></div>', h, re.S)
assert m, 'topbar not found'
OLD = m.group(0)
NEW = '''<div class="topbar">
  <div class="tb">
    <span class="tbname">OM-3 色彩配方手册</span>
    <span class="tabs mod">
      <button type="button" data-p="A" class="on" id="tabBuiltin">内置配方</button>
      <button type="button" data-p="E" id="tabMine">我的配方</button>
      <button type="button" data-p="D" id="tabCam">连接相机</button>
    </span>
  </div>
</div>
<div id="gStatusBar" class="gstatus">● 未连接相机</div>
<div id="row2" class="row2"><button id="tocbtn" class="iconbtn" type="button" title="搜索 / 目录">🔍 搜索</button></div>'''
h = h[:m.start()] + NEW + h[m.end():]

# 顶栏样式补充 + 常驻状态条 + 底部切换栏样式
k = h.find('</style>')
assert k > 0
h = h[:k] + """
/* ---------- 三大模块顶栏 / 常驻状态条 / 底部小切换 ---------- */
.tabs.mod button{font-size:13.5px;padding:7px 10px}
.gstatus{position:sticky;top:0;z-index:60;padding:6px 12px;font-size:12.5px;background:#151515;border-bottom:1px solid #242424;color:#9aa3b2}
.gstatus.on{color:#bdf0cf;background:#121a14}
.row2{display:flex;gap:8px;align-items:center;padding:8px 12px 2px}
.row2 .iconbtn{flex:1;max-width:220px;justify-content:center;padding:9px 12px;border-radius:9px;border:1px solid #333;background:#1c1c1c;color:#ddd;font-size:13px}
.barABC,.barD{display:none;gap:6px;position:sticky;bottom:0;z-index:55;background:#101010;border-top:1px solid #242424;padding:8px 4px;margin-top:10px}
.barABC.show,.barD.show{display:flex}
.barABC button,.barD button{flex:1;padding:9px 4px;border-radius:9px;border:1px solid transparent;background:transparent;color:#9aa3b2;font-size:12.5px}
.barABC button.on,.barD button.on{background:#1e2636;border-color:#33507e;color:#cfe0ff;font-weight:600}
""" + h[k:]

# ---------- ② 底部两条切换栏（插在 body 末尾） ----------
mB = h.rfind('</body>')
assert mB > 0
BARS = '''
<!-- 内置配方的底部三切换 -->
<div class="barABC" id="barABC">
  <button type="button" data-p="A" class="on">原版方案</button>
  <button type="button" data-p="B">优化版</button>
  <button type="button" data-p="C">场景对比</button>
</div>
<!-- 连接相机的底部四切换（对应原有 4 步） -->
<div class="barD" id="barD">
  <button type="button" data-dstep="1" class="on">连接</button>
  <button type="button" data-dstep="2">安全备份</button>
  <button type="button" data-dstep="3">写入</button>
  <button type="button" data-dstep="4">记录</button>
</div>
'''
h = h[:mB] + BARS + h[mB:]

# ---------- ③ 逻辑：模块/子切换/状态条 ----------
anchor = "  /* ===== 蓝牙（实验）：扫描 + 调试日志 ====="
assert h.count(anchor) == 1, h.count(anchor)
LOGIC = '''  /* ===== 骨架：三模块 + 模块内底部切换 + 常驻状态条 ===== */
  function gStatus(txt, on){
    var e = document.getElementById('gStatusBar');
    if(!e) return;
    e.textContent = (on ? '◉ ' : '● ') + txt;
    e.classList.toggle('on', !!on);
  }
  window.__om3gStatus = gStatus;
  function applyModule(p){
    var abc = document.getElementById('barABC'), bd = document.getElementById('barD'), r2 = document.getElementById('row2');
    if(abc) abc.classList.toggle('show', p === 'A' || p === 'B' || p === 'C');
    if(bd) bd.classList.toggle('show', p === 'D');
    if(r2) r2.style.display = (p === 'A' || p === 'B' || p === 'C') ? 'flex' : 'none';
    document.querySelectorAll('#barABC button[data-p]').forEach(function(b){ b.classList.toggle('on', b.getAttribute('data-p') === p); });
    document.querySelectorAll('.tabs.mod button[data-p]').forEach(function(b){
      var tp = b.getAttribute('data-p');
      var on = (tp === p) || (tp === 'A' && (p === 'A' || p === 'B' || p === 'C'));
      b.classList.toggle('on', on);
    });
  }
  window.__om3applyModule = applyModule;
  /* 顶栏 / 底部栏统一走委托，互斥切换 */
  document.addEventListener('click', function(e){
    var t = e.target, btn = null;
    while(t && t !== document){
      if(t.getAttribute && (t.getAttribute('data-p') || t.getAttribute('data-dstep'))){ btn = t; break; }
      t = t.parentNode;
    }
    if(!btn) return;
    var dp = btn.getAttribute('data-p');
    if(dp){
      /* 复用原有页签逻辑：模拟点击顶栏对应按钮 */
      var top = document.getElementById(dp === 'E' ? 'tabMine' : (dp === 'D' ? 'tabCam' : 'tabBuiltin'));
      if(top && top !== btn){ top.click(); }
      setTimeout(function(){ applyModule(dp); }, 20);
      return;
    }
    var ds = btn.getAttribute('data-dstep');
    if(ds){
      try{ showStep(Number(ds)); }catch(err){}
      document.querySelectorAll('#barD button[data-dstep]').forEach(function(b){ b.classList.toggle('on', b === btn); });
    }
  }, true);
  /* 状态条同步：每 1.5 秒把连接相机页里的状态抄到常驻条 */
  setInterval(function(){
    try{
      var src = document.getElementById('camStatusTxt') || document.getElementById('camWifiState');
      var ssid = '', on = document.body.classList.contains('cam-on');
      if(src){ ssid = (src.textContent || '').replace(/\\s+/g, ' ').slice(0, 40); }
      gStatus(on ? ('已连接 ' + (ssid || '相机')) : '未连接相机（点这里去连接）', on);
    }catch(e){}
  }, 1500);
  document.addEventListener('click', function(e){
    var t = e.target;
    if(t && t.id === 'gStatusBar'){ try{ document.getElementById('tabCam').click(); }catch(x){} }
  }, true);
  setTimeout(function(){
    try{
      var p0 = 'A';
      document.querySelectorAll('.tabs.mod button[data-p]').forEach(function(b){ if(b.classList.contains('on')) p0 = b.getAttribute('data-p'); });
      applyModule(p0);
    }catch(e){}
  }, 600);

''' + anchor
h = h.replace(anchor, LOGIC, 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('骨架重构已写入（+%d 字节）' % (len(h) - n0))
