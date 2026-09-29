# -*- coding: utf-8 -*-
"""第 37 轮 · 规格 A：场景对比页新增「按场景找配方」索引（#scidx）。

设计要点（见 SPEC-round37.md §2）：
  · 场景**建在 IDX 的「适合」原文**上（g 字段）→ 不新增第二份会漂移的数据
  · 20 个场景，按 IDX.g 词频挑；**一条配方可以出现在多个场景**（用户明确要的）
  · 复用现成设施：色轮占位 .scwheel + window.__om3fillWheels()；跳转+高亮 data-jump + window.__jumpTo
  · 描述默认展开：画面感觉 / 适合 / 避开 直接平铺，不折叠
  · 幂等：靠 <!-- SCIDX-BEGIN --> / <!-- SCIDX-END --> 与 window.__om3scIdx 标记，重跑先删
"""
import io, re, sys
sys.stdout.reconfigure(encoding='utf-8')
P = r'D:\workspace\om3-handbook\app\base.html'
B, E = '<!-- SCIDX-BEGIN -->', '<!-- SCIDX-END -->'

CSS = """
  /* ===== 第 37 轮：按场景找配方索引 ===== */
  .sidxh{font-size:14.5px;font-weight:700;color:#d8d8d8;margin:18px 0 8px;line-height:1.5}
  .sidxh span{font-weight:400;color:#8a8a8a;font-size:12px}
  .scidxbar{display:flex;flex-wrap:wrap;gap:7px;margin:0 0 10px}
  .scidxbar button{background:#242424;border:1px solid #3a3a3a;color:#c8c8c8;border-radius:11px;
    padding:7px 11px;font-size:12px;font-family:inherit;cursor:pointer;line-height:1.25}
  .scidxbar button b{color:#8fd8c2;font-weight:700;margin-left:5px}
  .scidxbar button.on{background:#2f8f74;border-color:#2f8f74;color:#fff}
  .scidxbar button.on b{color:#d6f0e6}
  .scidxlist{display:flex;flex-direction:column;gap:10px}
  .scidxrow{display:flex;gap:10px;align-items:flex-start;background:#1c1c1c;border:1px solid #2c2c2c;
    border-radius:12px;padding:10px 11px}
  .scidxrow .scwheel{flex:0 0 auto;width:38px;height:38px;display:block}
  .scidxrow .scwheel svg{width:38px;height:38px}
  .scidxmeta{flex:1 1 auto;min-width:0}
  .scidxname{font-size:13.5px;font-weight:700;color:#eaeaea;line-height:1.4}
  .scidxname .scauth{font-weight:400;color:#9aa3b2;font-size:11.5px;margin-left:5px}
  .scidxname .scslot{font-weight:400;color:#8fd8c2;font-size:11px;margin-left:5px}
  .scidxtags{font-size:11px;color:#9aa3b2;margin:1px 0 4px}
  .scidxline{font-size:12.5px;line-height:1.6;color:#cfcfcf;margin:2px 0}
  .scidxline .mk{display:inline-block;width:auto;color:#8fd8c2;font-weight:700;margin-right:3px}
  .scidxline.avoid .mk{color:#d9b96a}
  .scidxacts{flex:0 0 auto;align-self:center}
  .scidxacts button{border:0;border-radius:9px;padding:8px 10px;font-size:11.5px;font-family:inherit;
    font-weight:700;cursor:pointer;background:#2f8f74;color:#fff;white-space:nowrap}
  .scidxacts button.os{background:#242424;color:#8fd8c2;border:1px solid #3a4a52}
  .scidxempty{font-size:12.5px;color:#8a8a8a;padding:8px 2px}
  @media (max-width:430px){ .scidxrow{flex-wrap:wrap} .scidxacts{width:100%;text-align:right} }
"""

# 20 个场景（关键词来自 IDX.g 的真实用词；一条配方可命中多个场景）
SCENES = [
 ('street',   '城市街拍',   ['街拍', '街头', '城市', '都市', '人文', '纪实', '市场', '市集']),
 ('indoor',   '室内暖光',   ['室内', '钨丝', '暖光', '咖啡馆', '餐厅', '家居', '窗光']),
 ('food',     '食物咖啡',   ['食物', '美食', '料理', '餐', '咖啡', '市集', '市场']),
 ('travel',   '旅行日常',   ['旅拍', '旅行', '日常', '通吃', '通用', '记录', '街头']),
 ('arch',     '建筑几何',   ['建筑', '几何', '线条', '形状', '结构', '极简']),
 ('portrait', '人像肤色',   ['人像', '肖像', '肤色', '人物']),
 ('film',     '复古胶片',   ['复古', '胶片', '老街', '老照片', '怀旧', '褪色']),
 ('sunset',   '日落晚霞',   ['日落', '晚霞', '黄昏', '夕阳', '日出', '清晨', '朝霞', '暖光人文']),
 ('wedding',  '婚礼聚会',   ['婚礼', '亲子', '聚会', '生日', '宴会', '活动']),
 ('kids',     '儿童亲子',   ['儿童', '小孩', '宝宝', '亲子', '生日']),
 ('mist',     '雾与阴天',   ['雾', '阴天', '柔光', '日系淡调', '情绪片']),
 ('skywater', '天空水面',   ['天空', '水面', '倒影', '海', '湖', '云']),
 ('still',    '静物极简',   ['静物', '极简', '留白', '简约']),
 ('night',    '夜景霓虹',   ['夜', '霓虹', '灯光', '车流', '夜市', '蓝调时刻', '星']),
 ('autumn',   '红叶秋色',   ['红叶', '秋叶', '秋色', '晚霞霓虹', '暖色主体']),
 ('backlight','逆光大光比', ['逆光', '光比大', '大光比', '强光', '硬光']),
 ('flower',   '花卉',       ['花卉', '花']),
 ('snow',     '雪景',       ['雪']),
 ('forest',   '森林绿意',   ['森林', '草地', '绿色主体', '苔', '溪流', '林间', '绿植']),
 ('rain',     '雨天',       ['雨', '雨后', '水汽', '玻璃反光']),
 ('mono',     '黑白 / 单色', ['黑白', '单色', '灰阶']),
]

HTML = (B + '\n<h2 class="sidxh">① 按场景找配方 <span>· %d 个场景，一条配方可以同时属于好几个场景'
        '（按每条配方自己的「适合」原文匹配出来的，不是hardcode分类）</span></h2>\n'
        '<div class="scidxbar" id="scidxbar"></div>\n<div class="scidxlist" id="scidxlist"></div>\n'
        '<h2 class="sidxh">② 实拍对比 <span>· 6 个统一场景，同一个构图横向比色（左右滑动，一次一张）</span></h2>\n'
        % len(SCENES)) + E + '\n'

JS = r"""
/* ===== 第 37 轮：按场景找配方（建在 IDX 的「适合」原文上；一条配方可出现在多个场景）=====
   为什么这么做：用户要"场景精细化 + 多条场景里都出现同一配方 + 遇到场景快速选择"。
   数据源就用搜索索引 IDX 的 g（适合）/v（避开）/f（一句话感觉）/t（标签），
   不再另存一份分类（存两份必然漂移）。 */
(function(){
  var bar = document.getElementById('scidxbar'), list = document.getElementById('scidxlist');
  if (!bar || !list) return;
  var DEF = __SCENES__;
  var IDX = window.IDX || [];
  var REC = window.__OM3RECIPES__ || [];
  /* 锚点 → 12 轴值：r-<slug> / <slug> 都要登记；优化版（oC / k 开头）只有名字没数据，按名字兜底 */
  var V = {}, BYNAME = {};
  for (var i = 0; i < REC.length; i++){
    var r = REC[i]; if (!r || !r.v) continue;
    if (r.slug){ V[r.slug] = r.v; V['r-' + r.slug] = r.v; }
    if (r.n && !BYNAME[r.n]) BYNAME[r.n] = r.v;
  }
  function wheelOf(h, n){ var v = V[h] || BYNAME[n]; return v ? v.join(',') : ''; }
  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){
    return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  /* 预计算：每个场景命中哪些索引条目（一条可以进多个场景 = 用户要的） */
  var HIT = {}, total = 0;
  for (var s = 0; s < DEF.length; s++){
    var k = DEF[s].k, kw = DEF[s].kw, arr = [];
    for (var j = 0; j < IDX.length; j++){
      var it = IDX[j];
      /* 匹配源 = 「适合」原文 g **加上** 标签 t（黑白/灰阶这类词只在标签里，g 里没有）*/
      var hay = String(it.g || '') + ' ' + String(it.t || '');
      if (!String(it.g || '')) continue;
      var score = 0;
      for (var w = 0; w < kw.length; w++) if (hay.indexOf(kw[w]) >= 0) score++;
      if (score > 0) arr.push({ it: it, score: score, at: j });
    }
    arr.sort(function(a, b){ return (b.score - a.score) || (a.at - b.at); });
    HIT[k] = arr; total += arr.length;
  }
  var cur = DEF[0].k;
  function chip(){
    var h = '';
    for (var s = 0; s < DEF.length; s++){
      var k = DEF[s].k, n = HIT[k].length;
      h += '<button type="button" data-k="' + k + '"' + (k === cur ? ' class="on"' : '') + '>' +
           esc(DEF[s].label) + '<b>' + n + '</b></button>';
    }
    bar.innerHTML = h;
  }
  function rows(){
    var arr = HIT[cur] || [], h = '';
    if (!arr.length) h = '<div class="scidxempty">这个场景暂时没有匹配的配方（换个场景试试）</div>';
    for (var i = 0; i < arr.length; i++){
      var it = arr[i].it, hh = it.h || '', v = wheelOf(hh, it.n);
      var isCard = hh.charAt(0) === 'r';
      h += '<div class="scidxrow" data-h="' + esc(hh) + '" data-t="' + esc(isCard ? 'card' : 'os') + '">' +
           (v ? '<span class="scwheel" data-v="' + esc(v) + '"></span>' : '') +
           '<div class="scidxmeta">' +
             '<div class="scidxname">' + esc(it.n) + '<span class="scauth">' + esc(it.a || '') + '</span>' +
             (it.sl ? '<span class="scslot">' + esc(it.sl) + '</span>' : '') + '</div>' +
             (it.t ? '<div class="scidxtags">' + esc(it.t) + '</div>' : '') +
             (it.f ? '<div class="scidxline"><span class="mk">画面</span>' + esc(it.f) + '</div>' : '') +
             (it.g ? '<div class="scidxline"><span class="mk">适合</span>' + esc(it.g) + '</div>' : '') +
             (it.v ? '<div class="scidxline avoid"><span class="mk">避开</span>' + esc(it.v) + '</div>' : '') +
           '</div>' +
           '<div class="scidxacts"><button type="button" class="' + (isCard ? '' : 'os') +
              '" data-jump="' + esc(hh) + '">' + (isCard ? '看卡片 →' : '看槽位 →') + '</button></div>' +
           '</div>';
    }
    list.innerHTML = h;
    if (window.__om3fillWheels) { try { window.__om3fillWheels(); } catch (e1) {} }
  }
  bar.addEventListener('click', function(e){
    var b = e.target && e.target.closest ? e.target.closest('button[data-k]') : null;
    if (!b) return;
    cur = b.getAttribute('data-k'); chip(); rows();
  }, false);
  chip(); rows();
  /* 探针用：暴露状态与统计（不参与渲染） */
  window.__om3scIdx = {
    scenes: DEF.map(function(d){ return d.k; }),
    labels: DEF.map(function(d){ return d.label; }),
    counts: (function(){ var o = {}; for (var s = 0; s < DEF.length; s++) o[DEF[s].k] = HIT[DEF[s].k].length; return o; })(),
    pairs: total,
    multi: (function(){   /* 出现在多个场景里的条目数（用户要的"一份配方可属多场景"） */
      var c = {}, m = 0;
      for (var s = 0; s < DEF.length; s++) for (var i = 0; i < HIT[DEF[s].k].length; i++){
        var h = HIT[DEF[s].k][i].it.h || ''; c[h] = (c[h] || 0) + 1;
      }
      for (var k2 in c) if (c[k2] > 1) m++;
      return m;
    })(),
    cur: function(){ return cur; },
    show: function(k){ cur = k; chip(); rows(); },
    rows: function(){ return document.getElementById('scidxlist').children.length; }
  };
})();
"""
JS = JS.replace('__SCENES__', repr([{'k': k, 'label': l, 'kw': w} for k, l, w in SCENES]).replace("'", '"'))


def main():
    s = io.open(P, encoding='utf-8').read()
    # 幂等
    s = re.sub(re.escape(B) + r'.*?' + re.escape(E) + r'\n?', '', s, flags=re.S)
    s = re.sub(r'\n/\* ===== 第 37 轮：按场景找配方索引 ===== \*/.*?(?=\n  /\*|\n</style>)', '', s, flags=re.S)
    s = re.sub(r'\n/\* ===== 第 37 轮：按场景找配方（建在 IDX 的「适合」原文上；一条配方可出现在多个场景）=====.*?\n\}\)\(\);\n', '', s, flags=re.S)

    # ① CSS：挂在 .scjump2 那条规则后面（同一个 <style> 里）
    anchor = '.scjump2{background:#242424;color:#8fd8c2;border:1px solid #3a4a52}'
    assert s.count(anchor) >= 1, 'CSS 锚点没找到'
    s = s.replace(anchor, anchor + CSS, 1)

    # ② HTML：插在场景对比页的 #scbar 之前
    bar = '<div class="scbar" id="scbar">'
    assert s.count(bar) == 1, 'scbar 不唯一：%d' % s.count(bar)
    s = s.replace(bar, HTML + bar, 1)

    # ③ JS：挂在 SC 那个脚本块的最后（同一块里 DOM 已就绪）
    i = s.find('var SC = window.SC')
    assert i > 0
    j = s.find('</script>', i)
    assert j > 0
    s = s[:j] + JS + '\n' + s[j:]

    io.open(P, 'w', encoding='utf-8', newline='').write(s)
    print('✅ 场景索引已插入：#scidx（%d 个场景）' % len(SCENES))


if __name__ == '__main__':
    main()
