# SPEC-round22：我的配方槽位布局 + 描述带入 + 浮层去重（v2.7）

## 0. 用户原话

> 「我的配方中槽位的显示也不太行，内置配方都改了，但是我的配方的色轮图还是占一列，下面空的，
> 然后我希望把内置配方放进我的配方时，能够把描述等也一起填入。
> 然后返回最上的小图标和展开全部重叠了，你把展开全部去掉，只留返回最上」

---

## 1. 槽位布局：色轮不再独占比一列（先量后改）

**探针实测（`scripts/dv_mplayout.py`，改前）**：

| 量到的东西 | 值 |
|---|---|
| `.mpsrow` | 454×**763** |
| 里面的 `svg.mpwheel` | x=36, **100×100**（独占左列） |
| `.mpmain`（内容） | x=146, 344 宽, **543 高** |
| **色轮下方到行底** | **507px 空白** ← 用户说的"下面空的" |

原因：内置配方卡的 `.cbody/.osbody` 早就改成"上下堆叠"，但**我的配方槽位行 `.mpsrow` 还是 flex-row**，
色轮 `.mpwheel{width:100px;height:100px}` 被钉在左边一列。

**改法**（`app/base.html` CSS，1 处）：

```css
.mpsrow{display:flex;flex-direction:column;gap:10px;align-items:stretch}   /* 原来 flex-row */
.mpsrow > svg.mpwheel{width:min(56vw,210px) !important;height:auto !important;align-self:center;margin:0 auto}
.mpsrow .mpmain{width:100%}
.mpsrow .vals,.mpsrow .vlegend{text-align:center}
.mpsrow .tags{justify-content:center}
```

**坑**：色轮 `svg` **自己就带 `class="mpwheel"`**（没有外层 div）——第一版我写成 `.mpwheel svg` 选择器，
结果整条规则落空、色轮被拉成整行宽。已在代码里注明。

**改后实测**：色轮 210×210 居中（x=158，行 36..490 → 正中），内容 454 宽全宽、紧接在色轮下方 10px；
`.mpsrow` 763 → 同样的内容不再有横向空列。

---

## 2. 内置配方 → 我的配方：描述（6 行）+ 标签一起带过来

- 用户此前要求过"描述全部手填"，本轮**按用户新要求改掉**（在代码注释里写明"此条已被本条替代"）。
- 内置配方的丰富描述**只存在于卡片 DOM**（`__OM3RECIPES__` 数据里没有）→ 新增
  `richFromCard(卡元素)`：抓 `.foldbody .row` 的 `画面感觉/色彩重点/影调/适合/避开/提示` + `.tags span`；
- 三个入口全部接上：内置配方卡（`saveCardToSets`）、优化版槽位卡（`saveCardToSets2`）、
  "仅名字"入口 —— 都调 `fillPickedSlot(t, rec, desc, rich)` → `putRecInSlot(..., rich)`；
- `putRecInSlot` 只在**卡片上真有文字**时才写（空的不写、不生成），日志与提示会说清带了什么：
  「＋带过来 6 行描述、3 个标签」；
- `__om3putRec(setIdx, slot, rec, nm, desc)` 旧签名**仍兼容**（第 6 个参数可选）。

---

## 3. 贴底浮层：「展开全部」删掉，只留「回到最上」

- 根因：`#top`（↑）`bottom: calc(barh + 12px)`、`#foldbar`（展开全部/说明）`bottom: calc(barh + 22px)`，
  同一个 `right:14px` → **必然重叠**，这正是用户看到的。
- 处理：**删掉 `#foldbtn`（展开全部）**；`#foldbar` 里只剩「说明」，并挪到 ↑ 上面
  （`bottom: calc(barh + 64px)`，手机上 `+62px`）；`#foldtip` 相应上移到 `+110px`；
- 防回归：`foldbar` 的 JS 改成 `if(!bar) return;` + `lab1/lab2` 判空（第一版漏了，`dv_camclean` 立刻抓到
  「Cannot read properties of null」→ 已修）；
- ⚠ 「展开全部」及它的 `#foldbtn` 样式仍留在 CSS 里（历史遗留 + 兼容旧结构），**页面上已没有这个按钮**。

---

## 4. 验收（`scripts/dv_mplayout.py` 重写为正式验收，10 项断言全过）

| 断言 | 结果 |
|---|---|
| ★4 个槽位都是"色轮单独一行居中 + 内容全宽" | ✅（居中=true / 内容全宽=true / 还是左右两列=false / 色轮够大=true） |
| ★色轮下方没有大片空白 | ✅ 间距 **10px**（改前 507px 的空白） |
| 详情页 4 个槽位行都在 | ✅ |
| ★走「加入我的方案」按钮 → 槽里带上了描述 | ✅（脚本真的点按钮、走自绘弹窗） |
| ★画面感觉/影调/适合/避开 都在 | ✅ |
| ★标签也带过来了 | ✅ `["微浓","偏冷","柔和"]` |
| ★同一入口 `putRecInSlot` 一定写进描述 | ✅（兜底直接调） |
| ★详情页能看到带过来的描述 | ✅（页面上出现「画面感觉」行） |
| ★「展开全部」已删掉（页面没有 `#foldbtn`），「回到最上」还在 | ✅ |
| ★两者不重叠（比 CSS `bottom`：说明 118 ≥ 回到最上顶 112） | ✅ |

**回归**：38 个脚本 + 4 个审计 **0 失败**；`按钮=81`、`运行错误=0` 与改动前一致。
（`dv_mpwheel.py` 里"色轮 100×100"的旧断言按新设计改成"正方形且 120–215 之间"，这是**用户要的布局变化**，不是放宽。）

---

## 5. 产物

| 项 | 值 |
|---|---|
| 版本 | **v2.7（build 207）** |
| APK | `C:\Users\82302\Desktop\OM-3色彩配方手册.apk`，53357984 字节，md5 `290451847fd2919064f5e8a5aac6d29b` |
| 源码 | `app/base.html` md5 `c8b7e75e841eafedb0e172419f932958` |

## 6. 局限 / 待确认

- 色轮尺寸定在 `min(56vw,210px)`（居中一行）——比内置卡片的 270px 略小（我的配方一屏有 4 个槽，避免页面过长）；
  想和内置卡片一模一样大，把 `56vw,210px` 改成 `64vw,270px` 即可；
- 描述带入只在**卡片上真有文字**时生效；"优化版槽位卡"如果描述结构不同（没有 `.foldbody .row`），
  会按空处理（不写脏数据）；
- 真机未验（本轮全是页面布局/文案，风险低）。
