# -*- coding: utf-8 -*-
"""第 49 轮生成器（幂等）· v3.3

用户 2026-09-25（真机反馈，原话）：
  「还是识别不出来，而且画面非常卡顿，我觉得你得考虑下你得方案是不是有问题的。
    如果难度很大就不用做了，因为大家用这个app都有官方app，官方连接一次按理说手机都存的有，
    你就写个指引让用户没用官方app连过得，就连一次，连过得就直接用那个wifi连接按钮就行了，
    就不扫码了，先把扫码隐藏一下」

→ 结论（承认第 48 轮方案有问题）：
  ① 第 48 轮为了"认得出"把取景提到 1280x720、还加了两遍裁剪放大 + 一遍原分辨率整帧
     ⇒ 每轮要跑 2~4 遍 jsQR，最大一帧 1280x720（0.92M 像素，是原来的 3 倍）
     ⇒ **界面被拖卡**，而且**还是认不出**。方案不对，撤掉。
  ② 改走用户给的路子：**扫码隐藏**，给"怎么连相机"的指引
     —— 没连过：用官方 App 连一次（以后手机就记住了）；连过：直接点「连接相机」。
     手动填 SSID/密码（相机屏幕上就有）作为"不想装官方 App"的兜底，仍然留着。

本脚本改 5 处（幂等；判定用只属于新代码的短标记）：
  A. 撤销第 48 轮的"高清取景"：1280x720 → 回到 640x480
  B. 撤销"裁剪放大 ×2/×3 + 每 3 轮原分辨率那遍"：回到「整帧 + 隔一轮中心 60% 裁剪」两遍
     （诊断行/诊断按钮/两条失败提示**保留**：它们几乎不吃 CPU，而且以后要再开扫码时有用）
  C. 隐藏三个扫码入口：`#camGateScan` / `#camScan` / `#camScanHelp`（加 `.hid49`，元素不删）
  D. 首屏换成「怎么连相机」指引（第一次用官方 App 连一次 → 以后直接点「连接相机」）
  E. 底栏第①步不再偷偷启动扫码；`#camManualCard` 直接可见（不再靠"看不到二维码？手动填"展开）
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
P = os.path.join(ROOT, 'app', 'base.html')
LOG = []

s = io.open(P, encoding='utf-8').read()
bak = os.path.join(ROOT, 'app', 'base.before_r49.html')
if not os.path.exists(bak):
    io.open(bak, 'w', encoding='utf-8', newline='').write(s)
    print('回退点已存：app/base.before_r49.html（= v3.2 源码）')


def rep(old, new, tag, marker):
    global s
    if marker in s:
        LOG.append('  · 已改过，跳过：' + tag)
        return
    n = s.count(old)
    if n != 1:
        LOG.append('  ✗ 锚点不唯一（%d 处）：%s' % (n, tag))
        raise SystemExit('锚点不唯一：' + tag)
    s = s.replace(old, new)
    LOG.append('  ✓ ' + tag)


# ================================================================ A. 撤销高清取景
rep(
    "    /* r48（①-a）：原来只要 640x480 —— 拍相机屏幕上那种二维码像素本来就紧：\n"
    "       只写 ideal，机型给不了 720p 就还是原来的分辨率，不会失败。 */\n"
    "    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},\n"
    "        width:{ideal:1280}, height:{ideal:720}}, audio:false})\n",
    "    /* r49：回到 640x480。第 48 轮试过 1280x720 —— 真机反馈「画面非常卡顿」且**还是认不出**，\n"
    "       所以撤掉（见 SPEC-round49.md）。扫码入口已经隐藏，这里保持轻量。 */\n"
    "    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},\n"
    "        width:{ideal:640}, height:{ideal:480}}, audio:false})\n",
    'A：取景分辨率回到 640x480（撤销 1280x720）',
    "width:{ideal:640}, height:{ideal:480}}, audio:false})\n    .then"
)

# ================================================================ B. 撤销放大/原图那几遍
rep(
    "        /* r48（①-b，关键）：原来 sc = Math.min(1, …) —— 注释写着「裁剪后放大」，其实**永远不会 >1**：\n"
    "           640x480 取景里一个只占 1/3 画面的二维码（≈200px、每模块 2~3 像素）从头到尾还是 200px，jsQR 认不出\n"
    "           （用户实测：帧在涨、识别尝试也在涨，就是不认出来）。现在裁剪那几遍允许插值放大到 upMax 倍。 */\n"
    "        function tryDecode(sx, sy, sw, sh, targetW, upMax){\n"
    "          var sc = Math.min(upMax || 1, targetW / Math.max(sw, sh));\n",
    "        /* r49：回到「不放大」。第 48 轮为了让小二维码认出来，试过裁剪后插值放大 ×2/×3 +\n"
    "           每 3 轮一遍原分辨率整帧 —— 真机上**画面非常卡顿而且仍然认不出**（每轮 2~4 遍 jsQR、最大 1280x720）。\n"
    "           撤掉：这里保持 sc ≤ 1（只缩不放），整轮只跑「整帧 + 隔一轮中心裁剪」两遍。 */\n"
    "        function tryDecode(sx, sy, sw, sh, targetW){\n"
    "          var sc = Math.min(1, targetW / Math.max(sw, sh));\n",
    'B1：tryDecode 去掉放大（sc 上限回到 1）',
    'function tryDecode(sx, sy, sw, sh, targetW){'
)

rep(
    "        var MAXNATIVE = 1280;    /* r48：原图那遍的长边上限（再大 jsQR 太吃 CPU） */\n"
    "        function canvasTry(){\n"
    "          if(!(v.readyState === v.HAVE_ENOUGH_DATA && v.videoWidth)) return false;\n"
    "          var VW = v.videoWidth, VH = v.videoHeight;\n"
    "          stat.vw = VW; stat.vh = VH; stat.round++;\n"
    "          /* ① 整帧（大就缩到 MAXW 省 CPU）：二维码本来就占满画面时这一遍就中 */\n"
    "          stat.p1++; if(tryDecode(0, 0, VW, VH, MAXW, 1)) return true;\n"
    "          /* ② 中心 60% 裁剪 + **最多放大 2 倍**：二维码占画面 1/3 左右时靠这遍（r48：以前这遍不放大） */\n"
    "          var cw = Math.round(VW * 0.6), chh = Math.round(VH * 0.6);\n"
    "          stat.p2++;\n"
    "          if(tryDecode(Math.round((VW - cw) / 2), Math.round((VH - chh) / 2), cw, chh, Math.round(MAXW * 1.4), 2)) return true;\n"
    "          /* ③ 隔一轮：中心 40% 裁剪 + **最多放大 3 倍**（手机拿得远、二维码更小） */\n"
    "          if(stat.round % 2 === 0){\n"
    "            var c2 = Math.round(VW * 0.4), h2 = Math.round(VH * 0.4);\n"
    "            stat.p3++;\n"
    "            if(tryDecode(Math.round((VW - c2) / 2), Math.round((VH - h2) / 2), c2, h2, Math.round(MAXW * 1.4), 3)) return true;\n"
    "          }\n"
    "          /* ④ 隔两轮：**原分辨率**整帧（取景比 MAXW 大时才跑）——分辨率是识别率的地基 */\n"
    "          if(stat.round % 3 === 0 && Math.max(VW, VH) > MAXW){\n"
    "            stat.p4++;\n"
    "            if(tryDecode(0, 0, VW, VH, Math.min(VW, MAXNATIVE), 1)) return true;\n"
    "          }\n"
    "          return false;\n"
    "        }\n",
    "        function canvasTry(){\n"
    "          if(!(v.readyState === v.HAVE_ENOUGH_DATA && v.videoWidth)) return false;\n"
    "          var VW = v.videoWidth, VH = v.videoHeight;\n"
    "          stat.vw = VW; stat.vh = VH; stat.round++;\n"
    "          /* ① 整帧：二维码本来就占满画面时这一遍就中（r49：回到只有这一遍 + 下面那遍） */\n"
    "          stat.p1++; if(tryDecode(0, 0, VW, VH, MAXW)) return true;\n"
    "          /* ② 隔一轮：中心 60% 裁剪（不再放大 —— 放大那版把界面拖卡了） */\n"
    "          if(stat.round % 2 === 0){\n"
    "            var cw = Math.round(VW * 0.6), chh = Math.round(VH * 0.6);\n"
    "            stat.p2++;\n"
    "            if(tryDecode(Math.round((VW - cw) / 2), Math.round((VH - chh) / 2), cw, chh, Math.round(MAXW * 1.4))) return true;\n"
    "          }\n"
    "          return false;\n"
    "        }\n",
    'B2：canvasTry 回到两遍（去掉 ×2/×3 放大与「原图」那遍）',
    'stat.p1++; if(tryDecode(0, 0, VW, VH, MAXW)) return true;'
)

rep(
    "        var stat = { frames: 0, tries: 0, lastMs: 0, bdFail: 0,\n"
    "                     vw: 0, vh: 0, round: 0, p1: 0, p2: 0, p3: 0, p4: 0,\n"
    "                     warnNoFrame: 0, warnSlow: 0 };   /* r48：画面尺寸/轮数/各遍计数/两个提示只出一次 */\n",
    "        var stat = { frames: 0, tries: 0, lastMs: 0, bdFail: 0,\n"
    "                     vw: 0, vh: 0, round: 0, p1: 0, p2: 0,\n"
    "                     warnNoFrame: 0, warnSlow: 0 };   /* 画面尺寸/轮数/两遍计数/两个提示只出一次 */\n",
    'B3：stat 去掉放大/原图那两个计数',
    'round: 0, p1: 0, p2: 0,\n'
)

rep(
    "        function statFull(){\n"
    "          return statText() + ' · 轮 ' + stat.round + '（整帧 ' + stat.p1 + ' / 放大×2 ' + stat.p2\n"
    "               + ' / 放大×3 ' + stat.p3 + ' / 原图 ' + stat.p4 + '）';\n"
    "        }\n",
    "        function statFull(){\n"
    "          return statText() + ' · 轮 ' + stat.round + '（整帧 ' + stat.p1 + ' / 裁剪 ' + stat.p2 + '）';\n"
    "        }\n",
    'B4：诊断行只说「整帧/裁剪」两遍',
    "'（整帧 ' + stat.p1 + ' / 裁剪 ' + stat.p2 + '）'"
)

# ================================================================ C. 隐藏扫码入口
rep(
    ".scantop{position:absolute;left:0;right:0;top:0;padding:14px 16px;",
    "/* r49：先把扫码藏起来（用户 2026-09-25：「先把扫码隐藏一下」）。\n"
    "   元素和代码都留着（要再开就把 .hid49 去掉），但界面上不给入口。 */\n"
    ".hid49{display:none !important}\n"
    "/* r49：首屏「怎么连相机」指引 */\n"
    ".camguide49{margin:0 0 12px}\n"
    ".camguide49 p{margin:0 0 10px;font-size:13px;line-height:1.8;color:#cfd6e2}\n"
    ".camguide49 p b{color:#fff}\n"
    ".camguide49 .g49n{font-size:12.5px;color:#9aa3b2;border-left:3px solid #3a4a52;padding-left:10px}\n"
    ".scantop{position:absolute;left:0;right:0;top:0;padding:14px 16px;",
    'C1：新增 .hid49（隐藏扫码入口）+ 指引块样式',
    '.camguide49{margin:0 0 12px}'
)

rep(
    '    <button type="button" class="big" id="camGateScan">扫二维码（第一次）</button>\n'
    '    <button type="button" class="big" id="camGateConn">连接相机</button>\n',
    '    <button type="button" class="big hid49" id="camGateScan">扫二维码（第一次）</button>\n'
    '    <button type="button" class="big" id="camGateConn">连接相机</button>\n',
    'C2：首屏那个「扫二维码（第一次）」按钮隐藏（元素保留）',
    'class="big hid49" id="camGateScan"'
)

rep(
    '    <button type="button" id="camScan" class="camprimary">扫二维码</button>\n'
    '    <button type="button" id="camScanHelp">看不到二维码？手动填</button>\n',
    '    <button type="button" id="camScan" class="camprimary hid49">扫二维码</button>\n'
    '    <button type="button" id="camScanHelp" class="hid49">看不到二维码？手动填</button>\n',
    'C3：折叠区里的「扫二维码 / 看不到二维码？手动填」两个按钮隐藏',
    'class="camprimary hid49" id="camScan"'
)

# ================================================================ D. 首屏换成指引
rep(
    '    <h3>连接相机</h3>\n'
    '    <ol>\n'
    '      <li>相机上：<b>MENU → Wi-Fi/蓝牙 → Wi-Fi 设置</b>，屏幕会出现二维码</li>\n'
    '      <li>手机：点「<b>扫二维码</b>」对着它扫一下（<b>只要第一次</b>）</li>\n'
    '      <li>以后：相机 Wi-Fi 打开后点「<b>连接相机</b>」就行，不用再扫</li>\n'
    '    </ol>\n',
    '    <h3>连接相机</h3>\n'
    '    <div class="camguide49">\n'
    '      <p><b>第一次连这台相机（手机还没记过它）</b><br>\n'
    '        · 用<b>官方 App</b>（OM Image Share）连一次：相机 <b>MENU → Wi-Fi/蓝牙 → 连接到智能手机</b>，\n'
    '          按相机屏幕上的提示连上。<br>\n'
    '        · 连上这一次，<b>手机就记住了这台相机的 Wi-Fi</b> —— 以后不用再动官方 App。</p>\n'
    '      <p><b>以后（已经连过一次）</b><br>\n'
    '        · 相机打开 Wi-Fi 传输，回到这一页直接点下面的「<b>连接相机</b>」就行 —— 不用扫码、不用官方 App。</p>\n'
    '      <p class="g49n">不想装官方 App？相机屏幕上会写 <b>SSID 和密码</b>，\n'
    '        在下面「连不上？更多方式 → <b>手动填 SSID / 密码</b>」里填一次，也一样（填过就记住）。</p>\n'
    '    </div>\n',
    'D：首屏三行「扫码」说明 → 换成「怎么连相机」指引（第一次用官方 App / 以后直接连 / 不想装 App 就手动填）',
    '<div class="camguide49">'
)

# ================================================================ E. 底栏第一步不再启动扫码 + 手动填直接可见
rep(
    "  if(gs) gs.addEventListener('click', function(){ showStep(1); var b = $('camScan'); if(b) b.click(); });\n",
    "  /* r49：这里原来会顺手点一下「扫二维码」把相机打开——扫码隐藏了，就别再偷偷启动它了 */\n"
    "  if(gs) gs.addEventListener('click', function(){ showStep(1); });\n",
    'E1：底栏第①步不再启动扫码',
    "if(gs) gs.addEventListener('click', function(){ showStep(1); });"
)

rep(
    '  <div class="camcard" id="camManualCard" style="display:none">\n',
    '  <div class="camcard" id="camManualCard">\n',
    'E2：手动填卡片直接可见（不再靠「看不到二维码？手动填」展开）',
    '<div class="camcard" id="camManualCard">'
)

# ================================================================ 写出
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('\n'.join(LOG))
print('写出 app/base.html：%.2f MB' % (len(s.encode('utf-8')) / 1048576.0))

print('\n=== 自检 ===')
S = io.open(P, encoding='utf-8').read()
print('还剩下 1280/720 取景：', S.count('width:{ideal:1280}'), '（应为 0）')
print('640x480 取景：', S.count('width:{ideal:640}'), '（应为 1）')
print('还剩下放大/原图那几遍：', S.count('MAXNATIVE') + S.count('upMax'), '（应为 0）')
print('sc 夹回 1：', S.count('Math.min(1, targetW / Math.max(sw, sh))'), '（应为 1）')
print('hid49：', S.count('hid49'), '｜ camguide49：', S.count('camguide49'))
print('扫码入口都带上 hid49：', all(('hid49" id="%s"' % i) in S for i in ['camGateScan', 'camScan', 'camScanHelp']))
print('底栏还会启动扫码吗：', "b.click(); });" in S)
