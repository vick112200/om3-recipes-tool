# -*- coding: utf-8 -*-
"""把联系表复制到工作目录 review_sheets/，并给"我的建议"画绿框（用户只看一眼点头即可）。

用法：python scripts/mark_sheet_r56.py
产出：D:\\workspace\\om3-handbook\\review_sheets\\
  0_先看这里.txt                 ← 一句话说明要用户做什么
  建筑几何.png / 建筑几何_我的建议.png
  婚礼聚会.png / 婚礼聚会_我的建议.png
  儿童亲子.png / 儿童亲子_我的建议.png
  其余（静物/日落/雾/逆光/花卉/食物）.png
"""
import io
import os
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')
from PIL import Image, ImageDraw, ImageFont      # noqa: E402

ROOT = r'D:\workspace\om3-handbook'
TMP = os.environ['TEMP']
OUT = os.path.join(ROOT, 'review_sheets')
COLS, TW, TH, TOP = 5, 300, 240, 38

SHEETS = [('arch', '建筑几何'), ('wedding', '婚礼聚会'), ('kids', '儿童亲子'),
          ('still', '静物极简'), ('sunset', '日落晚霞'), ('mist', '雾_阴天_雨天'),
          ('backlight', '逆光大光比'), ('flower', '花卉'), ('food', '食物咖啡')]

# 我建议的编号（1 起，对应表上的 #编号）
PICKS = {
    'arch': [2, 4, 7, 8, 10, 13, 14, 15, 18],
    'wedding': [1, 3, 8],          # 库里没有婚礼 → 退到"多人聚会"
    'kids': [],                    # 这张表里一个小孩都没有（唯一的小孩照在 Ilford HP5，见说明）
}

FONT = ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc', 15)


def main():
    os.makedirs(OUT, exist_ok=True)
    for key, cn in SHEETS:
        src = os.path.join(TMP, 'sheet_%s.png' % key)
        if not os.path.exists(src):
            print('  跳过（没生成）：', cn)
            continue
        dst = os.path.join(OUT, '%s.png' % cn)
        shutil.copy(src, dst)
        if key in PICKS and PICKS[key]:
            im = Image.open(dst).convert('RGB')
            d = ImageDraw.Draw(im)
            for n in PICKS[key]:
                k = n - 1
                x, y = (k % COLS) * TW + 3, (k // COLS) * TH + TOP + 3
                for w in range(4):                     # 粗绿框
                    d.rectangle([x - w, y - w, x + TW - 13 + w, y + TH - 46 + w], outline='#00d27a')
                d.text((x + 4, y - 20), '建议 #%d' % n, fill='#00d27a', font=FONT)
            p2 = os.path.join(OUT, '%s_我的建议.png' % cn)
            im.save(p2)
            print('  %-10s → %s（绿框 %d 个）' % (cn, os.path.basename(p2), len(PICKS[key])))
    tip = '''【看这里：我要你做什么】

一句话：打开同目录下的「建筑几何_我的建议.png」和「婚礼聚会_我的建议.png」，
        看绿框里那几张对不对 —— 对就回我一声"就这样"，不对就说"建筑第 2 个去掉"。

1) 建筑几何_我的建议.png —— 我挑了 9 张像建筑/几何线条的（绿框 + 标了"建议 #N"）。
   库里的作者样片就这些，剩下的都是泳池、吉他、恐龙玩具之类。

2) 婚礼聚会_我的建议.png —— 库里【一张婚礼都没有】，我退而求其次挑的是"多人聚会"那 3 张。
   你要是觉得不合适，就说"婚礼别挑"（那就保持现在的做法：明说本条没有实拍 + 用站点统一对比图）。

3) 儿童亲子 —— 这张表里【一个小孩都没有】。唯一的小孩照在配方 Ilford HP5（黑白，两个孩子+羊），
   但它不是"儿童亲子"这条场景的成员。要不要挂进去？回"挂"或"不挂"就行。

4) 静物 / 日落 / 雾 / 逆光 / 花卉 / 食物 —— 这些我用自动检测 + 画面条件判据搞定，不用你看。
   （图也在这个目录里，你想看可以看。）

回我一句就行，例如：`建筑就这样；婚礼别挑；儿童挂`
'''
    io.open(os.path.join(OUT, '0_先看这里.txt'), 'w', encoding='utf-8', newline='').write(tip)
    print('已写说明：review_sheets/0_先看这里.txt')


if __name__ == '__main__':
    main()
