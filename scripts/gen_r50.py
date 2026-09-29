# -*- coding: utf-8 -*-
"""第 50 轮生成器（幂等）· v3.4

用户 2026-09-25 四条：
  ① 放入我的槽位的弹窗里「（现：…）」是固定的、不是实际选中的方案 → 真 bug（写死 arr[0]）
  ② 所有显示槽位的地方都要同步显示白平衡偏移（配方合集 / 档位推荐 / 场景对比…）；有一处标了、别处没标不一致
     （用户点名「冷泉」：卡片上压根没标，只有档位 C4 标题写了 A0 G0）
  ③ 场景对比新加的场景都没有详细描述 + 「避开阴天」的还被推荐进阴天场景
  ④ 全面对账描述与特点（本轮做机械可验的部分）

体检结论（scripts/om3_audit_data.py + 临时探针）：
  · 58 张卡片里 40 张没有白平衡标签；31 个档位槽位一个都没有（页面里没有 .oswb 元素）
  · 291 条场景条目全部没有详细描述（__OM3SC__ 里没有 dd/fd，而场景页渲染 it.dd || it.d）
    但 window.SC（按照片存的那份）289 张照片全都有 dd/fd/fs/pb/ps，246/291 能对上
  · 场景关键词出现在配方「避开」里的：42 条

本脚本 7 处（幂等；用只属于新代码的短标记判定）：
  A. 块09 om3Ask：支持「options 是函数」——下拉能跟着别的字段变（老调用方一行不改）
  B. 块07 pickSetSlot：那个「现：」按**当前选中的方案**算（bug 修）
  C. 标记：40 张卡片补 <span class="slot">偏移</span>（数据来自 __OM3RECIPES__.wba/wbg）
  D. 标记：31 个档位槽位补 <span class="oswb">偏移</span>
  E. CSS：.oswb / .mpwb 两个小标签样式
  F. 块07：白平衡记法的唯一实现（om3wbtxt / om3wbparse）+ 槽位存偏移 + 我的配方槽位行显示偏移
  G. 数据：__OM3SC__ 的条目按 window.SC 补 dd/fd/fs/pb/ps；并按「场景词出现在『避开』里 → 移除」过滤
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
P = os.path.join(ROOT, 'app', 'base.html')
LOG = []
s = io.open(P, encoding='utf-8').read()
bak = os.path.join(ROOT, 'app', 'base.before_r50.html')
if not os.path.exists(bak):
    io.open(bak, 'w', encoding='utf-8', newline='').write(s)
    print('回退点已存：app/base.before_r50.html（= v3.3 源码）')


def rep(old, new, tag, marker):
    global s
    if marker in s:
        LOG.append('  · 已改过，跳过：' + tag)
        return
    n = s.count(old)
    if n != 1:
        raise SystemExit('锚点不唯一(%d)：%s' % (n, tag))
    s = s.replace(old, new)
    LOG.append('  ✓ ' + tag)


def grab(var, start=0):
    i = s.index('window.%s' % var, start)
    j = s.index('=', i) + 1
    while s[j] in ' \n':
        j += 1
    oc = s[j]
    cc = {'[': ']', '{': '}'}[oc]
    d = 0
    k = j
    while k < len(s):
        if s[k] == '"':
            k += 1
            while k < len(s):
                if s[k] == chr(92):
                    k += 2
                    continue
                if s[k] == '"':
                    break
                k += 1
        elif s[k] == oc:
            d += 1
        elif s[k] == cc:
            d -= 1
            if d == 0:
                return json.loads(s[j:k + 1]), j, k + 1
        k += 1
    raise SystemExit('抠不出来：' + var)


def wbtxt(a, g):
    """站点记法：A+n / B|n|（琥珀-蓝）· G+n / M|n|（绿-品红）；0 写 A0 / G0。"""
    a = int(a or 0)
    g = int(g or 0)
    return ((('A+%d' % a) if a > 0 else ('B%d' % -a) if a < 0 else 'A0') + ' '
            + (('G+%d' % g) if g > 0 else ('M%d' % -g) if g < 0 else 'G0'))


REC, _, _ = grab('__OM3RECIPES__')
byslug = dict((r['slug'], r) for r in REC)
byname = {}
for r in REC:
    byname.setdefault(r['n'], r)

# ================================================================ A. om3Ask 支持动态 options
rep(
    """      fields.forEach(function(f, i){
        hasInput = true;
        var id = 'of' + i;
        var lb = document.createElement('label');
        lb.textContent = f.label || ('输入 ' + (i + 1));
        var el;
        if(f.options && f.options.length){""",
    """      /* r50：字段的 options 允许是**函数** —— 拿到"前面字段当前的值"再算选项（「放进哪个槽位」那份
         下拉要跟着上面选的**方案**变）。只有传函数时才走新逻辑，老调用方（静态 options）行为完全不变。 */
      function r50vals(upTo){
        var out = [];
        for(var q = 0; q < fields.length; q++){
          var e0 = (q < upTo) ? $('of' + q) : null;
          out.push(e0 ? e0.value : (fields[q].value === undefined ? '' : String(fields[q].value)));
        }
        return out;
      }
      function r50opts(f, upTo){
        return (typeof f.options === 'function') ? (f.options(r50vals(upTo)) || []) : (f.options || []);
      }
      fields.forEach(function(f, i){
        hasInput = true;
        var id = 'of' + i;
        var lb = document.createElement('label');
        lb.textContent = f.label || ('输入 ' + (i + 1));
        var el;
        var fopts = r50opts(f, i);
        if(fopts && fopts.length){""",
    'A1：om3Ask 支持 options 函数（先按"前面已渲染字段的值"算一次）',
    'function r50vals(upTo){'
)

rep(
    """          el = document.createElement('select');
          f.options.forEach(function(o){
            var op = document.createElement('option');
            op.value = String(o.value);
            op.textContent = o.label || String(o.value);
            if(String(o.value) === String(f.value)) op.selected = true;
            el.appendChild(op);
          });""",
    """          el = document.createElement('select');
          el.setAttribute('data-r50dyn', (typeof f.options === 'function') ? '1' : '0');
          fopts.forEach(function(o){
            var op = document.createElement('option');
            op.value = String(o.value);
            op.textContent = o.label || String(o.value);
            if(String(o.value) === String(f.value)) op.selected = true;
            el.appendChild(op);
          });""",
    'A2：下拉上打一个"动态选项"标记（后面按它重画）',
    "el.setAttribute('data-r50dyn'"
)

rep(
    """      var ok = $('ook'), cancel = $('ocancel');
      ok.textContent = opt.okText || '确定';""",
    """      /* r50：有人用了动态 options → 任意下拉一变，就把「动态那几个字段」按最新的值重画一遍
         （保留用户已经选的槽号；老调用方没有动态字段，这段等于不跑）。 */
      if(fields.some(function(f){ return typeof f.options === 'function'; })){
        box.querySelectorAll('select').forEach(function(srcEl){
          srcEl.addEventListener('change', function(){
            var srcIdx = Number(String(srcEl.id).replace('of', '')) || 0;
            var vals = r50vals(fields.length);
            for(var i = 0; i < fields.length; i++){
              var f = fields[i];
              if(typeof f.options !== 'function') continue;
              var el = $('of' + i);
              if(!el) continue;
              var prev = (i === srcIdx) ? el.value : el.value;   /* 尽量留住用户原来的选择 */
              var opts = f.options(vals) || [];
              el.innerHTML = '';
              opts.forEach(function(o){
                var op = document.createElement('option');
                op.value = String(o.value);
                op.textContent = o.label || String(o.value);
                el.appendChild(op);
              });
              var keep = false;
              for(var z = 0; z < opts.length; z++) if(String(opts[z].value) === String(prev)) keep = true;
              if(keep) el.value = prev;
              else if(opts.length) el.value = String(opts[0].value);
              vals[i] = el.value;
            }
          });
        });
      }
      var ok = $('ook'), cancel = $('ocancel');
      ok.textContent = opt.okText || '确定';""",
    'A3：下拉变化 → 动态字段重画（保留选择）',
    "box.querySelectorAll('select').forEach(function(srcEl){"
)

# ================================================================ B. pickSetSlot 的「现：」跟着方案变
rep(
    """        { label: '放进哪个槽位', options: (function(){
            /* 槽位下拉里顺便显示每格现在放着什么，避免糊里糊涂覆盖别人 */
            var cur = arr.length ? arr[0].slots : null;
            return [1, 2, 3, 4].map(function(n){
              var o1 = cur && cur[n];
              var tag = o1 ? ('（现：' + (o1.name || (o1.used ? '有数据' : '空')) + '）') : '（空）';
              return { value: String(n), label: '槽 ' + n + tag };
            });
          })(),
          value: String(sgSlot) },""",
    """        { label: '放进哪个槽位',
          /* r50（用户 ①）：这里原来是写死 arr[0].slots —— 上面换成别的方案，下面「（现：…）」还是
             第 1 个方案的内容（看着就是"固定的、不是实际的"）。现在按**当前选中的方案**现算。 */
          options: function(vals){
            var si2 = Number(vals && vals[0]);
            var cur = (isFinite(si2) && arr[si2]) ? arr[si2].slots : null;
            return [1, 2, 3, 4].map(function(n){
              var o1 = cur && cur[n];
              var tag = (cur && o1) ? ('（现：' + (o1.name || (o1.used ? '有数据' : '空')) + '）')
                                    : (cur ? '（空）' : '（新方案）');
              return { value: String(n), label: '槽 ' + n + tag };
            });
          },
          value: String(sgSlot) },""",
    'B：pickSetSlot 的「现：…」按当前方案算（用户 ① 的 bug）',
    'r50（用户 ①）：这里原来是写死 arr[0].slots'
)

# ================================================================ C. 40 张卡片补白平衡标签
ncard = 0
for slug, r in byslug.items():
    m = re.search(r'(<div class="card" id="r-%s">.*?<div class="chd">)' % re.escape(slug), s, re.S)
    if not m:
        continue
    seg = s[m.end():m.end() + 400]
    if '<span class="slot">' in seg:
        continue
    want = wbtxt(r.get('wba'), r.get('wbg'))
    cn = re.search(r'(<span class="cname">(?:[^<]*)</span>)', seg)
    if not cn:
        continue
    at = m.end() + cn.end()
    s = s[:at] + '<span class="slot">' + want + '</span>' + s[at:]
    ncard += 1
LOG.append('  ✓ C：%d 张卡片补上白平衡标签' % ncard)

# ================================================================ D. 31 个档位槽位补 oswb
nslot = nskip = 0
# ⚠ 必须**从后往前**插：先 list 再逐个插入会让后面 match 的偏移失效（会把标签插进 </span> 中间）
for m in list(reversed(list(re.finditer(r'(<div class="oslot" id="oC\d+-(?:m?\d+)">)(.*?)(?=<div class="oslot" id="|</div></div></div>)', s, re.S)))):
    head, html = m.group(1), m.group(2)
    if 'class="oswb"' in html:
        continue
    nm = re.search(r'<span class="osname">([^<]*)</span>', html)
    if not nm:
        continue
    r = byname.get(nm.group(1).strip())
    if not r:                     # 自配配方（白里透红…）：库里没有 → 不猜，不标
        nskip += 1
        continue
    want = wbtxt(r.get('wba'), r.get('wbg'))
    au = re.search(r'(<span class="osauth">(?:[^<]*)</span>)', html)
    if not au:
        continue
    base = m.start(2)
    at = base + au.end()
    s = s[:at] + '<span class="oswb">' + want + '</span>' + s[at:]
    nslot += 1
LOG.append('  ✓ D：%d 个档位槽位补上白平衡标签（库里没有的 %d 个跳过：不猜）' % (nslot, nskip))

# ================================================================ E. CSS
rep(
    '/* 扫码诊断行：卡在哪一步',
    '/* r50：白平衡偏移小标签（配方卡 / 档位槽位 / 我的配方槽位行共用一套） */\n'
    '.oswb{display:inline-block;margin-left:8px;padding:1px 7px;border-radius:999px;'
    'background:#16303a;border:1px solid #2b6b7a;color:#8fd8c2;font-size:11.5px;font-weight:700;vertical-align:middle}\n'
    '.mpwb{display:inline-block;margin-left:8px;padding:1px 7px;border-radius:999px;'
    'background:#16303a;border:1px solid #2b6b7a;color:#8fd8c2;font-size:11.5px;font-weight:700}\n'
    '/* 扫码诊断行：卡在哪一步',
    'E：白平衡小标签样式',
    '.oswb{display:inline-block'
)

# ================================================================ F. JS：唯一记法 + 存/显偏移
rep(
    "  function putRecInSlot(setIdx, slot, rec, nm, desc, rich){",
    "  /* r50：白平衡偏移的**唯一**记法（全站共用）：A+n / B|n|（琥珀-蓝）· G+n / M|n|（绿-品红），0 写 A0 / G0。\n"
    "     数据源永远是 __OM3RECIPES__ 的 wba/wbg —— 页面各处不再各写一份（用户 ②：有的地方标、有的地方不标）。 */\n"
    "  function om3wbtxt(a, g){\n"
    "    if(a === null || a === undefined || g === null || g === undefined) return '';\n"
    "    a = Number(a) || 0; g = Number(g) || 0;\n"
    "    return (a > 0 ? ('A+' + a) : (a < 0 ? ('B' + (-a)) : 'A0')) + ' '\n"
    "         + (g > 0 ? ('G+' + g) : (g < 0 ? ('M' + (-g)) : 'G0'));\n"
    "  }\n"
    "  /* 反过来：把页面上的「A+2 G+1 / A0 G0 / B5 G+7 / A+4 M1」解析回 {a,g}（档位槽位卡上就写着这个） */\n"
    "  function om3wbparse(t){\n"
    "    var str = String(t || '');\n"
    "    var ma = /(?:^|[\\s（(])([AB])\\s*\\+?\\s*(\\d+)/.exec(str);\n"
    "    var mg = /(?:^|[\\s（(])([GM])\\s*\\+?\\s*(\\d+)/.exec(str);\n"
    "    if(!ma && !mg) return null;\n"
    "    return { a: ma ? ((ma[1] === 'A' ? 1 : -1) * Number(ma[2])) : null,\n"
    "             g: mg ? ((mg[1] === 'G' ? 1 : -1) * Number(mg[2])) : null };\n"
    "  }\n"
    "  window.__om3wbtxt = om3wbtxt;\n"
    "  window.__om3wbparse = om3wbparse;\n"
    "  function putRecInSlot(setIdx, slot, rec, nm, desc, rich){",
    'F1：om3wbtxt / om3wbparse（唯一实现）+ 导出',
    'window.__om3wbtxt = om3wbtxt;'
)

rep(
    "                con: rec ? rec.con : 0, name: name, desc: desc || '' };",
    "                con: rec ? rec.con : 0, name: name, desc: desc || '',\n"
    "                /* r50：白平衡偏移也存下来（我的配方里要显示；库里没有就存 null，不猜） */\n"
    "                wba: rec ? (rec.wba === undefined ? null : rec.wba) : null,\n"
    "                wbg: rec ? (rec.wbg === undefined ? null : rec.wbg) : null,\n"
    "                wb: rec ? (rec.wb || '') : '' };",
    'F2：putRecInSlot 存 wba/wbg',
    'wba: rec ? (rec.wba === undefined ? null : rec.wba) : null,'
)

rep(
    "            '　<span style=\"font-weight:400;color:#9aa3a2;font-size:12.5px\">' + tierLabelSafe(srcTier) + ' · 槽' + n + '</span></div>' +",
    "            '　<span style=\"font-weight:400;color:#9aa3a2;font-size:12.5px\">' + tierLabelSafe(srcTier) + ' · 槽' + n + '</span>' +\n"
    "            /* r50：这一格的白平衡偏移（配方库里带过来的；没有就不显示） */\n"
    "            (one && om3wbtxt(one.wba, one.wbg) ? ('<span class=\"mpwb\">' + om3wbtxt(one.wba, one.wbg) + '</span>') : '') + '</div>' +",
    'F3：我的配方槽位行显示白平衡偏移',
    'class="mpwb">'
)

# F4：档位槽位上的偏移 → 解析进 rec（这样「整个档位存入我的配方」也带着偏移过去）
rep(
    "      var bs = el.querySelectorAll('.osvals .ovc b'), v = [];\n",
    "      /* r50：槽位卡上那个白平衡小标签（.oswb）→ {wba,wbg}，跟着配方一起进「我的配方」 */\n"
    "      var wba0 = null, wbg0 = null;\n"
    "      try{\n"
    "        var wbe = el.querySelector ? el.querySelector('.oswb') : null;\n"
    "        if(wbe && window.__om3wbparse){\n"
    "          var wp = window.__om3wbparse(wbe.textContent);\n"
    "          if(wp){ wba0 = (wp.a === null ? 0 : wp.a); wbg0 = (wp.g === null ? 0 : wp.g); }\n"
    "        }\n"
    "      }catch(e){ om3err(e, \"silent\"); }\n"
    "      var bs = el.querySelectorAll('.osvals .ovc b'), v = [];\n",
    'F4a：recFromOslot 读槽位卡上的偏移',
    'wba0 = (wp.a === null ? 0 : wp.a)'
)

rep(
    "               con: num47(pick47(t, /对比\\s*([+-]?\\d+)/)) };",
    "               con: num47(pick47(t, /对比\\s*([+-]?\\d+)/)),\n"
    "               /* r50：偏移从槽位卡上的 .oswb 来（没有就是 null，不猜） */\n"
    "               wba: wba0, wbg: wbg0 };",
    'F4b：recFromOslot 返回 wba/wbg',
    'wba: wba0, wbg: wbg0 };'
)

# ================================================================ G. 场景数据：补详细描述 + 去矛盾推荐
SC, scj1, scj2 = grab('__OM3SC__')
i0 = s.index('window.__OM3SC__')          # ⚠ 赋值起点要自己找：不能拿 scj1 往前减（会把 window.__OM3SC__ 切坏）
LB, _, _ = grab('SC')
byf = {}
for _sc in LB:
    for _it in (_sc.get('items') or []):
        if _it.get('f'):
            byf[_it['f']] = _it
# 卡片（按照片对不上时的兜底来源：卡片里就有那 6 行折页）
CARDS = {}
for _m in re.finditer(r'<div class="card" id="r-([^"]+)">(.*?)(?=<div class="card" id="r-|</details>)', s, re.S):
    CARDS[_m.group(1)] = _m.group(2)


def card_detail(slug):
    """从卡片里抠出与 window.SC 同构的 dd/fd/fs/pb（照片对不上时用；不新写内容）"""
    h = CARDS.get(slug)
    if not h:
        return None
    m = re.search(r'<details class="fold fmine">.*?<div class="foldbody">(.*?)</div></details>', h, re.S)
    if not m:
        return None
    rows = m.group(1)
    def cell(mk):
        r = re.search(r'<span class="mk">' + mk + r'</span><span class="mv[^"]*">(.*?)</span>', rows, re.S)
        return re.sub(r'<[^>]+>', '', r.group(1)).strip() if r else ''
    feel, key = cell('画面感觉'), cell('色彩重点')
    if not feel:
        return None
    prm = re.search(r'<div class="params">(.*?)</div>', h, re.S)
    prm_t = re.sub(r'<[^>]+>', ' ', prm.group(1)) if prm else ''
    prm_t = re.sub(r'\s+', ' ', prm_t).replace(' ｜ ', ' ｜ ').strip()
    return {'dd': (feel + ('。' + key if key else '')),
            'fd': rows,
            'fs': '补充 · 画面感觉：' + (feel[:40] + '…' if len(feel) > 40 else feel),
            'pb': ('<div class="row"><span class="mk">参数</span><span class="mv">' + prm_t + '</span></div>') if prm_t else ''}


# 场景词（**克制**的子集：只用场景名本身/明确条件；不用"灯光"这种会把"避开室内钨丝灯"误判成"避开夜景灯光"的词）
SKW = {
    # 只做**天气 / 光线条件**类：这类场景的「避开」写的是真排除（用户举的"避开阴天却在阴天推荐里"）
    '雾与阴天': ['阴天', '雾'], '雨天': ['雨后', '雨天'], '雪景': ['雪'],
    '日落晚霞': ['日落', '晚霞', '黄昏', '夕阳'], '夜景霓虹': ['夜景'],
    '室内暖光': ['钨丝'], '逆光大光比': ['逆光', '大光比'],
}
# ⚠ 题材类场景（城市街拍 / 人像肤色 / 食物咖啡 / 建筑几何 …）**不**用这套过滤：
#   它们「避开」里的句子多半是前提（"需要柔和肤色的近距离人像"），删掉反而把好推荐删了、
#   还破坏"这个场景的图要和场景对得上"（dv_scene39 就在验这个）。
ndd = nfb = nrm = nparam = 0
for sc in SC:
    kws = SKW.get(sc.get('label')) or []
    keep = []
    for it in sc.get('items') or []:
        src_it = byf.get(it.get('f'))
        slug = re.sub(r'^[rk]-', '', it.get('i') or '')
        det = None
        if src_it and src_it.get('dd'):
            det = src_it
        else:
            det = card_detail(slug)
            if det:
                nfb += 1
        if not det:
            # 卡片上也没有补充说明（MONO / 只有作者样片的那些）→ 用**配方自己的数据**做一个参数明细折页
            _r = byslug.get(slug)
            if _r:
                _vv = ' '.join(('%+d' % int(x)) for x in (_r.get('v') or [])[:12])
                _tone = 'Sh %s / Mid %s / Hi %s' % (_r.get('sh'), _r.get('mid'), _r.get('hi'))
                _wb = wbtxt(_r.get('wba'), _r.get('wbg')) + ((' · %sK' % _r['wbt']) if _r.get('wbt') else '')
                det = {'dd': (it.get('d') or ''),   # 兜底时 d 本身就带"自动归类"那句，直接用
                       'fs': '参数明细（这条没有作者补充说明，下面是从配方参数直接列出来的）',
                       'fd': ('<div class="row"><span class="mk">饱和轮</span><span class="mv">' + _vv + '</span></div>'
                              '<div class="row"><span class="mk">色调曲线</span><span class="mv">' + _tone + '</span></div>'
                              '<div class="row"><span class="mk">白平衡</span><span class="mv">' + _wb + '</span></div>'
                              '<div class="row"><span class="mk">风格标签</span><span class="mv">' + (it.get('t') or '') + '</span></div>'),
                       'pb': ''}
                nparam += 1
        if det:
            for k in ('dd', 'fd', 'fs', 'pb', 'ps'):
                if det.get(k) and not it.get(k):
                    it[k] = det[k]
                    if k == 'dd':
                        # ⚠ 短描述开头那句「图按画面自动归类：…（自动判断，偶尔会看错）」必须留住：
                        #   页面渲染 it.dd || it.d，dd 一填就把这句顶掉，用户就看不到"归类可能看错"了
                        _pre = (it.get('d') or '').split('｜')[0].strip()
                        if '自动归类' in _pre and _pre not in it['dd']:
                            it['dd'] = _pre + '｜ ' + it['dd']
                        ndd += 1
            bad = ''
            m = re.search(r'<span class="mk">避开</span><span class="mv[^"]*">(.*?)</span>', det.get('fd') or '', re.S)
            if m:
                bad = re.sub(r'<[^>]+>', '', m.group(1))
            if bad and any(w and w in bad for w in kws):
                nrm += 1
                continue                      # 「避开」里写着这个场景 → 不该出现在这个场景的推荐里
        keep.append(it)
    sc['items'] = keep
# ⚠ 不要自己加分号：原文件那个 `;` 还在（拼接时只切到 JSON 的 `]`）→ 会变成 `];;`，
#   而 dv_* 里 `(\[.*?\]);\n` 这种非贪婪正则会一路吃到很远的 `];`（历史上踩过：JSON 解析 Extra data）
newsc = 'window.__OM3SC__ = ' + json.dumps(SC, ensure_ascii=False, separators=(',', ':'))
s = s[:i0] + newsc + s[scj2:]
LOG.append('  ✓ G：场景条目补详细描述 %d 条（其中卡片兜底 %d、参数明细兜底 %d）；'
           '按「避开」移除矛盾推荐 %d 条（剩 %d 条）'
           % (ndd, nfb, nparam, nrm, sum(len(x['items']) for x in SC)))

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('\n'.join(LOG))
print('写出 app/base.html：%.2f MB' % (len(s.encode('utf-8')) / 1048576.0))
