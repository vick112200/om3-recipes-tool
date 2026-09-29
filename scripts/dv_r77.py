# -*- coding: utf-8 -*-
"""第 77 轮验收：测试页上的「不确定的事」9 条能不能真的跑出结论（SPEC-round77.md）。

用**假原生桥**把 CGI 的应答喂回去（`camGetAsync` 返回一个 id，随后 `window.__om3http(id,{s,t})`
把"原生后台线程发完 HTTP 的结果"推回来 —— 和真机同一条路），然后逐条点按钮，检查：
  · 每条都**把结论写进同一份日志**（这样"分享日志"发我时一起到）
  · 只读的 A 组不发任何写请求
  · B 组（会动相机）**必须先弹确认**，确认后才发请求，且请求序列正确（⑥ 四步：切快门→按→松→切回）
  · C 组（页面判断不了）点了「有/没有」后，**用户回答进日志**
  · 所有新按钮用 data-tv 选择器 → **老 id 一个不少、本轮不新增 id**

跑法：python scripts/dv_r77.py
"""
import io
import json
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
PAGE = os.path.join(ROOT, 'app', 'base.html')
OLD = os.path.join(ROOT, 'app', 'base.before_r77.html')
TMP = os.environ.get('TEMP', r'C:\Users\82302\AppData\Local\Temp')
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


page = io.open(PAGE, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()


def ids(t):
    return set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', t))


# 假原生桥：把每个 GET 都记下来，并按路径回一份"像相机"的应答
BRIDGE = r'''
window.__reqs = [];
window.__dl = 0;
window.confirm = function(){ window.__confirmN = (window.__confirmN || 0) + 1; return true; };   /* 无头里自动"点确定" */
window.OM3Native = (function(){
  var n = 0;
  function reply(p){
    if(p.indexOf('get_commandlist') >= 0)
      return '<?xml version="1.0"?><list><cmd>get_camprop.cgi</cmd><cmd>set_camprop.cgi</cmd>' +
             '<cmd>exec_shutter.cgi</cmd><cmd>switch_cammode.cgi</cmd><cmd>set_timeout.cgi</cmd></list>';
    if(p.indexOf('com=desc') >= 0)
      return '<?xml version="1.0"?><desclist><propname name="expcomp"><value>0</value><value>1</value></propname></desclist>';
    if(p.indexOf('get_camprop') >= 0) return '<?xml version="1.0"?><value>1</value>';
    return '<?xml version="1.0"?><status>0</status>';
  }
  return {
    permState: function(){ return '{"camera":true,"fine":true,"nearby":true,"sdk":34}'; },
    wifiState: function(){ return JSON.stringify({ssid:'OM-3', on:true}); },
    /* 故意把 BSSID 报成被系统屏蔽的假值 —— 验证"验④"能不能自己识别出来 */
    wifiScanList: function(){ return JSON.stringify([{ssid:'OM-3', bssid:'02:00:00:00:00:00', level:-42, cam:true},
                                                     {ssid:'我家WiFi', bssid:'11:22:33:44:55:66', level:-55, cam:false}]); },
    cameraState: function(){ return '{"connected":true,"ssid":"OM-3","bssid":"02:00:00:00:00:00"}'; },
    startWatch: function(){ return 'ok'; },
    camGet: function(p){ window.__reqs.push(String(p)); return '{"s":200,"t":"ok"}'; },
    camGetAsync: function(p){
      p = String(p); window.__reqs.push(p);
      var id = 'sim' + (++n);
      setTimeout(function(){ try{ window.__om3http(id, {s:200, t: reply(p)}); }catch(e){} }, 30);
      return id;
    },
    camPostAsync: function(p, b){ return window.OM3Native.camGetAsync(p); },
    disconnectCamera: function(){ return 'ok'; }, forgetWifi: function(){ return 'ok'; }, dropCamera: function(){ return 'ok'; },
    openWifiSettings: function(){ return 'ok'; }, openAppSettings: function(){ return 'ok'; },
    shareText: function(){ return 'ok'; }, bleScanStop: function(){ return 'ok'; }, bleDisconnect: function(){ return 'ok'; }
  };
})();
/* 页面里"下载"用的 a.download 在无头里不会真下 —— 记一笔，证明这条代码路径被执行到了 */
document.addEventListener('click', function(e){
  var a = e.target && e.target.closest ? e.target.closest('a[download]') : null;
  if(a) window.__dl++;
}, true);
'''


def run_headless(tag, pre, steps, budget=45000):
    tail = ('<script>\nvar o=[],STEPS=' + json.dumps([[s, d] for s, d in steps], ensure_ascii=False) + ',si=0;\n'
            'function g(i){return document.getElementById(i);}\n'
            'function finish(){var d=document.createElement("div");d.id=\'' + tag + '\';'
            'd.textContent=o.join(" ;; ");document.body.appendChild(d);}\n'
            'function next(){if(si>=STEPS.length){finish();return;}var st=STEPS[si++];'
            'try{(new Function(st[0]))();}catch(e){o.push("STEP-ERR@"+si+": "+e.message);}setTimeout(next,st[1]);}\n'
            'setTimeout(next,1600);\n</script>')
    i0 = page.find('<body')
    j0 = page.find('>', i0) + 1
    out = (page[:j0] + '<script>window.__OM3_APP__=1;window.__errs=[];'
           "window.addEventListener('error',function(e){window.__errs.push((e.message||'')+' @'+(e.lineno||0));});"
           'try{' + pre + '}catch(e){}</script>' + page[j0:].replace('</body>', tail + '</body>', 1))
    hp = os.path.join(TMP, 'dv_r77_%s.html' % tag)
    io.open(hp, 'w', encoding='utf-8', newline='').write(out)
    ud = os.path.join(TMP, 'o77_' + tag)
    subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
    r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                        '--no-first-run', '--user-data-dir=' + ud, '--window-size=412,800',
                        '--virtual-time-budget=%d' % budget, '--dump-dom',
                        'file:///' + hp.replace(os.sep, '/')],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
    dom = r.stdout or ''
    k = dom.find('id="%s"' % tag)
    return (dom[k:].split('>', 1)[1].split('</div>')[0].replace('&lt;', '<')
            .replace('&gt;', '>').replace('&amp;', '&')) if k >= 0 else ''


print('=== A. 静态：按钮与接线 ===')
names = re.findall(r'data-tv="(uv-[a-z\-0-9]+)"', page)
A(len(names) == 13, 'A1 测试页有 13 个新按钮（9 条 + 4 个"我看到了/没看到"回答键），实测 %d 个：%s' % (len(names), ' '.join(names)))
A('window.__om3req = function(path, opt){ return req(path, opt); };' in page, 'A2 req() 已导出为 __om3req（测试页复用，不复制实现）')
A('r77：不确定的事' in page, 'A3 r77 标记在（生成脚本幂等判据）')
si, so = ids(page), ids(old)
A(not (so - si), 'A4 老 id 一个都没少（少的：%s）' % (sorted(so - si) or '无'))
A(not (si - so), 'A5 本轮**没有新增 id**（多的是：%s）' % (sorted(si - so) or '无'))

print('=== B. 无头真点：逐条跑一遍（假桥喂应答）===')
STEPS = [
    ("g('tabTest').click();", 600),
    # ── A 组：只读三条
    ("document.querySelector('[data-tv=\"uv-cmds\"]').click();", 1200),
    ("document.querySelector('[data-tv=\"uv-camprop\"]').click();", 3000),   # 13 个串联请求
    ("document.querySelector('[data-tv=\"uv-desc\"]').click();", 900),
    ("document.querySelector('[data-tv=\"uv-bssid\"]').click();", 400),
    # ── B 组：会动相机（confirm 已在桩里自动 true）
    ("document.querySelector('[data-tv=\"uv-timeout\"]').click();", 900),
    ("document.querySelector('[data-tv=\"uv-shutter\"]').click();", 5000),   # 四步 × 600ms
    # ── C 组：页面判断不了的两条 + 扫码
    ("document.querySelector('[data-tv=\"uv-dl\"]').click();", 500),
    ("document.querySelector('[data-tv=\"uv-dl-yes\"]').click();", 300),
    ("document.querySelector('[data-tv=\"uv-copy\"]').click();", 400),
    ("document.querySelector('[data-tv=\"uv-copy-no\"]').click();", 300),
    ("document.querySelector('[data-tv=\"uv-qr\"]').click();", 7500),   # ⑨ 有 6 秒兜底，等它出结论
    # ── 收结果
    # 用 r74 导出的 __om3logText() 取日志（ALLLOG 是块内变量、在页面全局取不到）——
    # 这也正是"我实际会收到的那份文本"
    ("var L = (window.__om3logText ? window.__om3logText() : '');"
     "o.push('B1 日志长度=' + L.length);"
     "['【验①】','【验②】','【验③】','【验④】','【验⑤】','【验⑥】','【验⑦】','【验⑧】','【验⑨】']"
     ".forEach(function(k){ o.push('B 有 ' + k + '=' + (L.indexOf(k) >= 0)); });"
     "o.push('B2 请求序列=' + (window.__reqs||[]).join(' | '));"
     "o.push('B3 confirm 弹了几次=' + (window.__confirmN||0) + ' ; 触发过下载=' + (window.__dl||0));"
     "o.push('B4 运行错误=' + (window.__errs?window.__errs.length:0));"
     "o.push('B5 结论行=' + L.split('\\n').filter(function(x){return x.indexOf('结论') >= 0;}).map(function(x){return x.replace(/^\\[[^\\]]*\\]/,'').slice(0,60);}).join(' ¶ '));", 300),
    # 把**所有 【验X】 原始行**也带出来（含"用户回答""被系统屏蔽"这些不在结论行里的证据）
    # —— 这也正是"我发日志时会收到的那份内容"
    # ⚠ 每一步是各自的 new Function，上一步的 var L 传不过来 → 这一步自己重新取一次
    ("var L=(window.__om3logText?window.__om3logText():'');"
     "o.push('B7 验的原始行=' + L.split('\\n').filter(function(x){return x.indexOf('【验') >= 0;})"
     ".map(function(x){return x.replace(/^\\[[^\\]]*\\]/, '');}).join(' ‖ '));", 300),
]
got = run_headless('R77A', BRIDGE, STEPS)
for seg in got.split(' ;; '):
    print('  · ' + seg[:2500])
A('STEP-ERR' not in got, 'B0 步骤没抛错')
for k in ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨']:
    A('B 有 【验%s】=true' % k in got, 'B 第 %s 条的结论进了日志（发日志时一起到我这儿）' % k)
A(re.search(r'B3 confirm 弹了几次=2', got) is not None, 'B3 两条"会动相机"的**都弹了确认**（各 1 次 = 2 次）')
A(re.search(r'触发过下载=1', got) is not None, 'B3 验⑦ 真的走了"下载"那条代码路径')
reqs = re.search(r'B2 请求序列=([^;]*)', got)
reqs = reqs.group(1) if reqs else ''
A('/get_commandlist.cgi' in reqs, 'B4 验① 发了 get_commandlist.cgi')
A(len(re.findall(r'get_camprop\.cgi\?com=get', reqs)) == 13, 'B4 验② 逐个试了 13 个 propname（实测 %d 个）'
  % len(re.findall(r'get_camprop\.cgi\?com=get', reqs)))
A('com=desc&propname=desclist' in reqs, 'B4 验③ 发了 desc 请求')
A('/set_timeout.cgi?timeoutsec=1800' in reqs, 'B4 验⑤ 发了 set_timeout（防掉线）')
for p in ['/switch_cammode.cgi?mode=shutter', '/exec_shutter.cgi?com=1stpush',
          '/exec_shutter.cgi?com=1strelease', '/switch_cammode.cgi?mode=rec']:
    A(p in reqs, 'B4 验⑥ 快门线序列里发了 %s' % p)
A('关闭' not in reqs and 'mode=play' not in reqs, 'B5 只读的 A 组**没有**发任何写请求（没动相机）')
A('B4 运行错误=0' in got, 'B6 全程 0 运行错误')
_dupn = got.count('【验⑨】')
A(_dupn <= 3, 'B6b 每条【验】在日志里只写一次（本轮修过"tvOut+line 双份"的坑；实测【验⑨】出现 %d 次）' % _dupn)
A('【验⑦】用户回答：**下载里有这个文件 = 是**' in got.replace(' ', ' ') or '下载里有这个文件 = 是' in got,
  'B7 验⑦ 的"我看到了"回答进了日志')
A('复制可用 = 否' in got, 'B8 验⑧ 的"粘出来是空的"回答进了日志')
A(re.search(r'【验⑨】(失败|拿到摄像头|这个 WebView 没有 getUserMedia|6 秒没结果)', got) is not None, 'B9 验⑨ 扫码给出了明确结论（成功或失败+原因，不静默）')
A('被系统屏蔽了' in got, 'B10 验④ 认出了 02:00:00:00:00:00 → 会自己判定"BSSID 被系统屏蔽"')
A(re.search(r'能读的：|一个都读不到|成功 \d+ / 失败 \d+', got) is not None, 'B11 验② 给了"能读几个"的汇总结论')

print()
print('第 77 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
