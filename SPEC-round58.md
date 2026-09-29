# 第 58 轮：官方 App（OI.Share）「连接手机」操作逻辑分析

> 目的：用户要「把官方的操作逻辑全部分析好」。本轮只做**分析**，不改手册 App。
> 素材：`om share.apk`（124.9 MB，`com.omdigitalsolutions.oishare`）反编译产物。
> 方法：`dexdump` 反汇编 → 自建结构索引 → 交叉验证（详见 §7「怎么得出这些结论」）。
> 本文件把结论分三档：**【已确证】**（有代码证据）／**【推测】**（证据支持但未逐字节验证）／**【未解】**。

---

## 0. 一句话结论

官方 App 连接相机是**四段式**：

```
① BLE 广播扫描（找相机）
   → ② BLE 连上 GATT，写"握手/鉴权/开机"三条命令（自定义 16 位 opcode 帧协议）
   → ③ 相机把 Wi-Fi 打成一个 AP；App 用 WifiNetworkSpecifier 按 SSID+BSSID+密码切过去
   → ④ 在 Wi-Fi 上对 http://192.168.0.10/ 调 68 个 .cgi 接口（取图/传图/遥控/改参数/固件）
```

关键事实：**相机的 HTTP 地址是固定 IP `192.168.0.10`**（不是域名、不是 mDNS），
所以「连相机」的本质就是「让手机加入相机自建的那个 Wi-Fi，然后访问 192.168.0.10」。

---

## 1. 连接相关的类地图【已确证】

包名 `com.omdigitalsolutions.oishare`，**UI/业务包基本没混淆**（类名可读），
只有 BLE 协议与传输两层被混淆成短名（`M2/*`、`N2/*`、`c2/*`、`J2/*`、`s2/*`、`t2/*`）。

| 层 | 类 | 作用 |
|---|---|---|
| 入口/流程 | `oishare.b`（`BaseFragmentActivity`） | 所有 Activity 的基类；`isDeviceConnected / showDeviceConnect / showImgTrans` |
| 入口 | `home.HomeActivity` | 主页；连接按钮 `HomeActivity$Z.onClick` |
| 设备页 | `device.DeviceConnectActivity` | 「连接相机」页（`buttonCameraStart`） |
| 设备页 | `device.DeviceWifiActivity` / `WifiSelectActivity` / `WifiSettingActivity` | 选 Wi-Fi / 连相机 AP |
| 设备页 | `device.DeviceQRActivity` / `ManualSettingActivity` | 扫码 / 手动输入 |
| 设备页 | `device.BluetoothSettingActivity` | 蓝牙权限/设置引导 |
| 连接完成 | `device.ConnectCompleteActivity` | 「连接完成」 |
| 相机状态机 | `oishare.e`（84 个方法） | **连接总控**：扫描→连接→鉴权→开机→切换模式→通知 UI |
| 相机状态机 | `oishare.track.d` / `d$i` | BLE 结果回调（`OlyBleConnectListener.onResult`） |
| BLE 协议 | `M2/b`（+ `M2/a` 数据对象、`M2/b$b/$c/$d`） | 自制 BLE 帧协议：组帧 `u()`、命令 12 条、应答等待 |
| BLE 传输 | `N2/a`（+ `N2/a$*`、`N2/c`） | Android BLE：扫描、连接、GATT、写特征、通知回调 |
| Wi-Fi 切换 | `J2/a`、`J2/d`、`J2/e` | 记住相机 AP、`WifiSwitcher` 切换标准 AP↔相机 AP、`WifiNetworkSpecifier` |
| Wi-Fi 工具 | `c2/F`（`.convertSSID`）、`c2/A`（配置读写） | SSID 转换、取配对参数 |
| HTTP | `oishare.a$c`、`oishare.d`、各 Activity | `.cgi` 调用（取图、传图、遥控、固件…） |

---

## 2. BLE 帧协议（`M2/b`）【已确证】

### 2.1 组帧格式（`M2/b.u(II[B)[B`，45 条指令）

反汇编逐字节可读出（`u()` 的实际写字节序列）：

| 偏移 | 值 | 含义 |
|---|---|---|
| 0 | `0x01` | 固定头 |
| 1 | `seq` | 序号：取实例字段 `M2/b.d`（`B`），**每发一帧 +1，回绕** |
| 2 | `len+3` | 长度 = 负载长度 + 3 |
| 3 | `w1` | 命令高字节（第 1 个 int 参数） |
| 4 | `w2` | 命令低字节（第 1 个 int 参数 +1；即整个 16 位 opcode 拆两字节） |
| 5 | `argc` | 第 2 个 int 参数（子命令/参数个数） |
| 6.. | payload | 负载 |
| 末尾-2 | `sum & 0xFF` | **累加校验**（含偏移 4 起，含 len 字段） |
| 末尾-1 | `0x00` | 结束 |

> 证据：`u()` 方法体可完整读出（`oi_graph.py 'M2/b;' --body u`）。

### 2.2 命令表（`M2/b`，12 条发送 + 对应的"期望应答"）

`M2/b$b.a()`（`Callable`，142 条指令）是**命令分发器**，逐个 `Integer.valueOf(...)` → 调用 12 个发送方法。
每个发送方法调用传输层的 `N2/a.s0(opcode, payload, len)`（写特征）或 `N2/a.r0(opcode, payload)`。
从发送方法的常量可直接读出 opcode：

| opcode | 发送方法 | 载荷 | 同组等待方法 | 猜测用途 | 证据 |
|---|---|---|---|---|---|
| `0x6801` | `M2/b.D` | 1 字节小数组 | `A(II)I` | 连接/会话类命令 ① | 反汇编：`aput-byte #1` + `s0(26625,…)` |
| `0x6802` | `M2/b.C` | 1 字节小数组 | `A(II)I` | 连接/会话类命令 ② | 同上（`#2` / `s0(26626,…)`） |
| `0x6803` | `M2/b.B` | 1 字节小数组 | `A(II)I` | 连接/会话类命令 ③ | 同上（`#3` / `s0(26627,…)`） |
| `0x6901` | `M2/b.K` | 小数组（未细看） | 等待码 `0x0F` | Wi-Fi/模式类 ① | `s0(26881,…)` |
| `0x6902` | `M2/b.I` | 小数组（未细看） | 等待码 `0x10` | Wi-Fi/模式类 ② | `s0(26882,…)` |
| `0x6903` | `M2/b.H` | 小数组（未细看） | 等待码 `0x0C` | Wi-Fi/模式类 ③ | `s0(26883,…)` |
| `0x6A01` | `M2/b.E` | 1 字节小数组 | `F(II)I` | 遥控/参数类 ① | 反汇编：`aput-byte` + `s0(27137,…)` |
| `0x6B01` | `M2/b.G` | 字符串（UTF-8） | `J([BI)I` | 遥控/参数类 ②（日志：`RMC-データコマンド発行：`） | `s0(27393,…)` + 字符串 |
| `0x0F01` | `M2/b.x` | 小数组 | `y(I)I` | **开机（電源ON）** | `e$e.run` 调 `y(20000)` → 日志 `.powerOn powerOnSync ret=` |
| `0x0410` | `M2/b.v` | 小数组 | `w(II)I` | 参数/模式类 | `s0(1040,…)` |
| `0x040F` | `M2/b.z` | 小数组 | `A(II)I` | 参数/模式类 | `s0(1039,…)` |
| `0x0C02` | `M2/b.i` | **字符串**（UTF-8） | `j(String)I` | **鉴权（密码/配对码 PASSCODE）** | `e$d.run` 调 `j(密码)` → 日志 `.authPasscode authPasscodeSync ret=` |
| `0x1D01` | `M2/b.L` | 小数组 | `M(II)I` | 心跳/保活（`0x1D`=29） | `s0(7425,…)` |

> 「载荷」列只有 **0x6801/02/03、0x6A01**（反汇编直接读到写字节）、**0x6B01/0x0C02**（`String.getBytes("UTF-8")`）
> 是逐字节看过的；其余标「小数组（未细看）」，不硬说字节数。

> 说明：`0x0C02` / `0x0F01` / `0x1D01` 的**用途**由调用点的日志字符串确证（`authPasscode` / `powerOn`），
> 属语义确证；`0x68xx/0x69xx/0x6A01/0x6B01` 的具体语义见 §3 的连接时序与 §6「未解」。

### 2.3 并发模型【已确证】

- `M2/b` 字段：`a:N2/a`（传输）、`c:M2/b$d`（回调）、`d:B`（序号）、`g:[B`、`i:I`（超时）、
  `k:M2/d`、`l:M2/d`（发送/等待队列）、`r:N2/a$f`（传输回调）。
- **发命令 = 建一个 `Callable` 放进 `M2/b$b`，`Executors.newFixedThreadPool(1)` 单线程串行执行**，
  再用 `Future.get()` 阻塞等结果（见 `M2/b.A/F/J/M/w/y` 的长方法，51 条指令里就是这套）。
- 等待侧：`A(II)I` 等把「序号 + 期望应答码 + 超时」配对，超时返回 `-2`，异常 `-1`。

### 2.4 GATT 与 UUID【已确证】

- `N2/a` 字段：`b:BluetoothAdapter`、`e:BluetoothGatt`、`I:BluetoothGattCallback`（final）、
  `E:Object`（final，**锁**）、`d:ArrayList`（扫描结果）、`t:ArrayList`、`q/x:M2/d`、`v:BroadcastReceiver`。
- 扫描/连接走 Android 标准 API：`BluetoothLeScanner.startScan`、`BluetoothGattCallback`、
  `setCharacteristicNotification`、`writeCharacteristic`。
- UUID：通用描述符 `00002902-0000-1000-8000-00805f9b34fb`（CCC 描述符，开通知用）；
  另有 4 个 128 位自定义 UUID（`b7a8015c-…` / `adc505f9-…` / `82f949b4-…` / `05a02050-…`），
  用途**未逐一确认**（见 §6）——很可能就是相机 BLE 服务/收发特征。

---

## 3. 连接时序【已确证（骨架）】

总控在 `oishare.e`，四个关键 `Runnable` 串起来：

| 步 | Runnable | 调用的协议方法 | 日志字符串（原文） | 判定 |
|---|---|---|---|---|
| ① 开始搜索 | `e$a.run` | `M2/b.N(ssid, name, 2)`（扫描，超时=2） | `.startDetect 検索開始` | `e.a()` 为假才启动 |
| ② 连接模式确认 | `e$c.run` | `M2/b.l(String, Z)Z`（18 条指令） | `.scanResultConnectMode 接続開始` / `接続失敗なのでもう一度` / `リトライ` / `何も見つからない mScanRetry=` | 失败→`e.h(null)`+`e.f()` 重试；成功→`Handler.sendEmptyMessageDelayed(10, …)` + 置结果码 6 |
| ③ 鉴权过码 | `e$d.run` | **`M2/b.j(passcode)`**（`0x0C02`） | `.authPasscode authPasscodeSync ret=` | `ret==0` → `e.l()` 进入下一步；否则 `e.J()` + 结果码 **34** |
| ④ 相机开机 | `e$e.run` | **`M2/b.y(20000)`**（`0x0F01`，超时 20 s） | `.powerOn powerOnSync ret=` | `ret>=0` → `e.m(0)`；否则 `e.J()` + 结果码 **35** |
| ⑤ 连上之后 | `e.b`（通知） | `e.I()` | — | — |
| 取消 | `oishare.e.A()`（`authPasscode`） | `M2/b` 为空 → `e.C(0xFFFF)`；已取消 → 直接返回 | `.authPasscode 既にキャンセルされている` | — |

**状态码（`OlyBleConnectListener` 结果）**【已确证字符串，编号为推测】：

```
0 = 默认失败（default）    1 = 已连接已连（ALREADY_CONNECTED）
5 = 搜索中（SEARCHING）     6 = 连接中（CONNECTING）
34 = 密码错（PASSCODE_ERROR）  35 = 开机失败（POWON_ERROR）
另见：BLE_RESULT_DISCONNECTED / NOT_FOUND / SUCCESS / BLUETOOTH_OFFON / GPS_OFF / FINALIZE / ABNORMAL_CONDITION
```

> `oishare.track.d$i.H(I)V`（128 行）是这批结果码的**分发器**（`if-eqz/if-eq 1/5/6` → 分别处理，
> 其余走 default），在这里可逐条对照 UI 行为。

> **上表证据强度**：日志字符串是**逐条反查**得到的（索引里查 `'powerOn'` → 命中 `e$e.run`；
> 查 `'authPasscode'` → `e$d.run`；查 `'scanResultConnectMode'` → `e$c.run`；查 `'startDetect'` → `e$a.run`），
> 不是靠类名前缀猜的。状态码 34/35 来自 `e$d.run` / `e$e.run` 里的 `const/16 #int 34` / `#int 35`。

**其它已确证的开关**：
- `oishare.track.d$j.run`：BLE 检测完成 → 取单例 `OIShareApplication.J()`（= `oishare.e`）→ `e.L()` 拿 `M2/b`。
- `HomeActivity$Z.onClick`：连接按钮，读 `str.PairingCameraSsid` / `str.bleName` / `str.PairingCameraName`
  （都是 **String 资源名**，即真正文案在 `res/values-ja|en` 里）→ 显示「配对中」对话 → `OIShareApplication.J()` 启动连接。
- 相机名/BLE 名/SSID 来自资源，不是硬编码 —— 不同机型/地区可不同。

---

## 4. Wi-Fi 切换【已确证（机制）+ 推测（触发点）】

### 4.1 机制

- **相机 HTTP 固定地址：`http://192.168.0.10/`**（出现 10 次，另有 8 次 `http://192.168.0.10`），
  所有 `.cgi` 都挂在这个 IP 下（如 `http://192.168.0.10/get_connectmode.cgi`）。
- `J2/e`：用 **`WifiNetworkSpecifier.Builder`** 按 `setBssid(MacAddress)` + SSID + 密码
  请求连接（Android 10+ 的"按需连指定 AP"，不需要用户去系统设置里点）。
  字段/字符串：`str.wifi.camera.ssid` / `str.wifi.camera.bssid` / `str.wifi.camera.password`。
  `J2/e$b.run`、`J2/e$c.onCapabilitiesChanged/onUnavailable` 都出现 `str.wifi.camera.bssid`。
- `J2/a`：**记住**相机 AP（`.updateCameraAP ssid=`、`connectedCameraAP:`、`.checkConnectTimeout`、
  `.connectTimeout`），注释式日志「**ワンタイム、モード不明時は覚えない**」（一次性模式/模式不明时不记），
  「不明なSSIDは覚えない ssid=」（未知 SSID 不记）。
- `J2/d`（`WifiSwitcher`）：`.currentDisconnect change std. ap.`（切回标准 AP）、
  `removeCameraAP 今まで使用していた netId=`（删旧的相机 AP 配置）、`WifiSwitcher#WifiApChanger.turnWifi:`。
  支持多档：`isWifiPlayOnlyPrivateEnabled` / `isWifiPrivateEnabled` / `isWifiOnetimeEnabled`。
- `J2/b$f`：`WifiConnectListener 接続NG` / `接続OK` → 连上/失败回调。
- 连接前先「扫描找目标 AP」：`J2/a$z` 日志 `scanResults targetAP detected: %s, start connect` /
  `targetAP go out` / `targetAP detected skip (connectState/connectTry)`。
- Wi-Fi 开关走 Android：`WifiManager.setWifiEnabled(Z)`（`J2/d$a`、`WifiSelectActivity$f`）。
- SSID 转换：`c2/F.d`（`.convertSSID`）。

### 4.2 两种"连接模式"

- `get_connectmode.cgi`：查相机当前连接模式；`WifiSwitcher.setConnectModeInner mode: ` ← 模式号；
  `WifiSwitcher.setCameraInfoInner modelName: ` ← 机型。
- `oishare.b` 里另有 `str.wifi.Security.Type`、`wifi`（WPA2/WPA3：见 `setWpa2Passphrase` / `setWpa3Passphrase`）。
- 「远程遥控 vs 传图」两类场景都走 `e.L()` 这台相机对象，区别在连接模式（BLE 常连做遥控；Wi-Fi 大带宽做取图/传图）。

### 4.3 开机失败的特殊分支【已确证】

`e$e.run` 里有「Buletooth接続モード、Locationモード時は電源ONしない」的日志分支，
即：某些模式下**不发开机命令**（相机本来就在运行）。

---

## 5. 68 个 HTTP 接口（控件/遥测全清单）【已确证】

全部形如 `http://192.168.0.10/<name>.cgi`。按用途分组：

| 分组 | 接口 |
|---|---|
| **查询** | `get_caminfo` `get_camprop` `get_connectmode` `get_commandlist` `get_dcffilenum` `get_exif` `get_imglist` `get_rsvimglist` `get_movfileinfo` `get_moviestreaminfo` `get_screennail` `get_thumbnail` `get_resizeimg` `get_resizeimg_witherr` `get_trimresizeprocstatus` `get_unusedcapacity` `get_playtargetslot` `get_cameraloginfo` `get_partialcameralogdata` `get_snsloglist` `get_gpsloglist` `get_gpsdivunit` `get_agpsinfo` `get_mysetname` `get_mysetdatasize` `get_mysetdatamodekind` `get_mysetbackupstate` `get_mysetrestorestate` `get_partialmysetdata` |
| **设置/动作** | `set_camprop` `set_takemode` `set_timeout` `set_utctimediff` `set_playtargetslot` `set_mysetdatasize` `switch_cammode` `exec_shutter` `exec_takemotion` `exec_takemisc` `exec_erase` `exec_reboot` `exec_pwoff` `exec_movietrimresize` `cancel_trimresize` |
| **状态检查** | `check_gpsrecording` `check_mountmedia` `check_snsrecording` |
| **直播流** | `start_moviestream` `start_moviestreamts` `ready_moviestream` `exit_moviestream` `stop_moviestream` |
| **GPS/日志** | `req_attachexifgps` `req_storegpsinfo` `send_agpsassistdata` `update_agpsassistdata` `clear_cameralogdata` |
| **相机设置(MySet)** | `request_getmysetdata` `request_restoremysetdata` `send_partialmysetdata` `set_mysetdatasize` |
| **固件升级** | `fwup_check` `fwup_getversions` `fwup_getfirmstatus` `fwup_sendinfo` `fwup_sendsplit` `fwup_update` `fwup_updatemode` |
| **其他** | `clear_resvflg` |

> 注意：**这 68 个是官方 App 里出现的全部**。手册 App 若只做「配方→槽位/参数」，用不到大部分；
> 但若要复刻「遥控/取图」，`get_camprop`/`set_camprop`/`exec_shutter`/`exec_takemotion` 是核心。

---

## 6. 【未解 / 待确认】（不留 TODO 假实现，明确挂出来）

1. **`0x68xx` / `0x69xx` / `0x6A01` / `0x6B01` 各自的确切语义**
   —— 已确定它们是 BLE 命令、已确定调用点，但「哪条命令触发相机开 Wi-Fi、哪条查/设连接模式」
   还没逐条对上（需要把 `e$c.run` + `e$b` 的应答处理再挖一层，或抓真机 BLE 抓包对齐）。
2. **4 个自定义 128 位 UUID 的角色**（服务/写特征/通知特征）——已知存在，未逐个定位。
3. **状态码 34/35 之外的映射**（`C(I)` 里 130/131 的语义）。
4. **配对码（PASSCODE）来源**：是相机屏幕/机身显示、写死在资源里，还是扫码得到？未确认。
5. **`get_connectmode` 的返回码含义**（标准 AP / 相机 AP / 一次性 …）。
6. **UI 文案**：`str.PairingCameraSsid` 等是资源名，真值在 `resources.arsc`（本机无 `aapt`，未解包）。

---

## 7. 怎么得出这些结论（可复现）

工具都在 `official_app/`：

| 工具 | 作用 |
|---|---|
| `oi_index.py` | **结构索引**：把 13 万行 dexdump 切成「类→方法」表（77003 个方法，含整数/字符串/调用），落盘 `oi_index.json`。支持 `--build / --cls / --str / --find 0x69 / --call / --greps / --big` |
| `oi_graph.py` | 列某类全部方法的摘要（整数常量/字符串/调用），`--body 方法名` 打方法体 |
| `oi_mine.py` | 按类看方法、`--grep` 反查字符串 |
| `find_str.py` | 在 dexdump 里按关键词定位代码位置 |
| `dump.py` / `scan.py` | 早期抽取脚本 |

**关键修复**：`dexdump` 的字符串常量用**双引号**（`const-string v1, "xxx" // string@903a`），
旧工具只匹配单引号 → 字符串全丢空。本轮已修 `STR_RE` 并重建索引（现有 28939 条字符串常量可查）。

**反汇编源**：**`official_app/dis.txt`**（130 MB，`dexdump -d` 输出）已从 `%TEMP%\oishare\` 搬进工程；
对应的 dex 是 `official_app/classes.dex`（7.4 MB）。`oi_index.py` / `oi_graph.py` / `oi_mine.py` / `find_str.py`
**都优先读工程内这份**，`%TEMP%` 只作兜底（临时目录会被系统清理）。
需要重新生成时：`dexdump -d classes.dex > dis.txt`。

---

## 8. 对「手册 App（om3-handbook）」的可迁移点

1. **连接链路是可复刻的**：BLE 帧格式（§2.1）+ 4 个自定义 UUID + `WifiNetworkSpecifier` 切换 + `192.168.0.10` CGI，
   路线清晰。**难点不在协议，而在**：BLE 广播里怎么认出"这是相机"、配对码从哪来（§6-4）。
2. **手册 App 现在完全不需要这条链路**——它只是「查配方、看参数、手动拨盘」，没有联网/连相机需求。
   若哪天要加「一键把配方写进相机」，最小闭环 = BLE 连（§2/§3）+ `set_camprop`/`set_takemode`/`switch_cammode`（§5）。
3. **可借鉴的产品设计**（不是代码）：
   - 同一个「连接」动作分「蓝牙连接（遥控）」与「Wi-Fi 连接（传图）」两种模式，按需切换；
   - 相机 AP 会被**记住**，但有「一次性/模式不明不记」的自我保护；
   - 断线有 `startDisconnectMonitor` 监控 + `WifiConnectListener` 失败重试。

---

## 9. 本轮产物

| 文件 | 说明 |
|---|---|
| `SPEC-round58.md` | 本文件（分析报告） |
| `official_app/oi_index.py` + `oi_index.json` | 结构索引工具与产物（22 MB） |
| `official_app/oi_graph.py` | 方法摘要/方法体工具 |
| `official_app/oi_mine.py`、`find_str.py`（已修字符串正则、路径改工程内优先） | 反查工具 |
| `official_app/dis.txt` | 反汇编源，130,221,181 B，md5 `bbb659214b8e0679393a8f0bd59cbb52`（**从 `%TEMP%` 搬入工程**） |
| `official_app/classes.dex` | 对应 dex，7,382,600 B，md5 `ea3e6d3135bffbfb2816e04024ceeea4` |
| `AGENTS.md`（工程根） | 新增：项目指令文件，让新会话自动读 `HANDOVER.md` 并守规矩 |

**没做**：没有改 `app/base.html`、没有重出 APK（本轮是纯分析，手册 App 版本仍是 **v3.15**）。
