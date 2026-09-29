# -*- coding: utf-8 -*-
"""第 74 轮：把「扫码」放回来（往后放，不做第一入口）+ 修推演发现的两个连接问题 + 日志可直接给我
（见 SPEC-round74.md）。

需求方 2026-09-28：
  「手机现在扫码连接好像被屏蔽了，之前说过把扫码往后放了，你要是做好了我们可以试试，
    你还是自己推演一遍吧。而且我们之前不是说需要尝试连接相机有个需要我发给你日志的吗，
    你看看这个任务是怎么弄」

推演（`scripts/sim_connect.py`，假原生桥 + 时间线）拿到三条结论：
 ① **扫码是被"藏"了**，不是坏了：第 49 轮给三个扫码入口加了 `.hid49{display:none!important}`
    （注释写着"用户 2026-09-25：先把扫码隐藏一下…要再开就把 .hid49 去掉"）。
    更糟的是**文案还在让用户去点它**（"点下面「扫二维码（第一次）」最稳"）→ 指向一个看不见的按钮。
 ② **点「连接相机」会先白等 10 秒**：即使蓝牙这条路根本跑不起来（没有原生蓝牙接口 / 已停用），
    也会先进"等蓝牙链"的循环（实测日志："没有蓝牙接口 → 跳过蓝牙唤醒"，然后还是等满 10 秒）。
 ③ **等相机热点时每 500ms 扫一次 Wi-Fi**（`camHotspotVisible()` → `wifiScanList()`），
    10 秒里扫 20 次：安卓对 Wi-Fi 扫描有节流、结果还会滞后 → 费电 + 可能误判"热点没起来"。

本轮改 4 处 + 1 套"日志给我"的落地：
  ① 扫码入口放回来（`#camGateScan` 降级成次要样式、排在「连接相机」之后；`#camScan`/`#camScanHelp` 也放回）
  ② 蓝牙跑不起来就别等（直接进 Wi-Fi）
  ③ 热点探测节流（真扫最多 5 秒一次，其余只读 wifiState）
  ④ 导出日志加"头"：版本/设备/屏幕/权限/记住的相机（**不含密码**）/连接态/蓝牙口令是否已存
  ⑤ `logs/` 目录 + `scripts/read_log.py`：把日志文件放进 logs/ 我直接读并出分诊结论

规矩：幂等（标记 `r74：扫码放回 + 日志头`）+ 每步必须真的改到东西 + 老 id 一个不少 + 本轮不新增 id。

用法：python scripts/gen_r74.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r74：扫码放回 + 日志头'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


# ---------------------------------------------------------------- ① 扫码入口放回来（往后放）
@step('① 扫码入口放回来：#camGateScan 变次要样式 + 改文案；#camScan/#camScanHelp 去掉 hid49')
def s_scan_back(html):
    o1 = ('<button type="button" class="big hid49" id="camGateScan">扫二维码（第一次）</button>\n'
          '    <button type="button" class="big" id="camGateConn">连接相机</button>')
    assert html.count(o1) == 1, 'camGateScan/camGateConn 那两行没找到'
    n1 = ('<!-- r74：扫码放回来，但**往后放**：排在「连接相机」之后、样式降一级（.gho 灰底）。\n'
          '       第 49 轮是把它整个藏起来（.hid49），而下面的提示文案还在让用户去点它（指向一个看不见的按钮）。\n'
          '       要再藏回去：给这三个按钮加回 class="hid49" 即可（.hid49 那条 CSS 保留着）。 -->\n'
          '    <button type="button" class="big" id="camGateConn">连接相机</button>\n'
          '    <button type="button" class="big gho" id="camGateScan">扫码连接（忘了密码时用）</button>')
    html = html.replace(o1, n1, 1)
    o2 = '<button type="button" id="camScan" class="camprimary hid49">扫二维码</button>'
    assert html.count(o2) == 1, 'camScan 那条没找到'
    html = html.replace(o2, '<button type="button" id="camScan" class="camprimary">扫二维码</button>', 1)
    o3 = '<button type="button" id="camScanHelp" class="hid49">看不到二维码？手动填</button>'
    assert html.count(o3) == 1, 'camScanHelp 那条没找到'
    html = html.replace(o3, '<button type="button" id="camScanHelp">看不到二维码？手动填</button>', 1)
    return html


@step('① 提示文案里的旧按钮名「扫二维码（第一次）」统一成新名字（4 处）')
def s_msg_text(html):
    # 按钮改名了（扫码连接（忘了密码时用）），但提示文案还在叫旧名 —— 文案和按钮必须对得上
    n = html.count('扫二维码（第一次）')
    assert n >= 4, '旧按钮名只找到 %d 处（应 ≥4）' % n
    html = html.replace('「扫二维码（第一次）」', '「扫码连接（忘了密码时用）」')
    assert '扫二维码（第一次）' not in html, '还有残留的旧按钮名'
    return html


@step('① 更新 .hid49 的注释：写清"现在=开（显示）"和怎么再藏')
def s_hid49_note(html):
    old = ('/* r49：先把扫码藏起来（用户 2026-09-25：「先把扫码隐藏一下」）。\n'
           '   元素和代码都留着（要再开就把 .hid49 去掉），但界面上不给入口。 */\n'
           '.hid49{display:none !important}')
    assert html.count(old) == 1, '.hid49 那段注释没找到'
    new = ('/* .hid49：**隐藏入口的开关**。\n'
           '   r49 曾用它把三个扫码入口全藏起来（用户 2026-09-25：「先把扫码隐藏一下」）；\n'
           '   **r74 起改为"放回来但往后放"**（见 SPEC-round74.md）：\n'
           '     · 现在 **没有一个按钮带 .hid49**（扫码可用，但排在「连接相机」后面、样式次要）\n'
           '     · 想再彻底藏起来：给 #camGateScan / #camScan / #camScanHelp 加回 class="hid49" */\n'
           '.hid49{display:none !important}')
    return html.replace(old, new, 1)


# ---------------------------------------------------------------- ② 蓝牙跑不起来就别白等
@step('② 蓝牙这条路跑不起来（没接口/已停用）→ 不等那 10 秒，直接进 Wi-Fi')
def s_no_ble_wait(html):
    old = ("    step('第 1/3 步：确认蓝牙那条链（它负责让相机开 Wi-Fi）…');\n"
           "    if(!_bleAutoDone && !_bleAutoStop && !camHotspotVisible()){\n"
           "      try{ camBleAuto('点「连接相机」'); }catch(e){ om3err(e, \"ble-chain\"); }\n"
           "      var waited = 0;")
    assert html.count(old) == 1, 'camWifiChain 的蓝牙等待段没找到'
    new = ("    step('第 1/3 步：确认蓝牙那条链（它负责让相机开 Wi-Fi）…');\n"
           "    /* r74：先判断\"蓝牙这条路到底跑不跑得起来\"——\n"
           "       以前不管能不能跑，都会进\"等蓝牙链\"的循环、干等满 10 秒（实测日志：\n"
           "       先打印\"这个版本没有蓝牙接口 → 跳过蓝牙唤醒\"，然后又等满 10 秒才进 Wi-Fi，用户看着像卡住）。\n"
           "       判据：没有原生蓝牙接口 / 用户点过「停止自动连蓝牙」→ 直接进 Wi-Fi。 */\n"
           "    var blePossible = (function(){\n"
           "      try{\n"
           "        var N = window.OM3Native;\n"
           "        if(!N) return false;\n"
           "        if(!N.bleScan && !N.bleConnect && !N.bleCmd && !N.bleWrite) return false;   /* 这个版本没蓝牙接口 */\n"
           "        if(_bleAutoStop) return false;                                              /* 用户已停用自动连蓝牙 */\n"
           "        return true;\n"
           "      }catch(e){ return false; }\n"
           "    })();\n"
           "    if(!_bleAutoDone && !_bleAutoStop && !camHotspotVisible()){\n"
           "      try{ camBleAuto('点「连接相机」'); }catch(e){ om3err(e, \"ble-chain\"); }\n"
           "      if(!blePossible){\n"
           "        step('蓝牙这条路现在跑不起来（没有蓝牙接口 / 已停用）→ 不等它了，直接进 Wi-Fi', 'warn');\n"
           "        wifi(); return;\n"
           "      }\n"
           "      var waited = 0;")
    return html.replace(old, new, 1)


# ---------------------------------------------------------------- ③ 热点探测节流
@step('③ camHotspotVisible() 节流：真扫 Wi-Fi 最多 5 秒一次，其余只读 wifiState')
def s_throttle(html):
    old = ("  function camHotspotVisible(){\n"
           "    try{\n"
           "      var N = window.OM3Native;\n"
           "      if(!N) return false;\n"
           "      if(N.wifiState){\n"
           "        var o = JSON.parse(String(N.wifiState() || '{}') || '{}');\n"
           "        if(o && o.ssid && camLookLikeCamera(String(o.ssid))) return true;\n"
           "      }\n"
           "      if(N.wifiScanList){\n"
           "        var raw = String(N.wifiScanList() || '');\n"
           "        if(raw.charAt(0) === '['){\n"
           "          var L = JSON.parse(raw) || [];\n"
           "          for(var i = 0; i < L.length; i++){\n"
           "            if(L[i] && (L[i].cam || camLookLikeCamera(String(L[i].ssid || '')))) return true;\n"
           "          }\n"
           "        }\n"
           "      }\n"
           "    }catch(e){ om3err(e, \"silent\"); }\n"
           "    return false;\n"
           "  }")
    assert html.count(old) == 1, 'camHotspotVisible 没找到'
    new = ("  /* r74：**别每 500ms 扫一次 Wi-Fi**。\n"
           "     wifiScanList() = 触发一次系统 Wi-Fi 扫描（安卓对扫描有节流、结果还会滞后）。\n"
           "     以前\"连接相机\"按钮的等待循环每 500ms 调一次 camHotspotVisible() → 10 秒里扫约 20 次：\n"
           "     费电，而且很可能因为结果滞后误判\"热点还没起来\"。\n"
           "     现在：**真扫最多 5 秒一次**，中间那些轮询只读 wifiState()（读当前挂的 SSID，几乎免费）；\n"
           "     扫到的结论缓存起来，下次扫之前先用缓存。 */\n"
           "  var _hsAt = 0, _hsVal = false, _hsSkipped = 0, _hsForce = false;\n"
           "  window.__om3hotspotForce = function(){ _hsForce = true; };      /* 需要立刻重扫时用（比如刚唤醒过相机） */\n"
           "  function camHotspotVisible(){\n"
           "    try{\n"
           "      var N = window.OM3Native;\n"
           "      if(!N) return false;\n"
           "      if(N.wifiState){\n"
           "        var o = JSON.parse(String(N.wifiState() || '{}') || '{}');\n"
           "        if(o && o.ssid && camLookLikeCamera(String(o.ssid))){ _hsVal = true; return true; }\n"
           "      }\n"
           "      if(N.wifiScanList){\n"
           "        var now = Date.now();\n"
           "        if(_hsForce || (now - _hsAt) >= 5000){\n"
           "          _hsForce = false; _hsAt = now;\n"
           "          var raw = String(N.wifiScanList() || '');\n"
           "          var found = false;\n"
           "          if(raw.charAt(0) === '['){\n"
           "            var L = JSON.parse(raw) || [];\n"
           "            for(var i = 0; i < L.length; i++){\n"
           "              if(L[i] && (L[i].cam || camLookLikeCamera(String(L[i].ssid || '')))){ found = true; break; }\n"
           "            }\n"
           "          }\n"
           "          _hsVal = found;\n"
           "          try{ if(_hsSkipped){ log('[热点探测] 之前 ' + _hsSkipped + ' 次轮询没重复扫 Wi-Fi（节流 5 秒）', 'ok'); _hsSkipped = 0; } }catch(e2){}\n"
           "          return found;\n"
           "        }\n"
           "        _hsSkipped++;\n"
           "      }\n"
           "    }catch(e){ om3err(e, \"silent\"); }\n"
           "    return _hsVal;\n"
           "  }")
    return html.replace(old, new, 1)


# ---------------------------------------------------------------- ④ 日志头
@step('④ 导出日志加"头"：版本/设备/屏幕/权限/记住的相机（不含密码）/连接态/蓝牙口令')
def s_log_header(html):
    old = ("  function logText(){\n"
           "    return 'OM-3 导入相机 日志\\n生成时间：' + new Date().toLocaleString() + '\\n' +\n"
           "           '页面：' + (location.href || '') + '\\n\\n' + ALLLOG.join('\\n') + '\\n';\n"
           "  }")
    assert html.count(old) == 1, 'logText() 没找到'
    new = ("  /* r74：导出的日志带一个**自足的『头』** —— 我要排查时不用再问你\"什么版本/什么手机/给没给权限\"。\n"
           "     ⚠ 绝不写相机密码（也不写蓝牙口令本身，只写\"有没有存\"）。 */\n"
           "  function logText(){\n"
           "    var ver = '';\n"
           "    try{ var av = document.querySelector('.appver'); ver = av ? String(av.textContent || '').replace(/\\s+/g, ' ').trim() : ''; }catch(e0){}\n"
           "    var ps = '(没有原生桥)';\n"
           "    try{ if(window.OM3Native && window.OM3Native.permState) ps = String(window.OM3Native.permState()); }catch(e1){ ps = '(读不到)'; }\n"
           "    var st = '';\n"
           "    try{ if(window.OM3Native && window.OM3Native.cameraState) st = String(window.OM3Native.cameraState()); }catch(e2){}\n"
           "    var sv = {};\n"
           "    try{ sv = camSaved() || {}; }catch(e3){}\n"
           "    var bt = '';\n"
           "    try{ bt = (typeof blePassGet === 'function' && blePassGet()) ? '已存（口令本身不写进日志）' : '没存'; }catch(e4){}\n"
           "    var mem = sv.ssid\n"
           "      ? ('SSID=' + sv.ssid + (sv.bssid ? (' BSSID=' + sv.bssid) : '') +\n"
           "         (sv.model ? (' 型号=' + sv.model) : '') + (sv.serial ? (' 序列号=' + sv.serial) : '') + '（密码不写进日志）')\n"
           "      : '（还没记住任何相机）';\n"
           "    return 'OM-3 导入相机 日志\\n' +\n"
           "           '生成时间：' + new Date().toLocaleString() + '\\n' +\n"
           "           'App：' + (ver || '(读不到)') + '\\n' +\n"
           "           '设备/系统：' + (navigator.userAgent || '') + '\\n' +\n"
           "           '屏幕：' + window.innerWidth + '×' + window.innerHeight + ' @' + (window.devicePixelRatio || 1) + 'x\\n' +\n"
           "           '权限：' + ps + '\\n' +\n"
           "           '记住的相机：' + mem + '\\n' +\n"
           "           '当前连接：' + (st || '(读不到)') + '\\n' +\n"
           "           '蓝牙口令：' + bt + '\\n' +\n"
           "           '页面：' + (location.href || '') + '\\n\\n' + ALLLOG.join('\\n') + '\\n';\n"
           "  }\n"
           "  window.__om3logText = logText;   /* r74：测试页 / 探针要取这份日志（含头）时用；也是\"日志头\"这条的锚点 */")
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
    html = html.replace('  var _hsAt = 0, _hsVal = false, _hsSkipped = 0, _hsForce = false;',
                        '  var _hsAt = 0, _hsVal = false, _hsSkipped = 0, _hsForce = false;   /* %s */' % MARK, 1)
    assert MARK in html, '标记没插进去'
    return html, changed


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r74] 已经是目标状态（页面里有 "%s"）—— 不重复改。' % MARK)
        return 0
    try:
        new, changed = run(html)
    except AssertionError as e:
        print('[r74] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r74] --check：%d 步都能跑通（未写盘）：' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(new)
    print('[r74] ✓ 已改 %d 步：扫码放回（往后放）/ 蓝牙跑不起来不等 10 秒 / 热点探测节流 5 秒 / 日志带头'
          % len(changed))
    before = io.open(os.path.join(ROOT, 'app', 'base.before_r74.html'), encoding='utf-8').read()
    print('[r74] 页面净增 %d 字节' % (len(new.encode('utf-8')) - len(before.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
