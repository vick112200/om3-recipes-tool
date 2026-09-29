# -*- coding: utf-8 -*-
"""跨模块引用挖掘（三个信号，都来自代码）：
1) JSON 字段/Go 标识符：别的模块的结构体里出现 <资源单数>Id（如 ciGroupId、placementPolicyId）
2) 权限码字符串：别的模块代码里出现 "<他模块>:<资源>:<动词>"（说明它代理/内嵌了那个资源）
3) 接口路径字符串：别的模块代码里出现 /api/<他模块>/v<n>/<资源>
"""
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


def forms(res):
    parts = re.split(r"[-_]", res)
    camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
    sing = camel
    if camel.endswith("ies"):
        sing = camel[:-3] + "y"
    elif camel.endswith("s") and not camel.endswith("ss"):
        sing = camel[:-1]
    out = {camel, sing}
    return sorted(out)


out = defaultdict(set)
for p in pages:
    mod, res = p["module"], p["resource"]
    pats = []
    for c in forms(res):
        up = c[0].upper() + c[1:]
        pats += [r'json:"' + c + r'[Ii]d', r'\b' + up + r'ID\b', r'\b' + up + r'Ids\b']
    pats += [re.escape(mod + ":" + res), re.escape("/" + res + "/" ), re.escape("/" + res + "?")]
    for f, text in cache.items():
        rel = f.replace(REPO + os.sep, "").replace("\\", "/")
        owner = rel.split("/")[2] if rel.startswith("pkg/apis/") and len(rel.split("/")) > 2 else rel
        if owner == mod:
            continue
        for pat in pats:
            for m in re.finditer(pat, text):
                line = text[:m.start()].count("\n") + 1
                snip = text.splitlines()[line - 1].strip()[:105]
                out[(mod + "/" + res, owner)].add((rel + ":" + str(line), pat[:24], snip))
                break

for (key, owner), ev in sorted(out.items()):
    ev = sorted(ev)[:3]
    for i, (loc, pat, snip) in enumerate(ev):
        head = "%-32s <- %-10s" % (key, owner) if i == 0 else "%-32s    %-10s" % ("", "")
        print("%s %-46s %s" % (head, loc, snip))
print()
print("共 %d 对" % len(out))
