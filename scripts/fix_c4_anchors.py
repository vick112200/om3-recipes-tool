# -*- coding: utf-8 -*-
"""把 patch_c4.py 里两个过时的锚点按 base.html 原文精确重写。"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
p = r'C:\Users\82302\AppData\Local\Temp\patch_c4.py'
s = open(p, encoding='utf-8').read()

TAIL = ("old_tail = ('<br><b>槽 1、槽 2 的原配方是 5300K A0 G0，不是 Auto。</b>挂在 Auto 上它们不算原味还原——'\n"
        "            '想要那一口的原味，进菜单把色温拨到 <b>5300K</b>（WB 按钮 → 色温 K → 前拨盘），'\n"
        "            '拍完记得拨回 Auto。<b>这就是\"通用夜景\"和\"原配方还原\"之间的那个开关。</b>')\n")
EXW = ("old_exwhy = ('<b>为什么第三个槽给 City Look：</b>它只动色彩通道，色调曲线三格全中性、没有曝光补偿，'\n"
       "             '白平衡本来就是 A0 G0 无偏移，挂在 Auto 上是零代价；黄推高、青一刀砍光、红收回 −4，'\n"
       "             '做出人造的、接近霓虹的都会暖黄。<br>'\n"
       "             '<b>为什么第四个槽给 Q116：</b>上一版它在 C5，这一版 C5 改成胶片档，它得另找地方。'\n"
       "             '它不是胶片还原，放进来纯粹是<b>影调对口</b>：Q116 暗部提 3 格、高光狠压 5 格、对比 −8，'\n"
       "             '是全场压缩动态范围最狠的一格之一——夜景要的正是这个：灯泡和招牌不会爆，暗部也不会糊成死黑。'\n"
       "             '它的原配方本来就是 Auto A0 G0，自然融入。')\n")

s, n1 = re.subn(r"old_tail = \(.*?\n(?=assert h\.count\(old_tail\))", TAIL, s, flags=re.S)
assert n1 == 1, ('tail', n1)
s, n2 = re.subn(r"old_exwhy = \(.*?\n(?=assert h\.count\(old_exwhy\))", EXW, s, flags=re.S)
assert n2 == 1, ('exwhy', n2)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('两个锚点已按原文精确重写')
