# -*- coding: utf-8 -*-
"""第 70 轮：搜索框 3 处毛病 + ☰ 菜单逐项分层（见 SPEC-round70.md）。

① 清空后残留（安卓 WebView 里 type=search 的原生 ✕ 不保证派发 input）→ 自绘「✕ 清空」+ 400ms 看门狗
② 搜索框不固顶 / 档位推荐的搜索框跑到页面**最底部**（实测 y=4518、页高 4537）
   → #row2 固顶 + 面板内"输入框+✕"整行固顶 + 把 #toc2q/#toc2chips/#toc2res 搬进 nav#toc2 面板
③ 场景对比顶部 56px 空位：.scselwrap 的 position 被后来的规则改成 relative，但 top:56px 还生效
   → 整块被相对下移 56px；改成 position:sticky;top:calc(--om3toph + --om3rowh)
   （顶栏/搜索条高度由 JS 每秒实测写进 CSS 变量，不写死）
④ ☰ 菜单分层：客户项留下、排查项搬到测试页（**同一份实现** menuAct，不删功能、不复制实现）

规矩：幂等（标记 `r70：搜索与菜单`）+ 每一步都必须"真的改到东西"（否则报错）+ 老 id 一个不少。

用法：python scripts/gen_r70.py [--check]
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r70：搜索与菜单'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


# ================================================================ ① ② ③：CSS
CSS = '''
/* ===== r70：搜索固顶 + 清空按钮 + 场景对比贴顶（详见 SPEC-round70.md §2） ===== */
:root{--om3pad:12px;--om3toph:49px;--om3rowh:47px}
/* 搜索入口条固顶在顶栏下面（以前滚下去就没了，想搜得先回到最上方）。
   负 margin 让它铺满整宽（跟 .topbar 同样的做法）；背景不透明才不会透出下面的内容。 */
#row2{position:sticky;top:var(--om3toph,49px);z-index:45;background:#121212;
  margin-left:calc(-1 * var(--om3pad,12px));margin-right:calc(-1 * var(--om3pad,12px));
  padding-left:var(--om3pad,12px);padding-right:var(--om3pad,12px);
  box-shadow:0 8px 10px -10px #000}
/* 面板里的"输入框 + ✕ 清空"整行固顶：翻搜索结果时输入框不会跟着滚走 */
.tocsearchrow{position:sticky;top:0;z-index:3;background:#1b1b1b;display:flex;gap:8px;align-items:center;
  padding:2px 0 10px}
.tocsearchrow .tocsearch{margin-bottom:0}
.tocclear{flex:none;width:36px;height:36px;border-radius:9px;border:1px solid #3a3a3a;background:#262626;
  color:#9aa3b2;font-size:15px;font-family:inherit;cursor:pointer}
.tocclear:active{background:#333;color:#fff}
/* 场景对比的"看哪个场景"：**position 与 top 必须同一条规则说了算**
   （原来 935 行 sticky+top:56px 被 939 行 relative 覆盖，但 top 还生效 → 整块下移 56px = 那片空位） */
.scselwrap{position:sticky;top:calc(var(--om3toph,49px) + var(--om3rowh,47px));z-index:20;background:#161616}
'''


@step('CSS：搜索固顶 + 清空按钮 + 场景对比贴顶')
def s_css(html):
    old = '</style></head><body>'
    assert html.count(old) == 1
    return html.replace(old, CSS + old, 1)


# ================================================================ ② 顶栏高度实测（CSS 变量）
@step('JS：每秒实测顶栏/搜索条高度 → 写进 --om3toph / --om3rowh')
def s_toph(html):
    old = '  window.__om3setBarH = setBarH;'
    assert html.count(old) == 1
    new = old + '''
  /* r70：固顶的偏移量别写死 —— 顶栏高度会随字体/宽度变。每秒实测一次写进 CSS 变量，
     CSS 里用 var(--om3toph) / var(--om3rowh)（见样式表里的 r70 段）。 */
  function setTopH(){
    try{
      var tb = document.querySelector('.topbar');
      var h = tb ? Math.round(tb.getBoundingClientRect().height) : 0;
      if(h > 0) document.documentElement.style.setProperty('--om3toph', h + 'px');
      var r2 = document.getElementById('row2'), rh = 0;
      if(r2){
        var cs = getComputedStyle(r2);
        if(cs.display !== 'none' && cs.position === 'sticky') rh = Math.round(r2.getBoundingClientRect().height);
      }
      document.documentElement.style.setProperty('--om3rowh', rh + 'px');
      window.__om3topH = h; window.__om3rowH = rh;
    }catch(e){}
  }
  window.__om3setTopH = setTopH;'''
    return html.replace(old, new, 1)


@step('JS：把 setTopH() 挂进那个每秒一次的自检（和 setBarH 一起）')
def s_toph_call(html):
    old = '    setBarH();                      /* 底栏高度会随字体/档位变化 → 顺手更新贴底浮层的让位量 */'
    assert html.count(old) == 1
    new = old + '\n    setTopH();                      /* r70：顶栏高度 → 固顶偏移（#row2 / 场景对比的"看哪个场景"） */'
    return html.replace(old, new, 1)


# ================================================================ ① #tocq：固顶行 + ✕
@step('① 配方合集：#tocq 包进"固顶行 + ✕ 清空"')
def s_tocq(html):
    i = html.index('<input id="tocq"')
    j = html.index('\n', i)
    line = html[i:j]
    assert 'class="tocsearch"' in line and 'tocqc' not in html
    new = ('<div class="tocsearchrow">\n' + line +
           '\n<button type="button" id="tocqc" class="tocclear" title="清空搜索框" aria-label="清空搜索框">✕</button>\n</div>')
    return html[:i] + new + html[j:]


# ================================================================ ② 档位推荐：搜索组包成盒子（末尾 JS 再搬进 nav#toc2）
@step('② 档位推荐：搜索组包成「固顶行+✕」的盒子（稍后由末尾 JS 搬进 nav#toc2）')
def s_toc2move(html):
    i = html.index('<input id="toc2q"')
    j = html.index('<div id="toc2res"')
    j = html.index('\n', j)
    block = html[i:j]
    assert block.count('id="toc2q"') == 1 and block.count('id="toc2chips"') == 1 and block.count('id="toc2res"') == 1
    assert html.count('<nav id="toc2">\n') == 1
    # 输入框那一行包"固顶行 + ✕"，三个元素一起包进一个盒子（盒子**留在原地**；由文档末尾的小脚本搬进面板）
    k = block.index('<div class="chips"')
    inp = block[:k].rstrip('\n')
    rest = block[k:]
    assert 'id="toc2q"' in inp
    head_txt = ('<!-- r70：这一组原来直接躺在 paneB 的**最后面**（实测 y=4518 / 页高 4537）——搜索框在页面最底部。\n'
                '     这里先包成一个盒子，等文档解析完（页面末尾那个小脚本）再整体搬进 nav#toc2 面板：\n'
                '     **只搬 DOM 节点、id 一个不改**，所以前面脚本里早就拿到的 getElementById 引用依然有效。 -->\n'
                '<div class="toc2searchbox">\n<div class="tocsearchrow">\n')
    wrapped = (head_txt + inp +
               '\n<button type="button" id="toc2qc" class="tocclear" title="清空搜索框" aria-label="清空搜索框">✕</button>\n</div>\n'
               + rest + '\n</div>')
    return html[:i] + wrapped + html[j:]


@step('② 末尾 JS：把 .toc2searchbox 搬进 nav#toc2 的最前面（结构对齐配方合集）')
def s_toc2move_js(html):
    old = '</body></html>'
    assert html.count(old) == 1
    new = '''<script>
/* r70：档位推荐的"搜索组"（#toc2q / #toc2chips / #toc2res）在标记里躺在 paneB 的最后面，
   历史上就被放到了页面最底部（实测 y=4518、页高 4537）→ 用户得滚到底才搜得到。
   这里在**文档解析完之后**（本脚本就在 body 末尾）整体搬进 nav#toc2 面板的最前面，
   和配方合集的 nav#toc 结构对齐：点搜索条 → 面板顶部就是搜索框（固顶）＋ 目录。
   ⚠ 只搬 DOM 节点（id 一个不改）—— 前面脚本里 getElementById 早就拿到的引用**依然指向同一个节点**，
     所以不需要改那些代码，也不会出现"取到 null"的问题。 */
(function(){
  try{
    var box = document.querySelector('.toc2searchbox');
    var nav2 = document.getElementById('toc2');
    if(box && nav2 && nav2.firstChild) nav2.insertBefore(box, nav2.firstChild);
  }catch(e){}
})();
</script>
''' + old
    return html.replace(old, new, 1)


# ================================================================ ① 搜索：✕ + 看门狗
@step('① 搜索 JS：自绘 ✕ 清空 + 值变化看门狗（400ms）')
def s_searchjs(html):
    old = """ var chips2=document.querySelectorAll('#toc2chips button');
 for(var c2=0;c2<chips2.length;c2++){
   chips2[c2].addEventListener('click',function(){q2.value=this.dataset.q;run(q2);});
 }"""
    assert html.count(old) == 1
    new = old + '''

  /* ===== r70：清空可靠 + 固顶配套（需求方 2026-09-28：\"清空后还留着一个字的搜索记录\"） =====
     根因：`<input type="search">` 自带的 ✕ 由 **WebView 自己画**，清空文本后**不保证派发 input 事件**，
     而我们的结果渲染只挂在 input/search 上 → 框空了，上一次（可能只有一个字）的搜索结果还在屏幕上。
     两手抓：① 自绘 ✕（点它一定走我们自己的代码）② 看门狗：每 400ms 比一次\"输入框实际值 vs 上次渲染用的值\"，
     不一致就重渲染（不管是谁改的 —— 原生 ✕、输入法、程序化赋值都覆盖）。 */
  (function(){
    function bindClear(inp, bid){
      var b = document.getElementById(bid);
      if(!inp || !b) return;
      b.addEventListener('click', function(){
        try{ inp.value = ''; }catch(e){}
        try{ inp.dispatchEvent(new Event('input', { bubbles: true })); }catch(e2){ try{ run(inp); }catch(e3){} }
        try{ inp.focus(); }catch(e4){}
      });
    }
    bindClear(q, 'tocqc');
    bindClear(q2, 'toc2qc');
    var seen = { A: null, B: null };
    try{ if(q)  seen.A = q.value;  if(q2) seen.B = q2.value; }catch(e){}
    setInterval(function(){
      try{
        if(q  && ASC === 'A' && q.value  !== seen.A){ seen.A = q.value;  run(q);  }
        if(q2 && ASC === 'B' && q2.value !== seen.B){ seen.B = q2.value; run(q2); }
      }catch(e){ om3err(e, "silent"); }
    }, 400);
  })();'''
    return html.replace(old, new, 1)


# ================================================================ ④ ☰ 菜单：分层
@step('④ ☰ 菜单标记：删掉 7 个排查项、加一行"去测试页"、直连文案说清')
def s_menu_html(html):
    a = html.index('<div class="cammdrop hide" id="camMenuDrop">')
    b = html.index('</div>', html.index('data-act="map"'))
    seg = html[a:b]
    DIAG = ['copylog', 'dllog', 'clearlog', 'perm', 'bardiag', 'prof', 'map']
    keep = []
    dropped = []
    for line in seg.split('\n'):
        if any(('data-act="%s"' % d) in line for d in DIAG):
            dropped.append(line.strip())               # 排查项：搬到测试页
            continue
        keep.append(line)
    assert len(dropped) == len(DIAG), '要删的排查项数不对：%d（应为 %d）' % (len(dropped), len(DIAG))
    for d in DIAG:
        assert sum(1 for l in dropped if ('data-act="%s"' % d) in l) == 1, '菜单项 %s 没找到或重复' % d
    seg2 = '\n'.join(keep)
    seg2 = seg2.replace('>直连相机 Wi-Fi（已开热点时）<', '>相机 Wi-Fi 已开 → 直接连（跳过扫描）<')
    # ⚠ 第 68 轮**已经**有一个 data-act="test" 的菜单项了 —— 这里只**改它的文案**，绝不新增第二个
    assert seg2.count('data-act="test"') == 1, 'test 菜单项不是恰好 1 个（本轮只改文案，不加新的）'
    seg2 = seg2.replace('>🔧 测试页（连接诊断 · 日志在这里复制）<',
                        '>🔧 测试页（连接诊断 · 日志/权限/自检都在那里）<')
    old_sep = '<div class="cammsep"></div>\n      <button type="button" data-act="verify">'
    assert seg2.count(old_sep) == 1
    seg2 = seg2.replace(old_sep,
                        '<!-- r70：复制/下载/清空日志、检查权限、底栏自检、相机档案、首次自检 —— 这 7 项都搬到\n'
                        '           「🔧 测试页」了（那边每项都写清了用途）；菜单里只留客户会用的。 -->\n'
                        '      <button type="button" data-act="verify">', 1)
    return html[:a] + seg2 + html[b:]


@step('④ 菜单处理：抽成 menuAct(a) 统一出口（菜单项与测试页按钮共用）')
def s_menu_js(html):
    a = html.index("    menuDrop.addEventListener('click', function(e){\n      var b = e.target.closest")
    b = html.index('      closeMenu();\n    });', a) + len('      closeMenu();\n    });')
    old = html[a:b]
    # 动作分支：从 `if(a === 'test')` 起（**不含**前面那行 `var s = b.getAttribute(...)` —— 那行属于点击事件，
    # menuAct 只收一个动作字符串，用不到它；留着会引用未定义的 b、还会覆盖参数 a）
    body = old[old.index("      if(a === 'test')"):old.index('      closeMenu();')]
    body = body.replace('\n      ', '\n    ')                    # 缩进对齐（原来在事件回调里，深两格）
    body = body.replace("      if(a === 'test')", "    if(a === 'test')", 1)   # 第一行没有前导换行，单独处理
    body = re.sub(r'\breturn;', 'return true;', body)            # 每支的"处理完了" → 统一返回 true
    new = ('''    menuDrop.addEventListener('click', function(e){
      var b = e.target.closest ? e.target.closest('button') : null;
      if(!b) return;
      var s1 = b.getAttribute('data-step'), a1 = b.getAttribute('data-act');
      if(s1){ showStep(+s1); return; }                 /* data-step 的项 = 切步骤，不进 menuAct */
      /* r70：统一出口 —— 菜单项与**测试页**里的按钮都走 window.__om3menuAct(a)，实现只写一份 */
      window.__om3menuAct(a1);
      closeMenu();
    });''')
    tail = html[b:b + 5]
    assert tail == '\n  }\n', '菜单 if 块的收尾不是预期的 %r（实为 %r）' % ('\\n  }\\n', tail)
    fn = ('''
  /* ===== r70：菜单动作统一实现（原来那段 if/else 链原样搬进来；每支 return true 表示"我处理了"） ===== */
  function menuAct(a){
''' + body + '''    return false;                                    /* 不认识的动作 */
  }
  window.__om3menuAct = menuAct;''')
    return html[:a] + new + tail + fn + html[b + 5:]


# ================================================================ ④ 测试页：补 4 个按钮
@step('④ 测试页：加「原 ☰ 菜单里的排查项」一张卡（4 个按钮，每个写清用途）')
def s_testpage(html):
    old = '''  <div class="camcard">
    <div class="camhd">日志（三步共用这一份；直接复制这一份给我就行）</div>'''
    assert html.count(old) == 1
    new = '''  <div class="camcard">
    <div class="camhd">排查项（原来在「连接相机」的 ☰ 菜单里，现在都搬到这里 —— 每项写清是干嘛的）</div>
    <button type="button" class="bigbtn alt" id="tvPerm">检查权限（相机 / 位置 / 附近的设备 / 蓝牙，缺哪个能一键申请）</button>
    <div class="tvhint">用途：连接失败时先看这条 —— 权限没给全，扫码/连热点/蓝牙唤醒都会失败。结果同时写进下面的日志。</div>
    <button type="button" class="bigbtn alt" id="tvBarDiag">底栏自检（把底栏状态写进日志）</button>
    <div class="tvhint">用途：只有\"底栏按钮少了/不固底\"这类显示问题才需要；结果在日志里。</div>
    <button type="button" class="bigbtn alt" id="tvProf">查看相机档案（本机见过的相机：型号 / 序列号 / 备份情况）</button>
    <div class="tvhint">用途：确认\"这台机器到底算不算连过\"、以及有没有存下 MySet 备份。弹窗展示，读完关掉即可。</div>
    <button type="button" class="bigbtn alt" id="tvMap">首次自检（换机型时跑一次：读一遍相机，标出哪些档/槽是空的）</button>
    <div class="tvhint">用途：换了一台相机时跑一次，之后写入就不会撞到\"原档位不存在\"。只读，不改相机。</div>
    <div class="camout" id="tvAdvOut">（这四个按钮的结果也会进下面的日志）</div>
  </div>

''' + old
    return html.replace(old, new, 1)


@step('④ 测试页 JS：把这 4 个按钮接到 menuAct（同一份实现）')
def s_testpage_js(html):
    old = "    tvBind('tvBack', function(){ var t = $('tabCam'); if(t) t.click(); });"
    assert html.count(old) == 1
    new = old + '''
    /* r70：原来在 ☰ 菜单里的排查项 —— 这里只是换个入口，实现仍走 window.__om3menuAct（不复制） */
    function tvAdv(id, act, what){
      tvBind(id, function(){
        tvOut('（' + what + '）');
        try{ if(window.__om3menuAct) window.__om3menuAct(act); else tvOut('这个版本没有该功能', 'err'); }
        catch(e){ tvOut('出错：' + e.message, 'err'); }
      });
    }
    tvAdv('tvPerm', 'perm', '检查权限：结果写在下面日志里（也写进「连接相机」页的权限卡）');
    tvAdv('tvBarDiag', 'bardiag', '底栏自检：结果在日志里');
    tvAdv('tvProf', 'prof', '相机档案：弹窗展示');
    tvAdv('tvMap', 'map', '首次自检：读一遍相机（只读）');'''
    return html.replace(old, new, 1)


def run(html, check=False):
    changed = []
    for label, fn in STEPS:
        before = html
        try:
            html = fn(html)
        except AssertionError as e:
            raise AssertionError('第「%s」步失败：%s' % (label, e or '锚点没找到（可能页面已被改过）'))
        except ValueError as e:
            raise AssertionError('第「%s」步失败（找不到锚点）：%s' % (label, e))
        if html == before:
            raise AssertionError('这一步什么都没改：' + label)
        changed.append(label)
    if MARK in html:
        raise AssertionError('标记重复')
    html = html.replace('  function menuAct(a){', '  /* %s */\n  function menuAct(a){' % MARK, 1)
    assert MARK in html
    return html, changed


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r70] 已经是目标状态（页面里有 "%s"）—— 不重复改。' % MARK)
        return 0
    try:
        new, changed = run(html)
    except AssertionError as e:
        print('[r70] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r70] --check：%d 步都能跑通（未写盘）：' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(new)
    print('[r70] ✓ 已改 %d 步：搜索清空可靠/固顶、档位推荐搜索框搬家、场景对比贴顶、☰ 菜单分层' % len(changed))
    before = io.open(os.path.join(ROOT, 'app', 'base.before_r70.html'), encoding='utf-8').read()
    print('[r70] 页面净增 %d 字节' % (len(new.encode('utf-8')) - len(before.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
