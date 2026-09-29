# -*- coding: utf-8 -*-
"""第 97 轮：把「扫码连接」**收起来**（需求方 2026-09-29）+ 顺手修两个"可能让它扫不出"的点

需求方原话：
> 「现在扫码还是扫不出来，你看看怎么回事，实在不行就把扫码连接去掉吧」

根因（详见 SPEC-round97.md §0）：这条链第 48/49/74/79 轮已经反复调过（jsQR + 系统 BarcodeDetector 双路、
反色、裁剪、诊断行、两次超时提示），真机反馈仍是"卡顿 + 认不出"；电脑上能查到的两个**确定**问题是
  ② WebSettings 少了 `setMediaPlaybackRequiresUserGesture(false)`（WebView 里 video.play() 可能被拦，
     表现就是"摄像头拿到了但没有画面"—— OI-09 真机只验过"拿到摄像头 ✓"，从没验过画面）；
  ③ `v.play()` 的 reject 被 `catch(function(){})` 静默吞掉（真机出错日志里一个字都没有）。

本轮做四件事：
  1. **隐藏 3 个扫码入口**（只加 `style="display:none"`，class/节点/逻辑一个不动）：
     `#camGateScan`、`#camScan`、`#camScanHelp`
  2. **把所有"点扫码连接"的指引文案改成手动填 SSID / 密码**（约 15 处）——
     ⚠️ 第 49 轮藏按钮时忘了改文案，页面上还在让用户去点看不见的按钮（SPEC-round74.md 的复盘），这次不能重犯
  3. **Java 一行**：`s.setMediaPlaybackRequiresUserGesture(false);`
  4. **`play()` 失败不再静默**：写日志 + 浮层提示（将来再开扫码时能定位）

显式声明（SPEC-round97.md §2）：新增 id = 0、新增 data-tv = 0；解码器/浮层/诊断行/测试页 ⑨ 一条不删；
数据格式不动；不加权限、不联网。

用法：python scripts/gen_r97.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
MARK = 'r97：'

# ============ ① HTML：隐藏 3 个入口 + 改文案 ============
H1_OLD = ("        <b>情况 A：相机屏幕上有「二维码」</b><br>\n"
          "        　→ 这台相机点下面<b>「扫码连接」</b>，对着二维码即可（系统弹窗点「连接」）。<br>\n"
          "        <b>情况 B：相机屏幕上只有 SSID 和密码，没有二维码</b><br>\n"
          "        　→ 点下面<b>「连不上？更多方式」</b> → <b>「手动填 SSID / 密码」</b>，照抄两格即可。<br>")
H1_NEW = ("        <b>情况 A：相机屏幕上有「二维码」</b><br>\n"
          "        　→ 二维码里装的<b>就是 SSID 和密码</b>：看相机屏幕上写的那两行，\n"
          "用下面<b>「连不上？更多方式」→「手动填 SSID / 密码」</b>抄进去（填一次就记住）。<br>\n"
          "        　<span style=\"color:#8b93a1\">（本版 App 的扫码识别不稳：相机屏幕小、有反光，\n"
          "扫半天扫不出来反而耽误事，所以先把「扫码连接」收起来了 —— 用同样的两格手填就行。）</span><br>\n"
          "        <b>情况 B：相机屏幕上只有 SSID 和密码，没有二维码</b><br>\n"
          "        　→ 同上：点下面<b>「连不上？更多方式」</b> → <b>「手动填 SSID / 密码」</b>，照抄两格即可。<br>")

H2_OLD = ("    <!-- r74：扫码放回来，但**往后放**：排在「连接相机」之后、样式降一级（.gho 灰底）。\n"
          "       第 49 轮是把它整个藏起来（.hid49），而下面的提示文案还在让用户去点它（指向一个看不见的按钮）。\n"
          "       要再藏回去：给这三个按钮加回 class=\"hid49\" 即可（.hid49 那条 CSS 保留着）。 -->")
H2_NEW = ("    <!-- r97：**扫码入口又收起来了**（需求方 2026-09-29：「现在扫码还是扫不出来，实在不行就把扫码连接去掉吧」）。\n"
          "       只加 style=\"display:none\"（class/节点/逻辑一个没动），所以：\n"
          "         · 想再开：删掉这 3 处 style —— ① #camGateScan（下一行）② #camScan ③ #camScanHelp；\n"
          "           并把本页「情况 A/B」指引文案改回「扫码连接」那一版（第 74 轮那版在 git 历史里）。\n"
          "         · 解码代码（jsQR / 全屏浮层 #scanMask / 诊断行 #scanStat / 测试页 ⑨ 自检）**一条没删**。\n"
          "       第 49 轮藏的时候忘了改指引文案，页面上还让用户点一个看不见的按钮 —— 这次文案一起改了。 -->\n"
          "    <!-- r97：扫码入口（隐藏）—— 想开就删掉这行末尾的 style -->")
H3_OLD = ("    <button type=\"button\" class=\"big gho\" id=\"camGateScan\">扫码连接（忘了密码时用）</button>")
H3_NEW = ("    <button type=\"button\" class=\"big gho\" id=\"camGateScan\" style=\"display:none\">扫码连接（忘了密码时用）</button>")

H4_OLD = "<p class=\"sub\">手机直连 OM-3 写配方 · 扫码连一次，以后自动连</p>"
H4_NEW = "<p class=\"sub\">手机直连 OM-3 写配方 · 手填一次 SSID / 密码，以后自动连</p>"

H5_OLD = "    <summary>连接详情（扫码 / 手动填 / 检测 / 忘掉相机）—— 点开看细节</summary>"
H5_NEW = "    <summary>连接详情（手动填 / 检测 / 忘掉相机）—— 点开看细节</summary>"

H6_OLD = ("    <div class=\"camhd\">扫相机屏幕上的二维码</div>\n"
          "    <div class=\"camout\" style=\"border-color:#33507e\">\n"
          "      <b>连接流程（照这个顺序）：</b><br>\n"
          "      1. 相机上：菜单 → Wi-Fi / 蓝牙 → 切到 <b>Wi-Fi 传输状态</b>（屏幕显示二维码 / SSID）<br>\n"
          "      2. 手机：点「扫码连接」扫相机屏幕的二维码（或手动填 SSID + 密码）<br>\n"
          "      3. 系统弹窗点「连接」→ 手机连上相机热点（记住后无需重复）<br>\n"
          "      4. 显示 <b>OM-3 · 已连接</b> 后，就能备份 / 写入配方<br>\n"
          "      <span style=\"color:#d8b45a\">相机一关机或退出传输态，手机会自动断，状态球变回\"未连接\"。</span>\n"
          "    </div>\n"
          "    <p class=\"camnote\">相机上：<code>MENU → Wi-Fi/蓝牙 → Wi-Fi 设置</code>（或屏幕上「连接智能手机」那一屏），会出现二维码。<br>\n"
          "      对着它扫一下，密码就自动填好并交给系统 —— <b>扫这一次就够：以后相机开机 Wi-Fi 打开，手机会自动连上</b>，不用再扫、也不用装官方 app。</p>\n"
          "    <button type=\"button\" id=\"camScan\" class=\"camprimary\">扫二维码</button>\n"
          "    <button type=\"button\" id=\"camScanHelp\">看不到二维码？手动填</button>\n"
          "    <div class=\"camout\" id=\"camScanOut\">还没扫。相机没显示二维码的话，点右边「手动填」也行（SSID 和密码相机屏幕上都有写）。</div>")
H6_NEW = ("    <div class=\"camhd\">手动填 SSID / 密码（这张卡原来是「扫二维码」）</div>\n"
          "    <div class=\"camout\" style=\"border-color:#33507e\">\n"
          "      <b>连接流程（照这个顺序）：</b><br>\n"
          "      1. 相机上：菜单 → Wi-Fi / 蓝牙 → 切到 <b>Wi-Fi 传输状态</b>（屏幕显示 SSID / 密码，有的还显示二维码）<br>\n"
          "      2. 手机：把相机屏幕上的 <b>SSID</b> 和<b>密码</b>抄到下面「手动填 SSID / 密码」那两格<br>\n"
          "      3. 系统弹窗点「连接」→ 手机连上相机热点（记住后无需重复）<br>\n"
          "      4. 显示 <b>OM-3 · 已连接</b> 后，就能备份 / 写入配方<br>\n"
          "      <span style=\"color:#d8b45a\">相机一关机或退出传输态，手机会自动断，状态球变回\"未连接\"。</span>\n"
          "    </div>\n"
          "    <p class=\"camnote\">相机上：<code>MENU → Wi-Fi/蓝牙 → Wi-Fi 设置</code>（或屏幕上「连接智能手机」那一屏），SSID 和密码都写在屏幕上。<br>\n"
          "      二维码里装的也就是这两个值 —— <b>手填一次就够：以后相机开机 Wi-Fi 打开，手机会自动连上</b>，不用再填、也不用装官方 app。</p>\n"
          "    <!-- r97：扫码入口（隐藏）—— 想开就删掉下面两行末尾的 style -->\n"
          "    <button type=\"button\" id=\"camScan\" class=\"camprimary\" style=\"display:none\">扫二维码</button>\n"
          "    <button type=\"button\" id=\"camScanHelp\" style=\"display:none\">看不到二维码？手动填</button>\n"
          "    <div class=\"camout\" id=\"camScanOut\">扫码这版先收起来了（相机屏幕小、有反光，识别不稳）。<b>照相机屏幕上写的 SSID / 密码，填到下面「手动填 SSID / 密码」那两格就行。</b></div>")

# ============ ② JS 里的运行期文案 ============
J1_OLD = "      el.textContent = '还没记住相机：扫一次二维码，或手动填 SSID / 密码后点「记住它」。';"
J1_NEW = "      el.textContent = '还没记住相机：把相机屏幕上的 SSID / 密码填到「手动填」那两格，再点「记住它」。';"

J2_OLD = "        log('[连相机] 连不上 ' + sv.ssid + '：可能是密码变了。可以：① 点「扫码连接（忘了密码时用）」自动重填；② 点下面填新密码。', 'warn');"
J2_NEW = "        log('[连相机] 连不上 ' + sv.ssid + '：可能是密码变了（相机每次进 Wi-Fi 模式都可能重发）。可以：① 点「手动填 SSID / 密码」填一遍新密码（相机屏幕上写着）；② 直接在弹窗里填。', 'warn');"

J3_OLD = "            body: '相机屏幕上（Wi-Fi 设置那一屏）写着当前密码。填一次就记住了，以后自动用这个。\\n也可以点「扫二维码」让它自动填。',"
J3_NEW = "            body: '相机屏幕上（Wi-Fi 设置那一屏）写着当前密码。填一次就记住了，以后自动用这个。',"

J4_OLD = "              if(!pw){ camOut('没填密码 —— 也可以点「扫码连接（忘了密码时用）」让它自动填。', 'warn'); return; }"
J4_NEW = "              if(!pw){ camOut('没填密码 —— 相机屏幕上（Wi-Fi 设置那一屏）写着当前密码，再看一眼。', 'warn'); return; }"

J5_OLD = "    if(!ssid){ camOut('先扫二维码，或把 SSID 填上。', 'warn'); return 'no_ssid'; }"
J5_NEW = "    if(!ssid){ camOut('先把 SSID 填上（相机屏幕上写着）。', 'warn'); return 'no_ssid'; }"

J6_OLD = "      else if(!camSaved() || !camSaved().ssid) nt.textContent = '（还没记住相机 —— 先扫一次二维码或手填 SSID）';"
J6_NEW = "      else if(!camSaved() || !camSaved().ssid) nt.textContent = '（还没记住相机 —— 先手动填 SSID / 密码）';"

J7_OLD = ("      L.push('先让相机开着：<b>MENU → Wi-Fi/蓝牙</b> 里把 Wi-Fi 打到「Wi-Fi 传输状态」（屏幕出现二维码）。'\n"
          "           + '手机这边点上面①「扫二维码」或「连接相机」。');")
J7_NEW = ("      L.push('先让相机开着：<b>MENU → Wi-Fi/蓝牙</b> 里把 Wi-Fi 打到「Wi-Fi 传输状态」（屏幕出现 SSID / 密码）。'\n"
          "           + '手机这边点「连接相机」，或到「连不上？更多方式」里手动填 SSID / 密码。');")

J8_OLD = ("      log('[自动] 试了 ' + AUTO_MAX + ' 次都没连上 —— 先确认：① 相机开着 Wi-Fi（MENU → Wi-Fi/蓝牙）② 就在旁边 ③ 或者用「扫二维码」', 'warn');\n"
          "      camOut('自动连接没成功（试了 ' + AUTO_MAX + ' 次）。用上面「扫二维码」最稳；连过一次以后系统会记住。', 'warn');")
J8_NEW = ("      log('[自动] 试了 ' + AUTO_MAX + ' 次都没连上 —— 先确认：① 相机开着 Wi-Fi（MENU → Wi-Fi/蓝牙）② 就在旁边 ③ 或者手动填 SSID / 密码', 'warn');\n"
          "      camOut('自动连接没成功（试了 ' + AUTO_MAX + ' 次）。到「连不上？更多方式」里手动填 SSID / 密码最稳；连过一次以后系统会记住。', 'warn');")

J9_OLD = "        var p = v.play(); if(p && p.catch) p.catch(function(){});"
J9_NEW = ("        /* r97：play() 的失败原来被**静默吞掉** —— 真机上若 WebView 拦了自动播放（\"必须有用户手势\"），\n"
          "           用户只看到黑屏、日志里一个字都没有，这就是\"扫不出来\"里最难查的一种。现在写进日志 + 浮层。 */\n"
          "        var p = v.play(); if(p && p.catch) p.catch(function(e2){\n"
          "          var _why = (e2 && e2.name) ? e2.name : String(e2);\n"
          "          try{ log('[扫码] 画面播不出来（' + _why + '）—— 摄像头拿到了但画面没进来', 'warn'); }catch(x2){}\n"
          "          scanSay('摄像头起来了但画面播不出来（' + _why + '）—— 把日志发我：☰ → 测试页 → 分享日志。');\n"
          "        });")

J10_OLD = ("      step('没看到相机 Wi-Fi。**App 不会替你开相机 Wi-Fi** —— 请在相机上进入传输状态'\n"
           "           + '（MENU → Wi-Fi/蓝牙 → 连接到智能手机），再点「连接相机」（忘了密码就点「扫码连接」）', 'warn');")
J10_NEW = ("      step('没看到相机 Wi-Fi。**App 不会替你开相机 Wi-Fi** —— 请在相机上进入传输状态'\n"
           "           + '（MENU → Wi-Fi/蓝牙 → 连接到智能手机），再点「连接相机」（忘了密码就手动填 SSID / 密码）', 'warn');")

J11_OLD = ("        step('已经交给系统了 —— 连上后这里会自动「检测相机」；'\n"
           "           + '若一直连不上，点下面「扫码连接（忘了密码时用）」最稳（相机屏幕上那个码）');")
J11_NEW = ("        step('已经交给系统了 —— 连上后这里会自动「检测相机」；'\n"
           "           + '若一直连不上，到「连不上？更多方式」里手动填 SSID / 密码最稳（相机屏幕上写着）');")
J12_OLD = ("      step('已经交给系统了 —— 连上后这里会自动「检测相机」；'\n"
           "         + '若一直连不上，点下面「扫码连接（忘了密码时用）」最稳（相机屏幕上那个码）');")
J12_NEW = ("      step('已经交给系统了 —— 连上后这里会自动「检测相机」；'\n"
           "         + '若一直连不上，到「连不上？更多方式」里手动填 SSID / 密码最稳（相机屏幕上写着）');")
J13_OLD = ("             + ' → 点下面「扫码连接（忘了密码时用）」最稳；或到相机上确认 Wi-Fi 已打到「Wi-Fi 传输状态」', 'warn');")
J13_NEW = ("             + ' → 到「连不上？更多方式」里手动填 SSID / 密码最稳；或到相机上确认 Wi-Fi 已打到「Wi-Fi 传输状态」', 'warn');")

# ============ ③ Java：允许无手势播放 ============
M_OLD = "        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);"
M_NEW = ("        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);\n"
         "        /* r97：WebView 默认\"播放必须由用户手势触发\" → 摄像头流的 video.play() 可能被拦，\n"
         "           表现就是\"摄像头拿到了但没有画面\"（扫码一直认不出可能就是这个）。关掉这条限制。 */\n"
         "        s.setMediaPlaybackRequiresUserGesture(false);")


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    steps = []
    skipped = []
    try:
        pairs = [('H1 首屏 A/B 指引', H1_OLD, H1_NEW), ('H2 r74 注释', H2_OLD, H2_NEW),
                 ('H3 camGateScan', H3_OLD, H3_NEW), ('H4 副标题', H4_OLD, H4_NEW),
                 ('H5 折叠 summary', H5_OLD, H5_NEW), ('H6 扫码卡', H6_OLD, H6_NEW),
                 ('J1 还没记住相机', J1_OLD, J1_NEW), ('J2 连不上日志', J2_OLD, J2_NEW),
                 ('J3 重填密码弹窗', J3_OLD, J3_NEW), ('J4 没填密码', J4_OLD, J4_NEW),
                 ('J5 没 SSID', J5_OLD, J5_NEW), ('J6 自动连提示', J6_OLD, J6_NEW),
                 ('J7 状态提示', J7_OLD, J7_NEW), ('J8 自动连接失败', J8_OLD, J8_NEW),
                 ('J9 play 失败不再静默', J9_OLD, J9_NEW), ('J10 蓝牙提示', J10_OLD, J10_NEW),
                 ('J11 已交给系统·8空格', J11_OLD, J11_NEW), ('J12 已交给系统·6空格', J12_OLD, J12_NEW),
                 ('J13 看门狗 30 秒', J13_OLD, J13_NEW)]
        # 逐条幂等：**已经改过的条目**跳过（按"旧锚点没了 + 新文本已在"判定），没改的按"旧锚点恰好 1 处"替换。
        # 第 97 轮第一次跑完后才发现还有 3 处文案在指扫码（J11/J12/J13），就是靠这条补进去的。
        for name, old, new in pairs:
            if old not in html:
                if new[:24] in html:
                    skipped.append(name)
                    continue
                raise AssertionError('%s：旧锚点不在了，新文本也没找到（页面被别的改动动过？）' % name)
            n = html.count(old)
            if n != 1:
                raise AssertionError('%s 的锚点不是 1 处（%d 处）' % (name, n))
            html = html.replace(old, new, 1)
            steps.append(name + ' ✓')
        java = io.open(JAVA, encoding='utf-8').read()
        if java.count('setMediaPlaybackRequiresUserGesture(false);') == 0:
            if java.count('setMediaPlaybackRequiresUserGesture') != 0:
                raise AssertionError('Java 里已经有 setMediaPlaybackRequiresUserGesture 了（但不是我们要的那行）')
            if java.count(M_OLD) != 1:
                raise AssertionError('Java 的 setMixedContentMode 锚点不是 1 处（%d）' % java.count(M_OLD))
            java = java.replace(M_OLD, M_NEW, 1)
            steps.append('Java：setMediaPlaybackRequiresUserGesture(false) ✓')
        else:
            skipped.append('Java')

        checks = [
            (html.count('id="camGateScan"') == 1 and 'id="camGateScan" style="display:none"' in html,
             '#camGateScan 的 style 没加上'),
            (html.count('id="camScan" class="camprimary" style="display:none"') == 1, '#camScan 的 style 没加上'),
            (html.count('id="camScanHelp" style="display:none"') == 1, '#camScanHelp 的 style 没加上'),
            (html.count('style="display:none"') - html.count('id="camGateScan" style="display:none"')
             - html.count('id="camScan" class="camprimary" style="display:none"')
             - html.count('id="camScanHelp" style="display:none"') >= 0, '（内部一致性）'),
            ('data-tv="uv-qr"' in html, '测试页 ⑨ 扫码自检被删了（不该删）'),
            ('window.__om3startScan = startScanNow;' in html, '扫码驱动入口被删了（不该删）'),
            ('id="scanMask"' in html and 'id="scanStat"' in html, '扫码浮层/诊断行被删了（不该删）'),
            ('画面播不出来' in html, 'play() 失败的提示没写上'),
            ('class="big gho" id="camGateScan" style="display:none">扫码连接（忘了密码时用）' in html,
             'camGateScan 的文案/class 被动了（应该只加 style）'),
            ('点下面<b>「扫码连接」</b>' not in html and '忘了密码就点「扫码连接」' not in html
             and '点上面①「扫二维码」' not in html, '页面里还有指向"看不见的扫码按钮"的祈使句'),
            (html.count('扫二维码」最稳') == 0, '还有"扫二维码最稳"这种旧指引'),
            ('手动填 SSID / 密码' in html, '手动填这条路的指引没写上'),
            (java.count('setMediaPlaybackRequiresUserGesture(false);') == 1, 'Java 那行不是 1 处'),
            (java.count('shouldOverrideUrlLoading') == 1, 'Java 第 95 轮那段被动了（不该动）'),
        ]
        bad = [m for ok, m in checks if not ok]
        if bad:
            raise AssertionError('；'.join(bad))
    except (AssertionError, ValueError) as e:
        print('[r97] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r97] --check 通过（未写盘）：')
        for s in steps:
            print('   · ' + s)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(html)
    io.open(JAVA, 'w', encoding='utf-8', newline='').write(java)
    print('[r97] ✓ %d 步：' % len(steps))
    for s in steps:
        print('   · ' + s)
    if skipped:
        print('[r97] 已经是目标状态、跳过的 %d 条：%s' % (len(skipped), '、'.join(skipped)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
