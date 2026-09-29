# -*- coding: utf-8 -*-
"""第 91 轮：**认出连写的十六进制 + 认出相机的"回执包"**（v3.40 真机日志把相机的话听全了）

## 真机日志（2026-09-29 06:47，v3.40）逐条读出来

```
[06:47:41] 发【唤醒：電源ON】01 01 04 0F 01 01 02 13 00 → ok:sent
[06:47:42] ← 通知 0501000000            ← 相机**回执**（第 1 帧收到了）
[06:47:42] ← 通知 0402040f0101011200    ← 相机**应答**：通道 0F、子命令 01、结果码 1、校验 0x12 ✓
[06:47:46] 相机没回应答（5 秒）—— 这条它可能不认，继续     ← ★ 我们**没认出**上面那条应答
[06:47:46] 发【唤醒：リモコンモード（让相机开 Wi-Fi）】01 02 04 1D 01 01 02 21 00 → ok:sent
[06:47:47] ← 通知 0502000000            ← 只有回执，**没有** 0x1D01 的应答
（06:47:52 再试一轮，一样：電源ON → 回执 + 应答"结果码 1"；リモコンモード → 只有回执）
```

**两条硬结论**：
1. 相机**收到了**我们的每一帧（每帧都回 `05 <seq> 00 00 00` 回执）；
2. 相机**答了 `0x0F01`**（`04 <seq+1> 04 0F 01 01 01 12 00`，结果码 1 = 已经在开机状态），
   但**不答 `0x1D01{0x02}`**（连应答都没有，只有回执）。

**为什么我们没认出来**：`bleDecodeFrame()` / `bleResultCode()` / `bleScanTlv()` 都是
`t.split(/\\s+/)` 后要求"每段正好 2 个十六进制字符" —— 真机通知是**连写**的 `0402040f0101011200`
（一整段 18 个字符）→ 直接被判成"不是字节流" → 解码放弃。第 86 轮我修的是"首字节不是 0x01"，
**没修"连写"**，所以真机上一直等于没修。

## 本轮改动（页面 only）

1. 新增 `bleBytes(hex)`：**空格/连写/带逗号冒号/带 0x** 都能拆成字节数组；奇数长度或非法字符 → null。
2. `bleDecodeFrame()` / `bleResultCode()` / `bleScanTlv()` 三处都改用它（行为不变，只是能认连写）。
3. 认"**回执包**"：`05 <seq> 00 00 00`（5 字节、首字节 0x05）→ 日志写
   `　└ 相机**回执**：确认收到第 N 帧（这类包不是命令应答）`，并记 `_bleLastReceipt`。
4. ② 里"没等到应答"那句按回执分开说：
   - 有回执、没应答 → `相机**确认收到**了这条帧（有回执），但没给这条命令的应答 —— 官方判据下这也是"没成功"`；
   - 连回执都没有 → 还是原来的"没回应答"。

## 显式声明

- 涉及：`app/base.html`、`scripts/gen_r91.py`、`scripts/dv_r91.py`、本文档 + `HANDOVER.md` + `AGENTS.md` + `OPEN-ITEMS.md` + `TEST-camera.md`。
- 不涉及：**Java 不改**；帧字节、订阅三连、`0x1D01` 序列都不动；不加权限；**新增 id / data-tv：无**。
- 探针用**真机抓到的那三串连写十六进制**当数据：`0501000000` / `0402040f0101011200` / `0502000000`。

用法：python scripts/gen_r91.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r91：'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


@step('P1 新增 bleBytes()：空格/连写/带 0x 都能拆字节')
def p1_bytes(html):
    old = """  function bleDecodeFrame(hex){"""
    new = """  /* STEPS_MARK：真机通知是**连写**的十六进制（`0402040f0101011200`），
     以前三处解码都按"空格分隔、每段 2 字符"切 → 连写直接被判成"不是字节流"、
     于是相机明明回了（结果码 1）我们却说"没回应答"。这里统一成一个拆字节函数。 */
  function bleBytes(hex){
    var t = String(hex == null ? '' : hex).trim();
    if(!t) return null;
    t = t.replace(/0x/gi, '').replace(/[\\s,;:\\-]/g, '');
    if(!/^[0-9a-fA-F]+$/.test(t) || (t.length % 2)) return null;
    var out = [], i;
    for(i = 0; i < t.length; i += 2) out.push(parseInt(t.substr(i, 2), 16));
    return out;
  }
  window.__om3bleBytes = bleBytes;
  function bleDecodeFrame(hex){"""
    assert html.count(old) == 1, 'bleDecodeFrame 没找到'
    return html.replace(old, new, 1)


@step('P2 bleDecodeFrame 用 bleBytes')
def p2_decode(html):
    old = """    var t = String(hex || '').trim();
    if(!t) return '';
    var p = t.split(/\\s+/), b = [];
    for(var i = 0; i < p.length; i++){
      if(!/^[0-9a-fA-F]{2}$/.test(p[i])) return '';      /* 不是纯字节流（例如文本）→ 不解 */
      b.push(parseInt(p[i], 16));
    }"""
    new = """    var b = bleBytes(hex);
    if(!b) return '';"""
    assert html.count(old) == 1, 'bleDecodeFrame 的切字节那段没找到'
    return html.replace(old, new, 1)


@step('P3 bleResultCode 用 bleBytes')
def p3_code(html):
    old = """    var t = String(hex || '').trim();
    if(!t) return -1;
    var p = t.split(/\\s+/), b = [];
    for(var i = 0; i < p.length; i++){
      if(!/^[0-9a-fA-F]{2}$/.test(p[i])) return -1;
      b.push(parseInt(p[i], 16));
    }"""
    new = """    var b = bleBytes(hex);
    if(!b) return -1;"""
    assert html.count(old) == 1, 'bleResultCode 的切字节那段没找到'
    return html.replace(old, new, 1)


@step('P4 bleScanTlv 用 bleBytes')
def p4_tlv(html):
    old = """    var t = String(hex || '').trim();
    if(!t) return false;
    var p = t.split(/\s+/), b = [], i;
    for(i = 0; i < p.length; i++){
      if(!/^[0-9a-fA-F]{2}$/.test(p[i])) return false;
      b.push(parseInt(p[i], 16));
    }"""
    new = """    var b = bleBytes(hex), i;
    if(!b) return false;"""
    assert html.count(old) == 1, 'bleScanTlv 的切字节那段没找到'
    return html.replace(old, new, 1)


@step('P5 认"回执包" 05 <seq> 00 00 00')
def p5_receipt(html):
    old = """        var hx = String(b || '');
        bleRec(dir + (bleShort(u) ? ('[' + bleShort(u) + ']') : '') + ' ' + hx);"""
    new = """        var hx = String(b || '');
        bleRec(dir + (bleShort(u) ? ('[' + bleShort(u) + ']') : '') + ' ' + hx);
        /* STEPS_MARK：相机对**每一帧**都回一个 5 字节回执 `05 <序号> 00 00 00`（真机 06:47 每次发帧后都有）。
           它不是命令应答 —— 但它能证明"帧真的到了相机"。 */
        try{
          var _rb = bleBytes(hx);
          if(_rb && _rb.length === 5 && _rb[0] === 0x05){
            _bleLastReceipt = { seq: _rb[1], at: Date.now() };
            bleRec('　└ 相机**回执**：确认收到第 ' + _rb[1] + ' 帧（这类包不是命令应答）', 'ok');
          }
        }catch(e5r){ om3err(e5r, "silent"); }"""
    assert html.count(old) == 1, '通知处理那两行没找到'
    return html.replace(old, new, 1)


@step('P6 ② 里"没等到应答"按回执分开说')
def p6_say(html):
    old = """        else bleAutoSay('相机没回应答（' + (BLE_AUTO_ACK_MS / 1000) + ' 秒）—— 这条它可能不认，继续', 'warn');"""
    new = """        else if(_bleLastReceipt && _bleLastReceipt.at >= _bleSendAt){
          bleAutoSay('相机**确认收到**了这条帧（有回执：第 ' + _bleLastReceipt.seq + ' 帧），'
            + '但没给这条命令的应答 —— 官方判据下这也是"没成功"', 'warn');
        }
        else bleAutoSay('相机没回应答（' + (BLE_AUTO_ACK_MS / 1000) + ' 秒）—— 这条它可能不认，继续', 'warn');"""
    assert html.count(old) == 1, '没回应答那句没找到'
    return html.replace(old, new, 1)


@step('P7 声明 回执/发帧时间 变量，并在发帧时记时刻')
def p7_vars(html):
    old = """  var _bleLastAck = null;    /* 第 35 轮：相机最后一次回帧（原始 hex + 解码），供现场判断 */"""
    new = """  var _bleLastAck = null;    /* 第 35 轮：相机最后一次回帧（原始 hex + 解码），供现场判断 */
  var _bleLastReceipt = null; /* r91：相机最后一次"回执"（05 <序号> 00 00 00）—— 证明帧真的到了相机 */
  var _bleSendAt = 0;         /* r91：最近一次发帧的时刻（判"回执/应答是不是这一帧的"） */"""
    assert html.count(old) == 1, '_bleLastAck 声明没找到'
    html = html.replace(old, new, 1)
    old2 = """    bleRec('发【' + label + '】' + hex + ' → ' + r, r.indexOf('err') === 0 ? 'err' : 'ok');"""
    new2 = """    bleRec('发【' + label + '】' + hex + ' → ' + r, r.indexOf('err') === 0 ? 'err' : 'ok');
    if(r.indexOf('err') !== 0){ _bleSendAt = Date.now(); _bleLastReceipt = null; }   /* r91 */"""
    assert html.count(old2) == 1, 'bleSendPreset 记录行没找到'
    return html.replace(old2, new2, 1)


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r91] 已经是目标状态 —— 不重复改。')
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
        print('[r91] ✗ %s —— **不写盘**' % e)
        return 1
    cur = cur.replace('STEPS_MARK', MARK)
    assert MARK in cur
    for once in ('function bleBytes(', 'window.__om3bleBytes'):
        if cur.count(once) < 1:
            print('[r91] ✗ 结构自检：%s 缺' % once)
            return 1
    if '_bleLastReceipt' not in cur or 'var _bleSendAt = 0;' not in cur:
        print('[r91] ✗ 结构自检：回执变量没声明')
        return 1
    if cur.count('var b = bleBytes(hex);') < 2:
        print('[r91] ✗ 结构自检：bleBytes 没有接到 decode/resultCode 两处')
        return 1
    dh = len(cur.encode('utf-8')) - len(html.encode('utf-8'))
    if not (0 < dh < 6000):
        print('[r91] ✗ 页面体积不对（%+d 字节）—— **不写盘**' % dh)
        return 1
    if '--check' in sys.argv:
        print('[r91] --check：%d 步都能跑通（未写盘）' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(cur)
    print('[r91] ✓ 页面 %d 步：连写十六进制能解 + 认出相机回执' % len(changed))
    print('[r91] 页面净增 %d 字节' % dh)
    return 0


if __name__ == '__main__':
    sys.exit(main())
