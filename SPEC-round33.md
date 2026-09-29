# SPEC-round33.md · v2.21（第三十四轮）

> ## 用户 2026-09-24 的两句话 + 四个决定
> 原话：①「**再检查下有没有bug**」 ②「能不能参考官方app的功能，看看**你的连接有没有问题**，
> 现在**蓝牙连接很繁琐**，你要不做一下」
>
> 四个决定（用户答）：
> 1. **和官方一样：进「连接相机」页自动连蓝牙；按钮负责连 Wi-Fi**
> 2. 蓝牙没打开 → **app 自动打开**（照官方 `BluetoothAdapter.enable()`）
> 3. 唤醒帧失败 → **自动依次试 68/子2（开 Wi-Fi）→ 68/子3（电源 ON）**
> 4. 范围 → **连接改造 + 全站再扫一遍 bug 一起修**
>
> 本轮 = **第 34 轮**。规格先落地（本文件），实现完把「§6 验收结果」回填。

---

## 0. 一眼版

| # | 改什么 | 类型 |
|---|---|---|
| 1 | **进页自动连蓝牙**：进「连接相机」页 → 自动（权限→开蓝牙→只扫相机→自动连第一条📷→发唤醒帧），**不用点任何按钮** | 修 + 新（用户决定 1/2/3） |
| 2 | **「连接相机」按钮 = 连 Wi-Fi**：直连（修好的）→ 记住的凭据 → 都不行才提示；连上自动检测 | 修 |
| 3 | bug①：`wifiScanList` 的 SSID **没去引号** → 相机热点标不出来 → 直连第一条路永远走不通 | 修 bug |
| 4 | bug②：`camDirectConnect` **问了密码却不保存**（文案承诺"填一次就记住"）→ 每次都要重输 | 修 bug |
| 5 | bug④：`camWifi` / `camCopyLog` **不接剪贴板 Promise 拒绝**，且 `camCopyLog` **假报成功** | 修 bug |
| 6 | 原生新增 `bleState()` / `bleEnable()` / `openBtSettings()`；`wifiScanList` 去引号 | 新 + 修 |
| 7 | 幂等 + 进度 + 可停止（照官方 `既に接続処理中` / `既に接続済み` / `リトライ`） | 新 |

版本 **v2.21**（`versionCode 221`；= v2.20 + 注释日期纠正，见 §6.3b）。回退点 `app/base.before_r34.html`（= v2.19 源码）。

---

## 1. 官方是怎么连的（反汇编 `om share.apk`，本轮的"参考"依据）

**状态机**：类 `Lcom/omdigitalsolutions/oishare/e;` 方法 `H`（日志前缀 `.connectInner`）与 `e0`/`a0`。
按字节码读出来的顺序（`dis.txt` 行 530124-530344 等）：

```
connectInner():
  没有监听器            → 清标志返回
  「既に接続処理中」     → 已在连 → 直接返回          ← 幂等
  「既に接続済み」       → 已连上 → 直接返回          ← 幂等
  「BLE_INIT_BLE_OFF」  → BluetoothAdapter.enable()  ← 蓝牙关着就自己开
  「BLE_INIT_COMPLETE」 → 初始化 BLE 管理器
  「既に見つけていれば接続処理へ」→ 以前发现过相机 → 跳过扫描直接连（a0）
  「見つけていないので検索処理へ」→ 否则进扫描
a0(devices):
  「.scanResultConnectMode 接続開始」  → 连
  「接続失敗なのでもう一度」/「リトライ」→ 自动重试
```

其他关键证据：

| 官方字符串 | 说明 |
|---|---|
| `.startDetect bleName= / scanTime=` / `既に検索中` | 扫描有超时、且防重入 |
| `.convertSSID` | **SSID 去掉两边引号**（Android 的 `getSSID()` / `ScanResult.SSID` 会带引号） |
| `camera_ssid` / `ble_password`（SharedPreferences） | 记住相机热点与密码 |
| `.updateCameraAP 不明なSSIDは覚えない` | 不认识的 SSID 不记 |
| `.authPasscode` / `BLE_RESULT_PASSCODE_ERROR` | 存在 BLE 口令认证（本轮不涉及） |
| `.connectWiFi connectHelper onConnectCameraAP / onAccessDeniedAP / onConnectTimeout` | Wi-Fi 侧有独立的重试/超时/被拒分支 |

**结论**：官方把"找相机 + 连相机 + 让相机开 Wi-Fi"做成**一条自动状态机**（进页面就跑），
Wi-Fi 那一步由连接动作驱动。我们之前是"让用户分五步手动摆"，这就是"繁琐"的根源。

---

## 2. 规格（模块 → 子模块 → 功能点）

### 模块 A：连接相机（本轮主改）

#### A1. 进「连接相机」页 → 自动连蓝牙（用户决定 1+2+3）

| 项 | 内容 |
|---|---|
| 输入 | 无（由 `showPane('D')` → `window.__om3camPaneShown()` 触发） |
| 输出 | 「两条链路」卡上的进度行 + 日志；副作用：可能**打开系统蓝牙**、建立 GATT 连接、**向相机发 1~2 条唤醒帧** |
| 前置条件 | 相机通电、相机蓝牙开着、手机在 1 米内 |
| 后置条件 | 成功：蓝牙已连相机 + 已发唤醒帧 + 相机热点应出现；失败：卡上写明卡在哪一步 + 下一步该点什么 |
| 业务规则 | 见下方步骤；**任一子步骤失败都不阻断其它步骤**（蓝牙失败也要能走 Wi-Fi 路） |
| 验收标准 | `dv_r34.py`：①HTTP 已通时不重复跑 ②已在跑时不重入 ③权限 `need:` → 拉起弹窗 → 回调后**继续**（不 return 死路）④蓝牙关 → 调 `bleEnable()` ⑤只扫相机模式下**自动连第一条 📷**（不用点）⑥连上后自动发唤醒帧，且**依次** 68/子2 → 68/子3 ⑦扫不到相机 → 明确文案 + 不阻断 |

步骤（幂等/边界都在里面）：

1. **幂等 1**：HTTP 已通（`body.cam-on`）→ 日志「相机已经连着了，不用再连蓝牙」→ 返回。
2. **幂等 2**：本轮已在跑（`__om3bleAutoRun`）→ 返回（照官方 `既に接続処理中`）。
3. **权限**：`Native.blePerm()` 返回 `need:` → 调 `Native.bleAskPerm()` 拉起系统弹窗；
   授权结果由既有 `window.__om3blePerm('ok'|'denied')` 回调**继续本链**（denied → 卡上给"去设置里给权限"的按钮文案）。
4. **蓝牙开关**：`Native.bleState()` → `off` → `Native.bleEnable()`；
   - 返回 `turned_on` → 等 1.5 秒再扫（系统刚开蓝牙要缓一下）
   - 返回 `need:…` / `err:…` → 卡上给「打开系统蓝牙设置」（`Native.openBtSettings()`）+ 结束（不阻断 Wi-Fi）
   - 老原生没有 `bleEnable` → 退回"只提示"，行为与现在一致（**兼容**）
5. **扫描**：`bleScanStart2(1)`（只找相机，官方那种带服务 UUID 过滤的扫法）等 `BLE_AUTO_CAM_MS=8000`；
   一个相机都没有 → `bleScanStart2(0)` 全量再等 8000（相机行带 📷）；
   仍没有 → 卡上写「没扫到相机：① 相机电源/蓝牙开着吗 ② 是不是被别的手机连着 ③ 站近一点」，结束蓝牙链。
6. **自动连**：`bleBestCam()`（📷 优先、信号最强的）→ **自动** `bleConnectTo()`（不再让用户挑）。
   连接超时 12 秒没出 `svc` → 记失败并结束蓝牙链。
7. **自动唤醒**：`svc`（服务发现完成）后 → 发 `68/子2`，等 3 秒；
   判据：`wifiScanList()` 出现相机热点 **或** `wifiState().ssid` 是相机热点 → 成功；
   否则发 `68/子3`，再等 3 秒；两帧都不行 → 卡上写「两帧都没让它开 Wi-Fi」+ 提示可在「高级/诊断」里手动点其它帧。
   （用户决定 3；每帧的结果都写日志，不静默）
8. **可停止**：卡上「停止自动连接」→ `__om3bleAutoStop=true`，清掉待跑的定时器。

#### A2. 点「连接相机」按钮 = 连 Wi-Fi（用户决定 1）

| 项 | 内容 |
|---|---|
| 输入 | 无（按钮 `#camGateConn`） |
| 输出 | 进度行（第 n/4 步）+ 日志；副作用：请求系统连相机热点 |
| 前置条件 | 手机 Wi-Fi 开着 |
| 后置条件 | 成功：HTTP 通 → `setConn(true)` → 自动「检测相机」；失败：明确"该点哪个按钮" |
| 业务规则 | 见下；**若蓝牙链还没跑过，先顺带触发一次，最多等 10 秒，超时也继续**（不阻断） |
| 验收标准 | `dv_r34.py`：①已连通 → 点它只提示、不重连（幂等）②蓝牙链没跑 → 会触发 ③直连扫到相机热点 → 询问密码并**保存**（bug② 的回归）④直连不行 → 退「记住的凭据」⑤都不行 → 提示扫码/手填 |

步骤：
1. 幂等：`body.cam-on` → 「已经连着了」+ 跳到 ② 备份 的提示，返回。
2. 若蓝牙链未跑（`!__om3bleAutoDone` 且 BLE 没连上）→ 触发 A1（不等待超过 10 秒）。
3. `camDirectConnect()`：扫附近 Wi-Fi → 像相机的热点（`cam` 标记 **或** 记住过的 SSID）→
   有记住的密码就直接连；没记住过 → **问一次密码 → `camSave({ssid,pass})` 记住** → 连。
4. 直连失败 → `connectNow()`（用记住的凭据走 `requestNetwork`，已有 8 次重试）。
5. 都不行 → 卡上写清三条路：扫码 / 手填 / 查权限（并高亮「扫二维码（第一次）」）。
6. 连上（`__om3camState('connected')`）→ 既有逻辑：`setConn(true)` → 1.5 秒后自动「检测相机」。

#### A3. 保留（不删任何控件）

现有细粒度按钮（`#bleScan` / `#bleStop` / `#bleConn` / `#bleWake` / `#blep1..3` / `#camGateDirect` /
`#camGateManual` / `#camJoin` / `#camWifiSettings` / `#camForget` / `#camCheck` / `#camDisconnect` …）
**一个都不删**，蓝牙那张卡默认折叠的状态保持 —— 它现在变成"高级 / 诊断"。

### 模块 B：全站 bug 扫描（用户决定 4）

#### B1. 已修（本轮）

| bug | 症状 | 根因 |
|---|---|---|
| ① | 相机热点标不出 📷 → 「连接相机」直连第一条路永远走不通 | `wifiScanList()` 用 `r.SSID` 原值，**没去引号**；`cam` 正则 `^(OM[- ]?\d…)` 因此匹配失败（官方专门有 `convertSSID`） |
| ② | 每次都要重输密码；「进页面自动连」永不启动 | `camDirectConnect()` 问了密码后**没有 `camSave()`**（文案却写"填一次就记住了"） |
| ③ | 「用蓝牙唤醒相机」要先手动扫过才有效 | `bleBestCam()` 依赖扫描结果；没扫过只弹"先扫一下蓝牙" |
| ④ | 两个"复制"按钮产生**未处理 Promise 拒绝**；且日志复制**假报成功** | `camWifi` / `camCopyLog` 用 `try{ navigator.clipboard.writeText() }catch{}` —— Promise 的拒绝**不被同步 catch 捕获**；`camCopyLog` 还无条件 `ok = true` |

#### B2. 本轮扫过、**确认无问题**（记录，免得下轮重复查）

| 手段 | 结果 |
|---|---|
| `audit_all` / `audit_code` | 只有历史已知项（重复实现、空 catch、`ensureVisible` 等），**无新增** |
| **跨层接口对齐**（页面 `Native.*` ↔ 原生 `@JavascriptInterface`） | **0 不匹配** ✓ |
| 捕获阶段 `document` 级 `stopPropagation` 抢事件 | 只有第 33 轮修的那一处（`#tocbtn`），**无新增** |
| 用户输入（方案名/槽位名含 `<` `"` `&`）进 `innerHTML` | **已正确转义** ✓（实测名字原样显示、无注入元素） |
| `localStorage` 坏数据（`slots:null`、`vivid` 是字符串、数组里有 `null`） | 列表/详情**不崩** ✓ |
| **把 5 个页签的每个按钮点一遍** | **0 个 JS 报错** ✓（唯一发现就是 bug ④） |
| 原生 5 个 `@JavascriptInterface` 从没被页面调用（`bleMtu`/`bleMtuInfo`/`bleReadRemoteRssi`/`bleServices`/`toast`） | 死代码，**无害**（保留） |

---

## 3. 显式声明清单

| 约束 | 涉及 | 落到哪里 |
|---|---|---|
| **并发 / 幂等** | ✓ | A1 两个幂等门（已连通 / 已在跑，照官方）；按钮点击防重入；`bleEnable` 已开则返回 `ok(already)`；重复调 `camBleAuto()` 直接返回 |
| **权限** | ✓ | `BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT`（API31+ 运行时）→ 复用既有 `bleAskPerm` 系统弹窗；`NEARBY_WIFI_DEVICES`/位置 → 既有 `need_perm` 路径；**每个失败分支都给"该点哪个按钮"的可操作提示**，不出现"点了没反应" |
| **边界** | ✓ | 无蓝牙适配器 / 蓝牙关 / 权限拒 / 一个相机都扫不到 / 相机已被别的手机连 / 相机已在传输态（HTTP 已通）/ 已记住密码 / 密码为空 / 密码错 / 老原生缺接口（逐个兜住） |
| **超时 / 降级** | ✓ | 每段独立超时：权限 30s、只扫相机 8s + 全量 8s、GATT 连接 12s、唤醒每帧 3s；**任一子步骤失败不阻断**后续可独立完成的步骤（蓝牙失败照样走 Wi-Fi 链）；老原生无 `bleEnable`/`bleState` → 降级成"只提示" |
| **状态一致性** | ✓ | 进度写进「两条链路」卡（`#camLinkOut`）**且**写日志（不静默）；断开 / 忘掉相机时清 `__om3bleAuto*` 标志；每步只由一处改状态 |
| **兼容** | ✓ | 不删任何既有控件；老调用点行为不变；`wifiScanList` 去引号对上"原本就不带引号"的设备**无副作用**（去掉的是引号，SSID 本身不含引号） |
| **性能** | ✓ | 只在进入「连接相机」页时跑；扫描最多两轮（8s+8s）；不新增常驻定时器（复用既有 3.5s 状态刷新） |
| **迁移** | ∉ | 无数据结构变化（`camSaved` 仍是 `{ssid,pass,model,serial,at}`；只多写几次同一个键） |

---

## 4. 改动清单（改哪几处 · 影响面）

| # | 文件 / 位置 | 改什么 | 影响面 |
|---|---|---|---|
| 1 | `MainActivity.java` `wifiScanList()` | SSID 去引号（`replace("\"","")`），`cam` 正则不变 | 只影响扫描结果字符串；「直连」变准 |
| 2 | `MainActivity.java` 新增 `bleState()` / `bleEnable()` / `openBtSettings()` | 蓝牙开关状态 / 自动打开 / 跳系统蓝牙设置 | 新接口，老页面不受影响 |
| 3 | `base.html` BLE 段 | 新增 `camBleAuto()`（A1 全链）+ 进度渲染 + 停止 | 只在新链里调用；既有按钮不变 |
| 4 | `base.html` `__om3camPaneShown` | 追加：进页触发 `camBleAuto()` | 进页多一段自动动作（用户要求） |
| 5 | `base.html` `#camGateConn` | 改成 A2（Wi-Fi 链 + 顺带等蓝牙 ≤10s） | 原来只是"直连→凭据"，行为增强 |
| 6 | `base.html` `camDirectConnect()` | 问到的密码 `camSave()` + `renderSaved()` | 修复"记不住" |
| 7 | `base.html` `#camWifi` / `#camCopyLog` | 改用既有 `om3Copy()`（正确接 Promise 拒绝 + 失败给手动复制提示） | 只影响这两个按钮的提示文案 |
| 8 | `scripts/dv_r34.py`（新） | 第 34 轮验收探针 | — |
| 9 | `scripts/dv_clickall.py`（新，已建） | 全站点一遍（纳入回归） | — |

---

## 5. 验收方式（脚本 + 断言）

| 探针 | 覆盖 |
|---|---|
| `scripts/dv_r34.py`（新） | A1 七个断言（幂等×2 / 权限续跑 / 自动开蓝牙 / 自动连第一条📷 / 依次两帧唤醒 / 扫不到不阻断）、A2 五个断言、bug①（native 侧引号，用与 main 相同的正则做单测）、bug②（问密码→保存→下次直接连）、bug④（复制失败必须"无未处理拒绝"且**不假报成功**） |
| `scripts/dv_clickall.py`（本轮回填回归） | 全站按钮点一遍：0 JS 报错、0 未处理拒绝 |
| `scripts/check_syntax.py` / `check_app.py` / `verify_all.py` / `dv_r33.py` / `dv_barstep3.py` / `dv_mount.py` / `dv_mpwheel.py` | 回归全绿 |
| `javac --release 8` + `aapt2 dump badging` | 原生编译通过 / 版本号正确 |

---

## 6. 验收结果（已回填）

### 6.1 一条命令跑完本轮验收

`python scripts/dv_r34.py` → **原生/静态 18 项全 OK ＋ 8/8 场景通过**：

```
原生侧 + 静态检查（不需要浏览器）
  [OK ] ★bug①：wifiScanList() 的 SSID 去掉了两边的引号
  [OK ] ★机理：带引号的 SSID 匹配不上相机正则（→ 相机热点标不出 📷 → 直连第一条路走不通）
  [OK ] ★去掉引号后能匹配上（修好之后的行为）
  [OK ] ★去掉引号对"本来就不带引号"的设备无副作用
  [OK ] 原生新增接口 bleState() / bleEnable() / openBtSettings()（3 项）
  [OK ] 页面确实调了 bleState() / bleEnable() / openBtSettings()（3 项）
  [OK ] 跨层接口对齐：页面调用的 Native.* 全部有实现
  [OK ] ★bug④：camWifi / camCopyLog 都改用 bleTryCopy（2 项）

场景 A1-正常        进页自动只扫相机 → 自动连 → 第一帧就是 68/子2 → 热点起来判定成功
场景 A1-兜底        权限弹窗 → 自动开蓝牙 → 只扫没找到改全量 → 自动连 → 68/子2 → 68/子3 依次
场景 A1-权限死循环  授权后仍说缺权限 → 只弹 1 次（实测 1 次）＋ 明确指路
场景 A1-失败        扫不到相机 → 明确文案；不发帧；点停止后也不补发
场景 A1-幂等        连进两次页 → 蓝牙链只跑一次（实测 1 次）
场景 A2-按钮        点按钮顺带跑蓝牙链 → 直连 → 问密码 → **记住**（localStorage 里 ssid+pass 都在）
场景 A2-已连通      已连通点按钮 → 不重连，只提示"已经连着了"
场景 B-复制         两个复制按钮 0 未处理拒绝 ＋ 给明确结果 ＋ 不再有"已尝试复制"
===== 结论：8/8 场景通过 =====
```

调用序列证据（A1-兜底，完整链路）：
```
bleAskPerm → bleState → bleEnable → bleScanStart2(1) → bleScanStop → bleScanStart2(0)
  → bleConnect(AA:BB:CC:DD:EE:01) → bleScanStop → bleWrite(68/子2) → wifiScanList → bleWrite(68/子3)
```

### 6.2 全站"每个按钮点一遍"（新增 `scripts/dv_clickall.py`）

| 项 | 改前 | 改后 |
|---|---|---|
| JS 报错 | 0 | **0** |
| 未处理的 Promise 拒绝 | **2**（`camWifi` / `camCopyLog`） | **0** ✅ |
| `__om3errs` | 2 | **0** |

### 6.3 回归全套

| 脚本 | 结果 |
|---|---|
| `check_syntax.py` | 10 个内联块全部通过 ✅ |
| `check_app.py` | 配方卡 58 / 加入按钮 81 / 优化版槽位 23 / 运行错误 0 / om3errs 0 ✅ |
| `verify_all.py` | 全项正常（🔍 仍按第 33 轮口径跟着页签）✅ |
| `dv_r33.py` | 0 失败（第 33 轮那 6 件事无回归）✅ |
| `dv_barstep3.py` | 0 失败 ✅ |
| `dv_mount.py` / `dv_mpwheel.py` | 全部通过 ✅ |
| `javac --release 8`（MainActivity + R） | 退出码 0 ✅ |
| `aapt2 dump badging` | `versionCode=221 versionName=2.21` ✅ |

### 6.3b 收尾：日期纠正 → 重发 **v2.21**（用户指出"今天不是 09-29，是 **09-24**"）

用户一句话纠正了日期。查证：`app/base.before_*.html` 的**文件时间戳**近几轮全部落在 **09-24**
（r31=17:08 / r32=17:30 / r33=22:13 / r34=22:49），**没有一个**在 09-29 → 之前几轮文档里的
`2026-09-29` 是**系统性写错**。按"发现就改干净"处理：

| 范围 | 处数 | 处理 |
|---|---|---|
| `HANDOVER.md` / `SPEC-round29..33.md` | 19 | 全改 09-24（残留 0） |
| `app/base.html` + `app/index.html` | 23 + 23 | 全改（**全是注释**：`用户 2026-09-24 报的` / `⚠ 2026-09-24 修`；先逐条核对过**无断言、无用户可见文案**） |
| `apk/java/.../MainActivity.java` | 4 | 全改（注释） |
| `scripts/{verify_all,dv_mount,dv_blescan,dv_barstep3}.py` | 6 | 全改（注释/文档串） |
| `app/base.before_*.html`（历史回退点） | 36 | **故意不动** —— 它们的 md5 已写进各轮 SPEC，改了就对不上账；那几份快照本来也"带着当时的错日期" |
| `apk/assets/index.html` | 23 | 构建产物 → `mkasset.py` 重新生成 |

因为改到了 `base.html`/`MainActivity.java`，**源码与已构建的 APK 必须重新对齐** → 重建
（`bumpver.py` 无条件自增）→ 发 **v2.21**：只差注释里的日期，**功能与 v2.20 完全一致**。
重建后复验：`check_syntax` / `check_app`（58/81/23/0/0）/ `verify_all` / `dv_r33`（0 失败）/
`dv_clickall`（0 报错 0 未处理拒绝）/ `dv_r34`（**8/8**）全绿；
APK 内实测 `2026-09-29` **0 次**、`2026-09-24` 49 次、`bleState/bleEnable/openBtSettings` 三个原生方法都在。

### 6.4 实现过程中被探针/差异分析抓出来的 **4 个自己的错**（如实记录）

| # | 错 | 怎么发现的 | 修法 |
|---|---|---|---|
| 1 | 权限分支没放开幂等门 → **授权回调进来被"已在连"挡住**，整条链卡死 | `dv_r34.py` A1-兜底 第一版 | 暂停等权限时把 `_bleAutoRun` 放开 |
| 2 | 权限一直报 `need:` → **反复弹授权窗**（实测一次跑出 130 次 `bleAskPerm`） | 同上（A1-权限死循环 场景专为它而生） | 只允许自动续跑 1 次，之后明确指路去设置 |
| 3 | 扫到相机后**还要白等满 8 秒**才开始连（官方是"找到就立刻连"） | 探针时序（成功文案 12s 才出现） | 挂 `window.__om3bleAutoFound`，扫到即连（`_bleAutoConnStarted` 保证只连一次） |
| 4 | `openBtSettings()` 原生做了、**页面没有入口**（用户会干瞪眼） | `check_native()` 的"页面确实调了 xxx()"断言 | 卡上加「打开系统蓝牙设置」按钮 + 失败文案指向它 |

> 前 3 个都是 **"能跑通但不对"** 的典型：不写探针、只看"没报错"，是抓不出来的。

---

## 7. 回退清单

| # | 位置 | 回退动作 |
|---|---|---|
| 1 | 整份源码 | 用 `app/base.before_r34.html`（= v2.19，md5 `5a0087c9961dd7c3768ad3d7f40ab77e`）覆盖 `app/base.html` |
| 2 | 原生 | 删掉 `bleState` / `bleEnable` / `openBtSettings` 三个方法；`wifiScanList` 去掉 `.replace("\"","")` |
| 3 | 页面 | 拆掉 `camBleAuto()` / `bleAutoWake()` / `camWifiChain()` 与它们的触发点；`#camGateConn` 恢复成"直连→凭据"；`camDirectConnect` 去掉 `camSave`；两个复制按钮恢复原状；删掉卡上新增的两个按钮 |

| 文件 | 说明 |
|---|---|
| `app/base.html` | md5 `2ec98bfd835a5974835940f2ade9585d`（v2.21；v2.20 时是 `047d907f…`，只差注释里的日期） |
| `app/base.before_r34.html` | 回退点 = v2.19 源码（md5 `5a0087c9961dd7c3768ad3d7f40ab77e`） |
| `apk/java/com/om3/handbook/MainActivity.java` | SSID 去引号 + 新增 `bleState`/`bleEnable`/`openBtSettings`（注释日期已纠正） |
| `apk/assets/index.html` | md5 `5d6c0eaa75266a1c66053532068b6ac8`（含版本徽标 v2.21 / build 221） |
| `apk/build/om3.apk` | **v2.21**（`versionCode 221` / `versionName 2.21`），md5 `4ebebfd999c674aedb2595aab914f973`，53,398,944 字节 |
| `~/Desktop/OM-3色彩配方手册.apk` | 已同步为同一份；签名 SHA-256 `d51a42f3…` 未变 → **可直接覆盖安装 v2.19/v2.20** |
| `scripts/dv_r34.py` | **本轮新增**：原生/静态检查 + 8 个场景（本轮验收的唯一入口） |
| `scripts/dv_clickall.py` | **本轮新增**：全站"每个按钮点一遍"，抓运行时异常与未处理拒绝（可留作回归） |

---

## 8. 没做 / 已知遗留

1. **`#toc2` 那两条历史遗留**（第 33 轮记的：`nav2` 解析期为 null、`#toc2` 里没有搜索框）—— **本轮未动**（无害）。
2. **官方那套"BLE 口令认证"没做**（`authPasscode` / `BLE_RESULT_PASSCODE_ERROR`）：本轮只做了
   扫描→连接→唤醒；口令认证是另一条路（要真机报文才知道帧格式）。
   **如果真机上连上蓝牙后发帧没反应 → 下一个目标就是它**（对应 `SPEC-round19.md` 记的 `0x040F/0x0410`）。
3. **没做"从 BLE 拿 Wi-Fi 的 SSID/密码"**：官方把相机热点记在 `camera_ssid` / `ble_password` 里，
   但反汇编里**没定位到它从哪一次 BLE 通知解析出密码**（`Lu2/a` 只是 SharedPreferences 包装）。
   所以**首次仍然要扫码 / 手填一次密码**；填完就记住了（这正是 bug② 修好的部分）。
4. **进页面自动跑蓝牙链**在"只是路过连接页"时也会跑（会开蓝牙、扫 8~16 秒）—— 已给
   「停止自动连蓝牙」的出口；若嫌打扰，把 `__om3camPaneShown` 里那一行删掉即可（一行）。
5. **真机未验**（本轮全部验证都在无头 Chrome + `OM3Native` 替身上做，替身字段照 `MainActivity` 抄）：
   - 真机上 `bleEnable()`（`BluetoothAdapter.enable()`）在 Android 13/14 上**能不能自己开蓝牙** ——
     `enable()` 在新系统已废弃；系统若拒绝，页面会走「打开系统蓝牙设置」那条退路（已接好）；
   - "扫到就立刻连"会不会和相机广播节奏打架（官方就是扫到就连，理论上一致）；
   - **两帧唤醒（68/子2 → 68/子3）在真机上的实际效果** ← 最需要真机日志的一条；
   - 首次连上后 `camSaved()` 记住了密码，**下次进页面应能直接连**（省掉扫码）——请顺手验这一条。

