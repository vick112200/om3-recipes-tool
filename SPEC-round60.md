# 第 60 轮：官方 App 连接逻辑收尾（检测监听码值 / 传输层状态方法 / 配对二维码链路）

> ⚠️ **勘误（第 61 轮）**：本文件 §0.3 / §2.4 表（`a`/`g` 行）/ §2.4.5 有两处结论**已被推翻**：
> ① **二维码确实携带 BLE 配对码**（`f$a.j`，prefs `str.blePass`；`f$a.a()` 强制 `i/j` 非空）——
> 原文「二维码里不含蓝牙配对码」是反的；
> ② `f$a.g` **不是** Wi-Fi 安全类型，是 **Wi-Fi netId**（构造器里恒 `-1`；安全类型只在 `f$a.a`）。
> 详见 `SPEC-round61.md` §3。**其余结论（检测码值、传输层方法、QR 格式/置换表/`b/f/c/d`）仍然有效。**

> 目的：把 `SPEC-round59.md` §6「仍然未解」里**静态能解的三条**挖掉（真机抓包那条做不了）。
> **纯分析，没有动手册 App**：`app/base.html` md5 仍 `1b5254a238a857a63a3c5808d55e3a39`（v3.15）。

---

## 0. 一句话结论

1. **BLE「检测」监听的结果码也解出来了**：`0=検索成功`、`1=既に接続済み`、`2=NOT_FOUND`、
   `5=検索中`、**`36=FINALIZE`**、**`128=ABNORMAL_CONDITION`**（`s2/b$d.O` 的 if-eq 链）。
2. `M2/b` 的三个「状态方法」不是「查码值」，而是**传输层生命周期 + 能力位掩码**：
   `o(cb)=初始化/重置传输层`、`p(mask)=能力位掩码查询`、`q()=是否忙`、`m()=断开`、`n()=finalize`。
3. **配对二维码（QR）链路已通**：格式 `OIS1|OIS2|OIS3` + `,` 分段 + 段内 `-` 分隔，
   字符先经**静态置换表**还原（`oishare.f.<clinit>` 里 60 组 `Character→Character`），
   解析器 `oishare.f.b(String)` → 模型 `oishare.f$a`；**SSID/密码/安全类型/设备名/连接模式都能对上 prefs 键**。
   （二维码里**不含**蓝牙配对码——与第 59 轮结论一致：配对码是用户在「Bluetooth パスコード入力」界面输入的。）

---

## 1. 本轮范围与「必须显式声明清单」

| 项 | 说明 |
|---|---|
| 输入 | `official_app/dis.txt`、`official_app/classes.dex`、`official_app/oi_index.json` |
| 输出 | 本规格、新工具 `official_app/oi_switch.py` |
| 前置条件 | 只要 Python 3 标准库；无需网络/java/aapt |
| 后置条件 | 手册 App 产物零变化（md5 不变、不出 APK） |
| 权限 / 幂等 / 事务 / 并发 / 数据迁移 / 性能 / 安全 | **不涉及**（只读分析） |
| 失败回退 | **不涉及**（只新增 1 个脚本，删掉即回退） |

---

## 2. 遗留项收敛

### 2.1 BLE「检测」监听（`OlyBleDetectListener`）的码值【已确证】

`s2/b$d.O(ILjava/util/ArrayList;)V`（行 `L1269420-1269669`）用 **if-eq 链**分发（不是 switch），
分支偏移可直接换算成目标地址，再把目标地址对到分支体里的日志：

| 码 | 分支体日志 | 含义 | 证据（`dis.txt` 行号 / 偏移） |
|---|---|---|---|
| 0 | `.OlyBleDetectListener 検索成功` | 搜索成功（找到相机） | `if-eqz v6 → 0x199`，日志在 `L1269622` |
| 1 | `.OlyBleDetectListener 既に接続済み` | 已连接过 | `if-eq v6,1 → 0x157`，日志在 `L1269591` |
| 2 | `.OlyBleDetectListener BLE_RESULT_NOT_FOUND` | 没找到 | `if-eq v6,2 → 0x124`，日志在 `L1269568` |
| 5 | `.OlyBleDetectListener 検索中` | 搜索中 | `if-eq v6,5 → 0x106`，日志在 `L1269555` |
| 36 | `.OlyBleDetectListener BLE_RESULT_FINALIZE` | 结束 | `if-eq v6,36 → 0xa9`，日志在 `L1269514` |
| 128 | `.OlyBleDetectListener BLE_RESULT_ABNORMAL_CONDITION` | 异常状态（蓝牙/GPS 等不可用） | `if-eq v6,128 → 0x6d`，日志在 `L1269487` |
| 其它 | `.OlyBleDetectListener その他 result=` | 未分类 | default（日志在 `L1269463`） |

**与连接监听的码值对照**（`s2/b$g.H`，第 59 轮已解）：两者是**两套**码表，只有 `2/5/36` 重合，
所以判断「同一个数字」在不同回调里含义可能不同，写代码时必须按监听器区分。

> 验收标准：`python official_app/oi_switch.py --cls 's2/b$g;' --meth H` 复现连接监听码表；
> 检测监听因用 if-eq 链，用 `sed -n '1269420,1269669p' official_app/dis.txt` 逐条对照上表的偏移。

### 2.2 `GPS_OFF`【结论：不是 BLE 栈返回的码值】

- `BLE_RESULT_GPS_OFF` 的日志在 `s2/b$g.H` 里，但**两个 packed-switch 的键值表都不包含它**
  （键只有 `0..6` 与 `33..36`），说明它不是「相机侧回传的码」，而是本地判断后打印的。
- 真正的 GPS 关判断在业务层：`oishare.e.H()` / `oishare.e.e0()` 的日志
  `.connectInner BLE_INIT_GPS_OFF` —— 即**连接前**自检「位置服务没开」。
- ⇒ 复刻时：**不需要**处理「GPS_OFF 码」，只需在发起连接前检查定位权限/开关。

> 验收标准：`python official_app/oi_index.py --greps 'GPS_OFF'` → 3 个方法
> （`oishare.e.H`、`oishare.e.e0`、`s2/b$g.H`）；`oi_switch.py` 在 `s2/b$g.H` 里**不会**输出 GPS_OFF 这个码。

### 2.3 `M2/b` 的传输层状态方法【已确证】

| 方法 | 实测语义 | 证据 |
|---|---|---|
| `M2/b.o(M2/b$d)I` | **初始化/重置传输层**：设回调 `c`；若已有 `N2/a` 先 `d0()`（释放）并置 null；再 `new N2/a(context)`；返回 `N2/a.k0()` | `M2/b;.o` 体（`L64603`）：`new-instance LN2/a;` + `N2/a.k0()I` |
| `M2/b.p(I)Z` | **能力/状态位掩码查询**：`(N2/a.f0() & mask) != 0` | `M2/b.p` 体：`f0()I` → `and-int/2addr` → `if-eqz` |
| `M2/b.q()Z` | **是否忙/是否可发命令**（读实例字段 `m:Z`） | `M2/b.q` 体：`iget-boolean … .m:Z` |
| `M2/b.m()V` | **断开**（日志 `接続切断` → `N2/a.b0()`） | `M2/b.m` 体 |
| `M2/b.n()V` | **finalize**（清字段、日志 `BLE Finalize`、`N2/a.d0()`、清队列） | `M2/b.n` 体 |
| `N2/a.k0()I` | 蓝牙可用性自检：`BluetoothManager.getAdapter()`、`hasSystemFeature("android.hardware.bluetooth_le")`、`isEnabled()`；常量 `129/130` | `N2/a.k0`（`L68692`）的字符串即证据 |
| `N2/a.f0()I` | 由 `M2/a.o()/p()/n()/l()/m()` 五个布尔拼成位掩码 | `N2/a.f0` 的 calls |

`M2/b.p(mask)` 的调用者只有 4 处（`oishare.e.B(I)`、`H()`、`I()`、`W()`）——
即「连接前/连接结果处理时判断当前相机是否具备某能力」。**各个 bit 的具体语义未逐位对齐**（见 §5）。

> 验收标准：`python official_app/oi_index.py --call 'M2/b.p('` → 4 个方法；
> `python official_app/oi_index.py --cls 'M2/b;' | rg ' (m|n|o|p|q) '` 能拿到行号复核。

### 2.4 配对二维码（QR）链路【格式+解析已确证，字段位序部分确证】

链路：

```
扫码(zxing, DeviceQRActivity) → 字符串
  → oishare.f.b(String)         // QRCodeUtils.decodeQRCode；null → "qrCode is null"
      ├ 前缀 "OIS1" → f.c([String])   // 字段少
      ├ 前缀 "OIS2" → f.d([String])   // 带 2 个 int 字段
      └ 前缀 "OIS3" → f.e([String])   // 带 3 个 int 字段
  → 每段先过 oishare.f.a(String)  // QRCodeUtils.convertStr：逐字符查静态置换表
  → 产出 oishare.f$a 模型；f$a.a()Z 校验
  → DeviceWifiActivity$k.j() / HomeActivity.d6() 等消费：写 prefs / 发起连接
```

1. **分段规则**：先按 `,` 切成最多 7 段（`String.split(",", 7)`），
   段内再按 `-` 切成子段（空子串用 `c2/F.T()` 处理）。
2. **字符混淆**：`oishare.f.<clinit>` 建了一张 `Character→Character` 的 **Map**（60 组），
   `oishare.f.a(String)` 逐字符 `map.get(c)` 还原；遇到表里没有的字符会打日志
   `想定外の文字が設定されました。 srcC: `。实测这张表是**两两互换**的定值置换，开头一段是：
   `0↔/`、`1↔-`、`2↔+`、`3↔*`、`4↔%`、`5↔$`、`6↔Z`、`7↔Y`、`8↔X`、`9↔W`、`A↔V`、`B↔U`、`C↔T` …（`0x20`~`0x5A` 一整个区间）。
3. **模型 `oishare.f$a`**：字段 `a:int b:String c:String d:String e:String f:String g:int h:int i:String j:String k:String`。
   **已确证**的字段语义（靠「prefs ↔ 字段」双向对照，不是猜）：

| 字段 | 语义 | 证据 |
|---|---|---|
| `b` | 相机 AP 的 **SSID 系**（复合串） | `J2/e.Z` 把 prefs **`str.wifi.camera.ssid`** 写进 `b`；`DeviceWifiActivity$k.j` 把 `b` 按 **`-P-`** 拆成 `str.PairingCameraName` + `str.PairingCameraSsid` 两个 prefs |
| `f` | **Wi-Fi 密码** | `J2/e.Z` 把 **`str.wifi.camera.password`** 写进 `f` |
| `a` / `g` | **Wi-Fi 安全类型**（int） | `J2/e.Z` 把 **`str.wifi.Security.Type`** 同时写进 `a` 和 `g` |
| `c` | **设备名** | `J2/d.q()` 的日志名是 `WifiSwitcher.getDeviceName`，体内读 `c` |
| `d` | **连接模式**（`private` / `onetime` / `playmodeonly_private`） | `J2/d.L(String)` 里 `iput f$a;.d` |
| `i` | 触发 `DeviceWifiActivity.d2(...)` 的一个串（与配对/注册相关，**未完全确认**） | `DeviceWifiActivity$k.j` 0xac~0xc0：读 `i` → 非空则 `d2()` |
| `e/h/j/k` | 未确认 | — |

4. **唯一入口**：全 dex 只有 2 处调 `oishare.f.b(String)`：`HomeActivity.d6`（`prepareConnectWifi`，
   失败日志 `QRコードのデコードに失敗しました。 qrCode: `）与 `DeviceWifiActivity.onResume`。
5. **二维码里没有蓝牙配对码**：`f$a` 的任何字段都没有被写成 prefs `str.blePass`；
   第 59 轮已确证 `str.blePass` 来自「Bluetooth パスコード入力」界面（用户输入）。
   → 与第 59 轮结论**互相印证**，不是矛盾。

> 验收标准：
> 1. `python official_app/oi_index.py --greps 'OIS1'` → 只有 `oishare.f.b`（含 `OIS1/OIS2/OIS3` 三个常量）。
> 2. `python official_app/oi_index.py --call 'oishare/f.b('` → 2 个调用点（`HomeActivity.d6`、`DeviceWifiActivity.onResume`）。
> 3. `sed -n '888395,888460p' official_app/dis.txt` 能看到 `str.wifi.camera.ssid → f$a.b`、
>    `str.wifi.camera.password → f$a.f`、`str.wifi.Security.Type → f$a.a/g` 三条 `iput`。

---

## 3. 新增工具：`official_app/oi_switch.py`

**为什么需要**：dalvik 把 switch 的「码值→分支」表放在 payload 里，dexdump 只打一行
`packed-switch-data (N units)` 而且**列不全**（后面跟 `...`），所以 `oi_index.py` 里看不到任何 `#int`，
肉眼看不出「34 = PASSCODE_ERROR」这类映射。第 59 轮是手写片段解的，本轮**固化成工具**：
它按 dexdump 行首的十六进制（= dex 文件偏移）直接读字节解表。

```bash
python official_app/oi_switch.py --cls 's2/b$g;' --meth H      # 按类+方法（用索引的行号区间）
python official_app/oi_switch.py --lines 1269701 1269930       # 或直接给行号
python official_app/oi_switch.py --cls 's2/b$g;' --meth H --key 34   # 只看某个码值
```

**自检**：对第 59 轮**人工**解出的 `s2/b$g.H` 跑一遍，输出与人工结果**逐行一致**
（`0→SUCCESS`、`1→ALREADY_CONNECTED`、`2/4→NOT_FOUND`、`3→DISCONNECTED`、`5→SEARCHING`、
`6→CONNECTING`、`33/34/35/36→BLUETOOTH_OFFON/PASSCODE_ERROR/POWON_ERROR/FINALIZE`），
即「工具 ↔ 人工」互为交叉验证。

> 踩坑记录：`packed-switch v6, 000001d8 // +000001cf` 里，**操作数是 payload 的绝对代码地址**
> （注释里的 `+xxxx` 才是相对偏移）。第一版把操作数当相对偏移用，目标地址整体偏掉了一个 insn 地址，
> 表现为「payload 未在区间内」。已修（并把相对偏移留作兜底）。

---

## 4. 设计与实现的差异分析（本轮）

| 规格（第 59 轮 §6 待办） | 本轮情况 | 处理 |
|---|---|---|
| ① `ABNORMAL_CONDITION`/`GPS_OFF` 码值 | `ABNORMAL_CONDITION=128` 已确证；`GPS_OFF` **不是码值**（本地自检日志） | **改规格**（关闭该项） |
| ② `M2/b.p/q/o` 状态码 | 已定性（生命周期/位掩码，不是码值表）；bit 语义未逐位对齐 | **改规格** + 留在 §5 |
| ③ 扫码配对字段映射 | 格式/解析器/混淆表 + `b/f/a/g/c/d` 六个字段已确证；`i/j` 未定 | **改规格**（部分关闭） |
| ④ `get_camprop/set_camprop` 字段表 | 未做（是「写配方进相机」才需要，量大，留给下一轮） | 保留在 §5 |
| ⑤ 真机抓包 | **做不了**（无设备）；但本轮把「静态可解」的都解完了 | 明确标注为环境限制，不作为待办 |

新增代码（`oi_switch.py`）**没有 TODO、没有假分支**：`--cls/--meth`、`--lines`、`--key` 三条路径实跑过，
且与人工结论交叉验证一致。

---

## 5. 仍然未解

1. `M2/b.p(mask)` 各位（bit）的具体语义（`N2/a.f0()` 由 `M2/a` 的 5 个布尔拼成，需再下钻 `M2/a`）。
2. `oishare.f$a` 的 `e/h/j/k` 字段语义；`i` 与 `DeviceWifiActivity.d2()` 的用途（配对码/注册）。
3. `get_camprop` / `set_camprop` 的 XML 字段表（**量最大**，做「把配方写进相机」时才需要）。
4. `camera_info_table`（SQLite）在真机上的实际内容 / 用户注册流程的完整 UI 路径。
5. 真机 BLE 抓包交叉验证（无设备，做不了）。

---

## 6. 本轮产物

| 文件 | 说明 |
|---|---|
| `SPEC-round60.md` | 本文件 |
| `official_app/oi_switch.py` | **新增**：packed/sparse-switch 键值表解码器（读 dex 字节） |
| `HANDOVER.md` | 顶部新增第 60 轮段落 |
| `AGENTS.md` | §5 工具清单加入 `oi_switch.py` |

**没做**：没有改 `app/base.html`（md5 仍 `1b5254a238a857a63a3c5808d55e3a39`）、没有重出 APK。
