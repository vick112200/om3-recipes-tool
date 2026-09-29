# -*- coding: utf-8 -*-
"""第 56 轮 A：给图库里每张照片做**真人脸检测**（YuNet，比 Haar 准得多）。

为什么要它：原来「按场景挑图」唯一依据是 `gen_phototags.py` 的**色彩统计**标签，
其中「人像」= 暖棕色像素 > 5% —— 木头、吉他、泳池围栏、暖石墙全都中，
于是「人像肤色」场景里塞了一堆没人的照片（已拼图确认）。

输出：`scripts/_r56_faces.json`
  { "文件名": {"n": 检出数(score≥0.6), "big": 占比≥2.5% 的面孔数, "max": 最大面孔占画面比, "px": [w,h]} }
幂等：按 (mtime, size) 缓存，已算过的跳过；--force 重算。

用法：
  python scripts/face_r56.py            # 只算缺的
  python scripts/face_r56.py --force    # 全部重算
  python scripts/face_r56.py --only 人像  # 只算某几条（调试）
"""
import io
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMG = os.path.join(ROOT, 'apk', 'assets', 'images')
MODEL = os.path.join(HERE, 'models', 'face_detection_yunet_2023mar.onnx')
OUT = os.path.join(HERE, '_r56_faces.json')

SCORE_MIN = 0.6      # YuNet 置信度门槛
BIG_RATIO = 0.025    # 「人像特写」门槛：最大人脸框占画面 ≥ 2.5%
CROWD_MIN = 3        # 「人群」门槛：检出 ≥3 张脸
LONG = 1000          # 检测前把长边缩到这个尺寸（够用又便宜）

import cv2  # noqa: E402  （放在常量后面，方便看清依赖）


def detect(det, path):
    im = cv2.imread(path)
    if im is None:
        return None
    h, w = im.shape[:2]
    sc = LONG / float(max(w, h))
    if sc < 1:
        im = cv2.resize(im, (max(1, int(w * sc)), max(1, int(h * sc))), interpolation=cv2.INTER_AREA)
    h, w = im.shape[:2]
    det.setInputSize((w, h))
    _, faces = det.detect(im)
    n = big = 0
    mx = 0.0
    if faces is not None:
        for f in faces:
            if float(f[14]) < SCORE_MIN:
                continue
            n += 1
            r = float(f[2]) * float(f[3]) / float(w * h)
            mx = max(mx, r)
            if r >= BIG_RATIO:
                big += 1
    return {'n': n, 'big': big, 'max': round(mx, 5), 'px': [w, h]}


def main():
    args = sys.argv[1:]
    force = '--force' in args
    only = args[args.index('--only') + 1] if '--only' in args else ''
    if not os.path.exists(MODEL):
        raise SystemExit('缺模型：%s（YuNet onnx）' % MODEL)
    cache = {}
    if os.path.exists(OUT) and not force:
        try:
            cache = json.load(io.open(OUT, encoding='utf-8'))
        except Exception:
            cache = {}
    files = sorted(f for f in os.listdir(IMG) if f.lower().endswith('.jpg'))
    if only:
        files = [f for f in files if only in f]
    todo, skip = [], 0
    for f in files:
        p = os.path.join(IMG, f)
        st = os.stat(p)
        c = cache.get(f)
        if c and c.get('_sig') == [int(st.st_mtime), st.st_size] and not force:
            skip += 1
            continue
        todo.append(f)
    print('图库 %d 张；已缓存跳过 %d；待算 %d' % (len(files), skip, len(todo)))
    if not todo:
        print('✅ 没有要算的')
        return 0
    # ⚠ FaceDetectorYN 不是线程安全的：8 个线程共用一个实例 → 519/534 张直接抛异常
    #   （第一版就这么踩了：结果里 519 条 err、剩下几条也是乱数）。改成**每线程一个实例**。
    tls = threading.local()

    def _det():
        d = getattr(tls, 'd', None)
        if d is None:
            d = cv2.FaceDetectorYN.create(MODEL, '', (LONG, LONG), SCORE_MIN, 0.3, 5000)
            tls.d = d
        return d

    t0, done = time.time(), [0]

    def one(f):
        p = os.path.join(IMG, f)
        try:
            r = detect(_det(), p)
        except Exception as e:                      # noqa: BLE001
            return f, {'n': 0, 'big': 0, 'max': 0.0, 'err': str(e)[:60]}
        st = os.stat(p)
        r['_sig'] = [int(st.st_mtime), st.st_size]
        done[0] += 1
        if done[0] % 50 == 0:
            print('   ...%d/%d  %.1f 分钟' % (done[0], len(todo), (time.time() - t0) / 60.0))
        return f, r

    with ThreadPoolExecutor(max_workers=8) as ex:
        for f, r in ex.map(one, todo):
            cache[f] = r
    io.open(OUT, 'w', encoding='utf-8', newline='').write(
        json.dumps(cache, ensure_ascii=False, separators=(',', ':'), sort_keys=True))
    n_face = sum(1 for k, v in cache.items() if v.get('n', 0) >= 1)
    n_big = sum(1 for k, v in cache.items() if v.get('big', 0) >= 1)
    n_crowd = sum(1 for k, v in cache.items()
                  if v.get('n', 0) >= CROWD_MIN and v.get('max', 0) < BIG_RATIO)
    print('完成：%d 张，用时 %.1f 分钟' % (len(todo), (time.time() - t0) / 60.0))
    print('   有脸 %d 张 ／ 人像特写(脸≥2.5%%) %d 张 ／ 人群(≥3 张脸且都很小) %d 张'
          % (n_face, n_big, n_crowd))
    print('   写入 %s' % os.path.basename(OUT))
    return 0


if __name__ == '__main__':
    sys.exit(main())
