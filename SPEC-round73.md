# 第 73 轮：修「点『连接相机 → 测试页』却回到配方合集」

> 需求方 2026-09-28：「**点击连接相机测试页，直接回到了配方合集，看看怎么回事**」。
>
> 排查结论：**两个 bug 叠在一起**，都用无头实测钉住了（不是猜）。修完点测试页就是测试页。
> 只改页面；出包 **v3.25**。

**回退点**：`app/base.before_r73.html`（= v3.24 源码，md5 `87cd50d120ae70d2ed55f2cb3bc2186a`）。
**生成脚本** `scripts/gen_r73.py`（2 步）；**探针** `scripts/dv_r73.py`（**26/26**）。

---

## 1. 范围与「必须显式声明清单」

| 项 | 说明 |
|---|---|
| 输入 | `app/base.html`（v3.24）；涉及：块07 的"页签转发"委托（把 `data-p` 派发到真实页签按钮）、`#paneT`（第 68 轮加的测试页）、`#paneD`（连接相机页）、`#tabTest`（隐藏代理页签） |
| 输出 | 改后的 `app/base.html`；`gen_r73.py`；`dv_r73.py`；本规格；出包 **v3.25** |
| 前置条件 | 过 `check_syntax`/`live_check`；**老 id 一个不少**；**本轮不新增 id**；搬动前后全文件 `<div>`/`</div>` 计数不变（配平） |
| 后置条件 | ① 点「🔧 测试页」→ 真的进测试页（配方合集/连接相机都收起来）② `#paneT` 是 `body` 的直接子元素，不再受 `#paneD` 显隐牵连 ③ 页签转发改成映射表：**以后加页签漏一个分支会打日志告警**，不再静默兜底 |
| 权限 | **不涉及** |
| 幂等 | **涉及**：标记 `r73：测试页搬出 paneD`；2 步每步都必须"真的改到东西" |
| 事务/并发 | **不涉及** |
| 数据迁移 | **不涉及**（只搬 DOM 节点，**id 全不动** → 所有 `getElementById` 继续有效） |
| 性能 | **不涉及** |
| 安全 | **不涉及** |
| 兼容性 | 隐藏代理页签 `#tabTest` 仍在（老逻辑/其它入口若引用它，行为不变） |
| 失败回退 | `cp app/base.before_r73.html app/base.html`；不重出包则无影响 |
| 明确不做 | ① 不动 Java ② 不重构页签体系（只补 T + 改表）③ 不新增 id ④ 不动 `#paneE`（见 §7 遗留） |

---

## 2. 真因（**两条，都有实测证据**）

### bug ① 页签转发漏了 `T` → 静默兜底成"配方合集"

块07 有一个 document 级（**捕获阶段**）委托，专门把"代理页签/底栏按钮"上的 `data-p` 派发到真实页签按钮：

```js
// 第 39 轮留下的嵌套三元（注释还写着"F 也要转发到自己的代理，否则会兜底到内置配方"）
var top = $(dp === 'E' ? 'tabMine' : (dp === 'D' ? 'tabCam' : (dp === 'B' ? 'tabB'
          : (dp === 'C' ? 'tabC' : (dp === 'F' ? 'tabF' : 'tabBuiltin')))));
if(top && top !== btn){ top.click(); }      // ← data-p="T" 落到 tabBuiltin！
```

第 68 轮加的测试页用的是 `data-p="T"`，**这条链里没有 `T` 分支** → 兜底成 `tabBuiltin`（配方合集）→
点「测试页」实际**程序化点击了"配方合集"**。实测（劫持 `HTMLElement.prototype.click` 记录谁被点了）：

```
程序化点击过的按钮 = camMenuBtn, BUTTON, tabTest, tabBuiltin
                                              ^^^^^^^^^^ 就是它把你弹回配方合集
```

### bug ② 测试页被嵌在「连接相机」页里面

用浏览器的真实父链一量就露馅：

```
#paneT → 父元素 div#paneD → body        ← 第 68 轮插入位置错了
```

后果：`#paneD` 一被 `.hide`（`display:none`），**里面的 `#paneT` 跟着一起消失**；
反过来在测试页上"连接相机页"的显隐也会牵连它。实测修前 `paneT` 的可见高度是 **0**，
修后是 **2131 px**（真的占满屏）。

> 两个 bug 是**叠加**的：① 让你被弹回配方合集，② 让测试页根本没法独立显示。只修一个都不够。

---

## 3. 改了什么

| # | 改动 | 说明 |
|---|---|---|
| **UC-R73-01** | 把 `#paneT` 从 `#paneD` 里搬出来 | 用**按 `<div>` 配平**的切割器整体搬（只搬 DOM 节点、**id 一个不改**），落在 `#paneD` 闭合标签之后，成为 `body` 的直接子元素，与 `#paneA/#paneB/…` 平级；原地留注释说明 |
| **UC-R73-02** | 页签转发改成**映射表** | `var TABP = { A:'tabBuiltin', B:'tabB', C:'tabC', D:'tabCam', E:'tabMine', F:'tabF', T:'tabTest' };` + `$(TABP[dp] \|\| 'tabBuiltin')`；**再遇到不认识的 `data-p` 就打一条 warn 日志**（不再静默兜底） |

**判据（防再犯）**：`dv_r73` 断言 ① `TABP` 表在且含 `T` ② 老的嵌套三元已删 ③ **`#paneT` 的父元素是 body**
④ 点测试页时的"程序化点击记录"里**不许出现 `tabBuiltin`**。

---

## 4. 实施方式 / 验收标准

```bash
python scripts/gen_r73.py            # 幂等（跑两次）
python scripts/check_syntax.py
python scripts/live_check.py         # 错误数=0 且与改前逐字段一致
python scripts/check_app.py          # 四数与改前一致
python scripts/verify_all.py
python scripts/dv_r73.py             # 本轮探针（26/26，含程序化点击记录）
python scripts/dv_r72.py / dv_r71.py / dv_r70.py / dv_r69.py / dv_r68.py / dv_r67.py / dv_r64.py / dv_r62.py
cd apk && bash build.sh              # → v3.25
```

**逐条验收点**
1. `dv_r73` 全绿：进测试页 **不再偷偷点 `tabBuiltin`**、`paneA`/`paneD` 都藏、`paneT` 显示且高度 > 300px、
   `cur=T`；从测试页能回配方合集、能去连接相机；直接点隐藏代理 `#tabTest` 也正常。
2. 静态：`TABP` 含 `T`；`#paneT` 父元素是 body；六个 pane 都在；老 id 一个不少；不新增 id。
3. `check_syntax`/`live_check` 错误数 0；`check_app` 四数与改前一致；`verify_all` 通过；防回归全绿。
4. 出包 **v3.25**，桌面已更新；APK 内页面复验。

---

## 5. 验收结果 / 差异分析

### 5.1 逐条验收（2026-09-28 实跑）

| # | 验收点 | 结果 |
|---|---|---|
| 1 | `gen_r73.py` 幂等 | ✅ 2 步；第二次打印"已经是目标状态"；搬动前后 `<div>`/`</div>` 计数不变 |
| 2 | `check_syntax` / `live_check` | ✅ 全过 / `错误数=0` 且与改前逐字段一致 |
| 3 | `check_app` / `verify_all` | ✅ 四数与改前**完全一致** / 退出码 0 |
| 4 | **`dv_r73.py`** | ✅ **26/26** |
| 5 | 防回归 | ✅ `dv_r72` 20/20、`dv_r71` 28/28、`dv_r70` 25/25、`dv_r69` 42/42、`dv_r68` 43/43、`dv_r67` 40/40、`dv_r64` 61/61、`dv_r62` 41/41 |
| 6 | 出包 | ✅ **v3.25（build 325）**，md5 `b454c50fbe2f4c8a8af798a8e63cacce`（79,304,841 字节），桌面已更新，签名同一把 `om3.jks` |
| 7 | 产物里真有本轮改动 | ✅ 读 APK 内 `assets/index.html`（3,849,430 字节）：`r73`×2、`TABP`×3、`r72`×6、`setTocBtn`×5 |

**改动规模**：页面 3,848,370 → **3,849,150** 字节（净增 780：主要是那段搬家注释 + 映射表），20,9xx 行。
`app/base.html` md5：`87cd50d120ae70d2ed55f2cb3bc2186a` → **`d88c5305fcbd4c48b4f4648df1a0ac29`**。
**Java / 清单 / 构建脚本：一个字节都没动；本轮不新增 id。**

### 5.2 无头实测拿到的原始证据（摘）

修前（v3.24）：
```
点完后 cur=T | paneA=pane(可见!) paneD=pane,hide paneT=pane
程序化点击过的按钮 = camMenuBtn, BUTTON, tabTest, tabBuiltin      ← 点了配方合集
paneA top=63 h=8284 ; paneT top=0 h=0                            ← 测试页高度 0（被嵌在隐藏的 paneD 里）
#paneT 父链：div#paneT.pane < div#paneD.pane < body
```
修后（v3.25）：
```
点完后 cur=T | paneA=pane,hide paneD=pane,hide paneT=pane
程序化点击过的按钮 = camMenuBtn, BUTTON, tabTest                   ← 不再点 tabBuiltin
paneA top=0 h=0 ; paneT top=63 h=2131                            ← 测试页真的占屏幕
#paneT 父链：div#paneT.pane < body
```

### 5.3 差异分析（规格 vs 实现）

| # | 规格原定 | 实际 | 结论 |
|---|---|---|---|
| 1 | 我以为只是"页签转发漏了 T" | 追下去发现**测试页的 DOM 位置也是错的**（嵌在 `#paneD` 里），两个 bug 互相掩盖 | **改代码（多修一个）**：本轮同时做"搬出来 + 补表"，`dv_r73` 两条都钉住 |
| 2 | 原本打算用"正则删除 + 在别处插入"来搬家 | 那样很容易切错（`#paneT` 里有嵌套 div） | **改实现**：写了个按 `<div>/</div>` **配平**的切割器，并断言"全文件 div 数不变 + 块内配平" |
| 3 | 第 68 轮的探针只断言了 `paneT 可见/隐藏` | 它**没有检查 DOM 嵌套**，所以这个 bug 从第 68 轮活到今天（用户先发现） | **改探针**：`dv_r73` 增加"父元素必须是 body"的结构断言 + "程序化点击记录里不许出现 tabBuiltin" —— 这一类"能点亮但不在对的地方"以后跑不掉了 |

### 5.4 这轮的教训（给以后）

- **`data-p` 这类"转发映射"必须唯一真源**：写成嵌套三元，加页签时漏一个分支就**静默**走兜底（第 39 轮 F 踩过一次，第 68 轮 T 又踩一次）。现在是映射表 + 未知值打 warn。
- **"某页可见" 不等于 "某页在对的位置"**：新加的整页（pane）必须断言**父元素是 body**，否则它会被某个隐藏页吞掉。

---

## 6. 真机测试单

连接相机的完整真机测试流程写在 **`TEST-camera.md`**（三轮：连得上 / 连上能干活 / 坏了能恢复；含"日志怎么给我"）。
本轮修完，测试单 §5 里的"测试页能不能进"一项应该从"会被弹回配方合集"变成"正常进入"。

---

## 7. 遗留

1. **`#paneE`（我的配方）在源码里的嵌套仍有点歪**：HTML 里 `#noresult2` 那处 `<div …></nav>` 标签不配对，
   浏览器会自行容错（实测 `#paneE` 显示正常、四数没变），所以本轮**没动它**——它属于"整理 HTML 结构"的活，
   真要做建议单独一轮（改完必须重跑全部探针 + 四数）。
2. 真机验证（`TEST-camera.md`）待需求方执行。
3. 旧候选：`set_timeout?timeoutsec=1800`、快门线、camprop（第 65/66 轮）。