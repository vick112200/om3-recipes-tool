# -*- coding: utf-8 -*-
"""第 87 轮：**把 ② 的承诺改成实话**（需求方：「最后试一次，再不行就不要这个功能了」）

## 结论（有反汇编证据，不是猜）

真机 v3.37（2026-09-29 05:51）：订阅三个特征值成功后，**相机对「電源ON」回了应答**
`04 02 04 0F 01 01 01 12 00` → 通道 0x0F、子命令 0x01、**结果码 1**、校验 0x12 ✓
（= 相机"已经在开机状态"，官方 `e$e.run` 里 `ret >= 0` 就算成功）。
可是相机**没有**因此打开 Wi-Fi，相机屏幕也没变（用户两次按「相机没反应」）。

把官方 App 的命令入口全列一遍（`official_app/oi_index.json` 反查 `LM2/b.*` 的调用点）：

| 命令 | 谁发 | 语义 | 出处 |
|---|---|---|---|
| `0x0F01` | `oishare/e$e.run` → `M2/b.y(20000)` | **電源ON（把睡着的相机唤醒）** | `M2/b.x` = `u(15,1,{2})` |
| `0x0C02` | `oishare/e$d.run` → `M2/b.j(口令)` | パスコード認証 | `M2/b.i(String)` |
| `0x6A01` | `M2/b.F(int,int)` | **GPS 付与**（日志 `GPS付与コマンド発行：`） | `M2/b.F` 体 |
| `0x1D01`/`0x040F`/`0x0410`/`0x6B01` | 只有分派表，没有对外调用点 | —— | `M2/b$b.a()` |

**没有"打开相机 Wi-Fi"的 BLE 命令。** 而且 `oishare/e.W()` 里还有一条前提：
相机报了「蓝牙连接模式」(bit3) 或「定位」(bit5) 时，官方**根本不发** `0x0F01`。
也就是说：官方 App 的"传输"也是**先把相机打到「连接到智能手机」（Wi-Fi 传输态）**，
再从相机屏幕上的二维码取 SSID/密码去连；BLE 只负责"唤醒睡着的相机 + 口令认证"。

→ 所以 v3.36/v3.37 的失败不是流程错，而是**这条命令本来就不会开 Wi-Fi**。
（需求方那句"相机开启 wifi 和手机连相机 wifi 不应该是随便的行为"其实说对了：开 Wi-Fi 是**相机侧**的动作。）

## 本轮改动（页面 only，只改文案 + 一条结论日志）

1. **② 改名**：`② 让相机开 Wi-Fi（传输）` → **`② 唤醒相机（電源ON）`**（它做的就是这件事）。
2. **说明改成实话**：② 旁边写明"**它不会打开相机 Wi-Fi** —— 相机 Wi-Fi 只能在相机上开
   （MENU → Wi-Fi/蓝牙 → 连接到智能手机），或用相机屏幕上的二维码"。
3. **收尾加一条结论**：② 收到相机应答后，日志里直接写
   `【结论】相机 Wi-Fi 是相机侧的事：请在相机上进入「连接到智能手机」（或用二维码）`，
   并在结果码 ≠0 时把官方语义一起写出来。
4. 老探针里断言旧按钮文案的那几条，按"同一件事、措辞更准"做**口径修正**。

## 显式声明

- 涉及：`app/base.html`（② 文案 + 说明 + 结论日志）、`scripts/gen_r87.py`、`scripts/dv_r87.py`、
  `dv_r81`（按钮文案口径）、本文档 + `HANDOVER.md` + `AGENTS.md` + `OPEN-ITEMS.md` + `TEST-camera.md`。
- 不涉及：**Java 不改**；订阅三连/判据/结果码逻辑不变；帧字节不变；**新增 id / data-tv：无**。

用法：python scripts/gen_r87.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r87：'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


@step('P1 ② 改名「唤醒相机（電源ON）」')
def p1_label(html):
    old = 'data-tv="cv-wake">② 让相机开 Wi-Fi（传输）</button>'
    new = 'data-tv="cv-wake">② 唤醒相机（電源ON）</button>'
    assert html.count(old) == 1, '② 按钮文案没找到'
    return html.replace(old, new, 1)


@step('P2 回答键那句 + cvnote 改成实话（② 不会开相机 Wi-Fi）')
def p2_note(html):
    old = '<span style="font-size:11.5px;color:#9aa3b2;display:block;margin:0 0 4px">点了「② 让相机开 Wi-Fi」之后，看一眼相机屏幕：</span>'
    new = '<span style="font-size:11.5px;color:#9aa3b2;display:block;margin:0 0 4px">点了「② 唤醒相机」之后，看一眼相机屏幕：</span>'
    assert html.count(old) == 1, '回答键那句没找到'
    html = html.replace(old, new, 1)
    old2 = """    <div class="cvnote">每一步都要你点：<b>App 不会自己连蓝牙，也不会自己开相机 Wi-Fi</b>。
      「②」会让相机进入传输态（屏幕会亮、比较费电）—— 用完请点「④ 断开全部」。
      三个按钮各做一件事、互不代劳：① 只连蓝牙（不开 Wi-Fi）② 只让相机开 Wi-Fi ③ 只连手机↔相机 Wi-Fi。</div>"""
    new2 = """    <div class="cvnote">每一步都要你点：<b>App 不会自己连蓝牙，也不会自己开相机 Wi-Fi</b>。
      <b>「②」只是把「電源ON」发给相机（唤醒睡着的相机）—— 它打不开相机 Wi-Fi</b>：
      相机 Wi-Fi 只能在<b>相机上</b>开（MENU → Wi-Fi/蓝牙 → 连接到智能手机），或用相机屏幕上的二维码扫。
      三个按钮各做一件事、互不代劳：① 只连蓝牙 ② 只发唤醒帧 ③ 只连手机↔相机 Wi-Fi。用完请点「④ 断开全部」。</div>"""
    assert html.count(old2) == 1, 'cvnote 没找到'
    return html.replace(old2, new2, 1)


@step('P3 收到相机应答后写一条结论（相机 Wi-Fi 是相机侧的事）')
def p3_concl(html):
    old = """          if(_bleLastAck){
            var _c2 = -1;
            try{ _c2 = bleResultCode(_bleLastAck.hex, 0x0F, 0x01); }catch(e13){ om3err(e13, "silent"); }
            bleAutoSay('相机回了应答' + (_c2 >= 0 ? ('（结果码 ' + _c2 + '：' + bleResultText(_c2) + '）') : '')
              + ' —— 蓝牙这条命令是通的；接下来看相机有没有进传输态（相机屏幕/相机状态包）', 'ok');
          } else {"""
    new = """          if(_bleLastAck){
            var _c2 = -1;
            try{ _c2 = bleResultCode(_bleLastAck.hex, 0x0F, 0x01); }catch(e13){ om3err(e13, "silent"); }
            bleAutoSay('相机回了应答' + (_c2 >= 0 ? ('（结果码 ' + _c2 + '：' + bleResultText(_c2) + '）') : '')
              + ' —— 蓝牙这条命令是通的；接下来看相机有没有进传输态（相机屏幕/相机状态包）', 'ok');
            /* STEPS_MARK：把结论摆明（反汇编证据：官方也只有 電源ON/口令认证/GPS 三条命令，
               没有"开 Wi-Fi"的命令；官方 App 自己也要求相机先进「连接到智能手机」）。 */
            bleAutoSay('【结论】相机 Wi-Fi 是**相机侧**的事：请在相机上 MENU → Wi-Fi/蓝牙 → 连接到智能手机'
              + '（屏幕会出二维码），再点③连它 —— 或用「扫码连接」扫那个二维码。'
              + '蓝牙这条链的作用是"唤醒相机 + 口令认证"，它不会替相机打开 Wi-Fi。', 'warn');
          } else {"""
    assert html.count(old) == 1, '收尾那段没找到'
    return html.replace(old, new, 1)


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r87] 已经是目标状态 —— 不重复改。')
        return 0
    changed = []
    cur = html
    try:
        for label, fn in STEPS:
            before = cur
            cur = fn(cur)
            if cur == before:
                raise AssertionError('这一步什么都没改：' + label)
            changed.append(label)
    except (AssertionError, ValueError) as e:
        print('[r87] ✗ %s —— **不写盘**' % e)
        return 1
    cur = cur.replace('STEPS_MARK', MARK)
    assert MARK in cur
    for once in ('② 唤醒相机（電源ON）', '【结论】相机 Wi-Fi 是**相机侧**的事'):
        if cur.count(once) != 1:
            print('[r87] ✗ 结构自检：`%s` 出现 %d 次' % (once, cur.count(once)))
            return 1
    if 'data-tv="cv-wake">② 让相机开 Wi-Fi（传输）' in cur:
        print('[r87] ✗ 按钮上还是旧文案 —— **不写盘**')
        return 1
    dh = len(cur.encode('utf-8')) - len(html.encode('utf-8'))
    if not (-2000 < dh < 6000):
        print('[r87] ✗ 页面体积不对（%+d 字节）—— **不写盘**' % dh)
        return 1
    if '--check' in sys.argv:
        print('[r87] --check：%d 步都能跑通（未写盘）' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(cur)
    print('[r87] ✓ 页面 %d 步：② 改成「唤醒相机（電源ON）」+ 说明/结论讲实话' % len(changed))
    print('[r87] 页面净增 %d 字节' % dh)
    return 0


if __name__ == '__main__':
    sys.exit(main())
