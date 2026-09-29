# 第 66 轮**方案**（未实施）：camprop「单项实时改参」要不要做、怎么做

> 需求方 2026-09-28 说「**能做的都做**」→ 这一项（原 HANDOVER 候选 ④）**本质是产品选择题 + 需要真机验收**，
> 所以本轮**只出方案**（照第 44 轮 `SPEC-round44-plan.md` 的先例），**不动代码**。
> 前置阅读：`SPEC-round61.md` §2.4（camprop 与 MySet 的关系）+ `SPEC-round65.md` §4.3（`get_/set_camprop` 参数表）。

---

## 1. 这个功能到底是什么

在手册 App 里**改一个参数、立刻在相机上生效**（比如把「对比度」从 +1 调到 +2，相机马上跟着变），
而不是像现在这样：**整份 my-set 打包上传**（我们现在的「写入配方」就是这条路，`SPEC-round61.md` §2.4①）。

两者在官方 APK 里是两个不同通道：

| 通道 | 官方 CGI | 我们 |
|---|---|---|
| **整包** | `request_getmysetdata` / `send_partialmysetdata` / `switch_cammode` … | ✅ **已实现、真机可用**（写配方走这条） |
| **单参数** | `get_camprop.cgi?com=get\|check\|desc&propname=X` / `set_camprop.cgi?com=set&propname=X`（XML body） | ❌ 没用过 |

**它们不冲突**：整包是"一次性把 12 个颜色的配方全写进去"，单参数是"只动某一个值"。

---

## 2. 现状与已确证的部分（第 65 轮的成果）

- **`set_camprop` 的 `propname` 全表**已经列出来了（`SPEC-round65.md` §4.3）：
  `qualitymovie` / `shutspeedvalue` / `takemode` / `exposemovie` / `colortone` / `colorphase` / `expcomp` /
  `SceneSub` / `focalvalue` / `wbvalue` / `isospeedvalue` / `drivemode` / `supermacrosub` + 运行时动态名。
- 官方调用点：`remocon/RemoconV21Activity` 的 **20 个方法**（都是遥控页上"改一下立刻生效"的交互）。
- `get_camprop` 的三种 `com`：`get`（读一个）/ `check`（查有没有）/ `desc`（拿描述表 `propname=desclist`）。

**还没读的（这是本方案的关键风险）**：

| 未读项 | 为什么重要 | 怎么读 |
|---|---|---|
| 每个 `propname` 的 **XML body 结构** | `set_camprop` 是 POST，值在 XML 里（dis.txt 里能看到 `<?xml version=` 开头的字面量） | `python official_app/oi_cgi.py --body 'Lcom/omdigitalsolutions/oishare/remocon/RemoconV21Activity;' Vd` 之类，逐个方法读 |
| 各 `propname` 的**取值域** | 不知道合法范围就没法做 UI（滑块/下拉） | 同上 + `get_camprop?com=desc&propname=desclist` 的**响应体**（要真机） |
| **相机支不支持** | 老机型可能没有某个 propname | `get_commandlist.cgi`（第 65 轮 §5②） |
| 响应体的**错误码** | 改参失败要怎么提示 | 只能真机 |

---

## 3. 三个选项（请需求方选一个）

| 选项 | 做什么 | 工作量 | 风险 |
|---|---|---|---|
| **A. 不做**（推荐先按这个走） | 保持现状：写配方继续走 MySet 整包 | 0 | 无。**但"改一个值试一下"的体验拿不到** |
| **B. 只做"读当前参数"** | 用 `get_camprop?com=get&propname=…` 在页面上显示相机当前值（对着调） | 小（1 个 CGI + 展示） | 低。**不过价值有限**：我们**已经能读整份 my-set**（`readMySet()`），要显示当前值从那里取就行，不必新通道 |
| **C. 做"单项实时改参"** | 页面上改一个值 → `set_camprop` 立即生效 | 中～大：① 先补读 XML 结构/取值域（静态，本机可做）② 做 UI ③ **真机验收**（没真机等于没做完） | 中：改错了会把相机参数改乱（要有"改回原值"）；且**必须真机能验** |

**建议**：
1. 先做 **选项 A**，但把**选项 C 的静态前置**（XML 结构 + 取值域 + `get_commandlist`）在**某轮支线**里一并读掉
   —— 那时就不需要真机、也不改 App，读完再决定做不做，**不欠账**。
2. 真要实施 C，**和"真机验证那一轮"合并做**（第 62/64 轮的连接改动也等着真机），一次把设备用足。

---

## 4. 如果做 C：验收标准（先写下来，免得做到一半说不清）

1. 只改一个值 → 相机上那个值确实变了（真机截图/相机屏幕照片为证）。
2. 改完能**读回来**（`get_camprop?com=get` 或整份 my-set 复核）——**不许"发了就算成功"**。
3. 失败/不支持时要**明说**（含"这台相机不支持这个参数"），不许静默。
4. 有**改回原值**的办法（每次改之前记住旧值）。
5. 不影响现有 MySet 写入链路（回归：`dv_r62` / `dv_r64` 仍全绿）。

---

## 5. 需要需求方拍板的三件事

1. **要不要做**（A / B / C）？
2. 如果要：**在哪一屏**？（「连接相机」页里加一个"调参"折叠？还是新页签？）
3. 如果要：**哪些参数**先做？（建议只挑 3~5 个最常用的：`expcomp` 曝光补偿、`wbvalue` 白平衡、`colorphase` 色调、`isospeedvalue` ISO）

> 在这些问题有答案之前，**这一项不写任何代码**（`app/base.html` 保持 md5 `3692725c82e022d643b69c465d77f474`）。
