# -*- coding: utf-8 -*-
"""界面重构：
1) 原版 / 优化版 改成一个开关按钮切换
2) 两个版本的档位 + 各大块都做成可折叠
3) 两个页面各加一排快速跳转（原版原本没有）+ 全部展开/折叠
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
P = TMP + r'\app\base.html'
h = open(P, encoding='utf-8').read()
open(TMP + r'\app\base.before_ui.html', 'w', encoding='utf-8', newline='').write(h)


def strip(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s or '')).strip()


def match_div(s, start):
    """start 指向 '<div'，返回配对的 '</div>' 之后的位置。"""
    depth = 0
    for m in re.finditer(r'<div\b|</div>', s[start:]):
        if m.group(0) == '</div>':
            depth -= 1
            if depth == 0:
                return start + m.end()
        else:
            depth += 1
    return -1


PA, PB = h.find('<div id="paneA"'), h.find('<div id="paneB"')
PD = h.find('<div id="paneD"')
assert 0 < PA < PB < PD
paneA_end = PB                                # paneA 的内容在 paneB 开始处结束
paneB_end = PD

# ============================================================ 1. 顶栏：版本开关
OLD_TABS = '<span class="tabs"><button type="button" data-p="A" class="on">原版方案</button><button type="button" data-p="B">优化版</button><button type="button" data-p="C">场景对比</button><button type="button" data-p="D" id="tabD" style="display:none">导入相机</button></span>'
assert h.count(OLD_TABS) == 1
NEW_TABS = ('<span class="tabs ver"><button type="button" data-p="A" class="on">原版方案</button>'
            '<button type="button" data-p="B">优化版</button></span>'
            '<span class="tabs rest"><button type="button" data-p="C">场景对比</button>'
            '<button type="button" data-p="D" id="tabD" style="display:none">导入相机</button></span>')
h = h.replace(OLD_TABS, NEW_TABS, 1)

# ============================================================ 2. CSS
CSS = '''
/* ---------- 版本开关 + 折叠块 + 跳转条 ---------- */
.tabs.ver{background:#232323;border:1px solid #3a3a3a;border-radius:999px;padding:3px;gap:2px;margin-left:auto}
.tabs.ver button{border:0;background:transparent;border-radius:999px;padding:6px 15px;font-weight:700;color:#9a9a9a}
.tabs.ver button.on{background:#2f8f74;color:#fff;box-shadow:0 1px 6px rgba(47,143,116,.35)}
.tabs.rest{margin-left:8px}
.tabs.rest button{padding:6px 12px}
details.sec{background:#1c1c1c;border:1px solid #2e2e2e;border-radius:12px;margin:14px 0;overflow:hidden}
details.sec>summary{list-style:none;cursor:pointer;padding:12px 15px;display:flex;align-items:center;gap:10px;background:#202020}
details.sec>summary::-webkit-details-marker{display:none}
details.sec>summary .sh{font-size:16px;font-weight:700;color:#fff;flex:1;line-height:1.4}
details.sec[open]>summary{background:#243030}
details.sec>summary .si{color:#7ed3bd;font-size:15px;font-weight:700;width:18px;text-align:center}
details.sec>summary .si::after{content:'＋'}
details.sec[open]>summary .si::after{content:'−'}
details.sec>.sb{padding:4px 15px 15px}
details.sec>.sb>h3:first-child,details.sec>.sb>p:first-child{margin-top:10px}
.jumpbar{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:14px 0 4px}
.jumpbar a,.jumpbar button{background:#242424;border:1px solid #3a3a3a;color:#c8c8c8;border-radius:999px;padding:6px 13px;font-size:12.5px;text-decoration:none;font-family:inherit;cursor:pointer;line-height:1.5}
.jumpbar a:active,.jumpbar button:active{background:#2f8f74;color:#fff;border-color:#2f8f74}
.jumpbar .jbsep{width:6px}
.jumpbar button.jball{color:#8fd8c2;border-color:#3a4a52}
/* 优化版档位卡片：可折叠 */
.omode{background:#1c1c1c;border:1px solid #2e2e2e;border-radius:12px;margin:12px 0;overflow:hidden}
.omtitle{cursor:pointer;display:flex;align-items:center;gap:10px;padding:12px 15px;background:#202020;margin:0!important}
.omode>.ombody{padding:0 15px 14px}
.omtitle .omi{color:#7ed3bd;font-size:15px;font-weight:700;margin-left:auto}
.omtitle.on{background:#243030}
'''
k = h.find('</style>')
h = h[:k] + CSS + h[k:]

# ============================================================ 3. 包 paneA 的各段
PA = h.find('<div id="paneA"'); PB = h.find('<div id="paneB"'); PD = h.find('<div id="paneD"')
paneA_end = PB
HS = [m for m in re.finditer(r'<h2([^>]*)>(.*?)</h2>', h[PA:paneA_end], re.S)]
secs = []
for idx, m in enumerate(HS):
    idd = re.search(r'id="([^"]+)"', m.group(1))
    secs.append((PA + m.start(), PA + m.end(),
                 PA + (HS[idx + 1].start() if idx + 1 < len(HS) else paneA_end - PA),
                 idd.group(1) if idd else '', m.group(2)))
assert len(secs) >= 8, len(secs)
for a, b, c, sid, title in reversed(secs):
    openattr = ' open' if sid == 'calib' else ''
    h = h[:a] + ('<details class="sec"%s id="%s"><summary><span class="sh">%s</span><span class="si"></span></summary><div class="sb">'
                 % (openattr, sid, title.strip())) + h[b:c] + '</div></details>' + h[c:]
print('paneA：包了 %d 个可折叠块（%s）' % (len(secs), ', '.join(s[3] for s in secs)))

# ============================================================ 4. 包 paneB 的各段
PB = h.find('<div id="paneB"')
PD = h.find('<div id="paneD"')
HS = [m for m in re.finditer(r'<h2([^>]*)>(.*?)</h2>', h[PB:PD], re.S)]
secs = []
for idx, m in enumerate(HS):
    idd = re.search(r'id="([^"]+)"', m.group(1))
    secs.append((PB + m.start(), PB + m.end(),
                 PB + (HS[idx + 1].start() if idx + 1 < len(HS) else PD - PB),
                 idd.group(1) if idd else '', m.group(2)))
assert len(secs) >= 4, len(secs)
for a, b, c, sid, title in reversed(secs):
    h = h[:a] + ('<details class="sec" id="%s"><summary><span class="sh">%s</span><span class="si"></span></summary><div class="sb">'
                 % (sid, title.strip())) + h[b:c] + '</div></details>' + h[c:]
print('paneB：包了 %d 个可折叠块（%s）' % (len(secs), ', '.join(s[3] for s in secs)))

# 优化版开头那段说明（h1 之后、#oskin 之前）也折起来
PB = h.find('<div id="paneB"')
i = h.find('<p class="sub">', PB)
j = h.find('<details class="sec" id="oskin">', PB)
assert 0 < i < j
h = (h[:i] + '<details class="sec" id="ointro" open><summary><span class="sh">先读这一段：这一版改了什么、开工前要确认的开关</span>'
     '<span class="si"></span></summary><div class="sb">' + h[i:j] + '</div></details>' + h[j:])
print('paneB：开头说明折叠为 #ointro')

# ============================================================ 5. 优化版档位：内容包成 ombody + 标题可点
for n in range(1, 6):
    m = re.search(r'<div class="omode" id="oC%d">' % n, h)
    assert m, n
    a = m.start()
    b = match_div(h, a)
    assert b > a
    block = h[a:b]
    tm = re.search(r'<div class="omh">', block)
    assert tm
    t_end = match_div(block, tm.start())
    inner = block[t_end:]                       # 标题之后的内容
    assert inner.rstrip().endswith('</div>')
    cut = inner.rstrip().rfind('</div>')        # omode 自己的收尾
    newblock = (block[:tm.start()]
                + block[tm.start():t_end].replace('<div class="omh">', '<div class="omh omtog">', 1)
                  .replace('</div>', '<span class="omi"></span></div>', 1)
                + '<div class="ombody"' + (' style="display:none"' if n != 1 else '') + '>'
                + inner[:cut] + '</div>' + inner[cut:])
    h = h[:a] + newblock + h[b:]
print('paneB：5 个档位卡片已改造成可折叠（默认只展开 C1）')

# ============================================================ 6. 跳转条
JB_A = ('<div class="jumpbar">'
        '<a href="#calib" data-goto="calib">校准色轮</a>'
        '<a href="#plan" data-goto="plan">推荐总表</a>'
        '<a href="#mode-C1" data-goto="mode-C1">C1</a>'
        '<a href="#mode-C2" data-goto="mode-C2">C2</a>'
        '<a href="#mode-C3" data-goto="mode-C3">C3</a>'
        '<a href="#mode-C4" data-goto="mode-C4">C4</a>'
        '<a href="#mode-C5" data-goto="mode-C5">C5</a>'
        '<a href="#pool" data-goto="pool">备选池</a>'
        '<a href="#kelvin" data-goto="kelvin">固定色温</a>'
        '<a href="#nowheel" data-goto="nowheel">黑白 / 基础</a>'
        '<a href="#howto" data-goto="howto">录入要点</a>'
        '<span class="jbsep"></span>'
        '<button type="button" class="jball" data-all="A" data-open="1">全部展开</button>'
        '<button type="button" class="jball" data-all="A" data-open="0">全部折叠</button>'
        '</div>')
i = h.find('<h1>OM-3 色彩配方手册</h1>')
assert i > 0
j = h.find('</p>', i) + 4
h = h[:j] + JB_A + h[j:]

JB_B = ('<div class="jumpbar">'
        '<a href="#ointro" data-goto="ointro">说明</a>'
        '<a href="#oskin" data-goto="oskin">肤色对照</a>'
        '<a href="#oC1" data-goto="oC1">C1 人像</a>'
        '<a href="#oC2" data-goto="oC2">C2 街拍</a>'
        '<a href="#oC3" data-goto="oC3">C3 风光</a>'
        '<a href="#oC4" data-goto="oC4">C4 夜景</a>'
        '<a href="#oC5" data-goto="oC5">C5 胶片</a>'
        '<a href="#opink" data-goto="opink">白里透红</a>'
        '<a href="#osolo" data-goto="osolo">单独占档</a>'
        '<a href="#owb" data-goto="owb">肤色微调</a>'
        '<span class="jbsep"></span>'
        '<button type="button" class="jball" data-all="B" data-open="1">全部展开</button>'
        '<button type="button" class="jball" data-all="B" data-open="0">全部折叠</button>'
        '</div>')
i = h.find('<h1>优化版方案</h1>')
assert i > 0
j = h.find('</p>', i) + 4
h = h[:j] + JB_B + h[j:]

# 旧的 ojump 去掉（已被新跳转条取代）
i = h.find('<div class="ojump">')
if i > 0:
    j = h.find('</div>', h.find('</a>', i)) + 6
    h = h[:i] + h[j:]
    print('paneB：旧的 ojump 已移除')

# ============================================================ 7. JS：折叠 / 跳转 / showMode
OLD_SHOWMODE = """  function showMode(id, noScroll) {
    for (var i = 0; i < modes.length; i++) modes[i].style.display = (modes[i].id === id) ? '' : 'none';
    for (var j = 0; j < mbtns.length; j++) mbtns[j].classList.toggle('on', mbtns[j].getAttribute('data-m') === id);
    if (!noScroll && mtab) window.scrollTo(0, mtab.getBoundingClientRect().top + window.pageYOffset - 56);
  }"""
assert h.count(OLD_SHOWMODE) == 1
NEW_SHOWMODE = """  /* 档位：全部列出，点标题或跳转按钮展开/收起（同一时间只展开一个） */
  function setMode(id, open) {
    for (var i = 0; i < modes.length; i++) {
      var m = modes[i], on = (m.id === id) && (open !== false);
      var b = m.querySelector('.ombody');
      if (b) b.style.display = on ? '' : 'none';
      var t = m.querySelector('.omh');
      if (t) t.classList.toggle('on', on);
    }
    for (var j = 0; j < mbtns.length; j++) mbtns[j].classList.toggle('on', mbtns[j].getAttribute('data-m') === id);
  }
  function showMode(id, noScroll) {
    setMode(id, true);
    if (!noScroll) {
      var el = document.getElementById(id);
      if (el) { var top = el.getBoundingClientRect().top + window.pageYOffset - 56; window.scrollTo(0, top > 0 ? top : 0); }
    }
  }
  window.__showMode = showMode;
  window.__setAllModes = function (open) {
    for (var i = 0; i < modes.length; i++) {
      var b = modes[i].querySelector('.ombody');
      if (b) b.style.display = open ? '' : 'none';
      var t = modes[i].querySelector('.omh');
      if (t) t.classList.toggle('on', !!open);
    }
    if (!open) for (var j = 0; j < mbtns.length; j++) mbtns[j].classList.remove('on');
  };
  for (var mt = 0; mt < modes.length; mt++) {
    (function (m) {
      var t = m.querySelector('.omh');
      if (t) t.addEventListener('click', function () { showMode(m.id); });
    })(modes[mt]);
  }"""
h = h.replace(OLD_SHOWMODE, NEW_SHOWMODE, 1)

OLD_JUMPTO = """  function jumpTo(id) {
    if (!id) return;
    var el = document.getElementById(id);
    if (!el) return;
    closeLB();"""
assert h.count(OLD_JUMPTO) == 1
NEW_JUMPTO = """  /* 打开所有祖先折叠块（跳转前先展开，否则跳到看不见的地方） */
  function openTo(el) {
    while (el) {
      if (el.tagName === 'DETAILS' && el.classList && el.classList.contains('sec')) el.open = true;
      el = el.parentElement;
    }
  }
  window.__openTo = openTo;

  function jumpTo(id) {
    if (!id) return;
    var el = document.getElementById(id);
    if (!el) return;
    closeLB();
    openTo(el);"""
h = h.replace(OLD_JUMPTO, NEW_JUMPTO, 1)

OLD_JT_MODE = """      if (om) {
        for (var i = 0; i < modes.length; i++) modes[i].style.display = (modes[i].id === om.id) ? '' : 'none';
        for (var j = 0; j < mbtns.length; j++) mbtns[j].classList.toggle('on', mbtns[j].getAttribute('data-m') === om.id);
      }"""
assert h.count(OLD_JT_MODE) == 1
h = h.replace(OLD_JT_MODE, """      if (om && window.__showMode) window.__showMode(om.id, true);
      openTo(el);""", 1)

# 跳转条 + 目录锚点：点了先展开再滚
JS_JUMP = """
/* ---------- 快速跳转：先展开折叠块，再滚过去 ---------- */
(function () {
  function goSec(id) {
    var el = document.getElementById(id);
    if (!el) return;
    if (window.__showMode && /^oC\\d$/.test(id)) window.__showMode(id, true);
    if (window.__openTo) window.__openTo(el);
    var pane = el.closest ? el.closest('.pane') : null;
    if (pane && /^mode-C\\d$/.test(id)) {
      var ds = pane.querySelectorAll('details.sec');
      for (var i = 0; i < ds.length; i++)
        if (ds[i] !== el && /^mode-C\\d$/.test(ds[i].id)) ds[i].open = false;
    }
    setTimeout(function () {
      var top = el.getBoundingClientRect().top + window.pageYOffset - 56;
      window.scrollTo(0, top > 0 ? top : 0);
      if (el.tagName === 'DETAILS') {
        el.style.transition = 'box-shadow .3s';
        el.style.boxShadow = '0 0 0 2px #2f8f74';
        setTimeout(function () { el.style.boxShadow = ''; }, 900);
      }
    }, 40);
  }
  window.__goSec = goSec;
  document.addEventListener('click', function (e) {
    var t = e.target;
    var a = t && t.closest ? t.closest('[data-goto]') : null;
    if (a) { e.preventDefault(); goSec(a.getAttribute('data-goto')); return; }
    var b = t && t.closest ? t.closest('[data-all]') : null;
    if (!b) return;
    e.preventDefault();
    var pane = document.getElementById(b.getAttribute('data-all') === 'A' ? 'paneA' : 'paneB');
    if (!pane) return;
    var open = b.getAttribute('data-open') === '1';
    var ds = pane.querySelectorAll('details.sec');
    for (var i = 0; i < ds.length; i++) ds[i].open = open;
    if (b.getAttribute('data-all') === 'B' && window.__setAllModes) window.__setAllModes(open);
  }, false);
  /* 目录面板 / 锚点链接：也先展开折叠块 */
  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href^="#"]') : null;
    if (!a) return;
    var id = (a.getAttribute('href') || '').slice(1);
    if (!id) return;
    var el = document.getElementById(id);
    if (!el) return;
    if (window.__showMode && /^oC\\d$/.test(id)) window.__showMode(id, true);
    if (window.__openTo) window.__openTo(el);
  }, true);
})();
"""
j = h.rfind('</body>')
h = h[:j] + '<script>' + JS_JUMP + '</script>\n' + h[j:]

open(P, 'w', encoding='utf-8', newline='').write(h)
print('界面重构完成，base.html %.1f KB' % (len(h.encode('utf-8')) / 1024))
