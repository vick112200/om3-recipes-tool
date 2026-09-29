# -*- coding: utf-8 -*-
"""I. 拆掉危险路径：
   ① 新增 om3WriteViaSlot(rec, slot, target, model, lg)：把"target"映射成 my-set，
      再走新的"整份改写"函数 writeSlotRecipe
   ② 两处旧调用（③ 卡片 12580 / 配方卡导入 13223）改成调它
   ③ writeSlotRecipe 里加"读回对比"：上传完先试着读回目标 my-set 并逐项核对
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- ① 映射 + 包装函数（挂在 writeSlotRecipe 定义之前） ----------
anchor = "  async function writeSlotRecipe(modeName, slotN, rec){"
assert h.count(anchor) == 1, h.count(anchor)
WRAP = '''  /* 把界面上的"目标"（current / C1..C5 / 录像C1..C5）映射成相机 my-set 名 */
  function modeForTarget(target){
    target = String(target || 'current');
    if(target === 'current') return 'current';
    var m = /^(movie)?C([1-5])$/i.exec(target) || /^(movie)?([1-5])$/i.exec(target);
    if(m) return (m[1] ? 'moviemyset' : 'myset') + m[2];
    if(/^myset[1-5]$/i.test(target)) return target.toLowerCase();
    if(/^moviemyset[1-5]$/i.test(target)) return target.toLowerCase();
    return 'current';
  }

  /* 统一入口：界面两个按钮都走这里 —— 整份改写，不再下发那种 970 字节碎片 */
  async function om3WriteViaSlot(rec, slot, target, model, lg){
    lg = lg || log;
    if(!rec) return { ok: false, err: 'no_recipe' };
    var mode = modeForTarget(target);
    try{
      await writeSlotRecipe(mode, Number(slot) || 1, rec);
      return { ok: true, mode: mode };
    }catch(e){
      lg('写入中止：' + (e && e.message ? e.message : e), 'err');
      return { ok: false, err: (e && e.message) ? e.message : String(e) };
    }
  }
  window.__om3write = om3WriteViaSlot;

'''
h = h.replace(anchor, WRAP + anchor, 1)

# ---------- ② 两处旧调用改成新入口 ----------
old1 = "    var r = await writeRecipe(s.rec, s.slot, s.target, s.model, log);"
assert h.count(old1) == 1, h.count(old1)
h = h.replace(old1, "    var r = await om3WriteViaSlot(s.rec, s.slot, s.target, s.model, log);", 1)

old2 = "    var r = await writeRecipe(rec, slot, target, model, log);"
assert h.count(old2) == 1, h.count(old2)
h = h.replace(old2, "    var r = await om3WriteViaSlot(rec, slot, target, model, log);", 1)

# ---------- ③ 上传完成后：读回对比（best-effort） ----------
old3 = """    lg(okS ? '⑩ 相机报告写入完成 ✓' : '⑩ 状态不明确，继续读回验证', okS ? 'ok' : 'warn');
    var r9 = await req('exec_reboot.cgi', {timeout: 8000});"""
assert h.count(old3) == 1, h.count(old3)
new3 = """    lg(okS ? '⑩ 相机报告写入完成 ✓' : '⑩ 状态不明确 —— 用"读回对比"来判断', okS ? 'ok' : 'warn');
    /* 读回对比：上传的数据到底进没进相机（比那个状态接口可靠） */
    try{
      var back = await readMySet(modeName, lg);
      var bm = om3map(back), bad = [], kk;
      for(kk in kv){
        if(!Object.prototype.hasOwnProperty.call(kv, kk)) continue;
        if(bm[kk] !== kv[kk]) bad.push(kk + '：期望 ' + kv[kk] + '，相机里是 ' + (bm[kk] === undefined ? '（无此项）' : bm[kk]));
      }
      if(!bad.length) lg('⑩a 读回对比：19 项全部与配方一致 ✅ 写入已生效', 'ok');
      else { lg('⑩a 读回对比：有 ' + bad.length + ' 项不一致 ⚠', 'warn'); for(var b = 0; b < bad.length && b < 10; b++) lg('　　 ' + bad[b], 'warn'); }
    }catch(e){ lg('⑩a 读回对比没做成（' + e.message + '）——等相机重启后重连、再点一次 ② 也能对比', 'warn'); }
    var r9 = await req('exec_reboot.cgi', {timeout: 8000});"""
h = h.replace(old3, new3, 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('I 完成：两处入口已改为整份改写 + 读回对比（+%d 字节）' % (len(h) - n0))
