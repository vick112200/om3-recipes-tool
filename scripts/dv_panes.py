# -*- coding: utf-8 -*-
"""结构化定位：#paneA..#paneE 各自在 base.html 里的字节区间、父元素、嵌套深度。

用来确认「#paneD 被嵌进 #paneB 里」这种结构错误，并给出精确的搬运区间。
用法：python scripts/dv_panes.py
"""
import re
import sys
from html.parser import HTMLParser

sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
src = open(P, encoding='utf-8').read()

VOID = {'br', 'img', 'input', 'meta', 'link', 'hr', 'source', 'area', 'base', 'col', 'embed'}


class Walker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack = []          # [(tag, id, start_offset_of_tag)]
        self.panes = {}          # id -> dict

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        eid = d.get('id')
        if eid and eid.startswith('pane') and len(eid) == 5:
            parent = None
            for t, i, off in reversed(self.stack):
                if i:
                    parent = i
                    break
            self.panes[eid] = {
                'start': self.getpos_offset(),
                'depth': len(self.stack),
                'parent': parent,
                'parent_tag': self.stack[-1][0] if self.stack else None,
                'cls': d.get('class', ''),
            }
        if tag not in VOID:
            self.stack.append((tag, eid, self.getpos_offset()))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                t, eid, off = self.stack[i]
                if eid in self.panes and 'end' not in self.panes[eid]:
                    self.panes[eid]['end'] = self.rawdata.find('>', self.getpos_offset()) + 1
                del self.stack[i:]
                break

    def getpos_offset(self):
        line, col = self.getpos()
        # 由 (line, col) 反算偏移
        return self._line_off[line - 1] + col


class W2(Walker):
    def __init__(self, text):
        super().__init__()
        self._line_off = []
        off = 0
        for ln in text.split('\n'):
            self._line_off.append(off)
            off += len(ln) + 1


w = W2(src)
w.feed(src)

print('%-7s %-9s %-9s %-7s %-6s %s' % ('id', 'start', 'end', '父元素', '深度', 'class'))
for k in sorted(w.panes, key=lambda x: w.panes[x]['start']):
    p = w.panes[k]
    print('%-7s %-9s %-9s %-7s %-6s %s' % (k, p['start'], p.get('end', '?'),
                                           p['parent'] or '(body)', p['depth'], p['cls']))

print()
pd = w.panes.get('paneD')
if pd and pd['parent']:
    print('!! paneD 的父元素是 %s（应为 (body)）→ 被嵌在别的页签里了' % pd['parent'])
    print('   paneD 区间: %d ~ %d（长度 %d）' % (pd['start'], pd['end'], pd['end'] - pd['start']))
else:
    print('paneD 父元素正常 =', pd['parent'] if pd else '不存在')
