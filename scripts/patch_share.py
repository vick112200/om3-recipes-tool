# -*- coding: utf-8 -*-
"""收尾 A：菜单清理（删掉已完成使命的诊断项）+ 新增"导出/导入相机配置文件"。"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ① 删掉过时诊断菜单项（只删按钮，处理分支留着无副作用）
for act in ['probe', 'keys', 'w_c1s1', 'cal', 'calundo', 'maint']:
    m = re.search(r'\n\s*<button type="button" data-act="' + act + r'">[^<]*</button>', h)
    assert m, act
    h = h[:m.start()] + h[m.end():]

# ② 重命名 + 新增导出/导入
h = h.replace('data-act="verify">校验上次写入（重启后点我）', 'data-act="verify">校验写入结果', 1)
h = h.replace('data-act="map">档位映射诊断（只读）', 'data-act="map">首次自检（换相机时跑一次）', 1)
anchor_btn = '      <button type="button" data-act="verify">校验写入结果</button>'
assert h.count(anchor_btn) == 1, h.count(anchor_btn)
h = h.replace(anchor_btn, anchor_btn + '\n      <button type="button" data-act="exp">导出相机配置（文件）</button>\n      <button type="button" data-act="imp">导入配置文件（.json）</button>', 1)

# ③ 分支
old_a = "      else if(a === 'verify'){"
assert h.count(old_a) == 1, h.count(old_a)
h = h.replace(old_a, """      else if(a === 'exp'){
        var se = currentSel();
        runTask('导出配置', function(){ return om3ExportMySet(modeForTarget(se.target)); });
      }
      else if(a === 'imp'){ om3PickFile(); }
""" + old_a, 1)

# ④ 实现
anchor = "  /* ===== 「预览（只读）」入口"
assert h.count(anchor) == 1, h.count(anchor)
IMPL = r'''  /* ===== 导出 / 导入：把相机里的色彩配置变成可分享的文件 ===== */
  function om3decode(v, kind){
    var m = new RegExp('^MODE_' + kind + '_(P|M)?(\\d+)?').exec(String(v || '')) || [];
    if(!m[2]) return 0;
    return (m[1] === 'M' ? -1 : 1) * Number(m[2]);
  }
  var SLOTK = ['MODE_COLOR_CREATOR_2_TONE_CONTROL_HIGH_SET', 'MODE_COLOR_CREATOR_2_TONE_CONTROL_MIDDLE_SET',
               'MODE_COLOR_CREATOR_2_TONE_CONTROL_LOW_SET', 'MODE_COLOR_CREATOR_2_SHADING_SET',
               'MODE_COLOR_CREATOR_2_SHARP_SET', 'MODE_COLOR_CREATOR_2_CONTRAST_SET'];
  async function om3ExportMySet(modeName){
    showStep(3);
    log('===== 导出配置：' + modeName + '（只读）');
    var mp = om3map(await readMySet(modeName));
    var slots = {}, s, j, k, q;
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
      log('　槽' + s + '：' + (used ? (used + ' 条色轴非默认') : '空/默认') + '　色轮=[' + vivid.join(',') + ']');
    }
    var pack = { app: 'OM-3 色彩配方手册', kind: 'om3-colorprofile', version: 1,
                 camera: (function(){ try{ var p = profAll(), ks = Object.keys(p); return ks.length ? p[ks[0]].model : ''; }catch(e){ return ''; } })(),
                 from: modeName, exportedAt: new Date().toLocaleString('zh-CN'), slots: slots };
    var text = JSON.stringify(pack, null, 1);
    var name = 'OM3配置-' + modeName + '-' + new Date().toISOString().slice(0, 10) + '.json';
    try{
      var blob = new Blob([text], { type: 'application/json' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob); a.download = name;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      log('✅ 已生成文件：' + name + '（在手机「下载」里，可分享给同样装了本 app 的人）', 'ok');
    }catch(e){ log('生成文件失败：' + e.message, 'err'); }
    try{ navigator.clipboard.writeText(text); log('（内容也已复制到剪贴板）', 'ok'); }catch(e){}
    toastMsg('已导出配置文件');
  }
  window.__om3export = om3ExportMySet;

  function om3PickFile(){
    showStep(3);
    var inp = document.getElementById('om3File');
    if(!inp){
      inp = document.createElement('input');
      inp.type = 'file'; inp.id = 'om3File'; inp.accept = '.json,application/json'; inp.style.display = 'none';
      document.body.appendChild(inp);
      inp.addEventListener('change', function(){
        var f = inp.files && inp.files[0];
        if(!f) return;
        var rd = new FileReader();
        rd.onload = function(){
          try{
            var pack = JSON.parse(String(rd.result));
            if(!pack || pack.kind !== 'om3-colorprofile' || !pack.slots) throw new Error('不是本 app 导出的配置文件');
            var s = currentSel(), slot = Number(s.slot) || 1;
            var one = pack.slots[slot] || pack.slots[String(slot)];
            if(!one) throw new Error('文件里没有槽' + slot);
            log('===== 导入配置：' + f.name + '（来自 ' + (pack.camera || '未知相机') + '，' + (pack.exportedAt || '') + '）');
            log('　将写入：' + modeForTarget(s.target) + ' · 槽' + slot + '　色轮=[' + (one.vivid || []).join(',') + ']');
            var rec = { n: '（导入）' + f.name.replace(/\.json$/i, '') + ' 槽' + slot, a: 'file',
                        v: one.vivid || [0,0,0,0,0,0,0,0,0,0,0,0], hi: one.hi || 0, mid: one.mid || 0,
                        sh: one.lo || 0, eff: one.eff || 0, shp: one.shp || 0, con: one.con || 0 };
            runTask('导入配置 → 槽' + slot, function(){ return om3WriteViaSlot(rec, slot, s.target, modelNow(), log); });
          }catch(e){ log('导入失败：' + (e && e.message ? e.message : e), 'err'); toastMsg('导入失败，看日志'); }
        };
        rd.readAsText(f);
        inp.value = '';
      });
    }
    inp.click();
  }
  window.__om3pickFile = om3PickFile;

'''
h = h.replace(anchor, IMPL + anchor, 1)
open(P, 'w', encoding='utf-8', newline='').write(h)
print('菜单清理 + 导出/导入 已加（+%d 字节）' % (len(h) - n0))
