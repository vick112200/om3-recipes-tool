# -*- coding: utf-8 -*-
"""① 扫码更灵：允许反色 + 全帧失败后做"中心裁剪放大"二次扫描 + 原生/JS 双通道都试
   ② 悬浮连接气泡可收起成小图标（点=收起/展开，长按=去连接相机，位置仍记住）
   ③ 日志/记录类文本域加长（下面没有操作按钮的那类）
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- ① 扫码 ----------
old = """        function canvasTry(){
          if(!(v.readyState === v.HAVE_ENOUGH_DATA && v.videoWidth)) return false;
          var sc = Math.min(1, MAXW / Math.max(v.videoWidth, v.videoHeight));
          var w = Math.max(1, Math.round(v.videoWidth * sc)), hh = Math.max(1, Math.round(v.videoHeight * sc));
          if(!fixed || c.width !== w || c.height !== hh){    /* 只设一次，避免每帧重建画布造成越来越卡 */
            c.width = w; c.height = hh; fixed = true;
          }
          ctx.drawImage(v, 0, 0, w, hh);
          try{
            var img = ctx.getImageData(0, 0, w, hh);
            var f = window.jsQR(img.data, img.width, img.height, {inversionAttempts:'dontInvert'});
            return hit(f && f.data);
          }catch(e){ return false; }
        }"""
assert h.count(old) == 1, h.count(old)
new = """        function tryDecode(sx, sy, sw, sh, targetW){
          var sc = Math.min(1, targetW / Math.max(sw, sh));
          var w = Math.max(1, Math.round(sw * sc)), hh = Math.max(1, Math.round(sh * sc));
          if(!fixed || c.width !== w || c.height !== hh){ c.width = w; c.height = hh; fixed = true; }
          ctx.drawImage(v, sx, sy, sw, sh, 0, 0, w, hh);
          try{
            var img = ctx.getImageData(0, 0, w, hh);
            /* 允许反色：屏幕上拍的二维码经常是"白码黑底"，不试反色就会一直扫不出 */
            var f = window.jsQR(img.data, img.width, img.height, {inversionAttempts:'attemptBoth'});
            return hit(f && f.data);
          }catch(e){ return false; }
        }
        var pass2 = 0;
        function canvasTry(){
          if(!(v.readyState === v.HAVE_ENOUGH_DATA && v.videoWidth)) return false;
          var VW = v.videoWidth, VH = v.videoHeight;
          /* 第一遍：整帧 */
          if(tryDecode(0, 0, VW, VH, MAXW)) return true;
          /* 第二遍（每隔一次）：中心 60% 裁剪后放大，专治"二维码在画面里偏小/偏远" */
          pass2 = (pass2 + 1) % 2;
          if(pass2 === 0){
            var cw = Math.round(VW * 0.6), chh = Math.round(VH * 0.6);
            if(tryDecode(Math.round((VW - cw) / 2), Math.round((VH - chh) / 2), cw, chh, Math.round(MAXW * 1.4))) return true;
          }
          return false;
        }"""
h = h.replace(old, new, 1)
# 原生通道也放宽：每 100ms 试一次（更快抓到）
h = h.replace("if(BD && !busy && (now - lastT) > 120){", "if(BD && !busy && (now - lastT) > 100){", 1)
h = h.replace("var MAXW = BD ? 640 : 520;", "var MAXW = BD ? 720 : 700;", 1)

# ---------- ② 气泡可收起 ----------
old_tap = """      if(!moved){ try{ document.getElementById('tabCam').click(); }catch(e){} }"""
assert h.count(old_tap) == 1, h.count(old_tap)
new_tap = """      if(!moved){
        /* 点一下 = 收起/展开；长按(按住不动 500ms) = 去「连接相机」 */
        if(Date.now() - downAt > 500){ try{ document.getElementById('tabCam').click(); }catch(e){} }
        else { om3BadgeToggle(); }
      }"""
h = h.replace(old_tap, new_tap, 1)
# downAt 记录
h = h.replace("      dragging = true; moved = false;", "      dragging = true; moved = false; downAt = Date.now();", 1)
h = h.replace("    var K = 'om3fabc', moved = false, sx = 0, sy = 0, ox = 0, oy = 0, dragging = false;",
              "    var K = 'om3fabc', moved = false, sx = 0, sy = 0, ox = 0, oy = 0, dragging = false, downAt = 0;", 1)

anchor_badge = "  window.__om3gStatus = gStatus;"
assert h.count(anchor_badge) == 1
h = h.replace(anchor_badge, anchor_badge + """
  /* 状态气泡：可收起成一个小图标（收起状态记在本机） */
  var _badgeMini = false;
  function om3BadgeApply(){
    var el = document.getElementById('gStatusBar');
    if(!el) return;
    el.classList.toggle('mini', _badgeMini);
    if(_badgeMini){
      el.textContent = el.classList.contains('on') ? '📷' : '📷';
      el.title = '点一下展开连接状态（长按去连接相机）';
    } else {
      el.title = '点一下收起为小图标；长按去连接相机';
    }
    var st = document.getElementById('gStatusWrap') || el;
    try{ localStorage.setItem('om3badge', _badgeMini ? '1' : '0'); }catch(e){}
  }
  function om3BadgeToggle(){
    _badgeMini = !_badgeMini;
    om3BadgeApply();
    if(!_badgeMini){ try{ window.__om3gStatusTick && window.__om3gStatusTick(); }catch(e){} }
  }
  window.__om3badgeToggle = om3BadgeToggle;
  try{ _badgeMini = (localStorage.getItem('om3badge') === '1'); }catch(e){}
  setTimeout(om3BadgeApply, 800);""", 1)

# 收起时的样式
k = h.find('</style>')
h = h[:k] + """
.gstatus.mini{padding:7px 10px;border-radius:999px;font-size:14px;line-height:1;letter-spacing:0}
""" + h[k:]

# gStatus 刷新时保持收起态
old_g = """    var short = String(txt).replace('未连接相机（点这里去连接）', '未连接');
    e.textContent = (on ? '📷 ' : '📷 ') + short;
    e.classList.toggle('on', !!on);"""
assert h.count(old_g) == 1, h.count(old_g)
h = h.replace(old_g, """    var short = String(txt).replace('未连接相机（点这里去连接）', '未连接');
    if(e.classList.contains('mini')){ e.textContent = '📷'; }
    else { e.textContent = '📷 ' + short; }
    e.classList.toggle('on', !!on);""", 1)

# ---------- ③ 文本域加长 ----------
h = h.replace('.camout{', '.camout{max-height:46vh !important;', 1) if '.camout{' in h else h
for old_css in ['.camout{background:#111;border:1px solid #262626;border-radius:8px;padding:8px;font-size:12px;max-height:240px;overflow-y:auto;white-space:pre-wrap}',
                '.camout{max-height:240px;overflow-y:auto}']:
    if h.count(old_css) == 1:
        h = h.replace(old_css, old_css.replace('240px', '46vh'), 1)
        print('已加长 .camout')
k = h.find('</style>')
h = h[:k] + """
/* 下面没有操作按钮的文本域/日志：加长显示，少滚动 */
.camout, #camOut3, #mpFileOut{max-height:46vh !important}
textarea{min-height:38vh}
""" + h[k:]

open(P, 'w', encoding='utf-8', newline='').write(h)
print('扫码/气泡/文本域 三项已改（%+d 字节）' % (len(h) - n0))
