# -*- coding: utf-8 -*-
"""场景对比页大改：
1) 全屏看图里左右滑动后，关闭时把对比条滚回同一张
2) 全屏里加「看参数详情」按钮；每张对比卡加「看参数详情 / 优化版槽位」按钮，跳到原卡并高亮
3) 对比卡的文字描述改成原卡的完整「补充」六项（画面感觉/色彩重点/影调/适合/避开/提示）
4) 对比卡里新增可折叠的「调整参数」（档位白平衡 + 曲线等参数 + 12 点饱和轮）
"""
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'
P = BASE + r'\app\base.html'
h = open(P, encoding='utf-8').read()

# ============================================================
# 一、对比数据：给每个配方补上原卡 id / 完整补充 / 参数 / 优化版槽位
# ============================================================
dec = json.JSONDecoder()
i = h.find('window.SC=')
assert i > 0
SC, sc_end = dec.raw_decode(h, i + len('window.SC='))

j = h.find('var IDX=')
IDX, _ = dec.raw_decode(h, j + len('var IDX='))
idx_by_name = {}
for e in IDX:
    idx_by_name[(e['n'].strip().lower(), e['a'].strip().lower())] = e.get('h', '')

card_re = re.compile(r'<div class="card" id="r-([^"]+)">')
cards = list(card_re.finditer(h))
assert len(cards) > 40, len(cards)

imap = json.load(open(BASE + r'\imgmap.json', encoding='utf-8'))
doc2slug = {cid: slug for cid, slug, _files in imap['mapping']}

mode_heads = list(re.finditer(r'<h2 id="mode-(C\d)">(.*?)</h2>\s*<p class="sub"[^>]*>(.*?)</p>', h, re.S))


def strip_tags(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s or '')).strip()


def mode_of(pos):
    last = None
    for mm in mode_heads:
        if mm.start() < pos:
            last = mm
        else:
            break
    return (last.group(2), last.group(3)) if last else ('', '')


cards_info = {}
for n, m in enumerate(cards):
    cid = m.group(1)
    end = cards[n + 1].start() if n + 1 < len(cards) else h.find('<footer', m.start())
    blk = h[m.start():end]
    nm = re.search(r'<span class="cname">(.*?)</span>', blk)
    au = re.search(r'<span class="cauth">(.*?)</span>', blk)
    sl = re.search(r'<span class="slot">(.*?)</span>', blk)
    pa = re.search(r'<div class="params">(.*?)</div>', blk, re.S)
    va = re.search(r'<div class="vals">(.*?)</div>', blk)
    vl = re.search(r'<div class="vlegend">(.*?)</div>', blk)
    info = {
        'name': strip_tags(nm.group(1)) if nm else '',
        'auth': strip_tags(au.group(1)) if au else '',
        'slot': strip_tags(sl.group(1)) if sl else '',
        'params': pa.group(1).strip() if pa else '',
        'vals': strip_tags(va.group(1)) if va else '',
        'vleg': strip_tags(vl.group(1)) if vl else '',
        'slug': doc2slug.get(cid, ''),
        'gfeel': '', 'fd': '', 'fs': '',
    }
    mt, ms = mode_of(m.start())
    info['mode'] = strip_tags(mt)
    info['modesub'] = strip_tags(ms)
    d = re.search(r'<details class="fold fmine">(.*?)</details>', blk, re.S)
    if d:
        db = d.group(1)
        sm = re.search(r'<summary>(.*?)</summary>', db, re.S)
        info['fs'] = strip_tags(sm.group(1)) if sm else ''
        b0 = db.find('<div class="foldbody">')
        if b0 >= 0:
            b0 += len('<div class="foldbody">')
            b1 = db.rfind('</div>')
            info['fd'] = db[b0:b1]
        g = re.search(r'<span class="mk">画面感觉</span><span class="mv">(.*?)</span>', info['fd'], re.S)
        info['gfeel'] = strip_tags(g.group(1)) if g else ''
    cards_info[cid] = info

# 优化版槽位：按 slug 反查（槽位第一张图就是 slug__cmp__xxx.jpg）
slug2oslot = {}
oslots = list(re.finditer(r'<div class="oslot" id="(oC[^"]+)">', h))
for n, m in enumerate(oslots):
    oid = m.group(1)
    end = oslots[n + 1].start() if n + 1 < len(oslots) else h.find('<footer', m.start())
    blk = h[m.start():end]
    im = re.search(r'data-im="([^"]+?)__cmp__', blk)
    if im:
        slug2oslot.setdefault(im.group(1), (oid, oid.split('-')[0][1:]))

hit_card = hit_os = 0
for sc in SC:
    for it in sc['items']:
        key = (it['n'].strip().lower(), it['a'].strip().lower())
        cid = (idx_by_name.get(key) or '')[2:]
        c = cards_info.get(cid)
        if not c:
            continue
        hit_card += 1
        it['i'] = 'r-' + cid
        if c['slot']:
            it['sl'] = c['slot']
        if c['gfeel']:
            it['dd'] = c['gfeel']
        if c['fd']:
            it['fd'] = c['fd']
            it['fs'] = c['fs']
        pb = []
        mtxt = c['mode'] or c['slot']
        if mtxt or c['modesub']:
            pb.append('<div class="row"><span class="mk">档位</span><span class="mv">%s%s</span></div>'
                      % (mtxt, ('<br>' + c['modesub']) if c['modesub'] else ''))
        if c['params']:
            pb.append('<div class="row"><span class="mk">参数</span><span class="mv">%s</span></div>' % c['params'])
            it['ps'] = '调整参数：' + strip_tags(c['params'])
        if c['vals']:
            pb.append('<div class="row"><span class="mk">饱和轮</span><span class="mv">%s<br>%s</span></div>'
                      % (c['vals'], c['vleg']))
        it['pb'] = ''.join(pb)
        o = slug2oslot.get(c['slug'])
        if o:
            it['os'] = o[0]
            it['osm'] = o[1]
            hit_os += 1

print('对比配方 %d 条 / 匹配到原卡 %d 条 / 其中也在优化版 %d 条'
      % (sum(len(s['items']) for s in SC), hit_card, hit_os))

new_sc = json.dumps(SC, ensure_ascii=False, separators=(',', ':'))
h = h[:i + len('window.SC=')] + new_sc + h[sc_end:]

# ============================================================
# 二、JS：全屏同步 + 详情跳转 + 对比卡渲染
# ============================================================
js_start = h.find("(function () {\n  'use strict';")
js_end = h.find('</script>', js_start)
assert js_start > 0 < js_end
js = h[js_start:js_end]

REPL = []

REPL.append((
    "  var group = [], gi = 0, scale = 1, tx = 0, ty = 0;",
    "  var group = [], gi = 0, scale = 1, tx = 0, ty = 0, groupPager = null;"))

REPL.append((
    """    lbbot.innerHTML = (it.cap || '') +
      '<div class="lbhint">双指缩放 / 双击放大 · 左右滑动切换 · Esc 关闭（共 ' + group.length + ' 张）</div>';""",
    """    lbbot.innerHTML = (it.cap || '') +
      (it.cid ? '<button class="lbdetail" type="button" data-jump="' + it.cid + '">看参数详情 →</button>' : '') +
      '<div class="lbhint">双指缩放 / 双击放大 · 左右滑动切换 · Esc 关闭（共 ' + group.length + ' 张）</div>';"""))

REPL.append((
    "  function closeLB() { lb.classList.remove('on'); document.body.style.overflow = ''; lbimg.removeAttribute('src'); }",
    """  function closeLB() {
    lb.classList.remove('on'); document.body.style.overflow = '';
    lbimg.removeAttribute('src');
    /* 全屏里左右滑过之后，把下面的对比条也滚到同一张 —— 否则关掉会跳回点开前的位置 */
    if (groupPager && group[gi] && group[gi].el) {
      var sl0 = group[gi].el.closest ? group[gi].el.closest('.scslide') : null;
      var first = groupPager.querySelector('.scslide');
      if (sl0 && first && groupPager.contains(sl0)) groupPager.scrollLeft = sl0.offsetLeft - first.offsetLeft;
    }
    groupPager = null;
  }"""))

REPL.append((
    "    var cont = im.closest('.shots, .osshots, .scpager');\n    if (!cont) return;\n    var all = cont.querySelectorAll('img');",
    "    var cont = im.closest('.shots, .osshots, .scpager');\n    if (!cont) return;\n    var isSc = !!(cont.classList && cont.classList.contains('scpager'));\n    var all = cont.querySelectorAll('img');"))

REPL.append((
    "      items.push({ src: t.getAttribute('src'), title: title, cap: cap });",
    "      items.push({ src: t.getAttribute('src'), title: title, cap: cap, el: t,\n"
    "                   cid: (slide && slide.getAttribute('data-cid')) || '' });"))

REPL.append((
    "    if (items.length) openLB(items, idx);",
    "    if (items.length) { groupPager = isSc ? cont : null; openLB(items, idx); }"))

# 跳转函数 + 委托点击，插在「4. 场景对比」之前
REPL.append((
    "  /* ---------- 4. 场景对比 ---------- */",
    """  /* ---------- 3b. 从对比页 / 全屏看图跳回配方详情 ---------- */
  function jumpTo(id) {
    if (!id) return;
    var el = document.getElementById(id);
    if (!el) return;
    closeLB();
    var om = el.closest ? el.closest('.omode') : null;
    var tab = document.querySelector('.tabs button[data-p="' + (om ? 'B' : 'A') + '"]');
    if (tab) tab.click();
    setTimeout(function () {
      if (om) {
        for (var i = 0; i < modes.length; i++) modes[i].style.display = (modes[i].id === om.id) ? '' : 'none';
        for (var j = 0; j < mbtns.length; j++) mbtns[j].classList.toggle('on', mbtns[j].getAttribute('data-m') === om.id);
      }
      el.scrollIntoView({ block: 'center' });
      el.classList.add('flashcard');
      setTimeout(function () { el.classList.remove('flashcard'); }, 1900);
    }, 140);
  }
  window.__jumpTo = jumpTo;
  document.addEventListener('click', function (e) {
    var b = e.target && e.target.closest ? e.target.closest('[data-jump]') : null;
    if (!b) return;
    e.preventDefault();
    jumpTo(b.getAttribute('data-jump'));
  }, true);

  /* ---------- 4. 场景对比 ---------- */"""))

SLIDE_OLD = """      pager.innerHTML = SC[idx].items.map(function (it) {
        return '<div class="scslide"><img src="' + esc(IMG(it.f)) + '" alt="">' +
          '<div class="scmeta"><div class="scname">' + esc(it.n) + ' ' +
          '<span class="scauth">' + esc(it.a) + '</span></div>' +
          (it.t ? '<div class="sctags">' + esc(it.t) + '</div>' : '') +
          '<div class="scdesc">' + esc(it.d || '') + '</div></div></div>';
      }).join('');"""

SLIDE_NEW = """      pager.innerHTML = SC[idx].items.map(function (it) {
        var acts = '';
        if (it.i) {
          acts = '<div class="scacts"><button type="button" class="scjump" data-jump="' + esc(it.i) + '">看参数详情 →</button>' +
            (it.os ? '<button type="button" class="scjump2" data-jump="' + esc(it.os) + '">' + esc(it.osm || '') + ' 优化版 →</button>' : '') +
            '</div>';
        }
        return '<div class="scslide" data-cid="' + esc(it.i || '') + '">' +
          '<img src="' + esc(IMG(it.f)) + '" alt="">' +
          '<div class="scmeta"><div class="scname">' + esc(it.n) + ' ' +
          '<span class="scauth">' + esc(it.a) + '</span>' +
          (it.sl ? '<span class="scslot">' + esc(it.sl) + '</span>' : '') + '</div>' +
          (it.t ? '<div class="sctags">' + esc(it.t) + '</div>' : '') +
          '<div class="scdesc">' + esc(it.dd || it.d || '') + '</div>' +
          (it.fd ? '<details class="fold fmine scfold"><summary>' + esc(it.fs) + '</summary><div class="foldbody">' + it.fd + '</div></details>' : '') +
          (it.pb ? '<details class="fold fpar scfold"><summary>' + esc(it.ps || '调整参数') + '</summary><div class="foldbody">' + it.pb + '</div></details>' : '') +
          acts +
          '</div></div>';
      }).join('');"""

REPL.append((SLIDE_OLD, SLIDE_NEW))

for old, new in REPL:
    assert js.count(old) == 1, ('JS 锚点命中 %d 次: %s' % (js.count(old), old[:60]))
    js = js.replace(old, new, 1)

h = h[:js_start] + js + h[js_end:]
open(BASE + r'\app_extra.js', 'w', encoding='utf-8', newline='').write(js)
print('JS 已更新（%d 处），并同步回 app_extra.js' % len(REPL))

# ============================================================
# 三、CSS
# ============================================================
ANCHOR = '  .scbar,.modetabs{margin:0 -12px;padding:8px 12px}\n}'
assert h.count(ANCHOR) == 1, h.count(ANCHOR)

NEW_CSS = '''

/* ============ 场景对比：完整描述 / 参数折叠 / 跳详情 ============ */
.scslot{font-size:10.5px;color:#9a9a9a;background:#242424;border:1px solid #333;border-radius:6px;padding:1px 6px;margin-left:8px;white-space:nowrap}
.scdesc{color:#cfcfcf}
.scfold{margin:9px 0 0;border-radius:0 8px 8px 0}
.scfold>summary{font-size:12px;line-height:1.62}
.scfold>.foldbody{padding:9px 12px 11px;font-size:12.5px}
details.fold.fpar{background:#2a2318;border-left-color:#a8853f}
details.fold.fpar>summary{color:#d9b96a}
details.fold.fpar>.foldbody{color:#ded2b8}
.scacts{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.scacts button{border:0;border-radius:9px;padding:10px 13px;font-size:12.5px;font-family:inherit;font-weight:700;cursor:pointer;flex:1 1 auto}
.scjump{background:#2f8f74;color:#fff}
.scjump:active{background:#26735e}
.scjump2{background:#242424;color:#8fd8c2;border:1px solid #3a4a52}
.flashcard{animation:flashcard 1.9s ease-out}
@keyframes flashcard{0%,18%{box-shadow:0 0 0 3px #8fd8c2,0 0 28px #2f8f7490;border-color:#8fd8c2}100%{box-shadow:none}}
#lb .lbbot .lbdetail{display:block;width:100%;margin:10px 0 2px;background:#2f8f74;color:#fff;border:0;border-radius:9px;padding:10px;font-size:13px;font-family:inherit;font-weight:700;cursor:pointer}'''
h = h.replace(ANCHOR, ANCHOR + NEW_CSS, 1)

css = open(BASE + r'\app_extra.css', encoding='utf-8').read()
assert css.count(ANCHOR) == 1
open(BASE + r'\app_extra.css', 'w', encoding='utf-8', newline='').write(css.replace(ANCHOR, ANCHOR + NEW_CSS, 1))
print('CSS 已追加，并同步回 app_extra.css')

# ============================================================
# 四、页脚说明补一句
# ============================================================
OLD_NOTE = '点图片可全屏放大（双指缩放 / 左右滑动）。'
assert h.count(OLD_NOTE) == 1
h = h.replace(OLD_NOTE, '点图片可全屏放大（双指缩放 / 左右滑动，关掉后仍停在你看的那张）；要看完整说明点「看参数详情」，会跳到那个配方的原始卡片并高亮。', 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('base.html 已更新  %.1f KB' % (len(h.encode('utf-8')) / 1024))
