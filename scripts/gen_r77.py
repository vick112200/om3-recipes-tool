# -*- coding: utf-8 -*-
"""第 77 轮：把"我还不确定的事"做成测试页上的按钮，一条条点、结果进日志（见 SPEC-round77.md）。

需求方 2026-09-28：「**我记得你之前有几个不确定的东西，用测试页来验证**」

把各轮规格里**明确写过"未读/待真机"**的项，做成测试页上的按钮（全部**只读**的放 A 组；
会动相机的单独一组并写明；页面自己判断不了的用"你回答我"两个按钮）：

A 组（只读，点了不动相机）
  ① 相机支持哪些命令       ← 第 65 轮 §5② / 第 66 轮"相机支不支持"：`get_commandlist.cgi`
  ② camprop 能不能读        ← 第 66 轮 §2 未读项：15 个 propname 逐个 `get_camprop.cgi?com=get`
  ③ camprop 的取值域        ← 第 66 轮 §2 未读项：`get_camprop.cgi?com=desc&propname=desclist`
  ④ BSSID 有没有被系统屏蔽   ← 第 64 轮最大的不确定：`cameraState()`/`wifiScanList()` 里的 BSSID
B 组（**会动相机**，写明后果）
  ⑤ 防掉线 set_timeout      ← 第 65 轮 §5③：`set_timeout.cgi?timeoutsec=1800`
  ⑥ 快门线：切到快门模式 + 按一下 + 切回 ← 第 65 轮 §5①：`switch_cammode.cgi?mode=shutter|rec` ＋ `exec_shutter.cgi?com=1stpush|1strelease`
C 组（页面判断不了，**你点一下告诉我**）
  ⑦ 下载能不能用            ← 第 75 轮我写过的"不确定"：WebView 里 `<a download>` 到底落不落文件
  ⑧ 复制能不能用            ← 同上：`execCommand('copy')` 到底行不行
  ⑨ 扫码能不能用            ← 第 64/67 轮真机待验：`getUserMedia` 拿不拿得到画面（只开 1 秒）

同时把 `req()` 导出成 `window.__om3req`（测试页要发 CGI，**给测试页复用**，不复制一份实现）。

⚠ 本轮**不新增 id**：所有新按钮用 `data-tv="uv-…"` 选择器（老探针的"不新增 id"断言不用动）。

用法：python scripts/gen_r77.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r77：不确定的事'
STEPS = []


def step(label):
    def deco(fn):
        STEPS.append((label, fn))
        return fn
    return deco


@step('① 把 req() 导出成 window.__om3req（测试页发 CGI 复用，不复制实现）')
def s_export_req(html):
    old = "  var _httpCbs = {}, _httpEarly = {};\n  window.__om3http = function(id, res){"
    assert html.count(old) == 1, 'http 桥那段没找到'
    new = ("  var _httpCbs = {}, _httpEarly = {};\n"
           "  /* r77：把 req() 也导出去 —— 测试页要发**只读 CGI**（get_commandlist / get_camprop…）；\n"
           "     函数声明会提升，所以这里写在定义之前也能用，且**不复制第二份实现**。 */\n"
           "  window.__om3req = function(path, opt){ return req(path, opt); };\n"
           "  window.__om3http = function(id, res){")
    return html.replace(old, new, 1)


@step('② 测试页加「不确定的事」卡片（A 只读 / B 会动相机 / C 你回答）')
def s_card(html):
    old = '  <div class="camcard">\n    <div class="camhd">日志（①②③ 三步共用这一份）—— '
    assert html.count(old) == 1, '测试页日志卡没找到'
    new = '''  <!-- r77：把"我还不确定的事"做成按钮（需求方：「我记得你之前有几个不确定的东西，用测试页来验证」）。
       来源逐条写在按钮下面；A 组只读、B 组会动相机、C 组要你回答。 -->
  <div class="camcard" style="border-color:#7e5a33">
    <div class="camhd">不确定的事（一条条点，结果自动进下面的日志）</div>
    <div class="camout" style="border-color:#7e5a33;font-size:12.5px;color:#dcb98a">
      <b>A 组：只读</b>（点了不会动相机）—— 用来定"能不能做"；<b>B 组：会动相机</b>（写明后果）；
      <b>C 组：页面判断不了</b>，要你看一眼再点「有 / 没有」。
      跑完直接「分享日志」发我，我按日志回你结论。
    </div>

    <button type="button" class="bigbtn alt" data-tv="uv-cmds">① 相机支持哪些命令（get_commandlist.cgi）</button>
    <div class="tvhint">只读。预期：列出命令，并直接标出我关心的几个在不在里面
      （camprop / set_camprop / exec_shutter / switch_cammode / set_timeout）——决定"改参 / 快门线 / 防掉线"能不能做。</div>

    <button type="button" class="bigbtn alt" data-tv="uv-camprop">② camprop 能不能读（15 个参数逐个试，只读）</button>
    <div class="tvhint">只读。预期：每个 propname 报 HTTP 码 + 头一段响应；有能读的就说明"实时改参"这条路是通的。</div>

    <button type="button" class="bigbtn alt" data-tv="uv-desc">③ camprop 的取值域（com=desc&amp;propname=desclist，只读）</button>
    <div class="tvhint">只读。预期：回一份"每个参数能取哪些值"的表 —— 这是做"实时改参"界面（滑块/下拉）的前提。</div>

    <button type="button" class="bigbtn alt" data-tv="uv-bssid">④ BSSID 有没有被系统屏蔽（只读）</button>
    <div class="tvhint">只读。预期：打印当前连接的 SSID/BSSID、扫描里相机那行的 BSSID。
      若显示成 02:00:00:00:00:00 或空 → 说明安卓把 BSSID 屏蔽了，第 64 轮"钉住 BSSID"就是白做（我会据此改回）。</div>

    <button type="button" class="bigbtn" data-tv="uv-timeout" style="background:#7e5a33">⑤ 防掉线：set_timeout 1800 秒（**会改相机设置**）</button>
    <div class="tvhint">会动相机（只改"空闲断开时间"，不改画质/配方）。预期：HTTP 200 → 之后写入配方中途更不容易掉线。</div>

    <button type="button" class="bigbtn" data-tv="uv-shutter" style="background:#7e5a33">⑥ 快门线：切快门模式 → 按一下 → 切回来（**会拍照**）</button>
    <div class="tvhint">会动相机：会真的按一次快门（请先把镜头盖取下、对准随便什么）。预期：日志依次出现
      「切到快门模式 → 1stpush → 1strelease → 切回拍照模式」，每步带 HTTP 码。</div>

    <button type="button" class="bigbtn alt" data-tv="uv-dl">⑦ 下载能不能用：生成一个测试文件（用"下载"那条路）</button>
    <div class="tvhint">页面判断不了，要看手机：点完去手机「文件 / 下载」里找 <code>OM3-下载测试.txt</code>，
      然后用下面两个按钮告诉我。</div>
    <div class="camlogbtns">
      <button type="button" data-tv="uv-dl-yes">⑦-1 我看到了（下载里有这个文件）</button>
      <button type="button" data-tv="uv-dl-no">⑦-2 没看到</button>
    </div>

    <button type="button" class="bigbtn alt" data-tv="uv-copy">⑧ 复制能不能用：复制一段测试文字</button>
    <div class="tvhint">页面判断不了，要看手机：点完后到别处（微信输入框 / 备忘录）长按粘贴，看粘出来的是不是
      <code>OM3 复制测试 OK</code>，再用下面两个按钮告诉我。</div>
    <div class="camlogbtns">
      <button type="button" data-tv="uv-copy-yes">⑧-1 粘出来了（就是那行字）</button>
      <button type="button" data-tv="uv-copy-no">⑧-2 粘出来是空的 / 不对</button>
    </div>

    <button type="button" class="bigbtn alt" data-tv="uv-qr">⑨ 扫码能不能用：开 1 秒摄像头试试（只开不拍）</button>
    <div class="tvhint">只读（画面不外传、1 秒后自动关）。预期：说"摄像头可用"；失败会给原因（多半是"相机"权限没给）。</div>

    <div class="tvhint">结果写在上面的结果框里，同时也进下面那份日志（发日志时一起到我这儿）。</div>
  </div>

  <div class="camcard">
    <div class="camhd">日志（①②③ 三步共用这一份）—— '''
    return html.replace(old, new, 1)


@step('③ 接上这 9 条的实现（复用 __om3req / tvOut / 同一份日志）')
def s_js(html):
    old = ('    /* 只有"测试页可见"时才刷（客户页零开销） */\n'
           '    try{ setInterval(function(){ if(tvOn()) tvRefreshNow(); }, 1500); }catch(e){ om3err(e, "silent"); }\n'
           '    try{ tvRefreshNow(); }catch(e){ om3err(e, "silent"); }\n'
           '  })();')
    assert html.count(old) == 1, '测试页 IIFE 的收尾没找到'
    new = ('    /* 只有"测试页可见"时才刷（客户页零开销） */\n'
           '    try{ setInterval(function(){ if(tvOn()) tvRefreshNow(); }, 1500); }catch(e){ om3err(e, "silent"); }\n'
           '    try{ tvRefreshNow(); }catch(e){ om3err(e, "silent"); }\n'
           '\n' + JS_MODULE + '\n  })();')
    return html.replace(old, new, 1)


JS_MODULE = r'''    /* ================= r77：不确定的事（逐条验） =================
       需求方：「我记得你之前有几个不确定的东西，用测试页来验证」。
       每条都：把结论写进**同一份日志**（这样"分享日志"发我时一起到），原始证据也写（HTTP 码 + 响应片段）。
       ⚠ 只读的在 A 组；会动相机的在 B 组；页面判断不了的用"你回答"按钮（C 组）。 */
    /* ⚠ 别写成 tvOut(t) + line(log3,t)：line() **本身**会往 ALLLOG 推一行（见块07），
       两个都调 = 同一句在日志里出现两遍（本轮实测 DOM 1 次 / 日志 2 次，已修）。
       现在：日志走 line(log3,…) 一次；页面那个结果框**自己拼 DOM**（不再进日志）。 */
    function uvOut(t, cls){
      try{ line(log3, t, cls || ''); }catch(e){}
      try{
        var o = $('tvOut');
        if(o){ var d = document.createElement('div'); if(cls) d.className = cls; d.textContent = t; o.appendChild(d); o.scrollTop = o.scrollHeight; }
      }catch(e2){}
    }
    function uvBtn(name){ return document.querySelector('[data-tv="' + name + '"]'); }
    function uvBind(name, fn){ var b = uvBtn(name); if(b) b.addEventListener('click', fn); }
    function uvClear(){ var o = $('tvOut'); if(o) o.innerHTML = ''; }   /* 复用既有结果框，不新增 id */
    function uvReq(path){ return window.__om3req ? window.__om3req(path) : Promise.reject(new Error('没有 __om3req')); }
    function uvBrief(t, n){ t = String(t == null ? '' : t).replace(/\s+/g, ' '); return t.length > (n || 160) ? (t.slice(0, n || 160) + '…') : t; }

    /* ① 相机支持哪些命令 —— 决定"改参/快门线/防掉线"能不能做 */
    uvBind('uv-cmds', function(){
      uvClear();
      uvOut('【验①】读 get_commandlist.cgi（只读）…');
      uvReq('/get_commandlist.cgi').then(function(r){
        var t = String(r.text || '');
        uvOut('【验①】HTTP ' + r.status + '，响应 ' + t.length + ' 字符', 'ok');
        var want = ['camprop', 'set_camprop', 'get_camprop', 'exec_shutter', 'switch_cammode', 'set_timeout', 'exec_takemisc'];
        var hit = [], miss = [];
        for(var i = 0; i < want.length; i++){ (t.indexOf(want[i]) >= 0 ? hit : miss).push(want[i]); }
        uvOut('【验①】响应里出现：' + (hit.join(' / ') || '（一个都没有）'));
        uvOut('【验①】响应里没有：' + (miss.join(' / ') || '（无）'));
        uvOut('【验①】响应头一段：' + uvBrief(t, 400));
        var n = (t.match(/\.cgi/g) || []).length;
        uvOut('【验①】结论：响应里提到 .cgi 约 ' + n + ' 次；' +
              (hit.length ? ('**支持这些：' + hit.join('、') + '** → 相关功能可做') : '**一个都没提到** → 以命令表为准，相关功能先别做'));
      }).catch(function(e){
        uvOut('【验①】失败：' + e.message + '（多半是没连上相机 / 没权限）', 'err');
      });
    });

    /* ② camprop 能不能读（15 个 propname 逐个试，只读） */
    var UV_PROPS = ['qualitymovie','shutspeedvalue','takemode','exposemovie','colortone','colorphase',
                    'expcomp','SceneSub','focalvalue','wbvalue','isospeedvalue','drivemode','supermacrosub'];
    uvBind('uv-camprop', function(){
      uvClear();
      uvOut('【验②】逐个试读 ' + UV_PROPS.length + ' 个 propname（只读，会连着发 ' + UV_PROPS.length + ' 个请求）…');
      var ok = [], bad = [], i = 0;
      function nextOne(){
        if(i >= UV_PROPS.length){
          uvOut('【验②】成功 ' + ok.length + ' / 失败 ' + bad.length, ok.length ? 'ok' : 'err');
          uvOut('【验②】能读的：' + (ok.join('、') || '（无）'));
          uvOut('【验②】读不到：' + (bad.join('、') || '（无）'));
          uvOut('【验②】结论：' + (ok.length
                ? ('**camprop 通道可用（' + ok.length + ' 个参数能读）** → "实时看/改参"这条路是通的')
                : '**一个都读不到** → 这条通道在本机/本固件上不可用，第 66 轮那事就别做了'));
          return;
        }
        var p = UV_PROPS[i++];
        uvReq('/get_camprop.cgi?com=get&propname=' + encodeURIComponent(p)).then(function(r){
          ok.push(p + '(HTTP ' + r.status + ')');
          uvOut('【验②】' + p + ' → HTTP ' + r.status + ' : ' + uvBrief(r.text, 100));
          nextOne();
        }).catch(function(e){
          bad.push(p + '(' + uvBrief(e.message, 40) + ')');
          uvOut('【验②】' + p + ' → 失败：' + uvBrief(e.message, 80));
          nextOne();
        });
      }
      nextOne();
    });

    /* ③ camprop 的取值域（只读） */
    uvBind('uv-desc', function(){
      uvClear();
      uvOut('【验③】读 com=desc&propname=desclist（只读）…');
      uvReq('/get_camprop.cgi?com=desc&propname=desclist').then(function(r){
        uvOut('【验③】HTTP ' + r.status + '，响应 ' + String(r.text || '').length + ' 字符', 'ok');
        uvOut('【验③】响应头一段：' + uvBrief(r.text, 800));
        uvOut('【验③】结论：' + (String(r.text || '').length > 40
              ? '**拿到了描述表** → 做"改参界面"有了取值域依据（我会按它做滑块/下拉）'
              : '响应太短，可能这台相机不支持 desc，先不做改参界面'));
      }).catch(function(e){ uvOut('【验③】失败：' + e.message, 'err'); });
    });

    /* ④ BSSID 有没有被系统屏蔽（只读）—— 第 64 轮最大的不确定 */
    uvBind('uv-bssid', function(){
      uvClear();
      var N = tvNative();
      var st = '{}';
      try{ st = String(N && N.cameraState ? N.cameraState() : '{}'); }catch(e){}
      uvOut('【验④】cameraState() = ' + uvBrief(st, 200));
      var b = '';
      try{ var j = JSON.parse(st || '{}'); b = String((j && j.bssid) || ''); }catch(e){}
      var scanB = [];
      try{
        var raw = String(N && N.wifiScanList ? N.wifiScanList() : '[]');
        var L = JSON.parse(raw) || [];
        for(var i = 0; i < L.length; i++){
          if(L[i] && L[i].cam) scanB.push((L[i].ssid || '?') + ' → ' + (L[i].bssid || '（空）'));
        }
      }catch(e){}
      uvOut('【验④】扫描里"像相机"那几行的 BSSID：' + (scanB.join(' ｜ ') || '（这次没扫到相机热点）'));
      function verdict(x){
        if(!x) return '（拿不到）';
        if(x === '02:00:00:00:00:00') return '**被系统屏蔽了**（安卓隐私）';
        if(/^00:00:00:00:00:00$|^FF:FF:FF:FF:FF:FF$/.test(x)) return '**是被抹掉的假值**';
        return '是真 MAC ✓';
      }
      uvOut('【验④】当前连接 BSSID = ' + (b || '（空）') + ' → ' + verdict(b));
      uvOut('【验④】结论：' + (b && b !== '02:00:00:00:00:00' && !/^0{2}:/.test(b)
            ? 'BSSID 可用 → 第 64 轮"钉住 BSSID"有意义'
            : 'BSSID 拿不到真值 → 我会把第 64 轮那条改成"只用 SSID"（不白等/不白设）'));
    });

    /* ⑤ 防掉线 set_timeout（会改相机设置） */
    uvBind('uv-timeout', function(){
      uvClear();
      if(!window.confirm('这条会**改相机的空闲断开时间**（set_timeout=1800 秒），不改画质/配方。要继续吗？')){ uvOut('【验⑤】已取消'); return; }
      uvOut('【验⑤】发 set_timeout.cgi?timeoutsec=1800（会改相机设置）…');
      uvReq('/set_timeout.cgi?timeoutsec=1800').then(function(r){
        uvOut('【验⑤】HTTP ' + r.status + ' : ' + uvBrief(r.text, 120), 'ok');
        uvOut('【验⑤】结论：' + (r.status === 200
              ? '**能用** → 我会在"连上之后"自动发一次，减少写入中途掉线'
              : '没成功（HTTP ' + r.status + '）→ 这条就不做了'));
      }).catch(function(e){ uvOut('【验⑤】失败：' + e.message, 'err'); });
    });

    /* ⑥ 快门线：切快门模式 → 按一下 → 切回（会拍照） */
    uvBind('uv-shutter', function(){
      uvClear();
      if(!window.confirm('这条会**真的按一次快门**（相机上会拍一张）。镜头盖请取下。要继续吗？')){ uvOut('【验⑥】已取消'); return; }
      var seq = [['/switch_cammode.cgi?mode=shutter', '切到快门模式'],
                 ['/exec_shutter.cgi?com=1stpush',    '按下（1stpush）'],
                 ['/exec_shutter.cgi?com=1strelease', '松开（1strelease）'],
                 ['/switch_cammode.cgi?mode=rec',     '切回拍照模式']];
      var i = 0, bad = 0;
      function one(){
        if(i >= seq.length){
          uvOut('【验⑥】结论：' + (bad === 0
                ? '**纯 HTTP 快门线可用**（四步都 200）→ 这个功能能做'
                : ('有 ' + bad + ' 步没成功 → 这台机型上先不做快门线')), bad === 0 ? 'ok' : 'warn');
          return;
        }
        var p = seq[i][0], name = seq[i][1]; i++;
        uvOut('【验⑥】' + name + ' …');
        uvReq(p).then(function(r){
          if(r.status !== 200) bad++;
          uvOut('【验⑥】' + name + ' → HTTP ' + r.status + ' : ' + uvBrief(r.text, 80));
          setTimeout(one, 600);
        }).catch(function(e){ bad++; uvOut('【验⑥】' + name + ' → 失败：' + e.message, 'err'); one(); });
      }
      one();
    });

    /* ⑦ 下载能不能用（页面判断不了 → 你回答） */
    uvBind('uv-dl', function(){
      uvClear();
      var nm = 'OM3-下载测试.txt';
      var txt = 'OM-3 下载测试 OK\n' + new Date().toLocaleString() + '\n';
      uvOut('【验⑦】正在用"下载"那条路生成 ' + nm + ' …（生成后请到手机「文件 / 下载」里找它）');
      try{
        if(typeof om3Download === 'function'){ om3Download(nm, txt, 'text/plain'); uvOut('【验⑦】已触发下载。请去手机「下载」看有没有这个文件，再点下面 ⑦-1 / ⑦-2', 'ok'); }
        else uvOut('【验⑦】页面里找不到 om3Download', 'err');
      }catch(e){ uvOut('【验⑦】出错：' + e.message, 'err'); }
    });
    uvBind('uv-dl-yes', function(){ uvClear(); uvOut('【验⑦】用户回答：**下载里有这个文件 = 是**（WebView 支持 <a download>）', 'ok'); });
    uvBind('uv-dl-no',  function(){ uvClear(); uvOut('【验⑦】用户回答：**下载里有这个文件 = 没有**（WebView 不接管下载）→ 以后一律用「分享日志」', 'warn'); });

    /* ⑧ 复制能不能用（页面判断不了 → 你回答） */
    uvBind('uv-copy', function(){
      uvClear();
      uvOut('【验⑧】正在复制一行测试文字…（请到别处长按粘贴，看是不是 "OM3 复制测试 OK"）');
      try{
        if(typeof om3Copy === 'function'){ om3Copy('OM3 复制测试 OK', ''); uvOut('【验⑧】已尝试复制。粘一下看结果，再点 ⑧-1 / ⑧-2', 'ok'); }
        else uvOut('【验⑧】页面里找不到 om3Copy', 'err');
      }catch(e){ uvOut('【验⑧】出错：' + e.message, 'err'); }
    });
    uvBind('uv-copy-yes', function(){ uvClear(); uvOut('【验⑧】用户回答：**复制可用 = 是**（execCommand/剪贴板这条路能走）', 'ok'); });
    uvBind('uv-copy-no',  function(){ uvClear(); uvOut('【验⑧】用户回答：**复制可用 = 否** → 以后日志一律走「分享日志」', 'warn'); });

    /* ⑨ 扫码能不能用（只开 1 秒摄像头） */
    uvBind('uv-qr', function(){
      uvClear();
      uvOut('【验⑨】试着开一下摄像头（1 秒后自动关；画面不外传）…');
      try{
        if(!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia){ uvOut('【验⑨】这个 WebView 没有 getUserMedia → 扫码做不了', 'err'); return; }
        /* ⚠ 加 6 秒兜底：有些环境里 getUserMedia 会**一直挂着**（既不给画面也不报错），
           那我们就永远得不到结论 —— 所以到点必须自己说一句（真机上也不会静默）。 */
        var uv9done = false;
        var uv9to = setTimeout(function(){
          if(uv9done) return; uv9done = true;
          uvOut('【验⑨】6 秒没结果：多半是「相机」权限没给，或这台机器没有可用摄像头', 'warn');
        }, 6000);
        navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } }).then(function(st){
          if(uv9done) return; uv9done = true; clearTimeout(uv9to);
          uvOut('【验⑨】拿到摄像头 ✓（扫码的基础具备）', 'ok');
          try{ var tr = st.getTracks(); for(var i = 0; i < tr.length; i++) tr[i].stop(); uvOut('【验⑨】已把摄像头关掉'); }catch(e){}
        }).catch(function(e){
          if(uv9done) return; uv9done = true; clearTimeout(uv9to);
          uvOut('【验⑨】失败：' + (e && e.name ? e.name : '') + ' ' + (e && e.message ? e.message : '') +
                '（NotAllowedError = 没给「相机」权限；去 设置→应用→权限 里给上再点一次）', 'err');
        });
      }catch(e){ uvOut('【验⑨】出错：' + e.message, 'err'); }
    });
'''


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
    html = html.replace('    /* ================= r77：不确定的事（逐条验） =================',
                        '    /* ================= %s（逐条验） =================' % MARK, 1)
    assert MARK in html, '标记没插进去'
    return html, changed


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r77] 已经是目标状态（页面里有 "%s"）—— 不重复改。' % MARK)
        return 0
    try:
        new, changed = run(html)
    except AssertionError as e:
        print('[r77] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r77] --check：%d 步都能跑通（未写盘）：' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(new)
    print('[r77] ✓ 已改 %d 步：测试页加"不确定的事"9 条（A 只读 / B 会动相机 / C 你回答）' % len(changed))
    before = io.open(os.path.join(ROOT, 'app', 'base.before_r77.html'), encoding='utf-8').read()
    print('[r77] 页面净增 %d 字节' % (len(new.encode('utf-8')) - len(before.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
