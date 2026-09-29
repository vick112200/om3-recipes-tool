# -*- coding: utf-8 -*-
"""「我的配方」逻辑：方案库（读取/保存/写回/导出/导入）+ 档位管理"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

anchor = "  /* ===== 导出 / 导入：把相机里的色彩配置变成可分享的文件 ===== */"
assert h.count(anchor) == 1, h.count(anchor)

CODE = r'''  /* ================= 「我的配方」：方案库 + 档位管理 ================= */
  var SETKEY = 'om3sets', TIERKEY = 'om3tiers';
  function setsAll(){ try{ return JSON.parse(localStorage.getItem(SETKEY) || '[]'); }catch(e){ return []; } }
  function setsSave(a){ try{ localStorage.setItem(SETKEY, JSON.stringify(a)); return true; }catch(e){ log('保存方案失败（存储已满？）：' + e.message, 'err'); return false; } }
  function tiersAll(){
    try{ var t = JSON.parse(localStorage.getItem(TIERKEY) || 'null'); if(t && t.length) return t; }catch(e){}
    return ['current', 'myset1', 'myset2', 'myset3', 'myset4', 'myset5',
            'moviemyset1', 'moviemyset2', 'moviemyset3', 'moviemyset4', 'moviemyset5'];
  }
  function tiersSave(a){ try{ localStorage.setItem(TIERKEY, JSON.stringify(a)); }catch(e){} }
  function tierLabel(m){
    if(m === 'current') return '当前状态';
    var r = /^myset([0-9]+)$/.exec(m); if(r) return 'C' + r[1];
    r = /^moviemyset([0-9]+)$/.exec(m); if(r) return '录像档' + r[1];
    return m;
  }
  function mpOpt(list, val){ return list.map(function(m){ return '<option value="' + m + '"' + (m === val ? ' selected' : '') + '>' + tierLabel(m) + '</option>'; }).join(''); }

  /* 把一份 dump 变成"4 个槽 + 原始键值"（导出/保存共用） */
  function dumpToSlots(txt){
    var mp = om3map(txt), slots = {}, s, j, k, q;
    for(s = 1; s <= 4; s++){
      var vivid = [], raw = {}, used = 0;
      for(j = 1; j <= 12; j++){
        k = 'MODE_COLOR_CREATOR_2_VIVID_SET' + s + '_' + j;
        vivid.push(om3decode(mp[k], 'STEP'));
        if(mp[k] !== undefined) raw[k] = mp[k];
        if(om3decode(mp[k], 'STEP')) used++;
      }
      for(q = 0; q < SLOTK.length; q++) if(mp[SLOTK[q] + s] !== undefined) raw[SLOTK[q] + s] = mp[SLOTK[q] + s];
      slots[s] = { vivid: vivid, raw: raw, used: used,
                   hi: om3decode(mp[SLOTK[0] + s], 'STEP'), mid: om3decode(mp[SLOTK[1] + s], 'STEP'),
                   lo: om3decode(mp[SLOTK[2] + s], 'STEP'), eff: om3decode(mp[SLOTK[3] + s], 'STEP'),
                   shp: om3decode(mp[SLOTK[4] + s], 'SHARP'), con: om3decode(mp[SLOTK[5] + s], 'CONTRAST') };
    }
    return slots;
  }

  /* ---------- 界面：方案列表 ---------- */
  function mpRender(){
    var box = document.getElementById('mpList');
    if(!box) return;
    var a = setsAll();
    var c = document.getElementById('mpCount');
    if(c) c.textContent = a.length ? ('共 ' + a.length + ' 套') : '';
    if(!a.length){
      box.innerHTML = '<div class="mpempty">还没有方案。先连相机 → 选一个档位 → 点上面「读取并保存为方案」。</div>';
      return;
    }
    box.innerHTML = '';
    a.forEach(function(s, idx){
      var div = document.createElement('div');
      div.className = 'mpitem';
      var used = 0; for(var q = 1; q <= 4; q++) if(s.slots && s.slots[q] && s.slots[q].used) used++;
      div.innerHTML = '<div class="t">' + (s.name || '未命名方案') + '</div>' +
        '<div class="s">来自 ' + tierLabel(s.from || 'current') + '　·　' + used + '/4 槽有内容　·　' + (s.at || '') + '</div>' +
        '<div class="r"><button data-i="' + idx + '" data-op="write">写入相机</button>' +
        '<button data-i="' + idx + '" data-op="export">导出</button>' +
        '<button data-i="' + idx + '" data-op="rename">改名</button>' +
        '<button data-i="' + idx + '" data-op="del" class="mpbtn danger" style="flex:none">删除</button></div>' +
        '<div class="mpsel hide" id="mpw' + idx + '"></div>';
      box.appendChild(div);
    });
    box.querySelectorAll('button[data-op]').forEach(function(b){
      b.addEventListener('click', function(){
        var i = Number(b.getAttribute('data-i')), op = b.getAttribute('data-op'), arr = setsAll(), s = arr[i];
        if(!s) return;
        if(op === 'del'){
          if(!confirm('删除方案「' + (s.name || '') + '」？')) return;
          arr.splice(i, 1); setsSave(arr); mpRender(); log('已删除方案', 'ok'); return;
        }
        if(op === 'rename'){
          var nm = prompt('方案名字：', s.name || '');
          if(nm){ arr[i].name = nm; setsSave(arr); mpRender(); }
          return;
        }
        if(op === 'export'){ mpExportOne(s); return; }
        if(op === 'write'){ mpWritePanel(i, s); }
      });
    });
  }

  /* ---------- 写入面板（选档位 + 槽位） ---------- */
  function mpWritePanel(idx, s){
    var box = document.getElementById('mpw' + idx);
    if(!box) return;
    if(!box.classList.contains('hide')){ box.classList.add('hide'); return; }
    box.classList.remove('hide');
    box.innerHTML = '<span style="font-size:13px;color:#aaa">写入到</span>' +
      '<select id="mpwTier' + idx + '">' + mpOpt(tiersAll(), (s.from && tiersAll().indexOf(s.from) >= 0) ? s.from : 'myset1') + '</select>' +
      '<select id="mpwSlot' + idx + '"><option value="0">全部 4 个槽</option>' +
      '<option value="1">槽 1</option><option value="2">槽 2</option><option value="3">槽 3</option><option value="4">槽 4</option></select>' +
      '<button type="button" class="mpbtn primary" id="mpwGo' + idx + '" style="flex:none;padding:9px 14px">开始写入</button>';
    document.getElementById('mpwGo' + idx).addEventListener('click', function(){
      var mode = document.getElementById('mpwTier' + idx).value;
      var slot = Number(document.getElementById('mpwSlot' + idx).value);
      var list = slot ? [slot] : [1, 2, 3, 4];
      runTask('写入 ' + tierLabel(mode) + (slot ? (' · 槽' + slot) : ' · 全部槽'), async function(){
        var lg = log;
        lg('===== 写入方案「' + (s.name || '') + '」→ ' + tierLabel(mode) + (slot ? (' · 槽' + slot) : ' · 全部 4 槽'));
        await readMySet(mode);                        /* 先进维护模式（顺带确认相机可用） */
        for(var n = 0; n < list.length; n++){
          var sn = list[n], one = s.slots && s.slots[sn];
          if(!one || !one.raw || !Object.keys(one.raw).length){ lg('　槽' + sn + '：方案里没有内容，跳过', 'warn'); continue; }
          lg('　槽' + sn + '：写 ' + Object.keys(one.raw).length + ' 项（色轮=' + (one.vivid || []).join(',') + '）');
          await writeRawKV(mode, sn, one.raw);
        }
      });
    });
  }

  /* ---------- 读取并保存 ---------- */
  async function mpReadFromCamera(){
    var sel = document.getElementById('mpReadTier');
    var mode = sel ? sel.value : 'myset1';
    var slots, at = new Date().toLocaleString('zh-CN');
    await runTask('读取 ' + tierLabel(mode) + ' 并保存', async function(){
      var txt = await readMySet(mode);
      slots = dumpToSlots(txt);
      var arr = setsAll();
      var used = 0; for(var q = 1; q <= 4; q++) if(slots[q] && slots[q].used) used++;
      arr.push({ id: 'set' + Date.now(), name: tierLabel(mode) + ' ' + at.slice(5, 16), from: mode, at: at, camera: modelNow(), slots: slots });
      if(setsSave(arr)){ log('✅ 已保存方案：' + tierLabel(mode) + '（' + used + '/4 槽有内容）', 'ok'); mpRender(); toastMsg('已保存到我的配方'); }
    });
  }

  /* ---------- 导出 / 导入 ---------- */
  function om3Download(name, text, type){
    try{
      var blob = new Blob([text], { type: type || 'application/json' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob); a.download = name;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      return true;
    }catch(e){ log('生成文件失败：' + e.message, 'err'); return false; }
  }
  function mpExportOne(s){
    var pack = { app: 'OM-3 色彩配方手册', kind: 'om3-colorprofile', version: 2, camera: s.camera || modelNow(),
                 name: s.name, from: s.from, exportedAt: new Date().toLocaleString('zh-CN'), slots: s.slots };
    var name = 'OM3方案-' + String(s.name || '未命名').replace(/[\\/:*?"<>|\\s]/g, '_') + '.json';
    if(om3Download(name, JSON.stringify(pack, null, 1))) log('✅ 已导出：' + name + '（在「下载」里，可分享）', 'ok');
    var o = document.getElementById('mpFileOut'); if(o) o.textContent = '已导出：' + name;
  }
  function mpExportAll(){
    var a = setsAll();
    if(!a.length){ log('还没有方案可导出。', 'warn'); return; }
    var pack = { app: 'OM-3 色彩配方手册', kind: 'om3-colorprofile', version: 2, count: a.length,
                 exportedAt: new Date().toLocaleString('zh-CN'),
                 sets: a.map(function(s){ return { name: s.name, from: s.from, at: s.at, camera: s.camera, slots: s.slots }; }) };
    var name = 'OM3我的配方-' + new Date().toISOString().slice(0, 10) + '.json';
    if(om3Download(name, JSON.stringify(pack, null, 1))){ log('✅ 已导出 ' + a.length + ' 套方案：' + name, 'ok'); toastMsg('已导出'); }
  }
  function mpImportFile(){
    var inp = document.getElementById('mpFile');
    if(!inp){
      inp = document.createElement('input'); inp.type = 'file'; inp.id = 'mpFile';
      inp.accept = '.json,application/json'; inp.style.display = 'none';
      document.body.appendChild(inp);
      inp.addEventListener('change', function(){
        var f = inp.files && inp.files[0]; if(!f) return;
        var rd = new FileReader();
        rd.onload = function(){
          try{
            var pack = JSON.parse(String(rd.result));
            if(!pack || pack.kind !== 'om3-colorprofile') throw new Error('不是本 app 导出的文件');
            var arr = setsAll(), add = 0;
            if(pack.sets && pack.sets.length){
              pack.sets.forEach(function(s){ arr.push({ id: 'imp' + Date.now() + add, name: s.name || f.name, from: s.from, at: s.at || '', camera: s.camera, slots: s.slots }); add++; });
            } else if(pack.slots){
              arr.push({ id: 'imp' + Date.now(), name: (pack.name || f.name.replace(/\.json$/i, '')), from: pack.from, at: pack.exportedAt || '', camera: pack.camera, slots: pack.slots }); add++;
            } else throw new Error('文件里没有方案数据');
            if(setsSave(arr)){ mpRender(); log('✅ 已导入 ' + add + ' 套方案（在下面列表里，选档位+槽位即可写入相机）', 'ok'); toastMsg('已导入 ' + add + ' 套'); }
          }catch(e){ log('导入失败：' + (e && e.message ? e.message : e), 'err'); toastMsg('导入失败，看日志'); }
        };
        rd.readAsText(f); inp.value = '';
      });
    }
    inp.click();
  }

  /* ---------- 档位管理 ---------- */
  function mpTierUI(){
    var box = document.getElementById('mpTiers');
    if(!box) return;
    var t = tiersAll();
    box.innerHTML = '';
    t.forEach(function(m, i){
      var row = document.createElement('div');
      row.className = 'mptier';
      row.innerHTML = '<input value="' + m + '" data-i="' + i + '"><span style="font-size:12px;color:#888;flex:none">' + tierLabel(m) + '</span>' +
                      '<button type="button" class="mpbtn danger" data-del="' + i + '" style="flex:none;padding:8px 10px">删</button>';
      box.appendChild(row);
    });
    box.querySelectorAll('input[data-i]').forEach(function(el){
      el.addEventListener('change', function(){
        var a = tiersAll(); a[Number(el.getAttribute('data-i'))] = String(el.value || '').trim() || a[Number(el.getAttribute('data-i'))];
        tiersSave(a); mpTierUI(); mpFillTierSelect(); log('档位已更新：' + a.join(' / '));
      });
    });
    box.querySelectorAll('button[data-del]').forEach(function(el){
      el.addEventListener('click', function(){ var a = tiersAll(); a.splice(Number(el.getAttribute('data-del')), 1); tiersSave(a); mpTierUI(); mpFillTierSelect(); });
    });
  }
  function mpFillTierSelect(){
    var sel = document.getElementById('mpReadTier');
    if(!sel) return;
    var keep = sel.value;
    var t = tiersAll();
    sel.innerHTML = mpOpt(t, keep && t.indexOf(keep) >= 0 ? keep : t[0]);
  }

  /* 初始化 */
  try{
    mpFillTierSelect(); mpTierUI(); mpRender();
    var bR = document.getElementById('mpRead'); if(bR) bR.addEventListener('click', mpReadFromCamera);
    var bE = document.getElementById('mpExportAll'); if(bE) bE.addEventListener('click', mpExportAll);
    var bI = document.getElementById('mpImportFile'); if(bI) bI.addEventListener('click', mpImportFile);
    var bA = document.getElementById('mpTierAdd'); if(bA) bA.addEventListener('click', function(){ var a = tiersAll(); a.push('myset' + (a.length + 1)); tiersSave(a); mpTierUI(); mpFillTierSelect(); });
    var bT = document.getElementById('mpTierReset'); if(bT) bT.addEventListener('click', function(){ if(confirm('恢复默认 OM-3 档位列表？')){ try{ localStorage.removeItem(TIERKEY); }catch(e){} mpTierUI(); mpFillTierSelect(); } });
    window.__om3mpRender = mpRender; window.__om3mpRead = mpReadFromCamera;
  }catch(e){ try{ log('「我的配方」初始化出错：' + (e && e.message ? e.message : e), 'err'); }catch(x){} }

'''
h = h.replace(anchor, CODE + anchor, 1)
open(P, 'w', encoding='utf-8', newline='').write(h)
print('「我的配方」逻辑已加（+%d 字节）' % (len(h) - n0))
