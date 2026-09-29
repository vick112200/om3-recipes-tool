# AGENTS.md — 本项目每次会话自动加载

> 项目：**OM-3 色彩配方手册** · 工作目录 `D:\workspace\om3-handbook`
> 本文件是「进门须知」。**详细的当前状态在 `HANDOVER.md`，详细的工程说明在 `README.md`。**
>
> ⚠️ 仓库与本地之别：GitHub 上只有源码 + 工具 + 四份门面文档（README / AGENTS / TEST-camera / OPEN-ITEMS）；
> `HANDOVER.md` 和 `SPEC-round*.md` 是**本地开发档案**（`.gitignore` 里排除了，文件都在本机，只是不上传）。
> 所以下面的「先读 HANDOVER 顶部」这类规矩，在本机照旧执行。

---

## 0. 开工第一件事（强制，别跳）

**先读 `HANDOVER.md` 最上面那段 `# ▶▶▶ 最新（… · 第 NN 轮，接手请先看这段）`。**

- 该文件按轮次**倒序**堆积：最上面 = 最新，往下是历史。**别从中间读**。
- 里面写着：当前版本号与产物 md5、本轮做了什么、遗留清单、下一轮候选。
- 需要细节时再看对应规格 `SPEC-roundNN.md`。
- **顺手读 `OPEN-ITEMS.md`（待验证 / 待决策清单）** —— 这是「我在电脑上没法确认、必须靠真机或靠需求方拍板」的事的集中清单。
  **每轮只要碰巧能推进它，就顺手推进**（加个按钮、回填结论），不要留到「以后」。
  2026-09-28 需求方点破过一次：「你自己制定的计划怎么忘了呢」—— 根因就是这些项散在各轮 `SPEC` 的「遗留」里、
  每轮被写成一句笼统的「真机验证」然后冲掉。`scripts/check_open.py` 现在会强制它们**必须有点得到的入口**。
- 需要细节时再看对应规格 `SPEC-roundNN.md`。

**当前基线**（读到这里时请以 HANDOVER 顶部为准，下面可能已过时）：
手册 App **v3.45（已出包，桌面 `om3 recipes tool.apk`）**；`app/base.html` md5 `7f3ab915f99036ec791a911d4d3f6f65`；
`MainActivity.java` md5 `02e31ff0735376446e0709ce351f77a8`；
最新一轮 = **第 93–94 轮**（需求方：**改名 `om3 recipes tool`** + 右上角**打赏按钮展示收款码**；
随后「**不用嵌二维码，这个功能先隐藏，后面再做**」→ 按钮加 `style="display:none"`（代码/`set_donate.py` 全留），
以后想开：去掉那行 style + `python scripts/set_donate.py 收款码.png` + 出包）→ `SPEC-round93.md`；
第 92 轮 =（需求方决定「**不要蓝牙打开 wifi 了，以后都手动打开**，连接页多余的去掉」→
「蓝牙手动控制台」+「蓝牙工具（高级）」卡**整块搬到测试页**（诊断用；`data-tv`/`id` 一个没动），
② 改「唤醒相机（電源ON；**不会**开相机 Wi-Fi）」，连接页只留 A/B/C 对号入座 + 连接相机 + 扫码连接）
→ `SPEC-round92.md`；
第 91 轮 =（v3.40 真机日志：**相机其实答了**（`0402040f0101011200`，通道 0F/子命令 01/**结果码 1**），
而且**每一帧都有回执** `05 <seq> 00 00 00`；我们没认出来是因为解码器只认"空格分隔"的十六进制、真机是**连写**
→ 新增 `bleBytes()` 并接到 decode/resultCode/scanTlv 三处 + 认回执包。硬结论：帧到相机、相机答 `0x0F01`，
但**不答 `0x1D01{0x02}`**（官方判据下同样算失败）→ `SPEC-round91.md`；
第 90 轮 =（需求方"相机显示蓝牙已连接" → 只剩**口令**这一变量：官方 `BlePowOnActivity.x2()` 连蓝牙就带
`str.blePass`、`e$d.run` 的 `0x0C02` 跑在 `e$e`（電源ON）之前；我们一直是"蓝牙口令：没存" → 控制台加按钮
**`data-tv="cv-pass"`「① 填蓝牙口令」**：自绘弹窗 → 记住 → **按官方顺序重发**（有口令时实测三条帧：
`0C 01 02` → `0F 01 01 02` → `1D 01 01 02`））→ `SPEC-round90.md`；
第 89 轮 =（真机 v3.38 06:23 日志：**那一轮那条新命令根本没发出去** —— ①的"只连"链在跑时点②，
`camBleAuto` 见"已经在连了"直接 return（②的意图丢了），`lost`(133) 又清了 `__om3bleConnOnly`、重试按①的参数
写了 `__om3bleAutoWake=false` → `svc` 回调**两个分支都不走** → 一帧没发还把人挡住 → v3.39 让 ② 登记意图
（`__om3cvWantWake`）+ 能自愈补发 + 掉线收口）→ `SPEC-round89.md`；
第 86–88 轮 =（真机 v3.37 日志：相机**会回话**（`04 02 04 0F 01 01 01 12 00` = 结果码 1），
我们解码器写死首字节 `0x01` 认不出 → r86 改成按"校验和 + 通道/子命令"匹配，② 不再谎报"相机没回应答"；
需求方纠正「官方点**导入图片**时相机会自动开 Wi-Fi」→ 反汇编找到
`BlePowOnActivity$c.run → M2/b.M(2,10000) → cmd 0x1D01`（帧 `01 <seq> 04 1D 01 01 02 21 00`，**回 0 才算成功**，
且 `x2()` 连蓝牙时就带 `str.blePass` 口令）→ r88 把 ② 的序列补成
`[口令认证 0x0C02] → 電源ON 0x0F01 → リモコンモード 0x1D01{0x02}`；第 87 轮那句"官方也没法开 Wi-Fi"**已作废**）
→ `SPEC-round86.md`；
上一轮 = **第 83 轮**（真机日志 → 修 NaN / 窗口白开 / 判据落到"连一次"）→ `SPEC-round83.md`；
第 82 轮 = **真机日志 → 修"扫描永远慢一拍" + ②抢结论** → `SPEC-round82.md`；
第 81 轮 = **手动控制台**（状态区 + 四个按钮，②才发「電源ON」）→ `SPEC-round81.md`；
第 80 轮·上 = **删掉"自动唤醒相机 Wi-Fi"** → `SPEC-round80-plan.md`；
第 79 轮 = **修"点了没啥反应"** —— 第 74 轮把「扫码连接」放回来时**漏接功能**；
探针补上"入口点了必须真的有效果"这类断言）→ `SPEC-round79.md`；
第 78 轮 = **真机日志 → 修两个真 bug**（`Binding socket … EPERM` 断链、"像相机的 0 个"误判）→ `SPEC-round78.md`；
第 77 轮 = **测试页「不确定的事」9 条按钮**（把历轮"待真机"的项变成可点的自检）→ `SPEC-round77.md`；
第 76 轮 = **连接相机页把「怎么操作」写成三步 + 按钮挪到第一屏**（原来按钮在 y=737）→ `SPEC-round76.md`；
上一轮 = 第 75 轮（**测试页加「分享日志」按钮**，手机上一键发我）→ `SPEC-round75.md`；
第 74 轮 = **扫码放回来（往后放）** + 连接推演发现的两处（**蓝牙跑不起来别白等 10 秒**、**热点探测节流 5 秒**）+ **日志带头 + `logs/` 交接流程** → `SPEC-round74.md`。
**真机测试单 `TEST-camera.md`；日志丢 `logs/`，`scripts/read_log.py` 自动分诊。**
推演/诊断工具（都留着）：`sim_connect.py`（连接流程推演器）、`map_paneD.py`、`dump_text.py`、`dv_rect.py`。
第 73 轮 = （点「测试页」被弹回配方合集：页签转发漏 T + `#paneT` 嵌在 `#paneD` 里）→ `SPEC-round73.md`；
第 72 轮 = 搜索按钮文字被 `textContent` 抹掉；第 71 轮 = 搜索「留一个字」根治；第 70 轮 = 搜索 3 处毛病 + ☰ 菜单分层；
第 69 轮 = 弹窗/浮层体检；第 68 轮 = 独立测试页；第 67 轮 = 连接链复捋；第 65 轮 = 55 个未用 `.cgi`；第 64 轮 = BSSID。

**加新 id 的规矩（第 68 轮起）**：加新 id 是允许的，但 ① 每个**老 id 一个都不能少**（老探针钉的是这条）
② **新增的那一组必须在当轮规格里逐个列出**，并由当轮探针断言"新增集合**完全等于**那张表"（多一个少一个都红）。

---

## 1. 这个项目是什么

把 70+ 条胶片色彩配方做成**单页 HTML 手册**（`app/base.html`，约 3.8 MB，图片内嵌），
再套一个 Android 壳打成 APK 供手机离线看。目录结构见 `README.md`。

两条**互不相干**的产物线：
| 线 | 目录 | 说明 |
|---|---|---|
| 手册 App（主线） | `app/` `apk/` `scripts/` | 改页面 → 跑探针 → 出 APK |
| 官方 App 逆向（支线） | `official_app/` | 分析 OI.Share 的连接逻辑，见 §5 |

---

## 2. 硬规矩（违反会返工）

1. **`app/base.html` 是唯一真源**，所有页面改动只改它。
   改前先留回退点：`cp app/base.html app/base.before_<名字>.html`。
2. 改页面**用生成脚本改**（`scripts/gen_rNN.py` 那种：幂等、可重跑、带断言），
   不要手改 3.8 MB 的文件。**禁止**用「正则替换文案」而不加结构断言（以前踩过：吃掉 `">`、`\1` 被当控制字符）。
3. 每个功能点写进 `SPEC-roundNN.md`：功能点六要素 + 「必须显式声明清单」（不涉及的项也要写"不涉及"）
   + 可逐条验证的验收标准；末尾补**验收结果 + 设计与实现的差异分析**（差异要**改代码或改规格**，不许只记录）。
4. 改完**必须**跑（顺序见 README「改代码的固定流程」）：
   `python scripts/check_syntax.py` → `python scripts/live_check.py`（**错误数必须 0**）→ 相关 `scripts/dv_rNN.py` 探针（**全绿**）。
5. 探针**不许改小/改松来凑绿**。数字对不上先查根因（"改了却没效果"多半是选错了容器/类，如 `.oslot` 要改 `.osbody`）。
6. `apk/om3.jks` **务必别删别改**（丢了用户无法覆盖安装）；`app/base.before_*.html` 别删。
7. 出包顺序坑：`mkasset.py` 会用 `app/index.html` **覆盖** `apk/assets/index.html`，
   所以版本徽标必须由 `build.sh` 里的 `bumpver.py` **最后**写（必须排在 mkasset 之后）。版本号规则见 README。

---

## 3. 构建 / 发布（三步）

见 `README.md`「构建流程（三步）」。要点：
```bash
cp app/base.html app/index.html && python apk/mkasset.py   # ① 同步并注入 __OM3_APP__
cd apk && bash build.sh                                    # ② → apk/build/om3.apk
cp apk/build/om3.apk "/c/Users/82302/Desktop/OM-3色彩配方手册.apk"   # ③ 发布
```

---

## 4. 验收脚本速查

| 脚本 | 用途 |
|---|---|
| `scripts/check_syntax.py` | 抽全部内联 `<script>` 给 node 做语法检查 |
| `scripts/live_check.py` | 抓加载期运行时报错。**不带 `__OM3_APP__=1`，不能用它数按钮**（会是 0 个的假象） |
| `scripts/check_app.py` | 带 `__OM3_APP__=1` 的「四数验收」；也可验最终产物路径 |
| `scripts/verify_all.py` | 无头浏览器逐条验页签/底栏/置灰/搜索 |
| `scripts/dv_rNN.py` | **每轮一个的回归探针**（全绿才算完） |
| `scripts/audit_buttons.py` / `audit_deadclicks.py` | **找"点了没反应"的按钮**：前者静态筛"没人引用"，后者无头逐个点、看有没有可观察变化 |
| `scripts/check_open.py` | 待验证清单守卫：`OPEN-ITEMS.md` 里标「未验」的必须**有能点的验证入口**，页面里每个 `uv-*` 按钮必须有出处（专治「忘了自己列过的事」） |
| `scripts/dv_geom.py` / `dv_shot.py` | 量尺寸 / 截图。**布局变化别靠肉眼判断** |

四数基准会随版本变，**以 README 最新记录为准**。

---

## 5. 官方 App 逆向（支线，`official_app/`）

分析 `om share.apk`（OI.Share，124.9 MB）「连接手机」的操作逻辑。

- **`oi_index.py` + `oi_index.json`**：结构索引（77003 个方法，含整数/字符串/调用）。
  直接查，**不用重建**：`--cls 子串` / `--str 0x6801` / `--find 0x69` / `--call 子串` / `--greps 子串` / `--big 200`
- `oi_graph.py`（`--body 方法名` 打方法体）、`oi_mine.py`、`find_str.py`
- **`arsc.py`（第 59 轮新增）**：纯 Python 解包 `om share.apk` 里的 `resources.arsc`（本机没有 aapt/java）。
  `--list` / `--name 资源名子串` / `--value 值子串` / `--type string` / `--locale ja` / `--stats`
- **`oi_switch.py`（第 60 轮新增）**：解 `packed/sparse-switch` 的**键值表**（读 dex 字节；
  dexdump 的 payload 行会 `...` 截断，`oi_index.py` 里看不到这些 `#int`，所以「34=PASSCODE_ERROR」这类映射要靠它）。
  `--cls 's2/b$g;' --meth H` / `--lines A B` / `--key 34`
- **`oi_cgi.py`（第 65 轮新增）**：按 **CGI 名**抽"谁在调 + URL 参数 + 方法体"（68 个 `.cgi` 全覆盖）。
  `--list`（名单 + 我们有没有在用）/ `--cgi get_imglist [--raw]` / `--all`（一次全出，≈55 KB）/
  `--body 'Lc2/s;' a`（看某个方法体原文）/ `--keys`。**结论表见 `SPEC-round65.md`**，原始输出见 `official_app/cgi_table.txt`。
  ⚠️ `--cgi` 输出里的"调用"列多数是**日志**（`Lc2/s;.a/b/d/e` = Log.d/w/e/i；`s.g()/h()` = `Log.isLoggable`）
  —— 别把它当成 HTTP 调用；真正的请求在 `Lc2/k;.c/d/f` 或 `java.net.HttpURLConnection`。
- 反汇编源：**`official_app/dis.txt`（130 MB，随工程走）**；`official_app/classes.dex` 是它对应的 dex。
  上面几个工具都**优先读工程内**这份、找不到才退回 `%TEMP%\oishare\`。
  ⚠️ dexdump 的字符串常量用**双引号**（`const-string v1, "x"`），写正则别只匹配单引号。
  ⚠️ `--call` 的匹配串要用**去掉分号**的写法（索引里存的是 `Lcom/…/e.G(…)`，不是 `…e;.G(…)`）。
  （重新生成：`dexdump -d classes.dex > dis.txt`；两个文件 md5 见 `SPEC-round58.md` §9。）
- 已得结论：`SPEC-round58.md`（骨架）+ `SPEC-round59.md`（opcode/结果码/UUID/帧格式勘误）
  + `SPEC-round60.md`（检测码值/传输层方法/配对二维码链路）
  + **`SPEC-round61.md`（状态位语义/QR 字段语义/相机 DB schema，先看这份）**
  + **`SPEC-round65.md`（55 个未用 `.cgi` 的参数表 —— 要做取图/遥控/固件升级时先看这份）**；
  **注意 `SPEC-round61.md` §3 勘误了第 58/59/60 轮与本文件初稿几处**（二维码**确实**带 BLE 配对码；
  `f$a.g` 是 netId 不是安全类型；第 58 轮把 `set_camprop/switch_cammode`（HTTP CGI）和 BLE 并列为"最小闭环"是混搭）；
  **§8 的数字另有勘误**（"没用过的 53 个"应为 **55**，推导见 `SPEC-round65.md` §9.2）；
  待办见 `SPEC-round61.md` §5 —— **静态侧已清空**（`.cgi` 的"请求侧"第 65 轮也补完了，只剩"响应体格式"没读），
  剩下的**都要真机**（无设备做不了）。
  ✅ 手册 App 的「写配方进相机」走 **MySet 整包通道、能正常用**（`get_camprop/set_camprop` 是官方遥控用的
  单参数通道，不冲突也不替代）。那句过时说反的警告已由第 63 轮改掉（见 `SPEC-round63.md`）。

---

## 6. 协作风格（需求方偏好，照做）

- 用**中文**回复。
- **先做后问**：能自己查证、自己决定的别反复确认；只有**危险或不可逆**的才停下来问。
- 结论**落到文件**（`SPEC-roundNN.md` / `HANDOVER.md`），别只留在对话里 —— 上下文会满，
  历史上有好几轮是「挖到一半超上下文」断掉的。
- **长任务分段开新会话**：一轮做完就把结论写进 `HANDOVER.md` 顶部，再开新一轮（`/new`）。
- 遵循 `ai-dev-guardrails`（规格 → 实施 → 验收三阶段）。**纯文案/样式/常量改动可走轻流程**（只走读规范、执行、验证）。
