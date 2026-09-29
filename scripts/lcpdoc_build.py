# -*- coding: utf-8 -*-
"""把「代码抽取的页面清单」+「人写的叙述」拼成一份自包含的 HTML 功能说明书。"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lcpdoc_narrative import LAYERS, MODULE_META, SCENARIOS  # noqa: E402
from lcpdoc_pagedesc import PAGE_DESC  # noqa: E402
from lcpdoc_detail import MODULE_DETAIL, CROSS_USAGE  # noqa: E402
from lcpdoc_howto import PAGE_HOWTO, PAGE_PIT  # noqa: E402

TMP = "C:/Users/82302/AppData/Local/Temp"
REPO = "D:/workspace/github/lcp-github"
OUT = os.path.join(REPO, "docs", "LCP功能说明书.html")

PAGES_JSON = os.environ.get("LCPDOC_PAGES", "C:/Users/82302/AppData/Local/Temp/lcp-pages.json")
XREF_JSON = os.environ.get("LCPDOC_XREF", "C:/Users/82302/AppData/Local/Temp/lcp-xref.json")
xref_raw = json.load(io.open(XREF_JSON, encoding="utf-8")) if os.path.exists(XREF_JSON) else {}
xref = {}
for k, v in xref_raw.items():
    seen = {}
    for item in v:
        seen.setdefault(item["owner"], set()).add(item["key"])
    xref[k] = {o: sorted(ks) for o, ks in sorted(seen.items())}
data = json.load(io.open(PAGES_JSON, encoding="utf-8"))
pages = data["pages"]

# ---------- 附录 D 的页面一句话 ----------
summaries = {}
md = io.open(os.path.join(REPO, "docs", "端到端回归测试总纲.md"), encoding="utf-8").read()
for line in md.splitlines():
    m = re.match(r"^\|\s*([^|]+?)\s*\|\s*(.+?)\s*\|\s*(?:✅|◐|❌)", line)
    if not m:
        continue
    name, desc = m.group(1), m.group(2)
    if name in ("页面", "---") or name.startswith(":"):
        continue
    summaries.setdefault(name, desc)

# ---------- K8s 资源 kind ----------
kube_src = io.open(os.path.join(REPO, "ui/src/modules/kube/lib/kube-resources.ts"), encoding="utf-8").read()
kube_labels = {}
loc_dir = os.path.join(REPO, "ui/src/i18n/locales/zh-CN")
for fn in os.listdir(loc_dir):
    if fn.endswith(".ts"):
        for m in re.finditer(r'^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"',
                             io.open(os.path.join(loc_dir, fn), encoding="utf-8").read(), re.M):
            kube_labels[m.group(1)] = m.group(2)
kube = []
for line in kube_src.splitlines():
    m = re.match(r'\s*\{ key: "([^"]+)",\s*kind: "([^"]+)",\s*group: "([^"]*)",\s*version: "([^"]+)",\s*resource: "([^"]+)"', line)
    if not m:
        continue

    def g(k):
        mm = re.search(k + r':\s*"?([^",}]+)"?', line)
        return mm.group(1).strip() if mm else ""

    kube.append({
        "key": m.group(1), "kind": m.group(2), "group": m.group(3), "resource": m.group(5),
        "namespaced": "namespaced: true" in line,
        "navGroup": g("navGroup"),
        "name": kube_labels.get(g("labelKey"), m.group(2)),
        "hideFromNav": "hideFromNav: true" in line,
    })

# ---------- 场景反查：页面 -> 场景 ----------
scene_of = {}
def add_scene(pid, key):
    scene_of.setdefault(key, [])
    if pid not in scene_of[key]:
        scene_of[key].append(pid)
for sc in SCENARIOS:
    for step in sc["steps"]:
        add_scene(sc["id"], step[0])

KUBE_GROUP_NAME = {"workloads": "工作负载", "config": "配置", "network": "网络",
                   "storage": "存储", "cluster": "集群", "accessControl": "权限",
                   "custom": "扩展"}

ACTION_CN = {"restore": "恢复", "transfer": "转移", "stop": "停止", "proxy": "代理转发", "reboot": "重启", "shutdown": "关机", "power-on": "开机", "console": "控制台",
             "agent": "装/卸 agent", "exec": "容器内执行", "execute": "执行", "deploy": "部署",
             "snapshot": "快照", "change-password": "改密码", "reset-password": "重置密码",
             "reveal": "查看明文", "purge": "彻底删除", "add-nodes": "加节点",
             "remove-nodes": "移除节点", "cancel": "取消", "suspend": "暂停",
             "lifecycle": "生命周期", "chat": "对话"}
VERB_NAME = {"list": "查看列表", "get": "查看详情", "create": "新建", "update": "编辑",
             "patch": "修改", "delete": "删除", "deleteCollection": "批量删除"}


def rich(s):
    s = esc(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    return s


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def page_id(mod, res):
    return "page-" + mod + "-" + re.sub(r"[^a-z0-9]+", "-", res.lower())


def page_label(mod, res):
    for p in pages:
        if p["module"] == mod and p["resource"] == res:
            return p["name"]
    return res


# ---------- 模块顺序（按导航顺序） ----------
mod_order, seen = [], set()
for p in pages:
    if p["module"] not in seen:
        seen.add(p["module"])
        mod_order.append(p["module"])

# ---------- 渲染 ----------
H = []
A = H.append

A('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">')
A('<meta name="viewport" content="width=device-width,initial-scale=1">')
A('<title>LCP 功能说明书</title>')
A('<style>')
A(io.open(os.path.join(TMP, "lcpdoc.css"), encoding="utf-8").read())
A('</style></head><body>')

# 顶栏
A('<header class="top">')
A('<div class="brand"><span class="logo">LCP</span><div><h1>功能说明书</h1>'
  '<p class="sub">按「页面」和「场景」两条线读：先看场景知道要干什么，再点进页面知道在哪干。</p></div></div>')
A('<div class="tools">')
A('<input id="q" type="search" placeholder="搜索页面 / 场景 / 权限码…（按 / 聚焦）" autocomplete="off">')
A('<button id="clear" class="ghost" hidden>清空</button>')
A('<span id="hits" class="hits"></span>')
A('</div>')
A('<div class="chips" id="modchips"></div>')
A('</header>')

A('<div class="layout">')
A('<nav class="side"><div class="sideinner" id="side"></div></nav>')
A('<main id="main">')

# ---------- 概览 ----------
A('<section id="overview" class="sec">')
A('<h2>这份文档怎么用</h2>')
A('<div class="callout"><p><b>只看一个页面，通常看不出它是干嘛的。</b>'
  '比如「声明值」单独看像个字段编辑器，放到「资产录入」这条链里才知道它是双态模型的另一半：'
  '写下去的是“应该是什么”，然后由「配置漂移」拿它跟实际值比对。'
  '所以这份文档把<b>场景</b>放在<b>页面</b>前面：场景告诉你一条链上依次用哪几个页面，页面告诉你那一页具体在哪一步、和谁交接。</p></div>')
A('<ol class="how">')
A('<li><b>找事做</b>：看下面十个场景，找到和你目标最像的那个，照着步骤走。</li>')
A('<li><b>找页面</b>：用顶部搜索（页面名 / 权限码 / 场景名都能搜），或按模块筛。</li>')
A('<li><b>看关系</b>：每个页面卡片里「交接给谁 / 依赖谁」和「出现在哪些场景」都点得动。</li>')
A('</ol>')
A('<div class="stats" id="stats"></div>')
A('<h3>平台分层</h3><p class="muted">一个页面属于哪一层，决定了它和谁交接：越靠下越稳定、越靠上越常改。'
  '同一件事的“配置面”和“使用面”常常分在不同层，比如放置策略（底座）被应用拓扑（交付）引用。</p>')
A('<div class="layers">')
for key, name, color, desc in LAYERS:
    mods = [m for m in mod_order if MODULE_META.get(m, ("", "", ""))[1] == key]
    A(f'<div class="layer" style="--c:{color}"><h4>{esc(name)}</h4><p>{esc(desc)}</p>'
      f'<div class="chips small">' + "".join(
        f'<a class="chip" href="#mod-{m}">{esc(MODULE_META.get(m,("","",""))[0] or m)}</a>' for m in mods) +
      '</div></div>')
A('</div></section>')

# ---------- 概念 ----------
A('<section id="concepts" class="sec"><h2>先记住四个概念</h2>')
A('<div class="cols">')
A('<div class="box"><h4>① 三级作用域：平台 / 租户 / 项目</h4>'
  '<p>页面右上角切换。同一个页面在三个层级下打的是不同数据：平台看全局，租户看本部门，项目看本项目。'
  '<b>菜单变少不是 bug</b>——多数资源只在特定层级注册。资源归属链：平台 → 租户（workspace）→ 项目（namespace）。</p></div>')
A('<div class="box"><h4>② 权限码 = 模块:资源:动词</h4>'
  '<p>例如 <code>compute:hosts:create</code>。角色里存的是<b>通配符规则</b>（<code>*:*</code>、<code>*:list</code>、'
  '<code>dev:issues:*</code>），通过前缀/后缀匹配展开成具体权限码。所以「加一个新页面」不用给角色补授权，'
  '除非那个角色的规则是逐条枚举的。</p></div>')
A('<div class="box"><h4>③ 一个「页面」通常是一个资源的三件套</h4>'
  '<p>列表页（查找/筛选）→ 详情页（点名称进去，含 Tab）→ 动作（页面上的按钮：重启、同步、备份、导出……）。'
  '页面卡片里的「能做什么」就是按注册的权限码与接口路径自动列出来的，所见即系统真有的能力。</p></div>')
A('<div class="box"><h4>④ 数据不会自己出现：先有来源，再有视图</h4>'
  '<p>监控要先配端点、成本要先有价目、CMDB 要先有模型与关系、告警要有人认领才会找到人。'
  '「空态」多数不是 bug，是上游没配。每个场景都标了前置条件。</p></div>')
A('</div></section>')

# ---------- 场景 ----------
A('<section id="scenes" class="sec"><h2>场景走查</h2>'
  '<p class="muted">每个场景是一串页面调用：<b>用哪个页面 → 做什么 → 产出什么</b>。'
  '步骤里的页面名可点，跳到下面的页面详解；页面卡片里也会反向列出它属于哪些场景。</p>')
for sc in SCENARIOS:
    A(f'<article class="scene" id="scene-{sc["id"]}">')
    A(f'<h3>{esc(sc["title"])}</h3>')
    A(f'<p class="goal">{esc(sc["goal"])}</p>')
    A(f'<p class="prereq"><b>前置：</b>{esc(sc["prereq"])}</p>')
    A('<ol class="steps">')
    for key, what, result in sc["steps"]:
        mod, res = key.split("/")
        A('<li>')
        A(f'<div class="stephead"><a class="pagelink" href="#{page_id(mod,res)}">'
          f'{esc(page_label(mod,res))}</a><span class="modtag">{esc(MODULE_META.get(mod,("","",""))[0] or mod)}</span></div>')
        A(f'<div class="what">{esc(what)}</div><div class="result">{esc(result)}</div>')
        A('</li>')
    A('</ol>')
    A(f'<p class="notes"><b>边界与坑：</b>{esc(sc["notes"])}</p>')
    A('</article>')
A('</section>')

# ---------- 页面详解 ----------
A('<section id="pages" class="sec"><h2>页面详解</h2>'
  '<p class="muted">按模块分组。每个模块先给一段定位（它解决什么、依赖谁、被谁依赖、关键交接点），再逐页给出：'
  '作用域、能做什么（按权限码自动生成）、以及它和其它页面的关系。</p>')
for mod in mod_order:
    if mod not in MODULE_META:
        continue
    name, layer, intro, deps, used_by, handoff = MODULE_META[mod]
    layer_name = dict((k, n) for k, n, _c, _d in LAYERS).get(layer, layer)
    A(f'<section class="mod" id="mod-{mod}">')
    A(f'<h3>{esc(name)} <span class="pill">{esc(layer_name)}</span></h3>')
    A(f'<p class="intro">{esc(intro)}</p>')
    detail = MODULE_DETAIL.get(mod, [])
    if detail:
        A('<ul class="detail">')
        for d in detail:
            d = esc(d)
            d = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', d)
            d = re.sub(r'`([^`]+)`', r'<code>\1</code>', d)
            A(f'<li>{d}</li>')
        A('</ul>')
    A('<div class="relbar">')
    if deps:
        A('<div><span class="k">依赖</span>' + "".join(
            f'<a class="chip rel" href="#mod-{d}">{esc(MODULE_META.get(d,("",))[0] or d)}</a>' for d in deps) + '</div>')
    if used_by:
        A('<div><span class="k">被依赖</span>' + "".join(
            f'<a class="chip rel" href="#mod-{d}">{esc(MODULE_META.get(d,("",))[0] or d)}</a>' if d in MODULE_META else f'<span class="chip">{esc(d)}</span>'
            for d in used_by) + '</div>')
    A(f'<div><span class="k">交接点</span><span class="handoff">{esc(handoff)}</span></div>')
    A('</div>')
    for p in [x for x in pages if x["module"] == mod]:
        pid = page_id(mod, p["resource"])
        SCOPE_CN = {"platform": "平台", "workspace": "租户", "namespace": "项目"}
        scopes = "".join(f'<span class="scope s-{s}" title="{SCOPE_CN[s]}级">'
                         f'{SCOPE_CN[s]}</span>' for s in p["scopes"]) or '<span class="scope">—</span>'
        verbs = "".join(f'<span class="verb">{esc(VERB_NAME.get(v, v))}</span>' for v in p["verbs"])
        extras = "".join(f'<span class="verb act">{esc(ACTION_CN.get(e, e))}</span>' for e in p["extras"][:12])
        desc = PAGE_DESC.get(f'{mod}/{p["resource"]}', "") or summaries.get(p["name"], "")
        A(f'<article class="page" id="{pid}" data-mod="{mod}" data-key="{mod}/{p["resource"]}" '
          f'data-text="{esc(p["name"] + " " + p["resource"] + " " + (p["permission"] or "") + " " + desc + " " + " ".join(p["verbs"] + p["extras"]))}">')
        A(f'<div class="phead"><h4>{esc(p["name"])}</h4>'
          f'<code class="route">/{mod}/{p["resource"]}</code>{scopes}')
        A(f'<span class="perm">{esc(p["permission"] or "")}</span></div>')
        if desc:
            A(f'<p class="desc">{rich(desc)}</p>')
        howto = PAGE_HOWTO.get(f'{mod}/{p["resource"]}')
        if howto:
            A(f'<p class="howto"><span class="k">怎么用</span>{rich(howto)}</p>')
        if verbs or extras:
            A(f'<div class="caps">{verbs}{extras}</div>')
        pit = PAGE_PIT.get(f'{mod}/{p["resource"]}')
        if pit:
            A(f'<p class="pit"><span class="k">坑</span>{rich(pit)}</p>')
        used = xref.get(f'{mod}/{p["resource"]}')
        if used:
            chips = []
            for owner, keys in list(used.items())[:14]:
                label = MODULE_META.get(owner, (owner,))[0] if owner in MODULE_META else owner
                title = esc("、".join(keys[:6]))
                href = f'#mod-{owner}' if owner in MODULE_META else '#pages'
                chips.append(f'<a class="chip rel" href="{href}" title="{title}">{esc(label)}</a>')
            n = len(used)
            A(f'<div class="links"><span class="k">被引用</span>'
              f'<span class="hint">别处 {n} 个模块会用到它</span>' + "".join(chips) + '</div>')
        sibs = [x for x in pages if x["module"] == mod and x["resource"] != p["resource"]][:8]
        if sibs:
            A('<div class="links"><span class="k">同模块</span>' + "".join(
                f'<a class="chip" href="#{page_id(mod, s["resource"])}">{esc(s["name"])}</a>' for s in sibs) + '</div>')
        if scene_of.get(f'{mod}/{p["resource"]}'):
            A('<div class="links"><span class="k">出现在场景</span>' + "".join(
                f'<a class="chip scene" href="#scene-{sid}">{esc(next(s["title"] for s in SCENARIOS if s["id"] == sid).split("·")[0].strip())}</a>'
                for sid in scene_of[f'{mod}/{p["resource"]}']) + '</div>')
        A('</article>')
    A('</section>')

# K8s 资源浏览器
A('<section class="mod" id="mod-kube-resources"><h3>K8s 资源浏览器 <span class="pill">平台服务</span></h3>'
  '<p class="intro">「Kubernetes 集群」页进去之后的资源浏览器：50 多种 kind 用同一套列表/详情渲染，'
  '分组与集群页一致。它们共用权限 <code>kube:clusters:resources:list</code>，所以能看到集群不代表能看到全部 kind'
  '（部分 kind 需要集群装了对应 API group 才出现）。</p>')
A('<div class="kube">')
for k in kube:
    cls = "kubeitem hidden" if k["hideFromNav"] else "kubeitem"
    A(f'<span class="{cls}"><b>{esc(k["name"])}</b><i>{esc(k["kind"])}</i>'
      f'<em>{esc(k["group"] or "core/v1")}</em>{"<u>命名空间级</u>" if k["namespaced"] else "<u>集群级</u>"}'
      f'<s>{esc(KUBE_GROUP_NAME.get(k["navGroup"], k["navGroup"]))}</s></span>')
A('</div><p class="muted">灰底的是默认不在侧边栏出现的 kind（由别处跳进来）。</p></section>')

# ---------- 模块关系矩阵 ----------
A('<section id="map" class="sec"><h2>模块之间怎么交接</h2>'
  '<p class="muted">下表读法：行是「谁」，列是它依赖的模块（有格子=有交接）。'
  '更完整的说明在每个模块标题下的「依赖 / 被依赖 / 交接点」。</p>')
A('<div class="matrixwrap"><table class="matrix"><thead><tr><th></th>')
for m in mod_order:
    A(f'<th title="{esc(MODULE_META.get(m,("",))[0] or m)}">{esc((MODULE_META.get(m,("",))[0] or m)[:4])}</th>')
A('</tr></thead><tbody>')
for m in mod_order:
    deps = MODULE_META.get(m, ("", "", "", [], [], ""))[3]
    A(f'<tr><th><a href="#mod-{m}">{esc(MODULE_META.get(m,("",))[0] or m)}</a></th>')
    for n in mod_order:
        A('<td class="on"></td>' if n in deps else '<td></td>')
    A('</tr>')
A('</tbody></table></div>')
A('</section>')

# ---------- 附录 ----------
A('<section id="crossusage" class="sec"><h2>跨模块用法：一个页面在别处怎么被用到</h2>'
  '<p class="muted">这些不是猜的，是从代码里挖出来的字段/权限引用（<code>pkg/apis</code> 里别的模块出现了这个资源的 ID 或权限码），'
  '再加上「它到底解决了什么问题」。看这一节能回答最常见的一类问题：<b>这个页面配的东西，什么时候生效？</b></p>')
A('<div class="usages">')
for a, b, note in CROSS_USAGE:
    am, ar = a.split('/')
    bm, br = b.split('/')
    A(f'<div class="usage"><div class="uhead">'
      f'<a class="pagelink" href="#{page_id(am,ar)}">{esc(page_label(am,ar))}</a>'
      f'<span class="arrow">用到</span>'
      f'<a class="pagelink" href="#{page_id(bm,br)}">{esc(page_label(bm,br))}</a></div>'
      f'<div class="unote">{rich(note)}</div></div>')
A('</div></section>')

A('<section id="appendix" class="sec"><h2>附录</h2>')
A('<h3>术语表</h3><table class="terms"><tbody>')
for t, d in [
    ("作用域（scope）", "平台 / 租户 / 项目三级；页面注册在哪些层级决定它在哪个层级可见。"),
    ("租户 / 项目", "租户=workspace（部门/大组），项目=namespace（一套应用与环境的落地单元）。"),
    ("CI", "配置项，CMDB 里的一条资产记录；主机、数据库实例、应用服务都是 CI。"),
    ("双态模型", "每个字段有「声明值」（应该是什么）与「观测值」（实际是什么），不一致就是漂移。"),
    ("发现 ≠ 纳管", "扫描/发现只把对象找出来，纳管（装 agent、录台账、指派负责人）是另一步。"),
    ("封网（freeze）", "变更窗口的一种：期间高危变更被拦，声明豁免的照常，遵守封网的操作被按住等解冻。"),
    ("审批网关（gate rules）", "声明「哪个动作要审批、要不要遵守封网」的规则表；被门控的写操作会生成待办与待执行操作。"),
    ("deferred action", "审批通过后真正执行的队列：可撤回、可重新执行。"),
    ("计量口径", "成本按「分配量 × 时长」计，不按实际使用量；使用量只用于效率分析。"),
    ("分配量 vs 使用量", "分配量=分给它的规格（如 8C16G），使用量=实际跑掉的（如 1.2C）。"),
    ("agent", "装在主机上的采集/执行组件；监控、日志、巡检、脚本执行都依赖它。"),
    ("凭据（credential）", "pki 里加密存储的登录凭据，按作用域隔离，接口从不回显明文。"),
    ("端点（endpoint）", "o11y 里指标/日志/链路三个写入地址 + SD token，是监控数据的总开关。"),
]:
    A(f'<tr><th>{esc(t)}</th><td>{esc(d)}</td></tr>')
A('</tbody></table>')

A('<h3>权限、角色与可见性</h3>')
A('<div class="cols"><div class="box"><h4>内置角色</h4><ul>'
  '<li>平台/租户/项目 <b>Admin</b>：规则 <code>*:*</code>，全部权限。</li>'
  '<li>平台/租户/项目 <b>Viewer</b>：规则 <code>*:list</code> + <code>*:get</code>，只读。</li>'
  '<li>租户 Member：基础成员，权限按需另授。</li></ul>'
  '<p class="muted">新建的权限码会被 <code>*:*</code> 与 <code>*:list</code> 自动覆盖；'
  '只有逐条枚举权限码的自建角色需要手工补。</p></div>')
A('<div class="box"><h4>页面看不到时的排查顺序</h4><ol>'
  '<li>右上角作用域对不对（该资源可能只在平台级注册）。</li>'
  '<li>用角色管理查这个权限码给了谁。</li>'
  '<li>资源本身是不是「发现但未纳管」——那种对象不在列表里。</li>'
  '<li>最后才怀疑空数据：用审计日志反查有没有人真的建过。</li></ol></div></div>')

A('<h3>封网期间还能做什么</h3>')
A('<ul class="plain">'
  '<li><b>能</b>：看所有页面、发起审批、点单（申请会排队）、确认/静默告警、处理工单、导出报表。</li>'
  '<li><b>被按住</b>：声明「遵守封网」的已批准操作、自动履行的开通动作——解冻后继续，不丢失。</li>'
  '<li><b>被拦</b>：落在封网窗口里的例行变更；需要显式豁免并留痕。</li>'
  '<li>判断依据永远是 <code>cmdb/change-windows</code> + <code>workflow/gate-rules</code> 两张表，不靠约定。</li></ul>')

A('<h3>审批与封网的实现要点</h3>')
A('<ul class="plain">'
  '<li><b>引擎无状态</b>：流程推进靠 SQL 原子 claim（<code>UPDATE ... WHERE state = ...</code>），'
  '没有 leader election，多实例同时跑也不会重复推进。</li>'
  '<li><b>三个生产方</b>：模块提交 subject + hooks（审批通过后回调执行）、网关拦截高危写操作生成待执行项、'
  '定时/超时扫描推进 SLA 与升级。</li>'
  '<li><b>封网三处接线</b>：变更窗口（时间判定）、网关规则（是否遵守封网）、待执行操作（被按住后解冻续跑）。'
  '三处任一没配，封网就不会按预期生效——排障时三处都要看。</li>'
  '<li><b>通知回流</b>：审批事件是通知模块的第一个消费方，所以渠道不通会表现为「审批没人知道」。</li>'
  '</ul>')
A('<h3>这份文档怎么维护</h3>')
A('<p>页面清单、作用域、权限码、动作是从代码生成的（<code>ui/src/core/registry/nav-config.ts</code> + '
  '各模块 <code>install.go</code> 注册的权限表），所以<b>不会和系统脱节</b>；'
  '场景与页面用途是人工写的，加页面/改流程时需要跟着改。'
  '新增页面时的最小动作：确认它属于哪个模块的哪条链、补一句「它和谁交接」、在相关场景里加一步。</p>')
A('</section>')

A('</main></div>')
A('<button id="totop" title="回到顶部">↑</button>')

# ---------- 脚本 ----------
A('<script>')
A('const PAGES = ' + json.dumps([{
    "id": page_id(p["module"], p["resource"]), "mod": p["module"], "name": p["name"],
    "res": p["resource"], "perm": p["permission"] or "", "scopes": p["scopes"],
    "verbs": p["verbs"], "extras": p["extras"], "scenes": scene_of.get(f'{p["module"]}/{p["resource"]}', []),
} for p in pages], ensure_ascii=False) + ';')
A('const SCENES = ' + json.dumps([{"id": s["id"], "title": s["title"], "text": s["title"] + " " + s["goal"]} for s in SCENARIOS], ensure_ascii=False) + ';')
A('const MODS = ' + json.dumps([{"key": m, "name": MODULE_META.get(m, ("",))[0] or m,
                                 "count": len([x for x in pages if x["module"] == m])} for m in mod_order], ensure_ascii=False) + ';')
A(io.open(os.path.join(TMP, "lcpdoc.js"), encoding="utf-8").read())
A('</script></body></html>')

html = "\n".join(H)
io.open(OUT, "w", encoding="utf-8", newline="\n").write(html)
print("wrote", OUT)
print("pages:", len(pages), "kube kinds:", len(kube), "scenarios:", len(SCENARIOS), "size:", len(html))
