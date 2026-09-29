# -*- coding: utf-8 -*-
"""第 67 轮验收：连接链 5 处硬伤修好了 + 真机验证清单在位。

A. node 功能段：把页面里的**纯函数** `camWifiBleWait()` 原样抽出来跑：
   · 6 组边界（热点可见 / 蓝牙链跑完 / 用户停 / 超时 / 什么都没有 / **只有 BLEON**）
   · 再用它**模拟等待循环的时间线**：蓝牙 1 秒就连上、热点第 7 秒才起来 →
     必须等到第 7 秒（`hotspot`）才放行，**不能**在 1 秒就放行（第 67 轮修的就是这个）
B. 静态：旧条件（`BLEON ||` 当完成）已消失、按钮链会停掉自动重连、步骤编号 1/3→2/3→3/3 且没有 4/4、
   `_camHTTP` 的置真/置假点齐全、`cam-on` 的 SSID 判定没有被误标成"HTTP 通"、id 集合不变。
C. 规格里那份**真机验证清单**在位（场景 A..G + 日志导出说明）。

跑法：python scripts/dv_r67.py
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
PAGE = os.path.join(ROOT, 'app', 'base.html')
OLD = os.path.join(ROOT, 'app', 'base.before_r67.html')
SPEC = os.path.join(ROOT, 'SPEC-round67.md')
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


page = io.open(PAGE, encoding='utf-8').read()
old = io.open(OLD, encoding='utf-8').read()


def blk(t, marker):
    """从 marker 之后的第一个 '{' 起按大括号配平取一整块（也能取 `window.x = function(){…}`）。"""
    i = t.index(marker)
    i = t.index('{', i)
    d = 0
    for m in re.finditer(r'\{|\}', t[i:]):
        d += 1 if m.group(0) == '{' else -1
        if d == 0:
            return t[i:i + m.end()]
    raise AssertionError('取不到块: ' + marker)


def fn(t, name):
    """从 'function name(' 起取函数体。"""
    return blk(t, 'function ' + name + '(')


print('=== A. 功能：等蓝牙链的判定（node 喂样例 + 时间线模拟） ===')
js = page[page.index('function camWifiBleWait('):page.index('\n  function camWifiChain(')]
HARNESS = r'''
__JS__
function J(o){ return JSON.stringify(o); }
var out = [];
/* ① 6 组边界（bledone, stopped, hotspot, waited, limit） */
out.push(['边界', camWifiBleWait(false, false, true,  0,     10000),
                   camWifiBleWait(true,  false, false, 0,     10000),
                   camWifiBleWait(false, true,  false, 0,     10000),
                   camWifiBleWait(false, false, false, 10000, 10000),
                   camWifiBleWait(false, false, false, 500,   10000),
                   camWifiBleWait(false, true,  true,  0,     10000)]);
/* ② 时间线模拟：蓝牙 1 秒"连上"（BLEON=true，但**不是**完成条件）、热点第 7 秒才起来
      → 必须等到第 7 秒才放行；1~6 秒之间一直是"继续等" */
var tl = [];
var bleOn = false, done = false, hotspot = false;
for(var s = 0; s <= 12; s++){
  if(s >= 1) bleOn = true;         /* GATT 连上（老代码就是在这里放行的 —— 错的） */
  if(s >= 7) hotspot = true;       /* 相机热点真的起来了 */
  var why = camWifiBleWait(done, false, hotspot, s * 1000, 10000);
  tl.push(s + ':' + (why || '等'));
}
out.push(['时间线', tl.join(' ')]);
/* ③ 时间线2：蓝牙链 3 秒就自己跑完（done=true）→ 第 3 秒放行（不该傻等 10 秒） */
var tl2 = [];
for(var s2 = 0; s2 <= 5; s2++){
  var w2 = camWifiBleWait(s2 >= 3, false, false, s2 * 1000, 10000);
  tl2.push(s2 + ':' + (w2 || '等'));
}
out.push(['时间线2', tl2.join(' ')]);
/* ④ 时间线3：用户第 2 秒点了「停止自动连蓝牙」→ 立刻放行（别卡到 10 秒） */
var tl3 = [];
for(var s3 = 0; s3 <= 4; s3++){
  var w3 = camWifiBleWait(false, s3 >= 2, false, s3 * 1000, 10000);
  tl3.push(s3 + ':' + (w3 || '等'));
}
out.push(['时间线3', tl3.join(' ')]);
console.log(J(out));
'''
tmp = os.path.join(tempfile.gettempdir(), '_dv_r67.js')
io.open(tmp, 'w', encoding='utf-8').write(HARNESS.replace('__JS__', js))
try:
    r = subprocess.run(['node', tmp], capture_output=True, text=True, encoding='utf-8', timeout=60)
except FileNotFoundError:
    print('  （没装 node，跳过功能部分）')
    r = None
if r is not None:
    if r.returncode != 0:
        A(False, 'node 跑挂了：' + (r.stderr or '')[-400:])
    else:
        rows = dict((x[0], x[1:]) for x in json.loads(r.stdout.strip().splitlines()[-1]))
        o = rows['边界']
        A(o[0] == 'hotspot', '看到相机热点 → 立刻放行（hotspot）')
        A(o[1] == 'done', '蓝牙链自己跑完 → 放行（done，不用傻等 10 秒）')
        A(o[2] == 'stopped', '用户停了蓝牙链 → 放行（stopped）')
        A(o[3] == 'timeout', '等满上限 → 放行（timeout，并会说明"不等了"）')
        A(o[4] == '', '什么都没发生 → **继续等**（'' 空串）')
        A(o[5] == 'hotspot', '热点已可见时，优先级高于"用户停了"（先连上更实在）')
        tl = rows['时间线'][0]
        A('1:等' in tl and '6:等' in tl and '7:hotspot' in tl,
          '时间线：蓝牙第 1 秒就连上、热点第 7 秒才起来 → 1~6 秒都在等，第 7 秒才放行（%s）' % tl)
        A(':done' not in tl and ':stopped' not in tl, '时间线里没有提前放行')
        tl2 = rows['时间线2'][0]
        A('3:done' in tl2, '时间线2：蓝牙链第 3 秒跑完 → 第 3 秒就放行（%s）' % tl2)
        tl3 = rows['时间线3'][0]
        A('2:stopped' in tl3, '时间线3：用户第 2 秒停止 → 第 2 秒放行（%s）' % tl3)

print('=== B. 静态：5 处硬伤都改了、别处没被碰坏 ===')
chain = fn(page, 'camWifiChain')
A(page.count('function camWifiBleWait(') == 1 and chain.count('camWifiBleWait(') == 1,
  'camWifiBleWait 定义 1 次、在链里用了 1 次')
A('BLEON ||' not in chain and '!BLEON &&' not in chain,
  '① 链里**不再**把 BLEON 当完成条件（旧条件 `BLEON || _bleAutoDone…` 已消失）')
A('_autoWait = false; _autoRun = false;' in chain and '_autoT' in chain,
  '② 按钮链会先把「进页面自动连」的重试停掉')
A('第 1/3 步' in chain and '第 2/3 步' in chain and '第 3/3 步' in chain and '第 4/4 步' not in chain,
  '④ 步骤编号 1/3 → 2/3 → 3/3，且没有 4/4')
A('if(_camHTTP){' in chain and 'if(_camHTTP){                                  /* r67：只有真通才报成功 */' in page,
  '④ 看门狗只有 HTTP 真通才报 ✅')
A('看着已经挂在' in chain and '先「检测相机」确认一次' in chain,
  '③ 没确认 HTTP 前不说"已经连着了"，改说"先检测一次确认"')
A(page.count('var _camHTTP = false;') == 1 and page.count('function camHTTPok()') == 1
  and page.count('function camHTTPbad()') == 1, '_camHTTP 声明 + 两个置位函数各 1 次')
A(page.count('camHTTPok();') == 2,
  'camHTTPok() 的置真点恰好 2 处（检测相机成功 + 3 秒轮询成功；实为 %d）' % page.count('camHTTPok();'))
A(page.count('camHTTPbad();') == 5,
  'camHTTPbad() 的置假点恰好 5 处（lost/unavailable/denied + 轮询失败 + 断开 + 忘掉 + 不再是相机热点；实为 %d）'
  % page.count('camHTTPbad();'))
net = blk(page, 'window.__om3net = function')
A('camHTTPok' not in net,
  '③ 网络回调里**没有**把"SSID 像相机"误标成 HTTP 通（cam-on 的既有判定没被改）')
A('相机已经连着了（HTTP 通）' not in page, '⑤ 蓝牙链那句谎报"HTTP 通"的文案已消失')
A('_camHTTP ? ' in page, '⑤ 蓝牙链文案改成按事实（HTTP 已确认 / 按 SSID 判断）')
A('r67：连接链' in page, 'r67 标记块在（生成脚本幂等判据）')


def ids(t):
    return set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', t))


si, so = ids(page), ids(old)
# 第 68 轮起允许**新增** id（新增那一组由 dv_r68 按 SPEC-round68 §2.3 严格断言）。
# 这里钉"第 67 轮及以前的 id 一个都没少"——判据没放松，只是不再禁止后续轮次新增。
A(not (so - si), '第 67 轮及以前的 id 一个都没少（少的是：%s）' % (sorted(so - si) or '无'))
for x in ('camGateConn', 'camCheck', 'camDisconnect', 'camForgetSaved', 'camAutoStop', 'camHotspotVisible'):
    A(x in page, '这条链依赖的东西还在：%s' % x)

print('=== C. 真机验证清单在位（SPEC-round67 §3） ===')
spec = io.open(SPEC, encoding='utf-8').read()
A('## 3. 真机验证怎么做' in spec, '规格里有"真机验证怎么做"一节')
for s in 'ABCDEFG':
    A('| **%s** |' % s in spec, '场景 %s 在清单里' % s)
A('复制日志' in spec and '最小信息包' in spec, '写了怎么导出日志 / 最小信息包')
A('set_timeout' in spec, '顺手记了"防掉线（set_timeout）要等下一轮才试得了"')

print()
print('第 67 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
