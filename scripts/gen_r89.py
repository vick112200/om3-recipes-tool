# -*- coding: utf-8 -*-
"""第 89 轮：**修"①在连的时候点② → 连上后谁都不发帧"**（真机 v3.38 日志 06:23 那次的空窗）

## 真机日志（2026-09-29 06:23，v3.38）暴露的 bug

```
[06:23:23] ① 连接相机蓝牙：…（只连，不发唤醒帧）      ← 用户点①，启动"只连"链（__om3bleConnOnly=true）
[06:23:23] 蓝牙断开：连接断开（status=133）           ← 第一次连接失败
[06:23:27] ② 蓝牙还没连 → 先连蓝牙…（连上后自动发一次「電源ON」）   ← 用户点②
[06:23:27] [自动·蓝牙] 已经在连了，不重复跑（点②让相机开 Wi-Fi（传输））   ← ★ camBleAuto 直接 return
[06:23:43] 连相机蓝牙超时（20 秒）→ 自动再试一次…      ← 重试
[06:23:44] ✅ 已连接（status=0）→ 06:23:45 服务发现完成 → 订阅 3/3 成功
[06:23:49] ② 上一次发的帧还在等相机应答（最多 5 秒）…   ← 用户再点②被挡（其实**一帧都没发过**）
[06:24:11] 蓝牙链没在 10 秒内把热点点起来 → …          ← 观察窗白等到点
```

**根因（三处，都在我们的状态管理上）**：

1. `camCvWake()` 在"蓝牙没连"时只调了 `camBleAuto('点②…')`，**没有把"连上要发帧"这件事登记下来**；
   而 `camBleAuto` 一看"已经在连了"（① 的只连链）就 `return` —— ② 的意图**丢了**。
2. 重试里 `window.__om3bleAutoWake = !_cvConnectOnly` 用的是**启动时那个链**的 `_cvConnectOnly`（① 的 `true`），
   于是 `svc` 回调里"自动唤醒"分支和"只连"分支都不是它该走的——最后**一个分支都没走**（日志里两句话都没有）。
3. 连上后一帧都没发，② 的"防重入"判据 `_cvWaking && !_cvFrameSaid` 把用户**永久挡在外面**（到 45 秒窗结束），
   而且提示词是错的（"上一次发的帧还在等应答" —— 根本没发过）。

## 本轮改动（页面 only）

1. `camCvWake()`：点②时**登记意图** `window.__om3cvWantWake = true`，并把
   `__om3bleAutoWake = true / __om3bleConnOnly = false`（**即使** `camBleAuto` 因为"已经在连了"直接返回，意图也留住了）。
2. `camCvBle()`（①）：明确 `__om3bleConnOnly = true / __om3bleAutoWake = false / __om3cvWantWake = false`。
3. `tryConn()`：`window.__om3bleAutoWake = __om3cvWantWake ? true : !_cvConnectOnly`
   —— 用户点过②，连上就发；不再被"启动时那个链"的参数覆盖。
4. `svc` 的自动唤醒分支：跑完把 `__om3cvWantWake` 清掉（意图只用一次）。
5. `camCvWake()` 的防重入：**能自愈**
   - 蓝牙连上了却没发帧、也没有帧在等应答 → **当场补发**（而不是把用户挡住）；
   - 提示词按"帧发过没有"分开（发过才说"等应答"，没发过就说"还在连蓝牙/这就补发"）。
6. 蓝牙掉线（133/8/19/22）时：若观察窗还在等一帧没发出去的帧 → **收口**并提示"重新点②"，别让用户白等 45 秒。

## 显式声明

- 涉及：`app/base.html`（②/① 的意图登记 + 自愈 + 掉线收口）、`scripts/gen_r89.py`、`scripts/dv_r89.py`、
  本文档 + `HANDOVER.md` + `AGENTS.md` + `OPEN-ITEMS.md`（`OI-20` 复验口径）+ `TEST-camera.md`。
- 不涉及：**Java 不改**；订阅三连（r85）、应答解码（r86）、`0x1D01` 序列（r88）都不动；不加权限；**新增 id / data-tv：无**。
- 探针 `dv_r89` 复现的正是这份日志的顺序：**①（只连）→ 连失败 133 → ②（此时链还在跑）→ 重试连上 → svc**
  → 必须**发出两帧**（`0F 01 01 02` + `1D 01 01 02`）。

用法：python scripts/gen_r89.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r89：'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


@step('P1 ② 登记"连上要发帧"的意图（camBleAuto 可能直接 return）')
def p1_intent(html):
    old = """    camCvSay('② 蓝牙还没连 → 先连蓝牙（扫 → 连），连上后**自动发一次**「電源ON」（只发这一次）…');
    try{ camBleAuto('点②让相机开 Wi-Fi（传输）', false, {}); }"""
    new = """    camCvSay('② 蓝牙还没连 → 先连蓝牙（扫 → 连），连上后**自动发一次**（官方两条命令：電源ON + リモコンモード）…');
    /* STEPS_MARK：**先把意图登记下来**。真机 06:23 的教训：① 的"只连"链还在跑时点②，
       `camBleAuto` 会因为"已经在连了"直接 return → ② 的意图丢失 → 连上后一个分支都不走
       （日志里连"（自动链）蓝牙连上了…"都没有），用户白等 45 秒而且一帧都没发。 */
    window.__om3cvWantWake = true;
    window.__om3bleAutoWake = true; window.__om3bleConnOnly = false;
    try{ camBleAuto('点②让相机开 Wi-Fi（传输）', false, {}); }"""
    assert html.count(old) == 1, '② 的连蓝牙那段没找到'
    return html.replace(old, new, 1)


@step('P2 ① 明确"只连"（并撤掉②的意图）')
def p2_connonly(html):
    old = """    try{ camBleAuto('点①连接相机蓝牙', false, { connectOnly: true }); }"""
    new = """    /* STEPS_MARK：① 就是"只连"，明确登记（用户点① = 撤掉②的"连上发帧"意图） */
    window.__om3bleConnOnly = true; window.__om3bleAutoWake = false; window.__om3cvWantWake = false;
    try{ camBleAuto('点①连接相机蓝牙', false, { connectOnly: true }); }"""
    assert html.count(old) == 1, '① 那段没找到'
    return html.replace(old, new, 1)


@step('P3 重试不再用"启动时那个链"的参数盖掉用户的意图')
def p3_retry(html):
    old = """      window.__om3bleAutoWake = !_cvConnectOnly;   /* r81：手动控制台：只连模式不发唤醒帧 */"""
    new = """      window.__om3bleAutoWake = window.__om3cvWantWake ? true : !_cvConnectOnly;   /* r89：用户点过② → 连上就发 */"""
    assert html.count(old) == 1, 'tryConn 里那行没找到'
    return html.replace(old, new, 1)


@step('P4 svc 的自动唤醒分支：用完清掉意图')
def p4_clear(html):
    old = """          if(window.__om3bleAutoWake){
            window.__om3bleAutoWake = false;"""
    new = """          if(window.__om3bleAutoWake){
            window.__om3bleAutoWake = false;
            window.__om3cvWantWake = false;      /* r89：意图只用一次 */"""
    assert html.count(old) == 1, 'svc 自动唤醒分支没找到'
    return html.replace(old, new, 1)


@step('P5 ② 的防重入改成"能发就发"，提示词按"帧发过没有"分开')
def p5_selfheal(html):
    old = """    if(_cvWaking && !_cvFrameSaid){
      if(BLEON) camCvSay('② 上一次发的帧还在等相机应答（最多 5 秒）—— 等它跑完再点②', 'warn');
      else      camCvSay('② 正在连蓝牙（还没发帧）—— 连上就会自动发，稍等', 'warn');
      return;
    }"""
    new = """    if(_cvWaking && !_cvFrameSaid){
      /* STEPS_MARK：**能发就发**（真机 06:23：连上了、订阅也好了，却一帧都没发，
         而这里把人挡住 + 提示词还说"上一次发的帧还在等应答"——根本没发过）。 */
      if(!BLEON){ camCvSay('② 还在连蓝牙（还没发帧）—— 连上就会自动发，稍等', 'warn'); return; }
      if(_bleWakeRunning){ camCvSay('② 上一条命令还在等相机应答（最多 5 秒）—— 等它跑完再点②', 'warn'); return; }
      camCvSay('② 蓝牙已连但这一轮还没发帧 → 现在就补发（官方两条命令）…', 'warn');
      window.__om3cvWantWake = true;
      camCvWakeWatch();
      try{ bleAutoWake(); }catch(e0){ camCvSay('补发唤醒帧出错：' + e0.message, 'err'); }
      return;
    }"""
    assert html.count(old) == 1, '② 的防重入没找到'
    return html.replace(old, new, 1)


@step('P6 蓝牙掉线时：把"还在等一帧"的观察窗收口，别让用户白等')
def p6_lost(html):
    old = """      else if(ev === 'lost'){ BLEON = false; window.__om3bleConnOnly = false; bleRec('蓝牙断开：' + a + bleLostHint(a), 'warn'); bleRenderSvc(); }"""
    new = """      else if(ev === 'lost'){
        BLEON = false;
        /* STEPS_MARK：**掉线时别把"要发帧"的意图也清掉**（真机 06:23：133 一断，这里把 __om3bleConnOnly 清成 false，
           重试又按"启动时那个链"的参数写了 __om3bleAutoWake=false → svc 回调两个分支都不走 → 一帧都没发）。 */
        window.__om3bleConnOnly = false;
        bleRec('蓝牙断开：' + a + bleLostHint(a), 'warn');
        bleRenderSvc();
        /* 掉线时若"这一轮还没把帧发出去" → 收口观察窗，并告诉用户重来（别让他白等到 45 秒）。 */
        try{
          if(_cvWaking && !_cvFrameSaid){
            _cvWaking = false; _cvFrameSaid = false;
            if(_cvWakeT){ clearInterval(_cvWakeT); _cvWakeT = null; }
            camCvRender();
            camCvSay('② 这一轮蓝牙断了（命令还没发出去）—— 点①重连，连上后再点②（要发帧的意图我记着，连上就会发）', 'warn');
          }
        }catch(e9){ om3err(e9, "silent"); }
      }"""
    assert html.count(old) == 1, 'lost 分支没找到'
    return html.replace(old, new, 1)


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r89] 已经是目标状态 —— 不重复改。')
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
        print('[r89] ✗ %s —— **不写盘**' % e)
        return 1
    cur = cur.replace('STEPS_MARK', MARK)
    assert MARK in cur
    if cur.count('__om3cvWantWake') < 4:
        print('[r89] ✗ 结构自检：__om3cvWantWake 太少 —— **不写盘**')
        return 1
    dh = len(cur.encode('utf-8')) - len(html.encode('utf-8'))
    if not (0 < dh < 8000):
        print('[r89] ✗ 页面体积不对（%+d 字节）—— **不写盘**' % dh)
        return 1
    if '--check' in sys.argv:
        print('[r89] --check：%d 步都能跑通（未写盘）' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(cur)
    print('[r89] ✓ 页面 %d 步：② 的意图登记 + 连上没发帧就补发 + 掉线收口' % len(changed))
    print('[r89] 页面净增 %d 字节' % dh)
    return 0


if __name__ == '__main__':
    sys.exit(main())
