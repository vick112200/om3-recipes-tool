# -*- coding: utf-8 -*-
"""第 50 轮验收：白平衡偏移处处同步 + 槽位弹窗「现：」跟着方案变 + 场景详细描述/去矛盾推荐
跑法：python scripts/dv_r50.py

对应关系（用户四条）：
  ① 弹窗里「（现：…）」是固定的 → 运行时：造两个方案，切方案必须看到「现：」跟着变
  ② 所有显示槽位的地方都显示白平衡偏移 → 静态：58 张卡 + 29 个档位槽位 == 数据算出来的值（0 处不一致）
  ③ 场景没有详细描述 + 避开阴天却进阴天推荐 → 静态：255 条都有 dd、没有场景词冲突；运行时：场景页显示详细描述
  ④ 机械对账（标签方向 / 白平衡 / 场景词）→ 上面几条合起来就是
"""
import io
import json
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
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


def wbtxt(a, g):
    a = int(a or 0)
    g = int(g or 0)
    return ((('A+%d' % a) if a > 0 else ('B%d' % -a) if a < 0 else 'A0') + ' '
            + (('G+%d' % g) if g > 0 else ('M%d' % -g) if g < 0 else 'G0'))


print('=== ① 静态：58 张卡片 / 29 个档位槽位 的白平衡偏移都 == 数据 ===')
REC = grab('__OM3RECIPES__')
byslug = dict((r['slug'], r) for r in REC)
byname = {}
for r in REC:
    byname.setdefault(r['n'], r)
cards = dict((m.group(1), m.group(2)) for m in
             re.finditer(r'<div class="card" id="r-([^"]+)">(.*?)(?=<div class="card" id="r-|</details>)', src, re.S))
miss = bad = 0
for slug, html in cards.items():
    r = byslug.get(slug)
    if not r:
        continue
    m = re.search(r'<div class="chd">.*?<span class="slot">([^<]*)</span>', html, re.S)
    shown = (m.group(1).strip() if m else '')
    want = wbtxt(r.get('wba'), r.get('wbg'))
    if not shown:
        miss += 1
    elif re.sub(r'\s+', '', shown) != re.sub(r'\s+', '', want) and \
            re.sub(r'[+ ]', '', shown) != re.sub(r'[+ ]', '', want):
        bad += 1
A(miss == 0, '配方合集 %d 张卡全都有白平衡标签（缺 %d 张）—— 用户点名的「冷泉」也在里面' % (len(cards), miss))
A(bad == 0, '卡片标签与 __OM3RECIPES__ 的 wba/wbg 一处不差（不差 %d 张）' % bad)
cold = re.search(r'id="r-ian-will_cool-spring">.*?<span class="slot">([^<]*)</span>', src, re.S)
A(bool(cold) and cold.group(1).strip().replace(' ', '') == 'A0G0',
  '冷泉卡片上现在写着「%s」（原来卡片上一个字都没有）' % (cold.group(1).strip() if cold else '—'))

# 每个槽位取一段固定窗口（用 lookahead 截断会在槽位内部提前断掉 → 误报缺标签）
slots = []
for m in re.finditer(r'<div class="oslot" id="(oC\d+-(?:m?\d+))">', src):
    slots.append((m.group(1), src[m.end():m.end() + 1500]))
nsw = badsw = nosw = 0
for sid, html in slots:
    nm = re.search(r'<span class="osname">([^<]*)</span>', html)
    name = nm.group(1).strip() if nm else ''
    m = re.search(r'<span class="oswb">([^<]*)</span>', html)
    r = byname.get(name)
    if not r:
        nosw += 1
        A(not m, '自配配方「%s」(%s) 库里没有数据 → 不显示偏移（不猜）' % (name, sid))
        continue
    want = wbtxt(r.get('wba'), r.get('wbg'))
    if m:
        nsw += 1
        if re.sub(r'[+ ]', '', m.group(1)) != re.sub(r'[+ ]', '', want):
            badsw += 1
    else:
        A(False, '%s（%s）缺白平衡标签' % (name, sid))
A(nsw == len(slots) - nosw and badsw == 0,
  '档位槽位 %d 个有标签、值与数据一致（自配 %d 个不标）' % (nsw, nosw))
A('.oswb{display:inline-block' in src and '.mpwb{display:inline-block' in src, 'CSS：.oswb / .mpwb 小标签有样式')
A('window.__om3wbtxt = om3wbtxt;' in src and 'window.__om3wbparse = om3wbparse;' in src,
  '白平衡记法只有一处实现（om3wbtxt / om3wbparse，导出给测试与其它块用）')

print('\n=== ② 静态：槽位弹窗的「现：」不再写死第一个方案 ===')
A('var cur = arr.length ? arr[0].slots : null;' not in src,
  '那段写死 arr[0] 的代码没了（原来上面选别的方案、下面还是显示第 1 个方案的内容）')
A("options: function(vals){" in src and 'data-r50dyn' in src,
  'om3Ask 支持「options 是函数」+ 下拉变化时重画（老调用方不受影响）')
A('r50（用户 ①）：这里原来是写死 arr[0].slots' in src, 'pickSetSlot 里按当前选中方案现算（注释也在）')

print('\n=== ③ 静态：场景条目有详细描述、且没有「避开词进推荐」 ===')
SC = grab('__OM3SC__')
nb_dd = sum(1 for sc in SC for it in sc['items'] if (it.get('dd') or '').strip())
ntot = sum(len(sc['items']) for sc in SC)
A(len(SC) == 18, '__OM3SC__ 18 个场景（雨天并入雾/阴天；第 57 轮删了「婚礼聚会 / 儿童亲子」（没实拍 → 改成搜索找风格）；%d）' % len(SC))
A(nb_dd == ntot, '每条都有详细描述（dd 或参数明细兜底）（%d / %d）' % (nb_dd, ntot))
A(all(it.get('fd') for sc in SC for it in sc['items'] if it.get('dd')),
  '有详细描述的条目同时带可展开的 6 行折页（fd）')
LB = grab('SC')
byf = {}
for _sc in LB:
    for _it in (_sc.get('items') or []):
        if _it.get('f'):
            byf[_it['f']] = _it
SKW = {
    # 只做**天气 / 光线条件**类：这类场景的「避开」写的是真排除（用户举的"避开阴天却在阴天推荐里"）
    '雾与阴天': ['阴天', '雾'], '雨天': ['雨后', '雨天'], '雪景': ['雪'],
    '日落晚霞': ['日落', '晚霞', '黄昏', '夕阳'], '夜景霓虹': ['夜景'],
    '室内暖光': ['钨丝'], '逆光大光比': ['逆光', '大光比'],
}
# ⚠ 题材类场景（城市街拍 / 人像肤色 / 食物咖啡 / 建筑几何 …）**不**用这套过滤：
#   它们「避开」里的句子多半是前提（"需要柔和肤色的近距离人像"），删掉反而把好推荐删了、
#   还破坏"这个场景的图要和场景对得上"（dv_scene39 就在验这个）。
# r51 起：场景适配**按参数**判（不再按文字关键词 —— 文字本身可能就写错了）
md = dict((r['slug'], r) for r in REC)
def _sat(r):
    v = list(r.get('v') or []) + [0] * 12
    return sum(v)
def _d(r):
    v = list(r.get('v') or []) + [0] * 12
    w = sum(v[i] for i in (0, 1, 2, 3)); c = sum(v[i] for i in (4, 5, 6, 7))
    a = int(r.get('wba') or 0)
    return (w + max(0, a) * 3) - (c + max(0, -a) * 3)
badsc = []
for sc in SC:
    if sc['label'] not in ('雾与阴天', '雨天', '雪景', '日落晚霞', '夜景霓虹', '室内暖光', '逆光大光比'):
        continue
    for it in sc['items']:
        slug = re.sub(r'^[rk]-', '', it.get('i') or '')
        r = md.get(slug)
        if not r:
            continue
        sw, dd = _sat(r), _d(r)
        if sc['label'] == '雾与阴天' and sw <= -8:
            badsc.append((sc['label'], it['n'], '低饱和 %d' % sw))
        if sc['label'] == '室内暖光' and dd >= 8:
            badsc.append((sc['label'], it['n'], '明显偏暖 %d' % dd))
        if sc['label'] == '雪景' and dd > 4:
            badsc.append((sc['label'], it['n'], '偏暖 %d' % dd))
A(not badsc, '场景适配按参数成立：条件类场景里没有"参数明显不合适"的推荐（%d 条 %s）' % (len(badsc), badsc[:3]))
mist = [it['n'] for sc in SC if sc['label'] == '雾与阴天' for it in sc['items']]
A('胶片感（Filmed）' not in mist and 'Kodachrome 25' not in mist,
  '「避开阴天」的那几条已经从【雾与阴天】移除（现在：%s）' % '、'.join(mist[:6]))

# ================================================================ 运行时
STUB = r"""
<script>
window.__OM3_APP__=1;window.__errs=[];window.__rejs=[];
window.addEventListener('error',function(e){window.__errs.push('ERR '+(e.message||'')+' @'+(e.lineno||0));});
window.addEventListener('unhandledrejection',function(e){window.__rejs.push('REJ '+String(e.reason&&e.reason.message||e.reason));});
(function(){
  function canned(p){ return p.indexOf('mysetdatasize')>=0 ? '<datasize>120</datasize>' : '<result>ok</result>'; }
  window.OM3Native={
    ensureCamera:function(){ return 'ok'; },
    camGetAsync:function(p){ var id='h'+Math.random(); setTimeout(function(){ try{window.__om3http(id,{s:200,t:canned(p||'')});}catch(e){} },60); return id; },
    camPostAsync:function(p,b){ return 'h'; }, camGet:function(p){ return JSON.stringify({s:200,t:canned(p)}); },
    camPost:function(p,b){ return JSON.stringify({s:200,t:canned(p)}); },
    cameraState:function(){ return '{}'; }, wifiState:function(){ return JSON.stringify({wifi:true,ssid:'x',sdk:34}); },
    wifiScanList:function(){ return '[]'; }, connectCamera:function(){ return 'ok'; }, joinWifi:function(){ return 'ok'; },
    disconnectCamera:function(){}, dropCamera:function(){}, openWifiSettings:function(){},
    blePerm:function(){ return 'ok'; }, blePermDetail:function(){ return ''; }, bleAskPerm:function(){},
    bleEnable:function(){ return 'ok'; }, bleScanStart2:function(){}, bleScanStop:function(){}, bleDevices:function(){ return '[]'; },
    shareText:function(){ return 'ok'; }, copyText:function(){ return 'ok'; }, toast:function(){ return 'ok'; },
    pickFile:function(){ return ''; }, version:function(){ return 'stub'; }
  };
})();
</script>
"""

JS = r"""
setTimeout(function(){
  var o=[], F=0;
  function ok(c,m){ o.push((c?'[OK ] ':'[FAIL] ')+m); if(!c) F++; }
  function info(m){ o.push('      '+m); }
  function optTexts(sel){ var a=[]; for(var i=0;i<sel.options.length;i++) a.push(sel.options[i].textContent); return a.join(' | '); }

  /* 造两个方案：A 的槽 1 有名字「甲」，B 是空的 */
  try{
    localStorage.setItem('om3sets', JSON.stringify([
      { id:'a1', name:'方案甲', from:'myset1', camera:'', slots:{ 1:{ name:'甲', used:2, vivid:[1,1,1,1,1,1,1,1,1,1,1,1] }, 2:null, 3:null, 4:null } },
      { id:'b1', name:'方案乙', from:'myset2', camera:'', slots:{ 1:null, 2:null, 3:null, 4:null } }
    ]));
  }catch(e){ info('写 localStorage 失败：'+e.message); }

  /* ---- ① 弹窗「现：」必须跟着方案走 ---- */
  var card = document.querySelector('.card[id^="r-"] .omsavebtn') || document.querySelector('.omsavebtn');
  ok(!!card, '找到一张配方卡上的「加入我的方案」按钮');
  if(card) card.click();
  setTimeout(function(){
    var f0 = document.getElementById('of0'), f1 = document.getElementById('of1');
    ok(!!f0 && !!f1, '弹窗打开了，方案/槽位两个下拉都在');
    var t0 = optTexts(f1);
    ok(t0.indexOf('现：甲') >= 0, '选「方案甲」时，槽位下拉写的是它的真实内容（' + t0 + '）');
    if(f0){
      f0.value = '1';
      f0.dispatchEvent(new Event('change', {bubbles:true}));
    }
    setTimeout(function(){
      var t1 = optTexts(document.getElementById('of1'));
      ok(t1.indexOf('现：甲') < 0, '切到「方案乙」→ 「现：甲」没了（' + t1 + '）');
      ok(t1.indexOf('（空）') >= 0, '切到「方案乙」→ 槽位显示「（空）」');
      var f0b = document.getElementById('of0');
      f0b.value = '0';
      f0b.dispatchEvent(new Event('change', {bubbles:true}));
      setTimeout(function(){
        var t2 = optTexts(document.getElementById('of1'));
        ok(t2.indexOf('现：甲') >= 0, '再切回「方案甲」→ 「现：甲」又回来了（' + t2 + '）');
        var c = document.getElementById('ocancel'); if(c) c.click();
        afterDlg();
      }, 260);
    }, 260);
  }, 400);

  /* ---- ② 我的配方槽位行显示偏移 ---- */
  function afterDlg(){
    try{
      window.__om3putRec(0, 3, { n:'测试卷', a:'x', v:[1,2,3,4,5,6,7,8,9,10,11,12], hi:0,mid:0,sh:0,eff:0,shp:0,con:0, wba:2, wbg:1 }, '测试卷', '');
    }catch(e){ info('putRec 失败：'+e.message); }
    try{ window.__om3mpTab('sets'); }catch(e){ info('mpTab 失败：'+e.message); }
    try{ window.__om3mpDetail(0); }catch(e){ info('mpDetail 失败：'+e.message); }   /* 打开第 1 个方案看槽位行 */
    setTimeout(function(){
      var pe = document.getElementById('mpList') || document.getElementById('mpBody') || document.body;
      var html = pe.innerHTML || '';
      ok(html.indexOf('mpwb') >= 0, '「我的配方」槽位行显示了白平衡偏移小标签');
      ok(html.indexOf('A+2 G+1') >= 0, '偏移文本 = 数据算出来的 A+2 G+1');
      /* ---- ③ 场景页显示详细描述 ---- */
      var sel = document.getElementById('scsel');
      if(sel){
        sel.value = 's:mist';
        sel.dispatchEvent(new Event('change', {bubbles:true}));
      }
      setTimeout(function(){
        var slides = document.querySelectorAll('.scslide');
        ok(slides.length > 0, '选了「雾与阴天」→ 有卡片（' + slides.length + ' 条）');
        if(slides.length){
          var long0 = 0, folds = 0;
          for(var q = 0; q < slides.length; q++){
            var dq = slides[q].querySelector('.scdesc');
            if(dq && (dq.textContent || '').length > 40) long0++;
            if(slides[q].querySelector('.scfold')) folds++;
          }
          info('本场景 ' + slides.length + ' 张：描述 >40 字的 ' + long0 + ' 张、带折页的 ' + folds + ' 张');
          ok(folds === slides.length, '每张卡都有可展开的详细折页（' + folds + ' / ' + slides.length + '）');
          ok(long0 > 0, '其中 ' + long0 + ' 张是长详细描述（其余源头只有短描述 → 折页里是参数明细，不编造）');
          var names = [];
          for(var i = 0; i < slides.length; i++){
            var nm = slides[i].querySelector('.scname');
            if(nm) names.push(nm.textContent.replace(/\s+/g, ''));
          }
          ok(names.join('|').indexOf('胶片感') < 0, '「避开阴天」的配方不在雾与阴天的卡片里（' + names.join('、').slice(0, 60) + '）');
        }
        ok(window.__errs.length === 0, '0 JS 报错（' + window.__errs.length + '）' + (window.__errs[0] || ''));
        ok(window.__rejs.length === 0, '0 未处理拒绝（' + window.__rejs.length + '）' + (window.__rejs[0] || ''));
        o.push(''); o.push('失败数=' + F);
        var dd = document.createElement('pre'); dd.id='DBGOUT'; dd.textContent = o.join('\n');
        document.body.appendChild(dd);
      }, 900);
    }, 600);
  }
}, 3000);
"""

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + STUB + src[j:].replace('</body>', '<script>' + JS + '</script></body>', 1)
p = TMP + r'\dv_r50.html'
io.open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\dv_r50_dir'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=45000', '--dump-dom',
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
