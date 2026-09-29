# -*- coding: utf-8 -*-
"""第 79 轮：修「点了没啥反应」+ 把"怎么操作"写成按相机屏幕分支的三条路（见 SPEC-round79.md）

需求方 2026-09-28：
  「不是吧，我看点了没啥反应，我自己把相机wifi开的。你也没告诉我不要开相机wifi啊，
    你看你写的操作啥玩意，完全看不懂」

**真凶（已定位）**：`#camGateScan`（我第 74 轮放回来的「扫码连接」大按钮）的 click 处理器
**只有 `showStep(1)`** —— 这是第 49 轮藏扫码时的残骸（那时候按钮被 `.hid49` 藏了，空处理器没人发现）；
我第 74 轮"放回来"时只改了标记/样式/文案顺序，**漏了把功能接回去**，探针也只断言"可见/排后/样式次要"，
**没断言"点了会启动扫码"** → 于是用户点了完全没反应。

本轮：
  ① `#camGateScan` 接回功能：复用既有的 `window.__om3startScan()`（不复制实现）
  ② 三条路写成**按相机屏幕看到什么**分支的清单（并写明"相机 Wi-Fi 你自己开也行、App 也会自己开"）
  ③ 链接：`#camGateManual` 也给出可见反馈（打开手动填卡）
  ④ 新脚本 `scripts/audit_buttons.py`（静态筛"没人引用的按钮"）+ `scripts/audit_deadclicks.py`（行为体检）

用法：python scripts/gen_r79.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r79：入口真的能点'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


@step('① 把「扫码连接」接回功能（第 74 轮只放了按钮，没接功能）')
def s_scan_wired(html):
    old = '''  /* r49：这里原来会顺手点一下「扫二维码」把相机打开——扫码隐藏了，就别再偷偷启动它了 */
  if(gs) gs.addEventListener('click', function(){ showStep(1); });'''
    assert html.count(old) == 1, 'camGateScan 的处理器没找到'
    new = ('''  /* r49：这里原来会顺手点一下「扫二维码」把相机打开——扫码隐藏了，就别再偷偷启动它了。
     ⚠ ''' + MARK + '''：第 74 轮把扫码**放回来**了，但这里**忘了接功能**（只剩 showStep(1)）→
       用户 2026-09-28 点「扫码连接」**完全没反应**。
       现在接回既有的 __om3startScan()（不复制实现；它自己负责权限/组件/浮层/各种失败提示）。 */
  if(gs) gs.addEventListener('click', function(){''')
    new += '''
    showStep(1);
    if(typeof window.__om3startScan === 'function'){
      try{ window.__om3startScan(); }
      catch(e){ try{ camOut('扫码起不来：' + e.message + '（可以改用「手动填 SSID / 密码」）', 'err'); }catch(e2){} }
    } else {
      try{ camOut('这个版本的扫码没接上 —— 请点下面「手动填 SSID / 密码」，或更新 App。', 'err'); }catch(e3){}
    }
  });'''
    return html.replace(old, new, 1)


@step('② 「第一步」清单改成按相机屏幕分支的三条路（并写明 Wi-Fi 你自己开也行）')
def s_three_ways(html):
    old = '''      <p style="font-size:14px;color:#fff;font-weight:700;margin-bottom:8px">第一次连，就这三步：</p>
      <p style="line-height:2">
        <b>①（相机）</b>MENU → Wi-Fi/蓝牙 → 连接到智能手机 → 屏幕上出现<b>二维码</b><br>
        <b>②（手机）</b>点下面<b>「扫码连接」</b> → 对着相机屏幕的二维码 → 系统弹窗点<b>「连接」</b><br>
        <b>③</b>看到<b>「OM-3 · 已连接」</b>就成了 → 去 ② 备份 / ③ 写配方<br>
        <span style="color:#9aa3b2">以后：相机打开 Wi-Fi 传输，直接点<b>「连接相机」</b>，不用再扫码。</span>
      </p>'''
    assert html.count(old) == 1, '三步清单没找到'
    new = '''      <!-- r79：需求方「完全看不懂」→ 改成**按相机屏幕上看到什么**分支，并明确回答
           「要不要自己开相机 Wi-Fi」（三种情况都能连，不用先去看相机设置） -->
      <p style="font-size:14px;color:#fff;font-weight:700;margin-bottom:8px">先看相机屏幕上是什么，对号入座：</p>
      <p style="line-height:1.9">
        <b>情况 A：相机屏幕上有「二维码」</b><br>
        　→ 这台相机点下面<b>「扫码连接」</b>，对着二维码即可（系统弹窗点「连接」）。<br>
        <b>情况 B：相机屏幕上只有 SSID 和密码，没有二维码</b><br>
        　→ 点下面<b>「连不上？更多方式」</b> → <b>「手动填 SSID / 密码」</b>，照抄两格即可。<br>
        <b>情况 C：你已经自己在相机/手机设置里把相机 Wi-Fi 打开了（或连过一次）</b><br>
        　→ 直接点下面<b>「连接相机」</b>就行。<br>
        <span style="color:#7ed3bd">不用先去改相机的 Wi-Fi 开关 —— 相机没开也没关系：
        点「连接相机」，App 会先试「蓝牙唤醒相机」把它叫醒。</span>
      </p>'''
    return html.replace(old, new, 1)


@step('③ 「连接相机」按钮下面的说明也写清"两种都行"（自己开过 / 让 App 唤醒）')
def s_conn_hint(html):
    old = '  <div class="camhd">连接相机</div>'
    if html.count(old) != 1:
        old = '<h3>连接相机</h3>'
    assert html.count(old) == 1, '连接卡标题没找到'
    new = (old + '\n      <div style="font-size:12.5px;color:#9aa3b2;line-height:1.7;margin:-4px 0 8px">'
                 '已经开着相机 Wi-Fi（自己开的也算）或以前连过这台 → 直接点「连接相机」；'
                 '第一次连、手上又没二维码 → 用「手动填 SSID / 密码」。</div>')
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
    assert MARK in html, '标记没插进去'
    return html, changed


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r79] 已经是目标状态 —— 不重复改。')
        return 0
    try:
        new, changed = run(html)
    except AssertionError as e:
        print('[r79] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r79] --check：%d 步都能跑通（未写盘）：' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(new)
    print('[r79] ✓ 已改 %d 步：扫码入口接回功能 + 三条路按相机屏幕分支' % len(changed))
    before = io.open(os.path.join(ROOT, 'app', 'base.before_r79.html'), encoding='utf-8').read()
    print('[r79] 页面净增 %d 字节' % (len(new.encode('utf-8')) - len(before.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
