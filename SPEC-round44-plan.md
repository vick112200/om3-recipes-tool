# SPEC-round44-plan.md —— 第 ③ 步「档位推荐归约成 8–10 个候选档」的**开工依据**

> 用户 2026-09-25 已定：**按白平衡签名分档**。
> 本文只是**数据摸底 + 候选档骨架**，还没动代码。下一轮照着这个做。

---

## 1. 为什么必须按白平衡签名分

OM-3 的一个 C 档（Color Profile）里，**4 个槽共享同一个白平衡**（色温 + A-B + G-M 三者都锁死在档位级）。
所以同档里的 4 个配方，**白平衡必须完全一致**，否则录进去就不是原配方了。
⇒ 候选档 = 一组「白平衡签名相同、但色轮/影调不同」的配方。

## 2. 全库 79 条的签名分布（`scripts/_wb_groups.py` 算出来的）

40 个签名，其中**有卡片的** 20 个：

| 白平衡签名 | 有卡数 | 成员 |
|---|---|---|
| **A0 G0** | **15** | 冷泉（Cool Spring）、太平洋西北（PNW）、Q116、Velvia 50、沉静（Subdued）、真实（Real）、雨林气息（Rainforest Vibes）、OM Chrome、胶片感（Filmed）、默认 1–4、自然（Natural）… |
| **MONO**（挂 MONO 档，不占槽） | **6** | Ilford HP5、Fuji Monochrome、Fuji Acros、悉尼颗粒（Sydney Grain）、OM-3 X 单色胶片模拟（X-Monochrome）、致安塞尔（Ode to Ansel） |
| **A+2 G+1** | **6** | 夜市（Night Market）、OM-3 Fujicolor 200、Portra 400（Peter Turner）、Fuji Pro Neg Hi、Fuji Classic Chrome ×2 |
| **A+1 G+1** | **6** | 锈色复古（Rusty Vintage）、Kodachrome 25、Fuji Velvia、Fuji Provia、Fuji Pro Neg Std、Fuji Astia |
| A+3 G+1 | 3 | Portra 400（James Bloomer）、Fujicolor SUPERIA Premium 400、Kodachrome 64（Gareth） |
| A+2 G0 | 2 | OM-3 东京—韦茨拉尔、OMTC 柔调（OMTC Soft） |
| A+2 M1 | 2 | OMTC 冷调（OMTC Cool）、Kodachrome Slim Aarons |
| A+3 M1 | 2 | Kodachrome 64（冲印版）、Kodachrome 64（早期版） |
| A+4 G+3 | 2 | 电影感苔原（Cinematic Tundra）、Fuji Classic Neg |
| A+4 M1 | 2 | 玫瑰金（Rose Gold）、OMTC 暖调（OMTC Warm） |
| BASIC_COLOR | 2 | 自然（Natural）、Velvia |
| A+1 G+2 | 1 | Fuji Eterna |
| A+1 G0 | 1 | Kodachrome 64（James Bloomer） |
| A+1 M1 | 1 | 有点像波特拉（Kinda Portra） |
| A+4 G+1 | 1 | Kodak Gold 200 |
| A+4 G+2 | 1 | 怀旧之夏（Nostalgic Summer） |
| A+7 G+1 | 1 | 埃斯蒂尔斯普林斯绿（Estill Springs Green） |
| B1 G+1 | 1 | 欧洲城市（CityEurope） |
| B1 M1 | 1 | 微醺落日（Subtle Sunset） |
| B2 G+2 | 1 | Kodachrome 25（Gareth） |
| B5 G+7 | 1 | 夜市长（The Night Mayor） |

**另 20 个签名共 21 条，全都没有卡片**（都是**固定色温**配方：3800K / 4000K / 4200K / 5200K / 5300K…7500K）
⇒ 它们**单独成一册**（现在 `#kelvin` 那张表就是），不进候选档池：固定色温本身就要独占一个档。

> ⚠ 注意 `A0 G0` 有 15 张卡，但**一个档只有 4 槽** ⇒ 这一档必须做「**挑 4 个 / 其余进可替换池**」的取舍，
> 而且这是**最重要的一档**（中性万能），得按用途搭配：日常 / 人像 / 风光 / 黑白底子…

## 3. 候选档骨架（10 档，待用户点头再展开成「每档 4 槽 + 为什么放一起」）

| # | 候选档（白平衡签名） | 定位 | 原生可填槽数 |
|---|---|---|---|
| 1 | A0 G0 | 不偏移 · 万能中性 | 15（要挑 4） |
| 2 | A+1 G+1 | 淡暖 · 富士反转/负片 | 6（挑 4） |
| 3 | A+2 G+1 | 富士胶片系 / 暖纪实 | 6（挑 4） |
| 4 | A+3 G+1 | 柯达暖 · 日落 | 3（缺 1，可借 A+2 G+1 的） |
| 5 | A+4 M1 | 暖调 · 玫瑰肤色（人像） | 2（缺 2） |
| 6 | A+2 M1 / A+2 G0 | 偏冷 · 青调 | 4（正好） |
| 7 | A+4 G+3 | 浓郁冷暖 · 现代胶片 | 2（缺 2） |
| 8 | A+3 M1 | Kodachrome 怀旧 | 2（缺 2） |
| 9 | B1 G+1 / B1 M1 / B2 G+2 / B5 G+7 | 冷调 · 蓝调时刻/日落 | 4（各 1） |
| 10 | MONO（挂 MONO 档） | 黑白 | 6（挑 4，**不占 C 档槽**） |
| — | 固定色温 21 条 | 另册（`#kelvin`） | 不占候选档 |

**缺槽怎么办**（每档只有 2–3 张原生卡片的）：
- 方案 A：**该档就放 2–3 格**，页首写「这一档只填得满 2 格，另外 2 格留空给自配」
- 方案 B：从**位移最小的邻近签名**借（沿用现在档位推荐那套「位移格数」算法，`risk` 值越低越优先）
- ⚠ 现在这一版页面上那句「**20 个彩色槽位里只有 1 格动了白平衡**」是它的核心卖点 ⇒ **借来的槽要标出位移了多少格**，
  否则就变成"偷偷改了白平衡"

## 4. 下一轮要动的地方（改前先备份 `app/base.before_r44.html`）

| 位置 | 现在 | 要改成 |
|---|---|---|
| `#oC1`..`#oC5` 五段 | 5 档 × 4 槽 + 1 个 MONO 槽 | **10 段候选档**（id 建议 `#ods1`..`#ods10`，或保留 `#oC1..` 只加 `#oC6..`） |
| `#modetabs` | 5 个按钮 C1–C5 | 10 个候选档按钮（**`dv_r42` 断言「modetabs 5 个」要同步改**） |
| `__OM3OPT__` | 19 条 | 重算（候选档用到的全部 slug） |
| `IDX` 的 `oC*` 条目 | 21 条 | 重算（**`dv_r43` 断言「`oC*` ≥ 20」要同步改**） |
| `SC[].items[].os/osl` | 指向 `oC?-?` | 重算；**「日常挂机」那条现在 `os` 是空的，这一步要填上** |
| 页首 `#ointro` | 「5 个 C 档…20/20 全满」 | 「**相机只有 C1–C5；下面是 10 个候选档，挑 5 个写进去**」 |
| `#owb` / `#oskin` / `#osolo` 等对照表 | 按旧 5 档写死 | 跟着改 |
| `check_app` | 「优化版槽位 23」 | 同步改期望值 |
| `dv_r34` / `dv_r35` | 可能引用 `oC` 槽位 | 跑一遍看有没有写死 |

**验收**：`dv_r44.py` 新增断言 —— 每档所有槽的配方签名 = 该档签名（借的槽必须**显式标出位移**）；
`__OM3OPT__` / `IDX(oC)` / `SC(os)` 三处锚点全在；`#modetabs` 按钮数 = 候选档数；0 JS 报错。
