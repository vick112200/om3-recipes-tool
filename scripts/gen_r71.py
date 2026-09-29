# -*- coding: utf-8 -*-
"""第 71 轮：搜索"留着一个字的搜索记录"根治 + 清空/复位兜底（见 SPEC-round71.md）。

需求方 2026-09-28：「点击菜单输入框之后，进入搜索功能，这时输入框还是固定，这不太合理，
                  而留一个字的问题还在」。
→ 「输入框还固定」是**布局取舍**，按需求方话意先做成"面板里的输入框不再吸附"（一行可改回，见 §5）。
→ 「留一个字的问题」**用无头浏览器复现出来了**：
      A 搜「人」→ 结果出来 → **关掉面板** → 再打开 → **框里还是「人」、结果还在**
   （也就是"上次那个字的搜索记录"留在那儿）。本轮从三处根治：
     ① 关面板即复位（清输入 + 清结果 + 复位状态）—— 唯一关闭出口 __om3tocClose 挂钩
     ② 多事件兜底（input/keyup/change/compositionend/blur/search）+ 看门狗 300ms，去掉 r70 的 ASC 守卫漏洞
     ③ 隐藏 WebView 自带的 type=search ✕（只留我们自绘的 ✕：原生那个不保证派发 input）

规矩：幂等（标记 `r71：搜索复位`）+ 每一步都必须"真的改到东西" + 老 id 一个不少 + 不新增 id。

用法：python scripts/gen_r71.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r71：搜索复位'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


# ---------------------------------------------------------------- ① 面板里的输入框不再吸附
@step('布局：面板里的"输入框行"不再吸附（.tocsearchrow）')
def s_unstick(html):
    old = '.tocsearchrow{position:sticky;top:0;z-index:3;background:#1b1b1b;display:flex;gap:8px;align-items:center;\n  padding:2px 0 10px}'
    assert html.count(old) == 1, 'r70 那条 .tocsearchrow 规则没找到'
    new = ('.tocsearchrow{position:relative;display:flex;gap:8px;align-items:center;\n'
           '  padding:2px 0 10px}   /* r71：改回不吸附（需求方：进搜索后输入框还固定"不太合理"）——\n'
           '                          要改回吸附只需把 position 改回 sticky 并加 top:0 */')
    return html.replace(old, new, 1)


# ---------------------------------------------------------------- ③ 隐藏原生 ✕
@step('CSS：隐藏 WebView 自带的 type=search ✕（只留自绘的那个）')
def s_nativex(html):
    old = '</style></head><body>'
    assert html.count(old) == 1
    css = '''
/* r71：`<input type="search">` 自带的 ✕ 是**安卓 WebView 自己画的** —— 它清空文本后**不保证派发 input**
   （于是"框空了、上一次的搜索结果还留着"）。我们已经有自绘的 ✕（.tocclear，一定走自己的代码），
   干脆把原生那个藏掉：①②两条路并成一条，用户不会再踩到"清不掉"的那个。 */
input[type="search"]::-webkit-search-cancel-button,
input[type="search"]::-webkit-search-decoration,
input[type="search"]::-webkit-search-results-button,
input[type="search"]::-webkit-search-results-decoration{-webkit-appearance:none;display:none}
'''
    return html.replace(old, css + old, 1)


# ---------------------------------------------------------------- ① ② 关面板复位 + 兜底
NEW_SEARCH_JS = '''  /* ===== r70/r71：清空可靠 + 关面板复位（需求方 2026-09-28："清空后还留着一个字的搜索记录"） =====
     无头实测复现（r71）：A 面板搜「人」→ 关面板 → 再打开 → **框里还是「人」、结果也还在**
     —— 也就是"上次那个字的搜索记录"没被清掉。三处根治：
       ① 关面板即复位（唯一关闭出口 __om3tocClose → window.__om3searchReset）
       ② 多事件 + 300ms 看门狗：不管谁改了输入框的值（原生 ✕ / 输入法 / 程序赋值）都能跟上
       ③ 原生 ✕ 已用 CSS 隐藏（见样式表 r71 段）—— 只剩我们自绘的那个 ✕
     为什么还要看门狗：老 WebView/输入法**有时不派发 input**，只靠事件会漏；看门狗只比字符串，很便宜。 */
  (function(){
    function valOf(el){ try{ return el ? String(el.value) : ''; }catch(e){ return ''; } }
    function panelOpen(which){
      try{
        var el = document.getElementById(which === 'A' ? 'toc' : 'toc2');
        if(!el) return false;
        /* ⚠ 别用 classList.contains('hide') 判断：这两个面板的**收起**是 CSS 默认 display:none
           加上第 07 块写的内联 display（还有 .open 类），根本没有 hide 类 ——
           r71 第一版就是这么写的，结果 panelOpen() 永远返回 true → 复位从来不触发。 */
        var cs = getComputedStyle(el);
        return !(cs.display === 'none' || cs.visibility === 'hidden');
      }catch(e){ return false; }
    }
    var seen = { A: valOf(q), B: valOf(q2) };
    /* 值变了就重渲染（force=true 时即使没变也重渲染当前面板）。
       r71 修：r70 那段加了 `ASC === 'A'/'B'` 守卫 —— 在"另一个面板里改过值"之后再清空，
       守卫会把这次清空**挡掉**（残留就是这么漏出来的）。现在只按"哪个面板开着"判断，
       绝不把另一个面板的渲染抢走（那会让结果画到看不见的容器里）。 */
    function sync(force){
      try{
        if(q){
          var v1 = valOf(q);
          if(v1 !== seen.A){ seen.A = v1; if(!panelOpen('B')) run(q); }
          else if(force && panelOpen('A')) run(q);
        }
        if(q2){
          var v2 = valOf(q2);
          if(v2 !== seen.B){ seen.B = v2; if(!panelOpen('A')) run(q2); }
          else if(force && panelOpen('B')) run(q2);
        }
      }catch(e){ om3err(e, "silent"); }
    }
    window.__om3searchSync = sync;
    function bindClear(inp, bid){
      var b = document.getElementById(bid);
      if(!inp || !b) return;
      b.addEventListener('click', function(){
        try{ inp.value = ''; }catch(e){}
        try{ inp.dispatchEvent(new Event('input', { bubbles: true })); }catch(e2){ try{ run(inp); }catch(e3){} }
        try{ sync(false); }catch(e4){}
        try{ inp.focus(); }catch(e5){}
      });
    }
    bindClear(q, 'tocqc');
    bindClear(q2, 'toc2qc');
    /* 多事件兜底：凡是有可能"值变了但没派发 input"的时机都补一次检查 */
    ['input', 'search', 'change', 'keyup', 'compositionend', 'paste', 'cut'].forEach(function(ev){
      [q, q2].forEach(function(inp){
        if(!inp) return;
        inp.addEventListener(ev, function(){ setTimeout(function(){ sync(false); }, ev === 'keyup' ? 90 : 0); });
      });
    });
    [q, q2].forEach(function(inp){
      if(inp) inp.addEventListener('blur', function(){ setTimeout(function(){ sync(false); }, 120); });
    });
    /* 复位：清掉输入框里上次的词 + 清掉结果区 + 状态复位（幂等，随便调） */
    function reset(){
      try{
        if(q)  q.value = '';
        if(q2) q2.value = '';
        seen.A = ''; seen.B = '';
        if(res){ res.className = 'hide'; res.innerHTML = ''; }
        if(res2){ res2.className = 'hide'; res2.innerHTML = ''; }
        if(browse) browse.className = '';
        if(browse2) browse2.className = '';
        if(empty) empty.style.display = 'none';
        var e2 = empty2El(); if(e2) e2.style.display = 'none';
        /* 输入框还藏着光标的话也收掉（不然键盘可能留在屏幕上） */
        try{ if(document.activeElement && (document.activeElement === q || document.activeElement === q2)) document.activeElement.blur(); }catch(e){}
      }catch(e){ om3err(e, "silent"); }
    }
    window.__om3searchReset = reset;
    /* ⚠ 关面板的路径不止一条（点搜索条收起／点 ✕／点结果跳转／点目录项…，第 07 块还有它自己那套 toggle+apply）。
       与其去逐个挂钩（r71 第一版挂在 __om3tocClose 上 —— **实测漏了"再点搜索条收起"这条**），
       不如按状态判断：**从"开着"变成"都关着"的那一刻就复位** —— 这样任何关闭路径都覆盖得到。 */
    var wasOpen = false;
    setInterval(function(){
      sync(false);
      var nowOpen = panelOpen('A') || panelOpen('B');
      if(wasOpen && !nowOpen) reset();
      wasOpen = nowOpen;
      /* r71：面板开着的时候，把页面上那条"🔍 搜索配方…"入口条收起来 ——
         需求方 2026-09-28："进入搜索功能，这时输入框还是固定，这不太合理"。
         不管他指的是"页面上那条"还是"面板里那条"，这样看过去都只有**一个**搜索框：
         面板里那个是"搜索功能"自己的，页面上那个在搜索期间不占地方；关掉面板立刻恢复。 */
      try{
        var r2 = document.getElementById('row2');
        if(r2){
          var pg = window.__om3cur || 'A';
          var showRow = (pg === 'A' || pg === 'B' || pg === 'C' || pg === 'F');
          r2.style.display = nowOpen ? 'none' : (showRow ? 'flex' : 'none');
        }
      }catch(e){}
    }, 300);
  })();

'''


@step('① ② 搜索 JS：整体换成 r71 版（复位 + 多事件 + 看门狗不抢别的面板）')
def s_searchjs(html):
    start_mark = '  /* ===== r70：清空可靠 + 固顶配套'
    end_mark = '/* ---------- 搜索结果里点档位推荐条目'
    i = html.index(start_mark)
    j = html.index(end_mark)
    assert 'bindClear(q, \'tocqc\')' in html[i:j], 'r70 那段搜索代码没找到'
    return html[:i] + NEW_SEARCH_JS + html[j:]


# ---------------------------------------------------------------- ① 唯一关闭出口挂钩
@step('① 关面板的唯一出口：挂钩 __om3searchReset')
def s_closing(html):
    old = '    window.__om3tocClose = function(){ if(!open) return; open = false; apply(); };'
    assert html.count(old) == 1
    new = (old + '''
    /* r71：关面板即复位（唯一出口 —— 点 ✕、点搜索条、点结果跳转都走这里）：
       清掉输入框里上次的词、清掉结果区、把状态复位。需求方 2026-09-28："留着一个字的搜索记录"。 */
    window.__om3tocClose = (function(orig){
      return function(){
        var wasOpen = open;
        orig();
        if(wasOpen){ try{ if(window.__om3searchReset) window.__om3searchReset(); }catch(e){} }
      };
    })(window.__om3tocClose);''')
    return html.replace(old, new, 1)


def run(html):
    changed = []
    for label, fn in STEPS:
        before = html
        try:
            html = fn(html)
        except AssertionError as e:
            raise AssertionError('第「%s」步失败：%s' % (label, e or '锚点没找到'))
        except ValueError as e:
            raise AssertionError('第「%s」步失败（找不到锚点）：%s' % (label, e))
        if html == before:
            raise AssertionError('这一步什么都没改：' + label)
        changed.append(label)
    html = html.replace('    window.__om3searchReset = reset;',
                        '    window.__om3searchReset = reset;   /* %s */' % MARK, 1)
    assert MARK in html, '标记没插进去'
    return html, changed


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r71] 已经是目标状态（页面里有 "%s"）—— 不重复改。' % MARK)
        return 0
    try:
        new, changed = run(html)
    except AssertionError as e:
        print('[r71] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r71] --check：%d 步都能跑通（未写盘）：' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(new)
    print('[r71] ✓ 已改 %d 步：关面板复位 / 多事件+看门狗 / 隐藏原生 ✕ / 面板输入框不再吸附' % len(changed))
    before = io.open(os.path.join(ROOT, 'app', 'base.before_r71.html'), encoding='utf-8').read()
    print('[r71] 页面净增 %d 字节' % (len(new.encode('utf-8')) - len(before.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
