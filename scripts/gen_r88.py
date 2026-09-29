# -*- coding: utf-8 -*-
"""第 88 轮：**补上官方"导入图片"用的那条命令（0x1D01）**

需求方 2026-09-29 指出（我上一轮的结论错了）：
> 官方 app 的流程是：进入 app 自动连接蓝牙，**点击导入图片相机才会自动打开 wifi**，通过 wifi 给手机传输图片。

从反汇编里找到了这条命令（`official_app/dis.txt`）：

```
Lcom/omdigitalsolutions/oishare/trans/BlePowOnActivity$c;.run()V        ← "导入图片"这个界面
    iget-object v0, v4, ...$c;.s:LM2/b;
    const/4 v1, #int 2            ← 参数 = 2
    const/16 v2, #int 10000       ← 超时 10 秒
    invoke-virtual {v0, v1, v2}, LM2/b;.M:(II)I
    move-result v0
    if-eqz v0, ...                ← **必须回 0 才算成功**（否则走 L1() 失败分支）

LM2/b;.M(II)I                        ← 日志字符串 "リモコンモードコマンド発行："
    new-instance ..., LM2/b$b;.<init>:(LM2/b;III)V   ; cmd = 7425 = 0x1D01
LM2/b;.L(IILM2/b$c;)Z                ← 0x1D01 的发送实现
    new-array v0, 1, [B ; v0[0] = (byte)arg          ; 数据 1 字节 = 参数（2）
    invoke-direct {v2, 0x1D, 1, v0}, LM2/b;.u:(II[B)[B
    invoke-virtual {v2, 0x1D01, frame, timeout}, LN2/a;.s0:(I[BI)Z
```
→ 帧 = `01 <seq> 04 1D 01 01 02 21 00`（校验 = 0x1D+1+0x01+0x02 = **0x21**），
和官方"进入导入界面→BLE连上→发这条→再连相机热点（`q2()` 用 `.connectWiFi str.wifi.camera.ssid`）"完全一致。

**这就是"点了导入图片相机才开 Wi-Fi"背后的命令**（第 59 轮把它标成"遥控模式"，方向对，但没接到流程里）。
我们 ② 只发了 `0x0F01`（電源ON）→ 相机回 1 但不开 Wi-Fi，正是"少了这一条"。

## 本轮改动（页面 only）

1. ② 的发送序列改成**官方"导入图片"的顺序**：
   `[口令认证 0x0C02（有口令才发）] → 電源ON 0x0F01 → リモコンモード 0x1D01{0x02}`。
2. **按官方判据报结果**：`0x1D01` 的回帧必须**正好是 0** 才算成功（官方 `if(ret != 0) → 失败分支`）；
   非 0 就明说"相机拒绝/需要口令"，并把码写出来。
3. ② 按钮文案：`② 唤醒相机（電源ON）` → **`② 让相机开 Wi-Fi（官方两条命令）`**；
   说明里写清"官方做法 = 電源ON + リモコンモード（这才是点『导入图片』时官方发的）"。
4. 老探针里"一次②只发一帧"的断言改成"两帧、顺序对"（口径修正）。

## 显式声明

- 涉及：`app/base.html`（② 序列 + 判据 + 文案）、`scripts/gen_r88.py`、`scripts/dv_r88.py`、
  `dv_r83`/`dv_r84`/`dv_r85`/`dv_r86`（帧数口径）、本文档 + `HANDOVER.md` + `AGENTS.md` + `OPEN-ITEMS.md` + `TEST-camera.md`。
- 不涉及：**Java 不改**；订阅三连（r85）/结果码解码（r86）不变；0x0C02 / 0x0F01 的帧字节不变；
  新增帧只有 0x1D01；不加权限；**新增 id / data-tv：无**。

用法：python scripts/gen_r88.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r88：'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


@step('P1 ② 的序列加上官方的 0x1D01{0x02}（リモコンモード = 开 Wi-Fi）')
def p1_seq(html):
    old = """    seq.push({ ch: 0x0F, sub: 1, payload: [0x02], name: '電源ON' });"""
    new = """    seq.push({ ch: 0x0F, sub: 1, payload: [0x02], name: '電源ON' });
    /* STEPS_MARK：**官方"导入图片"发的是这一条**（BlePowOnActivity$c.run → M2/b.M(2,10000) → 0x1D01 数据 {0x02}，
       `M2/b.L` = u(0x1D,1,{arg}) → 帧 `01 <seq> 04 1D 01 01 02 21 00`）。
       我们以前只发 電源ON（相机回 1，但不开 Wi-Fi）—— 少了这一条。 */
    seq.push({ ch: 0x1D, sub: 1, payload: [0x02], name: 'リモコンモード（让相机开 Wi-Fi）' });"""
    assert html.count(old) == 1, '電源ON 那行没找到'
    return html.replace(old, new, 1)


@step('P2 0x1D01 的回帧必须正好 0 才算成功（官方 if(ret != 0) → 失败）')
def p2_judge(html):
    old = """        bleAutoSay('✅ 相机收下了「' + st.name + '」' + (code >= 0 ? ('：结果码 ' + code + '（' + bleResultText(code) + '）') : '')
                   + '（' + ackDec + '）', (code >= 0) ? 'ok' : 'warn');"""
    new = """        var _okCode = (code >= 0);
        if(st.ch === 0x1D){                     /* STEPS_MARK：官方对 0x1D01 用 `if(ret != 0) → 失败` */
          _okCode = (code === 0);
          bleAutoSay((_okCode ? '✅ 相机接受了「' + st.name + '」' : '❌ 相机**拒绝**了「' + st.name + '」')
            + '：结果码 ' + code + '（官方这条要求**正好 0**）'
            + (_okCode ? ' → 相机应该开始进 Wi-Fi 传输态了' : ' → 需要的是口令认证（相机屏幕「蓝牙配对」那串，或扫二维码自动填）'),
            _okCode ? 'ok' : 'err');
        } else {
          bleAutoSay('✅ 相机收下了「' + st.name + '」' + (code >= 0 ? ('：结果码 ' + code + '（' + bleResultText(code) + '）') : '')
                     + '（' + ackDec + '）', _okCode ? 'ok' : 'warn');
        }"""
    assert html.count(old) == 1, '应答判定那段没找到'
    return html.replace(old, new, 1)


@step('P3 ② 按钮文案 + 说明改成"官方两条命令"')
def p3_label(html):
    old = 'data-tv="cv-wake">② 唤醒相机（電源ON）</button>'
    new = 'data-tv="cv-wake">② 让相机开 Wi-Fi（官方两条命令）</button>'
    assert html.count(old) == 1, '② 按钮没找到'
    html = html.replace(old, new, 1)
    old2 = """      <b>「②」只是把「電源ON」发给相机（唤醒睡着的相机）—— 它打不开相机 Wi-Fi</b>：
      相机 Wi-Fi 只能在<b>相机上</b>开（MENU → Wi-Fi/蓝牙 → 连接到智能手机），或用相机屏幕上的二维码扫。"""
    new2 = """      <b>「②」发的是官方"点导入图片"时那两条命令</b>（`電源ON` + `リモコンモード 0x1D01`）——
      这才是让相机自动进 Wi-Fi 传输态的做法；若相机拒绝，多半是**还没有蓝牙口令**（官方在连蓝牙时就用 `str.blePass`）：
      扫相机屏幕上的二维码会自动填入口令，或手填（相机 MENU → Wi-Fi/蓝牙 → 连接到智能手机 → 蓝牙配对 会显示）。"""
    assert html.count(old2) == 1, '说明那段没找到'
    return html.replace(old2, new2, 1)


@step('P4 结论日志换成"官方两条命令"的说法')
def p4_concl(html):
    old = """            bleAutoSay('【结论】相机 Wi-Fi 是**相机侧**的事：请在相机上 MENU → Wi-Fi/蓝牙 → 连接到智能手机'
              + '（屏幕会出二维码），再点③连它 —— 或用「扫码连接」扫那个二维码。'
              + '蓝牙这条链的作用是"唤醒相机 + 口令认证"，它不会替相机打开 Wi-Fi。', 'warn');"""
    new = """            bleAutoSay('【下一步】相机接受 0x1D01 后应开始进 Wi-Fi 传输态 → 直接点③连它（记住的 SSID+BSSID）。'
              + '若 0x1D01 被拒（结果码 ≠0）：先扫相机二维码把**蓝牙口令**记住（官方连蓝牙时就带 `str.blePass`），再点②。', 'warn');"""
    assert html.count(old) == 1, '结论那段没找到'
    return html.replace(old, new, 1)


@step('P5 0x1D01 的"码认不出"≠"相机拒绝"（别把 -1 说成拒绝）')
def p5_nocode(html):
    old = """          _okCode = (code === 0);
          bleAutoSay((_okCode ? '✅ 相机接受了「' + st.name + '」' : '❌ 相机**拒绝**了「' + st.name + '」')
            + '：结果码 ' + code + '（官方这条要求**正好 0**）'"""
    new = """          _okCode = (code === 0);
          if(code < 0){
            bleAutoSay('这条「' + st.name + '」**没等到应答**（回帧不是给它的）—— 帧是发出去了，'
              + '若相机那边没动作，多半要先把**蓝牙口令**给它（扫二维码会自动填）', 'warn');
          } else
          bleAutoSay((_okCode ? '✅ 相机接受了「' + st.name + '」' : '❌ 相机**拒绝**了「' + st.name + '」')
            + '：结果码 ' + code + '（官方这条要求**正好 0**）'"""
    assert html.count(old) == 1, '0x1D01 判定那段没找到'
    return html.replace(old, new, 1)


@step('P6 没在观察窗里时，也别一律说"没能把相机唤醒"（回过帧就照实说）')
def p6_tail2(html):
    old = """        var tip = _bleLastAck
          ? ('相机回过帧（' + _bleLastAck.dec + '）→ 帧能到相机；把「复制日志」发我看它回了什么')"""
    new = """        var tip = _bleLastAck
          ? ('相机回过帧（' + _bleLastAck.dec + '）→ 帧能到相机；把「复制日志」发我看它回了什么')"""
    assert html.count(old) == 1, 'tip 那段没找到'
    old2 = """        bleAutoSay('没能把相机唤醒。' + tip, 'err');"""
    new2 = """        bleAutoSay((_bleLastAck ? '相机回过帧了（见上面那条）—— 这一轮不算"没能唤醒"，' : '没能把相机唤醒。') + tip,
          _bleLastAck ? 'warn' : 'err');"""
    assert html.count(old2) == 1, '没能唤醒那句没找到'
    return html.replace(old2, new2, 1)


@step('P7 序列跑完但没在观察窗里：不断言"没能唤醒"（结论只由观察窗下）')
def p7_verdict(html):
    old = """        bleAutoSay((_bleLastAck ? '相机回过帧了（见上面那条）—— 这一轮不算"没能唤醒"，' : '没能把相机唤醒。') + tip,
          _bleLastAck ? 'warn' : 'err');"""
    new = """        /* STEPS_MARK：**结论只由观察窗下**（r82 的原则）。这里只是"命令发完了还没听到回音"，
           所以不说"没能把相机唤醒"—— 相机有没有开，由 ② 的观察窗和 ③ 连一次说了算。 */
        bleAutoSay((_bleLastAck ? '相机回过帧了（见上面那条）——' : '命令都发完了，但相机一帧都没回 ——') + tip,
          _bleLastAck ? 'warn' : 'err');"""
    assert html.count(old) == 1, '收尾那句没找到'
    return html.replace(old, new, 1)


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r88] 已经是目标状态 —— 不重复改。')
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
        print('[r88] ✗ %s —— **不写盘**' % e)
        return 1
    cur = cur.replace('STEPS_MARK', MARK)
    assert MARK in cur
    if cur.count("ch: 0x1D, sub: 1, payload: [0x02]") != 1:
        print('[r88] ✗ 结构自检：0x1D01 那一帧不是 1 处 —— **不写盘**')
        return 1
    if 'data-tv="cv-wake">② 让相机开 Wi-Fi（官方两条命令）' not in cur:
        print('[r88] ✗ 按钮文案没换 —— **不写盘**')
        return 1
    dh = len(cur.encode('utf-8')) - len(html.encode('utf-8'))
    if not (-2000 < dh < 8000):
        print('[r88] ✗ 页面体积不对（%+d 字节）—— **不写盘**' % dh)
        return 1
    if '--check' in sys.argv:
        print('[r88] --check：%d 步都能跑通（未写盘）' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(cur)
    print('[r88] ✓ 页面 %d 步：② 补上官方的 0x1D01{0x02}（点"导入图片"时官方发的就是这条）' % len(changed))
    print('[r88] 页面净增 %d 字节' % dh)
    return 0


if __name__ == '__main__':
    sys.exit(main())
