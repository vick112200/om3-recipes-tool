# -*- coding: utf-8 -*-
"""精确版跨模块引用挖掘：只看 JSON 字段名（xxxId）与 Go 里的 XxxID 标识符，
避免英文单词（hooks/routes/providers）造成的噪声。"""
import io
import json
import os
import re
from collections import defaultdict

REPO = "D:/workspace/github/lcp-github"
pages = json.load(io.open("C:/Users/82302/AppData/Local/Temp/lcp-pages.json", encoding="utf-8"))["pages"]
cache = {}
for root, _d, fns in os.walk(os.path.join(REPO, "pkg/apis")):
    if "_test" in root:
        continue
    for fn in fns:
        if fn.endswith(".go") and not fn.endswith("_test.go"):
            f = os.path.join(root, fn)
            cache[f] = io.open(f, encoding="utf-8", errors="ignore").read()


def camel(res):
    parts = re.split(r"[-_]", res)
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


out = defaultdict(set)
for p in pages:
    mod, res = p["module"], p["resource"]
    c = camel(res)
    pats = [r'json:"' + c + r'[Ii]d', r'\b' + c[0].upper() + c[1:] + r'ID\b',
            r'\b' + c + r'IDs\b', r'\b' + c[0].upper() + c[1:] + r'Ids\b']
    for f, text in cache.items():
        rel = f.replace(REPO + os.sep, "").replace("\\", "/")
        owner = rel.split("/")[2] if rel.startswith("pkg/apis/") and len(rel.split("/")) > 2 else rel
        if owner == mod:
            continue
        for pat in pats:
            for m in re.finditer(pat, text):
                line = text[:m.start()].count("\n") + 1
                snip = text.splitlines()[line - 1].strip()[:100]
                out[(mod + "/" + res, owner)].add((rel + ":" + str(line), snip))

for (key, owner), ev in sorted(out.items()):
    ev = sorted(ev)
    print("%-34s <- %-9s %-46s %s" % (key, owner, ev[0][0], ev[0][1]))
    if len(ev) > 1:
        print("%-34s    %-9s %-46s %s" % ("", "", ev[1][0], ev[1][1]))
print()
print("共 %d 对跨模块引用" % len(out))
