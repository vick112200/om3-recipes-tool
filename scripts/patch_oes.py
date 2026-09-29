# -*- coding: utf-8 -*-
"""① 导入/导出改用官方 .oes 格式（官方的色彩配置文件，OM Workspace 认得、网站也用这个分享）
   ② UI 里去掉"时间"与"桌面版"相关字样
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- ① .oes 生成 / 解析 实现（挂在「我的配方」段之前） ----------
anchor = "  /* ================= 「我的配方」：方案库 + 档位管理 ================= */"
assert h.count(anchor) == 1, h.count(anchor)
OES = r'''  /* ===== 官方 .oes 色彩配置文件：生成 / 解析 ===== */
  function oesBuild(one){
    var v = (one && one.vivid) ? one.vivid : [0,0,0,0,0,0,0,0,0,0,0,0];
    function z(n){ var a = []; for(var i = 0; i < n; i++) a.push(0); return a.join(','); }
    return '<?xml version="1.0" encoding="UTF-8"?>' + '\n' +
      '<ImageProcessing>' + '\n' +
      '  <ParametersType FormatID="65539" Platform="M" Version="2401" />' + '\n' +
      '  <Parameters>' + '\n' +
      '    <RawEditMode Apply="true" Mode="2" />' + '\n' +
      '    <ExposureBias Apply="true" Numerator="0" Denominator="10" />' + '\n' +
      '    <WhiteBalance Apply="true" Mode="Preset" Kelvin="0" RedAdjust="0" GreenAdjust="0" Type="4096" />' + '\n' +
      '    <Contrast Apply="true" Mode="Manual" Value="' + (Number(one && one.con) || 0) + '" Adjust="0" />' + '\n' +
      '    <Sharpness Apply="true" Mode="Manual" Value="' + (Number(one && one.shp) || 0) + '" Adjust="0" />' + '\n' +
      '    <ToneControl Apply="true" Mode="Manual" Bright="' + (Number(one && one.hi) || 0) + '" Dark="' + (Number(one && one.lo) || 0) + '" Mid="' + (Number(one && one.mid) || 0) + '" />' + '\n' +
      '    <ColorCreater2 Apply="true" Mode="Manual" SatValue="' + v.join(',') + '" LumValue="' + z(12) + '" HueValue="' + z(12) + '" />' + '\n' +
      '  </Parameters>' + '\n' +
      '</ImageProcessing>' + '\n';
  }
  function oesParse(txt){
    txt = String(txt || '');
    function num(tag, attr){
      var m = new RegExp('<' + tag + '[^>]*' + attr + '="(-?[0-9.]+)"').exec(txt);
      return m ? Math.round(Number(m[1])) : 0;
    }
    var m = /<ColorCreater2[^>]*SatValue="([^"]*)"/.exec(txt);
    if(!m) throw new Error('不是 .oes 配置文件（找不到 ColorCreater2）');
    var vivid = m[1].split(',').map(function(s){ return Math.round(Number(s)) || 0; });
    while(vivid.length < 12) vivid.push(0);
    return { vivid: vivid.slice(0, 12), hi: num('ToneControl', 'Bright'), lo: num('ToneControl', 'Dark'),
             mid: num('ToneControl', 'Mid'), shp: num('Sharpness', 'Value'), con: num('Contrast', 'Value'), eff: 0 };
  }
  function oesName(one, base){
    var used = 0; for(var i = 0; i < 12; i++) if((one.vivid || [])[i]) used++;
    return String(base || 'OM3').replace(/[\\/:*?"<>|\s]/g, '_') + '-' + (used ? 'P' + used : 'default') + '.oes';
  }
  window.__om3oesBuild = oesBuild;

''' + anchor
h = h.replace(anchor, OES, 1)

# ---------- ① 方案条目：导出改为 .oes（每个有内容的槽一个文件） ----------
old_exp = "        if(op === 'export'){ mpExportOne(s); return; }"
assert h.count(old_exp) == 1, h.count(old_exp)
h = h.replace(old_exp, """        if(op === 'export'){ mpExportOes(s); return; }""", 1)

# 用 .oes 版导出替换原来的 mpExportOne / mpExportAll
m1 = re.search(r"  function mpExportOne\(s\)\{.*?\n  \}\n", h, re.S)
assert m1, 'mpExportOne not found'
h = h[:m1.start()] + '''  /* 导出一套方案：每个有内容的槽生成一个官方 .oes 文件 */
  function mpExportOes(s){
    var names = [];
    for(var q = 1; q <= 4; q++){
      var one = s.slots && s.slots[q];
      if(!one || !one.vivid) continue;
      var base = (s.name || 'OM3方案') + '-槽' + q;
      var fn = oesName(one, base);
      if(om3Download(fn, oesBuild(one), 'text/xml')) names.push(fn);
    }
    if(!names.length){ log('这套方案里没有可导出的槽。', 'warn'); return; }
    log('✅ 已导出 ' + names.length + ' 个官方 .oes 文件：' + names.join('、') + '（在「下载」里，可分享/给 OM Workspace 用）', 'ok');
    var o = document.getElementById('mpFileOut'); if(o) o.textContent = '已导出：' + names.join('、');
    toastMsg('已导出 .oes');
  }
''' + h[m1.end():]

m2 = re.search(r"  function mpExportAll\(\)\{.*?\n  \}\n", h, re.S)
assert m2, 'mpExportAll not found'
h = h[:m2.start()] + '''  function mpExportAll(){
    var a = setsAll();
    if(!a.length){ log('还没有方案可导出。', 'warn'); return; }
    var n = 0;
    for(var i = 0; i < a.length; i++){ for(var q = 1; q <= 4; q++){
      var one = a[i].slots && a[i].slots[q]; if(!one || !one.vivid) continue;
      if(om3Download(oesName(one, (a[i].name || 'OM3方案') + '-槽' + q), oesBuild(one), 'text/xml')) n++;
    } }
    log('✅ 已导出 ' + n + ' 个官方 .oes 文件（每套方案每个槽一个）', 'ok');
    toastMsg('已导出 ' + n + ' 个 .oes');
  }
''' + h[m2.end():]

# ---------- ① 导入：接受 .oes ----------
m3 = re.search(r"  function mpImportFile\(\)\{.*?\n  \}\n", h, re.S)
assert m3, 'mpImportFile not found'
h = h[:m3.start()] + '''  function mpImportFile(){
    var inp = document.getElementById('mpFile');
    if(!inp){
      inp = document.createElement('input'); inp.type = 'file'; inp.id = 'mpFile';
      inp.accept = '.oes,.json,text/xml,application/json'; inp.style.display = 'none';
      document.body.appendChild(inp);
      inp.addEventListener('change', function(){
        var f = inp.files && inp.files[0]; if(!f) return;
        var sel = document.getElementById('mpImpSlot');
        var toSlot = Number(sel ? sel.value : 1) || 1;
        var rd = new FileReader();
        rd.onload = function(){
          try{
            var text = String(rd.result), one, name = f.name.replace(/\\.[a-z]+$/i, '');
            if(/\\.oes$/i.test(f.name) || /<ImageProcessing/i.test(text)){
              one = oesParse(text);                                  /* 官方 .oes：一个文件 = 一个槽 */
            } else {
              var pack = JSON.parse(text);                           /* 兼容旧版本 app 文件 */
              if(!pack || pack.kind !== 'om3-colorprofile' || !pack.slots) throw new Error('不认识这个文件');
              var ks = Object.keys(pack.slots); one = pack.slots[ks[0]];
            }
            var arr = setsAll();
            var slots = { 1: null, 2: null, 3: null, 4: null };
            slots[toSlot] = { vivid: one.vivid, raw: {}, used: (function(){ var u = 0; for(var i = 0; i < 12; i++) if(one.vivid[i]) u++; return u; })(),
                              hi: one.hi || 0, mid: one.mid || 0, lo: one.lo || 0, eff: one.eff || 0, shp: one.shp || 0, con: one.con || 0 };
            arr.push({ id: 'imp' + Date.now(), name: name, from: 'imported', camera: modelNow(), slots: slots });
            if(setsSave(arr)){ mpRender(); log('✅ 已导入「' + name + '」→ 记在方案库的槽 ' + toSlot + '（色轮=[' + one.vivid.join(',') + ']）', 'ok'); toastMsg('已导入'); }
          }catch(e){ log('导入失败：' + (e && e.message ? e.message : e), 'err'); toastMsg('导入失败，看日志'); }
        };
        rd.readAsText(f); inp.value = '';
      });
    }
    inp.click();
  }
''' + h[m3.end():]

# ---------- ④ 卡片文案/控件：导入槽位选择；去掉时间字样 ----------
h = h.replace('<button type="button" id="mpExportAll" class="mpbtn">导出全部方案（文件）</button>',
              '<button type="button" id="mpExportAll" class="mpbtn">导出全部（官方 .oes）</button>', 1)
h = h.replace('<button type="button" id="mpImportFile" class="mpbtn">导入方案文件</button>',
              '<button type="button" id="mpImportFile" class="mpbtn">导入 .oes 文件</button>', 1)
old_hint = '导出的文件可以分享给同样装了本 app 的人；对方导入后可选槽位填充。'
assert h.count(old_hint) == 1, h.count(old_hint)
h = h.replace(old_hint, '官方 .oes 格式：OM Workspace 可直接读，也能分享给别人，对方导入后选槽位填充。', 1)
# 在导入按钮上方加"导入到槽位"选择
old_r = '<div class="mproll">\n        <button type="button" id="mpExportAll"'
i = h.find(old_r)
assert i > 0
h = h[:i] + '<div class="mpsel"><span style="font-size:13px;color:#aaa">导入到</span><select id="mpImpSlot"><option value="1">槽 1</option><option value="2">槽 2</option><option value="3">槽 3</option><option value="4">槽 4</option></select></div>\n      ' + h[i:]

# ---------- ② UI 去掉"时间"字样 ----------
h = h.replace("' · ' + (s.at || '') + '</div>'", "'</div>'", 1)
h = h.replace("'<div class=\"s\">来自 ' + tierLabel(s.from || 'current') + '　·　' + used + '/4 槽有内容　·　' + (s.at || '') + '</div>'",
              "'<div class=\"s\">' + tierLabel(s.from || 'current') + '　·　' + used + '/4 槽有内容</div>'", 1)
h = h.replace("var at = new Date().toLocaleString('zh-CN');", "var at = '';", 1)
h = h.replace("arr.push({ id: 'set' + Date.now(), name: tierLabel(mode) + ' ' + at.slice(5, 16), from: mode, at: at, camera: modelNow(), slots: slots });",
              "arr.push({ id: 'set' + Date.now(), name: tierLabel(mode) + ' 方案', from: mode, at: '', camera: modelNow(), slots: slots });", 1)
h = h.replace("'　·　' + (s.at || '')", "'　·　' + ''", 1)
# 桌面版字样
for bad in ['（桌面版）', '桌面版', '单文件 HTML', 'HTML 桌面']:
    h = h.replace(bad, '', )

open(P, 'w', encoding='utf-8', newline='').write(h)
print('官方 .oes 导入/导出 + 去掉时间/桌面字样（+%d 字节）' % (len(h) - n0))
print('残留检查：桌面版 =', h.count('桌面版'), '| at 显示 =', h.count("' · ' + (s.at"), '| .oes 生成 =', h.count('oesBuild'))
