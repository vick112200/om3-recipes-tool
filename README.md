# om3 recipes tool · 工程说明

> 工作目录：`D:\workspace\om3-handbook`
> 源码原来在 `C:\Users\82302\AppData\Local\Temp\`（临时目录，会被系统清理），现已搬到这里。
> 仓库地址：<https://github.com/vick112200/om3-recipes-tool>
>
> **公开仓库里有什么**：源码 + 工具 + 四份门面文档（`README.md` / `AGENTS.md` / `TEST-camera.md` / `OPEN-ITEMS.md`）。
> **没进仓库的**（见 `.gitignore`，都在本机）：`HANDOVER.md` 与 `SPEC-round*.md` 这类逐轮开发档案、
> 真机日志（含相机 SSID/MAC）、85 份回退点备份、签名密钥 `apk/om3.jks`、官方 App 反汇编（体积+版权）。

## 目录结构

```
om3-handbook/
├─ app/                        # 页面源码
│  ├─ base.html                ★ 唯一真源（约 3.8 MB，所有改动都改这个文件）
│  ├─ base.before_*.html       # 各阶段备份（改坏时可按名字回退）
│  └─ （index.html 不存这里，构建时生成）
├─ apk/                        # Android 打包
│  ├─ build.sh                 ★ 一键构建 APK（aapt2 + javac + d8 + zipalign + apksigner）
│  ├─ mkasset.py               # 把 app/index.html 注入 APK 资源 + 注入 window.__OM3_APP__
│  ├─ bumpver.py               # 版本号自增（versionCode / versionName 两处）+ 写页面版本徽标
│  ├─ java/com/om3/handbook/MainActivity.java   ★ App 外壳 + 原生桥（相机 HTTP / Wi-Fi / 蓝牙 / 文件选择 / 分享）
│  ├─ AndroidManifest.xml      # 权限：相机、网络、附近设备(蓝牙)、明文 HTTP 等
│  ├─ res/                     # 图标等资源
│  ├─ om3.jks                  # 签名密钥（务必保留！丢了就不能覆盖安装）
│  └─ build/                   # 构建中间产物（不建议提交/备份，可随时删）
├─ make_single.py              # 生成桌面单文件 HTML（图片内嵌）
├─ all_recipes.json            # 78 条配方原始数据（页面里已内嵌一份）
└─ scripts/                    # 历史补丁脚本 + 自检脚本（改动记录都在这里）
   ├─ check_syntax.py          # 抽出全部内联 <script> 交给 node --check（改完必跑）
   ├─ check_app.py             # 带 __OM3_APP__=1 的四数验收（按钮/方案/错误数）
   ├─ live_check.py            # 抓加载期运行时报错（改完必跑；注意它不带 __OM3_APP__）
   ├─ verify_all.py            # 逐条验收（无头浏览器实测页签/底栏/置灰/搜索）
   ├─ audit_all.py             # 结构自检（重复 id / 悬空引用 / 元素归属 / 浮层）
   ├─ audit_code.py            # 代码自检（重复定义 / 死代码 / 空 catch / 定时器）
   ├─ dv_*.py                  # 排查用一次性脚本（抓调用栈 / 验搜索栏 / 自递归扫描…）
   └─ patch_*.py, clean*.py    # 各次改动的补丁（可追溯"什么时候改了什么"）
```

> 这些脚本以前读的是 `C:\Users\82302\AppData\Local\Temp\app\base.html`（旧位置），
> 已全部改成读工程里的 `app/base.html`；`build.sh` / `mkasset.py` 同理。

## 构建流程（三步）

```bash
cd /d/workspace/om3-handbook

# ① 页面源码 → 同步并注入 app 标记
cp app/base.html app/index.html
python apk/mkasset.py            # → apk/assets/index.html（注入 __OM3_APP__ 标记）

# ② 打包 APK（build.sh 内部会先跑 bumpver.py 自增版本号 + 写徽标）
cd apk && bash build.sh          # → apk/build/om3.apk

# ③ 发布到桌面
cp apk/build/om3.apk "/c/Users/82302/Desktop/om3 recipes tool.apk"

# 可选：桌面单文件 HTML（图片内嵌，约 20 MB）
python make_single.py "/c/Users/82302/Desktop/OM-3色彩配方手册.html" 480 78
```

> 注意顺序：`mkasset.py` 用 `app/index.html` **覆盖** `apk/assets/index.html`，
> 所以版本徽标由 `build.sh` 里的 `bumpver.py` 最后写（必须排在 mkasset 之后）。
> **版本号规则**：第 16–45 轮是 **2.x**（`bumpver.py` 把 `versionCode + 1`，版本名 = `2.(code-200)`）；
> **第 46 轮（v3.0）起进 3.x**：版本名 = `3.(code-300)` → `300 = 3.0`、`301 = 3.1`……
> 所以**打出来的版本 = 构建前 manifest 里的 code + 1**（出 3.1 时构建前 manifest 是 `300`，构建后变 `301 / 3.1`）。
> `build.sh` 里只有 **Android SDK 路径**指向临时目录 `C:\Users\82302\AppData\Local\Temp\sdk`，换机器要改；
> 构建目录已改成工程自己的 `apk/`（以前写死 Temp/apk，会打包到旧文件）。

## 改代码的固定流程（这几轮踩坑后总结，第 16 轮起按 `ai-dev-guardrails` 三阶段走）

0. **先写/更新规格**（`SPEC-*.md`：功能点六要素 + "必须显式声明清单"七类 + 可逐条验证的验收标准）；
   改完在规格末尾补 **逐条验收结果 + 设计与实现的差异分析**（差异要**改代码或改规格**，不许只记录）。
1. **先读代码定位**（例如页签切换在 `base.html` 的 `function showPane(p)`，取值用 `$()` 或 `document.getElementById`），**不要先加补丁**；
   拿不准就先抓**真实调用栈 / 真实 DOM 状态**当证据，别猜。
2. 改前先 `cp app/base.html app/base.before_<改动名>.html`（回退点）；
3. 改完立刻 `python scripts/check_syntax.py`（抽出全部内联脚本做 node --check）；
4. 跑 `python scripts/live_check.py`（**必须错误数=0**）；
5. 跑 `python scripts/check_app.py`（**四数验收**，见下）；
6. 跑 `python scripts/verify_all.py`（页签/底栏/置灰/搜索逐条验收）+ 相关的 `dv_*.py`；
   （顺手 `python scripts/check_open.py`：待验证清单里标「未验」的项都必须有能点的入口）
7. 构建发布后，再跑一次 `check_app.py` **验最终产物**：
   `python scripts/check_app.py "D:\workspace\om3-handbook\apk\assets\index.html"`。

> ⚠️ `live_check.py` **不带** `window.__OM3_APP__=1`，主脚本会提前 return，
> 所以它只能查"加载期报错"，**不能用它数按钮**（会得到 0 个的假象）。
> 数按钮/方案必须用 `check_app.py`。
>
> 四数基准（**2026-09-29 实测 · v3.45**）：`om3errs=0`、`配方卡=77`、`加入方案按钮=110`（77 张卡 + 33 个优化版槽位）、
> `方案条目数=1`、`运行错误=0`。
>
> 真机怎么测：见 **`TEST-camera.md`**（连接相机三轮测试）。
> **日志怎么给我**：测试页点「分享日志（发微信/邮件给我）」最省事；也可以丢进 `logs/` 或直接粘——见 `logs/README.md`（我这边 `python scripts/read_log.py` 自动分诊）。
> 连接流程想先"推演"：`python scripts/sim_connect.py first|saved|nocam|noble`（假原生桥 + 时间线，不用真机）。
> （历史值：2026-09-23 是 `加入方案按钮=81`＝58 张卡 + 23 个槽位 —— **这两个数会随配方/槽位增删而变**，
> 判断"有没有回归"的正确做法是**拿改动前的备份跑一遍对照**，而不是死记基准值。）

## 已知待办

> **★★★ v2.31（第四十一轮）滑动回到最初那版（原生拖动 + CSS 吸附）**
> - 用户反馈「滑动还是不行，回到最初那版」：第 40 轮我加的手势拦截（touchstart/move/end + 强制落点 + 380ms 兜底）
>   会跟浏览器**原生拖动抢控制权** → 真机"滑不动"。本轮把 JS 拦截**整套删除**。
> - 现在：`scroll` 事件只更新位置标签（不碰 scrollLeft）；`‹ ›` 用 `scrollBy({left: ±(clientWidth+12)})` 翻一屏；
>   `scroll-snap-type:x mandatory` 保持（最初那版就有）。
> - 「一次只换一张」改成**声明式**：`.scslide{scroll-snap-stop:always}`（浏览器原生行为、零 JS；
>   不支持就退化成自由滚，不会坏）。
> - 验收：`dv_scene41`（19/19：浏览器认 `scrollSnapStop=always`、滚到第 4 张位置被保留、甩到末尾不跳回第一张、
>   `‹ ›` 位移 ±522）、`dv_scene39`(27/27)、`dv_r39`(35/35)、`dv_r37` 全通过；`dv_scene40.py` 已删除（测的是被撤掉的行为）。
>

## 全量排查怎么跑（大改之后建议走一遍）

```bash
python scripts/dv_audit_static.py   # 静态：重复 id / 悬空引用 / 空 catch / 页面里可见的日期
python scripts/dv_sweep.py          # 5 个页签是否真的可见有内容 + 缺元素 id 清单 + 报错
python scripts/dv_mpflow.py         # 「我的配方」列表→详情→改名→删除（取消不许误删）
python scripts/dv_tasktest.py       # 任务弹窗：后台运行 / 关闭 / 气泡
```

> ⚠️ 排查脚本**自己**也要带 `window.__OM3_APP__=1`（否则主模块直接 return，全是假象）。
> 本轮的 `dv_sweep.py` 一开始就漏了，白查半天一个假 bug；现在它会把
> `__OM3_APP__` / `__om3mpInit` 的类型打出来自检。

## 改这块代码前必看的一条规律

`app/base.html` 的多个 `<script>` 是**按顺序执行**的：块02 在解析期就缓存了一批 DOM 引用，
但 `#toc2` 那一组元素（含 `#noresult2`）是块08 **运行时才注入**的 →
任何"先缓存、后注入"的元素在块02 里都是 `null`，会抛
`Cannot read properties of null`。本轮的 `nav2` / `empty2` 两个 bug 都是这个原因。
**这类引用一律"用时再取"或判空。**

改布局还有一条（v1.131 踩到的）：**别只改外层容器的 `display`**。
优化版槽位卡里，色轮和文字是 `.osbody` 这个 flex 容器里的两列 —— 只给 `.oslot{display:block}`
是没用的（所以上一轮"改了"却看不出变化）。要让色轮不再独占窄列，必须改 `.osbody` 本身的
`flex-direction`。**量尺寸用 `scripts/dv_geom.py`，看图用 `scripts/dv_shot.py`，别靠肉眼判断。**

## 备份建议

- `app/base.before_*.html` 是各阶段备份，**别删**；
- `apk/java/com/om3/handbook/MainActivity.before_*.java` 是**原生桥**的各阶段备份（第 64 轮起会动 Java），同样**别删**；
- `apk/om3.jks` **务必单独备份**（丢了这个密钥，用户就无法覆盖安装更新）；
- 建议给这个目录做一次整体备份（约 87 MB）。

## 原生桥（`MainActivity.java`）改动注意

- 页面与 Java 是**同一个 APK 里一起发的**，但**不要改已有桥方法的签名/参数个数** —— 新增能力请**加新方法**
  （第 64 轮 `connectCamera2(ssid,pass,bssid)` 就是这么做的：老 `connectCamera(ssid,pass)` 原样保留并转调新方法），
  这样"老页面配新 Java"也不会炸，页面还能按 `Native.xxx` 是否存在自动退回。
- 改完 Java 不必等整包：`javac --release 8 -cp <android.jar> java/com/om3/handbook/MainActivity.java` 就能先编一遍
  （`scripts/dv_r64.py` 里已经这么干；`android.jar` 在临时目录的 `sdk/android-34/`）。
- 验证"新方法真进了包"：解开 `apk/build/om3.apk` 里的 `classes.dex` 搜方法名（只是个字符串表，`rg` 就能搜）。
