# -*- coding: utf-8 -*-
"""第 72 轮：修「搜索按钮上面的字，点进去就没了」（见 SPEC-round72.md）。

需求方 2026-09-28：「而且本来这个搜索按钮上面有字，点进去就没了，你如果搞不定你搞个前端组件库吧」。

**真因（无头实测钉住，不是猜的）**
    #tocbtn 的结构是：<div id="tocbtn" class="searchbar"><span class="sic">🔍</span><span class="stx">搜索配方 · 作者 · 场景，或打开目录</span></div>
    而老代码开/关面板时写的是 `btn.textContent = o ? '✕' : '🔍';`（第 1940 行）和 `btn.textContent='🔍';`（close() 里）
    —— **textContent 一写，两个 span 连同那句文字就被永久抹掉**。
    走的正是"搜出结果 → 点一条结果跳转"这条路（它会调 close()）。实测：
        A7 点结果跳转后 图标=[(没有)] 文字=[(没有)]      ← 按钮成了空的，只有个裸图标
本轮：
   ① 统一走 setTocBtn(open)：只切图标 + 切一个 .on 类，**文字永远不动**；结构万一已被抹过会**自愈重建**
   ② 开/关状态由"唯一状态作用点"（块07 的 apply()）统一推送 → 所有路径（点入口条/点✕关闭/点结果跳转）都一致
   ③ 顺手把第 71 轮那笔"面板打开时把入口条藏起来"**撤回**（需求方要的是"上面有字"）

规矩：幂等（标记 `r72：搜索按钮文字`）+ 每步必须真的改到东西 + 老 id 一个不少 + 本轮不新增 id。

用法：python scripts/gen_r72.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r72：搜索按钮文字'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


# ---------------------------------------------------------------- ① setTocBtn
@step('① 加 setTocBtn(open)：只切图标 + 自愈重建（文字不动）')
def s_setbtn(html):
    old = " function close(){if(nav)nav.classList.remove('open');if(nav2)nav2.classList.remove('open');btn.textContent='\\ud83d\\udd0d';"
    assert html.count(old) == 1, 'close() 那条锚点没找到'
    new = '''  /* ===== r72：搜索按钮上的字不许被抹掉（需求方 2026-09-28："本来这个搜索按钮上面有字，点进去就没了"） =====
     #tocbtn 是「🔍 + 说明文字」两段结构（.sic / .stx），而老代码开/关时写的是
         btn.textContent = '✕' / '🔍'
     —— textContent 一写，两个 span 连同那句说明**永久**就没了（点一条搜索结果跳转会走 close()）。
     现在统一走 setTocBtn(open)：只改图标那一小段 + 切一个 .on 类，**文字永远是那句**；
     并且做**自愈**：万一结构已经被抹过（老版本动过、或别的代码动过），照原样重建回来。 */
  var TOC_LABEL = '搜索配方 · 作者 · 场景，或打开目录';
  function setTocBtn(o){
    try{
      if(!btn) return;
      var ic = btn.querySelector('.sic'), tx = btn.querySelector('.stx');
      if(!ic || !tx){                        /* 自愈：结构没了就重建 */
        btn.innerHTML = '<span class="sic">\\ud83d\\udd0d</span><span class="stx">' + TOC_LABEL + '</span>';
        ic = btn.querySelector('.sic'); tx = btn.querySelector('.stx');
      }
      if(tx) tx.textContent = TOC_LABEL;     /* 文字开/关都是这一句 —— 不再变来变去 */
      if(ic) ic.textContent = o ? '\\u2715' : '\\ud83d\\udd0d';
      if(o) btn.classList.add('on'); else btn.classList.remove('on');
      try{ btn.setAttribute('aria-expanded', o ? 'true' : 'false'); }catch(e1){}
    }catch(e){
      /* 极端兜底：连 span 都建不出来时，退回老写法（至少还有个图标可点） */
      try{ btn.textContent = o ? '\\u2715' : '\\ud83d\\udd0d'; }catch(e2){}
    }
  }
  window.__om3tocSetBtn = setTocBtn;
  function close(){if(nav)nav.classList.remove('open');if(nav2)nav2.classList.remove('open');setTocBtn(false);'''
    return html.replace(old, new, 1)


@step('① close() 与点击处理都不再写 textContent')
def s_notext(html):
    old = "   btn.textContent=o?'\\u2715':'\\ud83d\\udd0d';\n"
    assert html.count(old) == 1, '点击处理里那条 textContent 没找到'
    new = "    setTocBtn(o);            /* r72：只切图标，别碰文字 */\n"
    return html.replace(old, new, 1)


# ---------------------------------------------------------------- ② apply() 统一推送状态
@step('② 块07 的 apply() 统一推送按钮状态（所有开关路径都一致）')
def s_apply(html):
    old = "      var b = $('tocbtn');\n      if(b) b.setAttribute('aria-expanded', open ? 'true' : 'false');\n"
    assert html.count(old) == 1, 'apply() 里的 tocbtn 那段没找到'
    new = (old +
           "      /* r72：按钮长什么样也在这里统一作用（点入口条／点「✕ 关闭」／点结果跳转／__om3tocClose 都汇到 apply()）。 */\n"
           "      try{ if(window.__om3tocSetBtn) window.__om3tocSetBtn(open); }catch(e4){}\n")
    return html.replace(old, new, 1)


# ---------------------------------------------------------------- ③ 撤回 r71 的"藏入口条"
@step('③ 撤回第 71 轮那笔"面板打开时把入口条藏起来"（需求方要的是上面有字）')
def s_unhide(html):
    a = html.index("      /* r71：面板开着的时候，把页面上那条")
    b = html.index('    }, 300);', a)
    assert 'r2.style.display' in html[a:b], 'r71 那段藏入口条的代码没找到'
    new = ('''      /* r72：**撤回**第 71 轮那笔"面板打开时把入口条藏起来" ——
         需求方 2026-09-28 说的是"本来这个搜索按钮上面有字，点进去就没了"，
         那条入口条正是 `#row2 > #tocbtn`（🔍 + 「搜索配方 · 作者 · 场景，或打开目录」）。
         面板本身是 fixed + z-index 49，已经盖在入口条（z-index 45）上面，不需要再藏。 */
''')
    return html[:a] + new + html[b:]


# ---------------------------------------------------------------- .on 样式
@step('④ .searchbar.on 的样式（开/关看得出来，且不动文字宽度）')
def s_css(html):
    old = '.row2 .searchbar:active{background:#202020;border-color:#3a3a3a}'
    assert html.count(old) == 1
    new = (old + '\n'
           '.row2 .searchbar.on{border-color:#3a4a66;background:#1d2026}          /* r72：面板开着时的样子 */\n'
           '.row2 .searchbar.on .sic{opacity:1}')
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
    html = html.replace('  function setTocBtn(o){',
                        '  function setTocBtn(o){   /* %s */' % MARK, 1)
    assert MARK in html, '标记没插进去'
    return html, changed


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r72] 已经是目标状态（页面里有 "%s"）—— 不重复改。' % MARK)
        return 0
    try:
        new, changed = run(html)
    except AssertionError as e:
        print('[r72] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r72] --check：%d 步都能跑通（未写盘）：' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(new)
    print('[r72] ✓ 已改 %d 步：搜索按钮文字不再被抹掉 / 状态统一推送 / 撤回藏入口条' % len(changed))
    before = io.open(os.path.join(ROOT, 'app', 'base.before_r72.html'), encoding='utf-8').read()
    print('[r72] 页面净增 %d 字节' % (len(new.encode('utf-8')) - len(before.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
