# -*- coding: utf-8 -*-
"""第 86 轮：**认出相机的应答**（真机 v3.37 日志：相机其实回了，是我们不认）

## 需求方真机日志（2026-09-29 05:53，v3.37）—— 这一份是决定性的

订阅三连**全部成功**：
```
[BLE] 订阅相机通知（…）：共 3 个
[BLE]   第 1/3 个：82F949B4-… → ok:subscribed   → CCCD 写入结果 status=0
[BLE]   第 2/3 个：B7A8015C-… → ok:subscribed   → CCCD 写入结果 status=0
[BLE]   第 3/3 个：05A02050-… → ok:subscribed   → CCCD 写入结果 status=0
[BLE] 订阅结束：成功 3/3 个特征值 —— 已订阅，发送就绪
```
发帧之后，**相机回了两条通知**（第一次！）：
```
[05:51:35] ← 通知 0501000000
[05:51:35] ← 通知 0402040f0101011200
```
第二条按官方帧布局逐字节对得上（`M2/b$b.a()` 就是比 `resp[3]`/`resp[5]`、取 `resp[6]`）：
`04 | 02 | 04 | 0F | 01 | 01 | 01 | 12 | 00` → 通道 `0x0F` ✓、子命令 `0x01` ✓、**结果码 `0x01`**、
校验 `0x0F+1+0x01+0x01 = 0x12` ✓（和我们发帧用的算法完全一样）。
=> **相机确实收到了「電源ON」并回了结果码 1。**

**但我们没认出来**：`bleDecodeFrame()` 第 5 行写着 `if(b[0] !== 0x01) return ''` ——
相机应答的首字节是 `0x04`（我们发帧才是 `0x01`），于是解码直接放弃 →
`_bleAckCb` 不触发 → 日志照旧喊"相机没回应答（5 秒）"。这就是"明明回了却像没回"的原因。

## 本轮改动（页面 only）

1. **`bleDecodeFrame()` 认两种帧**：
   - `0x01` 开头 = 我们发的（原样）；
   - 其它开头（真机看到的是 `0x04`）= **相机应答**：只要 `len+3`、通道/子命令、**校验和**自洽就按应答解，
     并直接写"结果码 N（0 = 成功）" —— 顺便把"结果码"的位置在**真机数据上**再确认一次。
2. **`bleResultCode()` 去掉 `b[0] === 0x01` 的限制**（改成校验和自洽 + 通道/子命令匹配），
   这样 `bleAckArm` 的应答回调能真的触发 → ② 不再谎报"相机没回应答"。
3. **按官方语义解释 電源ON 的结果码**（`e$e.run`：`ret >= 0` 才算成功，否则错误码 35）：
   - `0` → 相机接受；
   - `1` → **相机答"已经在开机状态"**（真机就是这个）→ 明确写一句：官方也把它当成功，
     但**它不会因此打开 Wi-Fi**（相机 Wi-Fi 要在相机上进入「连接到智能手机」）；
   - `34` → 口令错、`35` → 开机失败、其它 → 原样报码。
4. **把官方前提写到②的开头**（不再让用户白等 45 秒）：
   没收到状态包时说清"官方规则是**相机报了「蓝牙连接模式」才发开机帧**；没报包时官方**根本不发**、
   也不会让相机开 Wi-Fi —— 相机 Wi-Fi 要么在相机上开（MENU → Wi-Fi/蓝牙 → 连接到智能手机），
   要么扫相机屏幕上的二维码"。

## 显式声明

- 涉及：`app/base.html`（解码/结果码/文案）、`scripts/gen_r86.py`、`scripts/dv_r86.py`、本文档
  + `HANDOVER.md` + `AGENTS.md` + `OPEN-ITEMS.md` + `TEST-camera.md`。
- 不涉及：**Java 不改**；订阅三连（r85）不变；帧字节不变；不加权限；**新增 id / data-tv：无**。
- 探针里用**真机抓到的那两串字节**当测试数据（`0402040f0101011200` / `0501000000`）。

用法：python scripts/gen_r86.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r86：'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


# ---------------------------------------------------------------- P1 认应答帧
P1_OLD = """    if(b.length < 6 || b[0] !== 0x01) return '';
    var seq = b[1], lenB = b[2], ch = b[3], sub = b[5];
    var s = '相机回帧：序号 ' + seq + '　通道 0x' + bleByte2(ch) + '　子命令 0x' + bleByte2(sub);
    var bodyLen = lenB - 3;                              /* 数据长度 */
    var sumAt = 6 + bodyLen;
    if(bodyLen > 0 && sumAt + 1 <= b.length){
      var pay = [];
      for(var k = 6; k < sumAt; k++) pay.push(b[k]);
      s += '　数据 ' + bleHexOf(pay) + '（' + pay.length + ' 字节）';
    }
    if(sumAt + 1 <= b.length){
      var got = b[sumAt], calc = (ch + 1 + sub) & 0xFF;
      for(var k2 = 6; k2 < sumAt; k2++) calc = (calc + b[k2]) & 0xFF;
      s += '　校验 ' + (got === calc ? 'OK' : ('✗（帧里 0x' + bleByte2(got) + '，按官方算法应 0x' + bleByte2(calc) + '）'));
    }"""
P1_NEW = """    /* STEPS_MARK**两种帧都要认**：
       · `0x01` 开头 = 我们发出去的（照旧）；
       · **其它开头（真机抓到的是 `0x04`）= 相机应答** —— 布局一样（[2]=len+3、[3]=通道、[5]=子命令、
         [6..]=数据、末两字节=校验+0x00），只是首字节不同。以前这里写死 `b[0] !== 0x01 → 放弃`，
         于是相机明明回了（真机 2026-09-29 05:51:35 `0402040f0101011200`）我们却当没收到。 */
    if(b.length < 6) return '';
    var isAns = (b[0] !== 0x01);
    var seq = b[1], lenB = b[2], ch = b[3], sub = b[5];
    var s = (isAns ? '相机回帧（应答）：' : '相机回帧：')
      + '序号 ' + seq + '　通道 0x' + bleByte2(ch) + '　子命令 0x' + bleByte2(sub);
    var bodyLen = lenB - 3;                              /* 数据长度 */
    var sumAt = 6 + bodyLen;
    if(bodyLen > 0 && sumAt + 1 <= b.length){
      var pay = [];
      for(var k = 6; k < sumAt; k++) pay.push(b[k]);
      s += '　数据 ' + bleHexOf(pay) + '（' + pay.length + ' 字节）';
    }
    if(sumAt + 1 <= b.length){
      var got = b[sumAt], calc = (ch + 1 + sub) & 0xFF;
      for(var k2 = 6; k2 < sumAt; k2++) calc = (calc + b[k2]) & 0xFF;
      s += '　校验 ' + (got === calc ? 'OK' : ('✗（帧里 0x' + bleByte2(got) + '，按官方算法应 0x' + bleByte2(calc) + '）'));
      /* 校验自洽 + 有数据字节 → 这就是"结果码"（官方 M2/b$b.a() 取 resp[6]；真机数据再确认一次） */
      if(got === calc && isAns && bodyLen >= 1) s += '　→ **结果码 ' + b[6] + '**';
    }"""
P1_OLD2 = """    if(bodyLen >= 1){
      s += '　结果码 ' + b[6] + '（0 = 相机接受）／ ' + bleCodeText('conn', b[6])
        + ' ／ 检测监听：' + bleCodeText('detect', b[6]);
    }"""
P1_NEW2 = """    if(bodyLen >= 1){
      s += '　（结果码 ' + b[6] + '：' + bleResultText(b[6]) + '）';
    }"""


@step('P1 认相机应答帧（首字节不是 0x01 也算），并把结果码写清楚')
def p1_decode(html):
    assert html.count(P1_OLD) == 1, 'bleDecodeFrame 的帧头那段没找到'
    html = html.replace(P1_OLD, P1_NEW, 1)
    assert html.count(P1_OLD2) == 1, '结果码那段没找到'
    return html.replace(P1_OLD2, P1_NEW2, 1)


# ---------------------------------------------------------------- P2 结果码文本 + 去掉首字节限制
P2_ANCHOR = """  function bleResultCode(hex, ch, sub){"""
P2_NEW_FN = """  /* STEPS_MARK结果码的人话（官方 e$e.run：`ret >= 0` 才算成功，否则错误码 35；34 = 口令错）
     —— 真机 2026-09-29 05:51 相机对「電源ON」回的就是 **1**（相机已在开机状态）。 */
  function bleResultText(n){
    n = Number(n);
    if(n === 0) return '0 = 成功';
    if(n === 1) return '1 = 相机答「已经在开机状态」（官方也当成功，但**不会因此打开 Wi-Fi**）';
    if(n === 33) return '33 = 手机蓝牙被关了';
    if(n === 34) return '34 = 蓝牙口令错（要口令认证：相机屏幕「蓝牙配对」那串，或扫二维码自动填）';
    if(n === 35) return '35 = 开机失败（POWON_ERROR）';
    if(n === 36) return '36 = 结束';
    return n + ' = 认不出的码（把整条日志发我）';
  }
  window.__om3bleResultText = bleResultText;
"""
P2_OLD_CODE = """    if(b.length < 7 || b[0] !== 0x01) return -1;
    if(ch !== undefined && Number(b[3]) !== (Number(ch) & 0xFF)) return -1;
    if(sub !== undefined && Number(b[5]) !== (Number(sub) & 0xFF)) return -1;
    return Number(b[6]);"""
P2_NEW_CODE = """    /* STEPS_MARK首字节**不要求** 0x01：相机应答是 0x04（真机数据）。改用"校验自洽 + 通道/子命令匹配"来认。 */
    if(b.length < 8) return -1;
    if(ch !== undefined && Number(b[3]) !== (Number(ch) & 0xFF)) return -1;
    if(sub !== undefined && Number(b[5]) !== (Number(sub) & 0xFF)) return -1;
    var bodyLen = Number(b[2]) - 3, sumAt = 6 + bodyLen;
    if(bodyLen < 1 || sumAt + 1 > b.length) return -1;
    var calc = (Number(b[3]) + 1 + Number(b[5])) & 0xFF, k;
    for(k = 6; k < sumAt; k++) calc = (calc + Number(b[k])) & 0xFF;
    if(Number(b[sumAt]) !== calc) return -1;              /* 校验不对 → 不当作"这条命令的应答" */
    return Number(b[6]);"""


@step('P2 结果码：去掉"必须 0x01 开头"，改用校验和认；并加人话翻译')
def p2_code(html):
    assert html.count(P2_ANCHOR) == 1, 'bleResultCode 没找到'
    html = html.replace(P2_ANCHOR, P2_NEW_FN + P2_ANCHOR, 1)
    assert html.count(P2_OLD_CODE) == 1, 'bleResultCode 的判据没找到'
    return html.replace(P2_OLD_CODE, P2_NEW_CODE, 1)


# ---------------------------------------------------------------- P3 发帧前的实话
P3_OLD = """        } else {
      bleAutoSay('还没收到相机的状态包 → 等 2.5 秒（官方发开机帧前一定会先看它报的「蓝牙连接模式」位）…', 'warn');"""
P3_OLD = """      bleAutoSay('还没收到相机的状态包 → 等 2.5 秒（官方发开机帧前一定会先看它报的「蓝牙连接模式」位）…', 'warn');"""


@step('P3 ② 开头就说清官方前提（相机没报「蓝牙连接模式」时官方根本不开 Wi-Fi）')
def p3_pre(html):
    assert html.count(P3_OLD) == 1, '等状态包那句没找到'
    new = """      bleAutoSay('相机没报状态包 → 官方规则这时**根本不发**开机帧（它只在相机报了「蓝牙连接模式」时才发，'
        + '那才是相机进传输态的前提）。相机 Wi-Fi 只能在**相机上**开：MENU → Wi-Fi/蓝牙 → 连接到智能手机；'
        + '或扫相机屏幕上的二维码。我还是照发一次试试（2.5 秒后）…', 'warn');"""
    return html.replace(P3_OLD, new, 1)


# ---------------------------------------------------------------- P4 校验 ✗ 就不写"结果码"
P4_OLD = """    if(bodyLen >= 1){
      s += '　（结果码 ' + b[6] + '：' + bleResultText(b[6]) + '）';
    }"""
P4_NEW = """    if(bodyLen >= 1){
      if(sumOk === false) s += '　（校验 ✗ → **不当应答用**）';
      else s += '　（结果码 ' + b[6] + '：' + bleResultText(b[6]) + '）';
    }"""
P4_OLD2 = """      if(got === calc && isAns && bodyLen >= 1) s += '　→ **结果码 ' + b[6] + '**';
    }"""
P4_NEW2 = """      sumOk = (got === calc);
      if(sumOk && isAns && bodyLen >= 1) s += '　→ **结果码 ' + b[6] + '**';
    }"""
P4_OLD3 = """    var isAns = (b[0] !== 0x01);"""
P4_NEW3 = """    var isAns = (b[0] !== 0x01), sumOk = null;"""


@step('P4 校验 ✗ 的帧不许写"结果码"（不当应答用）')
def p4_sumok(html):
    assert html.count(P4_OLD3) == 1, 'isAns 那行没找到'
    html = html.replace(P4_OLD3, P4_NEW3, 1)
    assert html.count(P4_OLD2) == 1, '校验那行没找到'
    html = html.replace(P4_OLD2, P4_NEW2, 1)
    assert html.count(P4_OLD) == 1, '结果码汇总那行没找到'
    return html.replace(P4_OLD, P4_NEW, 1)


# ---------------------------------------------------------------- P5 收尾别再说"没回应答"
P5_OLD = """        if(_cvWaking){
          bleAutoSay('相机没回应答（' + (BLE_AUTO_ACK_MS / 1000) + ' 秒）—— 它本来就不回 ACK（真机证实，正常），'
            + '**继续等热点**…', 'warn');
          return;
        }"""
P5_NEW = """        if(_cvWaking){
          /* STEPS_MARK：**相机其实会回**（真机 2026-09-29 05:51 回了两条通知；以前是我们没认出来）。
             所以这里按"有没有回过帧"分两句，别再一律说"没回应答"。 */
          if(_bleLastAck){
            var _c2 = -1;
            try{ _c2 = bleResultCode(_bleLastAck.hex, 0x0F, 0x01); }catch(e13){ om3err(e13, "silent"); }
            bleAutoSay('相机回了应答' + (_c2 >= 0 ? ('（结果码 ' + _c2 + '：' + bleResultText(_c2) + '）') : '')
              + ' —— 蓝牙这条命令是通的；接下来看相机有没有进传输态（相机屏幕/相机状态包）', 'ok');
          } else {
            bleAutoSay('相机没回应答（' + (BLE_AUTO_ACK_MS / 1000) + ' 秒）—— **继续等热点**…', 'warn');
          }
          return;
        }"""
P5_OLD2 = """        bleAutoSay('✅ 相机收下了「' + st.name + '」' + (code >= 0 ? ('：结果码 ' + code + (code === 0 ? '（0 = 相机接受）' : '（≠0 = 相机拒绝）')) : '')
                   + '（' + ackDec + '）', (code > 0) ? 'warn' : 'ok');"""
P5_NEW2 = """        bleAutoSay('✅ 相机收下了「' + st.name + '」' + (code >= 0 ? ('：结果码 ' + code + '（' + bleResultText(code) + '）') : '')
                   + '（' + ackDec + '）', (code >= 0) ? 'ok' : 'warn');"""


@step('P5 收尾按"有没有回过帧"说话；结果码按官方语义（>=0 都算成功）')
def p5_tail(html):
    assert html.count(P5_OLD) == 1, '收尾那段没找到'
    html = html.replace(P5_OLD, P5_NEW, 1)
    assert html.count(P5_OLD2) == 1, '收下那句没找到'
    return html.replace(P5_OLD2, P5_NEW2, 1)


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r86] 已经是目标状态 —— 不重复改。')
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
        print('[r86] ✗ %s —— **不写盘**' % e)
        return 1
    cur = cur.replace('STEPS_MARK', MARK)
    assert MARK in cur
    for once in ('function bleResultCode(', 'function bleResultText(', 'function bleDecodeFrame('):
        n = cur.count(once)
        if n != 1:
            print('[r86] ✗ 结构自检：`%s` 出现 %d 次 —— **不写盘**' % (once, n))
            return 1
    dh = len(cur.encode('utf-8')) - len(html.encode('utf-8'))
    if not (0 < dh < 10000):
        print('[r86] ✗ 页面体积不对（%+d 字节）—— **不写盘**' % dh)
        return 1
    if '--check' in sys.argv:
        print('[r86] --check：%d 步都能跑通（未写盘）' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(cur)
    print('[r86] ✓ 页面 %d 步：认出相机应答（首字节≠0x01）+ 结果码人话 + ②开头讲清官方前提' % len(changed))
    print('[r86] 页面净增 %d 字节（Java 不动）' % dh)
    return 0


if __name__ == '__main__':
    sys.exit(main())
