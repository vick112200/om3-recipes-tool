# 第 59 轮：官方 App（OI.Share）连接逻辑——遗留项补齐 + 第 58 轮勘误

> 目的：把第 58 轮 `SPEC-round58.md` §6「未解 / 待确认」清单**逐条收敛**，并对第 58 轮的
> 协议描述做**勘误**（帧校验和、UUID 角色、opcode 语义）。
> **本轮纯分析，没有改手册 App**：`app/base.html` md5 仍是 `1b5254a238a857a63a3c5808d55e3a39`（v3.15）。
> 素材：`om share.apk`（`official_app/dis.txt` 130 MB + `official_app/classes.dex` 7.4 MB）。
> 方法：**读反汇编（不是猜）** + 直接读 dex 字节解 packed-switch 表 + 纯 Python 解 `resources.arsc`。

---

## 0. 一句话结论（第 59 轮新增）

第 58 轮的「四段式」主干**成立**，本轮把两侧的空白补上：

```
① BLE 广播扫描          —— 已确证（M2/b.N；e$a.run）
② GATT 连接 + 3 条命令  —— 已确证，且**补全了通道表**：
     服务 ADC505F9-…；特征 82F949B4=写(App→相机)、B7A8015C=通知(状态/应答)、05A02050=通知(数据帧)
     命令 opcode 逐个对齐了语义（0x040F=快门、0x0410=录像、0x6A01=GPS 附加、0x6B01=遥控数据、
     0x1D01=遥控模式、0x0C02=配对码、0x0F01=开机）；0x6801-03 / 0x6901-03 **定义了但没有任何调用点**
③ 相机开 Wi-Fi AP       —— App 只用 get_connectmode.cgi(HTTP) 读/设模式，模式值是**字符串**
     `private` / `onetime` / `playmodeonly_private`（不是数字码）
④ 192.168.0.10 + 68 个 .cgi —— 第 58 轮已确证，未变
```

**配对码（PASSCODE）不是写死在 APK 里**：由用户在「输入 Bluetooth 配对码」界面输入
（提示文案 `IDS_ENTER_THE_BLE_PATHKEY` = "Enter Bluetooth Passcode of %1$s."，输错 → 结果码 34）。

---

## 1. 本轮范围与「必须显式声明清单」

| 项 | 说明 |
|---|---|
| 输入 | `official_app/dis.txt`（dexdump 反汇编）、`official_app/classes.dex`、`om share.apk`（含 `resources.arsc`） |
| 输出 | 本规格、新工具 `official_app/arsc.py`、对 §6 六条遗留项的**结论 + 可复现验证命令** |
| 前置条件 | 无需网络、无需 java/aapt（本机都没有）；只需 Python 3 标准库 |
| 后置条件 | 手册 App 产物**零变化**（`app/base.html` md5 不变、不出 APK） |
| 数据迁移 / 权限 / 幂等 / 事务 / 并发 | **不涉及**（本轮不写业务代码，只加一个只读分析脚本） |
| 性能 | **不涉及**（`arsc.py` 全量解析 6 MB 资源约 1 秒；`--name/--value` 为全表过滤，可接受） |
| 安全 / 敏感信息 | **不涉及**（只解构 APK 元数据；不生成、不外传任何凭据） |
| 失败回退 | **不涉及**（不修改任何既有文件；`arsc.py` 是新增文件，删掉即回退） |

---

## 2. 遗留项逐条收敛（每项含验收标准）

### 2.1 §6-1 `0x68xx / 0x69xx / 0x6A01 / 0x6B01` 的确切语义

**结论【已确证】**：命令分发的**唯一入口**是 `M2/b$b.a()`（`Callable`），
它按 opcode 调用 12 个发送方法。逐条读出如下（`packed-switch` 的键值直接从 dex 字节解出）：

| opcode | 分发到的发送方法 | 谁发起（真正的语义） | 语义 | 证据 |
|---|---|---|---|---|
| `0x040F` | —（不经 dispatcher） | `M2/b.A(II)I` | **静止画快门释放**（`レリーズコマンド`） | `A` 的日志 `レリーズコマンド発行：` |
| `0x0410` | — | `M2/b.w(II)I` | **录像按钮**（`動画ボタンコマンド`） | `w` 的日志 |
| `0x0C02` | `M2/b.i` | `M2/b.j(String)` | **配对码鉴权**（payload = 配对码 UTF-8） | `j` 的日志 `パスコード認証開始` |
| `0x0F01` | `M2/b.x` | `M2/b.y(I)`（超时 20000ms） | **相机开机**（`電源ON`） | `y` 的日志 |
| `0x1D01` | `M2/b.L` | `M2/b.M(II)` | **遥控模式**（`リモコンモード`），不是心跳 | `M` 的日志；字段名/注释亦相关 |
| `0x6A01` | `M2/b.E`（1 字节 0/1） | `M2/b.F(II)` | **GPS 附加**（`GPS付与コマンド`） | `F` 的日志 |
| `0x6B01` | `M2/b.G`（字节流） | `M2/b.J([BI)` | **遥控数据命令**（`RMC-データコマンド`） | `J`/`G` 的日志 |
| `0x6801` | `M2/b.D`（低字节 1） | **无调用点** | 预留/死代码 | 见下 |
| `0x6802` | `M2/b.C`（低字节 2） | **无调用点** | 预留/死代码 | 见下 |
| `0x6803` | `M2/b.B`（低字节 3） | **无调用点** | 预留/死代码 | 见下 |
| `0x6901` | `M2/b.K`（低字节 1） | **无调用点** | 预留/死代码 | 见下 |
| `0x6902` | `M2/b.I`（低字节 2） | **无调用点** | 预留/死代码 | 见下 |
| `0x6903` | `M2/b.H`（低字节 3） | **无调用点** | 预留/死代码 | 见下 |

> 注：`B/C/D` 与 `H/I/K` 的载荷都是**字节数组**，对应 `M2/b$b.<init>(M2/b;I[BI)V`；
> 发送时 `u(0x68, 1|2|3, payload)` / `u(0x69, 1|2|3, payload)`（第 2 个参数即低字节，见 §3 帧格式）。

**「无调用点」是穷举出来的**：构造 `<opcode, 载荷, 超时>` 的类只有 `M2/b$b`，
全 dex 里 `M2/b$b.<init>` 只有 7 个调用点，opcode 分别是
`0x040F / 0x0410 / 0x0C02 / 0x0F01 / 0x1D01 / 0x6A01 / 0x6B01` ——
**0x68xx / 0x69xx 一个都没有**；`M2/b.B/C/D/H/I/K` 也**只被 dispatcher 调用**（静态调用图里入度为 1）。

> 验收标准：
> 1. `python official_app/oi_index.py --call 'M2/b$b.<init>'` 输出 **7 个方法**，其中 ints 含 `0x40f/0x410/0xc02/0xf01/0x1d01/0x6a01/0x6b01`，**不含** `0x68xx/0x69xx`。
> 2. `python official_app/oi_index.py --call 'LM2/b.B('` 等 6 条：各自只有 **1** 个调用者（`M2/b$b.a`）。
> 3. 用 §5 的 packed-switch 解码片段可复现「0x6801→D、0x6802→C、0x6803→B、0x6901→K、0x6902→I、0x6903→H」。

### 2.2 §6-2 4 个自定义 128 位 UUID 的角色

**结论【已确证】**（`N2/a` = BLE 传输层）：

| UUID | 角色 | 证据 |
|---|---|---|
| `ADC505F9-4E58-4B71-B8CA-983BB8C73E4F` | **服务**（Service） | `N2/a.u0()`：`gatt.getService(ADC505F9)` |
| `82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68` | **写特征**（App→相机） | `N2/a.A()` 存入字段 `m`；`N2/a.s0()` 用 `m` 做 `setValue()+writeCharacteristic()` |
| `B7A8015C-CB94-4EFA-BDA2-B7921FA9951F` | **通知特征②**（状态/应答，走 `N2/a.n0()`） | `N2/a.C()` 存入字段 `n`；`onCharacteristicChanged` 命中 `n` → `n0()` |
| `05A02050-0860-4919-8ADD-9801FBA8B6ED` | **通知特征③**（数据帧，交给协议层） | `N2/a.E()` 存入字段 `o`；`onCharacteristicChanged` 命中 `o` → `N2/a$f.t([B)`（→ `M2/b`） |
| `00002902-0000-1000-8000-00805f9b34fb` | 标准 CCC 描述符 | `u0()` 里 `getDescriptor(2902)` + `writeDescriptor` |

**连接后的开通知顺序**（`N2/a$c.onServicesDiscovered` → `onDescriptorWrite`）：
`82F949B4` → `B7A8015C` → `05A02050`，三个依次开通知；每次 `writeDescriptor` 成功后 post 下一个，
全部完成后 `N2/a.F()` → `h0()`（枚举该服务下全部特征 UUID，`sendEmptyMessage(5)` 通知上层）。
即 `h0()` 就是「特性清单」的产出点（**兼容不同机型/固件**：App 不假设只有 3 个特征）。

> 验收标准：`python official_app/oi_graph.py 'N2/a' --cls` 能列出 `N2/a;A/C/E/s0/u0/h0`；
> 在 `dis.txt` 里 `rg -n 'ADC505F9|82F949B4|B7A8015C|05A02050'` 命中的行落在上述方法体内（行号见 §5 附录）。

### 2.3 §6-3 结果码表（`OlyBleConnectListener`）

**结论【已确证】**：`s2/b$g.H(I)V`（行 `L1269701-1269930`）是**全量分发器**，
用两个 `packed-switch` 处理，**码值 = switch 键值**（直接读 dex 字节解出）：

| 码 | 名称 | 备注 |
|---|---|---|
| 0 | `BLE_RESULT_SUCCESS` | |
| 1 | `BLE_RESULT_ALREADY_CONNECTED` | |
| 2 | `BLE_RESULT_NOT_FOUND` | 与码 4 共用同一分支 |
| 3 | `BLE_RESULT_DISCONNECTED` | |
| 4 | （同上，复用 `NOT_FOUND` 分支） | |
| 5 | `BLE_RESULT_SEARCHING` | |
| 6 | `BLE_RESULT_CONNECTING` | `e$c.run` 成功时置 6、`Handler.sendEmptyMessageDelayed(10,…)` |
| 33 | `BLE_RESULT_BLUETOOTH_OFFON` | |
| 34 | `BLE_RESULT_PASSCODE_ERROR` | `e$d.run`（鉴权）失败置 34 |
| 35 | `BLE_RESULT_POWON_ERROR` | `e$e.run`（开机）失败置 35 |
| 36 | `BLE_RESULT_FINALIZE` | |
| — | `BLE_RESULT_GPS_OFF` | 有日志分支，但**不在**这两个 switch 里（走默认/else 路径） |
| — | `BLE_RESULT_ABNORMAL_CONDITION` | **只在 BLE 检测监听**里（`s2/b$d.O(ILjava/util/ArrayList;)V`）出现 |

> 第 58 轮把 34/35 写成「推测」，本轮**升为已确证**（switch 键值 34/35 直接解出）。
> 第 58 轮写的 `5=搜索中 / 6=连接中` **正确**；但「0=默认失败、1=已连接已连」中
> **0 应为 SUCCESS**（不是默认失败）。
>
> 另一处（`track/d$i.H(I)V`，界面通知用）只处理 `0/1/5/6` 四个码，其余走默认分支。
>
> 验收标准：`s2/b$g.H` 的 `packed-switch v6, 000001d8`（base=0x09）与 `000001ea`（base=0x0c）
> 的 payload 分别位于 dex 文件偏移 `0x50a358`（size=7，first_key=0）与 `0x50a37c`（size=4，first_key=33）；
> 用 §5 的片段可复现全部映射。

### 2.4 §6-4 配对码（PASSCODE）来源

**结论【已确证】：不是写死的，是用户输入的。** 完整链路：

```
用户在「Bluetooth パスコード入力」界面输入
  ↓ 存进 SQLite（表 camera_info_table，列 ble_password）
  ↓ 复制到 SharedPreferences 键 str.blePass（u2/a.n(c2/A) 写；t2/o.q0(String) 反向同步）
  ↓ s2/a.o() 读出：c2/A.i("str.bleName") / c2/A.i("str.blePass")
  ↓ oishare.e.G(ssid=?, passcode, mode, listener)   ← 配对码落在 oishare.e.d 字段
  ↓ e$d.run → M2/b.j(passcode) → 0x0C02 帧（payload = 配对码 UTF-8）
  ↓ ret != 0 → 结果码 34（BLE_RESULT_PASSCODE_ERROR）
```

证据：
- 提示文案（`resources.arsc`，本轮新工具解出）：`IDS_ENTER_THE_BLE_PATHKEY` =
  **"Enter Bluetooth Passcode of %1$s."**（多语言 22 条，ja = "Bluetooth Name \"%1$s\" のパスコードを入力してください。"）；
  失败文案 `IDS_BLE_PATHKEY_NOT_CORRECT` = "Passcode is incorrect."（ja = "パスコードが一致しません。"）→ 对应 34。
- `oishare.e.<init>` 把 `e.d` 置 null，**唯一写入点**是 `e.G(String,String,I,e$i)V`（日志 `.connect`），
  即配对码只能从外部传进来。
- `c2/A.<clinit>` 的默认值表里**只有 `settings.*`，没有 `str.*`** → `str.blePass` 没有内置默认值。
- 全 APK 只有 `classes.dex` 含 `str.blePass`（`resources.arsc` 里只有控件 id `textView_blePassCode`）；
  资产目录只有示例图，无配置/数据库文件 → 也没有「打包好的相机表」。

> 结论的实用含义：想复刻「连相机」，**必须先有配对码**（相机机身/说明书/二维码给出），
> 协议本身不是障碍。§6 第 4 条就此关闭。
>
> 验收标准：
> 1. `python official_app/arsc.py --name IDS_ENTER_THE_BLE_PATHKEY` → 22 条，default 值如上。
> 2. `python official_app/oi_index.py --call 'oishare/e.G('` → 9 个调用点（各 Activity 的配对流程）。
> 3. 全 dex 里 `iput-object … oishare/e;.d:Ljava/lang/String;` 只有 2 处：`<init>`（置 null）与 `G`（写入）。

### 2.5 §6-5 `get_connectmode` 的返回码含义

**结论【已确证】：不是数字码，是 XML 字符串。** 响应体形如 `<connectmode>…</connectmode>`，
解析点在 `J2/a$s.c`（含常量 `<connectmode>`）与 `t2/a$h.c`；取值判断在 `J2/d`：

| 方法 | 判定 | 含义 |
|---|---|---|
| `J2/d.B()` | `wifiNetMode.equals("onetime")` | **一次性 AP**（用完不记） |
| `J2/d.D()` | `wifiNetMode.equals("private") \|\| equals("playmodeonly_private")` | **私有 AP**（正常直连） |

另有写侧接口：`J2/a.w0()`（`.setConnectMode connectmode=`）以 POST 方式发
`<connectmode>private</connectmode>`（`RemoconV20Activity$l.c`、`RemoconV21Activity$n.c` 也用同一常量），
`J2/d.L(String)` 是「设置连接模式」的内层实现（日志 `接続モード設定をしました。 mode: `），
并把模式写进 SharedPreferences 键 `wifiNetMode`。

> 与第 58 轮的差异：第 58 轮把「模式号」当成数字（`setConnectModeInner mode: `）；实际是**字符串枚举**。
>
> 验收标准：`J2/d.B` / `J2/d.D` 体内可读到 `"onetime"`、`"private"`、`"playmodeonly_private"` 三个常量
> （行号：`dis.txt:50268`、`50340`）；`rg -n '"<connectmode>' dis.txt` 命中 `J2/a$s.c`、`t2/a$h.c`。

### 2.6 §6-6 UI 文案（`resources.arsc`）

**结论【已解决，且工具已落库】**：本机没有 `aapt/aapt2/java`，所以**自己写了一个纯 Python 解包器**
`official_app/arsc.py`（只依赖标准库）：

```bash
python official_app/arsc.py --stats                        # 类型统计
python official_app/arsc.py --name IDS_ENTER_THE_BLE_PATHKEY   # 按资源名查（含全部语言）
python official_app/arsc.py --value パスコード                  # 按值反查
python official_app/arsc.py --type string --locale ja          # 按类型/语言过滤
```

解析结果：单包 `com.omdigitalsolutions.oishare`，**68832 条**资源
（`string` 52814、`drawable` 9345、`id` 1833、`attr` 1315、`style` 1173、`dimen` 769、`color` 761、`layout` 364…），
支持 UTF-8/UTF-16 字符串池、Sparse/Offset16 类型表、复杂条目（数组/plurals）与多语言配置。

踩过的两个坑（已修，记录备查）：
1. 字符串池里存在的是**偏移**，不是字符串本身 —— 早期版本把「下标」当「偏移」用，
   结果每条字符串都从上一个字符串的第 N 个字符开始（表现为 `ress me - left animation…`）。
2. `ResTable_config` 的 density 在 **偏移 14**（`orientation` 12、`touchscreen` 13），不是 `0x22`。

> 验收标准：
> 1. `python official_app/arsc.py --stats` 第一行是 `string 52814`，总计 68832 条。
> 2. `python official_app/arsc.py --name textView_blePassCode` → 1 条（`id`，`0x7f0905d7`）。
> 3. `python official_app/arsc.py --value パスコード` → 6 条，含 `IDS_ENTER_BLE_PATHKEY` 等。

---

## 3. 对第 58 轮的勘误（**规格层面纠正，不是补充**）

| # | 第 58 轮的写法 | 本轮实测 | 影响 |
|---|---|---|---|
| 1 | §2.1：「累加校验（**含偏移 4 起**，含 len 字段）」 | 校验和 = **`arr[3]+arr[4]+arr[5]+Σpayload`，从偏移 3 起；不含 `len`（`arr[2]`）** | 会写出校验和算错的复刻实现 |
| 2 | §2.1：偏移 4 = 「命令低字节（第 1 个 int 参数 +1）」 | `M2/b.u(int cmdHigh, int cmdLow, byte[] payload)`：**偏移 3 = 高字节、偏移 4 = 常量 `0x01`、偏移 5 = 低字节**（不是「+1」） | 低字节位置写错 → 复刻帧对不上（例：`0x0C02` 的帧是 `0C 01 02`，不是 `0C 03`） |
| 3 | §3：状态码「0 = 默认失败」 | **0 = BLE_RESULT_SUCCESS**；34/35 升为已确证 | 结果码判断会反 |
| 4 | §2.4：4 个 UUID「用途未逐一确认」 | 已确认：1 服务 + 3 特征（写/通知/通知），并给出字段名 `m/n/o` 与开通知顺序 | 复刻缺关键信息 |
| 5 | §2.2 命令表：`0x6A01`=「遥控/参数类①」、`0x1D01`=「心跳/保活」 | `0x6A01` = **GPS 附加**；`0x1D01` = **遥控模式** | 语义错 |
| 6 | §6-1「哪条命令触发相机开 Wi-Fi 未对齐」 | 没有「开 Wi-Fi」的 BLE 命令：App 是**先把 Wi-Fi 打开/连上**（`WifiNetworkSpecifier`），再用 `get_connectmode.cgi` **读/设模式**（字符串）。`0x68xx/0x69xx` 是**死代码** | 少走一大圈弯路 |

### 修正后的帧格式（`M2/b.u(int cmdHigh, int cmdLow, byte[] payload)`）

```
len = payload==null ? 0 : payload.length
buf = new byte[len + 8]
buf[0] = 0x01
buf[1] = seq                      // 实例字段 d(B)，每帧 +1（byte 回绕）
buf[2] = (byte)(len + 3)
buf[3] = (byte) cmdHigh           // 如 0x68 / 0x69 / 0x0C / 0x0F / 0x04 / 0x1D / 0x6A / 0x6B
buf[4] = 0x01                     // 常量（u() 里写死的 1）
buf[5] = (byte) cmdLow            // 第 2 个 int 参数；0x6801 → 1、0x0C02 → 2
buf[6 .. 6+len-1] = payload
buf[6+len]   = (cmdHigh + 1 + cmdLow + Σpayload) & 0xFF
buf[6+len+1] = 0x00
```

> 汇编级证据（`M2/b.z` = 快门 0x040F）：`const/16 v1, #int 15` + `const/4 v3, #int 4` →
> `u(4, 15, {p1})` → 帧头 `04 01 0F`；`M2/b.x`（开机 0x0F01）→ `u(15, 1, {2})` → `0F 01 01`；
> `M2/b.v`（录像 0x0410）→ `u(4, 16, …)` → `04 01 10`。
> 即**第 2 个 int 参数就是命令低字节**，第 4 字节恒为 `0x01`。

**应答比对**（`M2/b$b.a()` 返回结果）：`resp[3] == cmdHigh` 且 `resp[5] == cmdLow`，
都通过则返回 `resp[6]`（业务结果码），否则返回 `-1`；超时返回 `-2`。

---

## 4. 设计与实现的差异分析（本轮）

| 规格（第 58 轮 §6 待办） | 本轮实现情况 | 处理 |
|---|---|---|
| §6-1 opcode 语义逐条对齐 | 已逐条对齐；并发现 6 条是死代码 | **改规格**（round58 表格 + 本节 §2.1） |
| §6-2 UUID 角色 | 已确认 | **改规格**（上表） |
| §6-3 结果码映射 | 已解出全部键值 | **改规格**（码 0 纠正） |
| §6-4 配对码来源 | 已确认 = 用户输入 | **改规格**（关闭该项） |
| §6-5 connectmode 返回码 | 已确认 = 字符串枚举 | **改规格**（关闭该项） |
| §6-6 UI 文案 | 新增 `arsc.py` 并跑通 | **改代码**（新增工具）+ **改规格**（用法与坑） |

**没有留下的「TODO 式假实现」**：`arsc.py` 的每条路径都实际跑过（`--stats/--name/--value`），
解析结果与 dex 侧字符串常量（`str.*` 键、`IDS_*` 文案）能相互印证。

---

## 5. 附录：可复现命令

```bash
# A. 工具自检
cd D:/workspace/om3-handbook
python official_app/oi_index.py --stats                    # 77003 个方法
python official_app/arsc.py --stats                        # 68832 条资源，string 52814

# B. opcode 调用点穷举（证明 0x68xx/0x69xx 无调用者）
python official_app/oi_index.py --call 'M2/b$b.<init>'     # 7 个方法
python official_app/oi_index.py --call 'LM2/b.B('          # 1 个（dispatcher）

# C. 结果码映射（直接解 dex 里的 packed-switch 键值）
python - <<'PY'
import struct
dex=open('official_app/classes.dex','rb').read()
def sw(off,base,label):
    ident,size=struct.unpack_from('<HH',dex,off)
    first=struct.unpack_from('<i',dex,off+4)[0]
    tg=[struct.unpack_from('<i',dex,off+8+4*i)[0] for i in range(size)]
    print(label,'first_key=%d targets=%s'%(first,['0x%x'%(base+t) for t in tg]))
sw(0x50a358,0x09,'s2/b$g.H switch#1')   # 0..6  -> SUCCESS/ALREADY/NOT_FOUND/DISCONNECTED/NOT_FOUND/SEARCHING/CONNECTING
sw(0x50a37c,0x0c,'s2/b$g.H switch#2')   # 33..36 -> BLUETOOTH_OFFON/PASSCODE_ERROR/POWON_ERROR/FINALIZE
PY

# D. UI 文案（无需 aapt）
python official_app/arsc.py --name IDS_ENTER_THE_BLE_PATHKEY
python official_app/arsc.py --value パスコード

# E. 关键行号自查
rg -n 'ADC505F9|82F949B4|B7A8015C|05A02050' official_app/dis.txt
rg -n '"(onetime|private|playmodeonly_private)"' official_app/dis.txt
```

**关键行号速查**（`official_app/dis.txt`，1-based）：

| 对象 | 行号 |
|---|---|
| `N2/a$c$b.run` / `N2/a$c$c.run` / `N2/a$c$d.run`（三个开通知任务） | 65725 / 65786 / 65847 |
| `N2/a$c.onDescriptorWrite`（串起三个特征） | 66189 |
| `N2/a$c.onServicesDiscovered` | 66305 |
| `N2/a.h0()`（枚举特征） / `N2/a.u0()`（写 CCC） | 67784 / 68265 |
| `M2/b.u()`（组帧） | 63728 |
| `M2/b$b.a()`（命令分发 + packed-switch） | 63168 |
| `M2/b.j()`（配对码鉴权） | 64448 |
| `oishare.e$d.run`（鉴权步骤，码 34） | 529299 |
| `oishare.e$e.run`（开机步骤，码 35） | 529377 |
| `oishare.e.G()`（连接入口，写入配对码） | 531493 |
| `s2/b$g.H()`（结果码全量分发） | 1269701 |
| `J2/d.B()` / `J2/d.D()`（模式判定） | 50244 / 50316 |
| `J2/d.L()`（设置连接模式） | 50517 |
| `c2/A.<clinit>`（设置项默认值表） | 311263 |
| `u2/c.b()`（`camera_info_table` 建表 SQL） | 849883 |
| `u2/a.n()`（DB→prefs 同步） | 848688 |

---

## 6. 仍然未解（明确挂出，不假装完成）

1. **`BLE_RESULT_ABNORMAL_CONDITION` / `GPS_OFF` 的码值**：这两条不在 `s2/b$g.H` 的 switch 里
   （`ABNORMAL_CONDITION` 属于 BLE 检测监听 `s2/b$d.O`，其 ints 为 `0/1/2/5/10/36/128/10000`，未逐条对齐）。
2. **`M2/b.p(I)Z` / `M2/b.q()Z` / `M2/b.o(M2/b$d)I`（连接状态查询）的返回码含义**未展开。
3. **配对码的扫码路径细节**：`DeviceQRActivity` 用 zxing 扫码，扫到的字符串如何映射到
   `ble_name/ble_password/camera_ssid` 未逐字段对齐（手动输入路径已确证）。
4. **`get_camprop` / `set_camprop` 的 XML 字段表**（若将来要做「一键写配方进相机」才需要）。
5. **真机 BLE 抓包对齐**：以上都是静态证据，没有真机/抓包交叉验证（无设备）。

---

## 7. 本轮产物

| 文件 | 说明 |
|---|---|
| `SPEC-round59.md` | 本文件（遗留项收敛 + 第 58 轮勘误） |
| `official_app/arsc.py` | **新增**：纯 Python 解包 `resources.arsc`（`--list/--name/--value/--type/--locale/--stats`） |
| `HANDOVER.md` | 顶部新增第 59 轮段落 |

**没做**：没有改 `app/base.html`（md5 仍 `1b5254a238a857a63a3c5808d55e3a39`）、没有重出 APK、
没有改 `official_app/` 里既有的 4 个工具（只新增 1 个）。
