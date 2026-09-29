# -*- coding: utf-8 -*-
"""第 48 轮生成器（幂等）· v3.2

用户 2026-09-25 提的两件：
  ① 「这个版本扫描二维码一直扫不出」
     追问答复：浮层开了、有实时画面，但一直认不出；诊断行「帧在涨 · 识别尝试也在涨，就是不认出来」
     → 根因（读代码找到的真缺陷）：
        ①-a 取景只要 640x480（拍相机屏幕，像素本来就紧）
        ①-b `var sc = Math.min(1, …)` —— 注释写「裁剪后放大」，其实**永远不会 >1**，从不放大
              ⇒ 只占画面 1/3 的二维码（≈200px、每模块 2~3 像素）jsQR 认不出
        ①-c 两个失败模式是静默的（没画面 / 一直认不出）
  ② 「参考下世面上的扫码界面，你这个界面看着都不太对，我建议放大一点画面」
     → 浮层从「420px 小卡片」改成「全屏取景」：画面铺满 + 中间取景窗 + 窗外汇暗 + 底部按钮行

本脚本改 4 处（全部幂等；判定用**只属于新代码的短标记** —— r47 用"整段新文本"判定踩过坑）：
  A. CSS：全屏取景样式（.scanbox/.scanwin/.scantop/.scanbot/.scanbtns）
  B. 标记：扫码浮层改成全屏结构（旧 id 一个不改，新增 scanManual/scanDiag/scanTop）
  C. 块07 识别率：取景 1280x720 + 裁剪那几遍**真的放大**（×2/×3）+ 每 3 轮「原图」那遍
  D. 块07 可见性：诊断行加「画面 WxH」+ 每 2 秒进日志 + 「复制诊断」按钮 + 没画面/认不出的提示
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
P = os.path.join(ROOT, 'app', 'base.html')
LOG = []

s = io.open(P, encoding='utf-8').read()
bak = os.path.join(ROOT, 'app', 'base.before_r48.html')
if not os.path.exists(bak):
    io.open(bak, 'w', encoding='utf-8', newline='').write(s)
    print('回退点已存：app/base.before_r48.html（= v3.1 源码）')


def rep(old, new, tag, marker):
    """唯一锚点替换。marker = 只属于新代码的短标记：在 → 说明改过了，跳过。"""
    global s
    if marker in s:
        LOG.append('  · 已改过，跳过：' + tag)
        return
    n = s.count(old)
    if n != 1:
        LOG.append('  ✗ 锚点不唯一（%d 处）：%s' % (n, tag))
        raise SystemExit('锚点不唯一：' + tag)
    s = s.replace(old, new)
    LOG.append('  ✓ ' + tag)


# ================================================================ A. CSS
rep(
    '.scanmask{position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:80;display:flex;'
    'align-items:center;justify-content:center;padding:16px}\n'
    '.scanmask.hide{display:none !important}   /* 关键：否则这片遮罩会一直盖在页面上（隐藏类被 display:flex 压掉） */\n'
    '.scanbox{width:100%;max-width:420px;background:#1b1b1b;border:1px solid #2e2e2e;border-radius:14px;padding:14px}\n'
    '.scanhd{font-size:14px;font-weight:700;color:#fff;margin-bottom:10px}\n'
    '.scanbox video{width:100%;border-radius:10px;background:#000;display:block;aspect-ratio:4/3;object-fit:cover}\n'
    '.scanbox button{margin-top:10px;background:#2a2a2a;color:#e8e8e8;border:1px solid #3a3a3a;'
    'border-radius:8px;padding:9px 14px;font-size:13.5px;font-family:inherit;cursor:pointer}',
    '/* ===== 第 48 轮：扫码浮层改成「全屏取景」（照主流扫码界面：满屏画面 + 中间取景窗 + 窗外汇暗）=====\n'
    '   用户 2026-09-25：「参考下世面上的扫码界面…我建议放大一点画面」——\n'
    '   原来是 420px 小卡片居中，video 实际只有约 390x293（≈视口的 26%）。 */\n'
    '.scanmask{position:fixed;inset:0;background:#000;z-index:9200;display:block}\n'
    '/* ↑ 层高：底栏（.barABC/.barD/.mpbar）是 fixed + z-index:9000，扫码浮层原来只有 80 —— 以前是居中卡片\n'
    '   所以没撞上；改成全屏取景后，底部那排按钮正好落在底栏底下**点不到**（命中测试抓出来的）。\n'
    '   9200 压在底栏与 #top/#foldbar(9050) 之上、又在 toast(9300)/taskpill(9400)/弹窗(9500+) 之下，\n'
    '   于是按钮点得到、提示也还看得见。 */\n'
    '.scanmask.hide{display:none !important}   /* 关键：否则这片遮罩会一直盖在页面上（隐藏类被 display:block 压掉） */\n'
    '.scanbox{position:absolute;inset:0;overflow:hidden}\n'
    '.scanbox video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background:#000;display:block}\n'
    '.scanwin{position:absolute;left:50%;top:46%;transform:translate(-50%,-50%);'
    'width:min(72vmin,420px);height:min(72vmin,420px);border-radius:16px;'
    'box-shadow:0 0 0 100vmax rgba(0,0,0,.55);pointer-events:none}\n'
    '.scanwin i{position:absolute;width:26px;height:26px;border:3px solid #6ee7b7;border-radius:4px}\n'
    '.scanwin i:nth-child(1){left:-2px;top:-2px;border-right:0;border-bottom:0}\n'
    '.scanwin i:nth-child(2){right:-2px;top:-2px;border-left:0;border-bottom:0}\n'
    '.scanwin i:nth-child(3){left:-2px;bottom:-2px;border-right:0;border-top:0}\n'
    '.scanwin i:nth-child(4){right:-2px;bottom:-2px;border-left:0;border-top:0}\n'
    '.scantop{position:absolute;left:0;right:0;top:0;padding:14px 16px;'
    'background:linear-gradient(rgba(0,0,0,.72),rgba(0,0,0,0));color:#fff;font-size:14.5px;'
    'font-weight:700;text-align:center;pointer-events:none}\n'
    '.scanbot{position:absolute;left:0;right:0;bottom:0;padding:12px 16px 16px;'
    'background:linear-gradient(rgba(0,0,0,0),rgba(0,0,0,.82))}\n'
    '.scanbot .camout{margin:0 0 8px;max-height:20vh;overflow:auto}\n'
    '.scanbtns{display:flex;gap:10px;align-items:stretch}\n'
    '.scanbtns button{flex:1;background:rgba(42,42,42,.92);color:#e8e8e8;border:1px solid #3a3a3a;'
    'border-radius:10px;padding:11px 10px;font-size:14px;font-family:inherit;cursor:pointer}\n'
    '.scanbtns button.scanmain{background:#2f6fd0;border-color:#3b7de0;color:#fff;font-weight:700}',
    'CSS：扫码浮层改成全屏取景样式',
    '.scanwin{position:absolute'
)

rep(
    '/* 扫码诊断行：卡在哪一步（画面没来 / 原生识别挂了 / jsQR 跑了但认不出）一眼能看出来 */\n'
    '.scanstat{margin-top:8px;font-size:11.5px;line-height:1.5;color:#7f8a99}',
    '/* 扫码诊断行：卡在哪一步（画面没来 / 原生识别挂了 / jsQR 跑了但认不出）一眼能看出来 */\n'
    '.scanstat{margin:0 0 8px;font-size:12px;line-height:1.5;color:#cfe0ff}',
    'CSS：诊断行放大一点、亮一点（全屏浮层里要看得清）',
    '.scanstat{margin:0 0 8px;font-size:12px'
)

# ================================================================ B. 浮层标记
rep(
    '<div class="scanmask hide" id="scanMask">\n'
    '  <div class="scanbox">\n'
    '    <div class="scanhd">对准相机屏幕上的二维码</div>\n'
    '    <video id="scanVideo" playsinline autoplay muted></video>\n'
    '    <canvas id="scanCanvas" style="display:none"></canvas>\n'
    '    <div class="camout" id="scanOut">把整个二维码放进画面，不用按快门，自动识别。</div>\n'
    '    <div class="scanstat" id="scanStat">准备中…</div>\n'
    '    <button type="button" id="scanStop">关闭</button>\n'
    '  </div>\n'
    '</div>',
    '<div class="scanmask hide" id="scanMask">\n'
    '  <div class="scanbox">\n'
    '    <video id="scanVideo" playsinline autoplay muted></video>\n'
    '    <canvas id="scanCanvas" style="display:none"></canvas>\n'
    '    <div class="scanwin" aria-hidden="true"><i></i><i></i><i></i><i></i></div>\n'
    '    <div class="scantop" id="scanTop">对准相机屏幕上的二维码</div>\n'
    '    <div class="scanbot">\n'
    '      <div class="camout" id="scanOut">把二维码放进中间的方框（占方框 1/3 以上最好）。不用按快门，认出来会自动关。</div>\n'
    '      <div class="scanstat" id="scanStat">准备中…</div>\n'
    '      <div class="scanbtns">\n'
    '        <button type="button" id="scanManual">手动填</button>\n'
    '        <button type="button" id="scanDiag">复制诊断</button>\n'
    '        <button type="button" id="scanStop">✕ 关闭</button>\n'
    '      </div>\n'
    '    </div>\n'
    '  </div>\n'
    '</div>',
    '标记：扫码浮层全屏结构（旧 id 全保留 + 新增 scanTop/scanManual/scanDiag）',
    'id="scanManual"'
)

# ================================================================ C+D. 块07
rep(
    '  var scanWatch = null, scanStartedAt = 0;\n',
    '  var scanWatch = null, scanStartedAt = 0, scanStatGet = null;   /* r48：诊断行取值函数（给「复制诊断」用） */\n'
    '  /* r48：诊断行——卡在哪一步就写在这儿（浮层里那行小字 + 复制诊断都读它） */\n'
    '  function scanStatSet(t){ var e = $(\'scanStat\'); if(e) e.textContent = t; }\n'
    '  window.__om3scanStat = function(){ return scanStatGet ? scanStatGet() : \'(还没开始扫)\'; };\n',
    '块07：诊断行取值函数 + scanStatSet',
    'window.__om3scanStat = function()'
)

rep(
    "  $('scanStop').addEventListener('click', stopScan);\n",
    "  $('scanStop').addEventListener('click', stopScan);\n"
    "  /* r48：底部「手动填」——把人直接带到那两格（扫不出时不用再自己找） */\n"
    "  $('scanManual').addEventListener('click', function(){\n"
    "    stopScan();\n"
    "    showManual('手动填：照相机屏幕上写的 SSID / 密码填到下面两格，一样能连。');\n"
    "  });\n"
    "  /* r48：「复制诊断」——扫不出时一键把关键状态复制出来（发我就知道卡在哪一步） */\n"
    "  $('scanDiag').addEventListener('click', function(){\n"
    "    var t = scanDiagText();\n"
    "    try{ log('[扫码] 诊断：' + t.replace(/\\n/g, ' | ')); }catch(e){}\n"
    "    var b = $('scanDiag');\n"
    "    bleTryCopy(t, function(okv, why){\n"
    "      if(b){ b.textContent = okv ? '已复制 ✓' : '复制失败'; setTimeout(function(){ b.textContent = '复制诊断'; }, 1600); }\n"
    "      if(!okv) toastMsg('复制没成功（' + why + '）——可以长按日志手动复制');\n"
    "    });\n"
    "  });\n"
    "  /* r48：诊断文本（型号/画面尺寸/帧数/识别次数/解码耗时/轨道设置/最近日志） */\n"
    "  function scanDiagText(){\n"
    "    var L = ['【扫码诊断】'];\n"
    "    L.push('时间：' + new Date().toLocaleString());\n"
    "    L.push('页面：' + (location.href || ''));\n"
    "    L.push('UA：' + navigator.userAgent);\n"
    "    try{ L.push('视口：' + window.innerWidth + 'x' + window.innerHeight); }catch(e){}\n"
    "    L.push('统计：' + (window.__om3scanStat ? window.__om3scanStat() : '(还没开始扫)'));\n"
    "    try{\n"
    "      var v = $('scanVideo');\n"
    "      L.push('video：readyState=' + v.readyState + ' · 画面 ' + v.videoWidth + 'x' + v.videoHeight + ' · paused=' + v.paused);\n"
    "    }catch(e){}\n"
    "    try{\n"
    "      if(scanStream && scanStream.getVideoTracks){\n"
    "        var tk = scanStream.getVideoTracks()[0];\n"
    "        L.push('轨道：' + (tk && tk.getSettings ? JSON.stringify(tk.getSettings()) : '无'));\n"
    "      } else L.push('轨道：无（摄像头没起来）');\n"
    "    }catch(e){}\n"
    "    L.push('原生识别：' + (window.BarcodeDetector ? '有' : '没有') + ' · jsQR：' + (window.jsQR ? '已加载' : '没加载'));\n"
    "    try{ L.push('浮层：' + ($('scanMask').classList.contains('hide') ? '已关' : '开着')); }catch(e){}\n"
    "    try{ L.push('最近日志：'); L.push(ALLLOG.slice(-12).join('\\n')); }catch(e){}\n"
    "    return L.join('\\n');\n"
    "  }\n"
    "  window.__om3scanDiag = scanDiagText;\n",
    '块07：「手动填」+「复制诊断」两个按钮 + 诊断文本',
    'window.__om3scanDiag = scanDiagText'
)

rep(
    "      if(pr.indexOf('need_perm') === 0){\n"
    "        pendingScan = true;\n",
    "      if(pr.indexOf('need_perm') === 0){\n"
    "        pendingScan = true;\n"
    "        scanStatSet('等相机权限…（在系统弹窗里点「允许」就会自动开始）');\n",
    '块07：等权限时诊断行写清楚（原来是静默的）',
    "scanStatSet('等相机权限"
)

rep(
    "    if(o0){ o0.innerHTML = ''; line(o0, '摄像头启动中…'); }\n",
    "    scanStatSet('正在打开摄像头…');\n"
    "    if(o0){ o0.innerHTML = ''; line(o0, '摄像头启动中…（认出来会自动关；一直认不出就点下面「手动填」）'); }\n",
    '块07：起摄像头时诊断行写清楚 + 首屏提示更可操作',
    "scanStatSet('正在打开摄像头…')"
)

rep(
    "    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},\n"
    "        width:{ideal:640}, height:{ideal:480}}, audio:false})\n",
    "    /* r48（①-a）：原来只要 640x480 —— 拍相机屏幕上那种二维码像素本来就紧：\n"
    "       只写 ideal，机型给不了 720p 就还是原来的分辨率，不会失败。 */\n"
    "    navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},\n"
    "        width:{ideal:1280}, height:{ideal:720}}, audio:false})\n",
    '块07：取景分辨率 640x480 → 1280x720（ideal）',
    'width:{ideal:1280}'
)

rep(
    "        var stat = { frames: 0, tries: 0, lastMs: 0, bdFail: 0 };\n",
    "        var stat = { frames: 0, tries: 0, lastMs: 0, bdFail: 0,\n"
    "                     vw: 0, vh: 0, round: 0, p1: 0, p2: 0, p3: 0, p4: 0,\n"
    "                     warnNoFrame: 0, warnSlow: 0 };   /* r48：画面尺寸/轮数/各遍计数/两个提示只出一次 */\n"
    "        scanStatGet = statFull;                       /* r48：给「复制诊断」用 */\n",
    '块07：stat 加画面尺寸/各遍计数 + 导出取值函数',
    'scanStatGet = statFull;'
)

rep(
    "        function status(){\n"
    "          var t = '帧 ' + stat.frames + ' · 识别尝试 ' + stat.tries\n"
    "                + ' · 原生识别' + (scanBD ? (BD ? '（开）' : '（挂了，已退回 jsQR）') : '（无）')\n"
    "                + ' · 上次解码 ' + stat.lastMs + 'ms';\n"
    "          var e = document.getElementById('scanStat');\n"
    "          if(e) e.textContent = t;\n"
    "        }\n",
    "        /* r48：这行就是「扫不出」时的定位依据 —— 画面尺寸/放大几遍/原图那遍跑没跑，全写出来 */\n"
    "        function statText(){\n"
    "          return '帧 ' + stat.frames + ' · 识别尝试 ' + stat.tries\n"
    "               + ' · 画面 ' + (stat.vw ? (stat.vw + 'x' + stat.vh) : '还没来')\n"
    "               + ' · 原生识别' + (scanBD ? (BD ? '（开）' : '（挂了，已退回 jsQR）') : '（无）')\n"
    "               + ' · 上次解码 ' + stat.lastMs + 'ms';\n"
    "        }\n"
    "        function statFull(){\n"
    "          return statText() + ' · 轮 ' + stat.round + '（整帧 ' + stat.p1 + ' / 放大×2 ' + stat.p2\n"
    "               + ' / 放大×3 ' + stat.p3 + ' / 原图 ' + stat.p4 + '）';\n"
    "        }\n"
    "        function status(){ scanStatSet(statText()); }\n",
    '块07：诊断行加画面尺寸 + 各遍计数（statText/statFull）',
    'function statFull(){'
)

rep(
    "        var fixed = false;\n"
    "        function tryDecode(sx, sy, sw, sh, targetW){\n"
    "          var sc = Math.min(1, targetW / Math.max(sw, sh));\n"
    "          var w = Math.max(1, Math.round(sw * sc)), hh = Math.max(1, Math.round(sh * sc));\n"
    "          if(!fixed || c.width !== w || c.height !== hh){ c.width = w; c.height = hh; fixed = true; }\n"
    "          ctx.drawImage(v, sx, sy, sw, sh, 0, 0, w, hh);\n"
    "          try{\n"
    "            var t0 = Date.now();\n"
    "            var img = ctx.getImageData(0, 0, w, hh);\n"
    "            /* 允许反色：屏幕上拍的二维码经常是\"白码黑底\"，不试反色就会一直扫不出 */\n"
    "            var f = window.jsQR(img.data, img.width, img.height, {inversionAttempts:'attemptBoth'});\n"
    "            stat.tries++; stat.lastMs = Date.now() - t0;\n"
    "            return hit(f && f.data);\n"
    "          }catch(e){ stat.tries++; return false; }\n"
    "        }\n"
    "        var pass2 = 0;\n"
    "        function canvasTry(){\n"
    "          if(!(v.readyState === v.HAVE_ENOUGH_DATA && v.videoWidth)) return false;\n"
    "          var VW = v.videoWidth, VH = v.videoHeight;\n"
    "          /* 第一遍：整帧 */\n"
    "          if(tryDecode(0, 0, VW, VH, MAXW)) return true;\n"
    "          /* 第二遍（每隔一次）：中心 60% 裁剪后放大，专治\"二维码在画面里偏小/偏远\" */\n"
    "          pass2 = (pass2 + 1) % 2;\n"
    "          if(pass2 === 0){\n"
    "            var cw = Math.round(VW * 0.6), chh = Math.round(VH * 0.6);\n"
    "            if(tryDecode(Math.round((VW - cw) / 2), Math.round((VH - chh) / 2), cw, chh, Math.round(MAXW * 1.4))) return true;\n"
    "          }\n"
    "          return false;\n"
    "        }\n",
    "        var fixed = false;\n"
    "        /* r48（①-b，关键）：原来 sc = Math.min(1, …) —— 注释写着「裁剪后放大」，其实**永远不会 >1**：\n"
    "           640x480 取景里一个只占 1/3 画面的二维码（≈200px、每模块 2~3 像素）从头到尾还是 200px，jsQR 认不出\n"
    "           （用户实测：帧在涨、识别尝试也在涨，就是不认出来）。现在裁剪那几遍允许插值放大到 upMax 倍。 */\n"
    "        function tryDecode(sx, sy, sw, sh, targetW, upMax){\n"
    "          var sc = Math.min(upMax || 1, targetW / Math.max(sw, sh));\n"
    "          var w = Math.max(1, Math.round(sw * sc)), hh = Math.max(1, Math.round(sh * sc));\n"
    "          if(!fixed){ c.width = w; c.height = hh; fixed = true; }        /* 画布只增不减：不每轮重分配 */\n"
    "          else if(c.width < w || c.height < hh){ c.width = w; c.height = hh; }\n"
    "          ctx.drawImage(v, sx, sy, sw, sh, 0, 0, w, hh);\n"
    "          try{\n"
    "            var t0 = Date.now();\n"
    "            var img = ctx.getImageData(0, 0, w, hh);\n"
    "            /* 允许反色：屏幕上拍的二维码经常是\"白码黑底\"，不试反色就会一直扫不出 */\n"
    "            var f = window.jsQR(img.data, img.width, img.height, {inversionAttempts:'attemptBoth'});\n"
    "            stat.tries++; stat.lastMs = Date.now() - t0;\n"
    "            return hit(f && f.data);\n"
    "          }catch(e){ stat.tries++; return false; }\n"
    "        }\n"
    "        var MAXNATIVE = 1280;    /* r48：原图那遍的长边上限（再大 jsQR 太吃 CPU） */\n"
    "        function canvasTry(){\n"
    "          if(!(v.readyState === v.HAVE_ENOUGH_DATA && v.videoWidth)) return false;\n"
    "          var VW = v.videoWidth, VH = v.videoHeight;\n"
    "          stat.vw = VW; stat.vh = VH; stat.round++;\n"
    "          /* ① 整帧（大就缩到 MAXW 省 CPU）：二维码本来就占满画面时这一遍就中 */\n"
    "          stat.p1++; if(tryDecode(0, 0, VW, VH, MAXW, 1)) return true;\n"
    "          /* ② 中心 60% 裁剪 + **最多放大 2 倍**：二维码占画面 1/3 左右时靠这遍（r48：以前这遍不放大） */\n"
    "          var cw = Math.round(VW * 0.6), chh = Math.round(VH * 0.6);\n"
    "          stat.p2++;\n"
    "          if(tryDecode(Math.round((VW - cw) / 2), Math.round((VH - chh) / 2), cw, chh, Math.round(MAXW * 1.4), 2)) return true;\n"
    "          /* ③ 隔一轮：中心 40% 裁剪 + **最多放大 3 倍**（手机拿得远、二维码更小） */\n"
    "          if(stat.round % 2 === 0){\n"
    "            var c2 = Math.round(VW * 0.4), h2 = Math.round(VH * 0.4);\n"
    "            stat.p3++;\n"
    "            if(tryDecode(Math.round((VW - c2) / 2), Math.round((VH - h2) / 2), c2, h2, Math.round(MAXW * 1.4), 3)) return true;\n"
    "          }\n"
    "          /* ④ 隔两轮：**原分辨率**整帧（取景比 MAXW 大时才跑）——分辨率是识别率的地基 */\n"
    "          if(stat.round % 3 === 0 && Math.max(VW, VH) > MAXW){\n"
    "            stat.p4++;\n"
    "            if(tryDecode(0, 0, VW, VH, Math.min(VW, MAXNATIVE), 1)) return true;\n"
    "          }\n"
    "          return false;\n"
    "        }\n",
    '块07：裁剪那几遍真的放大（×2/×3）+ 每 3 轮原分辨率那遍（①-b 根治）',
    'var MAXNATIVE = 1280;'
)

rep(
    "          if((now - lastStat) > 800){ lastStat = now; status(); }\n"
    "          scanRAF = setTimeout(tick, 120);\n"
    "        }\n"
    "        var lastJs = 0, lastStat = 0;\n"
    "        status();\n"
    "        scanRAF = setTimeout(tick, 60);\n",
    "          /* r48（①-c）：两个原本静默的情况，现在都要说出来（都**不停循环**，想停就点 ✕） */\n"
    "          if(!stat.warnNoFrame && !stat.vw && (now - scanStartedAt) > 4500){\n"
    "            stat.warnNoFrame = 1;\n"
    "            scanSay('摄像头开了但一直没画面（帧 ' + stat.frames + '）—— 关掉别的占用摄像头的 app，或点下面「手动填」。', 'warn');\n"
    "          }\n"
    "          if(!stat.warnSlow && (now - scanStartedAt) > 15000){\n"
    "            stat.warnSlow = 1;\n"
    "            scanSay('还没认出来。试试：相机屏幕调最亮 · 让二维码占满中间方框 1/3 以上 · 别正对反光；也可以点下面「手动填」。', 'warn');\n"
    "          }\n"
    "          if((now - lastStat) > 800){\n"
    "            lastStat = now; status();\n"
    "            /* 这行也进日志：用户点「☰ → 复制日志」时能把它带出来（r48） */\n"
    "            if((now - (lastLog || 0)) > 2000){ lastLog = now; try{ log('[扫码] ' + statFull()); }catch(e){} }\n"
    "          }\n"
    "          scanRAF = setTimeout(tick, 120);\n"
    "        }\n"
    "        var lastJs = 0, lastStat = 0, lastLog = 0;\n"
    "        status();\n"
    "        scanRAF = setTimeout(tick, 60);\n",
    '块07：诊断行进日志（每 2 秒）+ 没画面/认不出两个提示（①-c）',
    'stat.warnNoFrame = 1;'
)

rep(
    "      }, function(err){\n"
    "        $('scanOut').innerHTML = '';\n",
    "      }, function(err){\n"
    "        scanStatSet('打不开摄像头：' + err.message);      /* r48：诊断行也留一份 */\n"
    "        $('scanOut').innerHTML = '';\n",
    '块07：打不开摄像头时诊断行写清楚',
    "scanStatSet('打不开摄像头：'"
)

# ================================================================ 写出
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('\n'.join(LOG))
print('写出 app/base.html：%.2f MB' % (len(s.encode('utf-8')) / 1048576.0))

print('\n=== 自检 ===')
S = io.open(P, encoding='utf-8').read()
print('还剩 Math.min(1, targetW …（应为 0）：', S.count('Math.min(1, targetW'))
print('width:{ideal:1280}：', S.count('width:{ideal:1280}'))
print('scanwin：', S.count('scanwin'), '｜ scanDiag：', S.count('scanDiag'),
      '｜ scanManual：', S.count('scanManual'), '｜ __om3scanStat：', S.count('__om3scanStat'))
print('旧 id 都在：', all(('id="%s"' % i) in S for i in
                          ['scanMask', 'scanVideo', 'scanCanvas', 'scanOut', 'scanStat', 'scanStop']))
ids = set(re.findall(r'\bid="([^"]+)"', S))
print('死锚点：', sorted(l for l in set(re.findall(r'href="#([^"]+)"', S)) if l not in ids and "'" not in l) or '无')
