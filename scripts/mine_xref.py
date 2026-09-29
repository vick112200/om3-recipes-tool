# -*- coding: utf-8 -*-
"""挖掘跨模块引用并输出 JSON（供说明书生成器读取）。
输出结构：{ "module/resource": [ {"owner": "app", "kind": "字段|权限码|路径", "key": "changeRequestId"} ] }"""
import io
import json
import os
import re
from collections import defaultdict

REPO = os.environ.get("LCP_REPO", "D:/workspace/github/lcp-github")
PAGES = os.environ.get("LCPDOC_PAGES", "C:/Users/82302/AppData/Local/Temp/lcp-pages.json")
OUT = os.environ.get("LCPDOC_XREF", "C:/Users/82302/AppData/Local/Temp/lcp-xref.json")

pages = json.load(io.open(PAGES, encoding="utf-8"))["pages"]
cache = {}
for root, _d, fns in os.walk(os.path.join(REPO, "pkg/apis")):
    if "_test" in root:
        continue
    for fn in fns:
        if fn.endswith(".go") and not fn.endswith("_test.go"):
            f = os.path.join(root, fn)
            cache[f] = io.open(f, encoding="utf-8", errors="ignore").read()


def forms(res):
    parts = re.split(r"[-_]", res)
    camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
    sing = camel
    if camel.endswith("ies"):
        sing = camel[:-3] + "y"
    elif camel.endswith("s") and not camel.endswith("ss"):
        sing = camel[:-1]
    return sorted({camel, sing})


found = defaultdict(list)
for p in pages:
    mod, res = p["module"], p["resource"]
    pats = []
    for c in forms(res):
        up = c[0].upper() + c[1:]
        pats += [r'json:"' + c + r'[Ii]d', r'\b' + up + r'ID\b', r'\b' + up + r'Ids\b']
    pats += [re.escape(mod + ":" + res)]
    for f, text in cache.items():
        rel = f.replace(REPO + os.sep, "").replace("\\", "/")
        owner = rel.split("/")[2] if rel.startswith("pkg/apis/") and len(rel.split("/")) > 2 else rel
        if owner == mod or owner.endswith(".go"):
            continue
        for pat in pats:
            m = re.search(pat, text)
            if not m:
                continue
            line = text[:m.start()].count("\n") + 1
            snip = text.splitlines()[line - 1].strip()
            field = re.search(r'json:"([^",]+)', snip)
            perm = re.search(r'"([a-z]+:[a-z-]+:[a-zA-Z]+)', snip)
            key = field.group(1) if field else (perm.group(1) if perm else (m.group(0) if m.group(0) else ""))
            kind = "字段" if field else ("权限码" if perm else "标识符")
            found[mod + "/" + res].append({"owner": owner, "kind": kind, "key": key, "at": rel + ":" + str(line)})
            break

out = {k: sorted(v, key=lambda x: (x["owner"], x["key"])) for k, v in found.items()}
io.open(OUT, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print("wrote", OUT, "pairs:", sum(len(v) for v in out.values()), "pages:", len(out))
