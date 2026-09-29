# -*- coding: utf-8 -*-
"""① 修「我的配方」初始化（DOM 就绪后再渲染）+ 页签联动
   ② 分享格式改回 JSON，并支持 命名 / 描述 / 删除 等管理
   ③ .oes 保留为"每个槽单独导出"的可选按钮
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- ① 初始化：改成 DOM 就绪后执行 ----------
m = re.search(r"  /\* 初始化 \*/\n  try\{\n.*?\n  \}catch\(e\)\{[^\n]*\n", h, re.S)
assert m, 'init block not found'
INIT = '''  /* 初始化（必须等 DOM 就绪：面板在本脚本之后，之前直接调用会静默返回） */
  function mpInit(){
    try{
      mpFillTierSelect(); mpTierUI(); mpRender();
      function bind(id, fn){ var b = document.getElementById(id); if(b && !b.__om3bound){ b.__om3bound = true; b.addEventListener('click', fn); } }
      bind('mpRead', mpReadFromCamera);
      bind('mpExportAll', mpExportJsonAll);
      bind('mpImportFile', mpImportAny);
      bind('mpTierAdd', function(){ var a = tiersAll(); a.push('myset' + (a.length + 1)); tiersSave(a); mpTierUI(); mpFillTierSelect(); });
      bind('mpTierReset', function(){ if(confirm('恢复默认档位列表？')){ try{ localStorage.removeItem(TIERKEY); }catch(e){} mpTierUI(); mpFillTierSelect(); } });
      window.__om3mpRender = mpRender; window.__om3mpRead = mpReadFromCamera; window.__om3mpInit = mpInit;
      log('「我的配方」已就绪（' + tiersAll().length + ' 个档位，' + setsAll().length + ' 套方案）');
    }catch(e){ try{ log('「我的配方」初始化出错：' + (e && e.message ? e.message : e), 'err'); }catch(x){} }
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mpInit);
  else setTimeout(mpInit, 0);
'''
h = h[:m.start()] + INIT + h[m.end():]

# ---------- ① 页签联动：切到「我的配方」时隐藏其它面板 ----------
anchor_nav = "  /* ================= 「我的配方」：方案库 + 档位管理 ================= */"
assert h.count(anchor_nav) == 1, h.count(anchor_nav)
h = h.replace(anchor_nav, '''  /* 页签联动：切到「我的配方」时把其它面板收起来（并让其它页签切回来时收起本面板） */
  document.addEventListener('click', function(e){
    var t = e.target, btn = null;
    while(t && t !== document){ if(t.getAttribute && t.getAttribute('data-p')){ btn = t; break; } t = t.parentNode; }
    if(!btn) return;
    var p = btn.getAttribute('data-p');
    var ids = ['paneA', 'paneB', 'paneC', 'paneD', 'paneE'];
    ids.forEach(function(id){
      var el = document.getElementById(id);
      if(!el) return;
      var mine = (id === 'pane' + p);
      if(mine) el.classList.remove('hide');
      else if(p === 'E' || id === 'paneE') el.classList.add('hide');
    });
    if(p === 'E') setTimeout(mpInit, 30);
  }, true);

''' + anchor_nav, 1)

# ---------- ② JSON（带名字/描述）作为分享格式 ----------
old_exp_item = "        if(op === 'export'){ mpExportOes(s); return; }"
assert h.count(old_exp_item) == 1
h = h.replace(old_exp_item, """        if(op === 'export'){ mpExportOne(s); return; }
        if(op === 'oes'){ mpExportOes(s); return; }""", 1)

# 方案条目：加"描述"和"导出 .oes"按钮
old_r = """'<div class="r"><button data-i="' + idx + '" data-op="write">写入相机</button>' +
        '<button data-i="' + idx + '" data-op="export">导出</button>' +
        '<button data-i="' + idx + '" data-op="rename">改名</button>' +
        '<button data-i="' + idx + '" data-op="del" class="mpbtn danger" style="flex:none">删除</button></div>'"""
assert h.count(old_r) == 1, h.count(old_r)
h = h.replace(old_r, """'<div class="r"><button data-i="' + idx + '" data-op="write">写入相机</button>' +
        '<button data-i="' + idx + '" data-op="export">导出文件</button>' +
        '<button data-i="' + idx + '" data-op="rename">改名 / 描述</button>' +
        '<button data-i="' + idx + '" data-op="oes">导出 .oes</button>' +
        '<button data-i="' + idx + '" data-op="del" class="mpbtn danger" style="flex:none">删除</button></div>'""" , 1)

# 条目显示描述
h = h.replace("'<div class=\"s\">' + tierLabel(s.from || 'current') + '　·　' + used + '/4 槽有内容</div>'",
              "'<div class=\"s\">' + tierLabel(s.from || 'current') + '　·　' + used + '/4 槽有内容' + (s.desc ? ('<br>' + s.desc) : '') + '</div>'", 1)

# rename → 名称 + 描述
old_rn = """        if(op === 'rename'){
          var nm = prompt('方案名字：', s.name || '');
          if(nm){ arr[i].name = nm; setsSave(arr); mpRender(); }
          return;
        }"""
assert h.count(old_rn) == 1, h.count(old_rn)
h = h.replace(old_rn, """        if(op === 'rename'){
          var nm = prompt('方案名字：', s.name || '');
          if(nm === null) return;
          var ds = prompt('描述（可选，例如作者 / 风格 / 备注）：', s.desc || '');
          if(ds === null) ds = s.desc || '';
          arr[i].name = nm || s.name; arr[i].desc = ds;
          setsSave(arr); mpRender(); log('已更新方案：' + arr[i].name, 'ok');
          return;
        }""" , 1)

# 导出单套 → JSON（带名字/描述）
m_old = re.search(r"  /\* 导出一套方案：每个有内容的槽生成一个官方 \.oes 文件 \*/\n  function mpExportOes\(s\)\{.*?\n  \}\n", h, re.S)
assert m_old, 'mpExportOes not found'
h = h[:m_old.start()] + '''  /* 导出一套方案 → JSON（带名字/描述，方便分享与管理） */
  function mpExportOne(s){
    var pack = { app: 'OM-3 色彩配方手册', kind: 'om3-colorprofile', version: 2,
                 name: s.name || '未命名方案', desc: s.desc || '', from: s.from || '',
                 camera: s.camera || modelNow(), slots: s.slots };
    var fn = 'OM3-' + String(s.name || '方案').replace(/[\\/:*?"<>|\\s]/g, '_') + '.json';
    if(om3Download(fn, JSON.stringify(pack, null, 1))) log('✅ 已导出：' + fn + '（含名字/描述，可直接分享）', 'ok');
    var o = document.getElementById('mpFileOut'); if(o) o.textContent = '已导出：' + fn;
    toastMsg('已导出方案文件');
  }

  /* 可选：导出 .oes（给 OM Workspace 用；官方格式不含名字/描述） */
  function mpExportOes(s){
    var names = [];
    for(var q = 1; q <= 4; q++){
      var one = s.slots && s.slots[q];
      if(!one || !one.vivid) continue;
      var fn = oesName(one, (s.name || 'OM3方案') + '-槽' + q);
      if(om3Download(fn, oesBuild(one), 'text/xml')) names.push(fn);
    }
    if(!names.length){ log('这套方案里没有可导出的槽。', 'warn'); return; }
    log('✅ 已导出 ' + names.length + ' 个 .oes（官方格式，不含名字/描述）：' + names.join('、'), 'ok');
  }
''' + h[m_old.end():]

# 全部导出 → JSON
m_all = re.search(r"  function mpExportAll\(\)\{.*?\n  \}\n", h, re.S)
assert m_all, 'mpExportAll not found'
h = h[:m_all.start()] + '''  function mpExportJsonAll(){
    var a = setsAll();
    if(!a.length){ log('还没有方案可导出。', 'warn'); return; }
    var pack = { app: 'OM-3 色彩配方手册', kind: 'om3-colorprofile', version: 2, count: a.length,
                 sets: a.map(function(s){ return { name: s.name, desc: s.desc || '', from: s.from, camera: s.camera, slots: s.slots }; }) };
    var fn = 'OM3我的配方.json';
    if(om3Download(fn, JSON.stringify(pack, null, 1))){ log('✅ 已导出 ' + a.length + ' 套方案：' + fn, 'ok'); toastMsg('已导出 ' + a.length + ' 套'); }
  }
''' + h[m_all.end():]

# 导入：JSON 优先，也接受 .oes；保留名字与描述
m_imp = re.search(r"  function mpImportFile\(\)\{.*?\n  \}\n", h, re.S)
assert m_imp, 'mpImportFile not found'
h = h[:m_imp.start()] + '''  function mpImportAny(){
    var inp = document.getElementById('mpFile');
    if(!inp){
      inp = document.createElement('input'); inp.type = 'file'; inp.id = 'mpFile';
      inp.accept = '.json,.oes,application/json,text/xml'; inp.style.display = 'none';
      document.body.appendChild(inp);
      inp.addEventListener('change', function(){
        var f = inp.files && inp.files[0]; if(!f) return;
        var sel = document.getElementById('mpImpSlot');
        var toSlot = Number(sel ? sel.value : 1) || 1;
        var rd = new FileReader();
        rd.onload = function(){
          try{
            var text = String(rd.result), arr = setsAll(), add = 0;
            if(/<ImageProcessing/i.test(text)){                       /* 官方 .oes：一个文件一个槽 */
              var one = oesParse(text);
              var slots = { 1: null, 2: null, 3: null, 4: null };
              slots[toSlot] = { vivid: one.vivid, raw: {}, used: (function(){ var u = 0; for(var i = 0; i < 12; i++) if(one.vivid[i]) u++; return u; })(),
                                hi: one.hi, mid: one.mid, lo: one.lo, eff: 0, shp: one.shp, con: one.con };
              arr.push({ id: 'imp' + Date.now(), name: f.name.replace(/\\.[a-z]+$/i, ''), desc: '（从 .oes 导入）', from: 'imported', camera: modelNow(), slots: slots });
              add = 1;
            } else {                                                   /* 本 app 的 JSON（带名字/描述） */
              var pack = JSON.parse(text);
              if(!pack || pack.kind !== 'om3-colorprofile') throw new Error('不认识这个文件');
              if(pack.sets && pack.sets.length){
                pack.sets.forEach(function(s){ arr.push({ id: 'imp' + Date.now() + add, name: s.name || f.name, desc: s.desc || '', from: s.from || 'imported', camera: s.camera, slots: s.slots }); add++; });
              } else if(pack.slots){
                arr.push({ id: 'imp' + Date.now(), name: pack.name || f.name.replace(/\\.[a-z]+$/i, ''), desc: pack.desc || '', from: pack.from || 'imported', camera: pack.camera, slots: pack.slots }); add = 1;
              } else throw new Error('文件里没有方案数据');
            }
            if(setsSave(arr)){ mpRender(); log('✅ 已导入 ' + add + ' 套方案（可改名/加描述，再选档位+槽位写入相机）', 'ok'); toastMsg('已导入 ' + add + ' 套'); }
          }catch(e){ log('导入失败：' + (e && e.message ? e.message : e), 'err'); toastMsg('导入失败，看日志'); }
        };
        rd.readAsText(f); inp.value = '';
      });
    }
    inp.click();
  }
''' + h[m_imp.end():]

# ④ 卡片按钮文案 + "导出全部"改为 JSON
h = h.replace('id="mpExportAll" class="mpbtn">导出全部（官方 .oes）', 'id="mpExportAll" class="mpbtn">导出全部方案（.json）', 1)
h = h.replace('id="mpImportFile" class="mpbtn">导入 .oes 文件', 'id="mpImportFile" class="mpbtn">导入方案文件', 1)
h = h.replace('官方 .oes 格式：OM Workspace 可直接读，也能分享给别人，对方导入后选槽位填充。',
              '方案文件（.json）带名字和描述，方便分享与管理；也支持导入官方 .oes（给 OM Workspace 用）。', 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('初始化修复 + 页签联动 + JSON 管理（名字/描述）+ .oes 可选导出（+%d 字节）' % (len(h) - n0))
