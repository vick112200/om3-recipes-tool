# SPEC-round30.md · v2.17（第三十一轮）

> 用户 2026-09-24 原话：
> **「你要先连接蓝牙才唤醒相机，但是蓝牙设备根本看不出哪个是相机的，官方app好像不是这样的，这一块你再看看」**
>
> 结论：**官方是带过滤器扫蓝牙的**（只扫相机），我们是不带过滤器的全量扫描 —— 所以列表里
> 耳机、手表、电视都混在一起，谁也看不出哪个是相机。本轮照官方的做法改（证据在 §1）。

---

## 0. 一眼版

| # | 改动 | 依据 |
|---|---|---|
| 1 | 扫描改**两段式**：先 `ScanFilter(serviceUuid="ADC505F9-…")` **只扫相机**（6 秒）→ 没扫到再全量扫一遍 | 官方 `N2/c` 的扫描方法（§1.1） |
| 2 | 列表分两栏：**「📷 找到的相机」（带徽章 + 「连它」）** / 「其它蓝牙设备」；全量扫描时相机也按服务 UUID / 名字标出来 | 同上 |
| 3 | 点「蓝牙唤醒相机」时**没连蓝牙** → 自动连扫描到的**相机**那条，连上（服务发现完）后自动补发唤醒帧 | 用户原话"要先连接蓝牙才唤醒" |
| 4 | 发命令的写特征值**优先用官方那两个**（`82F949B4-…` / `B7A8015C-…`），下拉默认选中它 | 官方写路径（§1.2） |

版本 **v2.17**（`versionCode 217`）。回退点 `app/base.before_r31.html`（= v2.16 源码，md5 `9a6586c9dee9860b746ce9bdf0e6e2c8`）。

---

## 1. 证据（官方 APK 反汇编，逐条指令核对）

工具：`dexdump -d om share.apk` → `dis.txt`（1.3 亿行文本），模糊类名 `LN2/*`。

### 1.1 官方扫蓝牙：**带过滤器**

`LN2/c;` 的扫描方法（`startScan` 之前那段）：

```java
ScanSettings settings = new ScanSettings.Builder().setScanMode(??).build();
List<ScanFilter> filters = new ArrayList<>();
filters.add(new ScanFilter.Builder().setDeviceName(名字).build());          // 过滤器 1
filters.add(new ScanFilter.Builder().setDeviceAddress(地址).build());        // 过滤器 2
filters.add(new ScanFilter.Builder()
    .setServiceUuid(ParcelUuid.fromString(
        "ADC505F9-4E58-4B71-B8CA-983BB8C73E4F")).build());                  // 过滤器 3 ← 关键
adapter.getBluetoothLeScanner().startScan(filters, settings, callback);
```

`startScan(filters, …)` 带了非空过滤器 → **系统只回传匹配的设备**，所以官方列表里根本不会出现
耳机/手表；用户永远不需要猜"哪个是相机"。（过滤器之间是**或**关系：名字 / 地址 / 服务 UUID 任一匹配。）

### 1.2 同一个服务下的三个特征值（官方写命令发哪里）

`LN2/a;` 里连上后 `getService("ADC505F9-…")`，再取三个特征值（字段 m/n/o），其中**写命令用 m 和 n**：

| 官方字段 | UUID | 用途 |
|---|---|---|
| `m` | `82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68` | **写命令**（`setValue` + `writeCharacteristic`） |
| `n` | `B7A8015C-CB94-4EFA-BDA2-B7921FA9951F` | **写命令** |
| `o` | `05A02050-0860-4919-8ADD-9801FBA8B6ED` | 订阅通知（写 CCCD `00002902-…`） |

我们以前 `bleWriteTarget()` 只是"遍历服务、拿第一个可写的特征值"，而且 `#bleWUuid` 下拉默认选中的
也是**发现顺序第一个**（真机上 `0000FFF1` 排在前面）→ 帧可能发到相机不认的特征值上。

### 1.3 我们以前的做法（问题所在）

`MainActivity.Bridge.bleScanStart()`：

```java
sc.startScan(cb);                       // ← 没有任何过滤器 = 全量扫描
// callback 里只上报 name / mac / rssi，不判断"像不像相机"
```

页面把每个设备都渲染成一行灰字 + 「连接」 → 用户只能靠名字猜（这正是用户报的现象）。

---

## 2. 改法

### 2.1 原生（`apk/java/com/om3/handbook/MainActivity.java`）

- 新增常量（注释里写明来自官方 APK 的哪个类）：
  `OM3_BLE_SVC` / `OM3_BLE_WRITE1` / `OM3_BLE_WRITE2` / `OM3_BLE_NOTIFY`。
- `bleScanStart()` 保留（老调用点不破），内部转调新的 **`bleScanStart2(int onlyCam)`**：
  - `onlyCam = 1` → `ScanFilter.Builder().setServiceUuid(OM3_BLE_SVC)` + `startScan(filters, settings, cb)`
    （扫描模式 `SCAN_MODE_LOW_LATENCY`；和官方一样"扫到就报"）
  - `onlyCam = 0` → `startScan(null, settings, cb)`（不过滤，兼容"相机广播里不带这个 UUID"的机型）
- `found` 事件多带一个 `cam` 标记：`bleHasCamSvc(r)`（广播里带官方服务 UUID，最硬）
  → 否则 `bleCamLike(name)`（名字像 OM-3 / OM-D / E-M / PEN / TG-… 兜底）。
- 注意：`Bridge` 是**非静态内部类**，`--release 8` 下不能声明 `static` 方法（本轮编译踩到，已改实例方法）。

### 2.2 页面（`app/base.html`）

| 位置 | 改动 |
|---|---|
| `__om3ble('found', …, cam)` | 第 5 个参数 = 原生给的相机标记；再加一层名字兜底（和原生同一套规则） |
| `bleDevRow(o, nm, mac, rssi, cam)` | 相机行：`📷 相机` 徽章 + 绿字 + **「连它」**主按钮；非相机行：普通「连接」 |
| 新 `#bleCamBox` / `#bleOtherBox` | 相机 / 其它分两栏（有内容才显示）——相机不会跟耳机混在一起 |
| `bleScanGo()` | **两段式**：`bleScanMode(1)` → 6 秒没相机 → `bleScanMode(0)`；结束给小结（找到几个相机 / 没找到时给排查三步） |
| `bleBestCam()` | 从扫描结果挑"最像相机"的（📷 优先，其次信号最强） |
| `bleWakeCamera()` | 没连蓝牙时：有相机候选 → **自动连它**并记 `__om3wakeOnConnect`；没有 → 明确提示先扫描（不瞎发帧） |
| `__om3ble('svc')` | 服务发现完 → 若 `__om3wakeOnConnect`，1 秒后自动补发唤醒帧 |
| `bleWriteTarget()` / `#bleWUuid` | 官方那两个写特征值**排最前 + 默认选中**（标注「（官方）」）；没有官方特征值时才退回第一个可写的，并写警告 |
| CSS | 新增 `.blecam` 徽章样式 |

---

## 3. 显式声明清单（约束逐条落到代码）

| 约束 | 涉及 | 落到哪里 |
|---|---|---|
| 权限 | ✓ | 扫描前权限门不变（`blePerm` → `bleAskPerm` → 授权回调自动续扫）；只扫相机也走同一套 |
| 幂等 | ✓ | 重复点扫描只是重扫（先清两张列表 + `BLEDEV`）；`bleScanMode` 可重复调 |
| 超时 / 降级 | ✓ | "只扫相机"6 秒无结果 → 自动降级全量；再 10 秒停表并给小结 |
| 边界 | ✓ | 一个设备都没扫到 / 全是非相机 / 相机没名字（`（无名）`）都有明确文案；`cam` 参数缺失时靠名字兜底 |
| 异步 / 竞态 | ✓ | `__om3wakeOnConnect` 只在"服务发现完成"回调里消费一次（用完即清），不会重复发帧 |
| 状态机 | ✓ | 扫描模式 `1`（只扫相机）/ `0`（全量）显式传参，日志记录实际用的哪种 |
| 兼容 | ✓ | 老页面/老原生双向兼容：原生没 `bleScanStart2` → 页面退回 `bleScanStart()` 并提示；页面没传 `cam` → 原生只管上报 |
| 不猜协议 | ✓ | 服务/特征值 UUID 全部来自官方反汇编（不猜）；帧格式沿用 round19 已核对的 `01 <序号> 03 68 01 02 6D 00` |
| 失败可见 | ✓ | 没用上官方特征值时 **warn** 写日志（不静默） |
| 迁移 | ∉ | 无数据迁移（不改存储结构） |

---

## 4. 验收

| 脚本 | 结果 |
|---|---|
| `scripts/dv_blescan.py`（**新**） | 全过（0 失败）：S1 两段式（`[1]` → `[1,0]`）、S2 只扫相机命中就不再全量、S3 名字兜底、**S4 帧发到官方 `82F949B4`**（服务里第一个可写的是 `0000FFF1`）、**S5 没连蓝牙点唤醒 → 自动连相机并补发帧** |
| `scripts/dv_blecam.py`（改） | 5 段全过：相机/其它分栏、📷、「连它」、帧字节、权限、自动连接、唤醒语义 |
| `scripts/dv_camclean.py`（改文案断言） | 全过 |
| 其余全套 | 23 个脚本一轮全绿；四数 `om3errs=0 / 加入方案按钮=81 / 方案条目数=1 / 运行错误=0` |
| APK 产物自检 | `classes.dex` 里能查到 `ADC505F9-…` / `82F949B4-…` / `bleScanStart2`（确认编进去了） |

---

## 5. 差异分析

| 规格点 | 实现 |
|---|---|
| §1.1 照官方用服务 UUID 过滤 | ✅ 原生 `bleScanStart2(1)` + `ScanFilter(serviceUuid)` |
| §1.2 写命令优先官方特征值 | ✅ 下拉排序 + `selected` + `bleWriteTarget()` 双保险（harness S4 钉住） |
| 「不用先猜哪个是相机」 | ✅ 相机单独一栏 + 📷 + 「连它」；一键唤醒自动选相机 |
| 相机广播里**不带**那个 UUID 的情况 | ✅ 6 秒后降级全量 + 名字兜底（仍会标 📷） |

### 没做（显式记录）

1. **真机还没验**（蓝牙必须真机；本轮只到"页面把桥用对了没有"这一层）。
   真机上要看三点：① 扫的时候列表里是不是只剩相机（或相机单独一栏）；② 日志里 `[BLE] 开始扫描（只找相机…）`；
   ③ 连上后 `写入特征值用官方那个：82f949b4…`。
2. **没做"自动连蓝牙"**（进页面就主动扫+连）：官方是否这么做还没反汇编确认；而且蓝牙扫描/连接会弹系统权限，
   在用户没点之前主动扫不合适 —— 保持不变（点一下就好）。
3. **没做"记住上次连过的相机蓝牙地址"**（官方有 `setDeviceAddress` 过滤器，很可能是存了上次的地址）：
   要新增本地存储字段 + 迁移逻辑，收益是省 1~2 秒；留给下一轮（真机确认"每次都要扫"很烦的时候再做）。
4. **没动 Wi-Fi 那条路**（round29 刚改过）：蓝牙唤醒成功后仍然走既有的"自动连相机热点 + 检测相机"。

---

## 6. 回退清单 & 文件

想单独退掉本轮：

| # | 位置 | 回退动作 |
|---|---|---|
| 1 | `MainActivity.java` | 删 `OM3_BLE_*` 常量、`bleCamLike`、`bleHasCamSvc`、`bleScanStart2`；`bleScanStart()` 恢复原来的 `sc.startScan(cb)` 与三参数 `found` |
| 2 | `app/base.html` 扫描/列表 | `bleScanGo` 恢复单次 `bleScanStart()`；`bleDevRow` 去掉 cam 分支与徽章；删 `#bleCamBox`/`#bleOtherBox`/`bleDevBoxes`/`bleCamCount`/`bleBestCam` |
| 3 | `app/base.html` 唤醒 | `bleWakeCamera` 恢复"没连蓝牙就提示"；删 `__om3wakeOnConnect` 分支 |
| 4 | `app/base.html` 写入特征值 | `bleWriteTarget` 恢复"第一个可写的"；`#bleWUuid` 恢复不排序 |
| 5 | 整份源码 | 用 `app/base.before_r31.html`（= v2.16，md5 `9a6586c9dee9860b746ce9bdf0e6e2c8`）覆盖 `app/base.html` |

| 文件 | 说明 |
|---|---|
| `app/base.html` | md5 `2f1544494d8dce252bfd312305431618` |
| `app/base.before_r31.html` | 回退点 = v2.16 源码，md5 `9a6586c9dee9860b746ce9bdf0e6e2c8` |
| `apk/java/com/om3/handbook/MainActivity.java` | 蓝牙常量 + `bleScanStart2` + cam 标记 |
| `scripts/dv_blescan.py` | **新**验收脚本（S1–S5） |
| `scripts/dv_blecam.py` / `dv_camclean.py` | 跟着新交互更新断言 |
| `apk/build/om3.apk` | v2.17（`versionCode 217`），md5 `1d3e9a744a7003f90a01056f27a321b9`；`apk/assets/index.html` md5 `0f50751cb8183ca2b90172cbe08477dd` |
