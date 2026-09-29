# -*- coding: utf-8 -*-
"""① 自绘弹窗 om3Ask（替代系统 confirm/prompt）
   ② 「我的配方」重构：底部切换栏（方案/读取/档位/文件）+ 每页专属操作行
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ============ ① 自绘弹窗：CSS + DOM + 实现 ============
k = h.find('</style>')
assert k > 0
h = h[:k] + """
/* ---------- 自绘弹窗 ---------- */
.omask{position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:9700}
.omask.hide{display:none !important}
.ocard{width:min(90vw,400px);background:#181818;border:1px solid #2e2e2e;border-radius:14px;padding:16px;box-shadow:0 14px 44px rgba(0,0,0,.65)}
.ocard h4{margin:0 0 6px;font-size:15px;color:#f2f2f2}
.ocard .obody{font-size:13px;color:#b9c0cb;line-height:1.55;margin-bottom:8px;word-break:break-all}
.ocard label{display:block;font-size:12.5px;color:#9aa3b2;margin:10px 0 5px}
.ocard input,.ocard textarea{width:100%;box-sizing:border-box;padding:10px;border-radius:9px;border:1px solid #333;background:#111;color:#eee;font-size:13.5px}
.ocard textarea{min-height:64px;resize:vertical}
.obtns{display:flex;gap:9px;margin-top:15px}
.obtns button{flex:1;padding:11px;border-radius:9px;border:1px solid #333;background:#232323;color:#e8e8e8;font-size:13.5px}
.obtns button.primary{background:#2b5cff;border-color:#2b5cff;color:#fff;font-weight:600}
.obtns button.danger{background:#7a2a2a;border-color:#7a2a2a;color:#fff;font-weight:600}

/* ---------- 我的配方：底部切换栏 ---------- */
.mpbar{display:flex;gap:6px;position:sticky;bottom:0;background:#101010;border-top:1px solid #242424;padding:8px 4px;margin-top:10px}
.mpbar button{flex:1;padding:9px 4px;border-radius:9px;border:1px solid transparent;background:transparent;color:#9aa3b2;font-size:12.5px}
.mpbar button.on{background:#1e2636;border-color:#33507e;color:#cfe0ff;font-weight:600}
.mprow{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px}
.mpsub{display:none}
.mpsub.on{display:block}
""" + h[k:]

# 弹窗 DOM
mB = h.rfind('</body>')
assert mB > 0
h = h[:mB] + '''
<!-- 自绘弹窗 -->
<div id="omask" class="omask hide">
  <div class="ocard">
    <h4 id="otitle">提示</h4>
    <div class="obody" id="obody"></div>
    <div id="ofields"></div>
    <div class="obtns">
      <button type="button" id="ocancel">取消</button>
      <button type="button" id="ook" class="primary">确定</button>
    </div>
  </div>
</div>
''' + h[mB:]

# 弹窗实现（挂在「我的配方」段前）
anchor = "  /* ================= 「我的配方」：方案库 + 档位管理 ================= */"
assert h.count(anchor) == 1, h.count(anchor)
ASK = r'''  /* ===== 自绘弹窗：om3Ask({title, body, fields:[{label,value,multiline}], okText, danger}) → Promise ===== */
  function om3Ask(opt){
    opt = opt || {};
    return new Promise(function(resolve){
      var mask = document.getElementById('omask');
      if(!mask){ resolve(opt.fields ? null : false); return; }
      document.getElementById('otitle').textContent = opt.title || '提示';
      document.getElementById('obody').textContent = opt.body || '';
      var box = document.getElementById('ofields');
      box.innerHTML = '';
      var fields = opt.fields || [];
      fields.forEach(function(f, i){
        var id = 'of' + i;
        var lb = document.createElement('label');
        lb.textContent = f.label || ('输入 ' + (i + 1));
        var el = document.createElement(f.multiline ? 'textarea' : 'input');
        el.id = id; el.value = f.value || '';
        if(!f.multiline) el.type = 'text';
        box.appendChild(lb); box.appendChild(el);
      });
      var ok = document.getElementById('ook'), cancel = document.getElementById('ocancel');
      ok.textContent = opt.okText || '确定';
      ok.className = opt.danger ? 'danger' : 'primary';
      function done(val){
        mask.classList.add('hide'); mask.style.display = 'none';
        ok.onclick = null; cancel.onclick = null; mask.onclick = null;
        resolve(val);
      }
      ok.onclick = function(){
        if(!fields.length){ done(true); return; }
        if(fields.length === 1){ done(document.getElementById('of0').value); return; }
        var out = [];
        for(var i = 0; i < fields.length; i++) out.push(document.getElementById('of' + i).value);
        done(out);
      };
      cancel.onclick = function(){ done(opt.fields ? null : false); };
      mask.onclick = function(e){ if(e.target === mask) done(opt.fields ? null : false); };
      mask.classList.remove('hide'); mask.style.display = 'flex';
      setTimeout(function(){ var f = document.getElementById('of0'); if(f) f.focus(); }, 50);
    });
  }
  window.__om3ask = om3Ask;

''' + anchor
h = h.replace(anchor, ASK, 1)

# ============ ② paneE 重构：底部切换栏 ============
m = re.search(r'<!-- ============ 我的配方 ============ -->\s*<div id="paneE"[\s\S]*?\n</div>\n', h)
assert m, 'paneE block not found'
PANEL = '''<!-- ============ 我的配方 ============ -->
<div id="paneE" class="pane hide">
  <h1>我的配方</h1>

  <!-- 子页：方案 -->
  <div class="mpsub on" id="mpsub-sets">
    <div class="mpcard">
      <h3>我的方案 <span id="mpCount" style="color:#888;font-weight:400"></span></h3>
      <div id="mpList"></div>
    </div>
  </div>

  <!-- 子页：读取 -->
  <div class="mpsub" id="mpsub-read">
    <div class="mpcard">
      <h3>从相机读取并保存</h3>
      <div style="font-size:12.5px;color:#9aa3b2">把相机某个档位当前的 4 个色彩槽整套读回来，存成一套方案。</div>
      <div class="mpsel"><span style="font-size:13px;color:#aaa">读取档位</span><select id="mpReadTier"></select></div>
      <div class="mprow"><button type="button" id="mpRead" class="mpbtn primary">读取并保存为方案</button></div>
    </div>
  </div>

  <!-- 子页：档位 -->
  <div class="mpsub" id="mpsub-tiers">
    <div class="mpcard">
      <h3>档位管理</h3>
      <div style="font-size:12.5px;color:#9aa3b2;margin-bottom:6px">不是所有机器都有 5 个档位 —— 按你的机型增删改名，读取/写入都用这份列表。</div>
      <div id="mpTiers"></div>
      <div class="mprow"><button type="button" id="mpTierAdd" class="mpbtn">+ 添加档位</button><button type="button" id="mpTierReset" class="mpbtn">恢复默认</button></div>
    </div>
  </div>

  <!-- 子页：文件 -->
  <div class="mpsub" id="mpsub-file">
    <div class="mpcard">
      <h3>分享 / 导入</h3>
      <div style="font-size:12.5px;color:#9aa3b2">方案文件（.json）带名字和描述，方便分享；也支持导入官方 .oes（给 OM Workspace 用）。</div>
      <div class="mpsel"><span style="font-size:13px;color:#aaa">导入到</span><select id="mpImpSlot"><option value="1">槽 1</option><option value="2">槽 2</option><option value="3">槽 3</option><option value="4">槽 4</option></select></div>
      <div class="mprow"><button type="button" id="mpExportAll" class="mpbtn">导出全部方案（.json）</button><button type="button" id="mpImportFile" class="mpbtn primary">导入方案文件</button></div>
      <div id="mpFileOut" class="camout" style="margin-top:8px">导出后可分享给别人；对方导入 → 选槽位 → 写入相机。</div>
    </div>
  </div>

  <!-- 底部切换栏 -->
  <div class="mpbar">
    <button type="button" data-mp="sets" class="on">方案</button>
    <button type="button" data-mp="read">读取</button>
    <button type="button" data-mp="tiers">档位</button>
    <button type="button" data-mp="file">文件</button>
  </div>
</div>
'''
h = h[:m.start()] + PANEL + h[m.end():]

# 子页切换逻辑（加在页签联动那段之后）
anchor2 = "  /* ================= 「我的配方」：方案库 + 档位管理 ================= */"
assert h.count(anchor2) == 1
h = h.replace(anchor2, '''  /* 「我的配方」子页切换：底部栏 + 每页专属操作行 */
  function mpTab(name){
    ['sets', 'read', 'tiers', 'file'].forEach(function(n){
      var sec = document.getElementById('mpsub-' + n);
      if(sec) sec.classList.toggle('on', n === name);
    });
    document.querySelectorAll('.mpbar button[data-mp]').forEach(function(b){
      b.classList.toggle('on', b.getAttribute('data-mp') === name);
    });
    if(name === 'sets') try{ mpRender(); }catch(e){}
    if(name === 'tiers') try{ mpTierUI(); mpFillTierSelect(); }catch(e){}
    if(name === 'read') try{ mpFillTierSelect(); }catch(e){}
  }
  window.__om3mpTab = mpTab;
  document.addEventListener('click', function(e){
    var t = e.target, b = null;
    while(t && t !== document){ if(t.getAttribute && t.getAttribute('data-mp')){ b = t; break; } t = t.parentNode; }
    if(b) mpTab(b.getAttribute('data-mp'));
  }, true);

''' + anchor2, 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('自绘弹窗 + 底部切换栏 已加（+%d 字节）' % (len(h) - n0))
