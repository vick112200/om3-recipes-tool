# -*- coding: utf-8 -*-
"""第 84 轮：**照官方顺序补齐 BLE 会话** —— 需求方原话：「你不是解析了官方app？为什么照抄都不会」

## 需求方反馈（2026-09-29）

> 刚才点了2相机根本就没有开wifi怎么可能会有3，你不是解析了官方app？为什么照抄都不会

## 我重新翻官方反汇编的结论（逐条带出处）

| # | 官方怎么做（出处） | 我们原来怎么做 | 差在哪 |
|---|---|---|---|
| A1 | `M2/b.x(I)`：`u(15, 1, {2})` → `01 <seq> 04 0F 01 01 02 13 00`，写 **82F949B4** | 一样 | ✅ 帧字节、通道、特征值都对（本轮不动） |
| A2 | `N2/a.s0(I[B I)`：**先要求** `m`(写特征) **和** `n`(B7A8015C) 都拿到了才允许发命令（否则抛 `BLE is not initialized.` / 命令忙） | 我们的自动链**从不订阅**，只在手动工具里订阅 | ❌ **发命令前没有建立通知会话** |
| A3 | `N2/a.u0(...)`：`setCharacteristicNotification` + 写 CCCD `00002902-…`（订阅通知）；**只有在 `onDescriptorWrite` 回调里**才把 m/n/o 三个特征装进字段 | 我们 `bleSubscribe()` 只被"手动工具"调用；自动链没有 | ❌ 同上 |
| A4 | `oishare/e.W()`：**只有** `p(8)!=0 且 p(32)==0` 才发 `0x0F01`；否则打 `.powerOn Buletooth接続モード、Locationモード時は電源ONしない` 并**当成功**收口 | `blePowerOnBlock()` 写了这条规则，但自动链从没收过状态包 → `BLE_STAT.flags = -1` → **永远放行** | ❌ 前提判据从来没生效过 |
| A5 | 状态包从**通知**来：`N2/a.e0(BluetoothDevice,[B)` → TLV `len|type|payload`；`type=0xFF` → 8 字节状态 → `byte[5]` 的 bit0/1/2/3/5（bit3 = 蓝牙连接模式、bit5 = 定位），`M2/b.p(mask)` 取位 | `bleScanTlv()` 会解，但**从没人喂给它**（没订阅→没通知） | ❌ 同上 |
| A6 | `M2/b$b.a()`：等待应答，用 `c()[3]==cmd>>8 && c()[5]==cmd&0xFF` 认出"这是给这条命令的回帧"，**返回 `c()[6]` = 结果码**；`ret>=0` 才算成功（`oishare/e$e.run`） | 我们解出"相机回帧…"但把结果码标注成**【推测】** | ⚠ 现在**确证**：结果码就是回帧的第 7 字节（下标 6），本轮把标注改掉 |
| A7 | 连接顺序：`oishare/e.I()`（connectResult）→ `A()`(authPasscode `0x0C02`) → 成功后 `l()` → `W()`(powerOn `0x0F01`) | 我们：有口令才认证，然后直接 電源ON | ✅ 顺序一致（只是我们常常"没有口令"→跳过认证） |
| A8 | `N2/a.t0()`：往 `n`(B7A8015C) 写 5 字节 `03 <x> 00 00 00`（会话/握手，`mCmdStatus=103`） | 没做 | ⏳ 本轮**不做**（先用 A2/A3/A4 把会话建起来看结果；这条记进 OI，下一轮按真机反馈再定） |

## 本轮改动（页面 only，不动 Java、不动帧字节）

1. **`bleSubNotify(then, why)`**：自动链在"服务发现完成"后**先订阅通知**（`05A02050`），
   等 `cccd` 事件（= `onDescriptorWrite`）**status=0** 才继续；2.5 秒没等到就如实说"订阅没成功"再继续（不假装）。
2. **`svc` 分支**：①只连 / ②自动唤醒 / 唤醒前自动连 —— 三条都改到订阅回调里面跑（顺序：发现 → 订阅 → 命令）。
3. **`bleAutoWake` 发帧前按官方判据**：
   - 还没收到过状态包 → 先等最多 2.5 秒（官方发开机帧前一定会先看相机报的「蓝牙连接模式」位）；
   - 拿到就按 `blePowerOnBlock()` 判：**不在蓝牙连接模式 / 在定位模式 → 照官方"不发"**，并把相机自己报的状态写进日志；
   - 一直没状态包 → 如实写"相机没报状态包（可能没在「蓝牙连接模式」）"，照旧试一次。
4. **应答码确证**：发完帧等到通知时，用回帧的 `[6]` 当结果码来解读（`0 = 相机接受`），
   把 `bleDecodeFrame()` 里那句"【推测】"改成确证（出处 A6）。
5. 日志里加一行"相机状态包：…"，让"相机自己怎么说的"和"我们怎么判的"都在同一份日志里。

## 显式声明

- 涉及：`app/base.html`（订阅/顺序/判据/解码）、`scripts/gen_r84.py`、`scripts/dv_r84.py`、
  本文档 + `HANDOVER.md` + `AGENTS.md` + `OPEN-ITEMS.md`（`OI-17`）+ `TEST-camera.md`。
- 不涉及：**Java 一行都不改**（`bleSubscribe`/`cccd` 事件早就有了）；帧字节/通道/特征值不变；
  权限不变；`localStorage` 不变；相机 HTTP/CGI 不变；**新增 id：无；新增 data-tv：无**。
- 幂等：`r84：` 判据 + 每步断言 + 体积兜底（页面 < 16 KB）；重复跑 = "已经是目标状态"。

用法：python scripts/gen_r84.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r84：'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


# ---------------------------------------------------------------- P1 订阅
P1_OLD = """  var _bleAckCb = null;      /* 第 35 轮：正在等相机应答的回调（发完帧挂上，相机回通知时调） */"""
P1_NEW = """  var _bleAckCb = null;      /* 第 35 轮：正在等相机应答的回调（发完帧挂上，相机回通知时调） */
  /* STEPS_MARK官方顺序（N2/a.u0 + onDescriptorWrite + M2/b.s0）：
     发现服务 → **订阅通知（写 CCCD）** → 才能发命令。
     我们以前只在"手动蓝牙工具"里订阅，**自动链一直没订阅** → 相机的状态包/应答一个都收不到，
     `blePowerOnBlock()` 的前提判据（bit3 蓝牙连接模式）也永远拿不到 → 从不生效。 */
  var OM3_BLE_NOTIFY = '05A02050-0860-4919-8ADD-9801FBA8B6ED';   /* 官方字段 o：通知（N2/a.u0 里写 CCCD 的那个） */
  var _bleSubOk = false, _bleSubAt = 0, _bleSubCb = null;
  /* 订阅哪个特征值：先用官方那个 05A02050；万一这台相机没暴露它，就退而用"支持 notify/indicate 的第一个" */
  function bleNotifyUuid(){
    var i, j, svc = BLESVC || [];
    for(i = 0; i < svc.length; i++){
      var cs = (svc[i] && svc[i].chars) || [];
      for(j = 0; j < cs.length; j++){
        if(String(cs[j].uuid || '').toLowerCase() === OM3_BLE_NOTIFY.toLowerCase()) return cs[j].uuid;
      }
    }
    for(i = 0; i < svc.length; i++){
      var cs2 = (svc[i] && svc[i].chars) || [];
      for(j = 0; j < cs2.length; j++){
        var p2 = cs2[j].props || {};
        if(p2.notify || p2.indicate) return cs2[j].uuid;
      }
    }
    return OM3_BLE_NOTIFY;
  }
  function bleSubNotify(then, why){
    var N = window.OM3Native;
    var cb = (typeof then === 'function') ? then : function(){};
    if(_bleSubOk && (Date.now() - _bleSubAt) < 60000){ log('[BLE] 通知已经在订阅中（' + (why || '') + '），不重复订'); cb(); return; }
    if(!N || !N.bleSubscribe){
      log('[BLE] 这个版本没有订阅接口 → 跳过订阅（' + (why || '') + '）', 'warn'); cb(); return;
    }
    _bleSubCb = cb;
    var u = bleNotifyUuid();
    var r = ''; try{ r = String(N.bleSubscribe(u)); }catch(e){ r = 'err:' + e.message; }
    log('[BLE] 订阅相机通知（写 CCCD，官方顺序里发命令前必须先做）：' + bleShort(u) + ' → ' + r, 'ok');
    /* 兜底：2.5 秒还没等到 onDescriptorWrite（cccd 事件）就如实说，并继续（不假装订上了） */
    setTimeout(function(){
      if(!_bleSubCb) return;
      var f = _bleSubCb; _bleSubCb = null;
      log('[BLE] 订阅通知**没等到确认**（2.5 秒）→ 相机的状态包/应答可能收不到，先继续', 'warn');
      try{ f(); }catch(e2){ om3err(e2, "ble-sub"); }
    }, 2500);
  }"""


@step('P1 加 bleSubNotify（自动链先订阅通知，等 CCCD 确认再继续）')
def p1_sub(html):
    assert html.count(P1_OLD) == 1, '_bleAckCb 声明那行没找到'
    return html.replace(P1_OLD, P1_NEW, 1)


# ---------------------------------------------------------------- P2 cccd 事件
P2_OLD = """      else if(ev === 'cccd'){ bleRec('（CCCD 写入结果 status=' + b + '）', (String(b) === '0') ? 'quiet' : 'warn'); }"""
P2_NEW = """      else if(ev === 'cccd'){
        var _cok = (String(b) === '0');
        bleRec('（CCCD 写入结果 status=' + b + '）' + (_cok ? ' —— 通知订阅成功，相机会开始推状态包' : ''), _cok ? 'ok' : 'warn');
        if(_cok){ _bleSubOk = true; _bleSubAt = Date.now(); }
        if(_bleSubCb){
          var _cf = _bleSubCb; _bleSubCb = null;
          try{ _cf(); }catch(e5){ om3err(e5, "ble-sub-cb"); }
        }
      }"""


@step('P2 cccd 事件：订阅成功就放行后续（并把"订阅好了"写进日志）')
def p2_cccd(html):
    assert html.count(P2_OLD) == 1, 'cccd 分支没找到'
    return html.replace(P2_OLD, P2_NEW, 1)


# ---------------------------------------------------------------- P3 svc 分支
P3_OLD = """          /* 第 34 轮：自动蓝牙链连上后 → 走**依次试两帧**的自动唤醒（bleAutoWake） */
          if(window.__om3bleAutoWake){"""
P3_NEW = """          /* STEPS_MARK：**先订阅通知，再做后面的事**（官方：onDescriptorWrite 之后才允许发命令）。
             ①只连 / ②自动唤醒 / 唤醒前自动连 三条都挪进订阅回调里跑。 */
          bleSubNotify(function(){
          /* 第 34 轮：自动蓝牙链连上后 → 走**依次试两帧**的自动唤醒（bleAutoWake） */
          if(window.__om3bleAutoWake){"""
P3_OLD2 = """          if(!BLESVC.length) bleRec('⚠ 相机没暴露任何服务 —— 可能需要在相机上先\"配对/允许连接\"，或换个设备再连', 'warn');"""
P3_NEW2 = """          }, '服务发现完（发命令前）');
          if(!BLESVC.length) bleRec('⚠ 相机没暴露任何服务 —— 可能需要在相机上先\"配对/允许连接\"，或换个设备再连', 'warn');"""


@step('P3 svc 分支：把①只连/②自动唤醒整段挪进"订阅完成"的回调')
def p3_svc(html):
    assert html.count(P3_OLD) == 1, 'svc 里的自动唤醒入口没找到'
    html = html.replace(P3_OLD, P3_NEW, 1)
    assert html.count(P3_OLD2) == 1, 'svc 分支收尾那句没找到'
    return html.replace(P3_OLD2, P3_NEW2, 1)


# ---------------------------------------------------------------- P4 官方判据
P4_OLD = """    if(_bleWakeRunning){ bleAutoSay('唤醒已经在跑了，不重复发（等它跑完；要重来先点「停止自动连蓝牙」）', 'warn'); return; }
    _bleWakeRunning = true;
    var pass = blePassGet();"""
P4_NEW = """    if(_bleWakeRunning){ bleAutoSay('唤醒已经在跑了，不重复发（等它跑完；要重来先点「停止自动连蓝牙」）', 'warn'); return; }
    _bleWakeRunning = true;
    var pass = blePassGet();
    /* STEPS_MARK：**官方判据**（oishare/e.W()）：只有 p(8)!=0（相机报了「蓝牙连接模式」）且 p(32)==0（不在定位）
       才发 0x0F01；否则官方根本不发。要判就得先有状态包 —— 而状态包只在**订阅之后**才来。
       所以：没收到过 → 先等 2.5 秒；还是没有 → 如实说，照旧试（不因为"不知道"就把用户拦住）。 */
    if(BLE_STAT.at){
      bleAutoSay('相机状态包：' + (BLE_STAT.txt || ('标志 0x' + bleByte2(BLE_STAT.flags))), 'ok');
      var _blk0 = '';
      try{ _blk0 = blePowerOnBlock(); }catch(e9){ om3err(e9, "silent"); }
      if(_blk0){
        bleAutoSay('照官方**不发**开机帧：' + _blk0, 'warn');
        _bleWakeRunning = false; _bleAutoRun = false;
        /* r84：**没发帧就别再开"热点观察窗"** —— 否则 45 秒后那句"没看到相机热点"会误导
           （相机压根没收到任何东西）；直接收口并说清原因。 */
        try{
          _cvWaking = false;
          if(_cvWakeT){ clearInterval(_cvWakeT); _cvWakeT = null; }
          camCvRender();
        }catch(e12b){ om3err(e12b, "silent"); }
        try{ camCvSay('② 没发帧 —— ' + _blk0, 'warn'); }catch(e11){ om3err(e11, "silent"); }
        return;
      }
    } else {
      bleAutoSay('还没收到相机的状态包 → 等 2.5 秒（官方发开机帧前一定会先看它报的「蓝牙连接模式」位）…', 'warn');
      var _t0 = Date.now();
      var _w = setInterval(function(){
        if(BLE_STAT.at){
          clearInterval(_w);
          bleAutoSay('相机状态包：' + (BLE_STAT.txt || ('标志 0x' + bleByte2(BLE_STAT.flags))), 'ok');
          _bleWakeGo(pass); return;
        }
        if((Date.now() - _t0) > 2500){
          clearInterval(_w);
          bleAutoSay('相机一直没报状态包（多半没在「蓝牙连接模式」）→ 照旧试一次开机帧', 'warn');
          _bleWakeGo(pass);
        }
      }, 200);
      return;
    }"""
P4_ANCHOR = """    /* 官方顺序：先「パスコード認証」（知道口令时才发）→ 再「電源ON」 */
    var seq = [];"""
P4_WRAP = """    _bleWakeGo(pass);
  }
  /* STEPS_MARK：真正发明令的那一段（被上面两条路调用：状态包 OK / 等不到状态包） */
  function _bleWakeGo(pass){
    /* 官方顺序：先「パスコード認証」（知道口令时才发）→ 再「電源ON」 */
    var seq = [];"""


@step('P4 bleAutoWake：按官方判据（先看状态包，不该发就不发）')
def p4_gate(html):
    assert html.count(P4_OLD) == 1, 'bleAutoWake 头部没找到'
    html = html.replace(P4_OLD, P4_NEW, 1)
    assert html.count(P4_ANCHOR) == 1, '官方顺序注释那行没找到'
    return html.replace(P4_ANCHOR, P4_WRAP, 1)


# ---------------------------------------------------------------- P5 应答码确证
P5_OLD = """      if(ackHex) bleAutoSay('✅ 相机收下了（' + ackDec + '）', 'ok');"""
P5_NEW = """      if(ackHex){
        /* STEPS_MARK：结果码 = 回帧下标 6（官方 M2/b$b.a() 取 c()[6]，先比 c()[3]/c()[5] 认命令） */
        var code = -1; try{ code = bleResultCode(ackHex, st.ch, st.sub); }catch(e12){ om3err(e12, "silent"); }
        bleAutoSay('✅ 相机收下了「' + st.name + '」' + (code >= 0 ? ('：结果码 ' + code + (code === 0 ? '（0 = 相机接受）' : '（≠0 = 相机拒绝）')) : '')
                   + '（' + ackDec + '）', (code > 0) ? 'warn' : 'ok');
      }"""
P5_OLD2 = """        else bleAutoSay('相机没回应答（' + (BLE_AUTO_ACK_MS / 1000) + ' 秒）—— 这条它可能不认，继续', 'warn');"""
P5_NEW2 = """        else bleAutoSay('相机没回应答（' + (BLE_AUTO_ACK_MS / 1000) + ' 秒）—— 这条它可能不认，继续', 'warn');"""

P5_FN_ANCHOR = """  function bleDecodeFrame(hex){"""
P5_FN = """  /* STEPS_MARK：从回帧里取"结果码" —— 官方 M2/b$b.a() 的做法：
     先确认这是给我这条命令的回帧（下标 3 = 通道，下标 5 = 子命令），结果码取**下标 6**。
     （第 62 轮标它"推测"，本轮对着反汇编确证。）返回 -1 = 这不是给这条命令的回帧。 */
  function bleResultCode(hex, ch, sub){
    var t = String(hex || '').trim();
    if(!t) return -1;
    var p = t.split(/\\s+/), b = [];
    for(var i = 0; i < p.length; i++){
      if(!/^[0-9a-fA-F]{2}$/.test(p[i])) return -1;
      b.push(parseInt(p[i], 16));
    }
    if(b.length < 7 || b[0] !== 0x01) return -1;
    if(ch !== undefined && Number(b[3]) !== (Number(ch) & 0xFF)) return -1;
    if(sub !== undefined && Number(b[5]) !== (Number(sub) & 0xFF)) return -1;
    return Number(b[6]);
  }
  window.__om3bleResultCode = bleResultCode;
"""


@step('P5 结果码确证：新增 bleResultCode，发帧后把相机的结果码解出来')
def p5_code(html):
    assert html.count(P5_FN_ANCHOR) == 1, 'bleDecodeFrame 锚点没找到'
    html = html.replace(P5_FN_ANCHOR, P5_FN + P5_FN_ANCHOR, 1)
    assert html.count(P5_OLD) == 1, '发帧后的应答那句没找到'
    return html.replace(P5_OLD, P5_NEW, 1)


# ---------------------------------------------------------------- P6 干掉"推测"
P6_OLD = """    /* r62：payload 只有 1 字节时，顺手附一行"若是结果码"的推测。
       ⚠ 码在帧里的位置**还没确证**（SPEC-round62 §3.4），所以标明【推测】，不当结论用。 */
    if(bodyLen === 1){
      s += '　（若是结果码：' + bleCodeText('conn', b[6]) + ' ／ 检测监听：' + bleCodeText('detect', b[6]) + '）【推测】';
    }"""
P6_NEW = """    /* r84：结果码位置**已确证** —— 官方 M2/b$b.a() 就是取回帧下标 6（先比下标 3/5 认命令）。
       所以这里不再标【推测】。 */
    if(bodyLen >= 1){
      s += '　结果码 ' + b[6] + '（0 = 相机接受）／ ' + bleCodeText('conn', b[6])
        + ' ／ 检测监听：' + bleCodeText('detect', b[6]);
    }"""


@step('P6 解码文案：结果码从"【推测】"改成确证（出处：官方 M2/b$b.a()）')
def p6_text(html):
    assert html.count(P6_OLD) == 1, '那段【推测】注释没找到'
    return html.replace(P6_OLD, P6_NEW, 1)


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r84] 已经是目标状态 —— 不重复改。')
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
        print('[r84] ✗ %s —— **不写盘**' % e)
        return 1
    cur = cur.replace('STEPS_MARK', MARK)
    assert MARK in cur
    # 结构自检
    for once in ('function bleSubNotify(', 'function bleNotifyUuid(', 'function _bleWakeGo(', 'function bleResultCode(', 'function bleAutoWake('):
        n = cur.count(once)
        if n != 1:
            print('[r84] ✗ 结构自检：`%s` 出现 %d 次 —— **不写盘**' % (once, n))
            return 1
    dh = len(cur.encode('utf-8')) - len(html.encode('utf-8'))
    if not (0 < dh < 16000):
        print('[r84] ✗ 页面体积不对（%+d 字节）—— **不写盘**' % dh)
        return 1
    if '--check' in sys.argv:
        print('[r84] --check：%d 步都能跑通（未写盘）' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(cur)
    print('[r84] ✓ 页面 %d 步：自动链**先订阅通知**（官方顺序）→ 按相机状态包判该不该发 → 确证结果码' % len(changed))
    print('[r84] 页面净增 %d 字节（Java 本轮不动）' % dh)
    return 0


if __name__ == '__main__':
    sys.exit(main())
