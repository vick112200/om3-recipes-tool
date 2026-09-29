# -*- coding: utf-8 -*-
"""第 55 轮：补 19 条配方的**数据**与**图片**。

两件事（可分开跑）：
  A. 抓站点现存的 `tom-jackson_porta-400-print`（我们快照里没有）→ `scripts/_r55_extra.json`
     · 从配方页的 RSC 数据里抠出完整对象（57 个字段），字段名与 `all_recipes.json` 同构
     · **不改 all_recipes.json**（它是证据）
  B. 下这 19 条的图（1200px）：作者样片 `<slug>__s%02d.jpg` + 6 个统一对比场景 `<slug>__cmp__<scene>.jpg`
     · 只下这 19 条，不碰已有 431 张
     · 原子落盘 / 可续跑 / 上游 404 单独记账（与 fetch_r54.py 同一套纪律）

用法：
  python scripts/fetch_r55.py                     # 预演：只列计划与体积
  python scripts/fetch_r55.py --download          # 真下（24 线程）
  python scripts/fetch_r55.py --download --only isaac-mitropoulos_portra-400
"""
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, 'apk', 'assets', 'images')
SNAP = os.path.join(ROOT, 'all_recipes.json')
EXTRA = os.path.join(ROOT, 'scripts', '_r55_extra.json')
PLAN = os.path.join(ROOT, 'scripts', '_r55_plan.json')
MISSING = os.path.join(ROOT, 'scripts', '_r55_missing.json')

SIZE = '1200'
MIN_EDGE = 1100
RETRY = 3
via = 'auto'
UA = {'User-Agent': 'Mozilla/5.0'}

# 本轮要补的 19 条（= 站点 sitemap 有、app 没有卡片；已排除旧版 ian-will_kinda-portra）
NEW = [
    'kaleigh-whitaker_bluegill-teal', 'alberto_torrejon_bleached', 'tom-jackson_porta-400-print',
    'isaac-mitropoulos_dreamy-white', 'ali_o_keefe_omtc_chrome', 'paul_clark_paul_clark_recipe',
    'chris-brogan_a-bit-more-vivid', 'kitty-marie_red-soda-pop', 'terry_mclaughlin_terry_mclaughlin_recipe',
    'stella-toul_carte-postal', 'isaac-mitropoulos_portra-160', 'isaac-mitropoulos_portra-400',
    'jerred_z_eternal_sunshine', 'luis-chavez_dirty-pop', 'karol-mizunia_vintage-teal',
    'emily_m4nerds_m4nerds', 'dave_herring_vibrant_chrome', 'burak-yilmaz_portside-chrome',
    'burak-yilmaz_asteroid-city',
]
MUST_FETCH = 'tom-jackson_porta-400-print'
CMP_SCENES = ['marathon', 'peace-memorial', 'redbud', 'rosslyn-dusk', 'misty-mountains', 'moss']


def proxy_url(u, w=1200, q=90):
    """站点自己的 next/image 代理：`/_next/image?url=<原图>&w=1200&q=90`。
    2026-09-27 晚 CDN 直连（images.om-recipes.com，Oracle WAF）对我们这个出口彻底不通
    （连 320px 都读不动、偶发 connection reset），而这个代理 3~4 秒一张、尺寸正好 1200。"""
    return ('https://om-recipes.com/_next/image?url=' + urllib.parse.quote(u, safe='')
            + '&w=%d&q=%d' % (w, q))


def long_edge(path):
    try:
        from PIL import Image
        w, h = Image.open(path).size
        return max(w, h)
    except Exception:
        return 0


def scene_key(c):
    return c['preparedObjectKey'].split('/')[-1].rsplit('.', 1)[0].replace('_', '-')


# ---------------- A. 抓站点那条 ----------------
def extract_recipe(html, slug):
    """从页面 RSC 数据里抠出完整配方对象（花括号配对 + json.loads）"""
    s = html.replace('\\"', '"')
    for m in [i for i in range(len(s)) if s.startswith('{"id":', i) or s.startswith('{"uuid":', i)]:
        depth, k, q, esc = 0, m, False, False
        while k < len(s):
            c = s[k]
            if q:
                if esc:
                    esc = False
                elif c == '\\':
                    esc = True
                elif c == '"':
                    q = False
            elif c == '"':
                q = True
            elif c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        try:
            o = json.loads(s[m:k + 1])
        except Exception:
            continue
        if isinstance(o, dict) and o.get('slug') == slug:
            return o
    return None


def fetch_extra():
    if os.path.exists(EXTRA):
        print('A. _r55_extra.json 已在（跳过抓取）')
        return json.load(io.open(EXTRA, encoding='utf-8'))
    url = 'https://om-recipes.com/recipes/' + MUST_FETCH
    print('A. 抓 %s …' % url)
    html = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read().decode('utf-8', 'replace')
    o = extract_recipe(html, MUST_FETCH)
    assert o, '没抠出 %s 的配方对象' % MUST_FETCH
    need = ['slug', 'recipeName', 'authorName', 'description', 'type', 'yellow', 'orange', 'orangeRed',
            'red', 'magenta', 'violet', 'blue', 'blueCyan', 'cyan', 'greenCyan', 'green', 'yellowGreen',
            'contrast', 'sharpness', 'highlights', 'shadows', 'midtones', 'shadingEffect',
            'exposureCompensation', 'whiteBalance2', 'whiteBalanceAmberOffset', 'whiteBalanceGreenOffset',
            'monochromeProfile', 'sampleImages', 'comparisonImages']
    miss = [k for k in need if k not in o]
    assert not miss, '抓到的对象缺字段：%s' % miss
    out = {k: o.get(k) for k in need}
    out['_source'] = url
    io.open(EXTRA, 'w', encoding='utf-8', newline='').write(json.dumps(out, ensure_ascii=False, indent=1))
    print('   ✅ 已写 %s（12 轴 + 影调 + 样片 %d 张 + 对比图 %d 张）'
          % (os.path.basename(EXTRA), len(o['sampleImages']), len(o['comparisonImages'])))
    return out


def load_recipes():
    snap = json.load(io.open(SNAP, encoding='utf-8'))['results']
    by = {r['slug']: r for r in snap}
    ex = json.load(io.open(EXTRA, encoding='utf-8'))
    by[ex['slug']] = ex
    return by


# ---------------- B. 图片 ----------------
def build_tasks(by):
    have = set(os.listdir(IMG))
    tasks, unknown = [], []
    for slug in NEW:
        r = by.get(slug)
        if not r:
            unknown.append(slug + '(数据都没有)')
            continue
        for i, s in enumerate(r.get('sampleImages') or []):
            fn = '%s__s%02d.jpg' % (slug, i + 1)
            tasks.append((s['assetUrls'][SIZE], os.path.join(IMG, fn)))
        cmap = {scene_key(c): c for c in (r.get('comparisonImages') or [])}
        for sc in CMP_SCENES:
            if sc in cmap:
                tasks.append((cmap[sc]['assetUrls'][SIZE], os.path.join(IMG, '%s__cmp__%s.jpg' % (slug, sc))))
    return tasks, unknown


def main():
    args = sys.argv[1:]
    fetch_extra()
    by = load_recipes()
    tasks, unknown = build_tasks(by)
    missing = [t for t in tasks if not os.path.exists(t[1])]
    print('B. 计划下载 %d 张（已有 %d，待下 %d）；19 条里 %d 条没有数据'
          % (len(tasks), len(tasks) - len(missing), len(missing), len(unknown)))
    if unknown:
        print('   ⚠ 没数据：%s' % unknown)
    todo = missing
    if '--only' in args:
        want = args[args.index('--only') + 1]
        todo = [t for t in todo if want in os.path.basename(t[1])]
        print('   --only %s → %d 张' % (want, len(todo)))
    if len(args) and '--limit' in args:
        todo = todo[:int(args[args.index('--limit') + 1])]
    io.open(PLAN, 'w', encoding='utf-8', newline='').write(json.dumps(
        {'recipes': NEW, 'tasks': [os.path.basename(t[1]) for t in tasks],
         'todo': [os.path.basename(t[1]) for t in todo]}, ensure_ascii=False, indent=1))
    if '--download' not in args:
        print('（预演，未下载；加 --download 真下）')
        return 0
    if not todo:
        print('✅ 没有要下的')
        return 0

    t0 = time.time()
    done, nogain, fails, gone = [0], [0], [], []

    def one(t):
        url, path = t
        part = path + '.part'
        old = long_edge(path)
        for k in range(1, RETRY + 1):
            # 第 1 次直连 CDN；之后改走站点代理（默认 --via auto）
            use = url if (k == 1 and via != 'proxy') else proxy_url(url)
            if via == 'direct' and k > 1:
                use = url
            try:
                with urllib.request.urlopen(urllib.request.Request(use, headers=UA), timeout=tmo) as r:
                    b = r.read()
                if len(b) < 2000:
                    raise IOError('body too small: %d' % len(b))
                open(part, 'wb').write(b)
                new = long_edge(part)
                if old and new <= old:
                    os.remove(part)
                    nogain[0] += 1
                    return None
                os.replace(part, path)
                done[0] += 1
                if done[0] % 10 == 0 or done[0] == len(todo):
                    print('   ...%d/%d  %.1f 分钟' % (done[0], len(todo), (time.time() - t0) / 60.0))
                return None
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    gone.append((os.path.basename(path), url))
                    return None
                if k == RETRY:
                    return (os.path.basename(path), str(e))
                time.sleep(2 * k)
            except Exception as e:
                if k == RETRY:
                    try:
                        if os.path.exists(part):
                            os.remove(part)
                    except OSError:
                        pass
                    return (os.path.basename(path), str(e))
                time.sleep(2 * k)

    workers = int(args[args.index('--workers') + 1]) if '--workers' in args else 24
    global RETRY
    if '--retry' in args:
        RETRY = int(args[args.index('--retry') + 1])
    tmo = int(args[args.index('--timeout') + 1]) if '--timeout' in args else 300
    global via
    via = args[args.index('--via') + 1] if '--via' in args else 'auto'
    print('   取图方式：%s（auto = 先直连 CDN，失败改走站点 /_next/image 代理）' % via)
    print('   并发 %d 线程' % workers)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(one, todo):
            if r:
                fails.append(r)
    print('下载完成：新增 %d 张（%d 张像素没变大按原样保留），用时 %.1f 分钟'
          % (done[0], nogain[0], (time.time() - t0) / 60.0))
    if gone:
        print('ℹ 上游 404：%s' % ', '.join(n for n, _ in gone))
        io.open(MISSING, 'w', encoding='utf-8', newline='').write(json.dumps(
            [{'file': n, 'url': u} for n, u in gone], ensure_ascii=False, indent=1))
    if fails:
        print('❌ 失败 %d：' % len(fails))
        for n, e in fails:
            print('   %s %s' % (n, e))
    return 2 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
