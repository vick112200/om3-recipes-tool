# -*- coding: utf-8 -*-
"""第 39 轮（B）验收：场景对比页 —— select 下拉 + 按场景挑图 + 保留左右滑动 + 去掉顶部大标题。
跑法：python scripts/dv_scene39.py"""
import io, json, os, re, shutil, subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')
SRC = r'D:\workspace\om3-handbook'
TMP = r'C:\Users\82302\AppData\Local\Temp'
src = io.open(SRC + r'\app\base.html', encoding='utf-8').read()
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


print('=== 静态 ===')
ipc = src.find('<div id="paneC"')
pc = src[ipc:ipc + 60000]      # ⚠ 不能用 paneD 定界：paneD 在文件里排在 paneC 前面

A('<select id="scsel"' in pc, '① #scsel 下拉在场景对比页里')
A(pc.count('<optgroup') >= 2, '① 下拉分两组（实拍对比 / 按场景挑）')
A('id="scidxlist"' not in pc or '<!--' in pc[:pc.find('id="scidxlist"')], '② 旧的 78 行长索引已不显示')
A('#scbar{display:none !important}' in src, '② 旧按钮条用 CSS 隐藏（DOM 保留，原绑定不动）')
A('<h1>场景对比</h1>' not in pc, '③ paneC 顶部大标题已去掉')
A('.scselbtn{' in src and '.scmenu.open{display:block}' in src and '.scselnative{' in src,
  '③ 第 40 轮起：原生 select 已隐藏，改用**自绘下拉**（.scselbtn 按钮 + .scmenu 面板）')
sc = re.search(r'window\.__OM3SC__\s*=\s*(\[.*?\]);\n', src, re.S)
SC = json.loads(sc.group(1)) if sc else []
A(len(SC) == 18, '④ __OM3SC__ 有 18 个场景（第 57 轮删了「婚礼聚会 / 儿童亲子」（没实拍 → 改成搜索找风格）；实测 %d）' % len(SC))
A(all(len(x['items']) >= 1 for x in SC), '④ 每个场景都 ≥1 条有图（最少 %d）' % min(len(x['items']) for x in SC))
A(all(not str(it['f']).startswith('images/') for x in SC for it in x['items']),
  '④ 场景 slides 的图名都是裸文件名（不会拼成 images/images/）')
A(all(os.path.exists(os.path.join(SRC, r'apk\assets\images', it['f'])) for x in SC for it in x['items']),
  '④ 场景 slides 引用的图**全部存在**')
PT = json.loads(re.search(r'window\.__OM3PHOTOTAGS__\s*=\s*(\{.*?\});\n', src, re.S).group(1))
# 第 56 轮改口径：图库里真·人像特写很少（全库 3 张），所以不再要求"70% 带人像标签"，
# 改成：**声称是归类的，标签必须真的对得上；剩下的必须明说"没有对题实拍"**（详见 dv_r56）
_p = next(x for x in SC if x['k'] == 'portrait')
p_ok = sum(1 for it in _p['items'] if '人像特写' in PT.get(it['f'], []))
p_mis = sum(1 for it in _p['items'] if (it.get('d') or '').startswith('本条没有对「'))
p_bad = [it['n'] for it in _p['items']
         if (it.get('d') or '').startswith('图按画面自动归类') and '人像特写' not in PT.get(it['f'], [])]
A(p_ok + p_mis == len(_p['items']) and not p_bad,
  '④ 「人像肤色」%d 条：真·人像特写 %d 条、明说兜底 %d 条、谎报 %d 条'
  % (len(_p['items']), p_ok, p_mis, len(p_bad)))

# ---------------- 运行时（临时把图库挂到 app/images，验证图真能加载）----------------
print('=== 运行时（含图片真实加载）===')
d = SRC + r'\app\images'
shutil.rmtree(d, ignore_errors=True)
os.makedirs(d)
srcimg = SRC + r'\apk\assets\images'
# 只拷**页面实际引用**的图（卡片 data-im + 21 个场景 slides），不拷整个 52MB 图库
need = set(re.findall(r'data-im="([^"]+)"', src))
for x in SC:
    for it in x['items']:
        need.add(it['f'])
for f in sorted(need):
    sp = os.path.join(srcimg, f)
    if os.path.exists(sp):
        shutil.copy(sp, os.path.join(d, f))
print('    （探针临时挂了 %d 张图到 app/images，用于验证「图真的加载出来」）' % len(need))

JS = r"""
setTimeout(function(){
  var o = [];
  function ok(c, m){ o.push((c ? '[OK ] ' : '[FAIL] ') + m); }
  function shown(id){ var e = document.getElementById(id); return !!e && getComputedStyle(e).display !== 'none'; }
  function imgsOK(sel){
    var a = document.querySelectorAll(sel), n = 0, tot = 0;
    for (var i = 0; i < a.length; i++){ tot++; if (a[i].naturalWidth > 0) n++; }
    return [n, tot];
  }
  document.querySelector('#barABC button[data-p="C"]').click();
  setTimeout(function(){
    ok(shown('paneC'), '① 能切到场景对比页');
    ok(!!document.getElementById('scsel'), '① 下拉在页面上');
    var sel = document.getElementById('scsel');
    ok(sel.options.length === 24, '① 下拉 24 项（6 实拍 + 18 场景，实测 ' + sel.options.length + '）');
    ok(sel.value === 'u:0', '① 默认停在实拍对比第一项');
    ok(!shown('scbar'), '② 旧按钮条已隐藏');
    var a1 = imgsOK('#scpager .scslide img');
    ok(a1[1] > 40 && a1[0] === a1[1], '② 实拍对比：' + a1[1] + ' 张图，**全部真的加载出来**（' + a1[0] + '/' + a1[1] + '）');
    ok(/^1 – 1 \/ \d+/.test(document.getElementById('scpos').textContent), '② 还是一屏一张（' + document.getElementById('scpos').textContent + '）');
    /* 按场景挑：人像 */
    sel.value = 's:portrait';
    sel.dispatchEvent(new Event('change', {bubbles: true}));
    setTimeout(function(){
      var sl = document.querySelectorAll('#scpager .scslide');
      var a2 = imgsOK('#scpager .scslide img');
      ok(sl.length > 8, '③ 选「人像肤色」→ ' + sl.length + ' 张 slide');
      ok(a2[0] === a2[1] && a2[1] > 5, '③ 这些图也全部加载出来（' + a2[0] + '/' + a2[1] + '）');
      var txt = document.querySelector('#scpager .scslide').textContent || '';
      ok(txt.indexOf('自动归类') >= 0, '③ 图上标注了"按画面自动归类"（用户要知道可能看错）');
      ok(document.querySelectorAll('#scpager .scwheel').length > 0, '③ 每张还带小色轮');
      var hasJump = document.querySelectorAll('#scpager .scjump').length > 0;
      ok(hasJump, '③ 还能一键跳到原版卡片');
      /* 夜景场景 */
      sel.value = 's:night';
      sel.dispatchEvent(new Event('change', {bubbles: true}));
      setTimeout(function(){
        var n2 = document.querySelectorAll('#scpager .scslide').length;
        ok(n2 > 3, '④ 选「夜景霓虹」→ ' + n2 + ' 张');
        var a3 = imgsOK('#scpager .scslide img');
        ok(a3[0] === a3[1], '④ 夜景的图也全部加载（' + a3[0] + '/' + a3[1] + '）');
        /* 切回实拍对比 */
        sel.value = 'u:1';
        sel.dispatchEvent(new Event('change', {bubbles: true}));
        setTimeout(function(){
          ok(document.getElementById('scpos').textContent.indexOf('/') > 0 &&
             document.querySelectorAll('#scpager .scslide').length > 30, '⑤ 能切回实拍对比（' + document.getElementById('scpos').textContent + '）');
          ok(window.__errs.length === 0, '⑥ 全程 0 JS 报错（' + window.__errs.length + '）');
          var d2 = document.createElement('pre'); d2.id = 'DBGOUT'; d2.textContent = o.join('\n');
          document.body.appendChild(d2);
        }, 700);
      }, 900);
    }, 900);
  }, 1200);
}, 2600);
"""
k = src.find('<body')
j = src.find('>', k) + 1
head = '<script>window.__OM3_APP__=1;window.__errs=[];window.onerror=function(m,s2,l){window.__errs.push(m+" @"+l)};' \
       'window.addEventListener("unhandledrejection",function(e){window.__errs.push("rej:"+e.reason)});</script>'
out = src[:j] + head + src[j:].replace('</body>', '<script>' + JS + '</script></body>', 1)
p = SRC + '\\app\\_probe_scene39.html'   # 必须放在 app/ 下：页面里的图是相对路径 images/
io.open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\omsc39'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new', '--disable-gpu',
                    '--no-first-run', '--hide-scrollbars', '--user-data-dir=' + ud, '--window-size=560,900',
                    '--virtual-time-budget=30000', '--dump-dom', 'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
if kk < 0:
    print('  [FAIL] 探针没拿到输出'); F += 1
else:
    body = dom[kk:].split('>', 1)[1].split('</pre>')[0]
    print(body)
    K += body.count('['); F += body.count('[FAIL]')
shutil.rmtree(d, ignore_errors=True)
print()
print('===== 结论：%s（%d 项，失败 %d）=====' % ('全部通过 ✅' if F == 0 else '有 %d 项失败 ❌' % F, K, F))
sys.exit(1 if F else 0)
