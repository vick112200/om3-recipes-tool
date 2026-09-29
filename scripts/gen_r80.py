# -*- coding: utf-8 -*-
"""第 80 轮（上）：**不再自动唤醒相机 Wi-Fi**（需求方 2026-09-28 明确要求）

需求方原话：
  「（相机）只有开机状态才会连蓝牙，在官方app中点传输图片等才会连接相机wifi，
    **你可不能自动唤醒相机wifi啊**，我们也要做成**显示蓝牙已连接、并且点击按钮才能控制相机开启wifi**。
    如果……就可以做成**只有在点击传输时再开启wifi传输配方**，
    因为相机开启wifi和手机连相机wifi并不应该是个随随便便的行为。」

现状（改前，真机日志 `logs/OM3-真机-2026-09-28-2232.txt` 可证）：
  · 进「连接相机」页就自动跑蓝牙链：`[自动·蓝牙] 进入「连接相机」页：开始（权限 → 蓝牙开关 → 只扫相机 → 自动连 → 唤醒）`
  · 点「连接相机」也会自动跑蓝牙链并发「電源ON」帧 → **相机会自己开 Wi-Fi**（用户不接受）

本轮只做**安全的那一半**（立刻生效）：
  ① 进页面**不再**自动跑蓝牙链（只读状态、不扫不连不发帧）
  ② 点「连接相机」**不再**自动跑蓝牙链 / 不自动开相机 Wi-Fi；改成明确提示
     「App 不会替你开相机 Wi-Fi」+ 指两条路（相机上进入传输状态 / 手动点「用蓝牙唤醒相机」）
  ③ 把上一轮写错的文案（"App 会先试蓝牙唤醒"）改成如实的说明
  剩下的（状态显示 + 明确按钮 + "点传输才开 Wi-Fi"）写进 `SPEC-round80-plan.md`，下一轮做。

用法：python scripts/gen_r80.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r80：不自动开相机 Wi-Fi'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


@step('① 进「连接相机」页：不再自动跑蓝牙链（只读状态）')
def s_no_auto_ble(html):
    old = """  window.__om3camPaneShown = function(){
    camAutoStart('进入「连接相机」页');
    try{ camLinkRender(); }catch(e){ om3err(e, "silent"); }
    try{ if(window.__om3camBleAuto) window.__om3camBleAuto('进入「连接相机」页'); }
    catch(e2){ om3err(e2, "ble-auto"); }
  };"""
    assert html.count(old) == 1, 'paneShown 钩子没找到'
    new = """  window.__om3camPaneShown = function(){
    camAutoStart('进入「连接相机」页');
    try{ camLinkRender(); }catch(e){ om3err(e, "silent"); }
    /* ⚠ STEPS_MARK（需求方 2026-09-28：「你可不能自动唤醒相机wifi啊」「相机开启 wifi 和手机连相机 wifi
       并不应该是个随随便便的行为」）：
       以前这里会自动跑蓝牙链（权限 → 蓝牙开关 → 只扫相机 → 自动连 → 发「電源ON」帧）——
       那等于**一进页面就让相机开 Wi-Fi**（真机日志里有：`[自动·蓝牙] 进入「连接相机」页：开始…`）。
       现在**只读状态**：不扫、不连、不发帧；要不要让相机开 Wi-Fi，由用户点「用蓝牙唤醒相机」。 */
    try{ log('[连接] 进入连接页：**不做任何自动蓝牙动作**（不扫/不连/不发唤醒帧）—— 要相机开 Wi-Fi 请点「用蓝牙唤醒相机」', 'ok'); }
    catch(e3){ om3err(e3, "silent"); }
  };"""
    return html.replace(old, new, 1)


@step('② 点「连接相机」：不再自动跑蓝牙链；改为明确提示 + 指路')
def s_no_chain_ble(html):
    old = """    if(!_bleAutoDone && !_bleAutoStop && !camHotspotVisible()){
      try{ camBleAuto('点「连接相机」'); }catch(e){ om3err(e, "ble-chain"); }
      if(!blePossible){
        step('蓝牙这条路现在跑不起来（没有蓝牙接口 / 已停用）→ 不等它了，直接进 Wi-Fi', 'warn');
        wifi(); return;
      }"""
    assert html.count(old) == 1, 'camWifiChain 里那段自动蓝牙没找到'
    new = """    /* ⚠ STEPS_MARK：**不再自动替用户开相机 Wi-Fi**。
       以前这里会 `camBleAuto(...)`（扫 → 连 → 发「電源ON」帧）→ 相机自己开 Wi-Fi。
       需求方 2026-09-28：「你可不能自动唤醒相机wifi啊」→ 改成：只提示，不动作。
       （要开就点下面「用蓝牙唤醒相机」那个按钮；或者你自己在相机上进入传输状态。） */
    if(!_bleAutoDone && !_bleAutoStop && !camHotspotVisible()){
      step('没看到相机 Wi-Fi。**App 不会替你开相机 Wi-Fi** —— 请在相机上进入传输状态'
           + '（MENU → Wi-Fi/蓝牙 → 连接到智能手机），或点下面「用蓝牙唤醒相机」让它开', 'warn');
      if(!blePossible){
        step('（这台设备没有蓝牙接口）→ 直接试 Wi-Fi', 'warn');
        wifi(); return;
      }"""
    return html.replace(old, new, 1)


@step('③ 文案：把"App 会先试蓝牙唤醒"改成如实说明（不会再自动开）')
def s_text(html):
    old = '点「连接相机」，App 会先试「蓝牙唤醒相机」把它叫醒。</span>'
    assert html.count(old) == 1, 'r79 那句文案没找到'
    new = ('<b>App 不会替你开相机 Wi-Fi</b>（开启相机 Wi-Fi 是有副作用的动作，得你点头）：'
           '请在相机上进入传输状态（MENU → Wi-Fi/蓝牙 → 连接到智能手机）；'
           '想让 App 代劳就点下面「用蓝牙唤醒相机」。</span>')
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
    html = html.replace('STEPS_MARK', MARK)
    assert MARK in html, '标记没插进去'
    assert html.count(MARK) >= 2, '标记应当出现在两处（页面钩子 + 连接链）'
    return html, changed


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r80] 已经是目标状态 —— 不重复改。')
        return 0
    try:
        new, changed = run(html)
    except AssertionError as e:
        print('[r80] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r80] --check：%d 步都能跑通（未写盘）：' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(new)
    print('[r80] ✓ 已改 %d 步：进页面/点连接都不再自动开相机 Wi-Fi（改成提示 + 指路）' % len(changed))
    before = io.open(os.path.join(ROOT, 'app', 'base.before_r80.html'), encoding='utf-8').read()
    print('[r80] 页面净增 %d 字节' % (len(new.encode('utf-8')) - len(before.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
