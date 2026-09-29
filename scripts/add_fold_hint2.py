# -*- coding: utf-8 -*-
"""折叠按钮改成「两行说明式」，并取消打开时自动弹气泡。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()

# ---------- 1. CSS ----------
i = h.find('#foldbar{position:fixed')
j = h.find('#foldtip:after{')
j = h.find('}', j) + 1
assert 0 < i < j
NEW_CSS = ('''#foldbar{position:fixed;right:14px;bottom:64px;display:none;gap:8px;align-items:center;z-index:48}
#foldbar.on{display:flex}
#foldinfo{height:34px;padding:0 12px;border-radius:17px;background:#242424;color:#8fd8c2;border:1px solid #3a3a3a;font-size:12px;font-family:inherit;cursor:pointer;box-shadow:0 3px 12px #0008;white-space:nowrap}
#foldinfo:active{background:#2f8f74;color:#fff}
#foldbtn{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:6px 15px;border-radius:15px;background:#2f8f74;color:#fff;border:0;font-family:inherit;cursor:pointer;box-shadow:0 3px 12px #0008;white-space:nowrap;line-height:1.3}
#foldbtn:active{background:#26735e}
#foldbtn .fb1{font-size:12.5px;font-weight:700}
#foldbtn .fb2{font-size:10px;color:#cdeee2;margin-top:1px}
#foldtip{position:fixed;right:14px;bottom:118px;width:min(330px,calc(100vw - 28px));background:#232a2e;border:1px solid #3a4a52;border-left:3px solid #2f8f74;border-radius:10px;padding:12px 14px;font-size:12.5px;line-height:1.75;color:#cfe0d8;z-index:49;box-shadow:0 8px 26px #000b;display:none}
#foldtip.on{display:block}
#foldtip b{color:#8fd8c2}
#foldtip .ftclose{margin-top:9px;background:#2f8f74;color:#fff;border:0;border-radius:7px;padding:6px 13px;font-size:12.5px;font-family:inherit;cursor:pointer}
#foldtip:after{content:"";position:absolute;right:20px;bottom:-7px;width:12px;height:12px;background:#232a2e;border-right:1px solid #3a4a52;border-bottom:1px solid #3a4a52;transform:rotate(45deg)}''')
h = h[:i] + NEW_CSS + h[j:]

# ---------- 2. 手机端覆盖 ----------
i = h.find('#foldbar{bottom:60px;right:12px;gap:7px}')
if i > 0:
    j = h.find('#foldtip{bottom:104px;right:12px;font-size:12.5px;line-height:1.7}')
    j = h.find('\n', j) if j > 0 else -1
    assert j > i
    h = h[:i] + ('''#foldbar{bottom:60px;right:10px;gap:6px}
  #foldinfo{height:32px;padding:0 10px;font-size:11.5px}
  #foldbtn{padding:5px 12px;border-radius:14px}
  #foldbtn .fb1{font-size:12px}
  #foldbtn .fb2{font-size:9.5px}
  #foldtip{bottom:106px;right:10px;line-height:1.7}''') + h[j:]

# ---------- 3. 标记 + 脚本 ----------
i = h.find('<div id="foldbar">')
assert i > 0
j = h.find('</script>', i) + len('</script>')
assert j > i

NEW_BLOCK = '''<div id="foldbar">
  <button id="foldinfo" type="button">说明</button>
  <button id="foldbtn" type="button"><span class="fb1">展开全部</span><span class="fb2">原文 · 补充 · 说明</span></button>
</div>
<div id="foldtip" role="status">
  <b>说明段落默认是收起的。</b><br>
  · 每条折叠标题（如「补充 · 画面感觉」）<b>点一下单独展开</b>，标题里已经带了最关键的一句预览，扫一眼通常就够；<br>
  · 按钮上写的「原文 · 补充 · 说明」就是被折叠的三类内容，点它可以<b>一次展开 / 折叠当前页签的全部说明</b>；<br>
  · 按钮下面那行小字是当前页签里三类各有多少条。
  <br><button class="ftclose" id="foldtipclose" type="button">知道了</button>
</div>
<script>
(function () {
  var bar = document.getElementById('foldbar');
  var btn = document.getElementById('foldbtn');
  var info = document.getElementById('foldinfo');
  var tip = document.getElementById('foldtip');
  var closeBtn = document.getElementById('foldtipclose');
  if (!bar || !btn) return;

  var lab1 = btn.querySelector('.fb1');
  var lab2 = btn.querySelector('.fb2');

  function pane() {
    var ps = document.querySelectorAll('.pane');
    for (var i = 0; i < ps.length; i++) {
      if (!ps[i].classList.contains('hide')) return ps[i];
    }
    return document.body;
  }
  function folds() { return pane().querySelectorAll('details.fold'); }

  function sync() {
    var f = folds();
    if (!f.length) { bar.classList.remove('on'); return; }
    bar.classList.add('on');
    var n1 = 0, n2 = 0, n3 = 0, open = 0;
    for (var i = 0; i < f.length; i++) {
      var c = f[i].classList;
      if (c.contains('fnote')) n1++;
      else if (c.contains('fmine')) n2++;
      else n3++;
      if (f[i].open) open++;
    }
    lab1.textContent = (open >= f.length) ? '\\u6298\\u53e0\\u5168\\u90e8' : ('\\u5c55\\u5f00\\u5168\\u90e8 \\u00b7 ' + f.length);
    var parts = [];
    if (n1) parts.push('\\u539f\\u6587 ' + n1);
    if (n2) parts.push('\\u8865\\u5145 ' + n2);
    if (n3) parts.push('\\u8bf4\\u660e ' + n3);
    lab2.textContent = parts.join(' \\u00b7 ') || '\\u539f\\u6587 \\u00b7 \\u8865\\u5145 \\u00b7 \\u8bf4\\u660e';
  }

  btn.addEventListener('click', function () {
    var f = folds();
    var open = 0;
    for (var i = 0; i < f.length; i++) if (f[i].open) open++;
    var want = open < f.length;
    for (var k = 0; k < f.length; k++) f[k].open = want;
    sync();
  });

  document.addEventListener('toggle', function (e) {
    if (e.target && e.target.classList && e.target.classList.contains('fold')) sync();
  }, true);
  // 切页签后刷新统计
  document.addEventListener('click', function () { setTimeout(sync, 60); }, false);

  function hideTip() { tip.classList.remove('on'); }
  function showTip() { tip.classList.add('on'); }
  info.addEventListener('click', function () {
    if (tip.classList.contains('on')) hideTip(); else showTip();
  });
  closeBtn.addEventListener('click', hideTip);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') hideTip();
  });

  sync();
})();
</script>'''

h = h[:i] + NEW_BLOCK + h[j:]
open(P, 'w', encoding='utf-8', newline='').write(h)
print('折叠按钮已改成两行说明式；取消了自动弹气泡')
