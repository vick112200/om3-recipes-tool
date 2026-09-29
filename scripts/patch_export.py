# -*- coding: utf-8 -*-
"""导出兜底（OM-3 的 my-set 直连通道已探测确认不可用）：
- ② 加「导出全部配方（文件）」：生成可读文本 + JSON，下载/复制
- ③ 加「我手动写好了 → 记入记录」：不假装自动写，但槽位记录照样维护
- ②③ 卡片标注本机型不支持（已探测）
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()

# ---- ② 卡片：导出按钮 + 说明 ----
old = '<button type="button" id="camDl" disabled>下载备份文件</button>'
assert h.count(old) == 1
h = h.replace(old, old + '<button type="button" id="camExport">导出全部配方（文件）</button>', 1)
old_note = '<div class="camhd">备份相机当前设置（只读，不会改任何东西）</div>'
assert h.count(old_note) == 1
h = h.replace(old_note, old_note + '''
    <div class="camout" style="color:#d8b45a">⚠ 2026-09-23 实测：本机 OM-3 的 my-set 接口全部返回 520/1001（相机不开放这条通道，仅 get_caminfo.cgi 可用）。
      「读取并备份」在本机型上不会成功 —— 用它之前请先看下面「导出全部配方」，那份文件才是能带走的东西。</div>''', 1)

# ---- ③ 卡片：手动记入记录 ----
old_w = '<button type="button" id="camWrite" class="camprimary">写入相机'
assert h.count(old_w) == 1, h.count(old_w)
h = h.replace(old_w, old_w + '<button type="button" id="camManRec">我已在相机上写好 → 记入记录</button>', 1)

# ---- JS：导出 + 手动记录 ----
anchor = "  window.__om3restoreBackup = restoreBackup;"
assert h.count(anchor) == 1
ADD = anchor + '''

  /* ---------- 导出全部配方（可读文本 + JSON） ---------- */
  function recipeBlock(r, idx){
    var L = [];
    L.push('[' + idx + '] ' + r.n + ' · ' + r.a + '　（' + r.t + '）');
    L.push('    色调曲线: 高光 ' + r.hi + ' / 阴影 ' + r.sh + ' / 中间调 ' + r.mid +
           '　对比 ' + r.con + '　锐度 ' + r.shp + '　效果 ' + r.eff);
    L.push('    白平衡: ' + r.wb + (r.wbt ? ' ' + r.wbt + 'K' : '') +
           '　A-B ' + r.wba + '　G-M ' + r.wbg +
           (r.monoColor ? ('　单色: ' + r.monoColor + '/' + r.monoStr) : '') +
           (r.grain ? ('　颗粒: ' + r.grain) : '') + (r.hue ? ('　色相: ' + r.hue) : ''));
    L.push('    12 色轮: ' + (r.v || []).join(' '));
    L.push('    原始参数: ' + JSON.stringify(r));
    return L.join('\\n');
  }
  function exportRecipes(){
    var L = [];
    L.push('OM-3 色彩配方手册 · 配方导出');
    L.push('生成时间：' + new Date().toLocaleString('zh-CN'));
    L.push('共 ' + REC.length + ' 条配方（原版 79 + 优化版 20 槽位所用）');
    L.push('');
    L.push('用法：① 想直接在相机上录入 → 照每条下面的数值；② 想给官方 app / OM Workspace 用 → 文件末尾有机器可读 JSON。');
    L.push('='.repeat(60));
    for(var i=0;i<REC.length;i++){ L.push(recipeBlock(REC[i], i+1)); L.push(''); }
    L.push('='.repeat(60));
    L.push('机器可读 JSON：');
    L.push(JSON.stringify({ exported: new Date().toISOString(), recipes: REC }, null, 1));
    var text = L.join('\\n');
    try{
      var blob = new Blob([text], {type:'text/plain'});
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'OM3-配方导出-' + new Date().toISOString().slice(0,10) + '.txt';
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      line(o2, '已生成导出文件（在「下载」文件夹里），共 ' + REC.length + ' 条。', 'ok');
      log('已导出 ' + REC.length + ' 条配方到文件');
    }catch(e){ line(o2, '生成文件失败：' + e.message, 'err'); }
    try{ navigator.clipboard.writeText(text.slice(0, 200000)); line(o2, '（前 20 万字符也已复制到剪贴板）', 'ok'); }catch(e){}
  }
  document.getElementById('camExport').addEventListener('click', exportRecipes);
  window.__om3export = exportRecipes;

  /* ---------- 手动写入后记入记录 ---------- */
  document.getElementById('camManRec').addEventListener('click', function(){
    var s = currentSel();
    if(!s.rec){ log('先在上面选配方。', 'err'); return; }
    impRecord(s.rec, s.target, s.slot);
    var lbl = (s.target === 'current') ? '当前状态' : (s.target + ' · 槽' + s.slot);
    log('已记入：' + s.rec.n + ' → ' + lbl + '（手动登记）', 'ok');
    toastMsg('已记入记录：' + lbl);
  });'''
h = h.replace(anchor, ADD, 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('导出兜底 + 手动记入记录 已加')
