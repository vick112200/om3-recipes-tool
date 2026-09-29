#!/usr/bin/env python3
# 从代码里抽取「页面清单」，作为 LCP 功能说明书的骨架数据。
# 数据来源（都以仓库实际代码为准，不手抄）：
#   1. ui/src/core/registry/nav-config.ts  → 每个导航页面：模块/资源/权限/分组/作用域
#   2. ui/src/modules/kube/lib/kube-resources.ts → K8s 资源浏览器的各 kind
#   3. ui/src/i18n/locales/zh-CN/*.ts      → 中文名（nav.* 与分组名）
#   4. ui/src/modules/*/defs.ts            → 哪些资源有详情页（detailParam）
#   5. perms.json（从 lcp-dev 库导出的 permissions 表）→ 每个资源实际注册的动词与动作
import io
import json
import os
import re
import sys
from collections import defaultdict

REPO = "D:/workspace/github/lcp-github"
OUT = "C:/Users/82302/AppData/Local/Temp/lcp-pages.json"

# ---------- 1. i18n 中文标签 ----------
labels = {}
loc_dir = os.path.join(REPO, "ui/src/i18n/locales/zh-CN")
for fn in os.listdir(loc_dir):
    if not fn.endswith(".ts"):
        continue
    text = io.open(os.path.join(loc_dir, fn), encoding="utf-8").read()
    for m in re.finditer(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"', text, re.M):
        labels[m.group(1)] = m.group(2)

# ---------- 2. NAV_ITEMS ----------
nav_text = io.open(os.path.join(REPO, "ui/src/core/registry/nav-config.ts"), encoding="utf-8").read()
items = []
for line in nav_text.splitlines():
    if "resource:" not in line or "module:" not in line:
        continue
    def grab(key):
        m = re.search(key + r':\s*"([^"]*)"', line)
        return m.group(1) if m else None
    scopes = re.search(r"scopes:\s*\[([^\]]*)\]", line)
    items.append({
        "resource": grab("resource"),
        "module": grab("module"),
        "permission": grab("permission"),
        "labelKey": grab("labelKey"),
        "group": grab("group"),
        "parentGroup": grab("parentGroup"),
        "scopes": [s.strip().strip('"') for s in scopes.group(1).split(",")] if scopes else [],
        "hideFromNav": "hideFromNav: true" in line,
    })

# ---------- 3. K8s 资源浏览器 ----------
kube_text = io.open(os.path.join(REPO, "ui/src/modules/kube/lib/kube-resources.ts"), encoding="utf-8").read()
kube_group_labels = dict(re.findall(r'(\w+):\s*"(nav\.kube\w+)"', kube_text))
kube_items = []
for m in re.finditer(r"\{\s*key:\s*\"([^\"]+)\",(.*?)\n  \}", kube_text, re.S):
    body = m.group(2)
    def g(k):
        mm = re.search(k + r':\s*"([^"]*)"', body)
        return mm.group(1) if mm else None
    kube_items.append({
        "key": m.group(1),
        "labelKey": g("labelKey"),
        "navGroup": g("navGroup"),
        "namespaced": "namespaced: true" in body,
        "group": g("group") or "",
        "resource": g("resource"),
        "requiresApiGroup": g("requiresApiGroup"),
        "hideFromNav": "hideFromNav: true" in body,
    })

# ---------- 4. 详情页 ----------
detail = {}
for mod in sorted(os.listdir(os.path.join(REPO, "ui/src/modules"))):
    p = os.path.join(REPO, "ui/src/modules", mod, "defs.ts")
    if not os.path.exists(p):
        continue
    text = io.open(p, encoding="utf-8").read()
    for m in re.finditer(r"module:\s*\"(\w+)\",\s*name:\s*\"([\w/-]+)\",(.*?)\}\)", text, re.S):
        body = m.group(3)
        dp = re.search(r'detailParam:\s*"(\w+)"', body)
        detail[(m.group(1), m.group(2))] = dp.group(1) if dp else None

# ---------- 5. 权限 → 资源能力 ----------
perms = json.load(io.open("C:/Users/82302/AppData/Local/Temp/perms.json", encoding="utf-8"))
VERBS = {"list", "get", "create", "update", "patch", "delete", "deleteCollection"}
cap = defaultdict(lambda: {"verbs": set(), "extras": set(), "paths": set(), "scopes": set()})
for p in perms:
    code, path, scope = p["code"], p["path"], p["scope"]
    parts = code.split(":")
    if len(parts) < 3:
        continue
    mod, res = parts[0], parts[1]
    # 只把「资源自身」的动词算进去；子资源的动词归到子资源名下
    if len(parts) == 3:
        verb = parts[2]
        if verb in VERBS:
            cap[(mod, res)]["verbs"].add(verb)
            cap[(mod, res)]["paths"].add(path)
            cap[(mod, res)]["scopes"].add(scope)
        else:
            # 第 3 段不是 CRUD 动词，就是这一页的动作（重启/关机/快照/改密码…）
            cap[(mod, res)]["extras"].add(verb)
    else:
        # 子资源 / 动作：/api/<mod>/v1/<res>/{id}/<x> 形状，取最后一段做人话
        seg = parts[-1]
        if seg not in VERBS:
            cap[(mod, res)]["extras"].add(seg)

# 把 path 里 id 后面的动作段也提取出来（那些 action 的权限码就是 <mod>:<res>:<verb>，见上）
for p in perms:
    m = re.match(r"/api/(\w+)/v\d+/([\w-]+)(?:\{[\w]*\})?/([\w-]+)$", p["path"])
    if m:
        cap[(m.group(1), m.group(2))]["extras"].add(m.group(3))

pages = []
for it in items:
    key = (it["module"], it["resource"])
    c = cap.get(key, {"verbs": set(), "extras": set(), "scopes": set()})
    pages.append({
        **it,
        "name": labels.get(it["labelKey"] or "", it["labelKey"]),
        "groupName": labels.get(it["group"] or "", None),
        "parentName": labels.get(it["parentGroup"] or "", None),
        "detailParam": detail.get(key),
        "verbs": sorted(c["verbs"]),
        "extras": sorted(x for x in c["extras"] if x not in VERBS),
    })

kube_pages = []
for k in kube_items:
    kube_pages.append({
        "key": k["key"],
        "name": labels.get(k["labelKey"] or "", k["key"]),
        "navGroup": k["navGroup"],
        "groupName": labels.get(kube_group_labels.get(k["navGroup"] or "", ""), k["navGroup"]),
        "namespaced": k["namespaced"],
        "group": k["group"],
        "resource": k["resource"],
        "requiresApiGroup": k["requiresApiGroup"],
        "hideFromNav": k["hideFromNav"],
    })

data = {"pages": pages, "kubePages": kube_pages}
json.dump(data, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------- 摘要打印 ----------
by_mod = defaultdict(list)
for p in pages:
    by_mod[p["module"]].append(p)
print(f"页面（含隐藏）共 {len(pages)} 个，模块 {len(by_mod)} 个；K8s 资源 kind {len(kube_pages)} 个")
print()
for mod in sorted(by_mod):
    print(f"## {mod}  ({len(by_mod[mod])})")
    for p in by_mod[mod]:
        g = f"{p['parentName'] or ''}/{p['groupName'] or ''}".strip("/")
        print(f"   {p['resource']:<28} {p['name']:<22} scopes={'+'.join(s[:2] for s in p['scopes']):<10} "
              f"grp={g:<28} verbs={','.join(p['verbs']):<40} extras={','.join(p['extras'][:6])}")
