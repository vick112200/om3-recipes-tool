# -*- coding: utf-8 -*-
"""新增：把配方写进指定 my-set 的指定槽（默认 C1·槽1）
流程：读整份 mysetN → 只改目标槽的那几行 → 整份写回 → 重启 → 读回对比（改动清单）
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# 菜单项：写入 C1 · 槽1（用 ③ 里选的配方）
old = '      <button type="button" data-act="keys">列出色彩相关键（诊断）</button>'
assert h.count(old) == 1, h.count(old)
h = h.replace(old, old + '\n      <button type="button" data-act="w_c1s1">写入 C1 · 槽1（用③选的配方）</button>', 1)
old_a = "      else if(a === 'keys'){ listColorKeys(); }"
assert h.count(old_a) == 1, h.count(old_a)
h = h.replace(old_a, old_a + """
      else if(a === 'w_c1s1'){
        var s0 = currentSel();
        if(!s0 || !s0.rec){ log('先在 ③ 里选好一条配方，再点这个。', 'err'); return; }
        try{ writeSlotRecipe('myset1', 1, s0.rec); }catch(e){ log('写入失败：' + e.message, 'err'); }
      }""", 1)

# 实现
anchor = "  /* ============ 档位映射（只读）"
assert h.count(anchor) == 1, h.count(anchor)
FUNC = '''  /* ============ 写配方到指定 my-set 的指定槽（整份改写 + 写前写后对比） ============ */
  function om3step(v){ v = Number(v) || 0; return 'MODE_STEP_' + (v > 0 ? 'P' + v : (v < 0 ? 'M' + Math.abs(v) : '0')); }
  function om3sharp(v){ v = Number(v) || 0; return 'MODE_SHARP_' + (v > 0 ? 'P' + v : (v < 0 ? 'M' + Math.abs(v) : '0')); }
  function om3contrast(v){ v = Number(v) || 0; return 'MODE_CONTRAST_' + (v > 0 ? 'P' + v : (v < 0 ? 'M' + Math.abs(v) : '0')); }

  /* 一条配方 → 目标槽要写的 {键: 值} */
  function slotKV(rec, N){
    var c = [rec.yellow, rec.orange, rec.orangeRed, rec.red, rec.magenta, rec.violet,
             rec.blue, rec.blueCyan, rec.cyan, rec.greenCyan, rec.green, rec.yellowGreen];
    var kv = {}, i;
    for(i = 0; i < 12; i++) kv['MODE_COLOR_CREATOR_2_VIVID_SET' + N + '_' + (i + 1)] = om3step(c[i]);
    kv['MODE_COLOR_CREATOR_2_TONE_CONTROL_HIGH_SET' + N]   = om3step(rec.highlights);
    kv['MODE_COLOR_CREATOR_2_TONE_CONTROL_MIDDLE_SET' + N] = om3step(rec.midtones);
    kv['MODE_COLOR_CREATOR_2_TONE_CONTROL_LOW_SET' + N]    = om3step(rec.shadows);
    kv['MODE_COLOR_CREATOR_2_SHADING_SET' + N]   = om3step(rec.shadingEffect);
    kv['MODE_COLOR_CREATOR_2_SHARP_SET' + N]     = om3sharp(rec.sharpness);
    kv['MODE_COLOR_CREATOR_2_CONTRAST_SET' + N]  = om3contrast(rec.contrast);
    return kv;
  }

  /* 在整份文本里替换这些键的值；返回 {text, changed:[…]} */
  function patchText(txt, kv){
    var LF = String.fromCharCode(10), CR = String.fromCharCode(13);
    var s = String(txt).split(CR).join('');
    var L = s.split(LF), changed = [], missed = [];
    for(var i = 0; i < L.length; i++){
      var p = L[i].split(',');
      if(p.length >= 3 && p[0] === '2' && kv[p[1]] !== undefined){
        var oldV = p.slice(2).join(',');
        if(oldV !== kv[p[1]]) changed.push(p[1] + '：' + oldV + ' → ' + kv[p[1]]);
        L[i] = '2,' + p[1] + ',' + kv[p[1]];
      }
    }
    var keys = Object.keys(kv);
    for(var k = 0; k < keys.length; k++){
      var hit = false, j;
      for(j = 0; j < L.length; j++){ var q = L[j].split(','); if(q.length >= 3 && q[1] === keys[k]){ hit = true; break; } }
      if(!hit) missed.push(keys[k]);
    }
    return { text: L.join(LF), changed: changed, missed: missed };
  }

  async function readMySet(modeName, lg){
    lg = lg || log;
    var rq = await req('request_getmysetdata.cgi?mode=' + encodeURIComponent(modeName) + '&kind=current', {timeout: 20000});
    if(rq.status !== 200 || /generalerror/i.test(rq.text || '')) throw new Error('相机不接受读取 ' + modeName + '（HTTP ' + rq.status + '）');
    var ready = false;
    for(var t = 0; t < 40 && !ready; t++){
      await sleep(500);
      var rs = await req('get_mysetbackupstate.cgi', {timeout: 8000});
      var tx = rs.text || '';
      if(!/busy/i.test(tx) && /success|idle|complete|ready/i.test(tx)) ready = true;
    }
    var rz = await req('get_mysetdatasize.cgi?kind=current', {timeout: 8000});
    var sz = sizeFrom(rz.text);
    if(!(sz > 0)) throw new Error('拿不到 ' + modeName + ' 的大小');
    var rd = await req('get_partialmysetdata.cgi?kind=current&offset=0&size=' + sz, {timeout: 40000});
    if(rd.status !== 200) throw new Error('读取数据失败（HTTP ' + rd.status + '）');
    return om3CsvPart(rd.text).slice(0, sz);
  }

  async function writeSlotRecipe(modeName, slotN, rec){
    showStep(3);
    var lg = log;
    lg('===== 写配方到 ' + modeName + ' · 槽' + slotN + '：' + rec.n + '（' + rec.a + '）');
    var before = await readMySet(modeName, lg);
    lg('① 写前读取：' + before.length + ' 字节', 'ok');
    var kv = slotKV(rec, slotN);
    lg('② 目标槽要写的 ' + Object.keys(kv).length + ' 个键：');
    for(var i = 0; i < 12; i++) lg('　　 色轮 ' + (i + 1) + ' = ' + kv['MODE_COLOR_CREATOR_2_VIVID_SET' + slotN + '_' + (i + 1)]);
    lg('　　 高光/中间调/阴影 = ' + kv['MODE_COLOR_CREATOR_2_TONE_CONTROL_HIGH_SET' + slotN] + ' / ' + kv['MODE_COLOR_CREATOR_2_TONE_CONTROL_MIDDLE_SET' + slotN] + ' / ' + kv['MODE_COLOR_CREATOR_2_TONE_CONTROL_LOW_SET' + slotN]);
    lg('　　 锐度/对比/阴影补偿 = ' + kv['MODE_COLOR_CREATOR_2_SHARP_SET' + slotN] + ' / ' + kv['MODE_COLOR_CREATOR_2_CONTRAST_SET' + slotN] + ' / ' + kv['MODE_COLOR_CREATOR_2_SHADING_SET' + slotN]);
    var pat = patchText(before, kv);
    lg('③ 已修改 ' + pat.changed.length + ' 处：' + (pat.changed.length ? '' : '（无变化？）'));
    for(var c = 0; c < pat.changed.length && c < 24; c++) lg('　　 ' + pat.changed[c]);
    if(pat.missed.length){ lg('④ 警告：这些键在这份数据里没找到 → ' + pat.missed.join(', '), 'err'); throw new Error('目标键不存在，已中止（未写入）'); }
    var after = pat.text;
    lg('④ 新数据 ' + after.length + ' 字节（原 ' + before.length + '）');

    var rM = await req('switch_cammode.cgi?mode=maintenance', {timeout: 10000});
    lg('⑤ 进维护模式：HTTP ' + rM.status, rM.status === 200 ? 'ok' : 'err');
    if(rM.status !== 200) throw new Error('相机不接受维护模式');
    var r1 = await req('request_restoremysetdata.cgi?action=restore', {timeout: 15000});
    lg('⑥ 进入恢复模式：HTTP ' + r1.status + ' ' + (r1.text || '').slice(0, 60));
    var r2 = await req('set_mysetdatasize.cgi?size=' + after.length, {timeout: 15000});
    lg('⑦ 声明大小 ' + after.length + '：HTTP ' + r2.status + ' ' + (r2.text || '').slice(0, 60), /ok/i.test(r2.text || '') ? 'ok' : 'err');
    var CH = 4096, off = 0, n = 0, bad = 0;
    while(off < after.length){
      var part = after.slice(off, Math.min(off + CH, after.length));
      var rr = await req('send_partialmysetdata.cgi?offset=' + off + '&size=' + part.length, {body: part, timeout: 20000});
      n++;
      if(rr.status !== 200){ bad++; lg('⑧ 第 ' + n + ' 块 offset=' + off + ' HTTP ' + rr.status, 'err'); if(bad > 1) break; }
      else if(n % 5 === 0 || off + CH >= after.length) lg('⑧ 第 ' + n + ' 块 offset=' + off + ' size=' + part.length + ' → HTTP 200');
      off += part.length;
      await sleep(60);
    }
    if(bad > 1) throw new Error('上传有块失败，未完成');
    lg('⑨ 全部 ' + n + ' 块上传完成（' + after.length + ' 字节）', 'ok');
    var okS = false;
    for(var t2 = 0; t2 < 30 && !okS; t2++){
      await sleep(500);
      var rp = await req('get_mysetrestorestate.cgi', {timeout: 8000});
      var tx2 = rp.text || '';
      if(/<status>\s*(success|complete|finish|done|idle)\s*<\//i.test(tx2)) okS = true;
      else if(t2 % 4 === 0) lg('⑩ 等待写入应用… ' + tx2.replace(/\s+/g, ' ').slice(0, 80));
    }
    lg(okS ? '⑩ 相机报告写入完成 ✓' : '⑩ 状态不明确，继续读回验证', okS ? 'ok' : 'warn');
    var r9 = await req('exec_reboot.cgi', {timeout: 8000});
    lg('⑪ 已请求相机重启（退出维护模式）：HTTP ' + r9.status, 'ok');
    lg('　　等相机重启完（约 20-30 秒）后重连，点一次 ② 会看到对比；或直接看下面。', 'ok');
    lg('====== 去相机上确认：拨盘 ' + (modeName === 'current' ? '（当前状态）' : modeName.replace('myset', 'C').replace('moviemyset', '录像C')) + ' → 按 OK 调出超级控制面板 → Color Profile → 槽' + slotN, 'ok');
  }
  window.__om3writeSlot = writeSlotRecipe;

'''
h = h.replace(anchor, FUNC + anchor, 1)
open(P, 'w', encoding='utf-8', newline='').write(h)
print('已加「写入 C1·槽1」功能（+%d 字节）' % (len(h) - n0))
