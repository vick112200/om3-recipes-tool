# -*- coding: utf-8 -*-
"""子区块可见性兜底：模块初始化万一没跑到，「我的配方」/「连接相机」也不留白屏"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

anchor = '  /* 搜索框：兜底开合 + 保证有关闭按钮 */'
assert h.count(anchor) == 1, h.count(anchor)
ADD = '''  /* ===== 子区块可见性兜底：哪怕主模块初始化失败，页面也不空 ===== */
  function ensureVisible(){
    try{
      var cur = window.__om3cur || 'A';
      if(cur === 'D'){
        var any = false, k;
        for(k = 1; k <= 4; k++){ var v = document.getElementById('camV' + k); if(v && !v.classList.contains('hide')) any = true; }
        if(!any){ var v1 = document.getElementById('camV1'); if(v1) v1.classList.remove('hide'); }
      }
      if(cur === 'E'){
        var on = document.querySelector('#paneE .mpsub.on');
        if(!on){ var s1 = document.getElementById('mpsub-sets'); if(s1) s1.classList.add('on'); }
        var box = document.getElementById('mpList');
        if(box && !(box.textContent || '').trim() && !box.querySelector('.mpempty')){
          box.innerHTML = '<div class="mpempty">还没有方案。到「读取」页从相机读一份，或在配方卡上点「加入我的方案」。</div>';
        }
      }
    }catch(e){}
  }
  window.__om3ensureVisible = ensureVisible;
  setInterval(ensureVisible, 800);
''' + anchor
h = h.replace(anchor, ADD, 1)
open(P, 'w', encoding='utf-8', newline='').write(h)
print('子区块兜底已加（%+d 字节）' % (len(h) - n0))
