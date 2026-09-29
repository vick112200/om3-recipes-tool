# -*- coding: utf-8 -*-
"""第 54 轮：把图片库全量升到 **1200px**（作者主图/样片优先方案的配套）。

背景
----
`app/base.html` 的 `__OM3PHOTOS__` 是按**文件名字典序**建的（`__cmp__…` 排在 `__s…` 前面），
所以场景挑图（`gen_r52.py::pick_photo` 按顺序取第一张对题的）几乎永远先撞上「本站统一对比场景」。
本轮把顺序改成作者优先，同时把图换成原站 1200px（原来 960px）。

本脚本只干一件事：**把 apk/assets/images 里的图按原站 1200px 重下**，文件名不变。
  · 目标文件名规则（与 `fetch_all.py` 完全一致，别改）：
      `<slug>__s%02d.jpg`      ← 原站 sampleImages[i]，i 从 0 起
      `<slug>__cmp__<scene>.jpg` ← 原站 comparisonImages 里 scene ∈ 本库 6 个的场景
  · **跳过条件**：文件已存在且长边 ≥ 1100（用 PIL 量）→ 不重下（幂等）
  · **原子落盘**：先写 `<目标>.part`，成功才 `os.replace`（中断不会留半张图）
  · 只读 `all_recipes.json`，不猜任何 URL；映射不到源站的图（如 momo_everyday 那 1 张）**原样保留**
  · 失败会逐条打印并在最后汇总；有失败则退出码 2（便于外面判成败）

用法
----
  python scripts/fetch_r54.py                 # 预演：只列任务与体积，不下载
  python scripts/fetch_r54.py --download      # 真下（10 线程，可反复重跑）
  python scripts/fetch_r54.py --download --limit 5      # 只下前 5 个（冒烟）
  python scripts/fetch_r54.py --download --only andrew-gow_rose-gold
"""
import io, json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding='utf-8')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(BASE, 'apk', 'assets', 'images')
SRC = os.path.join(BASE, 'all_recipes.json')
MANIFEST = os.path.join(BASE, 'scripts', '_r54_fetch.json')
MISSING = os.path.join(BASE, 'scripts', '_r54_missing.json')   # 上游 404 的清单（别每次重试）

SIZE = '1200'
MIN_EDGE = 1100                      # 长边达到这个数就不重下
SCENES = ['marathon', 'peace-memorial', 'redbud', 'rosslyn-dusk', 'misty-mountains', 'moss']
UA = {'User-Agent': 'Mozilla/5.0'}
RETRY = 3


def long_edge(path):
    """返回长边像素；读不出来返回 0（当成需要重下）"""
    try:
        from PIL import Image
        w, h = Image.open(path).size
        return max(w, h)
    except Exception:
        return 0


def scene_key(c):
    """原站 comparisonImages 的 key：文件名去扩展、下划线转连字符"""
    return c['preparedObjectKey'].split('/')[-1].rsplit('.', 1)[0].replace('_', '-')


def build_tasks(size=SIZE):
    data = json.load(io.open(SRC, encoding='utf-8'))
    by_slug = {r['slug']: r for r in data['results']}
    have = set(os.listdir(IMG))
    tasks, keep, unknown = [], [], []

    # ① 已在库里的图：按文件名反查源 URL（cmp 与 sNN 两种命名都要能对上）
    for f in sorted(have):
        m = re.match(r'^(?P<slug>.+?)__cmp__(?P<scene>.+)\.jpg$', f)
        if m:
            r = by_slug.get(m.group('slug'))
            if not r:
                unknown.append(f)
                continue
            hit = [c for c in (r.get('comparisonImages') or []) if scene_key(c) == m.group('scene')]
            if hit:
                tasks.append((hit[0]['assetUrls'][size], os.path.join(IMG, f)))
            else:
                unknown.append(f)
            continue
        m = re.match(r'^(?P<slug>.+?)__s(?P<n>\d+)\.jpg$', f)
        if m:
            r = by_slug.get(m.group('slug'))
            i = int(m.group('n')) - 1
            if r and i < len(r.get('sampleImages') or []):
                tasks.append((r['sampleImages'][i]['assetUrls'][size], os.path.join(IMG, f)))
            else:
                unknown.append(f)
            continue
        unknown.append(f)

    # ② 库里还没有、但源站有的样片（补齐：例如 ibd-fuji-classic-neg 的第 6 张）
    #    ⚠ 只补「库里已经有图的 slug」——源站 78 条里有 20 条本 app 根本没收录，
    #      照单全下会多出 15 张没人引用的孤儿图（第一版就是这么写的，已改）。
    shipped = set()
    for f in have:
        m = re.match(r'^(?P<slug>.+?)__(?:cmp__|s\d+)', f)
        if m:
            shipped.add(m.group('slug'))
    for slug, r in by_slug.items():
        if slug not in shipped:
            continue
        for i, s in enumerate(r.get('sampleImages') or []):
            fn = '%s__s%02d.jpg' % (slug, i + 1)
            if fn not in have:
                tasks.append((s['assetUrls'][size], os.path.join(IMG, fn)))

    return tasks, unknown


def main():
    args = sys.argv[1:]
    bucket = SIZE
    if '--bucket' in args:
        bucket = args[args.index('--bucket') + 1]
    force = '--force' in args
    workers = 10
    if '--workers' in args:
        workers = int(args[args.index('--workers') + 1])
    tasks, unknown = build_tasks(bucket)
    # 三种情况不进下载队列：
    #   ① 已经是目标分辨率（长边 ≥ 1100）→ 上次跑过了
    #   ② 长边 < 960 → **原图本身就不够大**（960 桶返回 800x600 就说明原图只有 800），
    #      1200 桶不可能给出更多像素（实测：只会把同一尺寸重编码得更重）。纯浪费带宽。
    #   ③ --force（修桶用）时以上两条都不生效
    tried = set()
    if os.path.exists(MANIFEST):
        try:
            d0 = json.load(io.open(MANIFEST, encoding='utf-8'))
            # ⚠ 键名要和下面 json.dump 写的一致（第一版读 tried_no_gain、写 no_gain_files →
            #   那 36 张"升不动"的图每次重跑都会被再下一遍；写测试时抓到的）
            tried = set(d0.get('no_gain_files') or d0.get('tried_no_gain') or [])
        except Exception:
            tried = set()
    # 上游 404 的（原站自己就没这张图）也别每次重试
    if os.path.exists(MISSING):
        try:
            tried |= set(x['file'] for x in json.load(io.open(MISSING, encoding='utf-8')))
        except Exception:
            pass
    skip_ok = [t for t in tasks if os.path.exists(t[1]) and long_edge(t[1]) >= MIN_EDGE]
    skip_small = [t for t in tasks
                  if os.path.exists(t[1]) and long_edge(t[1]) < 960]
    # ③ 上次试过、1200 桶也只给出同样像素的（原图就在 960~1099 之间）→ 别再下一次
    skip_tried = [t for t in tasks if os.path.basename(t[1]) in tried]
    if force:
        todo = list(tasks)
    else:
        drop = set(map(tuple, skip_ok)) | set(map(tuple, skip_small)) | set(map(tuple, skip_tried))
        todo = [t for t in tasks if tuple(t) not in drop]

    print('图片库 %s' % IMG)
    print('  取自原站 %spx 桶；任务 %d' % (bucket, len(tasks)))
    print('  跳过：已达标 %d；原图就不够大（长边<960，升了也没用）%d；上次试过也升不动 %d；待下 %d'
          % (len(skip_ok), len(skip_small), len(skip_tried), len(todo)))
    print('  ⚠ 源站映射不到、原样保留的图 %d 张：%s' % (len(unknown), ', '.join(unknown[:8])))

    if '--only' in args:
        want = args[args.index('--only') + 1]
        todo = [t for t in todo if want in os.path.basename(t[1])]
        print('  --only %s → %d 个' % (want, len(todo)))
    if '--limit' in args:
        n = int(args[args.index('--limit') + 1])
        todo = todo[:n]
        print('  --limit → %d 个' % len(todo))

    if '--download' not in args:
        print('（预演，未下载；加 --download 真下）')
        return 0
    if not todo:
        print('✅ 全部已达标，无需下载')
        return 0

    t0 = time.time()
    done = [0]
    nogain = [0]
    nogain_names = []
    fails = []
    gone = []          # 原站 404：这张图源站自己就没有（不是我们的失败）

    def one(t):
        url, path = t
        part = path + '.part'
        old = long_edge(path)                      # 0 = 文件不在
        for k in range(1, RETRY + 1):
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=300) as r:
                    b = r.read()
                if len(b) < 2000:
                    raise IOError('body too small: %d' % len(b))
                with open(part, 'wb') as fh:
                    fh.write(b)
                new = long_edge(part)
                # ★ 只在**像素真的变大**时才替换：很多图的原图本来就只有 800x600，
                #   1200 桶只是把同一尺寸重编码得更重（实测 +40% 字节、零画质收益）。
                if old and not force and new <= old:
                    os.remove(part)
                    nogain[0] += 1
                    nogain_names.append(os.path.basename(path))
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
                    try:
                        if os.path.exists(part):
                            os.remove(part)
                    except OSError:
                        pass
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

    print('  并发 %d 线程' % workers)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(one, todo):
            if r:
                fails.append(r)

    print('下载完成：替换/新增 %d 张（其中 %d 张「像素没变大」按原样保留），用时 %.1f 分钟'
          % (done[0], nogain[0], (time.time() - t0) / 60.0))
    if gone:
        print('ℹ 原站 404（上游确实没有这张图，不再重试）：%s' % ', '.join(n for n, _ in gone))
        json.dump([{'file': n, 'url': u} for n, u in gone],
                  io.open(MISSING, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if fails:
        print('❌ 失败 %d 个（重跑本脚本会只补这些）：' % len(fails))
        for n, e in fails:
            print('   %s  %s' % (n, e))
    json.dump({'bucket': bucket, 'todo': len(todo), 'done': done[0],
               'no_gain': nogain[0], 'no_gain_files': nogain_names, 'fail': fails},
              io.open(MANIFEST, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return 2 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
