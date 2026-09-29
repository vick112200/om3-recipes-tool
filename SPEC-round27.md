# SPEC-round27：连相机权限 bug 修复 + 写入自检升级（v2.12）

## 0. 用户真机日志（2026-09-24）

> ```
> 扫到 21 个热点，其中像相机的有 1 个：OM-3-P-BJSA21721(-48dBm)
> 连接 OM-3-P-BJSA21721…（系统可能弹一次"加入网络"）
> 连接失败：dialog:com.om3.handbook was not granted either of these permissions:
>          android.permission.CHANGE_NETWORK_STATE,android.permission.WRITE_SETTINGS
> …
> 　（相机拒绝：generalerror）→ 试一次**重置写入通道**：先退出维护模式再重进…
> 　　① 退出维护模式 switch_cammode?mode=play → HTTP 200
> 　　② 重进维护模式 → HTTP 200
> 　❌ 重置通道后**仍然被拒**（generalerror）
> ```

## 1. 修好了：连不上相机热点 —— **清单里少了 `CHANGE_NETWORK_STATE`**（真 bug）

`connectCamera()` 用 `ConnectivityManager.requestNetwork()` 连相机热点，Android 强制要求
**`CHANGE_NETWORK_STATE`（或 `WRITE_SETTINGS`）**；我们清单里**只声明了 ACCESS_NETWORK_STATE**（读），
所以 `requestNetwork` 直接抛 SecurityException → 系统原文就是用户看到的那句
`was not granted either of these permissions: ...CHANGE_NETWORK_STATE,...WRITE_SETTINGS`。

- 修法：`apk/AndroidManifest.xml` 加 `<uses-permission android:name="android.permission.CHANGE_NETWORK_STATE" />`
  （**普通权限**：安装即给，不弹窗、不需要运行时申请）。
- 已用 `aapt2 dump badging` 验证打出的 APK 里确实有这条权限。
- 页面也补了对应文案：万一还出现这条错误，会直接说"这个版本少声明系统权限，装新版即可修好，
  临时可到系统 Wi-Fi 里手动选那个热点"。

## 2. 「写入自检（只读）」升级 —— 为下一次日志一次问全

现在按顺序问 **8 个只读接口**并**原样打印相机回话（各 200 字）**：

1. `switch_cammode.cgi?mode=maintenance`
2. `get_mysetbackupstate.cgi`
3. `get_mysetdatasize.cgi?kind=current`
4. `get_partialmysetdata.cgi?offset=0&size=256`
5. **`get_mysetrestorestate.cgi`** ← ★关键：**在我们尝试 restore 之前**先看一次
6. `get_mysetdatamodekind.cgi`（官方写前会问的"数据类型"）
7. `get_mysetname.cgi?mode=myset1`
8. `get_mysetname.cgi?mode=current`

最后再单独**试一次"进入恢复模式"**并把相机原话整句打出来，给出结论：
"读取/状态接口都能用 → 问题集中在进入恢复模式这一步"。

### 为什么第 5 步要放在 restore 之前
`get_mysetrestorestate` 如果我们**还没碰 restore** 就已经是 `generalerror`，那就证明
**相机在写入之前就已经卡住了**（只可能靠**关机再开机**清）—— 这能把"相机卡住"和"缺前置条件"两种可能**一次分开**。

## 3. 现状（诚实记录）

- `mode=play → maintenance` 重置**没能解开**用户的相机（真机已试，仍 generalerror）。
- 官方 APK 反汇编确认的顺序/参数与我们一致；v1.142（用户说成功过那版）的写入实现与现在**逐字一致**
  ⇒ 协议、时序都不是原因，**问题在相机侧状态**。
- 下一步分叉（见 §4）：先跑自检拿"restore 之前的状态"，再决定是断电还是继续查前置条件。

## 4. 请用户做的（顺序别颠倒，这能一次分辨原因）

1. **先别重启相机**，用 v2.12 点 ☰→「**写入自检（只读）**」→ 把整段日志发出来
   （重点看第 5 步 `get_mysetrestorestate` 在我们动手前是什么）
2. 然后**关机再开机**相机，重连，再写一次
3. 若**还是**失败：用**官方 OM Image Share** 试着写一次 my-set（你能改一个 Color Profile 再写回）
   - 官方也失败 → 相机/会话侧的问题，继续断电 + 反馈给售后或换卡试；
   - 官方成功 → 说明官方还有我们没复现的步骤，我把日志与官方流程再对一次（届时需要你提供官方的操作录像/抓包）。

## 5. 产物

| 项 | 值 |
|---|---|
| 版本 | **v2.12（build 212）** |
| APK | `C:\Users\82302\Desktop\OM-3色彩配方手册.apk`，md5 `531b62cdea5daa4a4846b0ee8e4241c7` |
| 源码 | `app/base.html` md5 `c124ac35b1b4bc6c7db0a5f17458e6ba`；`apk/AndroidManifest.xml` md5 `9a6529108a84c1b0bd89ed40e85e5b64` |

**回归**：18 个关键脚本 + `verify_all` / `check_app` / `audit_all` / `check_doc` **0 失败**；
`按钮=81`、`运行错误=0` 不变；Java `javac --release 8` 通过；`aapt2 dump badging` 已确认权限在包内。
