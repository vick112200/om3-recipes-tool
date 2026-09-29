# SPEC-round26：restore 卡死的自动重试 + 连相机密码自愈（v2.11）

## 0. 用户报的两件事（2026-09-24）

> 「我刚才点击连接相机按钮，没有自动连上 wifi（相机 wifi 已经打开了）。写入报错，日志如下 …
> ⑥ 进入恢复模式：HTTP 200　result=generalerror …
> 另外你要知道**最初在连接相机的写入页签那里选择写入是能重启并写入成功的，其实成功过**，我不知道现在为啥一直失败」

## 1. 先做的最重要一步：拿旧版对比（判断是不是我们改坏的）

把 v1.142（用户说"能成功"那版）的 `writeSlotRecipe` 与现在的 `writeRecipeCore` **逐行对比**：

```
readMySet → patchText → switch_cammode?mode=maintenance
→ request_restoremysetdata?action=restore → set_mysetdatasize?size=
→ send_partialmysetdata（4096 一块，失败重试 3 次、绝不跳过）→ get_mysetrestorestate → exec_reboot
```

**两边逐字一致**（连日志文案都一样）。结论：
**不是我们改坏了协议，是相机侧在拒绝** —— 上一次中断的写入会话把相机的 restore 状态机卡在错误态
（日志里 `get_mysetrestorestate` 一直回 `<status>generalerror</status>`，不是 idle）。

## 2. 对策 A：restore 被拒时**自动重置写入通道**再试一次（新增 `restoreHandshake()`）

```
① restore 被拒（result 明确非 ok）
② switch_cammode.cgi?mode=play      ← 退出维护模式（= 把卡住的会话放掉）
   等 1.5 秒
   switch_cammode.cgi?mode=maintenance ← 重新进入
③ 再试一次 restore
   ✅ 接受 → 继续正常写入（日志："重置通道后相机接受了恢复模式"）
   ❌ 仍被拒 → 中止（0 块上传、不请求重启）+ 建议"把相机**关机再开机**"（卡死的会话只有断电才能清）
```

`writeRecipeCore`（我的配方 / ③ 写入 共用）与 `uploadData`（备份恢复）都走这个握手。
好处：这是**比重启相机快得多**的一次自救；如果它能解开，用户不用每次都去拔电池。

## 3. 对策 B：连相机连不上时，主动问一次密码（相机密码会重发）

用户说"点连接相机按钮没有自动连上 wifi（相机 wifi 已经打开了）"，而日志里 `[自动] 开关是关的` ——
即自动连开关是关的（设计如此）；但**手动点了也没连上**。OM 相机的 Wi-Fi 密码**每次进入 Wi-Fi 模式都可能重发**，
用记住的旧密码就会一直连不上，而 app 以前只是说一句"没能连上"。

现在：原生回 `unavailable/error/failed` 且**有记住的相机**时 → 直接弹一次「连不上？重填一次密码」，
填完记住并自动重连（也可以点「扫二维码（第一次）」自动重填）。同一个失败只问一次，不反复弹。

## 4. 验收（`scripts/dv_writeproto.py` 扩到 7 场景 26 项，全过）

| 场景 | 假相机 | 断言 |
|---|---|---|
| A | restore 永远 generalerror | ★0 块、★0 声明大小、★不重启、★日志说清（含"重置通道重试也失败"） |
| B | 状态 generalerror | ★传之前就中止 |
| C | 声明大小回的 size 不符 | ★一块都不传 + 说明"不一致" |
| D | 传完才报错 | ★明说"这次写入没有成功"、★不重启 |
| E | reboot 202 | ★算"已请求重启"、★不再误报 |
| **F**（新） | 第一次 restore 被拒，**重置通道后**接受 | ★自动重试（2 次）、★确实用了 `mode=play`→`maintenance`、★日志说"重置后接受"、★继续写完、★请求重启 |
| **G**（新） | 重置后**仍**被拒 | ★0 块、★不重启、★日志"仍然被拒"、★给"关机再开机"建议 |

**回归**：36 个脚本 + 3 个审计 **0 失败**；`按钮=81`、`运行错误=0` 不变。

## 5. 产物

| 项 | 值 |
|---|---|
| 版本 | **v2.11（build 211）** |
| APK | `C:\Users\82302\Desktop\OM-3色彩配方手册.apk`，md5 `098e4435c9277aca9716abf3dad0570e` |
| 源码 | `app/base.html` md5 `a86bc84a181a1f7f6cd4f9b89511c286` |

## 6. 请用户做的（按顺序）

1. **把相机彻底关机再开机**（这是清掉卡住会话的唯一可靠办法）
2. 连相机：点「连接相机」；若弹「重填一次密码」→ 照相机屏幕填（或点「扫二维码」）
3. 再写一次：
   - 若 ⑥ 出现"**重置通道后相机接受了恢复模式**"→ 说明自救生效，继续走完即写入成功；
   - 若 ⑥ 仍然 `generalerror`（重置也失败）→ 把日志发我，我继续按反汇编里官方的前置条件查
     （下一个怀疑点：`get_mysetdatamodekind` / `get_mysetbackupstate` 的 done-inquiry 前置）。
