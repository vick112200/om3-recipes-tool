# -*- coding: utf-8 -*-
"""第 92 轮：**不做"蓝牙开相机 Wi-Fi"了 + 连接页瘦身**（需求方 2026-09-29 决定）

需求方原话：
> 「做不了是吧，那就不要蓝牙打开wifi了，以后都手动打开wifi，把连接页面优化一下，多余的该去掉去掉」

依据（`SPEC-round91.md` §4）：帧能到相机（有回执）、相机也会答 `0x0F01`，
但官方那条开 Wi-Fi 命令 `0x1D01{0x02}` 相机**只回执、不应答** → 官方判据下同样算失败。**功能放弃。**

## 本轮改动（页面 only）

1. **连接页（paneD）瘦身**：把两块"诊断用"的东西**整块搬到测试页（paneT）**：
   - 「蓝牙手动控制台」（状态框 `cvstate` + 四按钮 + 回答键 + 口令 `cv-pass` + `.cvnote`）；
   - 整张「蓝牙工具（高级）」卡（`id="bleCard"`）。
   两块**只换位置，`data-tv`/`id` 一个都不动**（探针按选择器找，不依赖位置）。
2. **文案讲实话**（② 不再承诺开 Wi-Fi）：见 REP。
3. 连接页顶部「先看相机屏幕上是什么，对号入座」保持（第 79 轮那套 A/B/C 分支仍然准）。

## 显式声明

- 涉及：`app/base.html`、`scripts/gen_r92.py`、`scripts/dv_r92.py`、`dv_r81`（口径：控制台已搬到测试页）、
  本文档 + `HANDOVER.md` + `AGENTS.md` + `OPEN-ITEMS.md` + `TEST-camera.md` + `README.md`。
- 不涉及：**Java 不改**；BLE 协议代码（订阅/解码/帧）**一行都不删**（搬到测试页继续可用）；
  相机 Wi-Fi 连接链、扫码、写配方不动；**新增 id / data-tv：无**；**删除 id / data-tv：无**。

用法：python scripts/gen_r92.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r92：连接页瘦身'
BS = chr(92)          # 反斜杠：下面的锚点里有 JS 的 \n

REP = [
    # ① 按钮本身
    ('data-tv="cv-wake">② 让相机开 Wi-Fi（官方两条命令）</button>',
     'data-tv="cv-wake">② 唤醒相机（電源ON；<b>不会</b>开相机 Wi-Fi）</button>'),
    # 控制台说明（三行分开改，避免多行锚点）
    ('<b>「②」发的是官方"点导入图片"时那两条命令</b>（`電源ON` + `リモコンモード 0x1D01`）——',
     '<b>相机 Wi-Fi 请在相机上开</b>（MENU → Wi-Fi/蓝牙 → 连接到智能手机）。'),
    ('      这才是让相机自动进 Wi-Fi 传输态的做法；若相机拒绝，多半是**还没有蓝牙口令**（官方在连蓝牙时就用 `str.blePass`）：',
     '      「②」只是把官方那两条命令（`電源ON` + `リモコンモード 0x1D01`）发出去**供诊断** ——'),
    ('      扫相机屏幕上的二维码会自动填入口令，或手填（相机 MENU → Wi-Fi/蓝牙 → 连接到智能手机 → 蓝牙配对 会显示）。',
     '      真机实测（2026-09-29）：相机收到并回执，但**不执行**「リモコンモード」→ **它开不了相机 Wi-Fi**'
     '（需求方已决定不做这个功能）。这个控制台现在放在<b>测试页</b>，平时不用管它。'),
    # 连接页那句"想让 App 代劳就点②"
    ('想让 App 代劳就点下面「② 让相机开 Wi-Fi（传输）」。',
     '<b>这一步只能你在相机上做</b>（App 不会替你开相机 Wi-Fi）。'),
    # 状态框那句
    ("        + ' → 点②让相机开，或在相机上进入传输状态</div>');",
     "        + ' → 在相机上进入传输状态（MENU → Wi-Fi/蓝牙 → 连接到智能手机）</div>');"),
    # ③ 里那句提示（第二行）+ 上面的注释
    ("           + '（MENU → Wi-Fi/蓝牙 → 连接到智能手机），或点下面「② 让相机开 Wi-Fi（传输）」让它开', 'warn');",
     "           + '（MENU → Wi-Fi/蓝牙 → 连接到智能手机），再点「连接相机」（忘了密码就点「扫码连接」）', 'warn');"),
    ('       （要开就点下面「用蓝牙唤醒相机」那个按钮；或者你自己在相机上进入传输状态。） */',
     '       （相机 Wi-Fi 只能你自己在相机上开：MENU → Wi-Fi/蓝牙 → 连接到智能手机。） */'),
    # 14567：进连接页那句日志
    ("—— 要相机开 Wi-Fi 请点「② 让相机开 Wi-Fi（传输）」', 'ok'); }",
     "—— 相机 Wi-Fi 请在相机上开（MENU → Wi-Fi/蓝牙 → 连接到智能手机）', 'ok'); }"),
    # 18019/18257：注释里的旧名字（代码注释，也一起改，别留误导）
    ('       · **唯一**会发「電源ON」帧（= 让相机开 Wi-Fi）的地方 = 「② 让相机开 Wi-Fi（传输）」这个按钮',
     '       · **唯一**会发「電源ON」/「リモコンモード」帧的地方 = 控制台的「② 唤醒相机」按钮（**开不了相机 Wi-Fi**，诊断用）'),
    ('  /* ② 让相机开 Wi-Fi（传输）—— **唯一**会发「電源ON」帧的按钮 */',
     '  /* ② 唤醒相机（電源ON + リモコンモード）—— **唯一**会发这两帧的按钮（诊断用；开不了相机 Wi-Fi） */'),
    # 控制台 ② 自己的日志
    ("camCvSay('② 蓝牙已连 → 发「電源ON」帧让相机开 Wi-Fi（相机会进传输态、屏幕会亮）…');",
     "camCvSay('② 唤醒相机：发官方那两条命令（電源ON + リモコンモード）—— 供诊断；**不会**开相机 Wi-Fi…');"),
    ("camCvSay('② 蓝牙还没连 → 先连蓝牙（扫 → 连），连上后**自动发一次**（官方两条命令：電源ON + リモコンモード）…');",
     "camCvSay('② 蓝牙还没连 → 先连蓝牙（扫 → 连），连上后自动发一次（诊断用，**不会**开相机 Wi-Fi）…');"),
]


def slice_div(html, start_anchor, must_have):
    """从 start_anchor 起，按 <div>/</div> 配平切出整块（含首尾）。"""
    i = html.index(start_anchor)
    depth, j, seen = 0, i, False
    while j < len(html):
        k1 = html.find('<div', j)
        k2 = html.find('</div>', j)
        if k2 < 0:
            raise AssertionError('配平失败：找不到 </div>')
        if 0 <= k1 < k2:
            depth += 1
            seen = True
            j = k1 + 4
        else:
            depth -= 1
            j = k2 + 6
            if seen and depth == 0:
                break
    block = html[i:j]
    if must_have not in block:
        raise AssertionError('切出来的块里没有 `%s`' % must_have)
    if len(block) < 280:
        raise AssertionError('切出来的块太小（%d 字节）' % len(block))
    return block, html[:i] + html[j:]


def cut_between(html, start_anchor, end_anchor, must_have):
    """按显式起止锚点切一块，并用 <div>/</div> 数量配平做校验。"""
    i = html.index(start_anchor)
    j = html.index(end_anchor, i) + len(end_anchor)
    blk = html[i:j]
    if must_have not in blk:
        raise AssertionError('切出来的块里没有 `%s`' % must_have)
    if blk.count('<div') != blk.count('</div>'):
        raise AssertionError('div 不配平（%d 开 / %d 闭）' % (blk.count('<div'), blk.count('</div>')))
    return blk, html[:i] + html[j:]


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r92] 已经是目标状态 —— 不重复改。')
        return 0
    try:
        CON_END = ('三个按钮各做一件事、互不代劳：① 只连蓝牙 ② 只发唤醒帧 ③ 只连手机↔相机 Wi-Fi。'
                   '用完请点「④ 断开全部」。</div>')
        con, tmp = cut_between(html, '<!-- r81：手动控制台（需求方 2026-09-28', CON_END, 'data-tv="cv-pass"')
        card, rest = slice_div(tmp, '<div class="mpcard" id="bleCard"', 'bleSvcBox')
        if 'camGateConn' in card or '<h1>导入相机</h1>' in card:
            raise AssertionError('蓝牙工具卡切多了（把连接页/导入页也切进去了）')
    except (AssertionError, ValueError) as e:
        print('[r92] ✗ 切块失败：%s —— **不写盘**' % e)
        return 1
    pane = '<div id="paneT" class="pane hide">'
    if rest.count(pane) != 1:
        print('[r92] ✗ 找不到唯一的 paneT —— **不写盘**')
        return 1
    pi = rest.index(pane)
    h1 = rest.index('</h1>', pi) + len('</h1>')
    host = ('\n  <!-- r92：连接页瘦身 —— 下面两块（蓝牙手动控制台 + 蓝牙工具卡）原来在「连接相机」页上，\n'
            '       现在搬到测试页（诊断用）。data-tv / id 一个都没动，探针照旧按选择器找。 -->\n'
            '  <details class="fold fnote" style="margin:14px 0">\n'
            '    <summary>蓝牙手动控制台（诊断用：①连接蓝牙 / ②唤醒帧 / ③连相机 Wi-Fi / ④断开 · 口令）</summary>\n'
            '    <div class="foldbody">\n' + con + '\n    </div>\n  </details>\n' + card + '\n')
    rest = rest[:h1] + host + rest[h1:]
    for a, b in REP:
        if rest.count(a) != 1:
            print('[r92] ✗ 文案没匹配上（%d 处）：%s —— **不写盘**' % (rest.count(a), a[:60]))
            return 1
        rest = rest.replace(a, b, 1)
    pd, pt = rest.index('<div id="paneD"'), rest.index('<div id="paneT"')
    checks = [
        ('class="cvbox"' not in rest[pd:pt], '连接页里还有控制台'),
        ('id="bleCard"' not in rest[pd:pt], '连接页里还有蓝牙工具卡'),
        ('class="cvbox"' in rest[pt:], '测试页里没有控制台'),
        ('id="bleCard"' in rest[pt:], '测试页里没有蓝牙工具卡'),
        ('② 让相机开 Wi-Fi（传输）' not in rest, '还有旧按钮文案'),
        ('data-tv="cv-wake">② 唤醒相机（電源ON；<b>不会</b>开相机 Wi-Fi）</button>' in rest, '② 新文案没写上'),
        ('想让 App 代劳就点下面' not in rest, '连接页那句②承诺还在'),
    ]
    for once in ('data-tv="cv-pass"', 'data-tv="cv-wake"', 'data-tv="cv-ble"', 'data-tv="cv-wifi"',
                 'data-tv="cv-off"', 'data-tv="cv-seen"', 'data-tv="cv-notseen"', 'class="cvbox"', 'id="bleCard"'):
        checks.append((rest.count(once) == 1, '%s 出现 %d 次（应为 1）' % (once, rest.count(once))))
    bad = [m for ok, m in checks if not ok]
    if bad:
        print('[r92] ✗ 结构自检不过：%s —— **不写盘**' % '；'.join(bad))
        return 1
    if '--check' in sys.argv:
        print('[r92] --check 通过（未写盘）：控制台 %d 字节、蓝牙工具卡 %d 字节会搬到测试页' % (len(con), len(card)))
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(rest)
    print('[r92] ✓ 连接页瘦身：控制台 %d 字节 + 蓝牙工具卡 %d 字节 → 测试页；② 文案讲实话' % (len(con), len(card)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
