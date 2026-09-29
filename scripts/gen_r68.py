# -*- coding: utf-8 -*-
"""第 68 轮：新增**独立「测试页（连接诊断）」** + 正常「连接相机」页降噪。

需求方 2026-09-28：「日志在哪里给你复制，还有操作的按钮是否明显，我建议你单独设计一个测试页面功能，
和正常的连接页面不放一起，方便测试。而正常连接的就不显示太多日志，免得误导客户。」

做法（详见 SPEC-round68.md §2）：
  · 新页 `#paneT`：状态面板 + 9 个大按钮（每个下面一行"预期看到什么"）+ 与客户页**共用**的完整日志
    + 「复制全部日志 / 下载日志文件 / 清空日志」+「← 回连接相机」。
    入口只挂 ☰ 菜单（**不进顶栏/底栏页签**，客户不会顺手点进去）；点击走**既有**页签切换逻辑
    （点隐藏代理页签 `#tabTest`，沿用第 39 轮 tabB/tabC 的做法）。
  · 客户页降噪：`#camOut3` 折进 `<details id="camLogFold">`（默认收起）；日志三按钮搬到测试页；
    直连的扫描明细只进日志；向导卡加一行"要排查去 ☰ → 测试页"。
  · 按钮**不复制实现**：一键走 `window.__om3camWifiChain`、直连走 `window.__om3direct`、
    检测/用记住的凭据/日志三按钮直接 `.click()` 既有的既有按钮、蓝牙链走 `window.__om3camBleAuto`。

规矩：幂等（标记 `r68：测试页`）+ 每处锚点断言命中恰好 1 次 + 原有 id 一个不少（新增 id 见规格 §2.3）。

用法：python scripts/gen_r68.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r68：测试页'
EDITS = []


def E(label, old, new):
    EDITS.append((label, old, new))


# ------------------------------------------------------------------ 1. 测试页 HTML
PANE_T = '''
<!-- ============ 测试页（连接诊断）—— r68 ============
     为什么要单独一页（需求方 2026-09-28）：客户页只该回答"下一步点哪个"；日志/明细/手动按钮是排查用的，
     堆在客户页会误导客户。所以：诊断的东西全在这一页，入口只放 ☰ 菜单（不进任何页签）。
     做法：按钮一律去调正常流程里**已有的**函数/按钮，不复制实现。 -->
<div id="paneT" class="pane hide">
  <h1>🔧 测试页 <span style="font-size:13px;color:#8d8d8d;font-weight:400">（连接诊断 · 客户看不到这里）</span></h1>

  <div class="camcard" style="border-color:#33507e">
    <div class="camhd">怎么用（三步）</div>
    <div class="camout" style="border-color:#33507e">
      <b>① 跑</b>：点下面按钮区里的按钮（每个按钮下面写了「预期看到什么」）。<br>
      <b>② 看</b>：看「状态面板」和下面的日志 —— 卡住时记一下<b>停在哪一句</b>。<br>
      <b>③ 发我</b>：点「复制全部日志」→ 连同那句「停在哪」一起粘给我。
    </div>
    <div class="camout" style="font-size:12.5px;color:#9aa3b2">
      7 个场景（A 第一次连 / B 第二次 / C 睡着后唤醒 / D 密码变了 / E 断开·忘掉 / F 看着挂上但没通 / G 扫码）
      的清单在 <code>SPEC-round67.md §3</code>；这一页只负责"能点、能看、能导出"。
    </div>
  </div>

  <div class="camcard">
    <div class="camhd">按钮区（都复用正常流程里的动作，不是另写一套）</div>
    <button type="button" class="bigbtn" id="tvChain">① 一键：按正常流程连（等蓝牙 → 直连 → 记住的凭据）</button>
    <div class="tvhint">预期：出现「第 1/3 步」→ 蓝牙链 →「相机热点已经起来了 → 进 Wi-Fi」→「第 2/3 步」→ 系统弹窗 →「已连上相机热点」→「相机应答（HTTP 200）」</div>
    <button type="button" class="bigbtn alt" id="tvDirect">② 只连相机热点（直连，相机 Wi-Fi 已开时最快）</button>
    <div class="tvhint">预期：日志里出现「[直连] 明细：…」并列出扫到的热点；之后「已发起连接」或明确说明走不通的原因</div>
    <button type="button" class="bigbtn alt" id="tvCheck">③ 检测相机（HTTP 通不通）</button>
    <div class="tvhint">预期：日志里「相机应答（HTTP 200）」；右下状态面板变成「HTTP 确认通了」</div>
    <button type="button" class="bigbtn alt" id="tvSaved">④ 用记住的凭据连（requestNetwork 那条路）</button>
    <div class="tvhint">预期：「正在请系统连接 …（如果弹窗，请点「连接」）」；连上后状态行变绿</div>
    <button type="button" class="bigbtn alt" id="tvScan">⑤ 扫附近 Wi-Fi（列出明细：SSID / 信号 / BSSID / 📷）</button>
    <div class="tvhint">预期：列出手机能看到的所有热点；相机那一行带 📷（名字像 OM-3 / OM-D / E-M…）</div>
    <button type="button" class="bigbtn alt" id="tvBle">⑥ 蓝牙：扫描 → 连接 → 唤醒相机</button>
    <div class="tvhint">预期：日志「[自动·蓝牙] 第 1/4…第 4/4 步」；成功时「✅ 相机热点起来了」</div>
    <button type="button" class="bigbtn alt" id="tvBleStop">停止蓝牙链</button>
    <div class="tvhint">预期：日志「已停止自动连蓝牙」；之后手动点 ⑥ 可以重来</div>
    <div class="camout" id="tvOut">（按钮的结果写在这里，同时也进下面那份日志）</div>
  </div>

  <div class="camcard">
    <div class="camhd">状态面板（在这一页时每 1.5 秒自动刷一次）</div>
    <div class="camout" id="tvState">正在读状态…</div>
    <button type="button" id="tvRefresh">立即刷新</button>
  </div>

  <div class="camcard">
    <div class="camhd">日志（三步共用这一份；直接复制这一份给我就行）</div>
    <pre class="camout" id="tvLog" style="white-space:pre-wrap;font-size:11.5px;line-height:1.5">（还没有日志）</pre>
    <div class="camlogbtns">
      <button type="button" id="camCopyLog">复制全部日志</button>
      <button type="button" id="camDlLog">下载日志文件</button>
      <button type="button" id="camClearLog" class="camghost">清空日志</button>
      <span class="camloghint">跑完点「复制全部日志」，粘给我就行</span>
    </div>
  </div>

  <button type="button" class="bigbtn alt" id="tvBack">← 回「连接相机」</button>
</div>
'''

# ------------------------------------------------------------------ 2. 测试页 JS（放进相机那个 <script> 块，能直接用 ALLLOG / Native / log）
TV_JS = '''
  /* ================= r68：测试页（连接诊断） =================
     为什么单独一页：客户页只该给"下一步点哪个"，日志/明细/手动按钮堆在那里会误导客户（需求方 2026-09-28）。
     实现要点：① 按钮全部**复用**既有动作（不复制实现）② 日志用同一份 ALLLOG（只多一个只读镜像视图）
     ③ 只有"测试页可见"时才刷（不增加客户页开销）。 */
  (function(){
    function tvPane(){ return document.getElementById('paneT'); }
    function tvOn(){ var p = tvPane(); return !!(p && !p.classList.contains('hide')); }
    function tvOut(t, cls){ try{ line($('tvOut'), t, cls || ''); }catch(e){ om3err(e, "silent"); } }
    function tvBind(id, fn){ var b = document.getElementById(id); if(b) b.addEventListener('click', fn); }
    function tvNoBridge(){ tvOut('这个版本没有原生桥（桌面单文件 HTML / 老 APK）—— 连接类动作在这里做不了，但日志和状态照样能看。', 'warn'); }
    function tvNative(){ return (window.OM3Native || Native || null); }

    tvBind('tvChain', function(){
      if(!window.__om3camWifiChain){ tvOut('找不到连接链函数', 'err'); return; }
      tvOut('按正常流程连（和客户点「连接相机」完全同一条链）…');
      try{ window.__om3camWifiChain(); }catch(e){ tvOut('出错：' + e.message, 'err'); }
    });
    tvBind('tvDirect', function(){
      var N = tvNative(); if(!N || !N.wifiScanList){ tvNoBridge(); return; }
      if(!window.__om3direct){ tvOut('找不到直连函数', 'err'); return; }
      tvOut('直连：扫附近热点 → 挑相机那个 → 连…');
      try{ window.__om3direct(function(reason){ tvOut('直连没成：' + reason, 'warn'); }); }
      catch(e){ tvOut('出错：' + e.message, 'err'); }
    });
    tvBind('tvCheck', function(){ tvOut('点了「检测相机」——结果看下面日志和状态面板'); var b = $('camCheck'); if(b) b.click(); else tvOut('找不到检测按钮', 'err'); });
    tvBind('tvSaved', function(){ tvOut('用记住的凭据连（客户页那条退路）…'); var b = $('camConnect'); if(b) b.click(); else tvOut('找不到连接按钮', 'err'); });
    tvBind('tvBle', function(){
      var N = tvNative(); if(!N || !N.bleScanStart){ tvOut('这个版本没有蓝牙接口', 'err'); return; }
      if(!window.__om3camBleAuto){ tvOut('找不到蓝牙链函数', 'err'); return; }
      tvOut('蓝牙链：权限 → 蓝牙开关 → 只扫相机 → 连接 → 发唤醒帧…（进度看日志）');
      try{ window.__om3camBleAuto('测试页'); }catch(e){ tvOut('出错：' + e.message, 'err'); }
    });
    tvBind('tvBleStop', function(){ var b = $('camLinkStop'); if(b){ b.click(); tvOut('已请求停止蓝牙链', 'warn'); } else tvOut('找不到「停止」按钮', 'warn'); });
    tvBind('tvBack', function(){ var t = $('tabCam'); if(t) t.click(); });

    /* ⑤ 扫附近 Wi-Fi：把明细列出来（客户页只留一句"扫到 N 个"，明细在这一页/日志里） */
    tvBind('tvScan', function(){
      var N = tvNative();
      if(!N || !N.wifiScanList){ tvNoBridge(); return; }
      var o = $('tvOut'); if(o) o.innerHTML = '';
      var raw = '';
      try{ raw = String(N.wifiScanList() || ''); }catch(e){ raw = 'err:' + e.message; }
      if(raw.charAt(0) !== '['){ tvOut('扫描失败：' + raw + '（多半是缺「附近的设备 / 位置信息」权限）', 'err'); return; }
      var L = []; try{ L = JSON.parse(raw) || []; }catch(e){ L = []; }
      tvOut('扫到 ' + L.length + ' 个热点（📷 = 名字像相机）：', 'ok');
      var cam = 0;
      for(var i = 0; i < L.length; i++){
        var x = L[i] || {};
        if(x.cam) cam++;
        tvOut((x.cam ? '📷 ' : '　 ') + (x.ssid || '（无名）') + '　' + (x.level || '?') + 'dBm　'
              + (x.bssid || '（系统没给 BSSID）'), x.cam ? 'ok' : '');
      }
      tvOut('其中像相机的 ' + cam + ' 个。', cam ? 'ok' : 'warn');
    });

    /* 状态面板：只读本机已有信息（不含密码） */
    function tvState(){
      var o = $('tvState'); if(!o) return;
      var N = tvNative();
      var L = [], st = {}, cs = {}, ps = {}, sv = camSaved() || {};
      try{ st = (typeof wifiCached === 'function' ? wifiCached(true) : {}) || {}; }catch(e){ st = {}; }
      try{ cs = JSON.parse((N && N.cameraState ? N.cameraState() : '{}') || '{}'); }catch(e){ cs = {}; }
      try{ ps = JSON.parse((N && N.permState ? N.permState() : '{}') || '{}'); }catch(e){ ps = {}; }
      var cur = String(st.ssid || ''); if(/^<?unknown/i.test(cur)) cur = '';
      var camOn = document.body.classList.contains('cam-on');
      L.push('<b>原生桥</b>：' + (N ? '在' : '<span class="warn">没有（桌面单文件 HTML / 老 APK）</span>'));
      L.push('<b>Wi-Fi</b>：' + (st.wifi ? '开着' : '关着') + '　当前连接：<b>'
             + esc(cur || '（系统没给 —— 多半缺「位置信息 / 附近的设备」权限）') + '</b>');
      L.push('<b>相机</b>：' + (_camHTTP ? '<span class="ok">HTTP 确认通了</span>'
             : (camOn ? '<span class="warn">按 SSID 看着挂上了，HTTP 还没确认</span>' : '未连接'))
             + '　（当前在客户页第 ' + (window.__om3camStep || 1) + '/4 步）');
      L.push('<b>记住的相机</b>：<b>' + esc(sv.ssid || '（没记住）') + '</b>'
             + (sv.bssid ? '　BSSID ' + esc(sv.bssid) : '　（还没有 BSSID）')
             + (sv.model ? '　机型 ' + esc(sv.model) : '') + (sv.serial ? '　序列号 ' + esc(sv.serial) : ''));
      L.push('<b>原生连接对象</b>：' + (cs.ssid ? ('ssid=' + esc(cs.ssid)) : '（空）')
             + (cs.bssid ? ('　bssid=' + esc(cs.bssid)) : '') + '　connected=' + (cs.connected ? 'true' : 'false'));
      L.push('<b>蓝牙</b>：' + (BLEON ? ('<span class="ok">已连接</span>　' + esc(BLENAME || '（无名）') + '　' + esc(BLEMAC)) : '未连接')
             + (BLEMTU ? ('　MTU ' + esc(BLEMTU)) : ''));
      L.push('<b>权限</b>：相机=' + (ps.camera ? '有' : '<span class="warn">缺</span>')
             + '　位置=' + (ps.fine ? '有' : '<span class="warn">缺</span>')
             + '　附近的设备=' + (ps.nearby ? '有' : '<span class="warn">缺</span>')
             + '　安卓 SDK=' + esc(ps.sdk || '?'));
      var bd = ''; try{ bd = String(N && N.blePermDetail ? N.blePermDetail() : ''); }catch(e){ bd = ''; }
      if(bd) L.push('<b>蓝牙权限</b>：' + esc(bd));
      var av = document.querySelector('.appver');
      if(av) L.push('<b>版本</b>：' + esc(String(av.textContent || '').trim().slice(0, 40)));
      o.innerHTML = L.join('<br>');
    }
    /* 日志镜像：和客户页共用同一份 ALLLOG，只多一个只读视图；内容没变就不动 DOM（免得闪烁/滚动回顶） */
    function tvRender(){
      if(!tvOn()) return;
      var pre = $('tvLog'); if(!pre) return;
      var t = ALLLOG.length ? ALLLOG.join('\\n') : '（还没有日志）';
      if(pre.textContent !== t){ pre.textContent = t; pre.scrollTop = pre.scrollHeight; }
    }
    function tvRefreshNow(){ tvState(); tvRender(); }
    tvBind('tvRefresh', function(){ tvRefreshNow(); tvOut('已刷新状态面板与日志。'); });
    window.__om3tvState = tvState;
    window.__om3tvRender = tvRender;
    /* 只有"测试页可见"时才刷（客户页零开销） */
    try{ setInterval(function(){ if(tvOn()) tvRefreshNow(); }, 1500); }catch(e){ om3err(e, "silent"); }
    try{ tvRefreshNow(); }catch(e){ om3err(e, "silent"); }
  })();
'''

# ------------------------------------------------------------------ 3. CSS（测试页的大按钮）
CSS = '''
/* r68：测试页（诊断）的大按钮 —— 排查时要"一眼看到、一按就对"，不做小按钮 */
#paneT .bigbtn{display:block;width:100%;box-sizing:border-box;margin:10px 0 2px;padding:12px 14px;border:0;border-radius:9px;
  background:#2f8f74;color:#fff;font-size:14.5px;font-weight:700;font-family:inherit;text-align:left;cursor:pointer}
#paneT .bigbtn.alt{background:#2b3444;color:#cfe0ff}
#paneT .tvhint{color:#9aa3b2;font-size:12px;line-height:1.6;margin:0 0 10px 2px}
#paneT #tvLog{max-height:40vh;overflow:auto}
'''

# ================================================================== 应用替换
E('CSS：测试页大按钮样式',
  '</style></head><body>',
  CSS + '</style></head><body>')

E('顶栏：加隐藏代理页签 tabTest（沿用 tabB/tabC 的做法）',
  '      <button type="button" data-p="C" id="tabC" style="display:none">场景对比</button>\n',
  '      <button type="button" data-p="C" id="tabC" style="display:none">场景对比</button>\n'
  '      <!-- r68：测试页的隐藏代理页签（不进可见页签；只为复用既有切换逻辑） -->\n'
  '      <button type="button" data-p="T" id="tabTest" style="display:none">测试页</button>\n')

E('☰ 菜单：加「🔧 测试页（连接诊断）」',
  '      <div class="cammsep"></div>\n      <button type="button" data-act="copylog">复制日志</button>',
  '      <div class="cammsep"></div>\n'
  '      <button type="button" data-act="test">🔧 测试页（连接诊断 · 日志在这里复制）</button>\n'
  '      <div class="cammsep"></div>\n'
  '      <button type="button" data-act="copylog">复制日志</button>')

E('菜单点击：test 走既有切换逻辑',
  "      if(s){ showStep(+s); return; }\n      if(a === 'copylog') $('camCopyLog').click();",
  "      if(s){ showStep(+s); return; }\n"
  "      if(a === 'test'){                                   /* r68：进测试页（点隐藏代理页签，复用既有逻辑） */\n"
  "        var tt = $('tabTest');\n"
  "        if(tt) tt.click(); else log('这个版本没有测试页', 'warn');\n"
  "        try{ closeMenu(); }catch(e){ om3err(e, \"silent\"); }\n"
  "        return;\n"
  "      }\n"
  "      if(a === 'copylog') $('camCopyLog').click();")

E('页签名单① showPane 加 T',
  "    var PANES = ['A', 'B', 'C', 'D', 'E'];          /* 唯一真源：要加页签只改这一行 */",
  "    var PANES = ['A', 'B', 'C', 'D', 'E', 'T'];     /* 唯一真源：要加页签只改这一行（r68 加 T=测试页） */")

E('页签名单② 兜底 switchPane 加 T',
  "  var PS = ['A','B','C','D','E'];",
  "  var PS = ['A','B','C','D','E','T'];   /* r68：T = 测试页（诊断） */")

E('页签名单③ applyModule 的 map 加 T',
  "        var map = { A:'paneA', B:'paneB', C:'paneC', D:'paneD', E:'paneE' };",
  "        var map = { A:'paneA', B:'paneB', C:'paneC', D:'paneD', E:'paneE', T:'paneT' };")

E('返回键：测试页 → 回「连接相机」',
  "      // 3) 在「档位推荐 / 场景对比」里 → 回到「配方合集」\n"
  "      var on = document.querySelector('.tabs button.on');\n"
  "      if (on && on.getAttribute('data-p') !== 'A') {",
  "      // 2b) r68：在「测试页」里 → 先回「连接相机」（别直接退出 App）\n"
  "      var tpan = document.getElementById('paneT');\n"
  "      if (tpan && !tpan.classList.contains('hide')) {\n"
  "        var dtab = document.getElementById('tabCam');\n"
  "        if (dtab) { dtab.click(); return true; }\n"
  "      }\n"
  "      // 3) 在「档位推荐 / 场景对比」里 → 回到「配方合集」\n"
  "      var on = document.querySelector('.tabs button.on');\n"
  "      if (on && on.getAttribute('data-p') !== 'A') {")

E('插入测试页 HTML（paneD 之后）',
  '<!-- ============ 槽位选择弹层（配方卡 → 导入相机） ============ --></div>',
  '<!-- ============ 槽位选择弹层（配方卡 → 导入相机） ============ --></div>\n' + PANE_T)

E('客户页：日志折进 details（默认收起）+ 日志三按钮搬走',
  '''    <div class="camout" id="camOut3">选择配方和槽位，点「写入相机」。写入前会自动先备份一次。</div>
    <div class="camlogbtns">
      <button type="button" id="camCopyLog">复制全部日志</button>
      <button type="button" id="camDlLog">下载日志文件</button>
      <button type="button" id="camClearLog" class="camghost">清空日志</button>
      <span class="camloghint">三步的日志都在这里，跑完复制给我就行</span>
    </div>''',
  '''    <!-- r68：原始日志收进折叠（默认收起）—— 客户页只留"进度/结论"；日志与明细都在 ☰ → 🔧 测试页 -->
    <details class="fold fnote" id="camLogFold">
      <summary>运行日志（排查用 · 一般不用看）</summary>
      <div class="foldbody" style="padding:6px 0 0">
        <div class="camout" id="camOut3">选择配方和槽位，点「写入相机」。写入前会自动先备份一次。</div>
        <div style="color:#9aa3b2;font-size:12px;margin-top:6px">
          要整段日志：☰（右上）→ <b>🔧 测试页（连接诊断）</b> → 点「复制全部日志」。
        </div>
      </div>
    </details>''')

E('客户页：直连的扫描明细只进日志',
  """    say('扫到 ' + list.length + ' 个热点，其中像相机的有 ' + cands.length + ' 个'
        + (cands.length ? ('：' + cands.map(function(x){ return x.ssid + '(' + x.level + 'dBm)'; }).join('、') + '　' + cands[0].ssid) : ''));""",
  """    /* r68：客户页只说结论；明细（SSID/信号）进日志 —— 要看明细去 ☰ → 测试页 */
    say('扫到 ' + list.length + ' 个热点，像相机的有 ' + cands.length + ' 个');
    try{
      log('[直连] 明细：' + list.map(function(x){
        return x.ssid + '(' + x.level + 'dBm)' + (x.cam ? '📷' : '') + (x.bssid ? '@' + x.bssid : '');
      }).join('、'));
    }catch(e){ om3err(e, "silent"); }""")

E('客户页向导：加一行"要排查去哪儿"的出口',
  """    <div class="camout" id="camGateOut"></div>
  </div>""",
  """    <div class="camout" id="camGateOut"></div>
    <!-- r68：排查出口（客户页只给这一行；日志/明细都在测试页） -->
    <div style="color:#9aa3b2;font-size:12px;margin-top:2px">连不上、要排查？右上角 <b>☰</b> → <b>🔧 测试页（连接诊断）</b>
      → 点「复制全部日志」发我（日志与扫描明细都在那里，这一页只显示进度和结论）。</div>
  </div>""")

E('插入测试页 JS（相机那个 script 块里，紧跟在直连函数导出之后）',
  '  window.__om3direct = camDirectConnect;',
  '  window.__om3direct = camDirectConnect;\n' + TV_JS)


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r68] 已经是目标状态（页面里有 "%s"）—— 不重复改。' % MARK)
        return 0
    bad = []
    for label, old, new in EDITS:
        n = html.count(old)
        if n != 1:
            bad.append('%s：锚点命中 %d 次（要求 1 次）' % (label, n))
    if bad:
        print('[r68] ✗ 以下锚点不匹配，页面可能已被改过 —— **不写盘**：')
        for b in bad:
            print('   · ' + b)
        return 1
    if '--check' in sys.argv:
        print('[r68] --check：%d 处锚点都命中 1 次（未写盘）：' % len(EDITS))
        for label, old, new in EDITS:
            print('   · ' + label)
        return 0
    for label, old, new in EDITS:
        html = html.replace(old, new, 1)
    # 标记：写进测试页那段注释里（它本来就是 r68 的东西）
    html = html.replace('<!-- ============ 测试页（连接诊断）—— r68 ============',
                        '<!-- ============ 测试页（连接诊断）—— %s ============' % MARK, 1)
    assert MARK in html, '替换后标记不在页面里'
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(html)
    print('[r68] ✓ 已改 %d 处：新增测试页（#paneT）+ 客户页降噪（日志折叠/明细进日志/加排查出口）' % len(EDITS))
    before = io.open(os.path.join(ROOT, 'app', 'base.before_r68.html'), encoding='utf-8').read()
    print('[r68] 页面净增 %d 字节' % (len(html.encode('utf-8')) - len(before.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
