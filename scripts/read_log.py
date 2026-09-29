# -*- coding: utf-8 -*-
"""日志分诊器：读**相机日志文件**（就是 App 里「下载日志文件」导出的那个 .txt，
或 ☰ → 测试页 →「复制全部日志」粘出来的文本），自动给一份排查摘要。

用法：
    python scripts/read_log.py                      # 读 logs/ 里最新的 .txt
    python scripts/read_log.py logs/xxx.txt         # 读指定文件
    python scripts/read_log.py -                    # 从标准输入读（粘贴用）

它会打印：
  · 日志头（App 版本 / 设备 / 权限 / 记住的相机 / 连接态）—— 这正是 r74 加进去的那一段
  · 走过的"步骤链"（①检测 → ②备份 → ③写入）
  · 见过的 HTTP 状态码（含出现次数）
  · **第一个失败点** + 它前面 5 行上下文（排查主要看这个）
  · 按规则给的"下一步做什么"
  · 安全检查：万一日志里出现了密码样式的内容，会大声报警（我们的规矩是永不写密码）
"""
import glob
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGDIR = os.path.join(ROOT, 'logs')

HEAD_KEYS = ['App：', '设备/系统：', '屏幕：', '权限：', '记住的相机：', '当前连接：', '蓝牙口令：', '生成时间：', '页面：']
BAD = re.compile(r'(失败|不通|超时|timeout|denied|need_perm|err[:：]|错误|连不上|no_cam_ap|not found|520|500|403|401)')
RULES = [
    (r'"nearby":false', '安卓 13+ 少了「附近的设备」权限 → 到 设置→应用→权限 里给上，再点「连接相机」'),
    (r'"fine":false', '安卓 12 及以下少了「位置信息」权限 → 给上再连（连 Wi-Fi 热点必须要它）'),
    (r'err:wifi_off|手机的 Wi-Fi 开关是关的', '手机 Wi-Fi 被关了 → 打开 Wi-Fi 再点「连接相机」'),
    (r'err:|扫不到 Wi-Fi', '扫不到 Wi-Fi：多半是权限（见上）或系统限流 → 也可以直接「手动填 SSID / 密码」'),
    (r'no_cam_ap|没扫到任何 Wi-Fi|像相机的有 0 个', '手机没看到相机热点 → 相机那边把 Wi-Fi 打到「Wi-Fi 传输状态」；'
                                                '或者用「用蓝牙唤醒相机」先把相机叫醒'),
    (r'need_perm:android.permission.CAMERA|camera.*false', '扫二维码要相机权限 → 到 设置→应用→权限 给「相机」'),
    (r'get_mysetname.*520|HTTP 520', 'HTTP 520 若只出现在 get_mysetname 上，是**已知的相机不支持的查询**，不影响读写（见规格）'),
    (r'30 秒还没连上|连不上', '超过 30 秒没连上 → 相机热点可能没起来 / 手机被"智能网络切换"抢走连接 → 关掉它再试'),
    (r'等了 \d+ 秒没看到相机热点', '⚠ 这是 v3.33 的**假失败**：① 相机不回 ACK 本来就不代表没开；'
                                  '② 老的原生扫描是"startScan 后立刻读缓存"，永远慢一拍。'
                                  'v3.34 已修（等新结果的扫描 + 45 秒窗口 + 到点给"直接点③"）→ 装新版再试一次'),
    (r"没等到系统给新结果|扫描没拿到新结果：系统不让 App 触发扫描|startScan_false",
     '⚠ 安卓 13+ 的限额：`startScan()` 直接返回 false（**不是相机的问题**）。'
     'v3.35 起：会隔 1.2 秒再试一次，并在日志里写清 why（startScan_false / no_broadcast / register_failed / wifi_off）'),
    (r"扫描没拿到新结果", '扫描没拿到新结果 ≠ 相机没开（见上）→ 判定请**直接点③**（按记住的 SSID+BSSID 连，不依赖扫描）'),
    (r'【②之后 · 人看到的】相机屏幕\*\*亮了',  # 人看到的判据（v3.35 起）
     '✅ 你亲眼看到相机进了传输态 → 相机确实开了：**直接点③**连它（这台机器扫描拿不到新结果，别等扫描）'),
    (r'【②之后 · 人看到的】相机\*\*没反应',
     '❌ 相机没执行开机帧 → 查：相机是否**开机**、MENU → Wi-Fi/蓝牙 里蓝牙是否「开」、'
     '相机是不是已经连着手机/别的设备（一条链占着）；也可点测试页的「蓝牙口令」那条把口令填上再点②'),
    (r'BLE|蓝牙', '日志里有蓝牙那条链 → **相机不回「電源ON」的应答是正常的**（真机结论）：'
                  '看后面有没有「相机热点起来了 / 相机 Wi-Fi 起来了」；没有就看相机屏幕亮没亮，'
                  '并直接点③（用记住的 SSID+BSSID 连，不依赖扫描）'),
]


def read_text(arg):
    if arg == '-':
        return sys.stdin.read()
    if arg:
        return io.open(arg, encoding='utf-8', errors='ignore').read()
    files = sorted(glob.glob(os.path.join(LOGDIR, '*.txt')), key=os.path.getmtime, reverse=True)
    if not files:
        print('logs/ 里没有 .txt。把手机导出的「OM3-导入相机-日志-*.txt」拷进 %s 再跑一次；' % LOGDIR)
        print('或者：python scripts/read_log.py "把日志粘贴到一个文件里.txt"')
        return None
    print('（自动选了最新的一份：%s）' % os.path.basename(files[0]))
    return io.open(files[0], encoding='utf-8', errors='ignore').read()


def main():
    txt = read_text(sys.argv[1] if len(sys.argv) > 1 else None)
    if txt is None:
        return 1
    lines = txt.split('\n')

    print('=== ① 日志头（一眼看环境） ===')
    head_n = 0
    for l in lines[:14]:
        if any(k in l for k in HEAD_KEYS):
            print('   ' + l.strip())
            head_n += 1
    if not head_n:
        print('   （没有日志头 —— 这是旧版本导出的日志；新版本 v3.26+ 才有）')

    print()
    print('=== ② 走过的步骤链 ===')
    tags = []
    for l in lines:
        m = re.match(r'\[[^\]]+\]\s*(①检测|②备份|③写入)\s*(.*)', l)
        if m:
            tag, msg = m.group(1), m.group(2).strip()
            if not tags or tags[-1][0] != tag:
                tags.append([tag, 0, msg])
            tags[-1][1] += 1
            tags[-1][2] = msg
    if tags:
        for tag, n, last in tags:
            print('   %s（%d 行）最后一句：%s' % (tag, n, last[:90]))
    else:
        print('   （没识别到步骤行；日志可能不完整）')

    print()
    print('=== ③ 见过的 HTTP 状态码 ===')
    codes = {}
    for m in re.finditer(r'HTTP\s*(\d{3})|状态\s*[:：]?\s*(\d{3})', txt):
        c = m.group(1) or m.group(2)
        codes[c] = codes.get(c, 0) + 1
    print('   ' + ('、'.join('%s×%d' % (k, v) for k, v in sorted(codes.items())) if codes else '（日志里没有 HTTP 状态码）'))

    print()
    print('=== ④ 第一个失败点（排查主要看这个） ===')
    idx = next((i for i, l in enumerate(lines) if BAD.search(l)), None)
    if idx is None:
        print('   ✅ 没找到失败/报错字样 —— 如果功能还是不对，把整份日志发我')
    else:
        for l in lines[max(0, idx - 5):idx + 3]:
            mark = '>>' if l == lines[idx] else '  '
            print('   %s %s' % (mark, l.strip()[:150]))

    print()
    print('=== ⑤ 下一步做什么 ===')
    hit = False
    for pat, tip in RULES:
        if re.search(pat, txt, re.I):
            print('   · ' + tip)
            hit = True
    if not hit:
        print('   · 规则库里没有明显命中：先看 ④ 那几行；还不行就把整份日志贴给我')

    print()
    print('=== ⑥ 安全检查：日志里有没有不该出现的东西 ===')
    bad = [l for l in lines if re.search(r'(密码|pass|pwd)\s*[:：=]\s*\S', l) and '不写进日志' not in l]
    if bad:
        print('   ⚠⚠ 发现疑似密码！这违反约定，请把这行发我（说明哪里漏了）')
        for l in bad[:3]:
            print('      ' + l.strip()[:120])
    else:
        print('   ✅ 没有密码样式的内容（密码永不进日志这条守住了）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
