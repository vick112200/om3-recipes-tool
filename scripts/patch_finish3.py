# -*- coding: utf-8 -*-
"""收尾 1-3：
   1) 配方卡加「加入我的方案」（按 slug 精确取配方，不依赖旧注入逻辑）
   2) 连接相机 · 安全备份页按"自动安全网"定位精简文案
   3) 第二行搜索按钮：确保点开搜索/目录面板
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- ① 配方卡「加入我的方案」 ----------
anchor = "  /* ===== 蓝牙（实验）：扫描 + 调试日志 ====="
assert h.count(anchor) == 1, h.count(anchor)
SAVE = '''  /* ===== 配方卡 → 加入我的方案（用 slug 精确匹配，和卡片 id r-<slug> 对齐） ===== */
  function recBySlug(slug){
    try{
      var a = window.__OM3RECIPES__ || [];
      for(var i = 0; i < a.length; i++) if(a[i].slug === slug) return a[i];
    }catch(e){}
    return null;
  }
  function saveCardToSets(card){
    var id = card && card.id ? card.id : '';
    var slug = id.replace(/^r-/, '');
    var rec = recBySlug(slug);
    if(!rec){ log('没找到这条配方的数据（slug=' + slug + '）', 'err'); toastMsg('这条配方暂无参数数据'); return; }
    if(!rec.v || rec.v.length < 12){ log('这条配方没有色轮数据，不能存为方案', 'err'); return; }
    var kv = {};
    try{ kv = slotKV(rec, 1); }catch(e){ kv = {}; }
    var used = 0; for(var i = 0; i < 12; i++) if(rec.v[i]) used++;
    var arr = setsAll();
    arr.push({ id: 'b' + Date.now(), name: rec.n + ' · ' + rec.a, desc: '来自内置配方', from: 'builtin',
               camera: modelNow(), slots: { 1: { vivid: rec.v, raw: kv, used: used, hi: rec.hi, mid: rec.mid,
               lo: rec.sh, eff: rec.eff, shp: rec.shp, con: rec.con }, 2: null, 3: null, 4: null } });
    if(setsSave(arr)){
      log('✅ 已加入我的方案：' + rec.n + ' · ' + rec.a + '（在「我的配方」里可改名/加描述/写入相机/分享）', 'ok');
      toastMsg('已加入我的方案');
      try{ mpRender(); }catch(e){}
    }
  }
  function injectMineBtns(){
    try{
      var cards = document.querySelectorAll('.card[id^="r-"]');
      for(var i = 0; i < cards.length; i++){
        var c = cards[i];
        if(c.querySelector('.omsavebtn')) continue;
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'omsavebtn';
        b.textContent = '加入我的方案';
        b.addEventListener('click', function(ev){
          ev.stopPropagation();
          var cc = ev.target;
          while(cc && cc !== document && !(cc.className && String(cc.className).indexOf('card') >= 0)) cc = cc.parentNode;
          if(cc && cc.id) saveCardToSets(cc);
        });
        var host = c.querySelector('.cbody') || c;
        host.appendChild(b);
      }
      log('配方卡「加入我的方案」按钮已就绪（' + cards.length + ' 张卡）');
    }catch(e){ log('注入「加入我的方案」失败：' + (e && e.message ? e.message : e), 'err'); }
  }
  window.__om3saveCard = saveCardToSets;
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', injectMineBtns);
  else setTimeout(injectMineBtns, 300);
  document.querySelectorAll('.tabs.mod button[data-p]').forEach(function(b){
    b.addEventListener('click', function(){ setTimeout(injectMineBtns, 400); });
  });

''' + anchor
h = h.replace(anchor, SAVE, 1)

# 按钮样式
k = h.find('</style>')
h = h[:k] + """
.omsavebtn{display:block;width:100%;margin-top:8px;padding:9px;border-radius:9px;border:1px solid #33507e;background:#1b2436;color:#cfe0ff;font-size:12.5px}
""" + h[k:]

# ---------- ② 安全备份页文案（按"自动安全网"定位） ----------
old_hd = '<div class="camhd">② 备份相机当前设置（只读，不会改任何东西）</div>'
if h.count(old_hd) == 1:
    h = h.replace(old_hd, '<div class="camhd">② 安全备份（自动安全网）</div>\n    <div class="camout">写入配方前会<b>自动</b>做一次；平时不用管这里，只有出问题时点「写回备份」回滚。</div>', 1)
else:
    m2 = re.search(r'<div class="camhd">[^<]*备份[^<]*</div>', h)
    if m2:
        h = h[:m2.start()] + '<div class="camhd">② 安全备份（自动安全网）</div>\n    <div class="camout">写入配方前会<b>自动</b>做一次；平时不用管，出问题时点「写回备份」回滚。</div>' + h[m2.end():]

# ---------- ③ 搜索按钮：确保点开搜索/目录面板 ----------
anchor3 = "  window.__om3applyModule = applyModule;"
assert h.count(anchor3) == 1
h = h.replace(anchor3, anchor3 + """
  /* 第二行搜索按钮 → 打开搜索/目录面板（沿用原有搜索；若原监听丢了这里兜底） */
  (function(){
    var b = document.getElementById('tocbtn');
    if(!b) return;
    b.addEventListener('click', function(){
      try{
        var panel = document.getElementById('toc2');
        if(panel){
          var hidden = panel.classList.contains('hide');
          if(hidden){
            panel.classList.remove('hide');
            try{ var i = panel.querySelector('input'); if(i) i.focus(); }catch(e){}
            log('已打开搜索 / 目录');
          } else panel.classList.add('hide');
        } else { log('搜索面板元素没找到（toc2）', 'err'); }
      }catch(e){ log('打开搜索失败：' + e.message, 'err'); }
    });
  })();""", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('1-3 已写入（+%d 字节）' % (len(h) - n0))
