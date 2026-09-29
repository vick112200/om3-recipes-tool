# -*- coding: utf-8 -*-
"""第 39 轮（B1）：给图库里每张照片打**画面自动归类**标签，供「按场景挑图」用。

用户选的方案：自动按画面归类（并明确标注"可能看错"）。用 PIL 看几个便宜但有效的特征：
  · 肤色占比             → 人像（人在画面里、且脸/皮肤占一定比例）
  · 暗部占比 + 亮度分布   → 夜景
  · 绿色占比             → 绿意 / 森林 / 秋叶
  · 蓝青占比（上部偏多）  → 天空水面
  · 品红/粉红占比         → 花卉 / 晚霞
  · 高亮低饱和占比        → 雪 / 高调
另外：6 个**统一场景**的图自带题材标签（marathon=人群、redbud=花卉、rosslyn-dusk=夜景、
moss=绿意暗部、misty-mountains=雾与远景、peace-memorial=中性白），直接按文件名给。

产出（嵌进 base.html，markers 幂等）：
  window.__OM3PHOTOTAGS__ = { "文件名": ["人像","绿意", …], … }
  window.__OM3PHOTOS__    = { "配方 slug": ["该配方的所有图文件名", …], … }
"""
import io, json, os, sys
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\workspace\om3-handbook'
IMG = BASE + r'\apk\assets\images'
P = BASE + r'\app\base.html'
B, E = '<!-- OMPTAGS-BEGIN -->', '<!-- OMPTAGS-END -->'
SCENE_TAG = {'marathon': '人群', 'redbud': '花卉', 'rosslyn-dusk': '夜景',
             'moss': '绿意', 'misty-mountains': '雾', 'peace-memorial': '中性白'}
# 第 54 轮：主图表 {slug: 主图文件名}，由 gen_r54.py 在调用 main() 前注入（默认空 = 退回旧行为）
HERO = {}
# 第 56 轮：YuNet 人脸检测结果（face_r56.py 产出）。缺文件 = 不加人脸类标签（退回旧行为）
FACES = {}
FACES_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_r56_faces.json')
BIG_RATIO = 0.025      # 人脸占画面 ≥2.5% 算「人像特写」（与 face_r56.py 同一口径）


ANIMALS = {}          # 手工例外（猫/狗…人脸检测会把它们当人）——见 scripts/_r56_animals.json
ANIMALS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_r56_animals.json')


def face_tags(fl):
    """人脸类标签：人像特写 / 人脸 / 人群 —— 只有真检出脸、且不是动物才给。"""
    if fl in ANIMALS:
        return ['动物']
    v = FACES.get(fl)
    if not v:
        return []
    n, big, mx = v.get('n', 0), v.get('big', 0), v.get('max', 0)
    out = []
    if big >= 1 or (n >= 1 and mx >= BIG_RATIO):
        out.append('人像特写')
    if n >= 1:
        out.append('人脸')
    if n >= 3 and mx < BIG_RATIO:
        out.append('人群')
    return out


def tags_of(path):
    im = Image.open(path).convert('RGB').resize((160, 120))
    px = list(im.getdata())
    n = len(px)
    skin = green = sky = dark = pink = bright = 0
    top = px[:len(px) // 2]
    sky_top = 0
    for i, (r, g, b) in enumerate(px):
        mx, mn = max(r, g, b), min(r, g, b)
        v = mx
        if r > 95 and g > 40 and b > 20 and r > g > b and (mx - mn) > 15 and abs(r - g) > 15:
            skin += 1
        if g >= mx and (g - b) > 18 and (g - r) > 8:
            green += 1
        if b >= mx and (b - r) > 18 and v > 105:
            sky += 1
            if i < len(px) // 2:
                sky_top += 1
        if v < 62:
            dark += 1
        if r > 150 and b > 105 and g < min(r, b) + 25 and (r - g) > 30:
            pink += 1
        if v > 218 and (mx - mn) < 42:
            bright += 1
    f = lambda c: c / float(n)
    t = []
    # ★ 第 56 轮改口径：原来这里给的是「人像」—— 但判据只是"暖棕色像素 > 5%"，
    #   木头、吉他、泳池围栏、暖石墙全都中 → 「人像肤色」场景里塞了一堆没人的照片（已拼图确认）。
    #   现在这个色彩判据只叫「暖肤调」，真正的「人像特写 / 人脸 / 人群」由 YuNet 人脸检测给（见 face_r56.py）。
    if f(skin) > 0.05:
        t.append('暖肤调')
    if f(green) > 0.28:
        t.append('绿意')
    if f(sky) > 0.18:
        t.append('天空水面')
    if f(dark) > 0.38:
        t.append('夜景')
    if f(pink) > 0.10:
        t.append('花卉')
    if f(bright) > 0.30:
        t.append('高调')
    if not t:
        t.append('日常')
    return t


def main():
    # ★ 第 54 轮：图清单的**顺序**决定「按场景找配方」挑到哪张（gen_r52.pick_photo 按顺序取
    #   第一张标签对题的）。原来直接 sorted() 按文件名字典序 → `…__cmp__…` 排在 `…__s…` 前面,
    #   于是 263 条里 229 条挑中的是站点统一对比图。现在改成：
    #   主图 → 其余作者样片 → 对比场景（对比图只做兜底）。
    def order_key(f):
        slug = f.split('__')[0]
        hero = HERO.get(slug, '')
        is_author = '__cmp__' not in f
        return (0 if (hero and f == hero) else (1 if is_author else 2), f)

    files = sorted((f for f in os.listdir(IMG) if f.lower().endswith('.jpg')), key=order_key)
    if os.path.exists(ANIMALS_JSON):
        ANIMALS.update(json.load(io.open(ANIMALS_JSON, encoding='utf-8')))
        print('   动物例外：%d 张（%s）' % (len(ANIMALS), '、'.join(ANIMALS.values())))
    if os.path.exists(FACES_JSON):
        FACES.update(json.load(io.open(FACES_JSON, encoding='utf-8')))
        print('   人脸检测结果：%d 条（人像特写 %d / 有脸 %d）'
              % (len(FACES), sum(1 for v in FACES.values() if v.get('big', 0) >= 1),
                 sum(1 for v in FACES.values() if v.get('n', 0) >= 1)))
    tags, photos = {}, {}
    for i, f in enumerate(files):
        t = face_tags(f)                       # 第 56 轮：人脸类标签放最前（最可信）
        t += [x for x in tags_of(os.path.join(IMG, f)) if x not in t]
        for k, v in SCENE_TAG.items():
            if '__cmp__%s.jpg' % k in f and v not in t:
                t.append(v)
        tags[f] = t
        slug = f.split('__')[0]
        photos.setdefault(slug, []).append(f)
        if (i + 1) % 100 == 0:
            print('   已归类 %d/%d' % (i + 1, len(files)))
    print('  共 %d 张图；标签分布：' % len(files))
    from collections import Counter
    c = Counter(x for v in tags.values() for x in v)
    for k, v in c.most_common():
        print('    %-6s %d 张' % (k, v))
    js = ('window.__OM3PHOTOTAGS__ = ' + json.dumps(tags, ensure_ascii=False, separators=(',', ':')) + ';\n'
          'window.__OM3PHOTOS__ = ' + json.dumps(photos, ensure_ascii=False, separators=(',', ':')) + ';\n')
    s = io.open(P, encoding='utf-8').read()
    import re
    s = re.sub(re.escape(B) + r'.*?' + re.escape(E) + r'\n?', '', s, flags=re.S)
    # ⚠ 这段是插到**已有的 <script> 块内部**（场景对比脚本之前），所以只能写 JS 语句；
    #    再套一层 <script> 标签就是 `SyntaxError: Unexpected token '<'`（第 39 轮踩过）。
    block = B + '\n' + js + E + '\n'
    k = s.find('/* ---------- 4. 场景对比')      # 第 39 轮起标题带后缀，匹配前缀即可
    assert k > 0, '找不到场景对比脚本块'
    s = s[:k] + block + s[k:]
    io.open(P, 'w', encoding='utf-8', newline='').write(s)
    print('  ✅ 已嵌入 base.html（%d 张图的标签 + %d 个配方的图清单，约 %.0f KB）'
          % (len(tags), len(photos), len(block) / 1024.0))


if __name__ == '__main__':
    main()
