# -*- coding: utf-8 -*-
"""第 53 轮验收：雨天并入「雾 / 阴天 / 雨天」+ 暖光现场提示 + 解读不再膨胀
跑法：python scripts/dv_r53.py
"""
import io
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\workspace\om3-handbook\scripts')
from om3_profile import gen6   # noqa: E402

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


SC = grab('__OM3SC__')
SN = grab('__OM3SCENES__')
REC = grab('__OM3RECIPES__')
sc = dict((x['label'], x['items']) for x in SC)

print('=== ① 雨天并入「雾 / 阴天 / 雨天」 ===')
A(len(SC) == 18, '场景 18 个（原 21；第 57 轮删了「婚礼聚会 / 儿童亲子」（没实拍 → 改成搜索找风格））')
A(not any(x['k'] == 'rain' for x in SC), '__OM3SC__ 里没有 rain 场景了')
A(not any(x['k'] == 'rain' for x in SN), '__OM3SCENES__ 里也没有 rain')
A(any(x['k'] == 'mist' and x['label'] == '雾 / 阴天 / 雨天' for x in SC), 'mist 场景改名「雾 / 阴天 / 雨天」')
A('>s:rain<' not in src and 'value="s:rain"' not in src, '下拉里没有「雨天」这一项了')
A('value="s:mist">雾 / 阴天 / 雨天' in src, '下拉里 mist 的文案也改了')
A('18 个场景' in src, '下拉的说明改成「18 个场景」')
mist_kw = next(x for x in SN if x['k'] == 'mist')['kw']
A(all(w in mist_kw for w in ('雨', '雨后', '水汽')), '合并后场景词包含雨/雨后/水汽（%s…）' % '/'.join(mist_kw[:6]))
A(len(sc.get('雾 / 阴天 / 雨天') or []) == 8, '合并后 8 条（原来是两个场景、名单还互不相同）')

print('\n=== ② 暖光 / 灯光下：加"暖光现场"提示，条数不动 ===')
room = sc.get('暖光 / 灯光下') or []
A(len(room) == 8, '仍是 8 条（按判断"不收窄"）')
A(all('暖光现场' in (i.get('fd') or '') for i in room), '8 条都带「暖光现场」一行')
A(all(('关「保持暖色调」' in (i.get('fd') or '')) and ('M 方向拨 1 格' in (i.get('fd') or '')) for i in room),
  '提示内容 = 先 AUTO + 关「保持暖色调」；压不住按 M 方向拨 1 格')
A(all('AUTO' in (i.get('fd') or '') for i in room), '每条都写了 AUTO')

print('\n=== ③ 参数解读没有膨胀（结构仍是 6 行 + 现场四句）===')
c6 = gen6([r for r in REC if r['t'] != 'MONO'][0])
A(c6['tip'].count('；') in (3, 4), '彩色配方的「提示」固定 4 段（内含一个分号时算 5 段；实测 %d 段）' % (c6['tip'].count('；') + 1))
folds = re.findall(r'<details class="fold fgen">.*?</details>', src, re.S)
A(len(folds) == 77, '卡片上还是每张卡 1 个参数解读折页（77 张 = 58 + 第 55 轮 19；没有为"更长"改结构）')
A(all(f.count('<div class="row">') in (6, 7) for f in folds), '每个折页仍是 6 行（+来源）')
print()
print('===== 结论：%s（%d 项，失败 %d）=====' % ('全部通过 ✅' if F == 0 else '有 %d 项失败 ❌' % F, K, F))
sys.exit(1 if F else 0)
