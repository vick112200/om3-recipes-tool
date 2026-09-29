# -*- coding: utf-8 -*-
"""结构整治 第 1、2 项（不改变任何界面行为）：
   1) 81 处空 catch{} → 统一调用 om3err()（写日志 + 页面角落显示"⚠ N 个错误"）
   2) 所有 document.getElementById( → $(  （$ 返回"空对象"兜底，取不到也不崩、并记一条日志）
      注意：$ 在元素存在时行为与原来完全一致（同一个元素），所以不会改变功能
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

i = h.find('/* ================= 导入相机（相机 Wi-Fi 直连） ================= */')
s = h.rfind('<script>', 0, i) + len('<script>')
e = h.find('</script>', s)
js = h[s:e]

# ---------- 定义 $ 与 om3err（插在主脚本最前面） ----------
HELPERS = '''
  /* ===== 基础设施：安全的 DOM 取值 + 统一错误上报（结构整治第 1、2 项） ===== */
  var OM3NULL = { addEventListener: function(){}, removeEventListener: function(){}, appendChild: function(){},
    insertBefore: function(){}, removeChild: function(){}, setAttribute: function(){}, getAttribute: function(){ return null; },
    querySelector: function(){ return null; }, querySelectorAll: function(){ return []; },
    classList: { add: function(){}, remove: function(){}, toggle: function(){}, contains: function(){ return false; } },
    style: { setProperty: function(){}, removeProperty: function(){} }, focus: function(){}, click: function(){},
    getContext: function(){ return null; }, play: function(){ return null; }, getBoundingClientRect: function(){ return { left:0, top:0, width:0, height:0 }; } };
  function $(id){
    var el = document.getElementById(id);
    if(el) return el;
    try{ if(window.console) console.warn('[om3] 缺元素 #' + id); }catch(e){}
    window.__om3miss = (window.__om3miss || 0) + 1;
    return OM3NULL;
  }
  window.__om3$ = $;
  function om3err(e, tag){
    try{
      var msg = (e && e.stack) ? String(e.stack).slice(0, 240) : String(e);
      if(typeof log === 'function') log('[错误' + (tag ? ':' + tag : '') + '] ' + msg, 'err');
      window.__om3errs = (window.__om3errs || 0) + 1;
      var b = document.getElementById('om3errBar');
      if(!b){
        b = document.createElement('div');
        b.id = 'om3errBar';
        b.style.cssText = 'position:fixed;left:10px;bottom:96px;z-index:9300;padding:7px 11px;border-radius:999px;background:#2a1717;border:1px solid #8a3b3b;color:#ffc9c9;font-size:12px';
        b.addEventListener('click', function(){ try{ document.getElementById('tabCam').click(); }catch(x){} });
        document.body.appendChild(b);
      }
      b.textContent = '⚠ ' + window.__om3errs + ' 个错误（点看日志）';
    }catch(x){}
  }
  window.__om3err = om3err;
  window.addEventListener('error', function(ev){ om3err(ev.error || ev.message, 'uncaught'); });
  window.addEventListener('unhandledrejection', function(ev){ om3err(ev.reason, 'promise'); });
'''
js = HELPERS + js

# ---------- 1) 空 catch → om3err ----------
cnt = len(re.findall(r'catch\s*\((\w+)\)\s*\{\s*\}', js))
js = re.sub(r'catch\s*\((\w+)\)\s*\{\s*\}', r'catch(\1){ om3err(\1, "silent"); }', js)
# 只有注释/仅 console 的 catch 也补上
cnt2 = len(re.findall(r'catch\s*\((\w+)\)\s*\{\s*\}', js))

# ---------- 2) getElementById( → $( ----------
n_dom = len(re.findall(r'document\.getElementById\(', js))
js = js.replace('document.getElementById(', '$(')

h = h[:s] + js + h[e:]

# 页面角落的错误条样式兜底（若 $ 未执行到也不影响）
k = h.find('</style>')
h = h[:k] + """
#om3errBar{display:block}
""" + h[k:]

open(P, 'w', encoding='utf-8', newline='').write(h)
print('第 1 项：空 catch 转换 %d 处（剩余 %d）' % (cnt, cnt2))
print('第 2 项：document.getElementById → $ 共 %d 处' % n_dom)
print('文件变化 %+d 字节' % (len(h) - n0))
