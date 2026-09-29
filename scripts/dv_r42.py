# -*- coding: utf-8 -*-
"""第 42 轮验收 · 步骤 1：**我做的 12 条已彻底删除** + 库/图/场景的一致性
（替代原 dv_r37 —— 它的断言主体就是那 12 条，随之作废）
跑法：python scripts/dv_r42.py"""
import io, json, math, os, re, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')
SRC = r'D:\workspace\om3-handbook'
TMP = r'C:\Users\82302\AppData\Local\Temp'
src = io.open(SRC + r'\app\base.html', encoding='utf-8').read()
IMG = SRC + r'\apk\assets\images'
DEC = json.JSONDecoder()
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


print('=== 静态：删除是否干净 ===')
for kw in ('om3lab', 'oLAB', 'id="paneF"', 'id="toc3"', 'data-p="F"', 'OM3LAB-BEGIN', 'OLAB-BEGIN'):
    A(kw not in src, '① 已无残留：%s' % kw)
m = re.search(r'window\.__OM3RECIPES__=', src)
REC, _ = DEC.raw_decode(src, m.start() + len('window.__OM3RECIPES__='))
m2 = re.search(r'var IDX=', src)
IDX, _ = DEC.raw_decode(src, m2.start() + len('var IDX='))
A(len(REC) == 80, '② 配方数 80 条（原站 78 + 日常挂机 + 第 55 轮补的 Porta 400 Print；实测 %d）' % len(REC))
A(len(IDX) == 129, '② 搜索索引 129 条（100 + 10 个候选档槽位 + 第 55 轮补的 19 条；实测 %d）' % len(IDX))
# 三处一致：卡片 / 数据 / 索引
cards = re.findall(r'<div class="card" id="(r-[^"]+)"', src)
A(len(cards) == 77, '② 配方合集卡片 77 张（58 + 第 55 轮补的 19；实测 %d）' % len(cards))
missing = [c for c in cards if not any(x.get('slug') == c[2:] for x in REC)]
A(not missing, '② 每张卡都能在数据里找到（缺 %d）' % len(missing))
A(all(not str(x.get('slug', '')).startswith('om3lab_') for x in REC), '② 数据里已无自设计配方')
A(all(not str(x.get('h', '')).startswith(('r-om3lab_', 'oLAB-')) for x in IDX), '② 索引里已无自设计锚点')
# data-im 体检（第 39 轮那条通用断言，保留）
ims = re.findall(r'data-im="([^"]+)"', src)
A(not [x for x in ims if x.startswith('images/')], '② 没有 data-im 带 images/ 前缀（%d 处）' % len([x for x in ims if x.startswith('images/')]))
miss = sorted(set(x for x in ims if not os.path.exists(os.path.join(IMG, x))))
A(not miss, '② 所有 data-im 的图都在（缺 %d：%s）' % (len(miss), miss[:2]))
# 场景表（21 个场景，不能引用已删锚点）
sc = re.search(r'window\.__OM3SC__\s*=\s*(\[.*?\]);\n', src, re.S)
SC = json.loads(sc.group(1)) if sc else []
A(len(SC) == 18, '③ __OM3SC__ 18 个场景（雨天并入雾/阴天；第 57 轮删了「婚礼聚会 / 儿童亲子」（没实拍 → 改成搜索找风格）；%d）' % len(SC))
bad = [it['i'] for x in SC for it in x['items'] if it['i'].startswith(('r-om3lab_', 'oLAB-')) or it['os'].startswith('oLAB-')]
A(not bad, '③ 场景 slides 不再引用已删锚点（%d 处）' % len(bad))
A(all(len(x['items']) >= 1 for x in SC), '③ 每个场景都 ≥1 条（最少 %d）' % min(len(x['items']) for x in SC))
A(all(os.path.exists(os.path.join(IMG, it['f'])) for x in SC for it in x['items']), '③ 场景 slides 的图全部存在')
# 图库不再有模拟图
sims = [f for f in os.listdir(IMG) if '__sim__' in f or f.startswith('simcheck__')]
A(not sims, '④ 图库里已无模拟预览图（残留 %d）' % len(sims))

print('=== 运行时（页面还能正常跑）===')
JS = r"""
setTimeout(function(){
  var o = [];
  function ok(c, m){ o.push((c ? '[OK ] ' : '[FAIL] ') + m); }
  function vis(id){ var e = document.getElementById(id); return e ? !e.classList.contains('hide') : false; }
  function tab(p){ return document.querySelector('#barABC button[data-p="' + p + '"]'); }
  setTimeout(function(){
    ok(window.__errs.length === 0, '① 首屏 0 JS 报错（' + window.__errs.length + '）');
    tab('B').click();
    setTimeout(function(){
      ok(vis('paneB'), '② 能切到优化版');
      var mt = document.querySelectorAll('#modetabs button');
      ok(mt.length === 10, '② 档位推荐 modetabs 10 个候选档（实测 ' + mt.length + '）');
      ok(!document.getElementById('oLAB'), '② LAB 档已移除');
      tab('A').click();
      setTimeout(function(){
        ok(vis('paneA'), '③ 能切回原版');
        ok(document.querySelectorAll('#paneA .card').length === 77, '③ 配方合集 77 张卡（58 + 第 55 轮补的 19）（' + document.querySelectorAll('#paneA .card').length + '）');
        tab('C').click();
        setTimeout(function(){
          ok(vis('paneC') && !!document.getElementById('scsel'), '④ 场景对比页正常');
          ok(window.__errs.length === 0, '⑤ 全程 0 JS 报错（' + window.__errs.length + '）');
          var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
          document.body.appendChild(d);
        }, 900);
      }, 700);
    }, 900);
  }, 1500);
}, 2600);
"""
k = src.find('<body')
j = src.find('>', k) + 1
head = '<script>window.__OM3_APP__=1;window.__errs=[];window.onerror=function(m,s2,l){window.__errs.push(m+" @"+l)};' \
       'window.addEventListener("unhandledrejection",function(e){window.__errs.push("rej:"+e.reason)});</script>'
out = src[:j] + head + src[j:].replace('</body>', '<script>' + JS + '</script></body>', 1)
p = TMP + r'\dv_r42.html'
io.open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\omr42'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--hide-scrollbars', '--user-data-dir=' + ud, '--window-size=560,900',
                    '--virtual-time-budget=20000', '--dump-dom', 'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
if kk < 0:
    print('  [FAIL] 探针没拿到输出'); F += 1
else:
    body = dom[kk:].split('>', 1)[1].split('</pre>')[0]
    print(body)
    K += body.count('['); F += body.count('[FAIL]')
print()
print('===== 结论：%s（%d 项，失败 %d）=====' % ('全部通过 ✅' if F == 0 else '有 %d 项失败 ❌' % F, K, F))
sys.exit(1 if F else 0)
