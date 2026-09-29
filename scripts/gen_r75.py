# -*- coding: utf-8 -*-
"""第 75 轮：把「发我日志」做成手机上真的能用的三步（见 SPEC-round75.md）。

需求方 2026-09-28：「不用 测试页（连接诊断）吗」

澄清与加固：
  · **要用**测试页 —— 「复制全部日志 / 下载日志文件」这两个按钮只在那儿（第 68 轮按"客户页别堆排查项"搬过去的）。
    连接相机页只剩一个默认收起的「运行日志（排查用 · 一般不用看）」，里面写着"要整段日志 → ☰ → 🔧 测试页 → 复制全部日志"。
  · 但真机上"复制"和"下载"都可能不灵：
      - 「复制全部日志」走 `document.execCommand('copy')`（WebView 的 file:// 页面里**不保证成功**）；
      - 「下载日志文件」走 `<a download>` + blob：**安卓 WebView 常常不接管**，点了像没反应。
    而项目里**早就有了更稳的一条路**：`om3Share()` → 原生 `shareText()` → **系统分享面板**（微信/邮件/QQ 都能发）。
  · 所以本轮：测试页日志卡加一个**「分享日志（发微信 / 邮件）」**按钮（排在最前，作为首选），
    并把"下载可能没反应"这件事如实写出来；连接相机页折叠里那句提示也改成三种方式。

⚠ 本轮**不新增 id**：新按钮用 `data-tv="sharelog"` 选择器（省得动 5 个老探针里"不新增 id"的断言，也够好选）。

规矩：幂等（标记 `r75：日志分享`）+ 每步必须真的改到东西 + 老 id 一个不少 + 不新增 id。

用法：python scripts/gen_r75.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r75：日志分享'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


# ---------------------------------------------------------------- ① 测试页：加"分享日志"按钮（首选）
@step('① 测试页日志卡：加「分享日志（发微信 / 邮件）」+ 文案改成"首选分享"')
def s_share_btn(html):
    old = '''    <div class="camlogbtns">
      <button type="button" id="camCopyLog">复制全部日志</button>
      <button type="button" id="camDlLog">下载日志文件</button>
      <button type="button" id="camClearLog" class="camghost">清空日志</button>
      <span class="camloghint">跑完点「复制全部日志」，粘给我就行</span>
    </div>'''
    assert html.count(old) == 1, '测试页日志按钮那一排没找到'
    new = '''    <div class="camlogbtns">
      <!-- r75：**首选「分享日志」** —— 走原生 shareText 打开系统分享面板（微信/邮件/QQ…），
           手机上比"复制"（WebView 的 execCommand('copy') 不保证成功）和"下载"（<a download> 常被 WebView 忽略）
           都稳。没有原生分享时 om3Share() 会自己退回剪贴板。 -->
      <button type="button" data-tv="sharelog">分享日志（发微信 / 邮件给我）</button>
      <button type="button" id="camCopyLog">复制全部日志</button>
      <button type="button" id="camDlLog">下载日志文件</button>
      <button type="button" id="camClearLog" class="camghost">清空日志</button>
      <span class="camloghint">首选「分享日志」（系统分享面板发给微信/邮件）；
        分享不了就点「复制全部日志」粘给我；「下载日志文件」存到手机「下载」文件夹，
        再拷到电脑丢进项目的 logs/ 目录也行（<b>若下载点了没反应，请用前两种</b>）。</span>
    </div>'''
    return html.replace(old, new, 1)


@step('① 给新按钮接上处理器（复用现成的 om3Share / __om3logText）')
def s_share_js(html):
    old = "  $('camCopyLog').addEventListener('click', function(){\n"
    assert html.count(old) == 1, "camCopyLog 的处理器没找到"
    new = ('''  /* r75：分享日志（首选）—— 用现成的 om3Share（原生 shareText → 系统分享面板）。
     ⚠ 这里**不新增 id**：按钮用 [data-tv="sharelog"] 选（老探针里"不新增 id"的断言不用动）。 */
  (function(){
    var b = document.querySelector('[data-tv="sharelog"]');
    if(!b) return;
    b.addEventListener('click', function(){
      var t = '';
      try{ t = (typeof window.__om3logText === 'function') ? window.__om3logText() : logText(); }
      catch(e){ t = ''; }
      if(!t){ try{ line(log3, '取日志失败（页面里没有日志）', 'warn'); }catch(e2){} return; }
      var nm = 'OM3-导入相机-日志-' + new Date().toISOString().slice(0,16).replace(/[:T]/g,'-') + '.txt';
      var ok = false;
      try{ ok = (typeof window.__om3share === 'function') ? window.__om3share(nm, t, 'text/plain') : false; }
      catch(e3){ ok = false; }
      try{ line(log3, ok ? ('已打开系统分享：' + nm + '（发给微信/邮件给我即可）')
                         : ('没有系统分享，已把日志放进剪贴板（' + t.length + ' 字符）—— 直接粘给我'), ok ? 'ok' : 'warn'); }catch(e4){}
    });
  })();

''') + old
    return html.replace(old, new, 1)


# ---------------------------------------------------------------- ② 「下载」可能没反应：如实说明
@step('② 「下载日志文件」点完多写一句"没反应就用分享/复制"')
def s_dl_hint(html):
    old = "    line(log3, '日志文件已生成（在「下载」文件夹里）。', 'ok');"
    assert html.count(old) == 1, '下载日志的提示那句没找到'
    new = ("    line(log3, '日志文件已生成（在「下载」文件夹里）。"
           "**若「下载」里没有这个文件（安卓 WebView 有时不接管下载）：请改用上面的「分享日志」或「复制全部日志」。**', 'ok');")
    return html.replace(old, new, 1)


# ---------------------------------------------------------------- ③ 连接相机页那句提示也改成三种
@step('③ 连接相机页折叠里的提示：改成"分享（首选）/复制/下载"三种')
def s_pane_hint(html):
    old = ("          要整段日志：☰（右上）→ <b>🔧 测试页（连接诊断）</b> → 点「复制全部日志」。")
    assert html.count(old) == 1, 'paneD 折叠里的提示没找到'
    new = ("          要整段日志：☰（右上）→ <b>🔧 测试页（连接诊断）</b> → "
           "点<b>「分享日志」</b>（首选，系统分享面板发微信/邮件）或「复制全部日志」。")
    return html.replace(old, new, 1)


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
    html = html.replace("  (function(){\n    var b = document.querySelector('[data-tv=\"sharelog\"]');",
                        "  (function(){   /* %s */\n    var b = document.querySelector('[data-tv=\"sharelog\"]');" % MARK, 1)
    assert MARK in html, '标记没插进去'
    return html, changed


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r75] 已经是目标状态（页面里有 "%s"）—— 不重复改。' % MARK)
        return 0
    try:
        new, changed = run(html)
    except AssertionError as e:
        print('[r75] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r75] --check：%d 步都能跑通（未写盘）：' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(new)
    print('[r75] ✓ 已改 %d 步：日志"分享"按钮（首选）+ 下载没反应时如实说明 + 连接页提示改三种' % len(changed))
    before = io.open(os.path.join(ROOT, 'app', 'base.before_r75.html'), encoding='utf-8').read()
    print('[r75] 页面净增 %d 字节' % (len(new.encode('utf-8')) - len(before.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
