# -*- coding: utf-8 -*-
"""全面自检：扫描这个单文件 app 常见的几类缺陷"""
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
h = open(P, encoding='utf-8').read()

print('文件大小: %.0f KB' % (len(h) / 1024))
print()

# 1) 重复 id
ids = re.findall(r'\sid="([^"]+)"', h)
dup = [k for k, v in Counter(ids).items() if v > 1]
print('1) 重复 id:', dup if dup else '无 ✓')

# 2) JS 里 getElementById 的悬空引用
refs = set(re.findall(r"getElementById\(\s*'([^']+)'\s*\)", h))
have = set(ids)
miss = sorted(r for r in refs if r not in have)
print('2) getElementById 引用了但不存在的 id:', miss if miss else '无 ✓')

# 3) 原生弹窗残留
print('3) 原生 confirm/prompt/alert:', len(re.findall(r'\bconfirm\(', h)), '/',
      len(re.findall(r'\bprompt\(', h)), '/', len(re.findall(r'\balert\(', h)), '（都应为 0）')

# 4) 关键元素是否放在正确的页签里
panes = {}
for p in ['paneA', 'paneB', 'paneC', 'paneD', 'paneE']:
    panes[p] = h.find('id="%s"' % p)
order = sorted([(v, k) for k, v in panes.items() if v > 0])
def owner(idx):
    for i in range(len(order)):
        a = order[i][0]
        b = order[i + 1][0] if i + 1 < len(order) else len(h)
        if a < idx < b:
            return order[i][1]
    return 'body/其它'
for key in ['id="toc2"', 'id="bleCard"', 'id="barABC"', 'id="barD"', 'id="gStatusBar"', 'id="taskMask"', 'id="omask"']:
    i = h.find(key)
    print('4) %-16s → %s' % (key, owner(i) if i > 0 else '不存在 ✗'))

# 5) .hide 优先级风险：容器基础样式的 display 是否会盖过 .hide
bad = []
for m in re.finditer(r'\.([a-zA-Z][\w-]*)\{([^}]*display:\s*(flex|block|grid)[^}]*)\}', h):
    cls, body = m.group(1), m.group(2)
    if '!important' in body:
        continue
    if ('.%s.hide' % cls) in h or ('%s hide' % cls) in h or ('"%s hide"' % cls) in h or ("'%s hide'" % cls) in h or ('class="%s hide' % cls) in h:
        bad.append(cls)
print('5) 可能被 display 盖过 .hide 的类:', bad if bad else '无 ✓')

# 6) fixed 定位元素（遮罩/浮层，容易挡点击）
fx = re.findall(r'#?\.?([\w-]+)\{[^}]*position:\s*fixed[^}]*\}', h)
print('6) fixed 定位的类:', sorted(set(fx))[:12])

# 7) 页签与底栏定义
print('7) 顶部模块按钮:', re.findall(r'<button[^>]*data-p="([A-Z])"[^>]*>([^<]{2,8})</button>', h))
print('7) 底部三切换:', re.findall(r'#barABC|data-p="([ABC])"', h)[:6])
print('7) barD 四切换:', re.findall(r'data-dstep="([0-9])"[^>]*>([^<]{1,8})', h))

# 8) 功能点清单（存在性）
feats = {
    '写入配方(writeRawKV)': 'function writeRawKV',
    '读取整份(readMySet)': 'function readMySet',
    '预览(previewSlot)': 'function previewSlot',
    '方案库(setsAll)': 'function setsAll',
    '档位管理(tiersAll)': 'function tiersAll',
    '导出 .oes(oesBuild)': 'function oesBuild',
    '导入(om3Parse/oes)': 'function oesParse',
    '系统分享(shareText)': 'shareText',
    '文件选择(onShowFileChooser)': 'onShowFileChooser',
    '任务弹窗(runTask)': 'async function runTask',
    '自绘弹窗(om3Ask)': 'function om3Ask',
    '扫码(jsQR)': 'window.jsQR',
    '原生扫码(BarcodeDetector)': 'BarcodeDetector',
    '悬浮状态球(gStatusBar)': 'gStatusBar',
    '相机在线探测': '检测不到相机',
    '安全备份回滚': 'restoreBackup',
    '导入记录': 'function renderRecords',
    'BLE 扫描': 'bleScanStart',
}
print()
print('8) 功能点检查（应全部 ✓）:')
for k, v in feats.items():
    print('   %-26s %s' % (k, '✓' if v in h else '✗ 缺失'))
