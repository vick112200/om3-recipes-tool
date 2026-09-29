# -*- coding: utf-8 -*-
"""搜索面板开合：用"自己掌权"的写法彻底修掉
   1) 用一个状态变量 + 内联 display !important 强制控制显隐（任何样式表都压不过）
   2) 用捕获阶段监听 + stopPropagation，挡住父层其它处理器在同一次点击里再开它
   3) 面板里加一个 ✕ 关闭按钮，保证任何一个用户都能关掉
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# 替换掉我之前那段 toggle 实现
i = h.find("  /* 第二行搜索框 → 打开搜索/目录面板")
assert i > 0, 'block not found'
j = h.find('})();', i)
assert j > i
j += len('})();')
NEW = '''  /* 第二行搜索框 → 搜索/目录面板：由本函数独占控制开合 */
  (function(){
    var open = false;
    function apply(){
      var p = document.getElementById('toc2');
      if(!p) return;
      try{ p.classList.toggle('open', open); }catch(e){}
      /* 内联 !important：任何样式表或其它处理器都改不动它 */
      try{ p.style.setProperty('display', open ? 'block' : 'none', 'important'); }catch(e){ p.style.display = open ? 'block' : 'none'; }
      var b = document.getElementById('tocbtn');
      if(b) b.setAttribute('aria-expanded', open ? 'true' : 'false');
      /* 面板里塞一个关闭按钮（只塞一次） */
      if(open && !p.querySelector('.om3tocclose')){
        var x = document.createElement('button');
        x.type = 'button'; x.className = 'om3tocclose'; x.textContent = '✕ 关闭';
        x.addEventListener('click', function(ev){ ev.stopPropagation(); open = false; apply(); });
        p.insertBefore(x, p.firstChild);
      }
    }
    function toggle(ev){
      if(ev){ try{ ev.stopPropagation(); ev.preventDefault(); }catch(e){} }
      open = !open;
      apply();
      if(open){ try{ var inp2 = document.getElementById('toc2').querySelector('input'); if(inp2) inp2.focus(); }catch(e){} log('已打开搜索 / 目录'); }
    }
    window.__om3tocToggle = toggle;
    document.addEventListener('click', function(ev){
      var t = ev.target;
      while(t && t !== document){
        if(t.id === 'tocbtn'){ toggle(ev); return; }
        t = t.parentNode;
      }
    }, true);                       /* 捕获阶段：抢在别的处理器之前，并阻止它们继续 */
    document.addEventListener('keydown', function(ev){
      if((ev.key === 'Enter' || ev.key === ' ') && document.activeElement && document.activeElement.id === 'tocbtn'){ toggle(ev); }
      if(ev.key === 'Escape' && open){ open = false; apply(); }
    }, true);
  })();'''
h = h[:i] + NEW + h[j:]

# 关闭按钮样式
k = h.find('</style>')
h = h[:k] + """
#toc2 .om3tocclose{display:block;width:calc(100% - 24px);margin:10px 12px 4px;padding:9px;border-radius:9px;border:1px solid #33507e;background:#1b2436;color:#cfe0ff;font-size:13px}
""" + h[k:]

open(P, 'w', encoding='utf-8', newline='').write(h)
print('搜索面板开合已改为"独占控制"（%+d 字节）' % (len(h) - n0))
