# -*- coding: utf-8 -*-
"""第 56 轮验收：场景挑图「人像可信化」（YuNet 人脸检测 + 说真话的兜底）+ 重名配方区分。

跑法：
  python scripts/dv_r56.py            # 静态（快）
  python scripts/dv_r56.py --runtime  # 另加无头 Chrome：切到「场景对比 → 人像肤色」看真渲染结果
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding='utf-8')
SRC = r'D:\workspace\om3-handbook'
TMP = r'C:\Users\82302\AppData\Local\Temp'
IMG = os.path.join(SRC, 'apk', 'assets', 'images')
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


src = io.open(os.path.join(SRC, 'app', 'base.html'), encoding='utf-8').read()
OLD = io.open(os.path.join(SRC, 'app', 'base.before_r56.html'), encoding='utf-8').read()


def grab(text, marker):
    j, k = None, None
    i = text.rindex(marker) + len(marker)
    while text[i] in ' \n':
        i += 1
    return json.JSONDecoder().raw_decode(text, i)[0]


REC = grab(src, 'window.__OM3RECIPES__=')
OLD_REC = grab(OLD, 'window.__OM3RECIPES__=')
PT = grab(src, 'window.__OM3PHOTOTAGS__ =')
OLD_PT = grab(OLD, 'window.__OM3PHOTOTAGS__ =')
PH = grab(src, 'window.__OM3PHOTOS__ =')
SC = grab(src, 'window.__OM3SC__ =')
SCN = grab(src, 'window.__OM3SCENES__ =')
FACES = json.load(io.open(os.path.join(SRC, 'scripts', '_r56_faces.json'), encoding='utf-8'))
by = {r['slug']: r for r in REC}
# 第 57 轮口径（婚礼/儿童两个场景已删；没有检测依据的场景 = []；建筑几何走人工白名单）
WANT = {'portrait': ['人像特写'], 'mono': [],
        'flower': ['花卉'], 'sunset': [], 'forest': ['绿意'], 'autumn': ['绿意'],
        'night': ['夜景'], 'skywater': ['天空水面'], 'snow': ['高调'], 'mist': [],
        'arch': ['建筑几何'], 'still': [], 'street': ['人群'], 'travel': ['人群'],
        'backlight': [], 'food': [], 'indoor': ['夜景'], 'film': []}

print('=== ① 人脸检测数据 ===')
A(len(FACES) == 534, '人脸检测结果覆盖图库全部 534 张（实测 %d）' % len(FACES))
A(os.path.exists(os.path.join(SRC, 'scripts', 'models', 'face_detection_yunet_2023mar.onnx')),
  'YuNet 模型已入库（离线可用）')
A(sum(1 for v in FACES.values() if v.get('big', 0) >= 1) == 3,
  '「人像特写」（人脸占画面 ≥2.5%%）全库 %d 张' % sum(1 for v in FACES.values() if v.get('big', 0) >= 1))
A(FACES['james-bloomer_om-3-tokyo-wetzlar__s02.jpg']['n'] == 0,
  '★ 回归用例：吉他特写那张检出 0 张脸（旧色彩判据把它当人像）')
A(FACES['peter-turner_portra-400__s01.jpg']['big'] >= 1,
  '★ 回归用例：咖啡馆人像那张算出人像特写（最大脸 %.2f%%）'
  % (FACES['peter-turner_portra-400__s01.jpg']['max'] * 100))

print('\n=== ② 标签口径（人像 → 暖肤调 + 人脸类）===')
warm_new = {k for k, v in PT.items() if '暖肤调' in v}
warm_old = {k for k, v in OLD_PT.items() if '人像' in v}
A(warm_new == warm_old, '「暖肤调」的图集合 == 旧「人像」的图集合（%d 张，纯改名不换图）' % len(warm_new))
A(not any('人像' in v for v in PT.values()), '旧「人像」标签已彻底不存在（不再拿木墙当人像）')
bad_big = [k for k, v in PT.items() if '人像特写' in v and FACES.get(k, {}).get('big', 0) < 1
           and FACES.get(k, {}).get('max', 0) < 0.025]
A(not bad_big, '「人像特写」只给真检出大脸的图（可疑 %s）' % (bad_big[:3] or 0))
bad_face = [k for k, v in PT.items() if '人脸' in v and FACES.get(k, {}).get('n', 0) < 1]
A(not bad_face, '「人脸」只给检出≥1 张脸的图（可疑 %s）' % (bad_face[:3] or 0))
bad_crowd = [k for k, v in PT.items() if '人群' in v and not (
    '__cmp__marathon' in k or (FACES.get(k, {}).get('n', 0) >= 3 and FACES.get(k, {}).get('max', 0) < 0.025))]
A(not bad_crowd, '「人群」只给多人小脸的图（或站点统一人群场景图）（可疑 %s）' % (bad_crowd[:3] or 0))
A(len(PH) == 77, '配方图清单仍是 77 条（PHOTOS %d）' % len(PH))
# 手工动物例外：人脸检测不认物种（andrew-gow 那张是猫），必须不给 人脸/人像特写
_AN = json.load(io.open(os.path.join(SRC, 'scripts', '_r56_animals.json'), encoding='utf-8'))     if os.path.exists(os.path.join(SRC, 'scripts', '_r56_animals.json')) else {}
A(all('动物' in (PT.get(f) or []) and '人像特写' not in (PT.get(f) or []) and '人脸' not in (PT.get(f) or [])
      for f in _AN), '动物例外表里的图只标「动物」，不标人脸类（%d 张：%s）'
  % (len(_AN), '、'.join(_AN.values())))

print('\n=== ③ __OM3SC__ 每条：图 / 说明 三态自洽 ===')
bad = []
for sc in SC:
    want = WANT.get(sc['k'], [])
    for it in sc['items']:
        f, d = it['f'], it.get('d') or ''
        tags = PT.get(f) or []
        hit = bool(want) and any(t in want for t in tags)
        if d.startswith('图按画面自动归类：'):
            got = d.split('（自动判断', 1)[0][len('图按画面自动归类：'):]
            if sorted(got.split(' / ')) != sorted(tags):
                bad.append((sc['k'], it['n'], '说明里的标签与图不符', got, tags))
            elif not hit:
                bad.append((sc['k'], it['n'], '声称归类但没命中期望标签', got, want))
        elif d.startswith('本条没有对「'):
            if hit:
                bad.append((sc['k'], it['n'], '命中了却写了兜底说明', d[:24], tags))
            elif '显示站点统一对比图' in d and '__cmp__' not in f:
                bad.append((sc['k'], it['n'], '说用对比图但给的不是对比图', f, ''))
            elif '显示作者样片' in d and '__cmp__' in f:
                bad.append((sc['k'], it['n'], '说用作者样片但给的是对比图', f, ''))
            elif ('「%s」' % sc['label']) not in d:
                bad.append((sc['k'], it['n'], '兜底说明里的场景名不对', d[:24], sc['label']))
        elif d.startswith('本场景不挑题材'):
            # 第 57 轮：没有检测依据的场景（食物/静物/日落/逆光/雾/胶片）改成"不挑题材"
            if want:
                bad.append((sc['k'], it['n'], '有期望却说不挑题材', d[:24], ''))
        elif d.startswith('人工挑选：'):
            if '「%s」' % sc['label'] not in d:
                bad.append((sc['k'], it['n'], '人工挑选说明里场景名不对', d[:24], sc['label']))
        else:
            bad.append((sc['k'], it['n'], '说明没有前缀（既没声称也没兜底）', d[:24], ''))
A(not bad, '每条说明与图、与场景期望三者自洽（问题 %d：%s）' % (len(bad), bad[:2] or 0))

print('\n=== ④ 人相关场景：要么真·人像，要么明说是兜底 ===')
# 第 57 轮：婚礼聚会 / 儿童亲子 两个场景已删（没实拍 → 改成搜索找风格）
for k in [x for x in ('portrait', 'wedding', 'kids') if any(y['k'] == x for y in SC)]:
    sc = next(x for x in SC if x['k'] == k)
    n_hit = sum(1 for it in sc['items'] if '人像特写' in (PT.get(it['f']) or []))
    n_mis = sum(1 for it in sc['items'] if (it.get('d') or '').startswith('本条没有对「'))
    A(n_hit + n_mis == len(sc['items']),
      '「%s」%d 条：真·人像特写 %d 条 / 明说兜底 %d 条（没有第三种）' % (sc['label'], len(sc['items']), n_hit, n_mis))
    A(n_hit >= 1, '「%s」至少有一条真·人像特写（%d 条）' % (sc['label'], n_hit))
    first = sc['items'][0]
    A('人像特写' in (PT.get(first['f']) or []), '「%s」第一条就是真·人像特写（%s）' % (sc['label'], first['f']))
A(sum(1 for sc in SC for it in sc['items'] if (it.get('d') or '').startswith('本条没有对「')) >= 1,
  '兜底条目确实出现在数据里（不是空话）')

print('\n=== ⑤ 命中优先排序 ===')
bad_order = []
for sc in SC:
    seen_miss = False
    for it in sc['items']:
        miss = (it.get('d') or '').startswith('本条没有对「')
        if miss:
            seen_miss = True
        elif seen_miss:
            bad_order.append(sc['k'])
            break
A(not bad_order, '每个场景里"对题"的都排在"兜底"前面（乱序 %s）' % (bad_order[:3] or 0))

print('\n=== ⑥ 页面 SEL_TAGS 口径（第 39 轮那套已是死代码，表要跟数据一致）===')
tab = src[src.index('var SEL_TAGS = {'):src.index('};', src.index('var SEL_TAGS = {'))]
cmt = src[max(0, src.index('var SEL_TAGS = {') - 700):src.index('var SEL_TAGS = {')]
for k, v in (('portrait', '人像特写'), ('wedding', '人像特写'), ('kids', '人像特写')):
    A("'%s'" % v in tab.split(k + ':')[1].split('\n')[0], 'SEL_TAGS.%s 指向「%s」' % (k, v))
A('暖肤调' in cmt or '暖棕像素' in cmt, 'SEL_TAGS 那段注释写明了「人像」已改名暖肤调（口径一致）')
A('function pickPhoto' not in src, '页面里没有 pickPhoto（第 39 轮那套挑图确实是死代码，真正生效的是数据侧）')
# 第 57 轮删了婚礼/儿童 → 现在是 18 个场景
A(len(SCN) == 18 and all(x['k'] in WANT for x in SCN),
  '%d 个场景都在期望表里（不缺口径）' % len(SCN))

print('\n=== ⑦ 重名配方区分 ===')


def norm(n):
    return re.sub(r'[\s·\-—]', '', re.sub(r'[（(].*?[)）]', '', n)).lower()


g = defaultdict(list)
for r in REC:
    g[norm(r['n'])].append(r)
named = [k for k, v in Counter(r['n'] for r in REC).items() if v > 1]
A(not named, 'REC %d 条名字全部唯一（重名 %s）' % (len(REC), named[:3] or 0))
cards = re.findall(r'<div class="card" id="r-([^"]+)">.*?<span class="cname">([^<]*)</span>', src, re.S)
dup_c = [k for k, v in Counter(n for _, n in cards).items() if v > 1]
A(not dup_c, '卡片 %d 张标题全部唯一（重名 %s）' % (len(cards), dup_c[:3] or 0))
for slug in ('peter-turner_portra-400', 'james-bloomer_portra-400', 'isaac-mitropoulos_portra-400',
             'gareth_b_kodachrome_64', 'ibd-fuji-classic-chrome'):
    nm = by[slug]['n']
    A(('（%s）' % by[slug]['a'].strip()) in nm, '%s 名字带作者区分：%s' % (slug, nm))
A(by['tom-jackson_kodachrome-64-print']['n'] == 'Kodachrome 64（冲印版）',
  '已有区分词的没被误伤（Kodachrome 64（冲印版）保持原样）')
A(by['james-bloomer_kodachrome-64-v0']['n'] == 'Kodachrome 64（早期版）',
  '已有区分词的没被误伤（Kodachrome 64（早期版）保持原样）')
IDX = grab(src, 'var IDX=')
A(sum(1 for it in IDX if 'Portra 400（' in str(it.get('n'))) >= 3,
  '搜索索引里也换了名（IDX 里带作者的 Portra 400 有 %d 条）'
  % sum(1 for it in IDX if 'Portra 400（' in str(it.get('n'))))
A(sum(1 for it in IDX if it.get('n') == 'Portra 400') == 0, 'IDX 里不再有裸的「Portra 400」')
k_rows = re.findall(r'<tr id="k-([^"]+)">\s*<td>([^<]*)</td>', src)
_mis = [(sl, n, by[sl]['n']) for sl, n in k_rows if sl in by and n != by[sl]['n']]
A(not _mis, '固定色温表 %d 行的名字与 REC 逐字一致（不一致 %s）' % (len(k_rows), _mis[:2] or 0))
A(len(OLD_REC) == len(REC), '配方条数没变（%d）' % len(REC))
# 槽位：名字和作者都必须与 REC 一致（本轮发现 3 个槽位原本就写错了作者，靠白平衡偏移认人纠正）
_sl = re.findall(r'<div class="oslot" id="([^"]+)">.*?<span class="osname">([^<]*)</span>'
                 r'<span class="osauth">([^<]*)</span>', src, re.S)
_bysl = {}
for r in REC:
    _bysl.setdefault(r['n'], r)
_badsl = [(i, n, a2) for i, n, a2 in _sl
          if n in _bysl and _bysl[n]['a'].strip() != a2.strip()]
A(not _badsl, '槽位的名字/作者与 REC 一致（不一致 %s）' % (_badsl[:3] or 0))
A(sum(1 for i, n, a2 in _sl if n in _bysl) == 29, '29 个档位槽位指向真配方（另 4 个是自配）')

print()
print('===== 静态结论：%s（%d 项，失败 %d）=====' % ('全部通过 ✅' if F == 0 else '有 %d 项失败 ❌' % F, K, F))

if '--runtime' not in sys.argv:
    sys.exit(1 if F else 0)

# ---------------------------------------------------------------- 运行时
print('\n=== ⑧ 运行时：真的切到「场景对比 → 人像肤色」看渲染出来的东西 ===')
d = os.path.join(SRC, 'app', 'images')
shutil.rmtree(d, ignore_errors=True)
os.makedirs(d)
need = set(re.findall(r'data-im="([^"]+)"', src))
for x in SC:
    for it in x['items']:
        need.add(it['f'])
for f in sorted(need):
    sp = os.path.join(IMG, f)
    if os.path.exists(sp):
        shutil.copy(sp, os.path.join(d, f))
print('    （临时挂了 %d 张图到 app/images）' % len(need))

JS = r"""
setTimeout(function(){
  var o = [];
  function ok(c, m){ o.push((c ? '[OK ] ' : '[FAIL] ') + m); }
  document.querySelector('#barABC button[data-p="C"]').click();
  setTimeout(function(){
    var sel = document.getElementById('scsel');
    sel.value = 's:portrait';
    sel.dispatchEvent(new Event('change', {bubbles: true}));
    setTimeout(function(){
      var sl = document.querySelectorAll('#scpager .scslide');
      ok(sl.length >= 10, '⑧ 人像肤色渲染出 ' + sl.length + ' 张 slide');
      var first = sl[0], img = first.querySelector('img');
      var fn = (img.getAttribute('data-im') || img.getAttribute('src') || '').split('/').pop();
      ok(fn === 'andrew-gow_rose-gold__s01.jpg',
         '⑧ 第一张是**真·人像**（' + fn + '）——修前这里是作者的绿植棚架图');
      var t0 = first.textContent || '';
      ok(t0.indexOf('人像特写') >= 0, '⑧ 第一张说明里写了「人像特写」');
      var t2 = (sl[2] ? sl[2].textContent : '');
      ok(t2.indexOf('本条没有对') >= 0 && t2.indexOf('人像肤色') >= 0,
         '⑧ 第 3 张**明说**"本条没有对「人像肤色」的实拍"（不再拿没人的图冒充）');
      var n = 0, tot = 0, i;
      for (i = 0; i < sl.length; i++){ var im = sl[i].querySelector('img'); tot++; if (im && im.naturalWidth > 0) n++; }
      ok(n === tot && tot > 5, '⑧ 这些图全部真的加载出来（' + n + '/' + tot + '）');
      ok(document.querySelectorAll('#scpager .scwheel').length > 0, '⑧ 每张还带小色轮');
      ok(window.__errs.length === 0, '⑧ 全程 0 JS 报错（' + window.__errs.length + '）');
      var d2 = document.createElement('pre'); d2.id = 'DBGOUT'; d2.textContent = o.join('\n');
      document.body.appendChild(d2);
    }, 1200);
  }, 1400);
}, 2600);
"""
k = src.find('<body')
j = src.find('>', k) + 1
head = ('<script>window.__OM3_APP__=1;window.__errs=[];window.onerror=function(m,s2,l){window.__errs.push(m+" @"+l)};'
        'window.addEventListener("unhandledrejection",function(e){window.__errs.push("rej:"+e.reason)});</script>')
out = src[:j] + head + src[j:].replace('</body>', '<script>' + JS + '</script></body>', 1)
p = os.path.join(SRC, 'app', '_probe_r56.html')
io.open(p, 'w', encoding='utf-8', newline='').write(out)
ud = os.path.join(TMP, 'omr56')
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--hide-scrollbars', '--user-data-dir=' + ud, '--window-size=560,900',
                    '--virtual-time-budget=30000', '--dump-dom', 'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
if kk < 0:
    print('  [FAIL] 探针没拿到输出')
    F += 1
    K += 1
else:
    body = dom[kk:].split('>', 1)[1].split('</pre>')[0]
    print(body)
    K += body.count('[')
    F += body.count('[FAIL]')
shutil.rmtree(d, ignore_errors=True)
try:
    os.remove(p)
except OSError:
    pass
print()
print('===== 全部结论：%s（%d 项，失败 %d）=====' % ('全部通过 ✅' if F == 0 else '有 %d 项失败 ❌' % F, K, F))
sys.exit(1 if F else 0)
