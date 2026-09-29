# SPEC-round25：修写入协议（真机日志定因）+ 底栏/直连（v2.10）

## 0. 真机日志（用户 2026-09-24 提供，本次定因的唯一依据）

关键几行：

| 步 | 相机回的 |
|---|---|
| ⑤ `switch_cammode.cgi?mode=maintenance` | HTTP 200 |
| ⑥ `request_restoremysetdata.cgi?action=restore` | **HTTP 200，但 body = `<response><result>generalerror</result></response>`** |
| ⑦ `set_mysetdatasize.cgi?size=55422` | HTTP 200 `<result>ok</result><size>5542…` |
| ⑧ 14 块全部 | HTTP 200 |
| ⑩ `get_mysetrestorestate.cgi`（反复） | `<result>ok</result><status>generalerror</status>` |
| ⑪ `exec_reboot.cgi` | **HTTP 202** |

## 1. 两个真 bug（都不是"随机不灵"，是代码错）

### bug 1：只看 HTTP 码，不看相机回的 `result` ★主因
`request_restoremysetdata` 明确回了 `generalerror`（= 相机**拒绝进入恢复模式**），
我们**只判 HTTP 200** → 当成成功 → 白传 14 块（55 KB）→ 相机根本没接受 → 数据不会应用 → 也就没什么可重启的。
**这就是"写完相机没重启、色轮没生效"的完整因果链。**

### bug 2：`exec_reboot` 回 202 被我们误判成"没接受重启请求"
官方 APK（`settings.myset` 系列）在 `exec_reboot` 的回调里**只把状态码写日志**，不当失败；
202 = Accepted 本身就是"收到了，开始重启"。我们却因为 `!== 200` 报了大红字，误导用户。

## 2. 顺序也跟官方不一致（本轮按官方改）

反汇编官方 `com.omdigitalsolutions.oishare.settings.myset.a`（方法 `l/m/n/o` + `a$c/a$d` 回调）得到的真实顺序：

```
switch_cammode(maintenance)
→ request_restoremysetdata?action=restore        ← 判 result==ok，否则进错误态
→ get_mysetrestorestate 轮询（就绪）              ← 我们以前**缺这一步**
→ set_mysetdatasize?size=N                        ← 还要核对相机回的 <size>
→ send_partialmysetdata?offset=&size=（分块）
→ get_mysetrestorestate 轮询（完成）
→ exec_reboot
```

我们以前是"传完才轮询"，**少了一次传前就绪确认**。现在补上（等不到就绪但也没报错 → 只警告、继续传，不卡死）。

## 3. 本轮改了什么

**新增 `xmlVal(txt,tag)` / `camSayNo(txt)` 两个小工具**
- `xmlVal`：从相机回的 XML 里取标签值。
- `camSayNo`：**只在相机明确说不行时**返回原因（`<result>` 有值且不是 ok，或 `<status>` 是 generalerror/invalid/error/ng/fail）。
  没有 `result` 标签（有些接口不回）→ 不算不行、按原流程继续 —— **不能因为"认不出"把写入卡死**。

**写入主路径 `writeRecipeCore`（我的配方 / ③ 写入 共用）**
1. ⑥ restore → 判 `camSayNo`：明确报错就**立刻中止**（0 块上传、不请求重启），并告诉用户「相机拒绝进入恢复模式 → 关机再开机后重写」；
2. ⑦ **新增传前就绪轮询**（最多 ~8 秒，遇 error 中止，认不出就继续并记录）；
3. ⑧ 声明大小 → 判 `camSayNo` + **核对相机回的 `<size>` 与本地一致**（不一致就中止：照它传必定缺一段）；
4. ⑩ 传完轮询 → `camSayNo` 命中就抛「这次写入没有成功（数据没被接受）」+ 建议关机再开机；
5. ⑪ 重启：**2xx（含 202）都算已请求重启**，只有真失败才报错。

**备份恢复路径 `uploadData`** 同样处理（restore/就绪/大小/完成四处都判 `camSayNo`）。

## 4. 验收：`scripts/dv_writeproto.py`（新增，21 项断言全过）

假相机按真机回包复现 5 种场景，逐条断言"页面会不会被骗"：

| 场景 | 假相机怎么回 | 断言（全过） |
|---|---|---|
| A | restore → `<result>generalerror</result>` | ★0 块上传、★0 声明大小、★不请求重启、★日志写"拒绝进入恢复模式"、★给出"关机再开机" |
| B | restore ok，但状态 `generalerror` | ★传之前就中止（0 块） |
| C | 声明大小回的 `<size>` 与本地差 100 | ★一块都不传 + 日志说"不一致" |
| D | 传完（1 块）后才 `status=generalerror` | ★明确报"没有成功"、★不请求重启 |
| E | `exec_reboot` 回 **202** | ★算"已请求重启"、★不再误报、★提示会自动核对 |

**回归**：37 个脚本 + 3 个审计 **0 失败**（其中 `dv_mpwrite`/`dv_mount` 一度因新检查过严而红 →
把口径收敛成"只认明确报错"后恢复绿）；`按钮=81`、`运行错误=0` 不变。

## 5. 产物

| 项 | 值 |
|---|---|
| 版本 | **v2.10（build 210）** |
| APK | `C:\Users\82302\Desktop\OM-3色彩配方手册.apk`，md5 `1e252174d7a95bf8ed6452c52ba532af` |
| 源码 | `app/base.html` md5 `d8520e410198429ff4d2a318299d9050` |

## 6. 还需真机确认的一件事

相机为什么**一开始就拒绝** restore（`generalerror`）—— 两种可能：
(a) 上一次失败的写会话把相机卡在错误态 → **关机再开机**后应该就好了（新版本会在这一步明确喊出来）；
(b) 还有别的先决条件（比如必须先做一次 `get_mysetbackupstate` 的"done inquiry"，或需要 `get_mysetdatamodekind`）。

请在**关机再开机**后用新版本再写一次：
- 若 ⑥ 变成 `result=ok` → 后面按新顺序走完，重启后日志会自动给"✅ 生效"；
- 若**仍然** `generalerror` → 点 ☰「写入自检（只读）」把日志发我，我按 (b) 继续查（官方那几个接口的调用条件已经从反汇编里拿到了）。
