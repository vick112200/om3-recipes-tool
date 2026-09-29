# 第 65 轮：官方 App 剩下 **55 个未用 `.cgi`** 的「参数表」（静态全覆盖）

> 需求方 2026-09-28 说「能做的都做」→ 本轮 = HANDOVER 候选 **③**（支线，纯静态分析，**不改 App、不出包**）。
> 上一轮（第 64 轮）已经收尾并出包 v3.18（见 `SPEC-round64.md`）。
>
> **本轮不产生任何 APK 产物**：只加了一个分析工具 + 这份表。改的是**分析结论**，不是页面 ——
> **App 一个字节都没动**（`app/base.html` md5 与第 64 轮产物逐位相同，见 §9.1 第 6 条）。

---

## 1. 范围与「必须显式声明清单」

| 项 | 说明 |
|---|---|
| 输入 | `official_app/dis.txt`（130 MB 反汇编源）+ `official_app/oi_index.json`（第 58 轮建的方法索引）；`SPEC-round61.md` §8 给出的"没碰过的"清单（**本轮把它从 53 订正为 55**，见 §9.2 第 4 条） |
| 输出 | **`official_app/oi_cgi.py`**（新工具，按 CGI 名抽参数表）+ **`official_app/cgi_table.txt`**（`--all` 的原始输出，可复现的证据）+ 本规格（人工判读后的表） |
| 前置条件 | 工程里已有 `dis.txt` / `oi_index.json`（**不重建**，第 58 轮的 md5 见 `SPEC-round58.md` §9） |
| 后置条件 | **手册 App 一个字节都没改**（`app/base.html` md5 仍是第 64 轮的 `3692725c…`）；不重新出包 |
| 权限 | **不涉及**（离线读文件） |
| 幂等 | **涉及**：工具是只读脚本，随便重跑；`--all > cgi_table.txt` 可随时重新生成 |
| 事务/并发 | **不涉及** |
| 数据迁移 | **不涉及** |
| 性能 | 工具一次 `--all` 约 10 秒（57 MB 索引 + 55 KB 输出） |
| 安全 | **不涉及**（不联网；分析对象是本地文件） |
| 失败回退 | 无副作用 —— 只新增文件，删掉即可 |
| 明确不做 | ① **不改** `app/base.html` / `MainActivity.java`；② **不做**新功能（只看"能不能做、怎么做"）；③ **不读响应格式**（见 §7 显式声明）；④ 不动 `.cgi` 之外的东西（BLE / MySet 已在第 58~62 轮做完） |

---

## 2. 方法（证据怎么来的、怎么复现）

```bash
cd D:\workspace\om3-handbook
python official_app/oi_cgi.py --list                 # 68 个 .cgi 名（从 dis.txt 流式数出来，不重建索引）
python official_app/oi_cgi.py --cgi get_imglist --raw# 某个 CGI：谁在调 + 参数键 + 调用目标 + 原文上下文
python official_app/oi_cgi.py --all > official_app/cgi_table.txt   # 55 个一次性全出（本轮证据，55 KB）
python official_app/oi_cgi.py --body 'Lc2/s;' a      # 单看一个方法体的原文
```

**证据强度分级**（表里逐行标注）：

| 级别 | 含义 |
|---|---|
| **实** | URL **字面量**直接写在 dis.txt 里（形如 `const-string v2, "get_imglist.cgi?DIR="`）→ 参数名与顺序**逐字可信** |
| **推** | 由方法名/所属 Activity/相邻字符串推断的用途（URL 是实的，用途是名字推的） |
| **待** | 还没读到（响应体格式、取值域）——**不猜**，表里写明"待读" |

> ⚠️ **关于"逐字"的边界**：dis.txt 里同一个 URL 常常是**几个 `const-string` 拼**出来的
> （例如 `"?DIR=" + dir + "&size=" + n`）。本表把这种写法**拆成逐个字面量**列出（`?DIR=` + `&size=`），
> 拼出来的**顺序**照官方代码里的 append 顺序；**不把拼接结果伪装成一个字面量**（`dv_r65` 会逐条核对）。
>
> ⚠️ **工具的一个坑（会误导判读，已修）**：`--cgi` 输出的"调用"列里，`Lc2/s;.a/b/d/e` 出现得最多 ——
> 它们**不是 HTTP 调用，只是日志**（`Log.d/w/e/i`）。查证：`python official_app/oi_cgi.py --body 'Lc2/s;' a` →
> 方法体只有一句 `invoke-static {v0,v1}, Landroid/util/Log;.d`。**看"谁真的发了请求"要看 `Lc2/k;.c/d/f` 或 `Ljava/net/HttpURLConnection`**。

---

## 3. 共享助手速查（读表前先看这几行）

| 类/方法 | 是什么 | 证据 |
|---|---|---|
| `Lc2/s;.a(String,String)` | **Log.d**（tag=`"s"`） | `--body 'Lc2/s;' a`：方法体就是 `Log.d` |
| `Lc2/s;.b` / `.d(…,Throwable)` / `.e` | Log.w（带 `isLoggable` 门）/ **Log.e** / Log.i | `--body 'Lc2/s;' b`、`d`、`e` |
| `Lc2/s;.g()` / `.h()` | **`Log.isLoggable("s", DEBUG/INFO)`** —— 是"日志等级开没开"，**不是**"相机连没连" | `--body 'Lc2/s;' g`：`sget tag "s"` + `Log.isLoggable` |
| `Lc2/k;` | **HTTP 命令执行器 + 命令表白名单**：`k.c(url)Z` 拿 URL 去 `ArrayList<k$b>`（=`get_commandlist.cgi` 的结果）里查 | `--body 'Lc2/k;' c`：遍历 `Lc2/k;.h:ArrayList`，取 `k$b.b()` 字符串比较 |
| `Lc2/k;.d(url,data)Z` / `.f(url)Z` / `.g()Z` | 发请求（`set_camprop` 那批用的是 `d`；`get_*` 那批用 `f`/`c`） | 第 62 轮已用（`SPEC-round61.md` §2.4） |
| `Lc2/A;`（`OIShareApplication.K()` 返回） | SharedPreferences 包装（`i(k)` 读 / `s(k,v)` 写） | `SPEC-round61.md` §2.3 |
| `LJ2/a;` | **相机命令表执行器**（`y0/d0/A0/Z/X/I…` 每个方法 = 一个 CGI，30 条指令左右的薄封装） | 本表：`get_commandlist/get_connectmode/fwup_getversions/get_cameraloginfo/…` 都落在它上面 |
| `LJ2/d;`（`OIShareApplication.Q()`） | 相机会话/状态（`C()` 判断、`n()` 取时间串） | 本表：`exec_pwoff` 用 `J2/d.C()`、`set_utctimediff` 用 `J2/d.n()` |
| `trans/b;` | **流控制器**（`readyMovieStream` / `startMovieStream` / `startMovieStreamTS` / `stop` / `exit` / `info`） | 本表 §4.4 |
| `track/d;` | GPS/记录相关 CGI 的薄封装（每个方法一个 CGI） | 本表 §4.5 |
| 主机地址 | 一律 `http://192.168.0.10/`（少数用相对路径 `/xxx.cgi`） | 逐行 URL 字面量 |

---

## 4. 参数表（**55 个**，按功能分组）

> 写法：`CGI 名` **参数（逐字）** —— 用途〔官方类/方法〕。没写"参数"的 = URL 里**没有任何查询参数**（实）。

### 4.1 看图 / 传图（17）—— 全在 `trans/ImageTransListActivity`（只有一处例外）

| # | CGI | 参数（实） | 用途 | 官方类/方法 |
|---|---|---|---|---|
| 1 | `get_imglist.cgi` | `?DIR=`（值 = `URLEncoder.encode(目录)`） | 列目录里的图片 | `ImageTransListActivity.S7`（推） |
| 2 | `get_rsvimglist.cgi` | — | 列"保留/流水"图列表 | `HomeActivity.K5`、`ImageTransListActivity.T7` |
| 3 | `get_thumbnail.cgi` | `?DIR=` | 缩略图 | `ImageTransListActivity.W7` |
| 4 | `get_screennail.cgi` | `?DIR=` | 屏幕尺寸预览图 | `ImageTransListActivity.V7` |
| 5 | `get_resizeimg.cgi` | `?DIR=` + `&size=` | 缩放图 | `ImageTransListActivity.U7`、`.V8` |
| 6 | `get_resizeimg_witherr.cgi` | `?DIR=` + `&size=` | 同上，但**失败时也返回一张图**（带错误图案） | `ImageTransListActivity.U7`、`.V8` |
| 7 | `get_exif.cgi` | `?DIR=%s` | EXIF | `ImageTransListActivity.f7`、`.g7` |
| 8 | `get_movfileinfo.cgi` | `?DIR=%s` | 视频文件信息 | `ImageTransListActivity.w7` |
| 9 | `get_dcffilenum.cgi` | — | DCF 文件编号/数量 | `track/d.t`（另一处在 `oishare/a$c.doInBackground` 那个大 HTTP 类） |
| 10 | `get_unusedcapacity.cgi` | — | 剩余容量 | `track/d.z` |
| 11 | `get_playtargetslot.cgi` | — | 读"播放目标槽" | `HomeActivity.M5`、`ImageTransListActivity.L7` |
| 12 | `set_playtargetslot.cgi` | `?targetslot=%d` | 设"播放目标槽" | `E2/a$J.g`（自己开的 HttpURLConnection）、`track/d.F`、`HomeActivity.o6`、`ImageTransListActivity.p9` |
| 13 | `check_mountmedia.cgi` | — | 检查媒体（卡）挂载 | `track/d.l` |
| 14 | `exec_erase.cgi` | `?DIR=%s` | 删除 | `ImageTransListActivity.K6(String,Z)` |
| 15 | `cancel_trimresize.cgi` | `?DIR=` | 取消裁剪/缩放 | `ImageTransListActivity.v6` |
| 16 | `exec_movietrimresize.cgi` | `?DIR=%s&starttimestamp=%d&stoptimestamp=%d&resizeparam=%s` | 视频裁剪 / 缩放 | `ImageTransListActivity.E8` |
| 17 | `get_trimresizeprocstatus.cgi` | — | 查裁剪/缩放进度 | `ImageTransListActivity.Q7` |

> **规律**：传图这一族**只认一个 `DIR=`**（目录路径，可能带文件名），值要 `URLEncoder.encode`；`&size=` 只出现在缩放那两支。

### 4.2 拍照 / 录像 / 关机（5）

| # | CGI | 参数（实） | 用途 | 官方类/方法 |
|---|---|---|---|---|
| 18 | `exec_shutter.cgi` | `?com=` + **6 个取值**：`1stpush`（半按）/ `1strelease` / `2ndpush`（全按）/ `2ndrelease` / `1st2ndpush`（半按+全按一次）/ `2nd1strelease`（全按后一起放） | **HTTP 快门** | `remocon/RemoconReleaseActivity.R2/S2/T2/x2/y2`、`RemoconReleaseBleActivity.K3` |
| 19 | `exec_takemisc.cgi` | `?com=` + `getlastjpg` / `getrecview` / `startliveview&port=` / `stopliveview` / `ctrlzoom&move=` / `digitalzoomshift` / `supermacroaflock&func=` / `supermacromfinaflock&move=` + `&movement=` / `OneTouchLight&switch=` / `MovieThroughStart` / `MovieThroughStop` / `GetMovieSetting` / `GetShortMoviesAlbumInfo`。取值（**推**：来自该方法内的字符串常量，映射未逐条核）：变焦 `off` `wideterm` `teleterm` `tele` `term` `supermacro` `widemove` `telemove`；超微距 `lock` `release` / `stop` `nearstep` `farstep`；补光灯 `on` `off` | 遥控"杂项"（取图 / 取景开关 / 变焦 / 超微距 / 补光灯 / 视频开关） | `remocon/RemoconV20Activity`、`RemoconV21Activity`（21 个方法） |
| 20 | `exec_takemotion.cgi` | `?com=` + `takeready` / `starttake`（可选 `&upperlimit=200`、`&exposuremin=%d`）、`&point=` / `stoptake` / `startmovietake`（可选 `&limitter=-1`、`&liveview=on` / `&liveview=off`）/ `stopmovietake` / `assignafframe&point=` / `assignaflock&point=` / `releaseafframe` / `releaseaflock` | 触屏对焦 / 连拍 / 长曝（"点哪拍哪"那套） | `remocon/RemoconV20Activity`、`RemoconV21Activity`（16 个方法） |
| 21 | `set_takemode.cgi` | `?com=normal` / `?com=selftimer` | 拍摄模式（计时器） | `RemoconV20Activity.g4/j4` |
| 22 | `exec_pwoff.cgi` | `?mode=withble`（**可省**：两种都在同一个方法里） | 关相机（BLE 连着时用 `withble`） | `OIShareApplication.W0` |

> **注意**：`exec_shutter.cgi` 那条链里，`RemoconReleaseActivity.x2` **同时**用了
> `http://192.168.0.10/switch_cammode.cgi?mode=shutter` —— 也就是
> **"切到快门模式 → 发 com="** 两步都是 HTTP，**不需要 BLE**（BLE 那条是 `RemoconReleaseBleActivity`）。见 §5 ①。

### 4.3 实时取景 / 流媒体（7）—— 全在 `trans/b`（流控制器）

| # | CGI | 参数（实） | 用途 |
|---|---|---|---|
| 23 | `ready_moviestream.cgi` | `?audiomethod=tcp&videomethod=udp&audioport=` + `&videoport=`（另有只带视频的变体 `?videomethod=udp&videoport=`） | 协商端口（音频 TCP / 视频 UDP） |
| 24 | `start_moviestream.cgi` | `?DIR=` + `&startsec=` + `&audiocodec=pcm&audiosample=24&audiochannel=1&videocodec=jpeg&videoquality=vga&videorate=10` | 开始拉流（**视频 = JPEG / VGA / 10fps；音频 = PCM 24k 单声道**） |
| 25 | `start_moviestreamts.cgi` | `?DIR=` + `&starttimestamp=`（编码参数同上一行） | 从某时间戳开始拉流 |
| 26 | `stop_moviestream.cgi` | — | 停止 |
| 27 | `exit_moviestream.cgi` | — | 退出流模式 |
| 28 | `get_moviestreaminfo.cgi` | — | 查流信息（端口/状态） |
| 29 | `get_camprop.cgi` | `?com=get&propname=touchactiveframe` / `?com=desc&propname=desclist` / `?com=check&propname=`（动态名） | 单参数读写相机属性（**我们不用它**，第 61 轮已说明） |
| 30 | `set_camprop.cgi` | `?com=set&propname=` + 下面那张 propname 表 | 单参数**写**相机属性（20 个调用点，全在遥控页） | `remocon/RemoconV21Activity`（20 个方法） |

### 4.4 GPS / AGPS / 社交投稿（10）

| # | CGI | 参数（实） | 用途 | 官方类/方法 |
|---|---|---|---|---|
| 30 | `check_gpsrecording.cgi` | — | 查 GPS 记录是否在跑 | `track/d.k`、`gpsassistdata/GpsAssistDataActivity.v3` |
| 31 | `check_snsrecording.cgi` | — | 查社交投稿记录 | `track/d.n` |
| 32 | `get_gpsdivunit.cgi` | — | 取 GPS 记录分块单位 | `track/d.u` |
| 33 | `get_gpsloglist.cgi` | — | 列 GPS 日志 | `track/d.v` |
| 34 | `get_snsloglist.cgi` | — | 列社交投稿日志 | `track/d.y` |
| 35 | `req_attachexifgps.cgi` | —（POST，参数在 body） | 给照片贴 GPS | `track/d.I(String,…)` |
| 36 | `req_storegpsinfo.cgi` | `?mode=` + `&date=` | 存 GPS 信息 | `track/d.E(3×String,…)` |
| 37 | `get_agpsinfo.cgi` | — | 取 AGPS 信息 | `GpsAssistDataActivity.s3` |
| 38 | `send_agpsassistdata.cgi` | —（数据走 body，方法体 114 条指令） | 传 AGPS 辅助数据 | `GpsAssistDataActivity.k2` |
| 39 | `update_agpsassistdata.cgi` | `?expiration-date=` | 更新 AGPS 有效期 | `GpsAssistDataActivity.q2` |

### 4.5 固件升级（7）

| # | CGI | 参数（实） | 用途 | 官方类/方法 |
|---|---|---|---|---|
| 40 | `fwup_check.cgi` | — | 固件升级前检查 | `settings/firmup/FirmupUploadActivity.b3` |
| 41 | `fwup_getfirmstatus.cgi` | — | 查升级状态 | `FirmupUploadActivity.e3` |
| 42 | `fwup_getversions.cgi` | — | 取版本号 | `LJ2/a.d0`、`settings/myset/b.m`、`settings/myset/c.C2`、`FirmupCameraInfoActivity.J2` |
| 43 | `fwup_sendinfo.cgi` | `?ObjectCompressSize=%d` | 传固件包信息（大小） | `FirmupUploadActivity.t3` |
| 44 | `fwup_sendsplit.cgi` | `?OffsetPos=%d&Byte=%d` | **分片传固件**（偏移 + 字节数） | `FirmupUploadActivity.s3` |
| 45 | `fwup_update.cgi` | — | 开始刷写 | `FirmupUploadActivity.D3` |
| 46 | `fwup_updatemode.cgi` | — | 切到升级模式 | `FirmupCameraInfoActivity.I2` |

### 4.6 相机日志（4）

| # | CGI | 参数（实） | 用途 | 官方类/方法 |
|---|---|---|---|---|
| 47 | `get_cameraloginfo.cgi` | — | 日志信息 | `LJ2/a.Z` |
| 48 | `get_partialcameralogdata.cgi` | `?offset=0&size=` | 分页拉日志 | `LJ2/a.X` |
| 49 | `clear_cameralogdata.cgi` | — | 清日志 | `LJ2/a.I` |
| 50 | `clear_resvflg.cgi` | — | 清"保留标记" | `trans/ImageTransListActivity.E6` |

### 4.7 连接 / 时间（4）

| # | CGI | 参数（实） | 用途 | 官方类/方法 |
|---|---|---|---|---|
| 51 | `get_commandlist.cgi` | — | **取相机支持的命令表**（结果存进 `Lc2/k;.h`，之后 `k.c(url)` 拿它当白名单） | `LJ2/a.y0` |
| 52 | `get_connectmode.cgi` | — | 连接模式（返回值第 59 轮已解） | `I2/i.l`、`LJ2/a.w0`、`t2/a.z`、`RemoconV20Activity.m3`、`RemoconV21Activity.V9` |
| 53 | `set_timeout.cgi` | `?timeoutsec=1800` | **设相机待机超时（字面量就是 1800 秒）** | `I2/i.i` |
| 54 | `set_utctimediff.cgi` | `?utctime=` + `&diff=`（两处都这么拼；`onetime` 是**推**：来自该方法内的字符串常量） | 校时（UTC 时间 + 时差） | `LJ2/a.A0`、`GpsAssistDataActivity.p2` |

> 合计 **55 行** = 官方 68 个 − 我们在用的 13 个（`SPEC-round61.md` §8 写的"53"少算了 2 个，见 §9.2 第 4 条）。
> 其中第 29/30 行（`get_/set_camprop`）属于第 61 轮已定性的"遥控单参数通道"——我们**不用**它，但既然在未用清单里，参数一并列出。

**`set_camprop.cgi` 的 `propname` 全表（实：逐条来自 dis.txt 的 URL 字面量）**

| propname | 干什么（名字直译，**用途未逐条核**） | propname | 干什么 |
|---|---|---|---|
| `qualitymovie` | 视频画质 | `colortone` | 色彩（`ifinish` / `natural`） |
| `shutspeedvalue` | 快门速度值 | `colorphase` | 色调相位 |
| `takemode` | 拍摄模式（多处在用） | `expcomp` | 曝光补偿 |
| `exposemovie` | 视频曝光 | `SceneSub` | 场景子项 |
| `focalvalue` | 焦距值 | `wbvalue` | 白平衡值 |
| `isospeedvalue` | ISO 值 | `drivemode` | 驱动模式（`selftimer` / `supermacro`） |
| `supermacrosub` | 超微距子项 | （动态名） | `?com=set&propname=` + 运行时拼的名字 |

---

## 5. 顺手查出来的 5 条（对**我们**有用的地方）

| # | 发现 | 对我们的意义 |
|---|---|---|
| ① | **纯 HTTP 快门链路**：`switch_cammode.cgi?mode=shutter` → `exec_shutter.cgi?com=1stpush/1strelease/2ndpush/2ndrelease/1st2ndpush/2nd1strelease`（`RemoconReleaseActivity.x2` 就是这么写的；BLE 版是另一个 Activity） | 我们的 App 已经有 `switch_cammode`（写 MySet 用它）。**"手机当快门线（半按对焦 / 全按）"可能不需要 BLE**——这是**新功能候选**（要不要做是产品问题，见 §8） |
| ② | `get_commandlist.cgi` → 相机把"支持哪些命令"列表返回给 App，之后每次请求前用 `Lc2/k;.c(url)` 查白名单 | 我们可以用它**探测机型能力**（例如判断这台相机支不支持某一个 CGI），而不是"试了才知道" |
| ③ | `set_timeout.cgi?timeoutsec=1800` —— 官方**每次连上都把待机超时设成 1800 秒**。**补查（2026-09-28，需求方追问后读的方法体）**：官方为它专门建了个**定时器类** `I2/i`（不是随便发一次）—— `I2/i;.i()` 里：① 先 `OIShareApplication.D()→Lc2/k;.c("set_timeout")` **查命令表**（这台相机支持这条吗）② 再看 `J2/d.n()` 是不是 `playmodeonly_private`（**只在"播放/传输模式"下发**）③ 若"正在通信"就**先推迟**（日志 `.setTimeout 通信中なので先送り` + `Handler.sendEmptyMessageDelayed`）④ 否则 `http://192.168.0.10/set_timeout.cgi?timeoutsec=1800`；类里还有个 **`b=600`（秒）**字段用于下一轮（≈每 10 分钟续一次）。 | 我们"写入配方"/"备份"中途掉线（相机进待机）**可能**有救：连上后（并可每约 10 分钟续一次）把它设长。**改动很小 —— 页面 `req('set_timeout.cgi?timeoutsec=1800')` 就能发**（走已有 `camGetAsync`，**不必改 Java**）。⚠️ 但要照官方那两条前置（先在命令表里确认支持、只在传输模式下发），别在不该发的时候发；续期期间相机会更费电，所以只在"正在操作"时才续。**"到底有没有用"必须真机验证**（§8 候选③） |
| ④ | 取景链路 = **HTTP 协商端口 + UDP 收 JPEG 流**（`ready_moviestream` 给端口，`videocodec=jpeg&videoquality=vga&videorate=10`，音频 `pcm 24k 单声道 TCP`） | 想在我们 App 里做"实时取景"的话，协议已经清楚（但要在 WebView 里收 UDP 得走原生，工程量大） |
| ⑤ | 传图全家共用 `DIR=`（目录路径，需 `URLEncoder.encode`），列表/缩略图/预览/缩放/EXIF 都是同一套 | 以后做"从相机取图"只需实现一个 `DIR` 概念 + 几个 GET，**不用逐个猜参数** |

---

## 6. 验收标准（可逐条跑）

```bash
python official_app/oi_cgi.py --list | tail -1        # 共 68 个；没用过的 55 个
python official_app/oi_cgi.py --all > official_app/cgi_table.txt
rg -c '^=== ' official_app/cgi_table.txt              # 应 = 55（53 + get_camprop 那族带出的重复计数说明见下表）
rg -c '索引里找不到' official_app/cgi_table.txt      # 应 = 0（每个 CGI 都定位到了引用它的方法）
python official_app/oi_cgi.py --cgi get_imglist       # 抽一个核对：URL 字面量 + 引用方法
python official_app/oi_cgi.py --body 'Lc2/s;' a       # 核对 §3 的"c2/s 只是日志"
python scripts/dv_r65.py                              # 本轮探针（见 §7）
```

**逐条验收点**
1. 工具能跑：`--list` / `--cgi` / `--all` / `--keys` / `--body` 都正常（`--raw` 才有大输出）。
2. `--all` 覆盖 **55 个**"没碰过的" CGI，且**每一个都能定位到引用它的方法**（0 个"索引里找不到"）；
   `dv_r65` 还会**逐个核对**"§4 表里提到的 CGI 名 == 工具算出来的未用名单"（不许漏、不许编）。
3. 表里**每一行的参数名都逐字来自 dis.txt 的 URL 字面量**（`dv_r65` 会把表里的 URL 模板与 dis.txt 比对）。
4. §3 的"共享助手"结论可复现（`--body` 直接看得到 `Log.d` / `isLoggable` / `ArrayList` 比较）。
5. **App 与 APK 零改动**：`app/base.html` md5 仍是 `3692725c82e022d643b69c465d77f474`；`apk/` 下没有新构建产物。

---

## 7. 不涉及 / 未读（显式声明，不猜）

- **未读**：55 个 CGI 的**响应体格式**（成功/失败的 XML/JSON 结构、结果码）—— 本表只覆盖"**请求怎么发、带什么参数**"。
  要做某个功能时，再按需读它对应的解析代码（`--body` 一步到位）。
- **未读**：`exec_takemotion` / `exec_takemisc` 里 `point=`、`upperlimit=`、`exposuremin=` 的**取值域**
  （只有字面量 `upperlimit=200`、`limitter=-1` 是实的，其它是"传进来的整数"，没读上限）。
- **已列名、未读取值**：`set_camprop.cgi` 的 `propname` 全表已列出（§4.3），但每个 propname 的**取值域**与**XML body 结构**未读（20 处调用点，第 61 轮已把它归为"官方遥控用的单参数通道"，我们不用它）。
- **不做**：BLE 那条线（第 58~62 轮已完成）。
- **不改**：`app/base.html`、`MainActivity.java`、`AndroidManifest.xml`、任何构建脚本。

---

## 8. 结论 / 下一轮候选

**结论**：55 个 CGI 的"请求侧"已经**全部摸清** —— 每个都能指出「URL 模板 + 参数名 + 官方哪个类在用」。
对"连接手机 + 配对 + 写配方"这条主线**仍然没有新增必需项**（第 61 轮的结论不变）；
新增的是**覆盖面**：以后要做取图 / 遥控 / 固件升级，不用再从零读 130 MB。

**下一轮候选（按性价比）**：

| # | 候选 | 为什么 / 前置 |
|---|---|---|
| ① | **真机验证第 62/64 轮的连接改动**（BSSID + 扫码源 + 蓝牙唤醒） | 只有真机能确认；**必须先问需求方**（要拿 OM-3 配合） |
| ② | **「相机当快门线」**（纯 HTTP：`switch_cammode?mode=shutter` + `exec_shutter?com=`） | §5① 挖出来的**新功能**，协议已清楚；**是产品选择题**（要不要做、UI 放哪） |
| ③ | **连上后 `set_timeout?timeoutsec=1800`** | 一行改动就能减少"写入中途掉线"；风险低、收益明确 |
| ④ | **camprop「单项实时改参」**（原 HANDOVER 候选④） | 产品选择题；与 MySet 通道的关系要先定（第 61 轮 §2.4③） |
| ⑤ | 取图（`get_thumbnail` / `get_resizeimg` 一族） | 工程量大（列表 UI + 下载 + 保存到相册），只在需求方明确要"从相机取图"时做 |

---

## 9. 验收结果 / 差异分析

（**回填**：逐条验收结果 + 设计与实现的差异。）

### 9.1 逐条验收（2026-09-28 实跑）

| # | 验收点 | 结果 |
|---|---|---|
| 1 | `--list`：68 个 `.cgi`，未用 **55** 个 | ✅（`共 68 个；其中我们没碰过的 55 个`） |
| 2 | `--all` 覆盖全部未用 CGI，0 个"索引里找不到" | ✅（55 个块） |
| 3 | 每个 CGI 的引用方法都定位到（类/方法/行号） | ✅（如 `get_imglist.cgi` → `ImageTransListActivity.S7 L1594660-1594709`） |
| 4 | **表里参数逐字来自 dis.txt 字面量**（不许编） | ✅ `dv_r65` 从 §4 抠出 **147 个**参数/取值/CGI 名片段，**147/147 全部命中**（第一版有 5 个红 —— 见 §9.2 第 4b 条） |
| 5 | **覆盖核对**：表里的 CGI 名 == 工具算出的未用名单 | ✅ 55 == 55，**不漏不多**（第一版漏了 `set_camprop.cgi` —— §9.2 第 4c 条） |
| 6 | §3 助手结论可复现 | ✅ 三条都跑过 `--body`；**顺手纠正**一个容易误读的点：`c2/s.g()/h()` 是 `Log.isLoggable`，**不是**"相机在不在线" |
| 7 | App/APK 零改动 | ✅ `app/base.html` md5 = `3692725c82e022d643b69c465d77f474`（与第 64 轮产物逐位相同）；本轮**没有**构建产物 |
| 8 | 本轮探针 | ✅ **`dv_r65` 15/15**（A 段 3 条 + B 段 7 条 + C 段 3 条 + D 段 2 条） |
| 9 | 产物文件就位 | ✅ `official_app/oi_cgi.py`（工具）、`official_app/cgi_table.txt`（`--all` 原始输出 55 KB，可重新生成） |

### 9.2 差异分析（规格 vs 实现，差异都落在"改代码或改规格"）

| # | 规格原定 | 实际 | 结论 |
|---|---|---|---|
| 1 | §1 写"输出 = 工具 + `cgi_table.txt` + 本规格" | 工具加了一个**规格里没提**的能力：`--body`（直接看方法体原文） | **改规格（已改）**：§2 用法里补上 `--body`。没它就核不了"`c2/s` 只是日志"这条关键判读。 |
| 2 | 原计划"逐个人工读 URL" | 实际做法是**先让工具把"谁在调 + 参数键 + 原文上下文"抽出来**，再人工判读用途 | **改规格（已改）**：§2 明确"证据强度分级（实/推/待）"，用途一律标"推"，不冒充实证。 |
| 3 | 没有预料到 `--cgi` 的"调用"列会被**日志方法**刷屏 | 判读时差点把 `Lc2/s;.a` 当成 HTTP 调用 | **改代码 + 改规格**：工具加 `--body` 便于查证；规格 §3 单列"共享助手速查"并写明这个坑。 |
| 4 | 沿用 `SPEC-round61.md` §8 的"53 个没碰过" | 工具按名字算出来是 **55**：68 − **13**。差 2 的原因是第 61 轮把我们自己的两个名字（`getmysetdata` / `get_mysetdata`，**dis.txt 里根本没有这两个 `.cgi`**）也算进了"在用 15 个" | **改规格（已改）**：全文订正为 55，并在 `SPEC-round61.md` §8 顶部加了勘误指针。**不是本轮新错，但本轮把它抓出来了**（"68 − 15 = 53"这个算式从一开始就多减了 2） |
| 4b | §4 里我把 5 个 URL 写成了**拼接后的整体**（`?DIR=&size=` 等） | `dv_r65` 逐条比对时报 5 条红（"编的会是：`?DIR=&size=`、`?audiomethod=…`…"） | **改规格（已改）**：拆成逐个字面量（`?DIR=` + `&size=`），并在 §2 写明"字面量可能是拼起来的、本表不伪装成整体"。**这是探针第一次真的抓到"表里有编的成分"** |
| 4c | §4 的"55 vs 54 行" | 探针做**覆盖核对**（表里 CGI 名 vs 工具算出的未用名单）→ 发现漏了 `set_camprop.cgi` | **改规格（已改）**：补上 §4.3 的 `set_camprop` 行 + propname 全表；§7 的"不做"改成"已列名、未读取值" |
| 5 | 原以为"53 个都要读方法体" | 实际 90% 只需 URL 字面量（工具已抽好），方法体只在少数几个（`Lc2/k`、`Lc2/s`）要读 | **改规格（已改）**：§7 明确"响应格式未读"，并说明按需读的方法（`--body`）。**不假装读完了。** |

### 9.3 遗留

1. 每条 CGI 的**响应格式/结果码**未读（显式声明，见 §7）；需要时用 `--body` 逐个补。
2. `--keys` 抽出的"参数键候选"里混着格式名/日志串（`NOISE` 名单只挡了一部分）—— 表里**没有**直接用它们，
   只用了 URL 字面量（实的），所以不影响结论。
3. **探针 D 段的"被测文件"在第 67 轮被纠正**（跟第 63 轮那次同一类）：`dv_r65` 原来断言"当前 `app/base.html` md5 还是第 64 轮那个"，
   第 67 轮正当改了页面（连接链）→ 必然红。改成拿 **`app/base.before_r67.html`**（第 64 轮产物、也正是第 65/66 两轮没动过的状态）来对照，
   **判据没放松**（仍是"md5 逐位相同"），只是把被测文件换成第 65 轮当时那一版。→ 实测 16/16。
