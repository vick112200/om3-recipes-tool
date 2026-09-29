# -*- coding: utf-8 -*-
"""修「连接相机」页签空白：#paneD 被嵌在 #paneB 里面了，把它搬成 body 的直接子元素。

真因：点「连接相机」时 JS 确实给 #paneD 去掉了 hide，但 #paneD 是 #paneB 的子元素，
而 #paneB 是 display:none（优化版页签没打开）→ 父元素不可见，子元素再"显示"也看不见。
（旧的 verify_all.py 只查元素自己有没有 hide 类，不查祖先，所以报了假通过。）

做法：用 HTMLParser 精确定位 #paneD 的字节区间，剪切出来，插到 #paneC 之前（body 层级）。
幂等：已经是 body 的子元素就直接跳过。
用法：python scripts/patch_paned_move.py
"""
import sys
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'

VOID = {'br', 'img', 'input', 'meta', 'link', 'hr', 'source', 'area', 'base', 'col', 'embed'}


class Parser(HTMLParser):
    """记录每个 <div id="paneX"> 的起始偏移、父 id、以及匹配的结束偏移。"""

    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text = text
        self.line_off = []
        off = 0
        for ln in text.split('\n'):
            self.line_off.append(off)
            off += len(ln) + 1
        self.stack = []
        self.panes = {}

    def _off(self):
        line, col = self.getpos()
        return self.line_off[line - 1] + col

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        eid = d.get('id')
        if eid and eid.startswith('pane') and len(eid) == 5:
            parent = None
            for t, i, o in reversed(self.stack):
                if i:
                    parent = i
                    break
            self.panes[eid] = {'start': self._off(), 'parent': parent, 'depth': len(self.stack)}
        if tag not in VOID:
            self.stack.append((tag, eid, self._off()))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                t, eid, off = self.stack[i]
                if eid in self.panes and 'end' not in self.panes[eid]:
                    self.panes[eid]['end'] = self.text.find('>', self._off()) + 1
                del self.stack[i:]
                break


h = open(P, encoding='utf-8').read()
n0 = len(h)

ps = Parser(h)
ps.feed(h)

d = ps.panes.get('paneD')
assert d, '找不到 #paneD'
assert 'end' in d, '#paneD 的结束标签没匹配上，中止'
assert d['parent'] is not None or True

if d['parent'] is None:
    print('已是 body 的直接子元素，无需搬运（幂等）')
    sys.exit(0)

print('搬运前：#paneD 父元素 = %s，区间 %d~%d（%d 字节）' % (d['parent'], d['start'], d['end'], d['end'] - d['start']))

block = h[d['start']:d['end']]
assert block.startswith('<div id="paneD"'), '区间起点不是 #paneD：%r' % block[:60]
assert block.endswith('</div>'), '区间终点不是 </div>：%r' % block[-60:]

# 插入点：#paneC 的起点（body 层级，正好在 #paneB 结束之后）
c = ps.panes.get('paneC')
assert c, '找不到 #paneC'
insert_at = c['start']

# 先剪切，再把插入点按被剪掉的长度左移
h2 = h[:d['start']] + h[d['end']:]
new_insert = insert_at - (d['end'] - d['start']) if insert_at > d['end'] else insert_at
h2 = h2[:new_insert] + block + '\n' + h2[new_insert:]

open(P, 'w', encoding='utf-8', newline='').write(h2)

# 复验
chk = Parser(h2)
chk.feed(h2)
nd = chk.panes['paneD']
print('搬运后：#paneD 父元素 = %s（期望 (body)）' % (nd['parent'] or '(body)'))
assert nd['parent'] is None, '搬运失败，父元素仍是 %s' % nd['parent']
for k in ('paneA', 'paneB', 'paneC', 'paneD', 'paneE'):
    p = chk.panes.get(k)
    if p:
        print('  %-6s 父=%-8s 区间 %d~%d' % (k, p['parent'] or '(body)', p['start'], p.get('end', -1)))
print('已修（%+d 字节）' % (len(h2) - n0))
