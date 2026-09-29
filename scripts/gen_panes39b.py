# -*- coding: utf-8 -*-
"""第 39 轮（A2）：把"哪几个页签才显示底栏 / 搜索行"的判断从写死的 A|B|C 扩到含 F。
（不改的话：切到「本站设计」页签时底栏 #barABC 与搜索行 #row2 会一起消失。）"""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')
p = r'D:\workspace\om3-handbook\app\base.html'
s = io.open(p, encoding='utf-8').read()
pairs = [
 ("abc.classList.toggle('show', p === 'A' || p === 'B' || p === 'C');",
  "abc.classList.toggle('show', p === 'A' || p === 'F' || p === 'B' || p === 'C');"),
 ("if(r2) r2.style.display = (p === 'A' || p === 'B' || p === 'C') ? 'flex' : 'none';",
  "if(r2) r2.style.display = (p === 'A' || p === 'F' || p === 'B' || p === 'C') ? 'flex' : 'none';"),
 ("if(abc) abc.classList.toggle('show', p==='A'||p==='B'||p==='C');",
  "if(abc) abc.classList.toggle('show', p==='A'||p==='F'||p==='B'||p==='C');"),
 ("if(r2) r2.style.display = (p==='A'||p==='B'||p==='C') ? 'flex' : 'none';",
  "if(r2) r2.style.display = (p==='A'||p==='F'||p==='B'||p==='C') ? 'flex' : 'none';"),
]
n = 0
for a, b in pairs:
    if a in s:
        s = s.replace(a, b, 1); n += 1
    else:
        print('  ⚠ 没找到（可能已改）：%s' % a[:56])
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('✅ 显示条件补了 %d 处' % n)
