# -*- coding: utf-8 -*-
"""用户 2026-09-23 第二轮反馈，三处一起修：

① 「成功的弹窗和底部栏有点重叠」→ 弹窗(.omask)是 fixed 居中、z-index 9700（在底栏之上），
   卡片高的时候下半部会压在底栏那一条上。改成遮罩底部留出底栏高度 + 卡片限高可滚。
② 「名字还是槽1 / 槽配方没有改名的地方」→ 实测：整套方案的名字是对的（Real · Murder Pink），
   但**槽位行的标题只写"槽 1"**，没有配方名，也没有改名入口。
   所以：存的时候把配方名一起记进槽位(one.name)，行标题显示它，并给每行加「改名」。
③ 「已加入我的配方 · C1 槽1」这句容易被当成名字 → 改成把名字放前面：'已加入：Real · Murder Pink（C1 · 槽1）'
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
p = r'D:\workspace\om3-handbook\app\base.html'
s = open(p, encoding='utf-8').read()

# ---------- ① 弹窗不压底栏 ----------
a = '.omask{position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:9700}'
b = ('.omask{position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:9700;'
     'padding:16px 16px calc(var(--om3barh,54px) + 16px) 16px}   /* 底部留出底栏高度：卡片不再压在底栏上 */')
assert s.count(a) == 1, ('omask', s.count(a))
s = s.replace(a, b, 1)

a = '.ocard{width:min(90vw,400px);background:#181818;border:1px solid #2e2e2e;border-radius:14px;padding:16px;box-shadow:0 14px 44px rgba(0,0,0,.65)}'
b = ('.ocard{width:min(90vw,400px);background:#181818;border:1px solid #2e2e2e;border-radius:14px;padding:16px;box-shadow:0 14px 44px rgba(0,0,0,.65);'
     'max-height:calc(100vh - var(--om3barh,54px) - 44px);overflow-y:auto;-webkit-overflow-scrolling:touch}'
     '  /* 卡片太高时自己滚，不把按钮顶到看不见 */')
assert s.count(a) == 1, ('ocard', s.count(a))
s = s.replace(a, b, 1)

# ---------- ② 槽位记名字 ----------
a = """    slots[N] = { vivid: rec.v, raw: kv, used: used, hi: rec.hi, mid: rec.mid,
                 lo: rec.sh, eff: rec.eff, shp: rec.shp, con: rec.con };"""
b = """    var keepName = name;   /* 槽位也记一份配方名：详情页每行显示它，并且可以单独改名 */
    slots[N] = { vivid: rec.v, raw: kv, used: used, hi: rec.hi, mid: rec.mid,
                 lo: rec.sh, eff: rec.eff, shp: rec.shp, con: rec.con, name: keepName };"""
assert s.count(a) == 1, ('slots[N]', s.count(a))
s = s.replace(a, b, 1)

# name 变量要先于 slots 计算：把 realTier/name 两行提到 slots 赋值之前
a = """    /* from 存**真实档位**（myset1..5），不再存 'builtin' —— 否则写回相机时 modeForTarget 认不出，
       会退到 'current' 或者去问相机要一个不存在的档位（这就是"显示完成但相机没变"的根因之一）。 */
    var realTier = /^(current|myset[1-5]|moviemyset[1-5])$/i.test(String(tier || '')) ? String(tier) : 'myset1';
    var name = String(nm || '').trim() || ((rec.n || '') + (rec.a ? (' · ' + rec.a) : ''));"""
b = """    /* from 存**真实档位**（myset1..5），不再存 'builtin' —— 否则写回相机时 modeForTarget 认不出，
       会退到 'current' 或者去问相机要一个不存在的档位（这就是"显示完成但相机没变"的根因之一）。 */
    var realTier = /^(current|myset[1-5]|moviemyset[1-5])$/i.test(String(tier || '')) ? String(tier) : 'myset1';
    var name = String(nm || '').trim() || ((rec.n || '') + (rec.a ? (' · ' + rec.a) : ''));"""
assert s.count(a) == 1, ('realTier', s.count(a))

# 把 realTier/name 的定义整块上移到 slots 之前
s = s.replace(b, '    /* （档位/名字在下面算好后再写进槽位） */', 1)
a2 = """    var kv = {};
    try{ kv = slotKV(rec, N); }catch(e){ kv = {}; }"""
b2 = """    /* 档位/名字先算好：槽位里也要存一份名字（详情页每行显示 + 可单独改名） */
    var realTier = /^(current|myset[1-5]|moviemyset[1-5])$/i.test(String(tier || '')) ? String(tier) : 'myset1';
    var name = String(nm || '').trim() || ((rec.n || '') + (rec.a ? (' · ' + rec.a) : ''));
    var kv = {};
    try{ kv = slotKV(rec, N); }catch(e){ kv = {}; }"""
assert s.count(a2) == 1, ('kv 开头', s.count(a2))
s = s.replace(a2, b2, 1)

# 去掉后面重复的 realTier/name 定义（原来在 arr.push 前）
a3 = """    var realTier = /^(current|myset[1-5]|moviemyset[1-5])$/i.test(String(tier || '')) ? String(tier) : 'myset1';
    var name = String(nm || '').trim() || ((rec.n || '') + (rec.a ? (' · ' + rec.a) : ''));
    arr.push({ id: 'b' + Date.now(), name: name, desc: desc, from: realTier,"""
b3 = """    arr.push({ id: 'b' + Date.now(), name: name, desc: desc, from: realTier,"""
assert s.count(a3) == 1, ('重复定义', s.count(a3))
s = s.replace(a3, b3, 1)

# toast 文案：名字放前面，避免被当成"槽1"
a4 = "      toastMsg('已加入我的配方 · ' + tierLabel(realTier) + ' 槽' + N);"
b4 = "      toastMsg('已加入：' + name + '（' + tierLabel(realTier) + ' · 槽' + N + '）');"
assert s.count(a4) == 1, ('toast', s.count(a4))
s = s.replace(a4, b4, 1)

open(p, 'w', encoding='utf-8', newline='').write(s)
print('①②③ 前三项改好；接下来处理行标题 + 每行改名')
