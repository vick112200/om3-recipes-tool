# -*- coding: utf-8 -*-
"""把 xref3 挖出来的 283 对压成「用户可见的耦合」清单：只保留 JSON 字段、
权限码、接口路径三类证据，并给出字段名/权限码。"""
import io
import re
from collections import defaultdict

rows = []
cur = None
for line in io.open("C:/Users/82302/AppData/Local/Temp/xref3.txt", encoding="utf-8"):
    m = re.match(r"^(\S+/\S+)\s+<- (\S+)\s+(\S+)\s+(.*)$", line)
    if m:
        cur = (m.group(1), m.group(2))
        snip = m.group(4)
    else:
        m2 = re.match(r"^\s+(\S+)\s+(.*)$", line)
        if not m2 or not cur:
            continue
        snip = m2.group(2)
    field = re.search(r'json:"([^",]+)', snip)
    perm = re.search(r'"([a-z]+:[a-z-]+:[a-zA-Z]+)', snip)
    route = re.search(r'"(/api/[^"]*?)"', snip)
    kind = "字段" if field else ("权限码" if perm else ("路径" if route else None))
    if not kind:
        continue
    key = field.group(1) if field else (perm.group(1) if perm else route.group(1))
    if kind == "路径" and re.search(r"/(hooks|routes|logs|providers)\b", snip):
        continue
    rows.append((cur[1], cur[0], kind, key))

by_owner = defaultdict(set)
for owner, target, kind, key in rows:
    by_owner[owner].add((target, kind, key))

for owner in sorted(by_owner):
    print("### %s 用到了：" % owner)
    for target, kind, key in sorted(by_owner[owner]):
        print("   %-30s [%s] %s" % (target, kind, key))
