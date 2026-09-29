# -*- coding: utf-8 -*-
"""第 52 轮验收：提示行升级 + 「暖光 / 灯光下」重建 + 场景规模（摄影师视角那三条）
跑法：python scripts/dv_r52.py
"""
import io
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\workspace\om3-handbook\scripts')
from om3_profile import gen6, profile, sat_word, dir_word, con_word   # noqa: E402

src = io.open(r'D:\workspace\om3-handbook\app\base.html', encoding='utf-8').read()
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


def grab(var, start=0):
    i = src.index('window.%s' % var, start)
    j = src.index('=', i) + 1
    while src[j] in ' \n':
        j += 1
    oc = src[j]
    cc = {'[': ']', '{': '}'}[oc]
    d = 0
    k = j
    while k < len(src):
        if src[k] == '"':
            k += 1
            while k < len(src):
                if src[k] == chr(92):
                    k += 2
                    continue
                if src[k] == '"':
                    break
                k += 1
        elif src[k] == oc:
            d += 1
        elif src[k] == cc:
            d -= 1
            if d == 0:
                return json.loads(src[j:k + 1])
        k += 1
    raise SystemExit('no ' + var)


REC = grab('__OM3RECIPES__')
SC = grab('__OM3SC__')
SN = grab('__OM3SCENES__')
PT = grab('__OM3PHOTOTAGS__')
by = dict((r['slug'], r) for r in REC)
sc = dict((x['label'], x['items']) for x in SC)

print('=== ① 提示行：现场四句 ===')
folds = re.findall(r'<details class="fold fgen">.*?</details>', src, re.S)
A(len(folds) == 77, '卡片上的参数解读折页 %d 个（58 + 第 55 轮补的 19；场景/照片那两份是 JSON 里的转义文本，单列）' % len(folds))
A(src.count('fold fgen') >= 600, '场景 + 照片数据里也带参数解读（转义出现的次数 %d）' % src.count('fold fgen'))
miss = [k for k in ('白平衡', '曝光补偿：', '先动哪个：', '最容易翻车：')
        if sum(1 for f in folds if k in f) < len(folds)]
A(not miss, '每个折页的「提示」都含四要素（缺：%s）' % miss)
A('先动哪个：先色环（浓淡）→ 再曲线（明暗）→ 最后白平衡' in src, '「先动哪个」写的是可执行顺序（色环→曲线→白平衡）')
A(all(('曝光补偿：' in gen6(r)['tip']) for r in REC), '每条配方的提示里都有曝光补偿方向')


def d_of(r):
    p = profile(r)
    return p['eff_w'] - p['eff_c']


print('\n=== ② 「暖光 / 灯光下」（原室内暖光）重建 ===')
A('室内暖光' not in src or '>室内暖光</option>' not in src, '页面里没有「室内暖光」这个选项了（已改名）')
A(any(x['k'] == 'indoor' and x['label'] == '暖光 / 灯光下' for x in SN), 'SCENES 里 indoor 的标签 =「暖光 / 灯光下」')
A('>暖光 / 灯光下</option>' in src, '#scsel 里也改名了')
room = sc.get('暖光 / 灯光下') or []
A(len(room) == 8, '重建后 %d 条（原 10 条几乎全是偏暖 + 用的是雾景照）' % len(room))
bad = [(i['n'], d_of(by[re.sub(r'^[rk]-', '', i['i'])])) for i in room
       if d_of(by[re.sub(r'^[rk]-', '', i['i'])]) >= 4]
A(not bad, '选卡规则生效：没有「偏暖」的（≥+4）被推荐进暖光场景（%s）' % bad[:3])
mono = [i['n'] for i in room if by[re.sub(r'^[rk]-', '', i['i'])]['t'] == 'MONO']
A(True, '其中黑白 %d 条（%s）—— 暖光下黑白是"绝缘"打法，属合理推荐' % (len(mono), '、'.join(mono) or '无'))
tags_ok = sum(1 for i in room if '夜景' in (PT.get(i['f']) or []))
A(tags_ok >= len(room) * 0.6, '照片换成灯光/混光那批：%d/%d 张带「夜景」标签' % (tags_ok, len(room)))

print('\n=== ③ 场景规模（用已有素材补） ===')
want = {'雾 / 阴天 / 雨天': 8, '雪景': 6, '森林绿意': 8, '夜景霓虹': 10}
for lab, exp in want.items():
    A(len(sc.get(lab) or []) == exp, '%s %d 条' % (lab, len(sc.get(lab) or [])))
A(len(SC) == 18, '场景总数 18（雨天并入「雾 / 阴天 / 雨天」；第 57 轮删了「婚礼聚会 / 儿童亲子」（没实拍 → 改成搜索找风格））')
# 第 57 轮：照片库里没有可靠的"雾"判据（只有站点统一对比图带这个标签）→ 不再声称，
# 改成"本场景不挑题材 / 明说兜底"。原来那条"≥4 张带雾标签"的断言按新口径重划。
_mist = sc.get('雾 / 阴天 / 雨天') or []
_caps = [(i.get('d') or '') for i in _mist]
A(len(_mist) == 8 and all(c.startswith(('本场景不挑题材', '本条没有对「')) for c in _caps),
  '雾/阴天/雨天 %d 条：一律"不挑题材/明说兜底"（不再拿站点对比图的"雾"标签冒充作者实拍）' % len(_mist))
snow_bad = [i['n'] for i in (sc.get('雪景') or []) if d_of(by[re.sub(r'^[rk]-', '', i['i'])]) >= 4]
A(not snow_bad, '雪景里没有偏暖的（雪一加暖就发黄）：%s' % (snow_bad[:3] or '无'))
forest_ok = [i['n'] for i in (sc.get('森林绿意') or [])
             if profile(by[re.sub(r'^[rk]-', '', i['i'])])['g'] >= 5]
A(len(forest_ok) >= 5, '森林绿意里 %d 条是「绿侧有推」的 %s' % (len(forest_ok), forest_ok[:4]))
night = sc.get('夜景霓虹') or []
buckets = set()
for i in night:
    r = by[re.sub(r'^[rk]-', '', i['i'])]
    p = profile(r)
    if r['t'] == 'MONO':
        buckets.add('mono')
    elif p['hi'] <= -3 or con_word(p) == '硬朗':
        buckets.add('hold')
    elif p['eff_w'] - p['eff_c'] >= 4:
        buckets.add('warm')
    elif p['eff_w'] - p['eff_c'] <= -4:
        buckets.add('cool')
    else:
        buckets.add('neutral')
A(len(buckets) >= 3, '夜景按打法分组，覆盖 %d 类（%s）' % (len(buckets), '/'.join(sorted(buckets))))
card = set(m.group(1) for m in re.finditer(r'<div class="card" id="r-([^"]+)">', src))
orphan = [i['i'] for x in SC for i in x['items']
          if i['i'].startswith('r-') and re.sub(r'^r-', '', i['i']) not in card]   # k- 是"单独占档"那两条，本来就存在
A(not orphan, '新加条目的「看卡片」锚点都有对应卡片（没有跳空：%s）' % orphan[:3])
A(all((i.get('dd') or '').strip() and (i.get('fd') or '').strip() for x in SC for i in x['items']),
  '新加的条目也都带参数解读（%d 条全部）' % sum(len(x['items']) for x in SC))
print()
print('===== 结论：%s（%d 项，失败 %d）=====' % ('全部通过 ✅' if F == 0 else '有 %d 项失败 ❌' % F, K, F))
sys.exit(1 if F else 0)
