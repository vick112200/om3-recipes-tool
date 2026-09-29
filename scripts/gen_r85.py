# -*- coding: utf-8 -*-
"""第 85 轮：**订阅三个特征值** —— 真机日志（v3.36）暴露的最后一处漏抄

## 需求方真机日志（2026-09-29 00:57，v3.36）说明了什么

好的一面（v3.36 的新东西都生效了）：
  · `[BLE] 订阅相机通知（写 CCCD，官方顺序里发命令前必须先做）… → ok:subscribed`
  · `订阅 05a02050-…：CCCD 已写` → `（CCCD 写入结果 status=0） —— 通知订阅成功，相机会开始推状态包`
  · 之后：`还没收到相机的状态包 → 等 2.5 秒` → `相机一直没报状态包（多半没在「蓝牙连接模式」）→ 照旧试一次开机帧`
  · 三次「電源ON」都发出去了（`01 01/02/03 04 0F 01 01 02 13 00`，`→ ok:sent`），**相机一次都没回**
  · 用户两次按「相机没反应（屏幕没变）」

**结论：订上了 CCCD（GATT 层面成功），但相机一个包都不推、也不回应答。**

## 根因（这次是反汇编里的最后一块拼图）

官方 App 在 `onDescriptorWrite` 之后**依次**订阅**三个**特征值（`N2/a$c$b/$c/$d.run`，各自 `t(gatt, UUID.fromString(...), true)`
= `u0()` = `setCharacteristicNotification` + 写 CCCD `00002902-…`；每个等上一个的 `onDescriptorWrite`，见 `N2/a$c.onDescriptorWrite`）：

| 顺序 | 特征值 | 类/行 |
|---|---|---|
| 1 | **`82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68`**（= **写命令**的那个！） | `N2/a$c$b.run` @dis.txt 65725–65749 |
| 2 | `B7A8015C-CB94-4EFA-BDA2-B7921FA9951F`（第二个写特征） | `N2/a$c$c.run` @65786–65810 |
| 3 | `05A02050-0860-4919-8ADD-9801FBA8B6ED` | `N2/a$c$d.run` @65847–65871 |

而我们 v3.36 只订了**第 3 个**（`05A02050`）—— 那就解释了真机现象：**相机的状态包和命令应答是从第一个（82F949B4）推回来的**，
我们没在听那一路，所以"订上了却什么都没收到"。（第 62 轮把 `05A02050` 当成"通知特征"，是因为 `bleScanTlv/decode` 那时
只看"内容像不像状态包"，没有核对**从哪个特征推来**。）

## 本轮改动（页面 only）

1. `bleSubNotify()`：按官方顺序**依次订阅三个**特征值（82F949B4 → B7A8015C → 05A02050），
   每个等 `cccd status=0` 再订下一个（单个 1.5 秒、整串 6 秒封顶）；少一个就跳过（有些固件可能不暴露），
   每个都写清结果；**只要第一个（82F949B4）订上**就算会话可用（`_bleSubOk`），
   整串都拿不到确认时如实说"没等到确认"再继续。
2. 其余不变（判据、结果码、观察窗收口都是上一轮的）。

## 显式声明

- 涉及：`app/base.html`（订阅三连）、`scripts/gen_r85.py`、`scripts/dv_r85.py`、`dv_r84`（口径修正：
  "订的是 05A02050" → "按官方顺序订三个"）、本文档 + `HANDOVER.md` + `AGENTS.md` + `OPEN-ITEMS.md`（`OI-17` 复验口径）
  + `TEST-camera.md`。
- 不涉及：**Java 不改**（`bleSubscribe(uuid)` 本来就能订任意特征值；`cccd`/`notify` 事件早就有）；
  帧字节 / 判据 / 结果码逻辑不变；不加权限；**新增 id：无；新增 data-tv：无**。

用法：python scripts/gen_r85.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r85：'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


OLD = """  function bleSubNotify(then, why){
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

NEW = """  /* STEPS_MARK**官方订的是三个特征值**（`N2/a$c$b/$c/$d.run`，各自 `t(gatt,UUID,true)`，等上一个 onDescriptorWrite）：
       1) 82F949B4-…（**写命令那个**；相机的状态包/命令应答从这一路推回来）
       2) B7A8015C-…
       3) 05A02050-…
     v3.36 只订了第 3 个 → 真机"CCCD 订上了却一个包都收不到"（日志 2026-09-29 00:56）。 */
  var OM3_BLE_SUBS = [
    '82F949B4-F5DC-4CF3-AB3C-FD9FD4017B68',   /* 命令特征 —— 应答/状态包走这里 */
    'B7A8015C-CB94-4EFA-BDA2-B7921FA9951F',
    '05A02050-0860-4919-8ADD-9801FBA8B6ED'
  ];
  /* 这台相机实际暴露了哪几个（拿 BLESVC 过滤，缺的就跳过） */
  function bleSubList(){
    var out = [], svc = BLESVC || [], i, j, k, have = {};
    for(i = 0; i < svc.length; i++){
      var u1 = String((svc[i] && svc[i].uuid) || '').toLowerCase();
      if(u1 && u1 !== OM3_BLE_SVC_LC) continue;          /* 官方只订那个服务下的三个特征 */
      var cs = (svc[i] && svc[i].chars) || [];
      for(j = 0; j < cs.length; j++) have[String(cs[j].uuid || '').toLowerCase()] = 1;
    }
    for(k = 0; k < OM3_BLE_SUBS.length; k++){
      if(have[OM3_BLE_SUBS[k].toLowerCase()]) out.push(OM3_BLE_SUBS[k]);
    }
    if(!out.length) out = OM3_BLE_SUBS.slice(0, 1);      /* 服务列表没解析出来 → 至少试命令特征 */
    return out;
  }
  var _bleSubOk = false, _bleSubAt = 0, _bleSubNext = null, _bleSubTimer = null;
  function bleSubNotify(then, why){
    var N = window.OM3Native;
    var done = (typeof then === 'function') ? then : function(){};
    if(_bleSubOk && (Date.now() - _bleSubAt) < 60000){ log('[BLE] 通知已经订阅中（' + (why || '') + '），不重复订'); done(); return; }
    if(!N || !N.bleSubscribe){
      log('[BLE] 这个版本没有订阅接口 → 跳过订阅（' + (why || '') + '）', 'warn'); done(); return;
    }
    if(_bleSubNext){ log('[BLE] 订阅正在进行中（' + (why || '') + '）→ 等它跑完', 'warn');
      var _pend = _bleSubNext; _bleSubNext = function(){ try{ _pend(); }catch(e0){} try{ done(); }catch(e1){} }; return; }
    var list = bleSubList(), idx = 0, failed = 0;
    log('[BLE] 订阅相机通知（写 CCCD；官方顺序 = 命令特征 82F949B4 → B7A8015C → 05A02050，各等上一个确认）：共 ' + list.length + ' 个');
    function finish(){
      if(_bleSubTimer){ clearTimeout(_bleSubTimer); _bleSubTimer = null; }
      _bleSubNext = null;
      if(list.length > failed){ _bleSubOk = true; _bleSubAt = Date.now(); }
      log('[BLE] 订阅结束：成功 ' + (list.length - failed) + '/' + list.length + ' 个特征值'
          + (failed ? '（有 ' + failed + ' 个没等到 CCCD 确认 → 相机的状态包/应答可能收不到）'
                    : ' —— 已订阅，发送就绪'), failed ? 'warn' : 'ok');
      try{ done(); }catch(e2){ om3err(e2, "ble-sub-done"); }
    }
    function step(){
      if(idx >= list.length){ finish(); return; }
      var u = list[idx++];
      var r = ''; try{ r = String(N.bleSubscribe(u)); }catch(e){ r = 'err:' + e.message; }
      log('[BLE]   第 ' + idx + '/' + list.length + ' 个：' + u + ' → ' + r, r.indexOf('err') === 0 ? 'warn' : 'ok');
      if(_bleSubTimer){ clearTimeout(_bleSubTimer); _bleSubTimer = null; }
      var _u = u;
      _bleSubTimer = setTimeout(function(){
        _bleSubTimer = null; failed++;
        log('[BLE]   ' + _u + ' **没等到 CCCD 确认**（1.5 秒）→ 订下一个', 'warn');
        step();
      }, 1500);
      _bleSubNext = step;
    }
    step();
  }"""


@step('P1 bleSubNotify：按官方顺序依次订阅三个特征值（命令特征 82F949B4 最要紧）')
def p1_three(html):
    assert html.count(OLD) == 1, 'bleSubNotify 没找到'
    return html.replace(OLD, NEW, 1)


P2_OLD = """  var OM3_BLE_NOTIFY = '05A02050-0860-4919-8ADD-9801FBA8B6ED';   /* 官方字段 o：通知（N2/a.u0 里写 CCCD 的那个） */"""
P2_NEW = """  var OM3_BLE_NOTIFY = '05A02050-0860-4919-8ADD-9801FBA8B6ED';   /* 官方字段 o：第三个通知特征 */
  var OM3_BLE_SVC_LC = 'adc505f9-4e58-4b71-b8ca-983bb8c73e4f';    /* 官方那个服务（只订它下面这三个） */
  /* r85：订阅三连的步进/超时（在 bleSubNotify 里声明，这里只放服务 UUID） */"""


@step('P2 定义服务 UUID / 订阅步进变量')
def p2_vars(html):
    assert html.count(P2_OLD) == 1, 'OM3_BLE_NOTIFY 那行没找到'
    return html.replace(P2_OLD, P2_NEW, 1)


P3_OLD = """        if(_cok){ _bleSubOk = true; _bleSubAt = Date.now(); }
        if(_bleSubCb){
          var _cf = _bleSubCb; _bleSubCb = null;
          try{ _cf(); }catch(e5){ om3err(e5, "ble-sub-cb"); }
        }"""
P3_NEW = """        if(_cok){ _bleSubOk = true; _bleSubAt = Date.now(); }
        /* r85：cccd 确认 → 订阅三连的下一步（继续订下一个；全订完才放行命令） */
        if(_bleSubTimer){ clearTimeout(_bleSubTimer); _bleSubTimer = null; }
        if(_bleSubNext){
          var _nx = _bleSubNext; _bleSubNext = null;
          try{ _nx(); }catch(e5){ om3err(e5, "ble-sub-next"); }
        }"""


@step('P3 cccd 事件：交给订阅三连的步进（不再直接把后续放行）')
def p3_cccd(html):
    assert html.count(P3_OLD) == 1, 'cccd 里的回调那段没找到'
    return html.replace(P3_OLD, P3_NEW, 1)


P4_OLD = """  var _bleSubOk = false, _bleSubAt = 0, _bleSubCb = null;
"""
P4_NEW = """  /* r84 的那三个变量已并入 r85 的订阅三连（见下面 bleSubList/bleSubNotify 上方） */
"""


@step('P4 清掉 r84 留下的重复声明（_bleSubCb 已并入订阅三连）')
def p4_dedupe(html):
    assert html.count(P4_OLD) == 1, 'r84 的变量声明行没找到'
    return html.replace(P4_OLD, P4_NEW, 1)


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r85] 已经是目标状态 —— 不重复改。')
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
        print('[r85] ✗ %s —— **不写盘**' % e)
        return 1
    cur = cur.replace('STEPS_MARK', MARK)
    assert MARK in cur
    for once in ('function bleSubNotify(', 'function bleSubList(', 'function bleNotifyUuid('):
        n = cur.count(once)
        if n != 1:
            print('[r85] ✗ 结构自检：`%s` 出现 %d 次 —— **不写盘**' % (once, n))
            return 1
    dh = len(cur.encode('utf-8')) - len(html.encode('utf-8'))
    if not (0 < dh < 12000):
        print('[r85] ✗ 页面体积不对（%+d 字节）—— **不写盘**' % dh)
        return 1
    if '--check' in sys.argv:
        print('[r85] --check：%d 步都能跑通（未写盘）' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(cur)
    print('[r85] ✓ 页面 %d 步：按官方顺序订阅**三个**特征值（命令特征 82F949B4 最先）' % len(changed))
    print('[r85] 页面净增 %d 字节（Java 不动）' % dh)
    return 0


if __name__ == '__main__':
    sys.exit(main())
