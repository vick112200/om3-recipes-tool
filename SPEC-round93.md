# 第 93–94 轮规格：**改名 om3 recipes tool** + **右上角打赏按钮（先隐藏）**

> 需求来源（需求方 2026-09-29 两条消息）：
> 1. 「**名字改一下，改成 om3 recipes tool**。然后我想在右上角增加个按钮，一个打赏图标，
>    功能是展示我的收款码，然后可以选择捐献请我喝咖啡什么的，怎么做」
> 2. 「**不用嵌二维码，这个功能先隐藏，后面再做**」
> 回退点：`app/base.before_r93.html`（r93 起点）、`app/base.before_r94.html`（r94 起点）、
> `apk/strings.before_r93.xml`（启动器名，**注意放在 `apk/` 下，不能放 `apk/res/values/`** —— aapt2 会报"文件名多余的点"）。
> 生成脚本 `scripts/gen_r93.py`（6 步）/ `scripts/gen_r94.py`（1 步）；探针 `dv_r93.py`（25/25）/ `dv_r94.py`（13/13）；
> 收款码工具 `scripts/set_donate.py`。

## 1. 第 93 轮：改名（`om3 recipes tool`）

| 位置 | 改前 | 改后 |
|---|---|---|
| `<title>` | OM-3 色彩配方手册 | **om3 recipes tool** |
| 顶栏 `.tbname` | OM-3 色彩配方手册 | **om3 recipes tool** |
| 首页 `<h1>` | OM-3 色彩配方手册 | **om3 recipes tool** |
| 导出文件头 | `OM-3 色彩配方手册 · 配方导出` | **om3 recipes tool · 配方导出** |
| 导出包 `app` 字段 | OM-3 色彩配方手册 | **om3 recipes tool** |
| Android 启动器名（`apk/res/values/strings.xml`） | OM-3 色彩配方 | **om3 recipes tool** |
| 桌面产物 | `OM-3色彩配方手册.apk` | **`om3 recipes tool.apk`** |

（页面里共 5 处字符串，一次替换；`kind: 'om3-colorprofile'` 这种**数据格式**字段不动 —— 老导出的包还能读。）

## 2. 第 93 轮：右上角打赏按钮（☕ → 展示收款码）

- **按钮**：顶栏 `.tb` 里、页签之后（= 右上角），选择器 **`data-tv="donate"`**（第 68 轮起的规矩：新控件只用 data-tv，
  **本轮不加任何 id**）。样式 `.donbtn`。
- **弹窗**：复用站内自绘弹窗 `om3Ask`（`#omask/#otitle/#obody/#ofields/#ook/#ocancel` **都是已有 id**），
  给它加两个能力：`opt.img`（显示收款码图，样式 `.om3qr` + 说明 `.om3cap`）与 `opt.onlyOk`（只留"谢谢"一个按钮）。
- **收款码**：离线单文件 App → **base64 内嵌**，就一行：
  ```js
  var OM3_DONATE_IMG = '';   /* r93:donate */
  ```
  填图：`python scripts/set_donate.py 你的收款码.png`（幂等；**按魔数校验**是 PNG/JPEG/WebP/GIF；>1.5 MB 拒绝；
  `--show` 看现状、`--clear` 清掉）。没填图时弹窗**如实说**"收款码还没放进来"。

## 3. 第 94 轮：先隐藏（需求方要求，代码全留）

- 只给按钮加 `style="display:none"`（一行 = 唯一开关），旁边注释写清"想开的三步"；
- 收款码那一行、弹窗能力、`set_donate.py` **全部保留**；
- 探针 `dv_r94` 验：按钮**在 DOM 但看不见**（渲染高 0）→ **把 style 去掉就能用**（点一下照常出弹窗）。

## 4. 显式声明

| 类别 | 声明 |
|---|---|
| 涉及 | `app/base.html`、`apk/res/values/strings.xml`、`scripts/gen_r93.py`/`gen_r94.py`、`scripts/set_donate.py`、`scripts/dv_r93.py`/`dv_r94.py`、`dv_r83/84/85/86/88/89/90/91/92`（各 1 处口径：第 93 轮按规格新增了 `donate`）、本文档 + `HANDOVER.md` + `AGENTS.md` + `README.md` + `TEST-camera.md` |
| 不涉及 | **Java 不改**；相机连接链/BLE/配方数据/导出格式都不动；不加权限；不联网 |
| 集合 | **新增 id：无**；**新增 data-tv：恰好 1 个 —— `donate`**（r93 探针断言"新集合 == 老集合 ∪ {donate}"；隐藏是 r94，集合不变） |
| 隐私 | 收款码放在 APK 里 → 解包可见（需求方自己的码，属预期）；**不联网、不上传** |

## 5. 验收结果

| # | 验收点 | 怎么验 | 结果 |
|---|---|---|---|
| 1 | 改名：页面 5 处 + 启动器名；旧名字一个不剩 | `dv_r93` A | ✅ |
| 2 | ☕ 在顶栏（右上角）；点它出站内弹窗、只一个"谢谢" | `dv_r93` B（`B3 位置右=260/宽526`、`标题=请我喝杯咖啡 ☕`） | ✅ |
| 3 | 没嵌图时如实说明、不放空图 | `dv_r93` B | ✅ |
| 4 | 嵌图那条路通（用 1×1 真 PNG 测）：嵌图后弹窗出 `<img class="om3qr">` + 说明；`--clear` 能回退 | `dv_r93` C | ✅ |
| 5 | 新增 data-tv 恰好 `{donate}`；id 集合不变；Java 未改 | `dv_r93` D | ✅ |
| 6 | **隐藏后**：按钮在 DOM、渲染高 0（右上角看不见）；去掉 style 就能用 | `dv_r94` A/B | ✅ |
| 7 | 防回归 | `dv_r92` 25/25、`dv_r91` 21/21、`dv_r90` 16/16、`dv_r89` 12/12、`dv_r88` 13/13、`dv_r86` 13/13、`dv_r85` 23/23、`dv_r84` 26/26、`dv_r83` 36/36、`dv_r82` 37/37、`dv_r81` 49/49、`r80` 15/15、`r79` 12/12、`r78` 21/21、`r77` 33/33、`r76` 13/13、`r75` 15/15、`r74` 31/31、`r73` 26/26、`r72` 20/20、`r71` 28/28、`r70` 25/25、`r69` 42/42、`r68` 44/44、`r67` 40/40、`r64` 61/61、`r62` 41/41 | ✅ |
| 8 | 固定流程 + 出包 | `check_syntax`/`live_check`(0 错)/`check_app`(四数一致)/`verify_all`/`check_open` 全过；**v3.45（build 345）** md5 `9274368ecb34adbfa6feabef0495f67e`，桌面 `om3 recipes tool.apk` | ✅ |

## 6. 差异分析

| # | 原定 | 实际 | 结论 |
|---|---|---|---|
| 1 | 备份 `strings.xml` 放原地 | 放 `apk/res/values/` 会让 aapt2 报 `file name cannot contain '.' other than for specifying the extension` → 首次打包失败 | **改流程**：备份挪到 `apk/strings.before_r93.xml`；本条已写进本文档（下次别再踩） |
| 2 | 第 93 轮按规格新增了 `donate` | 老探针 dv_r83..92 里"新增 data-tv 恰好 == 某某"的断言全红 | **改探针口径**（"新增的都在已声明表里"，表 = `{cv-pass, donate}`）；新那轮的探针仍断言"恰好 == {donate}" |
| 3 | 需求方先说"怎么做打赏" | 我按"内嵌收款码 + 站内弹窗"实现了整条路，随后需求方决定**先隐藏** | **改代码**（r94 一行 `display:none`）+ 把"想开的三步"写进注释/文档，代码一条不删 |
| 4 | 产物名 | 跟着改名 → `om3 recipes tool.apk`（旧的 `OM-3色彩配方手册.apk` 已从桌面删除，避免装错） | **改流程**（README/AGENTS 里的发布命令同步改） |

## 7. 以后想开打赏（三步）

1. 去掉 `app/base.html` 里那个按钮上的 `style="display:none"`（`data-tv="donate"` 那一行）；
2. `python scripts/set_donate.py 你的收款码.png`（把收款码内嵌进去；`--show` 可查）；
3. `cp app/base.html app/index.html && python apk/mkasset.py && cd apk && bash build.sh`，然后拷到桌面。
