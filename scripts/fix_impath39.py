# -*- coding: utf-8 -*-
"""第 39 轮（修 BUG）：我给模拟预览图写的 `data-im` 多了 `images/` 前缀。
   页面取图是 `IMG(f)` = `'images/' + f`（除非 IMGMAP 里有内嵌数据），
   我写成 `images/xxx.jpg` → 实际请求 `images/images/xxx.jpg` → **占位图/看着像链接错了**。
   这里：① 两个生成器改成只写文件名；② 顺带给 dv_r37 加一条通用断言
   （**所有 data-im 必须是裸文件名，且文件必须存在**）——这条断言本来就能第一时间抓到。
"""
import io, sys
sys.stdout.reconfigure(encoding='utf-8')
BASE = r'D:\workspace\om3-handbook'
n = 0

# ① gen_recipes.py
p = BASE + r'\scripts\gen_recipes.py'
s = io.open(p, encoding='utf-8').read()
old = "    sim = 'images/%s__sim__marathon.jpg' % slug\n"
new = ("    simf = '%s__sim__marathon.jpg' % slug          /* data-im 只写文件名：IMG() 会自己拼 images/ */\n"
       "    sim = simf\n")
if old in s:
    s = s.replace(old, new, 1)
old2 = "    sim_ok = os.path.exists(r'D:\\workspace\\om3-handbook\\apk\\assets\\%s' % sim.replace('/', '\\\\'))"
new2 = "    sim_ok = os.path.exists(os.path.join(IMG_DIR, simf))"
if old2 in s:
    s = s.replace(old2, new2, 1)
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('  ① gen_recipes.py 已改')

# ② gen_lab_slots.py
p2 = BASE + r'\scripts\gen_lab_slots.py'
t = io.open(p2, encoding='utf-8').read()
old3 = ("    sim = 'images/%s__sim__marathon.jpg' % slug\n"
        "    sim_ok = os.path.exists(r'D:\\workspace\\om3-handbook\\apk\\assets\\%s' % sim.replace('/', '\\\\'))")
new3 = ("    sim = '%s__sim__marathon.jpg' % slug          /* data-im 只写文件名：IMG() 会自己拼 images/ */\n"
        "    sim_ok = os.path.exists(os.path.join(r'D:\\workspace\\om3-handbook\\apk\\assets\\images', sim))")
if old3 in t:
    t = t.replace(old3, new3, 1)
else:
    print('  ⚠ gen_lab_slots.py 锚点没找到，需人工看一眼')
io.open(p2, 'w', encoding='utf-8', newline='').write(t)
print('  ② gen_lab_slots.py 已改')

# ③ gen_recipes.py 需要 IMG_DIR 常量
p3 = BASE + r'\scripts\gen_recipes.py'
u = io.open(p3, encoding='utf-8').read()
if 'IMG_DIR' not in u:
    u = u.replace("P = r'D:\\workspace\\om3-handbook\\app\\base.html'",
                  "P = r'D:\\workspace\\om3-handbook\\app\\base.html'\n"
                  "IMG_DIR = r'D:\\workspace\\om3-handbook\\apk\\assets\\images'", 1)
    io.open(p3, 'w', encoding='utf-8', newline='').write(u)
    print('  ③ gen_recipes.py 已加 IMG_DIR 常量')

# ④ dv_r37.py：加通用断言（所有 data-im 都是裸文件名 + 文件存在）
p4 = BASE + r'\scripts\dv_r37.py'
v = io.open(p4, encoding='utf-8').read()
anchor = "# ---------------- ⑤ 优化版 LAB 档 + 模拟预览图 ----------------"
add = '''# ---------------- ⑤b 通用：所有 data-im 必须是裸文件名、且图必须存在 ----------------
print('=== data-im 体检 ===')
ims = re.findall(r'data-im="([^"]+)"', src)
bad_pref = [x for x in ims if x.startswith('images/')]
A(not bad_pref, '⑤b 没有 data-im 带 images/ 前缀（会拼成 images/images/ → 占位图）；违规 %d 条 %s'
  % (len(bad_pref), bad_pref[:2]))
idir = SRC + r'\\apk\\assets\\images'
missing = sorted(set(x for x in ims if not os.path.exists(os.path.join(idir, x))))
A(not missing, '⑤b 所有 data-im 的图都在（缺 %d 张：%s）' % (len(missing), missing[:3]))

'''
assert anchor in v
v = v.replace(anchor, add + anchor, 1)
io.open(p4, 'w', encoding='utf-8', newline='').write(v)
print('  ④ dv_r37.py 已加 data-im 体检断言')
