# 第 61 轮：官方 App 逆向遗留项收敛（状态位语义 / QR 字段语义 / 相机 DB schema）

> 目的：把 `SPEC-round60.md` §5「仍然未解」里**静态能解的三条**挖掉（真机相关那条仍然做不了）。
> **纯分析，没有动手册 App**：`app/base.html` md5 仍 `1b5254a238a857a63a3c5808d55e3a39`（v3.15，零改动）。

---

## 0. 一句话结论

1. **`M2/b.p(mask)` 的位语义全部对齐**（不再是"未逐位对齐"）：掩码就是**相机状态包 byte[5] 的位号**，
   `1=ASIC电源`、`2=isShareFlag`、`4=isPairingFlag`、`8=isBluetoothFlag`、`16=恒 0（死位）`、`32=isLocationFlag`。
   每个名字都有 `oishare.e.O/R/S/T` 的日志与 prefs 双向证据。
2. **`oishare.f$a` 11 个字段全部定性**：`h`=二维码版本号、`a`=Wi-Fi 安全类型、`g`=Wi-Fi netId、
   `b/f`=SSID/密码、`c`=相机设备名、`d`=连接模式、`e`=`b` 的尾段（无读者）、
   **`i`=BLE 设备名（prefs `str.bleName`）**、**`j`=BLE 配对码（prefs `str.blePass`）**、`k`=二维码原文（无读者）。
3. **勘误第 60 轮两处**：① 二维码**是**携带 BLE 配对码的（`f$a.a()` 强制要求 `i/j` 非空，
   `updatePreferenceBleInfo` 把 `i/j` 写进 `str.bleName`/`str.blePass`）；
   ② `f$a.g` **不是**安全类型，是 **Wi-Fi netId**（`-1` = 未指定）；安全类型只放在 `a`。
   → 第 59 轮"配对码由用户输入"与第 60 轮"二维码不含配对码"**两条都要改**：**两条来源并存**（见 §3）。
4. **`camera_info_table`（SQLite）全列 + 注册 UI 路径已解**（`/camera/camera.db`，23 列，
   升级走 `ALTER TABLE %s ADD %s INTEGER DEFAULT 1`；列表 UI = `settings/camera/CameraInfoListActivity`）。

---

## 1. 本轮范围与「必须显式声明清单」

| 项 | 说明 |
|---|---|
| 输入 | `official_app/dis.txt`、`official_app/classes.dex`、`official_app/oi_index.json` |
| 输出 | 本规格（**不新增脚本、不改任何代码**） |
| 前置条件 | 只要 Python 3 标准库；无需网络/java/aapt；无需真机 |
| 后置条件 | 手册 App 产物零变化（md5 不变、不出 APK）；`official_app/` 只读 |
| 权限 / 幂等 / 事务 / 并发 / 数据迁移 / 性能 / 安全 | **不涉及**（只读分析，不产出可执行代码） |
| 失败回退 | **不涉及**（本轮没有新增/修改任何文件，除本规格与 `HANDOVER.md`/`AGENTS.md` 文档） |

---

## 2. 遗留项收敛

### 2.1 `M2/b.p(mask)` 的位语义【已确证，关闭第 60 轮 §5①】

**数据来源链路**（这是关键：掩码不是"能力枚举"，而是相机侧状态字节的位）：

```
BLE 通知 (N2/a.e0 ← BluetoothDevice + byte[])
  └ N2/a.V(byte[])                      // TLV 拆包：len | type | payload
       ├ type=0xFF → N2/a.Y(payload)    // 8 字节状态包
       └ type=0x07 → N2/a.X(payload)    // hex 值 == 硬编码 md5 → 布尔
  N2/a.Y(8B)：LE16@0 ∈ {0x04D0, 0x09F1}、LE16@2 == 1、byte[4]→M2/a.c、byte[5]→5 个布尔、byte[5]→M2/a.j
  N2/a.f0()  = 由 5 个布尔拼回位掩码（bit0/1/2/3/5，**bit4 从不赋值**）
  M2/b.p(mask) = (N2/a.f0() & mask) != 0
```

| mask | bit | `M2/a` 字段 | 语义 | 证据（`dis.txt`） |
|---|---|---|---|---|
| `1` | 0 | `.d` | **ASIC / 相机电源 ON** | `oishare.e.I()`：取反即日志 `.connectResult Asic OFF 時は何もしない` |
| `2` | 1 | `.e` | **isShareFlag（分享标志）** | `oishare.e.T()` 日志 `.isShareFlag` → 体内 `M2/a.p()` |
| `4` | 2 | `.f` | **isPairingFlag（配对标志）** | `oishare.e.S()` 日志 `.isPairingFlag` → 体内 `M2/a.n()`；`oishare.e.c0` `.sendFireBase Pairing ON` |
| `8` | 3 | `.g` | **isBluetoothFlag（蓝牙连接标志）** | `oishare.e.O()` 日志 `.isBluetoothFlag` → 体内 `M2/a.l()`；`c0` `.sendFireBase Bluetooth ON/OFF`；`e.W()` `.powerOn Buletooth接続モード…` |
| `16` | 4 | —（无字段） | **恒 0（死位）** | `N2/a.Y` 只读 byte[5] 的 0/1/2/3/5 位；`f0()` 从 `shl 3` 直接跳到 `shl 5` |
| `32` | 5 | `.h` | **isLocationFlag（GPS 定位标志）** | `oishare.e.R()` 日志 `.isLocationFlag` → 体内 `M2/a.m()`；`oishare.service.a` `.Location動作中` |

**掩码使用点（全 dex 只有 8 处 `p()` 调用 + 9 处 `e.G(…, mask, …)` 注册）**

| 调用方 | mask | 为什么合理 |
|---|---|---|
| `oishare.e.B(I)` 监听分发 | 1/2/4/8（表驱动） | `B()` = 遍历 `e.f` 监听器表：**当 `(mask & 状态位) == 0` 时才回调**（`v10 = (b&status)==0`），即"该标志还没亮时才通知" |
| `oishare.e.H()` 连接主流程 | 4、8 | 已连上时按 `Pairing/Bluetooth` 标志决定回 `C(4)` 还是 `C(1)` |
| `oishare.e.I()` 连接结果处理 | 1 | ASIC 关 → 直接返回 |
| `oishare.e.W()` 开机 | 8、32 | 只有 `p(8)!=0 且 p(32)==0` 才发 `0x0F01` 开机；否则打 `.powerOn Buletooth接続モード、Locationモード時は電源ONしない` |
| 注册 mask（`e.G` ← 9 个 UI） | Remocon 系 / `track/d$h` / `t2/a$c` = **8**；`BluetoothSettingActivity` / `DeviceWifiActivity` = **4**；`s2/a`、`s2/b.G`、`BlePowOnActivity` = **0** | 遥控要"蓝牙"、装置配对要"配对"、搜索/开机不挑 |

> 验收标准：
> 1. `python official_app/oi_index.py --call 'M2/b.p('` → 恰好 4 个方法（`oishare.e.B/H/I/W`）。
> 2. `rg -n -B4 'M2/b;\.p:\(I\)Z' official_app/dis.txt` 能看到每处紧跟的 `const/4`/`const/16` 即掩码值。
> 3. `sed -n '531719,532038p' official_app/dis.txt | rg 'const-string|M2/a;\.\w:\(\)Z'`
>    → 依次出现 `.isBluetoothFlag→l()`、`.isLocationFlag→m()`、`.isPairingFlag→n()`、`.isShareFlag→p()`。

### 2.2 `oishare.f$a` 的 11 个字段语义与二维码段位序【已确证，关闭第 60 轮 §5②】

**解析器版本规则**（`oishare.f.b(String)` 按前缀 `,` 分段后分发；`oishare.f.a(String)` 做静态置换还原）：

| 前缀 | 解析器 | 段数要求 | 字段取自哪几段 |
|---|---|---|---|
| `OIS1` | `f.c` | 必须 **3** 段 | b=段1, f=段2；`h` 硬编码 `1` |
| `OIS2` | `f.d` | 版本=1 → **4** 段；版本=3 → **6** 段 | h=parseInt(段1), b=段2, f=段3；版本=3 时 i=段4, j=段5 |
| `OIS3` | `f.e` | 版本=1 → **5** 段；版本=3 → **7** 段 | h=parseInt(段1), a=parseInt(段2), b=段3, f=段4；版本=3 时 i=段5, j=段6 |

（`f.d`/`f.e` 开头都 `parseInt(段1)`，异常 → `h=-1` → 返回 null；除 b/f/i/j 外的串都要过 `f.a()` 置换还原）

| 字段 | 类型 | 语义 | 证据 |
|---|---|---|---|
| `b` | String | 相机 AP **SSID 系复合串**（含 `-P-`；按 `-` 拆出 c/d/e） | `J2/e.Z`、`t2/a.C`、`HomeActivity.d6`、`oishare.f.c/d/e`（拆段） |
| `f` | String | **Wi-Fi 密码** | prefs `str.wifi.camera.password`（3 处构造器） |
| `a` | int | **Wi-Fi 安全类型** | prefs `str.wifi.Security.Type`（`J2/e.Z`、`t2/a.C`、`HomeActivity.d6`）；OIS3 亦来自段2 |
| `g` | int | **Wi-Fi netId**（`-1` = 未指定/需重选） | `J2/e.Z`/`t2/a.C` 写 `-1`；`HomeActivity.d6` 另一支写 prefs `num.wifiNetId`，并用 `J2/d.u(netId)` 反查 SSID |
| `c` | String | **相机设备名** | `J2/d.q()` 日志 `WifiSwitcher.getDeviceName` → 返回 `f$a.c` |
| `d` | String | **连接模式**（`private`/`onetime`/`playmodeonly_private`） | `J2/d.L(String)` 日志 `WifiSwitcher.setConnectModeInner mode: ` → `iput f$a.d` |
| `e` | String | `b` 按 `-` 拆出的**最后一段**（与 `d`=倒数第二段配对） | `oishare.f.c/d/e` 的拆段代码；**全 dex 无业务读者**（只有拷贝构造读它） |
| `h` | int | **二维码版本号**（OIS1 固定 1；OIS2/OIS3 取段1） | `f.c` `const/4 v0,#1 → iput h`；`f.d`/`f.e` `parseInt(段1)` |
| `i` | String | **BLE 蓝牙设备名** | `HomeActivity.d6` 0x82~0x88：prefs **`str.bleName`** → `f$a.i`；`DeviceWifiActivity.T2()`/`HomeActivity.m7()` 反向写回 `str.bleName`；`DeviceWifiActivity.t2` 把它当 `e.G(name,…)` 第 1 参 |
| `j` | String | **BLE 配对码（パスコード）** | 同上 0x8a~0x90：prefs **`str.blePass`** → `f$a.j`；`T2()`/`m7()` 反向写回 `str.blePass`；`t2` 把它当 `e.G(…,pass,…)` 第 2 参 |
| `k` | String | **扫到的二维码原文**（`HomeActivity.X` ← savedState `state_qrCodeVal`） | `HomeActivity.d6` 0x3f~0x41；**全 dex 无读者** |

**合法性判据**：`oishare.f$a.a()Z` = `h >= 1 && i != null && j != null`。
→ 也就是**"必须带 BLE 信息（名字+配对码）"才算有效二维码**。

**消费链**：

```
扫到 QR → f.b(String) → f$a
  ├ DeviceWifiActivity$k.j()      读 i → 非空则 d2(...)
  ├ DeviceWifiActivity.T2()/HomeActivity.m7()   // 日志 .updatePreferenceBleInfo BLE情報ありの場合は保存
  │     h>=1 且 a() 为真 → 把 i→prefs str.bleName、j→prefs str.blePass
  └ DeviceWifiActivity.t2()       → e.G(f$a.i, f$a.j, mask=4, listener)  // 用 QR 里的 BLE 名+配对码去连
```

> 验收标准：
> 1. `rg -n 'field@3afd|field@3b03' official_app/dis.txt` → `e`/`k` 只有"解析器写入 + 无业务读"。
> 2. `sed -n '532541,532566p' official_app/dis.txt` → `f$a.a()` 读 `h/i/j` 三者。
> 3. `sed -n '1543400,1543520p' official_app/dis.txt` → `HomeActivity.d6` 里
>    `str.bleName→i`、`str.blePass→j`、`str.wifi.camera.password→f`、`str.wifi.Security.Type→a`、`g=-1`。
> 4. `sed -n '888319,888460p' official_app/dis.txt` → `J2/e.I/Z` 两个构造器：`g` 都是 `const/4 #-1`（不是安全类型）。

### 2.3 `camera_info_table`（SQLite）【静态部分已确证；真机内容仍做不了】

- 库文件：`/camera/camera.db`，表 `camera_info_table`，插入辅助器 `CameraDBAdapter.*`，
  查询排序 `update_date DESC`，升级语句 `ALTER TABLE %s ADD %s INTEGER DEFAULT 1`。
- 列名（23 个，按 `dis.txt` 848xxx~850xxx 去重得到）：

```
camera_name  camera_ssid
ble_name  ble_password  ble_address  show_ble_message
wifi_ssid  wifi_password  wifi_security_type  wifi_bssid  wifi_net_id  wifi_net_mode  wifi_net_name  wifi_manual_connect
support_location  support_gps_link  support_firmup  support_release  support_myset_settings
update_date  std_net_id_bak
```

- 与 `SharedPreferences` 的镜像键（同区域字符串）：`str.bleName` / `str.blePass` / `str.bleAddress` /
  `str.PairingCameraName` / `str.PairingCameraSsid` / `str.wifi.camera.ssid` / `str.wifi.camera.password` /
  `str.wifi.camera.bssid` / `str.wifi.Security.Type` / `num.wifiNetId` / `num.stdNetIdBak` /
  `num.registeredCameraCount` / `is.CameraSupportBleLocation` / `is.CameraSupportGpsLink` /
  `is.CameraSupportFirmup` / `is.CameraSupportRelease` / `is.CameraSupportMysetSettings` /
  `is.DisplayBleRemoconMessage` / `is.wifiManualConnect`。
- **注册/管理 UI 路径**：`settings/camera/CameraInfoListActivity`（已注册相机列表，菜单里用
  `num.registeredCameraCount` 判空/置灰）→ `device/BluetoothSettingActivity`（选相机+输入配对码）
  → `device/DeviceWifiActivity`（切到相机 AP）→ `device/ConnectCompleteActivity`（连接完成）；
  手动补充入口 `device/ManualSettingActivity`。

> 验收标准：`awk 'NR>=847800 && NR<=850100' official_app/dis.txt | rg -o 'const-string v[0-9]+, "([^"]*)"' -r '$1' | sort -u`
> → 输出含 §2.3 的全部列名与 prefs 键。

### 2.4 `get_camprop` / `set_camprop` 的范围订正【**改判：不是"量最大"，而且和我们的"写配方"不是一条路**】

> 起因：需求方问「这个我们 app 不是已经实现了『把配方写进相机』吗，有啥区别」。
> 复跑 `rg -o '[a-z_0-9]+\.cgi' app/base.html | sort -u` 后确认：**我们 App 走的是另一条通道**。

**① 我们 App 的「写配方进相机」= MySet 整包通道【已实现，且真机可用】**

`app/base.html` 里已实现的 `.cgi`（15 个），全是 MySet 系：

```
switch_cammode.cgi              get_caminfo.cgi            exec_reboot.cgi
request_getmysetdata.cgi        get_partialmysetdata.cgi   getmysetdata.cgi
get_mysetdata.cgi               get_mysetname.cgi          get_mysetdatasize.cgi
get_mysetdatamodekind.cgi       get_mysetbackupstate.cgi   get_mysetrestorestate.cgi
set_mysetdatasize.cgi           send_partialmysetdata.cgi  request_restoremysetdata.cgi
```

流程（`base.html` §"写进相机"，`writeRecipeCore` / `om3WriteViaSlot`）：进维护模式
（`switch_cammode.cgi?mode=maintenance`）→ `request_getmysetdata.cgi` → `get_partialmysetdata.cgi`
（分块读整份 MySet）→ 本地按配方补丁改 → `set_mysetdatasize.cgi` + `send_partialmysetdata.cgi`×N
→ `request_restoremysetdata.cgi?action=restore` → 轮询 `get_mysetrestorestate.cgi` →
`exec_reboot.cgi`（**相机关机重启后才应用**，所以真正确认要用 ☰ →「校验上次写入」）。
**传的是一整份设置（blob），不是单参数。**

✅ **这条路是通的**（需求方 2026-09-28 确认："目前 app 写配方是可以的，完全没问题"）。
真机日志也早就支持这一点：`SPEC-round28.md` §187 与 `HANDOVER.md` 第 29 轮都写明
**520 只出现在 `get_mysetname.cgi?mode=current` 这一个查询上，标注是"固件不支持这个查询，与写入无关"**；
同一次日志里 `get_mysetname.cgi?mode=myset1` 正常返回 `<mysetname>port A</mysetname>`。
（第 28 轮当年"写不进去"的**真因**已在第 29 轮查明并修好：**是我们自己请求顺序错了**，不是相机不开放。）

⚠️ **但页面 1681 行还留着一句过时且说反了的警告**：
> ⚠ 实测：本机 OM-3 的 my-set 接口**全部**返回 520/1001（相机不开放这条通道），「读取并备份」在本机型上不会成功。

这句是第 28 轮那次误判的遗留物：① "全部"是错的（只有 `mode=current` 一个查询）；
② 写入功能第 29 轮就已修好、且真机验证可用 —— 而写入**必须先读整份 my-set**（`readMySet`），
所以"读取不成功"也不可能成立。**这是本轮发现的真问题（页面文案 bug），待需求方决定是否改页面。**

**② 官方 App 的 `get_camprop` / `set_camprop` = 单参数实时改参通道（另一条路，我们没用到）**

- 形式（都是 **HTTP CGI**，同一个 `192.168.0.10`，**与 BLE 无关**）：
  `get_camprop.cgi?com=get|check|desc&propname=X`、`set_camprop.cgi?com=set&propname=X&value=Y`
- 用它的地方**只有遥控**：`oishare/remocon/RemoconV20Activity` / `RemoconV21Activity`（取景时实时改参数）。
- **规模比预估的小得多**：全 dex 只出现 **14 个 `propname`**：
  `takemode`(4) / `exposemovie`(2) / `wbvalue` / `isospeedvalue` / `shutspeedvalue` / `expcomp` /
  `focalvalue` / `qualitymovie` / `drivemode` / `colortone` / `colorphase` / `supermacrosub` /
  `touchactiveframe` / `desclist`。
- **不需要"静态字段表"**：`get_camprop.cgi?com=desc&propname=desclist` 可以**在线问相机要描述表**
  （官方 App 自己就是这么做的：`RemoconV21Activity.Y9`）。

**③ 结论：这条待办应当作废**

| 原写法（第 61 轮初稿 / 第 58 轮 §5） | 订正后 |
|---|---|
| 「`get_camprop` 字段表**量最大**」 | ❌ 判错了。量最大的是**官方 App 68 个 .cgi 的整体盘**（第 58 轮数字没错），camprop 只占 2 个端点 + 14 个 propname，且可在线取描述表 |
| 「做『把配方写进相机』时才需要」 | ❌ 不准确。写配方我们**已经用 MySet 通道实现并且能用**；camprop 是**另一条**通道（遥控实时改参） |
| 「OM-3 的 MySet 520/1001 → 需找替代路」 | ❌ **前提就是错的**（误读了页面那句过时警告）。**没有"替代"的必要**：写配方已经能用 |
| 第 58 轮 §5「最小闭环 = BLE 帧协议 + `set_camprop`/`set_takemode`/`switch_cammode`」 | ⚠️ **仍是混搭**：这三个都是 **HTTP CGI**，与 BLE 无关。BLE 只负责"唤醒相机开 Wi-Fi"（`base.html` 1593 行同款说法） |
| — | ✅ camprop 唯一可能的**新增**用途是"**不进维护模式、不重启**就能改单项参数"（如遥控那 14 项），要不要做是**产品选择题**，不是技术障碍 |

---

## 3. 勘误汇总（对第 58/59/60 轮 **以及本文件初稿**）

| 位置 | 原文 | 本文件实测 | 处理 |
|---|---|---|---|
| `SPEC-round60.md` §0.3 / §2.4.5 | "二维码里**不**含蓝牙配对码；`f$a` 的任何字段都没有被写成 prefs `str.blePass`" | **反了**。`j` 就是配对码，`T2()`/`m7()` 明确把 `j` 写进 `str.blePass`，`f$a.a()` 还强制 `j` 非空 | **改规格**：二维码**携带** BLE 名字+配对码 |
| `SPEC-round60.md` §2.4 表（`a`/`g` 行） | "`str.wifi.Security.Type` 同时写进 `a` 和 `g`" | `a`=安全类型；`g`=**netId**，构造器里恒为 `-1` | **改规格** |
| `SPEC-round59.md` §3 / `SPEC-round60.md` §2.4.5（与上条互相印证的结论） | "配对码来源 = 用户输入（Bluetooth パスコード入力 界面）" | 界面输入**仍然存在**（`str.blePass` 也可能由用户敲），但**不是唯一来源** | **改规格**：两条来源并存，QR 优先（`DeviceWifiActivity` 只在 `f$a.a()` 为真时才用 QR 的 `j`） |
| `SPEC-round58.md` §5「最小闭环 = BLE 帧协议 + `set_camprop`/`set_takemode`/`switch_cammode`」 | 把 CGI 和 BLE 并列成一条闭环 | 这三个**都是 HTTP CGI**（`192.168.0.10`），与 BLE 无关；BLE 只负责唤醒相机开 Wi-Fi | **改规格**（见 §2.4③） |
| 本文件 §5 初稿「`get_camprop` 字段表**量最大**，做『把配方写进相机』时才需要」 | 判断错 | camprop 只有 **2 个端点 + 14 个 propname**，还能 `desc/desclist` 在线取描述表 | **改规格**（见 §2.4，§5 已改写） |
| 本文件 §2.4 初稿「OM-3 的 my-set 接口**全部** 520/1001 → 写配方本机不通」 | **判断错，且把需求方带偏了** | 真因是**误读了 `base.html:1681` 一句过时的硬编码警告**。真机事实：写配方**可用**（需求方确认 + `SPEC-round28.md` §187 与第 29 轮记录：520 只在 `get_mysetname?mode=current` 这一个查询上，"与写入无关"） | **改规格**（见 §2.4①）+ **把 `base.html:1681` 那句过时警告登记为待修页面文案**（见 §5） |

> 与第 60 轮不冲突的部分：BLE 那侧的"オペコード `0x0C02` 用 `str.blePass` 鉴权"结论不变 ——
> 变的只是"这个值最初从哪来"。

---

## 4. 设计与实现的差异分析（本轮）

| 规格（第 60 轮 §5） | 本轮情况 | 处理 |
|---|---|---|
| ① `M2/b.p(mask)` 各位语义 | **已逐位对齐**（含 1 个死位 bit4） | **改规格**（关闭） |
| ② `f$a` 的 `e/h/j/k` + `i`↔`d2()` | **11 个字段全定性**；`e`/`k` 证实为"只写不读" | **改规格**（关闭） |
| ④ `camera_info_table` 内容 / 注册 UI 路径 | 静态侧（schema/列/镜像键/UI 路径）已解；**真机实际行内容**无设备 | **改规格**（部分关闭，剩余标为环境限制） |
| ③ `get_camprop/set_camprop` "XML 字段表" | **范围改判**：不是"量最大"，也不是写配方的路；写配方（MySet）**本来就能用** | **改规格 → 待办作废**（见 §2.4） |
| ⑤ 真机 BLE 抓包 | 做不了（无设备） | 明确标注为环境限制，不作为待办 |

**本轮第二次修订（需求方指出"写配方没问题"之后）**：
`base.html:1681` 那句过时警告是**真问题**（页面在错误地告诉用户"这条通道不通"），
已登记为待修项（见 §5）。**本轮不动页面**（改了就要重出 APK，由需求方决定）。

新增代码：**没有**。本轮零代码改动、零新脚本 → 不存在 TODO / 假分支。

---

## 5. 仍然未解 / 待修

1. **【待修页面文案｜本轮发现的真 bug】`app/base.html:1681` 那句警告是过时且说反的**
   > ⚠ 实测：本机 OM-3 的 my-set 接口**全部**返回 520/1001（相机不开放这条通道），「读取并备份」在本机型上不会成功。

   事实：① "全部"不成立（只有 `get_mysetname.cgi?mode=current` 返回 520，`SPEC-round28.md` §187 原文就写着"与写入无关"）；
   ② 写入功能第 29 轮修好、真机验证可用（需求方 2026-09-28 确认），而写入必须先读整份 my-set。
   ⇒ 建议改成如实说明（例：*"读取并备份"用 my-set 通道；本机只有 `get_mysetname?mode=current` 这一个查询不支持，不影响读写*）。
   **改动很小（纯文案）**，但要动 `app/base.html` → 需走页面流程并重出 APK。
   **需求方 2026-09-28 决定："先不改，记着"** —— 本轮不动页面，**记在这里，等下一轮/需求方点头再做**。
2. **静态侧已无剩项**（camprop 的端点 / 14 个 propname / 用法已全部查清）。
3. **[产品选择题，非障碍]** 要不要用 camprop 做「**不进维护模式、不重启**就改单项参数」？——
   14 个 propname 基本对应取景时常用的那些（`takemode`/`wbvalue`/`isospeedvalue`/`shutspeedvalue`/`expcomp`/`colortone`/`colorphase`…）。
   注意：这**不能**替代写配方（配方的色环 12 轴、色调曲线、Color Profile 槽位都在 my-set 里）。
4. `camera_info_table` 在**真机**上的实际行内容（无设备，做不了）；`support_*` 各标志的取回时机未逐条对齐。
5. 真机 BLE 抓包交叉验证（无设备，做不了）。
6. `N2/a.X` 里那个硬编码 md5 `4f3ec7b83b98cab8714b584ef905c5ad` 对应哪种 0x07 类型通知（只知它是"特定内容校验"）。

---

## 6. 本轮产物

| 文件 | 说明 |
|---|---|
| `SPEC-round61.md` | 本文件 |
| `HANDOVER.md` | 顶部新增第 61 轮段落（第 60 轮降为「上一轮」）；补「MySet vs camprop」订正 |
| `AGENTS.md` | 基线轮次改 61；§5 结论文件顺序 + 勘误提示 + MySet/camprop 差别 |
| `SPEC-round60.md` | 顶部加**勘误横幅**（指向本文件 §3），避免后续会话沿用错误结论 |

**没做**：没有改 `app/base.html`（md5 仍 `1b5254a238a857a63a3c5808d55e3a39`）、没有重出 APK、
没有新增 `official_app/` 脚本。

---

## 7. 验收（可逐条复跑）

```bash
cd /d/workspace/om3-handbook
md5sum app/base.html                                   # 期望 1b5254a238a857a63a3c5808d55e3a39

# §2.1 位语义
python official_app/oi_index.py --call 'M2/b.p('       # 期望 4 个方法：oishare.e.B/H/I/W
sed -n '531719,532038p' official_app/dis.txt | rg 'const-string|M2/a;\.\w:\(\)Z'
#   期望：.isBluetoothFlag→l()  .isLocationFlag→m()  .isPairingFlag→n()  .isShareFlag→p()
sed -n '68651,68691p' official_app/dis.txt | rg 'shl-int'   # 期望 #1 #2 #3 #5（无 #4）

# §2.2 f$a 字段
sed -n '532541,532566p' official_app/dis.txt           # f$a.a() = h>=1 && i!=null && j!=null
sed -n '1543400,1543520p' official_app/dis.txt | rg 'const-string|field@3b0'   # str.bleName→i, str.blePass→j
rg -n 'field@3afd|field@3b03' official_app/dis.txt     # e/k 只写不读

# §2.3 DB
awk 'NR>=847800 && NR<=850100' official_app/dis.txt | rg -o 'const-string v[0-9]+, "([^"]*)"' -r '$1' | sort -u

# §2.4 MySet 通道 vs camprop 通道
rg -o '[a-z_0-9]+\.cgi' app/base.html | sort -u          # 期望 15 个（MySet 系 + get_caminfo + exec_reboot）
rg -o '[a-z_0-9]+\.cgi' official_app/dis.txt | sort -u | wc -l   # 期望 68（第 58 轮数字复核）
rg -o 'propname=[a-z_]+' official_app/dis.txt | sed 's/propname=//' | sort -u   # 期望 14 个 propname
python official_app/oi_index.py --greps 'camprop'        # 期望只有 remocon/RemoconV20/V21Activity（+ c2/F、c2/k）
rg -c 'camprop' app/base.html                            # 期望 0（确认我们没走这条路）

# §2.4① 页面那句过时警告，与第 28 轮记录对照
rg -n -o '.{0,24}my-set 接口.{0,60}' app/base.html        # base.html:1681 过时警告原文（"全部返回 520/1001"）
rg -n 'mysetname.*520|520.*mysetname' SPEC-round28.md HANDOVER.md
#   期望：SPEC-round28.md:187「get_mysetname?mode=current → HTTP 520 …与写入无关」
#         HANDOVER「本轮真机日志里其它几条（都属正常，别再当 bug）」那一段
rg -n 'readMySet\(|writeRecipeCore|request_restoremysetdata' app/base.html | head
#   期望：写入流程里先 readMySet 再 set_mysetsize/send/restore → 证明"读取不通"不可能成立
```

**验收结果（2026-09-28 实跑）**

| 项 | 结果 |
|---|---|
| `md5sum app/base.html` | `1b5254a238a857a63a3c5808d55e3a39` ✅ 与 v3.15 一致（本轮零改动） |
| `--call 'M2/b.p('` | 4 个方法（`oishare.e.B/H/I/W`）✅ |
| 位名对应 | `.isBluetoothFlag→l()`（bit3）、`.isLocationFlag→m()`（bit5）、`.isPairingFlag→n()`（bit2）、`.isShareFlag→p()`（bit1）✅ |
| `f0()` 位移 | `#1 #2 #3 #5`，无 `#4` ✅（bit4 死位） |
| `f$a.a()` | 读 `h`、`i`、`j` 三者，判据 `h>=1 && i!=null && j!=null` ✅ |
| `HomeActivity.d6` | `str.bleName→i`、`str.blePass→j` 两条 `iput` 均复现 ✅ |
| DB 列名 | 23 列 + 19 个 prefs 镜像键，去重输出稳定 ✅ |
| 我们 App 的 `.cgi` | **15 个**（MySet 系 + `get_caminfo`/`exec_reboot`），**`camprop` 0 次命中** ✅ |
| 官方 App 的 `.cgi` / propname | **68 个** `.cgi`（复核第 58 轮数字 ✅）、**14 个** propname ✅ |
| camprop 的使用者 | 只在 `remocon/RemoconV20Activity`、`RemoconV21Activity`（+ 工具类 `c2/F`、`c2/k` 的字面量）✅ |
| MySet 通道（写配方）状态 | **可用**（需求方 2026-09-28 确认）；`SPEC-round28.md` §187 原文：520 只出现在 `get_mysetname?mode=current`，"**与写入无关**" ✅ |
| `base.html:1681` 警告 | ❌ **过时且说反**（"全部 520/1001"）→ 已登记为待修文案（§5①），**本轮未改页面** |

---

## 8. 官方 App 的剩余覆盖面（回答"还差啥"）—— 68 个 `.cgi` 里我们只用 15 个

> ⚠️ **勘误（第 65 轮，2026-09-28）**：本节下面那两个数字**都不准** ——
> ① 我们真正在用的**官方** `.cgi` 是 **13 个**（下面列的 15 个里，`getmysetdata` / `get_mysetdata`
> 是**我们页面自己的名字**，`dis.txt` 里根本没有这两个 `.cgi`）；
> ② 所以"没碰过"是 **68 − 13 = 55**，不是 53。
> **逐条参数表见 `SPEC-round65.md`**（含 `set_camprop` 的 propname 全表、纯 HTTP 快门链路等）。
> 本节其余结论（"连接/配对/写配方这条线已挖完"）不受影响。

`rg -o '[a-z_0-9]+\.cgi' official_app/dis.txt | sort -u` → **68 个**；逐个与 `app/base.html` 对照：
**★ = 我们已在用（15 个）**，其余 **53 个没碰过**。（**数字订正见上面的勘误**）

| 分类 | 官方 CGI | 我们 |
|---|---|---|
| **我家设置（MySet）** | `switch_cammode`★ `request_getmysetdata`★ `get_partialmysetdata`★ `send_partialmysetdata`★ `set_mysetdatasize`★ `request_restoremysetdata`★ `get_mysetbackupstate`★ `get_mysetrestorestate`★ `get_mysetdatasize`★ `get_mysetdatamodekind`★ `get_mysetname`★ (+ 我们的 `getmysetdata`/`get_mysetdata`) | ✅ 用全了 |
| **杂项** | `get_caminfo`★ `exec_reboot`★ | ✅ |
| **看图 / 传图**（17） | `get_imglist` `get_rsvimglist` `get_thumbnail` `get_screennail` `get_resizeimg` `get_resizeimg_witherr` `get_exif` `get_dcffilenum` `get_unusedcapacity` `get_playtargetslot` `set_playtargetslot` `get_movfileinfo` `check_mountmedia` `exec_erase` `cancel_trimresize` `exec_movietrimresize` `get_trimresizeprocstatus` | ❌ 全未分析 |
| **拍照 / 录像**（5） | `exec_shutter` `exec_takemisc` `exec_takemotion` `set_takemode` `exec_pwoff` | ❌ |
| **实时取景（遥控）**（7） | `ready_moviestream` `start_moviestream` `start_moviestreamts` `stop_moviestream` `exit_moviestream` `get_moviestreaminfo` + `get_camprop`/`set_camprop`（见 §2.4②） | ❌ |
| **GPS / AGPS / 社交投稿**（10） | `check_gpsrecording` `get_agpsinfo` `send_agpsassistdata` `update_agpsassistdata` `get_gpsdivunit` `get_gpsloglist` `req_attachexifgps` `req_storegpsinfo` `check_snsrecording` `get_snsloglist` | ❌ |
| **固件升级**（7） | `fwup_check` `fwup_getfirmstatus` `fwup_getversions` `fwup_sendinfo` `fwup_sendsplit` `fwup_update` `fwup_updatemode` | ❌ |
| **相机日志**（4） | `get_cameraloginfo` `get_partialcameralogdata` `clear_cameralogdata` `clear_resvflg` | ❌ |
| **连接/时间**（4） | `get_commandlist` `get_connectmode` `set_timeout` `set_utctimediff` | ❌（`get_connectmode` 第 59 轮解过返回值） |

**结论**：

1. **对「连接手机 + 配对 + 写配方」这条线，已经挖完了** —— BLE 全链路 + 帧/opcode/结果码/UUID + 配对码两条来源 +
   状态位语义 + MySet 读写 + camprop + DB schema，复刻所需的信息齐了。
2. **剩下 53 个 CGI 只在做新功能时才要**：看图传图、遥控取景、固件升级、GPS。
   这就是"还差啥"的全部 —— 差的是**覆盖面**，不是已挖部分的深度。
3. **静态还能顺手做、性价比由高到低**：
   ① 那 53 个 CGI 的**参数表**逐个读（要做哪个功能就读哪个，不必一次全做）；
   ② `N2/a.X`（BLE 通知 type=0x07）到底在查什么内容 —— 只能查到"hex 等于某定值"，看调用者能补一半；
   ③ `M2/b` 传输层剩余细节（发送队列/重发/超时、`M2/b.l(String,boolean)I`）；
   ④ `arsc.py` 里几个资源真值（`str.PairingCameraSsid`/`bleName` 显示成什么）—— 几分钟，价值有限。
4. **必须真机**（本机做不了）：真机 BLE 抓包、真机 `camera_info_table` 内容、相机对 `get_camprop` 的响应。
