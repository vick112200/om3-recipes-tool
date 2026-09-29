# -*- coding: utf-8 -*-
"""挖跨模块引用：某个模块的页面/字段被别的模块用到哪里。
证据来自 pkg/apis 的 Go 代码（标识符）与 ui 的跨模块查询，不靠猜。"""
import io
import json
import os
import re
import subprocess
from collections import defaultdict

REPO = os.environ.get("LCP_REPO", "D:/workspace/github/lcp-github")
pages = json.load(io.open(os.environ.get("LCPDOC_PAGES", "C:/Users/82302/AppData/Local/Temp/lcp-pages.json"),
                          encoding="utf-8"))["pages"]

# 资源 -> 可能的标识符写法
def idents(res):
    parts = re.split(r"[-_]", res)
    camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
    pascal = "".join(p.capitalize() for p in parts)
    out = {camel, pascal, camel[0].upper() + camel[1:], camel + "Id", camel + "ID",
           pascal + "Id", pascal + "ID"}
    return sorted(out)


files = []
for root, _dirs, fns in os.walk(os.path.join(REPO, "pkg/apis")):
    if "_test" in root:
        continue
    for fn in fns:
        if fn.endswith(".go") and not fn.endswith("_test.go"):
            files.append(os.path.join(root, fn))
cache = {}
for f in files:
    cache[f] = io.open(f, encoding="utf-8", errors="ignore").read()

result = defaultdict(list)
for p in pages:
    mod, res = p["module"], p["resource"]
    for ident in idents(res):
        pat = re.compile(r"\b" + re.escape(ident) + r"\b")
        for f, text in cache.items():
            rel = f.replace(REPO + os.sep, "").replace("\\", "/")
            owner = rel.split("/")[2] if rel.startswith("pkg/apis/") and len(rel.split("/")) > 2 else "?"
            if owner == mod:
                continue
            for m in pat.finditer(text):
                line = text[:m.start()].count("\n") + 1
                snippet = text.splitlines()[line - 1].strip()[:110]
                result[f"{mod}/{res}"].append((owner, ident, rel + ":" + str(line), snippet))
                break

for key in sorted(result):
    hits = result[key]
    by_mod = defaultdict(list)
    for owner, ident, loc, snip in hits:
        if len(by_mod[owner]) < 2:
            by_mod[owner].append((ident, loc, snip))
    print("##", key)
    for owner in sorted(by_mod):
        for ident, loc, snip in by_mod[owner]:
            print(f"   <- {owner:<10} {ident:<22} {loc:<52} {snip}")
