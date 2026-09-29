# -*- coding: utf-8 -*-
"""第 63 轮验收：那句过时的 my-set 警告已改成如实说明。

要点：这条文案以前**说反了**（"接口全部 520/1001、读取并备份不会成功"），
会把人（包括 AI 自己）带偏 —— 第 61 轮就因此误判过"写配方不通"。所以探针要**钉住它别再回来**。

跑法：python scripts/dv_r63.py
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


src = io.open(os.path.join(ROOT, 'app', 'base.html'), encoding='utf-8').read()
OLD = io.open(os.path.join(ROOT, 'app', 'base.before_r63.html'), encoding='utf-8').read()
# 第 64 轮起页面又长了（BSSID）→ 「本轮只多了多少字节」这条要拿**第 63 轮当时改完的那一版**
# 做对照（= base.before_r64.html，也就是 v3.17 的源码），否则量的是"63 轮 + 后面所有轮"。
# 阈值仍是 400 字节，只是把被测量对象改成"第 63 轮那一次改动"——不是放松。
AFTER63 = os.path.join(ROOT, 'app', 'base.before_r64.html')
NEW63 = io.open(AFTER63, encoding='utf-8').read() if os.path.exists(AFTER63) else src

print('=== 第 63 轮：过时警告已改 ===')
A('my-set 接口全部返回 520/1001' not in src, '原文"my-set 接口全部返回 520/1001"一个字符都不剩')
A('「读取并备份」在本机型上不会成功' not in src, '原文"读取并备份…不会成功"也不剩')
A('相机固件不认' in src and '不影响读取 / 备份 / 写入' in src, '新文案在位（如实说明）')
A(src.count('get_mysetname?mode=current') >= 1, '新文案里点名了那一条不支持的查询')
A('color:#d8b45a">⚠ 实测' not in src, '不再用"⚠ 实测"的警告样式')
A('<!-- r63：' in src, '留了 <!-- r63 --> 溯源注释（可回查）')

print('=== 上下文没被碰坏 ===')
A('② 安全备份（自动安全网）' in src, '还在「② 安全备份」卡里')
for k in ('camBackup', 'camDl', 'camRestore', 'camBakInfo', 'camOut2'):
    A('id="%s"' % k in src, '备份卡的 id 还在：%s' % k)
A(len(NEW63) - len(OLD) < 400,
  '第 63 轮那一次改动只多了 %d 字节（纯文案替换）' % (len(NEW63.encode()) - len(OLD.encode())))
A(len(src) > len(OLD), '当前页面（含后面几轮的改动）比第 63 轮改前更长：%d 字节'
  % (len(src.encode()) - len(OLD.encode())))

print('=== 证据文件仍能自证 ===')
ev = io.open(os.path.join(ROOT, 'SPEC-round28.md'), encoding='utf-8').read()
A('与写入无关' in ev, 'SPEC-round28.md 里仍写着那条 520「与写入无关」')
hd = io.open(os.path.join(ROOT, 'HANDOVER.md'), encoding='utf-8').read()
A('别再当 bug' in hd, 'HANDOVER.md 里仍有"属正常，别再当 bug"的记录')

print()
print('第 63 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
