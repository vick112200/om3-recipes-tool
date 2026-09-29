# -*- coding: utf-8 -*-
"""第 98 轮：**连接相机页合并成一屏**（需求方 2026-09-29「现在连接相机上面一块下面一块，你觉得合适不」
→ 我判断"不合适"，需求方选了「合并成一屏（推荐）」）

现状（无头实测 412px）：`#camGateOff` 高 **793px**（全是说明文字）+ 下面 `.wrap` 189px（`<h1>导入相机</h1>`），
看着就是"上面一块下面一块"。毛病：一屏两个大标题、两个「连接相机」按钮、状态条被说明文字推到屏外。

本轮做 6 件事（**只改结构/文案，Java 一行不改、id 一个不删**）：
  1. 标题统一：`<h3>连接相机</h3>` 升为 `<h1>`；删掉 `.wrap` 里的 `<h1>导入相机</h1>` + `.sub`，换一行小字说明两块关系；
  2. 「怎么连」（A/B/C 对号入座）**收进折叠**（默认收起）；原来嵌在里面的「详细说明」折叠**拎出来同级并列**（不嵌套）；
  3. `#camGateManual`（手动填 SSID / 密码）**从折叠搬到首屏**（扫码收起后它是第二入口）；
  4. 去重：`#camV1` 里那张「连接 / 断开」卡改名「断开 / 忘掉相机」，`#camConnect` 隐藏（节点/逻辑保留）；
  5. 「蓝牙唤醒」折叠 `#camLinkFold` 整格隐藏（第 92 轮已定"不要蓝牙开 Wi-Fi"）；
  6. 清掉 6 处"点扫二维码"的残留文案（含**条件显示**的 `#gateHintD`）。

显式声明：**新增 id = 0、新增 data-tv = 0**；老 id 一个不少；
DOM 只搬两处（`.camguide49` 进折叠 + `#camGateManual` 上首屏）；扫码解码代码/浮层不动；不加权限、不联网。

用法：python scripts/gen_r98.py [--check]
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')

# ============ ① 标题统一 ============
T1_OLD = "    <h3>连接相机</h3>"
T1_NEW = "    <h1>连接相机</h1>"

T2_OLD = ("<h1>导入相机</h1>\n"
          "<p class=\"sub\">手机直连 OM-3 写配方 · 手填一次 SSID / 密码，以后自动连</p>")
T2_NEW = ("<!-- r98：这里原来是第二个大标题「导入相机」—— 一屏两个标题、看着像\"上面一块下面一块\"（需求方 2026-09-29）。\n"
          "     现在只留一行小字，把\"这两块是什么关系\"讲清楚。 -->\n"
          "<div style=\"color:#9aa3b2;font-size:12.5px;line-height:1.7;margin:2px 0 8px\">"
          "上面那块是「怎么连」；<b>连上之后</b>，下面这块才是「检测相机 · 备份 · 写配方」。</div>")

# ============ ②/③ 折叠重组（程序化搬块，见 main） ============
CG_MARK = '    <div class="camguide49">'
DF_MARK = '      <details class="fold fnote" style="margin-top:10px">'
CONN_LINE = '    <button type="button" class="big" id="camGateConn">连接相机</button>\n'
HOW_SIG = '<summary>怎么连？看相机屏幕上是什么'

# ============ ④ 去重：连接 / 断开 卡 ============
K_OLD = ("    <div class=\"camhd\">连接 / 断开</div>\n"
         "    <div class=\"camout\" id=\"camSaved\"></div>\n"
         "    <button type=\"button\" id=\"camConnect\" class=\"camprimary\">连接相机</button>\n"
         "    <button type=\"button\" id=\"camDisconnect\">断开（回到原来的 Wi-Fi）</button>\n"
         "    <button type=\"button\" id=\"camForgetSaved\" class=\"camghost\">忘掉这台相机</button>\n"
         "    <div class=\"camout\" id=\"camConnectOut\">扫过一次之后，这里会记住这台相机 —— 下次直接点「连接相机」就行，不用再扫。\n"
         "连上后相机的设置写入会走这条连接；点「断开」或退出 app，手机会自动回到原来的 Wi-Fi。</div>")
K_NEW = ("    <div class=\"camhd\">断开 / 忘掉相机</div>\n"
         "    <div class=\"camout\" id=\"camSaved\"></div>\n"
         "    <!-- r98：这个「连接相机」按钮跟首屏那个是同一件事（都走 connectNow）→ **去重**：只隐藏它\n"
         "         （id / 事件 / 测试页的 tvSaved 都照旧，节点还在）。首屏那个才是唯一主入口。 -->\n"
         "    <button type=\"button\" id=\"camConnect\" class=\"camprimary\" style=\"display:none\">连接相机</button>\n"
         "    <button type=\"button\" id=\"camDisconnect\">断开（回到原来的 Wi-Fi）</button>\n"
         "    <button type=\"button\" id=\"camForgetSaved\" class=\"camghost\">忘掉这台相机</button>\n"
         "    <div class=\"camout\" id=\"camConnectOut\">连过一次之后，这里会记住这台相机 —— 下次在首屏点「连接相机」就行。\n"
         "连上后相机的设置写入会走这条连接；点「断开」或退出 app，手机会自动回到原来的 Wi-Fi。</div>")

# ============ ⑤ 蓝牙唤醒整格隐藏 ============
B_OLD = '  <details class="fold cfold" id="camLinkFold">'
B_NEW = ('  <!-- r98：需求方第 92 轮已定「不要蓝牙开相机 Wi-Fi，以后都手动开」→ 这格整块隐藏\n'
         '       （节点 / id / 逻辑全保留，想再开删掉下面的 style 即可）。 -->\n'
         '  <details class="fold cfold" id="camLinkFold" style="display:none">')

# ============ ⑥ 残留文案 ============
C_OLD = [
    ("      camOut('相机权限被拒绝了：设置 → 应用 → 权限 → 相机，允许后再点「扫二维码」。', 'warn');",
     "      camOut('相机权限被拒绝了：设置 → 应用 → 权限 → 相机，允许后再试。', 'warn');"),
    ("    if(n === 34) return '34 = 蓝牙口令错（要口令认证：相机屏幕「蓝牙配对」那串，或扫二维码自动填）'",
     "    if(n === 34) return '34 = 蓝牙口令错（要口令认证：相机屏幕「蓝牙配对」那串，填进「① 填蓝牙口令」）'"),
    ("              + '若相机那边没动作，多半要先把**蓝牙口令**给它（扫二维码会自动填）', 'warn');",
     "              + '若相机那边没动作，多半要先把**蓝牙口令**给它（口令在相机屏幕上，填进「① 填蓝牙口令」）', 'warn');"),
    ("      if(!pw){ say('没填密码 → 不连（不猜密码；也可以点「扫二维码」让它自动填）', 'warn'); return; }",
     "      if(!pw){ say('没填密码 → 不连（不猜密码；相机屏幕上写着当前密码）', 'warn'); return; }"),
    ("      camOut('扫码等太久，已经关掉了。再点一次「扫二维码」或直接手动填。', 'warn');",
     "      camOut('扫码等太久，已经关掉了（扫码入口已收起，请手动填 SSID / 密码）。', 'warn');"),
    ("<div class=\"gatehint\" id=\"gateHintD\">相机还没连上 —— 先用上面①「扫二维码」或「连接相机」。连上后这里才能备份 / 写入 / 记录</div>",
     "<div class=\"gatehint\" id=\"gateHintD\">相机还没连上 —— 先在「连接相机」页点「连接相机」（忘了密码就点「手动填 SSID / 密码」）。连上后这里才能备份 / 写入 / 记录</div>"),
    ("    <div class=\"camhd\">手动填 SSID / 密码（这张卡原来是「扫二维码」）</div>",
     "    <div class=\"camhd\">手动填 SSID / 密码</div>"),
    # 折叠③里那句"详细说明"里的旧说法（"不用扫码"）
    ("        · 相机打开 Wi-Fi 传输，回到这一页直接点下面的「<b>连接相机</b>」就行 —— 不用扫码、不用官方 App。</p>",
     "        · 相机打开 Wi-Fi 传输，回到这一页直接点上面的「<b>连接相机</b>」就行 —— 不用装官方 App。</p>"),
    # 全库体检顺手逮到的：测试页那句**用户看得见**的文案里带日期（用户硬约束：界面上不许出现日期）
    ("<b>别用「下载日志文件」</b>：2026-09-28 真机实测 —— 安卓 WebView 不接管下载，点了不会有文件",
     "<b>别用「下载日志文件」</b>：真机实测 —— 安卓 WebView 不接管下载，点了不会有文件"),
    # 同一条体检逮到的第二处（测试页手动控制台的说明）
    ("真机实测（2026-09-29）：相机收到并回执，但**不执行**「リモコンモード」",
     "真机实测：相机收到并回执，但**不执行**「リモコンモード」"),
]


def balance(html, start, tag='div'):
    """从 start（某个 <tag ...> 的起点）起按同类标签配平，返回 [start, end) 的 end。"""
    depth = 0
    for m in re.finditer(r'<%s\b|</%s>' % (tag, tag), html[start:]):
        depth += 1 if m.group(0).startswith('<%s' % tag) else -1
        if depth == 0:
            return start + m.end()
    raise AssertionError('配平失败（%s @ %d）' % (tag, start))


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    steps, skipped = [], []
    try:
        # ---------- ①②③：搬块（.camguide49 进折叠 + 详细说明拆出 + 手动填上首屏）----------
        if HOW_SIG in html:
            skipped.append('②③ 折叠重组')
        else:
            for mark, name in ((CG_MARK, '.camguide49'), (DF_MARK, '详细说明折叠'), (CONN_LINE, '#camGateConn')):
                if html.count(mark) != 1:
                    raise AssertionError('%s 锚点不是 1 处（%d）' % (name, html.count(mark)))
            i = html.index(CG_MARK)
            j = balance(html, i, 'div')
            blk = html[i:j]
            p = blk.index(DF_MARK)
            q = balance(blk, p, 'details')
            keep = blk[:p] + blk[q:]                      # 去掉「详细说明」折叠后的 .camguide49
            detail = blk[p:q]                             # 那个折叠原样留着，等下同级放回
            if '<details' in keep:
                raise AssertionError('指引块里还有别的折叠（会有嵌套，先看代码）')
            html = html[:i] + html[j:]                    # ① 先把原块从首屏摘掉

            # ② 折叠③里那个手动填按钮删掉（它要上首屏；id 不能重复）
            man_line = '        <button type="button" class="gho" id="camGateManual">手动填 SSID / 密码</button>\n'
            if html.count(man_line) != 1:
                raise AssertionError('折叠里的 #camGateManual 不是 1 处（%d）' % html.count(man_line))
            html = html.replace(man_line, '        <!-- r98：#camGateManual 搬到首屏了（扫码头收起后它是第二入口）-->\n', 1)

            # ③ 在「连接相机」按钮之后插入：手动填按钮 + 「怎么连」折叠 + 「详细说明」折叠（同级）
            ins = ('    <button type="button" class="big gho" id="camGateManual">手动填 SSID / 密码</button>\n'
                   '    <!-- r98：首屏原来 793px 全是说明文字（按钮和下面的状态条被推到屏幕外，'
                   '需求方说\"上面一块下面一块\"）\n'
                   '         → 「怎么连」收进这个折叠（默认收起）；「详细说明」从它里面拎出来**同级并列**，'
                   '免得折叠套折叠。 -->\n'
                   '    <details class="fold fnote" style="margin-top:8px">\n'
                   '      <summary>怎么连？看相机屏幕上是什么 · 对号入座（点开）</summary>\n'
                   '      <div class="foldbody">\n'
                   + keep +
                   '      </div>\n'
                   '    </details>\n'
                   + detail + '\n')
            if html.count(CONN_LINE) != 1:
                raise AssertionError('#camGateConn 行不是 1 处')
            html = html.replace(CONN_LINE, CONN_LINE + ins, 1)
            steps.append('②③ 指引块进折叠 + 手动填上首屏')

        # ---------- ① 标题 ----------
        for name, old, new in ([('① h1 升格', T1_OLD, T1_NEW), ('① 删「导入相机」标题', T2_OLD, T2_NEW)] +
                               [('⑥ 文案%d' % (k + 1), o, n) for k, (o, n) in enumerate(C_OLD)] +
                               [('④ 连接/断开卡去重', K_OLD, K_NEW), ('⑤ 蓝牙唤醒隐藏', B_OLD, B_NEW)]):
            if old not in html:
                if new[:24] in html:
                    skipped.append(name)
                    continue
                raise AssertionError('%s：旧锚点不在了，新文本也没找到' % name)
            if html.count(old) != 1:
                raise AssertionError('%s 锚点不是 1 处（%d）' % (name, html.count(old)))
            html = html.replace(old, new, 1)
            steps.append(name + ' ✓')

        checks = [
            (html.count('<h1>连接相机</h1>') == 1, '没有唯一的 <h1>连接相机</h1>'),
            ('导入相机</h1>' not in html or html.count('导入相机</h1>') == 0, '「导入相机」大标题还在'),
            (HOW_SIG in html, '「怎么连」折叠没写上'),
            ('class="big gho" id="camGateManual"' in html, '手动填按钮没上首屏'),
            (html.count('id="camGateManual"') == 1, '#camGateManual 不止一处（id 冲突）'),
            (html.count('<div class="camguide49">') == 1, '.camguide49 容器没了（老探针静态断言要它）'),
            ('id="camConnect" class="camprimary" style="display:none"' in html, '#camConnect 没隐藏'),
            ('id="camLinkFold" style="display:none"' in html, '#camLinkFold 没隐藏'),
            ('扫二维码」最稳' not in html and '点「扫二维码」' not in html, '还有"点扫二维码"的祈使句'),
            ('先用上面①「扫二维码」' not in html, 'gateHintD 那句旧文案还在'),
            (html.count('r98：') >= 5, 'r98 标记太少（生成脚本改过的地方应留下标记）'),
        ]
        bad = [m for ok, m in checks if not ok]
        if bad:
            raise AssertionError('；'.join(bad))
    except (AssertionError, ValueError) as e:
        print('[r98] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r98] --check 通过（未写盘）：')
        for s in steps + (['（已跳过：%s）' % '、'.join(skipped)] if skipped else []):
            print('   · ' + s)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(html)
    print('[r98] ✓ %d 步：' % len(steps))
    for s in steps:
        print('   · ' + s)
    if skipped:
        print('[r98] 已经改过、跳过的 %d 条：%s' % (len(skipped), '、'.join(skipped)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
