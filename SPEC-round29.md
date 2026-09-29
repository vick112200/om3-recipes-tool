# SPEC-round29.md · v2.16（第三十轮）

> 本轮三件事，全部来自用户 2026-09-24 的原话：
> 1. **「方案挂载状态先改一下，我感觉现在这个有个挂载未生效的很奇怪，按理说要么挂载要么没挂」**
> 2. **「自动连接…体验一般，因为那里有好几个按钮，这个按钮也比较小还有个连接相机的按钮会产生歧义」**
> 3. **「点了写入下面底部栏消失了 / 拖到底出现底部栏，但是只有三个按钮了」**
>    + 「我觉得你那个底栏丢失可能是因为点了写入多了一堆内容导致的布局失效了，先看一遍代码能不能看出问题，我不想专门调日志」
>
> 结论先说：**第 3 件在代码里找到了根因，并且用探针复刻出了与用户截图完全一致的数值**（见 §1）。

---

## 0. 本轮做了什么（一眼版）

| # | 改动 | 类型 | 依据 |
|---|---|---|---|
| 1 | 底栏：删掉 `overflow-x:auto`；`pinBars()` 按 `visualViewport` 实测钉住；祖先有 transform/filter 时把底栏**搬到 body**；每秒/切步骤/切页签/滚动/转屏都重钉 | **修 bug（真机）** | 用户 3 张截图 + 探针复刻（§1） |
| 2 | 方案挂载状态：三态 → **两态**（未挂载 / 已挂载）；写入成功即「已挂载」；重启后自动核对**不一致**→ 自动打回「未挂载」 | 改口径（用户选定） | 用户第 1 句 + AskUserQuestion 选项 1 |
| 3 | 「连接相机」页：**合并成一个按钮**（先直连 → 不行再用记住的凭据 → 提示扫码）；旧的直连按钮收进「连不上？更多方式」折叠 | 改交互（用户选定） | 用户第 2 句 + AskUserQuestion 选项 1 |

版本：**v2.16**（`versionCode 216`）。构建前的源码快照 = `app/base.before_r30.html`（= v2.15，md5 `b09fd5264aef93c3aa8596b9512a7efb`）。

---

## 1. 底栏丢失 / 只剩三个按钮：根因与修法

### 1.1 用户的现象（三张截图）

| 截图 | 现象 |
|---|---|
| ① 连接页（第 1 步） | 底栏正常：贴屏幕底、4 个按钮（连接 / 安全备份 / 写入 / 记录） |
| ② 点了「写入」之后 | **底栏没了** |
| ③ 拖到页面最底 | 底栏出现，但**只有三个按钮**（写入高亮，第 4 个「记录」不见了） |

### 1.2 代码级根因（用户"看代码"要求的就是这一段）

```css
/* base.html（v2.15 及以前） */
.barABC,.barD{display:none;gap:6px;position:fixed;left:0;right:0;bottom:0;z-index:9000;…}
.barABC,.barD{flex-wrap:nowrap;overflow-x:auto}   /* ← 上一轮为了"4 个按钮都能滚到"加的 */
```

`overflow-x:auto` 让底栏**自己变成一个可滚动容器**。两个后果，正好对应两张截图：

1. **fixed 失效 / 被按"文档末尾的一块"排版** → 页面一长（点了写入，第 3 步多出表单 + 日志框），底栏就跑到文档最下面：**要滚到底才看得见**（截图 ②③）。
   为什么"连接页看着正常"？因为第 1 步内容短，文档末尾正好落在屏幕底部 —— 看起来像钉住了（截图 ①）。**用户自己的猜测是对的**（"点了写入多了一堆内容导致的布局失效"）。
2. **宽度按布局视口算** → 底栏比屏幕宽时，`flex:1 1 0` 的 4 个按钮按更宽的盒等分，**第 4 个被挤到屏幕外**（截图 ③只剩三个）。

### 1.3 复刻证据（本地，可重复）

`python scripts/dv_barstep3.py` —— 复刻用户操作（打开 cam-on → 点底栏「写入」→ 把第 3 步日志框塞满 40 行 → 滚到底），
再**人为把底栏弄歪**（`position:static`）以模拟真机状态，量到的数字：

```
弄歪后：position=static rect.y=1294（文档末尾，低于屏幕 548px）width=526 第4个按钮 right=534 → 看不见
```

**与用户截图完全一致**（要滚到底才出现 + 只剩三个按钮）。修完之后：

```
弄歪→自愈后：position=fixed 距底=0px 宽=526 ≤ 526 按钮=1:可见 2:可见 3:可见 4:可见
```

> ⚠ 旧探针 `dv_barprobe.py` **从来没量到过第 3 步**：它没打开 cam-on，`showStep(2/3/4)` 被"未连接"守卫拦回第 1 步 —— 所以上一轮"本地量不出问题"是**探针口径错了**，不是环境差异。这条已写进 HANDOVER §七。

### 1.4 修法（5 条，全在 `app/base.html`）

| 位置 | 改法 |
|---|---|
| CSS `.barABC,.barD` | `overflow-x:auto` → **`overflow:hidden`**（底栏永远不再是滚动容器，4 个按钮等分可见）；`.barABC,.barD,.mpbar` 加 `width:100vw;max-width:100vw;box-sizing:border-box` |
| 新 `pinBar(el)` | 用**实测**值钉：`position:fixed` + `left`/`width` 取 **min(visualViewport.width, innerWidth, documentElement.clientWidth)**（不管缩放 / overview / 布局视口比屏幕宽，都不会超屏）；视口被平移或缩放（`offsetLeft/offsetTop/scale`）时改用 `top` 计算，避免 `bottom:0` 跑到看不见的地方 |
| 新 `unnestBar(el)` | 祖先链上若有 `transform / filter / perspective / will-change / contain / backdrop-filter` → 说明 `fixed` 会按那个祖先定位 → **把底栏搬到 `body` 下**（结构性根治，写日志说明） |
| `pinBars()` 调用点 | 启动、`setBarH` 三处、`resize`、`orientationchange`、`scroll`（passive）、每秒自检、`showStep`、`applyModule`、`switchPane` |
| `barChk()` | 除"没贴屏幕底"外，新增"**底栏比屏幕宽**"这一路诊断（带底栏宽 / 视口宽 / 布局宽 / 横向溢出 / 缩放 / dpr / 祖先链） |

---

## 2. 方案「挂载状态」：三态 → 两态

**用户选定**：*"写入成功就算已挂载；重启后自动核对不一致 → 自动变回未挂载"*。

| 项 | v2.15 及以前 | v2.16 |
|---|---|---|
| 界面 | 未挂载 / **待重启确认** / 已确认在相机上（三态） | **未挂载 / 已挂载**（两态） |
| 写入成功 | 标 `pending`（待重启确认） | **直接标 `on`（已挂载）** |
| 核对一致 | `pending` → `on` | 仍是 `on`（日志"核对一致"） |
| 核对**不一致** | 只写日志（状态不变） | **自动打回「未挂载」+ 日志写明**（新函数 `mpMarkUnmount`） |
| 老数据 `pending` | 显示"待重启确认" | `mountOf()` 一律按**已挂载**显示（**不做数据迁移**） |
| 弹窗选项 | 3 个 | **2 个**（未挂载 / 已挂载） |

**为什么"核对不一致要自动打回"**：两态口径下"写完即绿"，如果写入其实没生效，列表上就会一直挂个假绿标 —— 必须有这条兜底才诚实。
打回**只认待校验记录里的 `setId`**：从「连接相机」页写的配方没有 `setId` → 不动任何方案状态（原有行为不变）。

---

## 3. 「连接相机」按钮合并

**用户选定**：*"合并成一个「连接相机」大按钮：先直连扫热点 → 不行再用记住的凭据连 → 都不行提示扫码"*。

- 首屏只剩 **2 个大按钮**：「扫二维码（第一次）」「连接相机」。
- 点「连接相机」→ 先走 `camDirectConnect()`（扫附近 Wi-Fi → 挑出像相机的热点 → 记住过密码就直接连，没记住就问一次，**不猜密码**）。
- **直连走不通就自动退回 `connectNow()`**（用记住的凭据走 `requestNetwork`）。为此给 `camDirectConnect(onFail)` 的每个死路都接上了回调：
  没有扫 Wi-Fi 接口 / 手机 Wi-Fi 关着 / 没权限 / 扫不到任何热点 / 没找到像相机的热点。
- 旧的直连按钮 `#camGateDirect` **不删**（保住 `dv_camclean` 的"控件一个没丢"口径），移进「连不上？更多方式」折叠，
  改名「只连相机热点（相机 Wi-Fi 已开时最快）」，绑定不变（`window.__om3direct` 仍在）。
- 日志会写清这一轮走的哪条路（`[连接相机] 直连走不通（原因）→ 改用「记住的凭据」这条路`）。

---

## 4. 显式声明清单（guardrails：需求里只提一次的约束，全部落到代码）

| 约束 | 本轮是否涉及 | 落到哪里 |
|---|---|---|
| 并发（同时点两下 / 两个任务） | ∉ | 写入仍是"一次一个任务"（`runTask` 原有互斥），本轮没动 |
| 幂等（重复执行安全） | ✓ | `pinBars()` 幂等（每秒重复设置同样的值）；重复点「连接相机」= 重复尝试连接（原有语义） |
| 权限（相机侧 / 系统侧） | ✓ | 直连失败给出"附近的设备 / 位置信息"权限指引；老版本缺 `CHANGE_NETWORK_STATE` 时给手动连的退路（原有） |
| 原子性（要么全成要么全不成） | ✓ | 挂载状态只有两态：写入抛错 → 到不了标记那行（不假报）；核对不一致 → 自动打回（不留假绿标） |
| 边界（0 / 空 / 超长 / 超时） | ✓ | 底栏宽度取三视口最小值（超宽场景）；`#camOut3` 40 行日志下底栏仍钉住；挂载文案最长组合「录像档5 · 已挂载（槽1、2、3、4）」不撑出横向滚动 |
| 超时 / 重试 | ✓ | 直连失败自动退回第二条路（不是"死路"）；扫不到热点不再直接 `return` |
| 异步（await / 竞态） | ✓ | `pinBars()` 只读视口 + 写样式，不碰业务状态；`camDirectConnect(onFail)` 回调可能同步触发 `connectNow()`（无 await 竞态） |
| 状态机（状态全枚举） | ✓ | 挂载：`''` / `on`（历史值 `pending` 归到 `on`），枚举在 `mountOf()` 一处 |
| 性能 | ✓ | 每秒 `pinBars()` 只做几次 `setProperty` + 一次 `getBoundingClientRect`（可忽略） |
| 兼容（老数据 / 老机型） | ✓ | 老数据 `pending` 不迁移、按两态显示；`visualViewport` 不存在时退回 `innerWidth`/`innerHeight` |
| 迁移（要不要动老数据） | ✓（明确**不做**） | 不写迁移代码：`mountOf()` 在读取时归一，写回时才变成 `'on'` |

---

## 5. 验收（本机全过，真机待用户装 v2.16）

| 脚本 | 结果 |
|---|---|
| `scripts/dv_barstep3.py`（**新**：复刻"点写入→内容变多→滚到底" + 弄歪→自愈） | 9 项断言全过 |
| `scripts/dv_barchk.py`（改：**同步**跑诊断 + 新增"弄歪后必须自愈/宽度收回/4 个按钮都在") | 9 项全过 |
| `scripts/dv_barprobe.py`（①~④ 四步各量一次） | 全过 |
| `scripts/dv_mount.py`（改：两态 + **新增 8b「核对不一致自动打回」** + 老数据 `pending` 显示） | 全过（含 20+ 项 ★） |
| `scripts/dv_blecam.py`（改：合并后手点「连接相机」仍能连） | 5 段全过 |
| `check_app / live_check / verify_all` | 四数 `om3errs=0 / 加入方案按钮=81 / 方案条目数=1 / 运行错误=0` |
| `dv_camclean / dv_mpwrite / dv_mpflow / dv_mpwheel / dv_mplayout / dv_slotren / dv_write new / dv_writeproto / dv_import / dv_model / dv_round24 / dv_audit_static / dv_stubguard / dv_asyncguard` | 全过（22 个脚本一轮全绿） |

产物：`apk/build/om3.apk`（`versionCode 216` / `versionName 2.16`），已复制到桌面。

---

## 6. 差异分析（规格 vs 实现）与逐条回退清单

### 6.1 差异分析

| 规格点 | 实现情况 |
|---|---|
| §1 底栏不再丢 / 不再少按钮 | ✅ CSS（overflow）+ `pinBar`（实测钉）+ `unnestBar`（搬家）+ 调用点齐全 |
| §1 "看代码就能看出问题" | ✅ 根因写在 §1.2（`overflow-x:auto` 让底栏成为滚动容器）；探针复刻数值与截图一致 |
| §2 两态 + 不一致自动打回 | ✅ `MOWN`/`mountOf`/`mountTier`/`mpMountDialog`/`mpMarkVerified`/`mpMarkUnmount` |
| §2 不迁移老数据 | ✅ 只在读取时归一（`mountOf`），没有写迁移代码 |
| §3 合并按钮 + 直连失败退回 | ✅ `camGateConn` 合并入口 + `camDirectConnect(onFail)` 5 条死路全接回调 |
| §3 旧直连按钮不丢 | ✅ 移进折叠，id/绑定不变 |

### 6.2 **没做（显式记录，别当成忘了）**

1. **没有删掉 `#camGateDirect`**（用户选项里说"合并成一个按钮"）—— 保留为折叠里的备用入口，理由：`dv_camclean` 有"控件一个都不许丢"的硬口径，删了要同时改三条历史断言，收益为零。
2. **没有给底栏加"真机端截图/上报"** —— 用户明确说不想调日志；改成"自愈优先 + 诊断只在自愈失败时才写一行"。
3. **没有动 `.mpbar`（我的配方底栏）的结构** —— 只跟着加了 `width:100vw` 与 `pinBar`，行为不变（它的宽度问题没有用户反馈）。
4. **没有把 `app/index.html` 从仓库里清掉** —— 它现在是"上一版源码快照"的载体（本轮的回退点就是它），保持原样。

### 6.3 v2.16 逐条回退清单（想退哪条就照这个改）

| # | 文件 / 位置 | 回退动作 |
|---|---|---|
| 1 | CSS `.barABC,.barD` / `.mpbar` | 去掉 `width:100vw;max-width:100vw;box-sizing:border-box`；`.barABC,.barD` 的 `overflow:hidden` 改回 `auto` |
| 2 | `pinBar()` / `unnestBar()` / `pinBars()` | 整段删除 + 删掉所有 `pinBars()` 调用点（启动/resize/转屏/scroll/每秒/showStep/applyModule/switchPane） |
| 3 | 挂载两态 | `MOWN` 加回 `pending`；`mountOf` 恢复三态判断；`mpMarkMount` 两处 `'on'` → `'pending'`；`mpMarkVerified` 加回 `mountOf(s) !== 'pending'` 早退；删 `mpMarkUnmount` 及其在 `verifyPending` 里的调用；`mpMountDialog` 加回第三个选项 |
| 4 | 连接按钮合并 | `camGateDirect` 挪出折叠；`camGateConn` 的 handler 改回 `connectNow()`；`camDirectConnect` 去掉 `onFail` 参数与 5 处回调 |
| 5 | 整份源码一起退 | `app/base.before_r30.html`（= v2.15，md5 `b09fd5264aef93c3aa8596b9512a7efb`）覆盖回 `app/base.html` |

---

## 7. 本轮文件清单与指纹

| 文件 | 说明 |
|---|---|
| `app/base.html` | 唯一源码（改：底栏 / 挂载两态 / 连接合并），md5 `9a6586c9dee9860b746ce9bdf0e6e2c8` |
| `app/base.before_r30.html` | **回退点** = v2.15 源码，md5 `b09fd5264aef93c3aa8596b9512a7efb` |
| `scripts/dv_barstep3.py` | **新**：复刻"点写入→底栏丢/少按钮" + 自愈断言 |
| `scripts/dv_barchk.py` | 改：同步诊断 + 自愈断言 |
| `scripts/dv_mount.py` | 改：两态口径 + 8b「核对不一致自动打回」 |
| `scripts/dv_blecam.py` | 改：合并后"手点连接仍能连" |
| `apk/build/om3.apk` | 产物 v2.16（`versionCode 216`），md5 `a4b48011c35cabedba87f1dd72eb87c8`；`apk/assets/index.html` md5 `8615115a8a5758602711c70546077718` |
| `HANDOVER.md` / `README.md` | 本轮接手段 / 版本表 / 变更记录 |
