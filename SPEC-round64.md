# 第 64 轮：Wi-Fi 连接加 **BSSID**（照官方「SSID + BSSID」精连那一个热点）

> 需求方 2026-09-28：第 63 轮收尾后，对「下一轮做哪项」的回答是 **「能做的都做」**。
> 本轮 = HANDOVER 顶部候选 **①**（**主线**，要改 Java + 出包），并把 **③ / ④** 另开轮次（见 §9）。
> 候选 **②**（真机验证第 62 轮改动）**只能等需求方拿手机配合**，本轮不做。

> **改动前基线**：`app/base.html` md5 `a0c8b6280f8d0876500aa410bac806cc`（= v3.17 源码）；
> `apk/java/com/om3/handbook/MainActivity.java` md5 `fdc19cf86c5d0537771783bb0f5f9f1a`。
> **回退点**：`app/base.before_r64.html`、`apk/java/com/om3/handbook/MainActivity.before_bssid.java`。

---

## 1. 范围与「必须显式声明清单」

| 项 | 说明 |
|---|---|
| 输入 | `app/base.html`（v3.17）+ `apk/java/com/om3/handbook/MainActivity.java`；结论来源 = `official_app/dis.txt`（第 58~61 轮的逆向产物） |
| 输出 | 改后的 `app/base.html`、`MainActivity.java`；新增 `scripts/gen_r64.py`、`scripts/dv_r64.py`；本规格；出包 **v3.18** |
| 前置条件 | 页面能过 `check_syntax.py` / `live_check.py`；**不改任何既有 id**（JS 大量依赖 id）；`connectCamera(ssid,pass)` 这一既有桥方法**保留** |
| 后置条件 | 记住的相机记录里多一个 `bssid` 字段（`localStorage` 键仍是 `om3cam`，**不新增键**）；APK 版本 **v3.18** |
| 权限 | **不涉及新增**。BSSID 只从**已有**两条路径拿：① `wifiScanList()`（13+ 用 `NEARBY_WIFI_DEVICES`、≤12 用 `ACCESS_FINE_LOCATION` —— 清单里都有）② 已连上这个网络的 `WifiInfo.getBSSID()`。**不加任何新权限**；拿不到就退回「只按 SSID 连」 |
| 幂等 | **涉及**：`gen_r64.py` 用写进页面的标记 `r64：BSSID` 作判据，**重跑不重复改**；脚本对每处锚点断言「命中恰好 1 次」 |
| 事务/并发 | **涉及（仅 Java 侧、无锁）**：`NetworkCallback` 在系统线程写 `lastBssid`、JS 线程读 → 字段声明为 `volatile`；不做加锁（单值、无复合操作） |
| 数据迁移 | **涉及**：老记录没有 `bssid` → 一律当空串处理（`camBssidOk('')` → `''`），**不需要迁移**；`JSON.parse` 老数据不会抛 |
| 性能 | **不涉及**（多传一个字符串；扫描一次已返回的 `ScanResult.BSSID` 是现成字段，不额外扫描） |
| 安全 | **不涉及**（BSSID 是热点 MAC，只写本机 `localStorage`，与 SSID/密码同级；本 app 无任何上传通道） |
| 兼容性 | **涉及**：① 桌面单文件 HTML / 老 APK 里没有 `connectCamera2` → 页面**自动退回** `connectCamera`（不抛、不静默）；② Android 11 及以下**不设 BSSID**（照官方 `30 < SDK_INT`），退回按 SSID 连 |
| 失败回退 | `cp app/base.before_r64.html app/base.html` + `cp MainActivity.before_bssid.java MainActivity.java`；不重出 APK 即无影响 |

---

## 2. 现状与依据（为什么是 BSSID）

### 2.1 需求方的疑问与官方做法（**硬证据在工程内**）

- 官方 APK 连相机热点时**确实**用的是 SSID **+ BSSID** + 密码：

```text
official_app/dis.txt:16452c  invoke-static {}, LJ2/e;.R:()Ljava/lang/String;        // 日志 tag
        164508  const-string v1, "str.wifi.camera.bssid"
        16451e  ... cond:  T(prefBSSID) == false → 跳过
        164524  sget v2, Landroid/os/Build$VERSION;.SDK_INT:I
        164528  const/16 v1, #int 30 ; if-ge v1, v2, +0042     // 只有 SDK_INT > 30 才继续
        16454c  const-string v3, ".connectDevice setBssid BSSID="
        16456e  invoke-static {v0}, Landroid/net/MacAddress;.fromString:(Ljava/lang/String;)Landroid/net/MacAddress;
        164576  invoke-virtual {v1, v0}, Landroid/net/wifi/WifiNetworkSpecifier$Builder;.setBssid:(Landroid/net/MacAddress;)
```

  复现命令：`sed -n '51318,51352p' official_app/dis.txt`。

- BSSID 从哪来（官方两条来源，都是**我们已有能力**）：
  1. **扫描**：`getBssid()` —— `WifiManager.getScanResults()` → 找 `ScanResult.SSID == 相机 SSID` 的那条 → 取 `ScanResult.BSSID` → 写 prefs
     （`dis.txt` 888xxx 段：`iget-object … Landroid/net/wifi/ScanResult;.BSSID`）。**我们 `wifiScanList()` 现在就在遍历同一个列表，只是没返回它。**
  2. **连上之后系统报告**：`J2/e$c.onCapabilitiesChanged` → `NetworkCapabilities.getTransportInfo()` → `WifiInfo.getSSID()/getBSSID()`
     → 变化了就存（`dis.txt` 51570~51635；官方在这里**要求"以前已经有 BSSID 才更新"**，且过滤 `endsWith("00:00")` 的假值）。

- **为什么值得做**：只给 SSID 时，系统可以在「所有叫这个名字的 AP」里挑（扫描缓存里有同名残留/邻居同名热点时就会连错），
  连错了相机 HTTP（`192.168.0.10`）自然不通 —— 这正是「显示连上了但检测不到相机」那一类现象的一个可能来源。
  给 BSSID = 只连那一个。

### 2.2 我们现在的代码（改动前的真实状态）

| 位置 | 现状 |
|---|---|
| `MainActivity.java:1062` | `connectCamera(String ssid, String pass)` → `WifiNetworkSpecifier.Builder().setSsid(ssid)` **只用 SSID** |
| `MainActivity.java:880` | `wifiScanList()` 返回 `{ssid, level, cam}` —— **不返回 BSSID** |
| `MainActivity.java:1270` | `cameraState()` 返回 `{connected, ssid}` |
| `app/base.html:13759` | 第 1 处 `Native.connectCamera(ssid, pass)`（「连接相机」按钮 / 扫码后自动连） |
| `app/base.html:19551` | 第 2 处 `window.OM3Native.connectCamera(pick.ssid, pw)`（直连扫描到的那台） |
| `app/base.html:13675` | 记住的相机 `localStorage['om3cam']` = `{ssid, pass, model, serial, at}` —— **没有 bssid** |

---

## 3. 功能点（六要素）

### 3.1 UC-R64-01 `wifiScanList()` 返回 BSSID【原生】

| 项 | 内容 |
|---|---|
| 输入 | 无（读系统扫描缓存 `WifiManager.getScanResults()`，调用前先 `startScan()` 一次，与现状一致） |
| 输出 | JSON 数组，每项 `{"ssid":…,"level":…,"cam":…,"bssid":"AA:BB:CC:DD:EE:FF"}`；拿不到/不合法时 `bssid:"` `"`（空串） |
| 前置条件 | Wi-Fi 开着；13+ 有 `NEARBY_WIFI_DEVICES`、≤12 有 `ACCESS_FINE_LOCATION`（否则已返回 `err:`，与现状一致） |
| 后置条件 | 不改任何系统状态；去重（同名留信号最好的）与「前 24 个」规则不变 |
| 业务规则 | `bssid = camMacNorm(r.BSSID)`：合法 MAC 才给大写形式；全 0 / 广播 / `02:00:00:00:00:00` → 给空串 |
| 验收标准 | 源码里 `"bssid"` 字段与 `camMacNorm` 在位（`dv_r64` 静态断言）；`bssid` 合法时页面把 `pick.bssid` 传进了连接调用 |

### 3.2 UC-R64-02 `connectCamera2(ssid, pass, bssid)`：按 SSID + BSSID 精连【原生】

| 项 | 内容 |
|---|---|
| 输入 | `ssid`（必填，空 → `bad_ssid`）、`pass`（可空/可短）、`bssid`（可空；非法当没给） |
| 输出 | 返回码与 `connectCamera` **完全一致**（`asking` / `need_perm:xxx` / `dialog:xxx` / `sec_error:xxx` / `error:xxx` / `unsupported` / `bad_ssid`），**外加后缀 `@bssid`**（仅当这次**真的**把 BSSID 交给系统时） |
| 前置条件 | 与 `connectCamera` 相同（`SDK≥29`，否则 `unsupported`） |
| 后置条件 | `lastSsid/lastPass/lastBssid` 记为本次请求的值；请求的系统网络与旧路径一致（`requestNetwork` + 60 秒超时） |
| 业务规则 | ① `bssid` 先过 `camMacNorm`；② **只有 `SDK_INT > 30` 且 BSSID 非空才 `setBssid(MacAddress.fromString(·))`**（照官方）；③ `setBssid` 抛异常 → **吞掉继续按 SSID 连**（不许因为 BSSID 让连接失败），并在日志里写明 |
| 验收标准 | `dv_r64`：Java 源码里有 `setBssid(`、`MacAddress.fromString(`、`SDK_INT > 30` 门；node 里对 `camConnectRaw` 喂假 `Native`：有 `connectCamera2` 且 BSSID 合法 → 走 3 参 + `via='ssid+bssid'`；没有 `connectCamera2` → 退回 2 参；BSSID 非法 → 退回 2 参 |

### 3.3 UC-R64-03 连上之后把「实际连到哪个 AP」回报页面【原生】

| 项 | 内容 |
|---|---|
| 输入 | `NetworkCallback.onCapabilitiesChanged(Network, NetworkCapabilities)`（另在 `onAvailable` 里主动查一次 `getNetworkCapabilities`） |
| 输出 | `window.__om3camBssid(ssid, bssid, "cap")`；同时 `cameraState()` 增加 `bssid` 字段 |
| 前置条件 | `SDK_INT >= 30`（官方：Android 11 以前**什么也不做**）；拿不到 `WifiInfo` 就直接返回 |
| 后置条件 | `lastBssid` 更新为**实际**连上的那个 AP；没变化不重复推 |
| 业务规则 | ① SSID 去引号；② `bssid` 空 / `endsWith("00:00")`（官方判据：假值）→ 不回；③ SSID 必须等于本次请求的 `lastSsid`（官方 `f$a.b.equals(ssid)`）→ 防止把别的网络报成相机；④ 过 `camMacNorm` 再回；⑤ 值没变不重复推。**与官方的唯一差别（有意）**：官方还要求"以前就存过 BSSID 才更新"（只更新、不首次写入），我们**首次连上也记** —— 值已经过这 5 重判据，记下来更有用（见 §7）。 |
| 验收标准 | `dv_r64`：Java 里有 `onCapabilitiesChanged`、`getTransportInfo`、`getBSSID`、`endsWith("00:00")`、`lastSsid.equals(ssid)`；页面有 `window.__om3camBssid` 处理器，且**只更新、不新建**记录 |

### 3.4 UC-R64-04 挂起重试也要带上 BSSID（顺手修一处真 bug）

| 项 | 内容 |
|---|---|
| 说明 | `onRequestPermissionsResult(4713)` 里授权通过后要重连，原代码是 `new Bridge().connectCamera(s, pw)` —— **新建了一个临时 Bridge**：连接状态、`lastSsid/lastBssid` 全记在临时实例上，`bridge.cameraState()`（页面用来显示"已连接/哪个热点"的那个）**看不到**。本轮改成用同一个 `bridge`（带上 `pendBssid`）。 |
| 输入 | `pendSsid / pendPass / pendBssid`（新增第 3 个挂起字段） |
| 输出 | 与旧路径同一个返回码 |
| 前置条件 | 授权通过且 `pendSsid != null` |
| 后置条件 | 连接由**主** Bridge 实例发起（`bridge` 为 null 时保持旧行为不崩） |
| 业务规则 | 不改变"授权被拒 → 回调页面 `denied`"的行为 |
| 验收标准 | `dv_r64`：Java 里 4713 分支不再出现 `new Bridge().connectCamera(`；且 `pendBssid` 出现 ≥3 次（声明/赋值/使用） |

### 3.5 UC-R64-05 页面上两处连接调用统一走一个入口【页面】

| 项 | 内容 |
|---|---|
| 输入 | `camConnectRaw(ssid, pass, bssid)`（新函数） |
| 输出 | `{ r: <返回码>, via: 'ssid+bssid' \| 'ssid' \| 'bssid' \| 'none', bssid: <真正生效的 BSSID 或 ''> }`；`r` 已剥掉 `@bssid` 后缀（调用方的 `if/else` 判断不需要改） |
| 前置条件 | `Native` 存在（不存在 → `r:'unsupported'`，与旧行为一致） |
| 后置条件 | 无副作用（只发一次桥调用）；发日志说明走的是哪条路 |
| 业务规则 | ① 合法 BSSID + `Native.connectCamera2` 存在 → 走 3 参；返回里带 `@bssid` 才认 `via='ssid+bssid'`（**不让页面替原生吹牛**）；② 有 BSSID 但原生没这个方法 → 退回 2 参并 `log(…, 'warn')`；③ BSSID 非法 → 退回 2 参 |
| 验收标准 | 两处调用点（`connectNow`、`camDirectConnect.go`）都不再直接调 `Native.connectCamera(`；`dv_r64` 的 node 段 4 条断言全绿 |

### 3.6 UC-R64-06 记住的相机记录统一构造（新增 `bssid` 字段）

| 项 | 内容 |
|---|---|
| 输入 | `camRec(ssid, pass, keep, opt)`（新函数）；`keep` = 现有 `om3cam` 记录；`opt` = `{bssid, model, serial, at}` 需要覆盖的可选项 |
| 输出 | 新的记录对象（`bssid` 仅在合法时出现，不写空串） |
| 前置条件 | 无 |
| 后置条件 | 5 处 `camSave()` 全部改用它 → 记录结构**只有一处定义** |
| 业务规则 | ① SSID **变了** → 不继承上一台的 `model/serial/at/bssid`（沿用第 34 轮的规矩，别把上一台的信息挂到新相机上）；② SSID **相同** → 继承 `keep.bssid`；③ `opt.bssid` 优先（页面上刚扫到的 BSSID 比旧的准） |
| 验收标准 | node 段：`camRec('A','p',{ssid:'A',bssid:'AA:BB:CC:DD:EE:01',model:'OM-3'})` → 继承 bssid 与 model；`camRec('B','p',<A 的记录>)` → **没有** bssid/model；`opt.bssid` 非法 → 不写字段 |
| 附带修正（显式声明，不是悄悄改） | `base.html:14728`（扫码成功那处）原先是 `camSave({ssid, pass})` —— 会**清掉**已记住的 `model/serial/at`（重扫一次二维码就丢机型）。改用 `camRec` 后与其它 4 处一致（同 SSID 时继承）。 |

### 3.7 UC-R64-07 学习 BSSID：扫到就存，连上后系统报的就更新【页面】

| 项 | 内容 |
|---|---|
| 输入 | ① `camDirectConnect` 里 `pick.bssid`（来自 `wifiScanList`）② `window.__om3camBssid(ssid,bssid,src)`（来自原生回调） |
| 输出 | 更新 `om3cam` 记录 + 日志 + `renderSaved()` |
| 前置条件 | 记录里已有同一个 `ssid`（`camBssidMerge` 里判）；BSSID 合法；**确实变了** |
| 后置条件 | 下次连接（`connectNow` / 直连）会把 `bssid` 传给原生 |
| 业务规则 | SSID 对不上 / BSSID 不合法 / 没变化 → **什么都不做**（不覆盖、不新建记录） |
| 验收标准 | node 段：`camBssidMerge` 四类输入（对得上+变了 → 新对象；对得上但没变 → `null`；SSID 不同 → `null`；BSSID 非法 → `null`） |

### 3.8 UC-R64-08 界面上"看得见但不喧宾夺主"【页面】

| 项 | 内容 |
|---|---|
| 输入 | `om3cam.bssid`、`cameraState().bssid` |
| 输出 | ① `#camSaved` 行尾多一段淡色小字 `BSSID AA:BB:…（记住它，连接时优先钉住这一个）`；② 「已连接」卡的信息行（`#camOnInfo`）多一项 `BSSID：…`；③ 连接日志写明走的是 `SSID+BSSID` 还是只 `SSID` |
| 前置条件 | BSSID 合法 |
| 后置条件 | **不新增任何 HTML 元素 id**（只在既有容器里加文字） |
| 业务规则 | BSSID 为空时**不显示**（不写"未知"，避免用户以为坏了）；**不新增输入框**（相机屏幕上只写 SSID/密码，用户抄不到 BSSID） |
| 验收标准 | `dv_r64` 静态：`base.html` 的 id 集合**一个不多一个不少**；`camOnInfo` 里出现 `BSSID`；`renderSaved` 里出现 `BSSID` |

### 3.9 UC-R64-09 扫描到多台时优先挑「记住过 BSSID 的那一台」【页面】

| 项 | 内容 |
|---|---|
| 输入 | `cands[]`（候选热点）+ `om3cam.bssid` |
| 输出 | `pick` |
| 前置条件 | 候选里有 BSSID 与记录相同的项 |
| 后置条件 | `pick` 换成那一个 |
| 业务规则 | 找不到匹配就保持原来的 `cands[0]`（信号最强）——**不改变既有默认行为** |
| 验收标准 | `dv_r64` 静态：`camDirectConnect` 里出现 `camBssidOk(cands[ci].bssid)` 的挑选循环 |

### 3.10 UC-R64-10 直连路径「成功了却报失败」顺手修正【页面】

> 实施时发现的既有 bug，**不是本轮新引入**；按护栏要求显式声明并落成规格（不许只记在差异分析里）。

| 项 | 内容 |
|---|---|
| 现象 | `camDirectConnect` 的 `go()` 里判的是 `if(r === 'ok')`，但原生 `connectCamera` **成功时回的是 `asking`**（见 §3.2 的返回码表）→ 用户点了「连接相机」，实际已交给系统，界面却显示「连接失败：asking」。 |
| 输入 | `camConnectRaw(...).r` |
| 输出 | 成功时显示「已发起连接 —— 连上后这里会自动变成"已连接：…"」 |
| 前置条件 | 返回码是 `ok` 或 `asking` |
| 后置条件 | 不改变任何连接行为（只是文案判定），`need:` / `CHANGE_NETWORK_STATE` / 其它错误分支顺序不变 |
| 业务规则 | `if(r === 'ok' \|\| r === 'asking')` 都算"已发起" |
| 验收标准 | `dv_r64` node 段：原生回 `asking@bssid` 时 `r` 剥成 `asking`（调用方的判定链不受 `@bssid` 影响）；页面静态断言该行含 `'asking'` |

---

## 4. 实施方式（生成脚本 + 直接改 Java，都不手改大文件）

1. 页面（3.8 MB）**只由** `scripts/gen_r64.py` 改：幂等标记 `r64：BSSID`，**13 处锚点**（含 1 处整块新增）各自断言"命中 1 次"，改完自检新标记在位。
2. Java（1379 行）直接改：先 `cp Java MainActivity.before_bssid.java`；改完由 `build.sh` 的 `javac --release 8` 兜底（编译不过 = 立刻红）。
3. 页面改动集中在**块 08**（`app/base.html` 行 12867–19666，同一个 IIFE 闭包内）→ 新函数直接互相调用，**不需要** `window.` 导出（除 `window.__om3camBssid` 这个原生回调入口，必须挂 window）。

---

## 5. 不涉及项（显式声明）

- **不新增/不改任何系统权限**（`AndroidManifest.xml` 一个字节都不改）。
- **不改 `joinWifi` / `addNetworkDialog`（不改 `WifiNetworkSuggestion` 的 BSSID）** —— 见 §7 主动不做。
- **不改蓝牙链路**（BLE 唤醒、配对码、结果码表全部不碰）；**不改 MySet 读/写/备份流程**；**不改布局/折叠顺序**（第 62 轮刚定的不动）。
- **不改版本号规则**（仍由 `build.sh` 里的 `bumpver.py` 在 mkasset 之后写）。
- **不新增 localStorage 键**（`om3cam` 里加字段）。
- **不改 `scripts/check_*` 的判据**（四数基准照旧比对，不许调松）。
- **不涉及**桌面单文件 HTML 的特殊处理（`Native` 不存在时新代码走 `unsupported` 分支，与旧版一致）。

---

## 6. 验收标准（可逐条跑）

```bash
python scripts/gen_r64.py            # 幂等：连跑两次，第二次打印"已经是目标状态"
python scripts/gen_r64.py           # （第二次）
python scripts/check_syntax.py      # 内联脚本语法
python scripts/live_check.py        # 错误数=0（且与改前逐字段一致）
python scripts/check_app.py         # 四数：卡 77 / 按钮 110 / 槽位 33 / 方案 1 / 可见步骤 [1] / om3errs=0
python scripts/verify_all.py        # 页签/底栏/置灰/搜索
python scripts/dv_r64.py            # 本轮探针：静态 + node 功能段（全绿）
python scripts/dv_r62.py            # 防回归（41/41）
cd apk && bash build.sh             # → v3.18
python scripts/check_app.py "D:\workspace\om3-handbook\apk\assets\index.html"   # 最终产物复验
```

**逐条验收点**
1. `gen_r64.py` 幂等（跑两次结果一致，第二次不改盘）。
2. `check_syntax` / `live_check` 错误数 0；`check_app` 四数与改动前**完全一致**。
3. `dv_r64` **61/61** 全绿：Java 静态 **22** 条（`connectCamera2` / 老方法转调 / `setBssid` / `SDK_INT > 30` 版本门 / 抛异常吞掉 / `@bssid` 后缀 / `volatile` / `onCapabilitiesChanged` / `getTransportInfo`+`getBSSID` / 官方三条判据 / `camMacNorm` 占位值 / `wifiScanList` 带 bssid / `cameraState` 带 bssid / 4713 用主实例 / `pendBssid`）+ **真跑一次 `javac`**）+ 页面静态 **12** 条（id 集合不变、`camConnectRaw` 之外不直接调原生、四个新函数各只定义一次、5 处 `camSave` 全走 `camRec`、两处显示在位…）+ node 功能 **27** 条（`camBssidOk` 9 / `camRec` 6 / `camBssidMerge` 5 / `camConnectRaw` 7）。
4. `dv_r62` 复跑 41/41（第 62 轮的 id/折叠/字段位序不回归）。
5. 出包 v3.18 且桌面 APK 已更新；`apk/assets/index.html` 复验四数一致、`om3errs=0`。

---

## 7. 主动不做（写清原因，避免被当成漏写）

| 不做 | 原因 |
|---|---|
| 给 `joinWifi`（`WifiNetworkSuggestion`）设 BSSID | suggestion 是"长期交给系统自动连"的东西：一旦钉死 BSSID，**相机换了 MAC / 系统 MAC 随机化 / 屋里多一个同名 AP** 时这条建议就永远不匹配 → 用户会觉得"自动连突然坏了"，只能靠「忘掉这台相机」救。相机的 SSID 本身唯一，收益小、风险大。**连接（`requestNetwork`）那条路才需要钉**，那正是官方钉的地方。 |
| 手动输入 BSSID 的输入框 | 相机屏幕只显示 SSID/密码，用户抄不到 BSSID；填错的后果是"连不上"。BSSID 全靠自动学习（扫描 / 连上后系统报告）。 |
| Android 11 及以下也设 BSSID | 官方就是 `SDK_INT > 30` 才设（`dis.txt` 164528 `if-ge`）；跟官方一致，低版本退回按 SSID 连并在日志里说明。 |
| 用 BSSID 去判断"是不是相机热点" | BSSID 的 OUI 不专属于 OM System（路由器也可能同 OUI），判据仍用"SSID 正则 + 官方 BLE 服务 UUID"。 |
| 照抄官方"必须先存过 BSSID 才更新" | 官方在 `onCapabilitiesChanged` 里要求 `prefBSSID` 非空才写（只更新、不首次写入）。我们**故意放宽**：首次连上就把真值记下来对用户更有用，而且值已经过 5 重判据（SDK≥30 / SSID 对得上 / 非空 / 不是 `…00:00` / 过 MAC 校验）。**这是一处有意的行为差异**，见 §3.3。 |
| 本轮做真机验证（候选 ②） | 需要需求方拿 OM-3 实测；本轮改动都写了日志，等需求方给了日志再判。 |

---

## 8. 验收结果 / 差异分析

（**改完回填**：逐条验收结果 + 设计与实现的差异，差异必须落到"改代码或改规格"，不许只记录。）

### 8.1 逐条验收（2026-09-28 实跑）

| # | 验收点 | 命令 | 结果 |
|---|---|---|---|
| 1 | 生成脚本幂等 | `python scripts/gen_r64.py` ×2 | 第一次改 13 处（净增 5791 字节）；第二次打印"已经是目标状态（页面里有 "r64：BSSID"）—— 不重复改" ✅ |
| 2 | 内联脚本语法 | `python scripts/check_syntax.py` | 10 个块全部通过 ✅ |
| 3 | 加载期运行时报错 | `python scripts/live_check.py` | `错误数=0`；与改前（`base.before_r64.html`）**逐字段完全一致**（`om3errs=3 缺元素=3 …`）✅ |
| 4 | 四数验收 | `python scripts/check_app.py`（改前/改后各一次） | 两边**完全相同**：配方卡 77 / 加入方案按钮 110 / 优化版槽位 33 / 方案条目数 1 / 可见步骤 `[1]` / `om3errs=0 运行错误=0` ✅ |
| 5 | 页签/底栏/置灰/搜索 | `python scripts/verify_all.py` | 全通过（顶栏模块 5、底栏 fixed、置灰项 3、卡片堆叠 true、运行错误 0）✅ |
| 6 | **本轮探针** | `python scripts/dv_r64.py` | **61/61 通过**：Java 静态 22 条（含真跑 `javac --release 8` 通过 + 产出 `MainActivity.class`）；页面静态 12 条；node 功能 27 条 ✅ |
| 7 | 防回归 | `python scripts/dv_r62.py` / `dv_r63.py` / `dv_r57.py` / `dv_scene39.py` / `dv_r56.py` | 41/41、**16/16**、47/47、27/27、39/39 ✅（`dv_r63` 有 1 条按 §8.3 做了**测量对象纠正**） |
| 8 | 出包 | `cp app/base.html app/index.html && python apk/mkasset.py && cd apk && bash build.sh` | **v3.18（build 318）**，79.3 MB，签名证书与旧版同一把（`om3.jks`）✅ |
| 9 | 发布 | `cp apk/build/om3.apk 桌面` | 桌面 APK 已更新（79,288,457 字节，时间 14:05）✅ |
| 10 | 最终产物复验 | `python scripts/check_app.py apk/assets/index.html` | 四数与改前一致、`om3errs=0`、产物里有 `r64：BSSID` ✅ |
| 11 | **新方法真进了 APK** | 解开 `om3.apk` 的 `classes.dex` 搜方法名 | `connectCamera2`×1、`camNoteBssid`×1、`setBssid`×2、`@bssid`×1 —— 不是"只改了源码没进包" ✅ |

**改动规模**：页面 3,801,650 → **3,807,441** 字节（净增 **5791**，20,359 行）；Java 1379 → **1492** 行。
`app/base.html` md5：`a0c8b6280f8d0876500aa410bac806cc` → **`3692725c82e022d643b69c465d77f474`**
`MainActivity.java` md5：`fdc19cf86c5d0537771783bb0f5f9f1a` → **`ae4e69fe4be824612497e0b1aeec6432`**

### 8.2 设计与实现的差异分析（逐条有结论：改代码 or 改规格）

| # | 规格原定 | 实际实现 | 结论 |
|---|---|---|---|
| 1 | §3.2 说"**改** `connectCamera(ssid,pass)` 的签名"（HANDOVER 候选①的写法） | 改成**新增** `connectCamera2(ssid,pass,bssid)`，老方法**原样保留**并转调新方法 | **改规格（已改）**。理由：改签名等于"页面与 Java 必须严格同步"，任何一侧落后（老页面配新 Java / 新页面配老 Java）调用点会直接抛异常；保留老方法 + 新方法则两边都能跑，页面还会自动退回（`dv_r64` 的 `crOldApk` 用例钉住这条）。**不是需求变更，是实现方式更稳。** |
| 2 | 设计阶段没写"页面怎么知道 BSSID 到底用上没" | 实现加了 `pinned` 标志 + 返回码后缀 `@bssid`，页面据此报"按 SSID+BSSID 精连"或只报"按 SSID 连" | **改规格（已改）**：补进 §3.2 的"输出"与 §3.5 的"业务规则"。理由：安卓 11 及以下会**故意不设 BSSID**（跟官方），如果页面一律写"已钉住"就是**新的说反**（第 61 轮的教训）。 |
| 3 | 设计阶段未列"直连路径把 `asking` 当失败" | 实施时发现并修（`r === 'ok' \|\| r === 'asking'`） | **改规格（已改）**：新增 §3.10 UC-R64-10 显式声明（不许只写在差异分析里）。 |
| 4 | 设计阶段未写"官方只更新、不首次写入 BSSID"这一条差异 | 实现**首次连上也记**（其余 5 重判据照官方） | **改规格（已改）**：补进 §3.3 业务规则 + §7 主动不做表。理由写清：值已过 5 重判据，首次记住对用户更有用。 |
| 5 | 设计阶段说"5 处 `camSave` 统一走 `camRec`" | 实施时确认第 5 处（扫码）原先会**清掉**机型/序列号 | **改规格（已改）**：§3.6 的"附带修正"行（原先只写在表格里，现已点明是显式声明的行为变化）。 |
| 6 | §6 写"`dv_r64` Java 侧 6 条静态断言" | 实跑 22 条 Java 断言（还加了 javac 真编译） | **改规格（已改）**：§6 第 3 条按实际条数改写（说的比做的少也算不一致）。 |

### 8.3 本轮自己踩的坑（都被探针/复跑兜住，逐条记下）

| 坑 | 现象 | 处理 |
|---|---|---|
| **探针的假 `Native` 给少了** | `dv_r64` 的 node 段一开始有 3 条红（`crNoSuffix` / `crPerm` / `crThrow`），值全是 `unsupported` | 根因：假 `Native` 只给了 `connectCamera2`，页面第一道兜底 `if(!Native \|\| !Native.connectCamera)` 先命中 → 返回 `unsupported`。**真实 app 两个方法同时存在**，所以是**夹具错**（不是页面错）→ 补上 `connectCamera` 桩。**没有改松任何断言。** |
| **静态断言写得不精确**（1） | `cameraState()` 那条一直红 | 我断言的字面串漏了前导逗号（Java 里是 `+ ",\"bssid\":" + jsonStr(...)`）→ 改成 `r'"bssid\":" + jsonStr(lastBssid)'`。 |
| **静态断言写得不精确**（2） | "页面里没有直接调 `connectCamera`"那条红 | `camConnectRaw` **自己**的兜底分支里就有一句 `Native.connectCamera(ssid, pass)`（那是设计要保留的）→ 断言改成"**把新增函数块抠掉之后**，页面里再没有 `.connectCamera(` / `.connectCamera2(`"。 |
| **把注释也算进了计数** | `new Bridge()` 计数那条红（期望 1，实得 3） | 我自己的注释里引用了旧代码 `new Bridge().connectCamera(s, pw)` → 改成断言"`if (bridge != null) … / else new Bridge()…` 两行相邻"，既精确又不受注释影响。 |
| **`dv_r63` 的字节差断言过期** | `dv_r63` 由 15/15 变 14/15（"整份页面只多了 6148 字节（纯文案替换）"） | 根因：那条量的是 `base.html − base.before_r63.html`，第 64 轮必然把它顶爆。**测量对象纠正**：改成量 `base.before_r64.html（= 第 63 轮产物）− base.before_r63.html`，**阈值仍是 400 字节**，并另加一条"当前页面比第 63 轮改前更长"。不是放松判据（探针测的仍是第 63 轮那一次改动）。 |
| **首次实现连 `live_check` 都对不上** | — | 这次没有；`live_check` 改前/改后逐字段一致，四数也一致 —— 因为页面只加了函数与调用点，没有触碰加载期路径。 |

### 8.4 遗留与下一轮

1. **只能真机验**：`setBssid` 到底有没有让系统"只连那一个 AP"、`onCapabilitiesChanged` 能不能拿到 `WifiInfo`（有些 ROM 只给 `02:00:00:00:00:00`）—— 都需要需求方拿 OM-3 跑一次并把日志发来。
   真机自查点（都已写进日志）：`[连相机] 按 SSID+BSSID 连` / `（钉住 BSSID xx）` / `[连相机] 学到 BSSID …（连接后系统报告）`。
2. 若真机上发现 BSSID 反而让连接变慢/失败，**回退只有两步**：`cp app/base.before_r64.html app/base.html` + `cp MainActivity.before_bssid.java …`（页面侧还有一层自动退回，见 §1 兼容性）。
3. 第 65 轮（.cgi 参数表）、第 66 轮（camprop 方案）见 §9。

---

## 9. 另外两项候选的处置（回答「能做的都做」）

| 候选 | 处置 |
|---|---|
| ② 真机验证第 62 轮的连接改动 | **只能需求方配合**（要有 OM-3 + 手机）。本轮不碰；需要时按 `SPEC-round62.md` §6 的清单走。 |
| ③ 官方 App 剩余 53 个 `.cgi` 参数表 | **另开一轮**（第 65 轮）：写 `official_app/oi_cgi.py`（按 CGI 名自动抽「调用点 + 参数键 + 相关字符串」）+ `SPEC-round65.md`。**不在本轮混做** —— 一轮一个主题，结论才好落。 |
| ④ camprop「单项实时改参」 | **另开一轮**（第 66 轮，产品选择题）：先出方案（做/不做、做成什么样、和现 MySet 通道的关系），再定实施。 |
