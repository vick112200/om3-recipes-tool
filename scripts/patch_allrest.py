# -*- coding: utf-8 -*-
"""把队列里能做的全做掉：
   1) #toc2 补 !important 隐藏兜底（浮层体检唯一隐患）
   2) 优化版槽位名匹配不上 → 写日志（不再静默）
   3) 底栏改 position:static（完全跟随内容，永不吸屏幕底 —— 你说"不能固定底部"）
   4) 顺手：优化版匹配不到时给出"手动加入"入口（点一下用槽位名当方案名，仍可用）
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---- 1) toc2 隐藏兜底 ----
k = h.find('</style>')
assert k > 0
h = h[:k] + """
#toc2:not(.open){display:none !important}
#toc2.hide{display:none !important}
""" + h[k:]

# ---- 3) 底栏 static（完全跟随内容） ----
h = h.replace('.barABC,.barD{display:none;gap:6px;position:sticky;bottom:0;z-index:55;background:#101010;border-top:1px solid #242424;padding:8px 4px;margin-top:12px}',
              '.barABC,.barD{display:none;gap:6px;position:static;background:#101010;border-top:1px solid #242424;padding:8px 4px;margin-top:14px}', 1)
h = h.replace('.mpbar{display:flex;gap:6px;position:sticky;bottom:0;z-index:55;background:#101010;border-top:1px solid #242424;padding:8px 4px;margin-top:12px}',
              '.mpbar{display:flex;gap:6px;position:static;background:#101010;border-top:1px solid #242424;padding:8px 4px;margin-top:14px}', 1)

# ---- 2)+4) 优化版：匹配不上就写日志 + 给手动加入入口 ----
old = """        var rec2 = recByName2(nmEl.textContent || '');
        if(!rec2) continue;"""
assert h.count(old) == 1, h.count(old)
new = """        var nmTxt = (nmEl.textContent || '').trim();
        var rec2 = recByName2(nmTxt);
        if(!rec2){
          /* 匹配不到参数：写日志（不静默），并给一个"只存名字"的入口 */
          try{ log('优化版槽位「' + nmTxt.slice(0, 18) + '」在内置配方数据里没匹配到参数，已提供"仅存名字"入口', 'warn'); }catch(e){}
          if(!o.querySelector('.omsavebtn')){
            var b3 = document.createElement('button');
            b3.type = 'button'; b3.className = 'omsavebtn';
            b3.textContent = '加入我的方案（仅名字）';
            b3.addEventListener('click', function(ev){
              ev.stopPropagation();
              var arr = setsAll();
              arr.push({ id: 'n' + Date.now(), name: nmTxt, desc: '来自优化版槽位（未匹配到参数，可自行补）', from: 'builtin',
                         camera: modelNow(), slots: { 1: null, 2: null, 3: null, 4: null } });
              if(setsSave(arr)){ log('已加入（仅名字）：' + nmTxt, 'ok'); toastMsg('已加入我的方案'); try{ mpRender(); }catch(e){} }
            });
            o.appendChild(b3);
          }
          continue;
        }"""
h = h.replace(old, new, 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('队列 1/2/3/4 全部落地（%+d 字节）' % (len(h) - n0))
print('检查：toc2 兜底 =', '#toc2:not(.open){display:none !important}' in h,
      '| 底栏 static =', h.count('position:static;background:#101010'), '| 仅名字入口 =', '仅名字' in h)
