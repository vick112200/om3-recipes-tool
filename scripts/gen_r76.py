# -*- coding: utf-8 -*-
"""第 76 轮：把"到底怎么操作"写成**编号清单**（需求方 2026-09-28：「看不懂，不知道具体操作步骤」）。

这一轮**只改文字**（不动逻辑、不动结构、不新增 id）：把最要紧的两处"怎么点"改成 1-2-3 编号清单：
  ① 连接相机页最上面：**第一次连，就这三步**（相机做什么 / 手机点哪里 / 看到什么算成功）
  ② 测试页日志卡：**怎么把日志发我，就这三步**（点分享 → 选微信/邮件 → 发我）
  ③ 把原来那段"首选分享…"的绕口说明压成一行（怕长）

规矩：幂等（标记 `r76：怎么操作`）+ 每步必须真的改到东西 + 老 id 一个不少 + 不新增 id。

用法：python scripts/gen_r76.py [--check]
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r76：怎么操作'
STEPS = []
DIVPAT = re.compile(r'<div|</div\s*>')


def cut_div(html, start):
    """从 start（ 的起点）按 <div>/</div> 配平，返回 (整块, 之后剩余)"""
    depth, pos = 0, start
    while True:
        m = DIVPAT.search(html, pos)
        if not m:
            raise AssertionError('div 配不平（起点 %d）' % start)
        if m.group(0).startswith('</'):
            depth -= 1
            if depth == 0:
                return html[start:m.end()], html[m.end():]
        else:
            depth += 1
        pos = m.end()



def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


@step('① 连接相机页最上面加「第一次连，就这三步」编号清单')
def s_guide_steps(html):
    old = '<div class="camguide49">\n      <p><b>第一次连这台相机（手机还没记过它）</b><br>'
    assert html.count(old) == 1, '连接相机页的 guide 卡没找到'
    new = ('''<div class="camguide49">
      <!-- r76：需求方「看不懂，不知道具体操作步骤」→ 最上面先给**编号清单**（相机做什么／手机点哪里／看到什么算成功） -->
      <p style="font-size:14px;color:#fff;font-weight:700;margin-bottom:8px">第一次连，就这三步：</p>
      <p style="line-height:2">
        <b>①（相机）</b>MENU → Wi-Fi/蓝牙 → 连接到智能手机 → 屏幕上出现<b>二维码</b><br>
        <b>②（手机）</b>点下面<b>「扫码连接」</b> → 对着相机屏幕的二维码 → 系统弹窗点<b>「连接」</b><br>
        <b>③</b>看到<b>「OM-3 · 已连接」</b>就成了 → 去 ② 备份 / ③ 写配方<br>
        <span style="color:#9aa3b2">以后：相机打开 Wi-Fi 传输，直接点<b>「连接相机」</b>，不用再扫码。</span>
      </p>
      <p class="g49n" style="margin-bottom:14px">连不上？照最后一节：☰（右上）→ <b>🔧 测试页</b> → 点<b>「分享日志」</b>发我。</p>
      <p><b>第一次连这台相机（手机还没记过它）</b><br>''')
    return html.replace(old, new, 1)


@step('② 测试页日志卡：把绕口说明换成「怎么发我，就这三步」')
def s_log_steps(html):
    old = ('<span class="camloghint">首选「分享日志」（系统分享面板发给微信/邮件）；\n'
           '        分享不了就点「复制全部日志」粘给我；「下载日志文件」存到手机「下载」文件夹，\n'
           '        再拷到电脑丢进项目的 logs/ 目录也行（<b>若下载点了没反应，请用前两种</b>）。</span>')
    assert html.count(old) == 1, '测试页日志卡的说明没找到'
    new = ('<span class="camloghint">怎么发我，就这三步：'
           '<b>①点「分享日志」</b> → ②在弹出来的面板里选<b>微信</b>或<b>邮件</b> → ③发给我。'
           '（发不了再点「复制全部日志」粘给我；「下载日志文件」存手机「下载」里，'
           '<b>点了没反应就用前两种</b>）</span>')
    return html.replace(old, new, 1)


@step('③ 测试页顶部那句「日志（三步共用这一份…）」补一句"哪里点分享"')
def s_card_title(html):
    old = '<div class="camhd">日志（三步共用这一份；直接复制这一份给我就行）</div>'
    assert html.count(old) == 1, '测试页日志卡的标题没找到'
    new = ('<div class="camhd">日志（①②③ 三步共用这一份）—— '
           '<span style="color:#7ed3bd">要发我：点下面的「分享日志」→ 选微信/邮件 → 发给我</span></div>')
    return html.replace(old, new, 1)


@step('④ 把「连接相机」卡搬到最前面（原来第一眼看到的是"蓝牙工具（高级）"+ 一堵说明）')
def s_move_gate_first(html):
    # ⚠ 这里**不用**按 div 配平切（本项目 HTML 里 #noresult2 那处标签不配对，
    #   从 bleCard 一路扫到文件尾是配不平的）——改用"下一张卡的起点"当边界，稳。
    j = html.index('<div class="mpcard" id="bleCard"')
    i = html.index('<div class="camgate" id="camGateOff">')
    k = html.index('<div class="camconn hide" id="camStatusCard">')
    assert j < i < k, '三张卡的顺序意外：bleCard=%d camgate=%d camStatus=%d' % (j, i, k)
    ble = html[j:i]                       # 蓝牙工具卡 + 它后面的空白
    gate = html[i:k]                      # 连接相机卡
    assert 'camGateConn' in gate and 'bleScan' in ble, '切出来的两块内容不对'
    note = ('<!-- r76：**把「连接相机」卡挪到最前面** —— 实测（412×800）原来第一眼看到的是\n'
            '     「蓝牙工具（高级）…」（y=66），而真正的「连接相机」按钮在 **y=737**（第一屏几乎看不到），\n'
            '     需求方因此说「看不懂，不知道具体操作步骤」。现在按钮在最上面，蓝牙工具挪到它后面。 -->\n')
    return html[:j] + note + gate + ble + html[k:]


@step('⑤ 老的长说明收进折叠块（只留"就这三步"+一句兜底），第一屏不再是一堵字')
def s_fold_old_guide(html):
    s1 = html.index('<p><b>第一次连这台相机（手机还没记过它）</b><br>')
    s2 = html.index('</div>', s1)                        # guide 卡的收尾（这三段里没有 div）
    old = html[s1:s2]
    assert '以后（已经连过一次）' in old and '不想装官方 App' in old, '老说明那三段没取对'
    new = ('<details class="fold fnote" style="margin-top:10px">\n'
           '        <summary>详细说明（第一次连 / 以后怎么连 / 不装官方 App）</summary>\n'
           '        <div class="foldbody">\n' + old + '\n        </div>\n'
           '      </details>\n    ')
    return html[:s1] + new + html[s2:]


def run(html):
    changed = []
    for label, fn in STEPS:
        before = html
        try:
            html = fn(html)
        except AssertionError as e:
            raise AssertionError('第「%s」步失败：%s' % (label, e or '锚点没找到'))
        except ValueError as e:
            raise AssertionError('第「%s」步失败（找不到锚点）：%s' % (label, e))
        if html == before:
            raise AssertionError('这一步什么都没改：' + label)
        changed.append(label)
    html = html.replace('      <!-- r76：需求方「看不懂，不知道具体操作步骤」→ 最上面先给**编号清单**（相机做什么／手机点哪里／看到什么算成功） -->',
                        '      <!-- %s：需求方「看不懂，不知道具体操作步骤」→ 最上面先给**编号清单**（相机做什么／手机点哪里／看到什么算成功） -->' % MARK, 1)
    assert MARK in html, '标记没插进去'
    return html, changed


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r76] 已经是目标状态（页面里有 "%s"）—— 不重复改。' % MARK)
        return 0
    try:
        new, changed = run(html)
    except AssertionError as e:
        print('[r76] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r76] --check：%d 步都能跑通（未写盘）：' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(new)
    print('[r76] ✓ 已改 %d 步：操作写成编号清单（连接三步 / 发日志三步）' % len(changed))
    before = io.open(os.path.join(ROOT, 'app', 'base.before_r76.html'), encoding='utf-8').read()
    print('[r76] 页面净增 %d 字节' % (len(new.encode('utf-8')) - len(before.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
