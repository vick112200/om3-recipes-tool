# SPEC-round23：蓝牙权限（Android 12+ 运行时权限）修复（v2.8）

## 0. 用户报的现象

> 「点扫描蓝牙设备，他弹窗让我给蓝牙权限，而且不是系统的权限弹窗，是 app 的小提示，但是权限我应该都给了」

## 1. 根因（代码里对得上的因果链）

| 环节 | 代码 | 问题 |
|---|---|---|
| 清单 | `apk/AndroidManifest.xml` 里 **已经**有 `BLUETOOTH_SCAN`（`neverForLocation`）+ `BLUETOOTH_CONNECT`，`targetSdk=34` | 没问题 —— 但**清单只是"有资格申请"** |
| 原生检查 | `Bridge.blePerm()`：SDK≥31 时查 `BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT`，没给就返回 `need:…` | 检查本身是对的 |
| 页面 | `bleStart()`：看到 `need:` → 写日志 + `toastMsg('请先给蓝牙权限')` → **`return`** | **从来没调用过任何申请**（`requestPermissions(4714)` 那时根本不存在） |

→ **Android 12(API 31) 起 `BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT` 是运行时权限**：不主动申请就永远拿不到；
系统设置里可能压根看不到我们 app 的「附近的设备」开关（因为没申请过）。
于是现象就是：**只弹 app 自己的提示，没有系统弹窗，用户也没地方给权限**。

## 2. 修法

**原生（`MainActivity.java`）**

1. 新增 `bleAskPerm()`（`@JavascriptInterface`）：SDK≥31 时把**缺的**那几个（SCAN/CONNECT）用
   `requestPermissions(…, 4714)` 拉起**系统弹窗**（`runOnUiThread`）；SDK<31 直接回 `ok`（旧版是安装即给）。
2. `onRequestPermissionsResult` 新增 `4714` 分支 → `window.__om3blePerm('ok'|'denied')`。
3. 顺带修两个"会静默失败"的点：
   - 扫描回调里的 `device.getName()` 加 try/catch（API31+ 需要 `BLUETOOTH_CONNECT`，没给会抛 SecurityException
     让扫描**看着在跑却什么都收不到**）；
   - `getBluetoothLeScanner()` 失败时把**真实异常**报给页面（原来只说"拿不到扫描器"）。
4. 新增 `blePermDetail()`：报 `SDK / BLUETOOTH_SCAN 有·缺 / BLUETOOTH_CONNECT 有·缺 / 蓝牙开关`。

**页面（`app/base.html`）**

1. `bleStart()`（扫描）遇到 `need:` → **`N.bleAskPerm()` 拉系统弹窗**，页面写「正在向系统申请蓝牙权限…请在系统弹窗里点「允许」」；
   老版本没有该接口时，明确提示去系统设置手动开。
2. 新增回调 `window.__om3blePerm(res)`：`ok` → **直接开扫**（不再拿可能过期的检查挡自己）→ 为此把"真扫描"
   抽成 `bleScanGo()`；`denied` → 说清去「设置 → 应用 → OM-3… → 权限 → 附近的设备」再点一次。
3. 「连接」那条路同样处理（申请后提示"允许后请再点一次连接"）。
4. ☰ →「**检查权限**」现在会多打一行**蓝牙权限明细**；若"缺"，就地给一个「**蓝牙：申请权限**」按钮。

## 3. 验收（`scripts/dv_blecam.py` 新增 **perm** 场景，5 项全过）

| 断言 | 结果 |
|---|---|
| ★★没权限时点「扫描蓝牙设备」→ **真的去申请系统权限**（申请次数=1，且不硬扫） | ✅ |
| 页面写明「正在向系统申请蓝牙权限…」 | ✅ |
| ★授权成功后（回调 `ok`）→ **自动继续扫描**，不用再点一次 | ✅ |
| ★被拒时明确说"权限被拒绝" + 指路「设置 → 应用 → 权限 → 附近的设备」，且不硬扫 | ✅ |
| ★权限齐了就直接扫（不弹任何多余提示） | ✅ |

**回归**：33 个脚本 + 2 个审计 **0 失败**；Java 单跑 `javac --release 8` 通过；`按钮=81`、`运行错误=0` 不变。

## 4. 产物

| 项 | 值 |
|---|---|
| 版本 | **v2.8（build 208）** |
| APK | `C:\Users\82302\Desktop\OM-3色彩配方手册.apk`，53362080 字节，md5 `8dad28a86fe7066025f4025723f182b2` |
| 源码 | `app/base.html` md5 `b105dd3bd9b1017268267038cb7acbe9`；`apk/java/.../MainActivity.java`（新增 bleAskPerm / blePermDetail / 4714 分支） |

## 5. 局限

- **本轮无法在本机验"系统弹窗真的出现"**（需要真机 + Android 12+）——harness 只能验到"页面确实去调了申请、
  并按结果继续/提示"这层。真机上请按 §六 走一遍：点「扫描蓝牙设备」→ 应弹出**系统**权限框 → 点「允许」→ 应自动开始扫描。
- 若真机上点了「允许」仍然扫不到相机：先点 ☰→「检查权限」看那行**蓝牙权限明细**（缺哪个一目了然），
  再点「蓝牙：申请权限」；如果系统弹窗**不再出现**（选了"不再询问"），得去「设置 → 应用 → OM-3… → 权限」手动开。
