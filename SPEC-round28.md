# SPEC-round28：写入顺序按官方 APK 改正 + 自检不再把 datasize=0 判成"一致"（v2.14）

## 0. 起因

### 0.1 用户真机日志（2026-09-24，v2.13）

```
2. get_mysetbackupstate.cgi          → <result>ok</result><status>generalerror</status>
3. get_mysetdatasize.cgi?kind=current → <datasize>0</datasize>   ← 以前这里是 55418
5. get_mysetrestorestate.cgi（还没碰 restore）→ status=generalerror
⑥ request_restoremysetdata.cgi?action=restore → HTTP 200 但 <result>generalerror</result>
```

上一轮（v2.13）的结论是"相机侧数据损坏，app 修不了"，并把希望放在 `kind=factory` 上。

### 0.2 本轮先把官方 APK 重新读了一遍（`om share.apk`，反汇编产物在临时目录）

写入实现是 **`com.omdigitalsolutions.oishare.settings.myset.a`**（一个 AsyncTask，4 个匿名回调
`a$a`~`a$d`，每个回调的日志字符串就写着它对应哪个 cgi）。按**调用链**（不是方法定义顺序）读出来：

| 谁调谁 | 方法 | 请求 | 证据 |
|---|---|---|---|
| `doInBackground` → | `n(int size, InputStream)` | `set_mysetdatasize.cgi?size=N` | `a.n` 在 `k()`（=doInBackground）里被**唯一**调用，第一件事就是它 |
| `a$a.onReceive`（setsize 的应答）→ | `b(task, total, stream)` → `o()` | `send_partialmysetdata.cgi?offset=&size=` | `a$a.c` 判 `result==ok` 后调 `a.b`；`o()` 里 `remaining = total - task.b`（total 就是 n() 收到的那个整数） |
| `a$b.onReceive`（每块的应答） | 未传完 → 再调 `o()`；**传完了** → `i()` | `request_restoremysetdata.cgi?action=restore` | `a$b.c` 里 `if (total == task.b + 缓冲长度) i(task)`；`i()` 是 `l()` 的唯一调用点，而 `l()` 里就是 restore 那个 URL |
| `a$c.onReceive`（restore 的应答） | `result==ok` → `j()` | `get_mysetrestorestate.cgi` | `a$c.c`：`generalerror`→错误码 4、`invalidparameter`→错误码 3、`ok`→`a.j()`（=轮询） |
| `a$d.onReceive`（轮询的应答） | `status=busy` → 再 `j()`；就绪 → 结束 | UI 侧之后才 `exec_reboot.cgi` | `a$d.c`：`busy`→重试、`lowbattery`→错误码 5、`generalerror/fail`→错误码 6、其它→成功码 1；`exec_reboot` 在 `settings.myset.c.K2()` |

结论（**官方真实顺序**）：

```
set_mysetdatasize（声明大小）→ send_partialmysetdata ×N（分块传完）→ request_restoremysetdata
（请求恢复）→ get_mysetrestorestate（轮询，status=busy 就再问）→ 调用方 exec_reboot
```

而 HANDOVER / `SPEC-round25` / `SPEC-round26` 里记的"**restore → 轮询 → 声明大小 → 传**"
是上一轮回读反了（大概是照 `l/m/n/o` 的**定义顺序**猜的调用顺序），我们 app 一直照着那个反序做：
**在还没暂存任何数据时就要求相机 restore** —— 相机回 `generalerror` 完全说得通。

同时确认（推翻上一轮的两个猜测）：

- `kind=factory`：官方**从不使用**（`settings.myset.a` 里没有 `factory` 字符串；只有读路径 `settings.myset.b`
  用 `kind=current`；`MysetInfoData` 只定义 `MYSET_DATA_TYPE_CURRENT / MYSET_DATA_TYPE_MYSET1..4`）。
  ⇒ 这条线索**关闭**，相机能力表里那个 `factory` 官方也没用。
- 官方在这条路上**不切维护模式**（`switch_cammode` 只出现在 t2/a、t2/o、ConnectCompleteActivity、Firmup*、
  Remocon* 里）；也**不查** `get_mysetbackupstate`（那是读路径/固件升级路径用的）。
- 官方的 `<result>` / `<status>` 取值集合：`ok` / `generalerror` / `invalidparameter` / `busy` / `lowbattery` / `fail`。
  我们对 `result` 的判读与官方一致（不是 ok 就算失败）。

## 1. 规格（要改成什么）

### 1.1 模块 → 子模块 → 功能点

| 编号 | 功能点 | 输入 | 输出 | 前置 | 后置 | 业务规则 | 验收标准 |
|---|---|---|---|---|---|---|---|
| F1 | 写入顺序 | 目标档位、槽号、配方 | 相机应用后的 my-set | 已连相机 | 相机重启 | **声明大小 → 分块传完 → restore → 轮询 → 重启**；任一步失败就中止且**不往下走** | `dv_writeproto` E 的顺序断言 |
| F2 | 开工前清通道 | 无 | 通道干净（或明确警告） | 已进维护模式、**尚未上传任何字节** | 继续声明大小 | 先问 `get_mysetrestorestate`；相机**明确报错**才 `mode=play`→`maintenance`；重置后仍报错只 warn、**不拦着写** | `dv_writeproto` B/F |
| F3 | 上传前就绪轮询 | 无 | 无 | 声明大小成功 | 每块上传 | **只在传完之后**才 restore；**不**在开工前 restore | `dv_writeproto` E/G |
| F4 | 上传完整性 | 本地字节 | 相机收到的字节 | 声明大小成功 | 全部传完才进 F5 | 每块最多 3 次；失败**绝不推进 offset**；没传完**绝不** restore | `dv_writeproto` G、`dv_write` A/B/C |
| F5 | restore 判读 | 相机应答 | 是否应用成功 | 数据已全部传完 | 轮询或中止 | 只认 `<result>ok</result>`；拒绝 → 报失败 + `关机再开机` 建议 + 自检入口，**不重启** | `dv_writeproto` A |
| F6 | 就绪轮询 | 相机应答 | 就绪/失败 | restore 成功 | 读回 + 重启 | `busy` → 400ms 再问；`lowbattery` → 直接失败（官方单列的错误码）；`generalerror/fail/invalidparameter` → 失败；`result=ok` 且无 status → 就绪；认不出的状态等满后按"状态不明确"继续（不卡死） | `dv_writeproto` D/F/G |
| F7 | 自检 datasize 判定 | `get_mysetdatasize?kind=current` | 日志结论 | 已连相机 | — | **0 与"没报"必须分开**；`0` = 相机里那份 my-set 是空的 → 明确报错 + 给修理路线，并写进自检结论 | 静态检查 + 真机日志 |
| F8 | 自检"单独试 restore"的口径 | 相机应答 | 日志 | 自检跑到最后 | — | 单独一次 restore 被拒**不再**判成"相机卡住/坏了"（没有数据可恢复时被拒是正常的） | 静态检查 |

### 1.2 必须显式声明清单（逐项，含"不涉及"）

| 项 | 本轮结论 |
|---|---|
| 并发 | **不涉及**：写入是单条链路（`runTask` 串行），本轮没加并发；两次写入同时点仍由既有 `runTask` 挡住 |
| 幂等 | **涉及**：分块可重发（同 offset 重发幂等，保留原 3 次重试）；**"重置通道"不幂等到可以放在上传之后** —— 它会清掉暂存数据，所以**必须**放在上传前 |
| 权限 | **不涉及**：不新增权限（`CHANGE_NETWORK_STATE` 在 v2.12 已修） |
| 事务/原子性 | **涉及**：声明大小 → 分块 → restore 是一个整体；任一步失败即中止，**绝不**只做一半就重启（否则相机应用半份数据） |
| 边界值 | **涉及**：`datasize=0`、`datasize` 缺失、`size` 与本地不一致、0 字节数据、单块（<4096）数据 |
| 超时/重试 | **涉及**：分块 20s×3；restore 15s（**只试一次**）；轮询 30×400ms；`busy` 不计数（继续轮询） |
| 异步 | **涉及**：全链路 await；`prog` 回调异常不吞（沿用既有）；不新增未接 Promise 的调用 |
| 状态机 | **涉及**：把"先 restore"改成"后 restore"；`restoreHandshake`（被拒 → 重置通道 → 再 restore）**删除**，换成"上传前 `prepareWriteChannel`"（见 §3 差异分析） |
| 性能 | **不涉及**：仍是 4096 字节/块，请求数不变 |
| 兼容性 | **涉及**：`v2.13` 写入流程的用户可见行为变化只在**顺序**与**失败文案**；日志步骤号重排（①..⑪ 含义变化，HANDOVER 已更新） |
| 数据迁移 | **不涉及**：不改任何本地数据结构（`pendSave`/挂载状态字段不动） |
| 安全/敏感信息 | **不涉及** |

## 2. 实施（改了什么）

| 文件 | 改动 |
|---|---|
| `app/base.html` | ① 新增 `prepareWriteChannel(lg)`（**上传前**清通道，带一次 `mode=play`→`maintenance` 重置）<br>② 新增 `requestRestoreMode(lg)`（传完之后请求恢复，只认 `result=ok`）<br>③ **删除** `restoreHandshake()`（它的"重置通道再 restore"在上传之后做会丢数据）<br>④ `writeRecipeCore`：顺序改为 ⑤ 维护模式 → ⑤b 清通道 → ⑥ 声明大小（核对 `size`）→ ⑦ 分块 → ⑧ restore → ⑨ 轮询 → ⑩ 读回 → ⑪ 重启；分块失败时**绝不**进 ⑧<br>⑤ `uploadData`（安全备份 → 恢复到相机）同序改造<br>⑥ `writeRawKV`（撤销标定）同序改造（**三处仍各自独立，没有合并**）<br>⑦ 自检：`datasize` 分"没报 / 0 / 对不上 / 一致"四态；`0` 报 err + 给相机侧修理路线 + 进结论<br>⑧ 自检：最后那次单独 restore 的口径更正 |
| `scripts/dv_writeproto.py` | 重写：7 个场景 + **顺序断言**（先失败、后通过，见 §3.1） |
| `scripts/dv_write.py` | `old` 对照模式的期望文案跟着步骤号改（⑧→⑦），仍然是"修复前的写法"对照 |

## 3. 验收

### 3.1 改前 vs 改后（`python scripts/dv_writeproto.py`）

改前（`app/base.html` = v2.13）实测序列 —— 顺序是反的，而且**上传失败也照样去 restore**：

```
E：…>MAINT>RESTORE>RSTATE>SETSIZE>CHUNK>RSTATE>MAINT>…>REBOOT        ← restore 在传之前
G（某块一直失败=3 次）：块尝试=3 restore=1 重启=0                    ← 传不完却已经 restore 了
--- 结果：失败 12 项 ---
```

改后：

```
A：序列=…>MAINT>RSTATE>SETSIZE>CHUNK>RESTORE>…            声明大小=1 块数=1 restore=1 重启=0
B：序列=…>MAINT>RSTATE>EXIT>…>MAINT>RSTATE>SETSIZE>CHUNK>RESTORE>RSTATE>…>REBOOT   play=1 块数=1 重启=1
C：声明大小=1 块数=0 restore=0 重启=0                     （size 不一致 → 一块都不传、也不 restore）
D：块数=1 restore=1 重启=0                                （轮询 generalerror → 报"没有成功"、不重启）
E：…>MAINT>RSTATE>SETSIZE>CHUNK>RESTORE>RSTATE>…>REBOOT    ★顺序全部通过 + 202 算接受
F：play=1 块数=1 restore=1                                （重置后仍报错 → 只 warn，不拦着写）
G：块尝试=3 restore=0 重启=0                              ★★传不完 → 绝不 restore
累计 js 报错=0  om3errs=0
--- 结果：全部通过 ---（47 项断言）
```

### 3.2 全量本机验收（都跑过，0 失败）

```
python scripts/check_syntax.py      → 10 个内联块全过
python scripts/live_check.py        → 错误数=0 om3errs=0 缺元素=0
python scripts/check_app.py         → om3errs=0 加入方案按钮=81 方案条目数=1 运行错误=0
python scripts/verify_all.py        → 页签/底栏/置灰 3 项/搜索 全过
python scripts/dv_writeproto.py     → 7 场景 47 项全过（含顺序断言）
python scripts/dv_write.py new      → A/B/C/D 全符（A/B 完整、C 中止不重启、D "完全一样"）
python scripts/dv_write.py old      → 对照：仍然复现"失败照旧往下传"的旧行为
python scripts/dv_mpwrite.py        → 五场景全过（含"重启前旧值不假报失败"）
python scripts/dv_mount.py          → 13 段全过（含"写入失败→状态一位都不变"）
python scripts/dv_share.py / dv_import.py / dv_model.py / dv_tasktest.py / dv_mpflow.py（详情条目=6）
python scripts/dv_round24.py / dv_blecam.py / dv_slotparams.py / dv_camclean.py → 全过
python scripts/dv_barchk.py / dv_float.py / dv_slotren.py / dv_mpwheel.py / dv_mplayout.py → 全过
python scripts/dv_audit_static.py   → 重复 id=0、页面里无日期、TODO/FIXME=0
python scripts/dv_stubguard.py / dv_asyncguard.py / dv_sweep.py → 与改前同一批（无新增）
python scripts/audit_all.py / audit_code.py → 与改前一致（onShowFileChooser 那条仍是已知假警报）
```

### 3.3 真机（**未验**，交给用户）

1. **正经写一次**（「我的配方 → 写入相机」或「连接相机 → 写入」）：相机应**重启**；重启后
   拨盘到位 → OK → Color Profile → 槽 N 应看到变化。日志里顺序应是
   `⑤进维护模式 → ⑤b通道自检 → ⑥声明大小 → ⑦全部 N 块上传完成 → ⑧请求恢复模式 → ⑨写入完成 → ⑪已请求重启`。
2. 若 ⑧ 仍回 `generalerror`：那就是**数据全部传完之后**相机还是不要 → 把日志发来（这时的结论才有意义）。
3. 顺便跑一次 ☰→「写入自检（只读）」：看 `datasize` 那行现在会不会明确报 `0`（旧版会写成"（一致）"）。
4. 若自检报 `datasize=0`：按日志里的 ①② 修相机（先在相机上自己保存一次色彩配置；不行再恢复出厂设置），
   修完先用「读取并备份」存一份再写。

## 4. 差异分析（规格 vs 实现）

| 规格点 | 实现情况 |
|---|---|
| F1 顺序 | ✅ 三处写入路径全部同序（`writeRecipeCore` / `uploadData` / `writeRawKV`） |
| F2 开工前清通道 | ✅ 只在**上传前**做；重置后仍报错只 warn（**刻意**不中止 —— 不能凭一个认不出的状态拦着写） |
| F3 不在开工前 restore | ✅ 自检里那次单独 restore 保留了，但**口径改了**（F8），它不参与写入流程 |
| F4 完整性 | ✅ 沿用"每块 3 次 / 失败不推进 offset / 没传完不 restore"；`dv_writeproto` G 专门断言"传不完绝不 restore"（改前这里会 restore） |
| F5 restore 判读 | ✅ 只认 `ok`；拒绝时**不重启**、给 `关机再开机` + 自检入口 |
| F6 就绪轮询 | ✅ 加了 `busy` 与 `lowbattery` 分支（官方口径：busy 继续问、lowbattery 直接失败）；`result=ok` 且无 `status` 视为就绪；认不出的状态 12 秒后按"状态不明确"继续 |
| F7 datasize 四态 | ✅ 静态检查 + 真机待验 |
| F8 自检口径 | ✅ |
| **没做（显式记录）**：分块大小仍是写死的 **4096** | 官方用相机能力值 `c2/l.f()`（来自能力表）。**本轮不动**：4096 一直能用，改成读能力表要新增一次请求 + 解析，属新功能，留给下一轮（真机若出现"某块老是失败"再考虑） |
| **没做（显式记录）**：调用前查相机能力表 | 官方每个 my-set 命令前都查 `c2/k.c("<命令名>")`（来自 `get_commandlist`），UI 还先查 `get_mysetdatamodekind`。**本轮不动**：这是"提前知道相机支不支持"的优化，不影响正确性；要做就做成自检里的一行输出 |
| **删除**：`restoreHandshake()`（被拒 → 重置通道 → 再 restore） | 它是 v2.11 为"反序时被拒"加的补丁。正确的顺序下 restore 在**传完之后**才发生，此时"重置通道"会**清掉刚暂存的数据**，重试没有意义。自愈能力**没有丢**：改成了开工前的 `prepareWriteChannel`（见 B 场景断言） |
| 步骤号变化 | 日志 ①..⑪ 的含义重排（HANDOVER §二/§六 已同步）；`dv_mpwrite` 等脚本断言的是文字内容不是编号，已全过 |

## 5. 文件清单

- 改：`app/base.html`（写入顺序 + 自检）
- 回退点：`app/base.before_r28.html`（= v2.13 源码，md5 `926584d325e9a0db7a5cd7d2a4f2c0fb`）
- 改：`scripts/dv_writeproto.py`（7 场景 + 顺序断言）、`scripts/dv_write.py`（old 对照文案）
- 改：`HANDOVER.md`（*补 v2.13/v2.14 版本表 + 顶部接手段 + 纠正"官方顺序"的记录*）、`README.md`（v2.13/v2.14 条目）
- 新增：本文件

---

## 6. 真机确认 + 两处误报修正（v2.15）

### 6.1 真机结果：**写入成功** ✅（2026-09-24，v2.14）

用户原话："这次写入成功"。⇒ **顺序就是根因**：官方顺序（**声明大小 → 分块传完 → restore → 轮询 → 重启**）
成立；v2.13 及之前"先 restore 再传"（相机还没暂存任何数据就被要求 restore）就是它一直回 `generalerror` 的原因。

### 6.2 随附自检日志的判读（这台相机 OM-3 / BJSA21721）

| 现象 | 判读 |
|---|---|
| `get_mysetrestorestate` → `<result>ok</result><status>generalerror</status>` | **这台相机"空闲"时就是这个值**：`result=ok` = 通道没坏；`status=generalerror` = "没有正在进行的恢复"，**不是错误**（v2.13/v2.14 按 `camSayNo` 会误判成"通道卡住"） |
| `get_mysetdatasize?kind=current` → `55422`，而"实读"`82614` | **两个数不是一回事**：55422 = my-set 数据大小；82614 = **current 全量设置**（开头就是 `1,OM-3,1100,BJSA21721,Current`）。实读更大是正常的，**不是"对不上"** |
| 1791 个键、7 行"不是键值行" | 7 行**全部集中在末尾**（相机自带的日志尾巴，如 `r1100 2025/08/22 08:16:58] bc L966 …`），不是被截断 |
| `get_mysetname?mode=current` → **HTTP 520** | 老现象（这台固件不支持这个查询），与写入无关 |
| `kind` 能力 = `current\|factory` | 印证 §0.2：官方**从不**使用 `factory`，这条线索早已关闭 |

### 6.3 修正的两处**误报**（v2.15 改的就是这两条）

1. **`datasize` 不再和"实读长度"比**（v2.13/v2.14 把"55422 vs 82614"判成"⚠ 对不上 → 去修相机"，**误报**）。
   现在的四态：没报 → warn（不判坏）；**`0` → err**（相机里那份 my-set 是空的 —— 这才是真问题，照旧给修理路线并写进结论）；
   `>0` → ok，并解释"实读是 current 全量设置、通常更大"；只有 `datasize > 实读` 才 warn（那才可能被截断）。
   末尾的"非键值行"也分开判：**全在末尾 = 相机自带日志尾巴（正常）**，**中间也有**才报"可能被截断"。
2. **`get_mysetrestorestate` 专用判读 `camRestoreState()`**（只看 `<result>`）：
   - `result` 有值且不是 ok → 真报错（**只有这时**才触发"重置通道"）；
   - `result=ok` + `status=generalerror/fail` → **空闲**，不重置、不改判；`busy` = 正忙；`lowbattery` = 电量低。
   ⇒ `prepareWriteChannel()` 不再每次写入前白重置一次通道（那会多花 ~2 秒，还会打印一句吓人的
   "上一次写入可能没干净收尾"）。
   ⚠ **⑨ 轮询（数据传完之后）仍用口径更严的 `camSayNo`** —— 那时相机应该在应用数据，两边口径不同是**刻意**的。
   **触发条件**：若真机出现"⑨ 报没成功、但重启后「校验上次写入」显示已生效"，就把 ⑨ 也换成 `camRestoreState`。
3. 自检里"第 5 步 `get_mysetrestorestate`"和最后那句结论的文案跟着实测口径改了（结论文案不再指向"去修相机"）。

### 6.4 验收（v2.15）

- `python scripts/dv_writeproto.py` 扩到 **8 场景 / 54 项断言**：
  **B** 改成真机的常态（`result=ok + status=generalerror` → **不做**多余重置）；
  新增 **H**（开工前 `result=generalerror` = 真报错 → **才**重置通道 → 重置后正常 → 写完）。
  改后全过（含原有 A/C/D/E/F/G 的顺序与"不假报"断言）。
- 四数 `om3errs=0 / 加入方案按钮=81 / 方案条目数=1 / 运行错误=0`；`verify_all`、`dv_write new`、
  `dv_mpwrite`、`dv_mount`、`dv_sweep`、`check_syntax` 全过。
- 构建：**v2.15**（`versionCode 215`）APK md5 `e81fa8c0944ef17b18721d73df510c1d`；源码 `app/base.html` md5 `b09fd5264aef93c3aa8596b9512a7efb`；
  产物 `apk/assets/index.html` md5 `6d68ac9f91616cd30876dd11446f84e7`。
- 真机：写入已成功（v2.14）；v2.15 只动了**自检判读**与**"重置通道"的触发条件**，
  写入主链路的顺序与 v2.14 **完全相同**。

### 6.5 v2.15 改动清单（想单独回退这几处就照这个改回去）

| 位置 | 改动 |
|---|---|
| `camSayNo()` 之后 | **新增** `camRestoreState(txt)`（只看 `<result>` 的专用判读） |
| `prepareWriteChannel()` | 用 `camRestoreState` 取代 `camSayNo`；常态（`result=ok`+`status=generalerror`）→ 直接开写、不重置 |
| 自检步骤循环 | 记下第 5 步原文 → 加一行"第 5 步说明" |
| 自检"整份数据体检" | `datasize` 四态 + 尾部异常行分开判（不再与实读比） |
| 自检结论 | `dataBad` 只在 `datasize=0` 时触发；正常时的结论文案改掉 |
