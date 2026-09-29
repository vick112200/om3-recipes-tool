# -*- coding: utf-8 -*-
"""IV. 相机档案（首次自检自动存）+ 极端值标定（确定 SET1–4 ↔ 相机 UI）
   ① mapModes 里顺手把学到的档位/大小/槽位占用存成"相机档案"（按序列号）
   ② 菜单「查看相机档案」
   ③ 菜单「标定测试：往目标槽写全 +5」+「撤销标定（还原原值）」
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- 实现：档案 + 标定（挂在 runTask 前面） ----------
anchor = "  /* ===== 任务条：把长任务包起来"
assert h.count(anchor) == 1, h.count(anchor)
FUNC = '''  /* ===== 相机档案：按序列号存"这台相机学到的东西" ===== */
  var PKEY = 'om3profile';
  function profAll(){ try{ return JSON.parse(localStorage.getItem(PKEY) || '{}'); }catch(e){ return {}; } }
  function profSave(serial, obj){ var a = profAll(); a[serial] = obj; try{ localStorage.setItem(PKEY, JSON.stringify(a)); }catch(e){} }
  function profShow(){
    showStep(3);
    var a = profAll(), ks = Object.keys(a);
    if(!ks.length){ log('还没有相机档案：先连相机 → ☰ →「档位映射诊断（只读）」，跑完就自动存了。', 'warn'); return; }
    for(var i = 0; i < ks.length; i++){
      var p = a[ks[i]];
      log('===== 相机 ' + p.model + '（序列 ' + ks[i] + '）　学习于 ' + p.learned);
      for(var j = 0; j < (p.modes || []).length; j++){
        var m = p.modes[j];
        log('　' + m.mode + '（' + m.name + '）　' + m.size + ' 字节　' + (m.slots || []).join(' / '));
      }
    }
    log('===== 档案结束（换新相机就跑一次映射诊断，会自动补一条）', 'ok');
    toastMsg('档案见日志');
  }
  window.__om3profShow = profShow;

  /* ===== 极端值标定：把目标槽 12 条色轴写成全 +5，一眼看出它对应相机上哪个槽 ===== */
  var CALKEY = 'om3cal';
  function calLoad(){ try{ return JSON.parse(localStorage.getItem(CALKEY) || 'null'); }catch(e){ return null; } }
  function calSave(o){ try{ localStorage.setItem(CALKEY, JSON.stringify(o)); }catch(e){} }
  function calRecipe(){
    var r = { n: '【标定】全 +5', a: 'cal', t: 'COLOR', v: [5,5,5,5,5,5,5,5,5,5,5,5],
              hi: 0, mid: 0, sh: 0, eff: 0, shp: 0, con: 0 };
    return r;
  }
  async function calibrate(mode, N){
    showStep(3);
    log('===== 标定测试：把 ' + mode + ' · 槽' + N + ' 的 12 条色轴写成全 +5');
    var before = await readMySet(mode);
    var kv = slotKV(calRecipe(), N), pat = patchText(before, kv);
    var orig = {}, k;
    /* 先记录原值（撤销时用） */
    for(k in kv){
      if(!Object.prototype.hasOwnProperty.call(kv, k)) continue;
      var m, out = {};
      var mm = om3map(before);
      orig[k] = (mm[k] === undefined ? '' : mm[k]);
    }
    calSave({ mode: mode, slot: N, orig: orig, missed: pat.missed, at: new Date().toLocaleString('zh-CN') });
    if(pat.missed.length){
      log('⚠ 这些键不存在：' + pat.missed.join(', ') + ' → 已中止，未写入', 'err');
      return;
    }
    log('① 原值已存（撤销用）：' + Object.keys(orig).length + ' 项');
    await writeSlotRecipe(mode, N, calRecipe());
    log('② 标定已下发。相机重启后：拨盘到该档位 → OK → 超级控制面板 → 逐个切 Color Profile 槽 →', 'ok');
    log('　　【哪个槽变成 12 条色轴全 +5，它就对应 SET' + N + '】', 'ok');
    log('③ 测完点 ☰ →「撤销标定（还原原值）」把那个槽改回来。', 'warn');
  }
  async function calUndo(){
    showStep(3);
    var c = calLoad();
    if(!c){ log('没有标定记录可撤销。', 'warn'); return; }
    var rec = { n: '【还原】标定前原值', a: 'cal', t: 'COLOR',
                v: [0,0,0,0,0,0,0,0,0,0,0,0], hi: 0, mid: 0, sh: 0, eff: 0, shp: 0, con: 0 };
    /* 直接用存下来的原值拼回目标键 */
    var key2field = {
      '_VIVID_SET': 'v', '_TONE_CONTROL_HIGH_SET': 'hi', '_TONE_CONTROL_MIDDLE_SET': 'mid',
      '_TONE_CONTROL_LOW_SET': 'sh', '_SHADING_SET': 'eff', '_SHARP_SET': 'shp', '_CONTRAST_SET': 'con'
    };
    var kv = {}, k;
    for(k in c.orig){
      if(!Object.prototype.hasOwnProperty.call(c.orig, k)) continue;
      kv[k] = c.orig[k];
    }
    try{
      var before = await readMySet(c.mode);
      var pat = patchText(before, kv);
      log('===== 撤销标定：' + c.mode + ' · 槽' + c.slot + '（改动 ' + pat.changed.length + ' 项）');
      var bak = {};
      for(k in kv){ if(Object.prototype.hasOwnProperty.call(kv, k)) bak[k] = kv[k]; }
      /* 用 writeSlotRecipe 的底层路径：先构造"与当前相同"的配方对象不可行，这里直接复用内部函数 */
      await writeRawKV(c.mode, c.slot, kv);
      log('✅ 已把标定前原值写回', 'ok');
    }catch(e){ log('撤销失败：' + e.message, 'err'); }
  }
  window.__om3cal = calibrate; window.__om3calUndo = calUndo;

'''
h = h.replace(anchor, FUNC + anchor, 1)

# writeRawKV：按"键:值"直接整份改写写回（标定撤销 / 通用）
anchor2 = "  async function writeSlotRecipe(modeName, slotN, rec){"
assert h.count(anchor2) == 1, h.count(anchor2)
RAW = '''  /* 通用：把一份 {键:值} 直接整份改写写回（标定撤销用） */
  async function writeRawKV(modeName, slotN, kv){
    var lg = log;
    var before = await readMySet(modeName);
    var pat = patchText(before, kv);
    var after = pat.text;
    lg('① 原 ' + before.length + ' → 新 ' + after.length + ' 字节，改 ' + pat.changed.length + ' 项');
    if(pat.missed.length) throw new Error('键不存在：' + pat.missed.join(', '));
    var r1 = await req('request_restoremysetdata.cgi?action=restore', {timeout: 15000});
    var r2 = await req('set_mysetdatasize.cgi?size=' + after.length, {timeout: 15000});
    lg('② 声明大小 ' + after.length + '：HTTP ' + r2.status);
    var CH = 4096, off = 0, n = 0, bad = 0;
    while(off < after.length){
      var part = after.slice(off, Math.min(off + CH, after.length));
      var rr = await req('send_partialmysetdata.cgi?offset=' + off + '&size=' + part.length, {body: part, timeout: 20000});
      n++; if(rr.status !== 200){ bad++; } off += part.length; await sleep(60);
    }
    lg('③ 上传 ' + n + ' 块，失败 ' + bad + ' 块', bad ? 'err' : 'ok');
    if(bad) throw new Error('上传有块失败');
    for(var t2 = 0; t2 < 30; t2++){
      await sleep(500);
      var rp = await req('get_mysetrestorestate.cgi', {timeout: 8000});
      if(/<status>\\s*(success|complete|finish|done|idle)\\s*<\\//i.test(rp.text || '')) break;
    }
    try{ await req('exec_reboot.cgi', {timeout: 8000}); lg('④ 已请求重启', 'ok'); }catch(e){}
  }

'''
h = h.replace(anchor2, RAW + anchor2, 1)

# ---------- mapModes 里顺手存档案 ----------
old_sig = "  async function mapModes(){"
assert h.count(old_sig) == 1, h.count(old_sig)
h = h.replace(old_sig, "  async function mapModes(pg){\n    var _learned = { model: '', serial: '', learned: new Date().toLocaleString('zh-CN'), modes: [] };", 1)
old_star = "        log('　★ mode=' + X + '　名字：' + nm + '　字节 ' + sz + '　头部：' + head, 'ok');"
assert h.count(old_star) == 1, h.count(old_star)
h = h.replace(old_star, old_star + """
        try{
          var _hi = String(head).split(',');
          if(_hi.length > 1 && _hi[1]) _learned.model = _hi[1];
          if(_hi.length > 3 && _hi[3]) _learned.serial = _hi[3];
          _learned.modes.push({ mode: X, name: String(nm).replace(/[\\s\\S]*<mysetname>([^<]*)<\\/mysetname>[\\s\\S]*/, '$1') || nm, size: sz, slots: om3slotSummary(body).split('｜') });
        }catch(e){}""", 1)
old_end = "log('===== \u6620\u5c04\u8bca\u65ad\u7ed3\u675f\u3002\u628a\u8fd9\u4e00\u6bb5\u590d\u5236\u7ed9\u6211\uff08\u542b \u2605 \u884c\u548c\"\u69fd\u4f4d\u5360\u7528\"\uff09\u3002', 'ok');"
assert h.count(old_end) == 1, h.count(old_end)
h = h.replace(old_end, """    if(_learned.serial){
      profSave(_learned.serial, _learned);
      log('⑤ 已存相机档案：' + _learned.model + '（序列 ' + _learned.serial + '），' + _learned.modes.length + ' 份 my-set（☰ →「查看相机档案」可看）', 'ok');
    }
""" + old_end, 1)

# ---------- 菜单项 + 处理 ----------
old_m = '      <button type="button" data-act="verify">校验上次写入（重启后点我）</button>'
assert h.count(old_m) == 1, h.count(old_m)
h = h.replace(old_m, old_m + """
      <button type="button" data-act="prof">查看相机档案</button>
      <button type="button" data-act="cal">标定测试：把目标槽写成全 +5</button>
      <button type="button" data-act="calundo">撤销标定（还原原值）</button>""", 1)
old_a = "      else if(a === 'verify'){"
assert h.count(old_a) == 1, h.count(old_a)
h = h.replace(old_a, """      else if(a === 'prof'){ profShow(); }
      else if(a === 'cal'){
        var s1 = currentSel();
        if(!s1 || !s1.rec){ log('先在 ③ 里选好配方（标定其实用不到它的数值，只是需要目标档位/槽）。', 'err'); return; }
        runTask('标定 ' + modeForTarget(s1.target) + ' · 槽' + s1.slot, function(){ return calibrate(modeForTarget(s1.target), Number(s1.slot) || 1); });
      }
      else if(a === 'calundo'){ runTask('撤销标定', function(){ return calUndo(); }); }
""" + old_a, 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('IV 完成：相机档案 + 标定/撤销（+%d 字节）' % (len(h) - n0))
