# -*- coding: utf-8 -*-
"""① 内置配方卡片：手机上改为上下堆叠（色轮一行居中，其余全宽），不再挤右边
   ② 「加入我的方案」补到优化版的槽位（.oslot）上
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- ① 卡片布局：堆叠 ----------
k = h.find('</style>')
assert k > 0
h = h[:k] + """
/* 配方卡：手机上上下堆叠 —— 色轮一行居中，其余内容全宽（不再挤压右边） */
.cbody{display:flex;flex-direction:column;gap:10px}
.cleft{width:100% !important;max-width:none !important;display:flex;flex-direction:column;align-items:center}
.cleft svg.wheel{width:min(64vw,270px);height:auto}
.cright{width:100% !important;max-width:none !important}
.cright .shots{grid-template-columns:repeat(auto-fill,minmax(140px,1fr)) !important}
.vals,.vlegend{text-align:center}
/* 优化版槽位卡同样处理 */
.oslot{display:block}
""" + h[k:]

# ---------- ② 优化版槽位也加「加入我的方案」 ----------
old = """  function injectMineBtns(){
    try{
      var cards = document.querySelectorAll('.card[id^="r-"]');"""
assert h.count(old) == 1, h.count(old)
new = """  function normN(s){ return String(s || '').replace(/[\\s·・\\-_/]+/g, '').toLowerCase(); }
  function recByName2(txt){
    try{
      var a = window.__OM3RECIPES__ || [], t = normN(txt);
      for(var i = 0; i < a.length; i++){
        var n = normN(a[i].n);
        if(n && (t.indexOf(n) === 0 || t.indexOf(n) >= 0)) return a[i];
      }
    }catch(e){}
    return null;
  }
  function injectMineBtns(){
    try{
      /* 优化版槽位：靠名字反查配方数据 */
      var os = document.querySelectorAll('.oslot');
      for(var q = 0; q < os.length; q++){
        var o = os[q];
        if(o.querySelector('.omsavebtn')) continue;
        var nmEl = o.querySelector('.osname') || o;
        var rec2 = recByName2(nmEl.textContent || '');
        if(!rec2) continue;
        var b2 = document.createElement('button');
        b2.type = 'button';
        b2.className = 'omsavebtn';
        b2.textContent = '加入我的方案';
        b2.addEventListener('click', function(ev){
          ev.stopPropagation();
          var t = ev.target, slot = t;
          while(slot && slot !== document && !(slot.className && String(slot.className).indexOf('oslot') >= 0)) slot = slot.parentNode;
          var nm2 = slot ? (slot.querySelector('.osname') || slot).textContent : '';
          var r2 = recByName2(nm2) || rec2;
          if(r2) saveCardToSets2(r2);
        });
        o.appendChild(b2);
      }
      var cards = document.querySelectorAll('.card[id^="r-"]');"""
h = h.replace(old, new, 1)

# 供槽位使用的保存函数（按配方对象直接存）
anchor = "  function injectMineBtns(){"
assert h.count(anchor) == 1
h = h.replace(anchor, """  function saveCardToSets2(rec){
    if(!rec || !rec.v || rec.v.length < 12){ log('这条配方没有色轮数据，不能存为方案', 'err'); return; }
    var kv = {}; try{ kv = slotKV(rec, 1); }catch(e){ kv = {}; }
    var used = 0; for(var i = 0; i < 12; i++) if(rec.v[i]) used++;
    var arr = setsAll();
    arr.push({ id: 'b' + Date.now(), name: rec.n + ' · ' + rec.a, desc: '来自内置配方（优化版）', from: 'builtin',
               camera: modelNow(), slots: { 1: { vivid: rec.v, raw: kv, used: used, hi: rec.hi, mid: rec.mid,
               lo: rec.sh, eff: rec.eff, shp: rec.shp, con: rec.con }, 2: null, 3: null, 4: null } });
    if(setsSave(arr)){ log('✅ 已加入我的方案：' + rec.n + ' · ' + rec.a, 'ok'); toastMsg('已加入我的方案'); try{ mpRender(); }catch(e){} }
  }

""" + anchor, 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('卡片堆叠 + 优化版按钮 已改（%+d 字节）' % (len(h) - n0))
