# -*- coding: utf-8 -*-
"""场景对比第二批修正：
- 全屏标题拼干净的「名称 · 作者（槽位）」，不再把槽位标签贴到作者后面
- 关闭全屏 / 切到对比页签时，立即刷新「第几张」的计数（原来依赖 scroll 事件，页签隐藏时量不到宽度）
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
P = BASE + r'\app\base.html'
h = open(P, encoding='utf-8').read()

js_start = h.find("(function () {\n  'use strict';")
js_end = h.find('</script>', js_start)
assert js_start > 0 < js_end
js = h[js_start:js_end]

REPL = []

REPL.append((
    """        return '<div class="scslide" data-cid="' + esc(it.i || '') + '">' +""",
    """        return '<div class="scslide" data-cid="' + esc(it.i || '') + '" data-lt="' +
          esc(it.n + ' · ' + it.a + (it.sl ? '（' + it.sl + '）' : '')) + '">' +"""))

REPL.append((
    """    if (c) c.classList.toggle('hide', p !== 'C');
    if (tc) tc.style.display = (p === 'C') ? 'none' : '';""",
    """    if (c) c.classList.toggle('hide', p !== 'C');
    if (tc) tc.style.display = (p === 'C') ? 'none' : '';
    if (p === 'C') setTimeout(function () { if (window.__scPos) window.__scPos(); }, 80);"""))

REPL.append((
    """        title = nm ? nm.textContent : '';""",
    """        title = (slide && slide.getAttribute('data-lt')) || (nm ? nm.textContent : '');"""))

REPL.append((
    """      scpos.textContent = (i + 1) + ' – ' + Math.min(n, i + p) + ' / ' + n;
    }""",
    """      scpos.textContent = (i + 1) + ' – ' + Math.min(n, i + p) + ' / ' + n;
    }
    window.__scPos = upd;"""))

REPL.append((
    """      if (sl0 && first && groupPager.contains(sl0)) groupPager.scrollLeft = sl0.offsetLeft - first.offsetLeft;""",
    """      if (sl0 && first && groupPager.contains(sl0)) groupPager.scrollLeft = sl0.offsetLeft - first.offsetLeft;
      if (window.__scPos) setTimeout(window.__scPos, 120);"""))

for old, new in REPL:
    assert js.count(old) == 1, ('锚点命中 %d 次: %s' % (js.count(old), old[:50]))
    js = js.replace(old, new, 1)

h = h[:js_start] + js + h[js_end:]
open(BASE + r'\app_extra.js', 'w', encoding='utf-8', newline='').write(js)
open(P, 'w', encoding='utf-8', newline='').write(h)
print('第二批：JS 修正 %d 处，base.html %.1f KB' % (len(REPL), len(h.encode('utf-8')) / 1024))
