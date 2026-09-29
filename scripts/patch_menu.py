# -*- coding: utf-8 -*-
"""导入相机页顶部瘦身：状态条 + 一个「☰」菜单（里面放 3 个步骤 + 日志操作），
原来那两行（日志条、步骤条）去掉。
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
P = TMP + r'\app\base.html'
h = open(P, encoding='utf-8').read()
open(TMP + r'\app\base.before_menu.html', 'w', encoding='utf-8', newline='').write(h)

# ---------- 1. 顶部结构 ----------
i = h.find('<div class="camstatus">')
j = h.find('<div class="camview" id="camV1">')
assert 0 < i < j
old_top = h[i:j]
assert 'camlogbar' in old_top and 'camsteps' in old_top
NEW_TOP = '''<div class="camhead">
  <div class="camstatus">
    <span id="camStWifi" class="cs">Wi-Fi：读取中…</span>
    <span id="camStCam" class="cs">相机：未检测</span>
    <span id="camStBak" class="cs">备份：无</span>
  </div>
  <div class="cammenu">
    <button type="button" id="camMenuBtn" class="cammbtn">☰ ① 连接相机</button>
    <div class="cammdrop hide" id="camMenuDrop">
      <button type="button" data-step="1">① 连接相机</button>
      <button type="button" data-step="2">② 备份设置</button>
      <button type="button" data-step="3">③ 写入配方</button>
      <div class="cammsep"></div>
      <button type="button" data-act="copylog">复制日志</button>
      <button type="button" data-act="dllog">下载日志文件</button>
      <button type="button" data-act="clearlog">清空日志</button>
    </div>
  </div>
</div>

'''
h = h[:i] + NEW_TOP + h[j:]
print('顶部：状态条 + ☰ 菜单（步骤和日志都在里面）')

# ---------- 2. CSS ----------
CSS_OLD = '.camstatus{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}\n.camstatus .cs{background:#1e1e1e;border:1px solid #2e2e2e;border-radius:20px;padding:5px 12px;font-size:12px;color:#9a9a9a}'
assert h.count(CSS_OLD) == 1
CSS_NEW = '''.camhead{display:flex;align-items:flex-start;gap:10px;justify-content:space-between;margin:0 0 14px}
.camstatus{display:flex;flex-wrap:wrap;gap:6px;flex:1 1 auto;min-width:0}
.camstatus .cs{background:#1e1e1e;border:1px solid #2e2e2e;border-radius:20px;padding:4px 10px;font-size:11.5px;color:#9a9a9a;white-space:nowrap}
.cammenu{position:relative;flex:0 0 auto}
.cammbtn{background:#2f8f74;color:#fff;border:0;border-radius:9px;padding:8px 13px;font-size:13px;font-weight:700;font-family:inherit;cursor:pointer;white-space:nowrap}
.cammdrop{position:absolute;right:0;top:110%;z-index:70;background:#1f1f1f;border:1px solid #333;border-radius:11px;padding:6px;min-width:190px;box-shadow:0 10px 30px rgba(0,0,0,.55)}
.cammdrop button{display:block;width:100%;text-align:left;background:transparent;border:0;color:#d6d6d6;border-radius:8px;padding:10px 12px;font-size:13.5px;font-family:inherit;cursor:pointer}
.cammdrop button:hover{background:#2a2a2a}
.cammdrop button.on{background:#2f8f74;color:#fff;font-weight:700}
.cammsep{height:1px;background:#333;margin:6px 4px}'''
h = h.replace(CSS_OLD, CSS_NEW, 1)
# 去掉旧的日志条/步骤条样式
for dead in ['.camlogbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px}\n'
             '.camlogbar button{background:#242424;border:1px solid #3a3a3a;color:#8fd8c2;border-radius:8px;padding:7px 13px;font-size:12.5px;font-family:inherit;cursor:pointer}\n',
             '.camsteps{display:flex;gap:6px;margin:0 0 16px}\n',
             '.camsteps button{flex:1;background:#242424;border:1px solid #3a3a3a;color:#aaa;border-radius:9px;padding:10px 6px;font-size:13.5px;font-weight:600;font-family:inherit;cursor:pointer}\n',
             '.camsteps button.on{background:#2f8f74;border-color:#2f8f74;color:#fff}\n']:
    if dead in h:
        h = h.replace(dead, '', 1)
print('CSS：菜单样式已加，旧的两行样式已清')

# ---------- 3. JS ----------
OLD_JS = """  /* 顶部常驻：复制日志 / 跳到日志（原来只有第 3 步底部有，扫码失败时够不着） */
  var c2 = document.getElementById('camCopyLog2');
  if(c2) c2.addEventListener('click', function(){ document.getElementById('camCopyLog').click(); });
  var sj = document.getElementById('camShowLog');
  if(sj) sj.addEventListener('click', function(){
    showStep(3);
    setTimeout(function(){ document.getElementById('camOut3').scrollIntoView({block:'center'}); }, 120);
  });

  /* ================= 三步向导 ================= */
  var stepBtns = document.querySelectorAll('#camSteps button');
  function showStep(n){
    for(var i=0;i<stepBtns.length;i++)
      stepBtns[i].classList.toggle('on', stepBtns[i].getAttribute('data-s') === String(n));
    for(var k=1;k<=3;k++)
      document.getElementById('camV'+k).classList.toggle('hide', k !== n);
    var top = document.getElementById('camSteps').getBoundingClientRect().top + window.pageYOffset - 56;
    window.scrollTo(0, top > 0 ? top : 0);
  }
  for(var sb=0; sb<stepBtns.length; sb++)
    stepBtns[sb].addEventListener('click', function(){ showStep(+this.getAttribute('data-s')); });"""
assert h.count(OLD_JS) == 1
NEW_JS = """  /* ================= 顶部菜单：3 个步骤 + 日志操作 ================= */
  var STEPNAME = {1:'① 连接相机', 2:'② 备份设置', 3:'③ 写入配方'};
  var menuBtn = document.getElementById('camMenuBtn');
  var menuDrop = document.getElementById('camMenuDrop');
  function showStep(n){
    for(var k=1;k<=3;k++) document.getElementById('camV'+k).classList.toggle('hide', k !== n);
    if(menuBtn) menuBtn.textContent = '☰ ' + (STEPNAME[n] || '菜单');
    if(menuDrop){
      var it = menuDrop.querySelectorAll('[data-step]');
      for(var i=0;i<it.length;i++) it[i].classList.toggle('on', +it[i].getAttribute('data-step') === n);
      menuDrop.classList.add('hide');
    }
    var host = document.getElementById('paneD');
    if(host){
      var t = host.querySelector('h1');
      var top = (t ? t.getBoundingClientRect().top : host.getBoundingClientRect().top) + window.pageYOffset - 56;
      window.scrollTo(0, top > 0 ? top : 0);
    }
  }
  window.__camStep = showStep;
  function closeMenu(){ if(menuDrop) menuDrop.classList.add('hide'); }
  if(menuBtn && menuDrop){
    menuBtn.addEventListener('click', function(e){
      e.stopPropagation();
      menuDrop.classList.toggle('hide');
    });
    document.addEventListener('click', function(e){
      if(menuDrop.classList.contains('hide')) return;
      if(e.target === menuBtn || menuDrop.contains(e.target)) return;
      closeMenu();
    });
    menuDrop.addEventListener('click', function(e){
      var b = e.target.closest ? e.target.closest('button') : null;
      if(!b) return;
      var s = b.getAttribute('data-step'), a = b.getAttribute('data-act');
      if(s){ showStep(+s); return; }
      if(a === 'copylog') document.getElementById('camCopyLog').click();
      else if(a === 'dllog') document.getElementById('camDlLog').click();
      else if(a === 'clearlog') document.getElementById('camClearLog').click();
      closeMenu();
    });
  }"""
h = h.replace(OLD_JS, NEW_JS, 1)
print('JS：菜单逻辑已就位（步骤 + 复制/下载/清空日志）')

open(P, 'w', encoding='utf-8', newline='').write(h)
print('完成，base.html %.1f KB' % (len(h.encode('utf-8')) / 1024))
