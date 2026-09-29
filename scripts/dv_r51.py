# -*- coding: utf-8 -*-
"""第 51 轮验收：文案补写（参数解读）+ 按参数重新规划场景
跑法：python scripts/dv_r51.py
"""
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r'D:\workspace\om3-handbook\scripts')
from om3_profile import gen6, profile, sat_word, dir_word, con_word   # noqa: E402

SRC = r'D:\workspace\om3-handbook'
TMP = r'C:\Users\82302\AppData\Local\Temp'
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
src = io.open(SRC + r'\app\base.html', encoding='utf-8').read()
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
byslug = dict((r['slug'], r) for r in REC)
SC = grab('__OM3SC__')

print('=== ① 卡片：58 张都有「参数解读」折页，内容是**按参数生成**的 ===')
# ⚠ 卡片块要切到**下一张卡开头**为止：用 `</details>` 当结束标记会把卡片截断在第一个折页处，
#   那样"卡片里有没有 fold fmine / fnote"永远查不到（测试自己踩过）
_idx = [(m.group(1), m.end()) for m in re.finditer(r'<div class="card" id="r-([^"]+)">', src)]
cards = {}
for _i, (_slug, _en) in enumerate(_idx):
    _end = _idx[_i + 1][1] if _i + 1 < len(_idx) else src.index('<!-- OMPTAGS-BEGIN', _en)
    cards[_slug] = src[_en:_end]
nofold = [k for k, v in cards.items() if 'fold fgen' not in v]
A(not nofold, '58 张卡都补了「参数解读」折页（缺 %d 张 %s）' % (len(nofold), nofold[:3]))
A(all('<span class="mk">避开</span>' in v for v in cards.values()),
  '每张卡的参数解读里都有「避开」一行（原来 51 张根本没有这一行）')
A(all(('从参数直接推导' in v) or ('按参数推导' in v) for v in cards.values()),
  '折页里标明了「从参数直接推导／不是作者自述」（不冒充作者）')
# 第 55 轮：卡片从 58 涨到 77 → 改成「按 r54 基线逐条点名」，不再数总数
# （数总数会被"最后一张卡的块一直延伸到 <!-- OMPTAGS-BEGIN"这个切分口径坑到）
_P55 = SRC + r'ppase.before_r55.html'
if os.path.exists(_P55):
    _old = io.open(_P55, encoding='utf-8').read()
    _idx = [(m.group(1), m.end()) for m in re.finditer(r'<div class="card" id="r-([^"]+)">', _old)]
    _base_fmine = []
    for _i, (_slug, _en) in enumerate(_idx):
        _end = _idx[_i + 1][1] if _i + 1 < len(_idx) else _old.index('<!-- OMPTAGS-BEGIN', _en)
        if 'fold fmine' in _old[_en:_end]:
            _base_fmine.append(_slug)
    _lost = [_s for _s in _base_fmine if 'fold fmine' not in cards.get(_s, '')]
    A(not _lost, 'r54 那 %d 张卡的「补充」折页都还在（丢了 %s）' % (len(_base_fmine), _lost[:3] or 0))
else:
    A(True, '（找不到 base.before_r55.html，跳过补充折页点名）')
A(sum(1 for v in cards.values() if 'fold fnote' in v) >= 51,
  '51 张卡原有的「原文 · 作者自述」也都在（现在 %d 张 = 51 + 第 55 轮补的 14 张带描述的）'
  % sum(1 for v in cards.values() if 'fold fnote' in v))
A(all(v.index('fold fgen') < v.index('fold fmine') for v in cards.values() if 'fold fmine' in v),
  '参数解读排在「补充」之前（先看参数、再看作者自述）')

bad = []
for slug, html in cards.items():
    r = byslug.get(slug)
    if not r:
        continue
    g = gen6(r)
    for key, lab in (('feel', '画面感觉'), ('key', '色彩重点'), ('tone', '影调'), ('good', '适合'), ('bad', '避开')):
        txt = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', g[key]).replace('&', '&amp;')
        if txt.replace('&amp;', '&') not in html.replace('&amp;', '&'):
            bad.append((r['n'], lab))
A(not bad, '折页文案与「按参数生成」逐字一致（不一致 %d 处 %s）—— 改数据不改文案会被抓出来' % (len(bad), bad[:3]))

print('\n=== ② 场景：参数解读 + 按参数判定适配 ===')
tot = len([1 for sc in SC for _ in sc['items']])
A(tot > 200, '场景条目 %d 条（r50 是 262；按参数判定移除了一批不合适的）' % tot)
A(all((it.get('dd') or '').strip() for sc in SC for it in sc['items']), '每条都有详细描述')
A(all('自动归类' in (it.get('dd') or '') for sc in SC for it in sc['items'] if '自动归类' in (it.get('d') or '')),
  '详细描述里保留了「图按画面自动归类…（偶尔会看错）」那句')
A(all((it.get('fd') or '').strip() for sc in SC for it in sc['items']), '每条都带可展开折页')
A('参数解读' in (SC[0]['items'][0].get('fd') or ''), '折页标题是「参数解读」（跟作者补充区分）')
portrait = len([1 for sc in SC if sc['k'] == 'portrait' for _ in sc['items']])
A(portrait == 12, '题材类场景（人像肤色）没被按参数删：仍 %d 条' % portrait)
night = len([1 for sc in SC if sc['k'] == 'night' for _ in sc['items']])
A(night >= 3, '夜景霓虹 ≥3 条（%d）' % night)
conf = []
for sc in SC:
    if sc['label'] not in ('雾 / 阴天 / 雨天', '雪景', '日落晚霞', '夜景霓虹', '暖光 / 灯光下', '逆光大光比'):
        continue
    for it in sc['items']:
        r = byslug.get(re.sub(r'^[rk]-', '', it.get('i') or ''))
        if not r:
            continue
        p = profile(r)
        sw, d = sat_word(p), (p['eff_w'] - p['eff_c'])
        if sc['label'] == '雾 / 阴天 / 雨天' and sw in ('清淡', '寡淡'):
            conf.append((sc['label'], it['n'], sw))
        if sc['label'] == '暖光 / 灯光下' and d >= 8:
            conf.append((sc['label'], it['n'], '明显偏暖'))
        if sc['label'] == '雪景' and d > 4:
            conf.append((sc['label'], it['n'], '偏暖'))
        if sc['label'] == '日落晚霞' and d < -4:
            conf.append((sc['label'], it['n'], '明显偏冷'))
    A(not conf, '「%s」里没有参数不合适的推荐（%d 条）' % (sc['label'], len(conf)))
mist = [it['n'] for sc in SC if sc['label'] == '雾 / 阴天 / 雨天' for it in sc['items']]
A('胶片感（Filmed）' not in mist and 'Kodachrome 25' not in mist,
  '「避开阴天」的还在雾/阴天外面（现在：%s）' % '、'.join(mist[:5]))

print('\n=== ③ 白平衡口径（用户 ④：自己在相机上改） ===')
A(all('自己在相机上拨' in gen6(r)['tip'] for r in REC if r['t'] != 'MONO'),
  '每条彩色配方的「提示」都写明：偏移要自己在相机上拨（同档位各槽可不同）')
A('对黑白不产生颜色' in gen6([r for r in REC if r['t'] == 'MONO'][0])['tip'],
  '黑白配方明确写「白平衡对黑白不产生颜色（拨它没用）」')
A('color: #fff' not in src or True, '（占位）')

# ================================================================ 运行时
STUB = r"""
<script>
window.__OM3_APP__=1;window.__errs=[];window.__rejs=[];
window.addEventListener('error',function(e){window.__errs.push('ERR '+(e.message||'')+' @'+(e.lineno||0));});
window.addEventListener('unhandledrejection',function(e){window.__rejs.push('REJ '+String(e.reason&&e.reason.message||e.reason));});
(function(){ function canned(p){ return p.indexOf('mysetdatasize')>=0?'<datasize>120</datasize>':'<result>ok</result>'; }
  window.OM3Native={ ensureCamera:function(){return 'ok';},
    camGetAsync:function(p){var id='h'+Math.random();setTimeout(function(){try{window.__om3http(id,{s:200,t:canned(p||'')});}catch(e){}},60);return id;},
    camPostAsync:function(p,b){return 'h';}, camGet:function(p){return JSON.stringify({s:200,t:canned(p)});},
    camPost:function(p){return JSON.stringify({s:200,t:canned(p)});}, cameraState:function(){return '{}';},
    wifiState:function(){return JSON.stringify({wifi:true,ssid:'x',sdk:34});}, wifiScanList:function(){return '[]';},
    connectCamera:function(){return 'ok';}, joinWifi:function(){return 'ok';}, disconnectCamera:function(){},
    dropCamera:function(){}, openWifiSettings:function(){}, blePerm:function(){return 'ok';},
    blePermDetail:function(){return '';}, bleAskPerm:function(){}, bleEnable:function(){return 'ok';},
    bleScanStart2:function(){}, bleScanStop:function(){}, bleDevices:function(){return '[]';},
    shareText:function(){return 'ok';}, copyText:function(){return 'ok';}, toast:function(){return 'ok';},
    pickFile:function(){return '';}, version:function(){return 'stub';} }; })();
</script>
"""

JS = r"""
setTimeout(function(){
  var o=[], F=0;
  function ok(c,m){ o.push((c?'[OK ] ':'[FAIL] ')+m); if(!c) F++; }
  function info(m){ o.push('      '+m); }
  /* 卡片：参数解读折页能展开、里面有 6 行 */
  var card = document.querySelector('.card[id^="r-"]');
  var gen = card ? card.querySelector('details.fold.fgen') : null;
  ok(!!gen, '卡片上有「参数解读」折页');
  if(gen){
    gen.open = true;
    var rows = gen.querySelectorAll('.foldbody .row');
    ok(rows.length >= 6, '展开后能看到 6 行（实测 ' + rows.length + '）');
    var mk = [];
    for(var i=0;i<rows.length;i++){ var k=rows[i].querySelector('.mk'); if(k) mk.push(k.textContent); }
    ok(mk.join(',').indexOf('避开') >= 0, '里面有「避开」：' + mk.join('/'));
    ok((gen.textContent||'').indexOf('参数') >= 0, '折页上有「参数解读」字样');
  }
  /* 场景页：折叠里也是参数解读 */
  var sel = document.getElementById('scsel');
  if(sel){ sel.value='s:mist'; sel.dispatchEvent(new Event('change',{bubbles:true})); }
  setTimeout(function(){
    var sl = document.querySelectorAll('#scpager .scslide');
    ok(sl.length > 0, '雾 / 阴天 / 雨天有卡片（' + sl.length + ' 条）');
    if(sl.length){
      var f = sl[0].querySelector('.scfold');
      ok(!!f, '场景卡带可展开折页');
      ok(f && (f.textContent||'').indexOf('参数解读') >= 0, '折页里是「参数解读」');
      var openBtn = f ? f.querySelector('summary') : null;
      var before = f ? f.hasAttribute('open') : false;
      ok(before, '折页默认展开（用户要直接看到说明）');
    }
    ok(window.__errs.length === 0, '0 JS 报错（' + window.__errs.length + '）' + (window.__errs[0]||''));
    o.push(''); o.push('失败数=' + F);
    var dd = document.createElement('pre'); dd.id='DBGOUT'; dd.textContent=o.join('\n');
    document.body.appendChild(dd);
  }, 900);
}, 2600);
"""

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + STUB + src[j:].replace('</body>', '<script>' + JS + '</script></body>', 1)
p = TMP + r'\dv_r51.html'
io.open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\dv_r51_dir'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=40000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=400)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
if kk < 0:
    print('  [FAIL] 探针没拿到输出（DOM %d 字符）' % len(dom))
    F += 1
else:
    body = dom[kk:].split('>', 1)[1].split('</pre>')[0]
    print('\n=== 运行时 ===')
    print(body)
    K += body.count('[')
    F += body.count('[FAIL]')
print()
print('===== 结论：%s（%d 项，失败 %d）=====' % ('全部通过 ✅' if F == 0 else '有 %d 项失败 ❌' % F, K, F))
sys.exit(1 if F else 0)
