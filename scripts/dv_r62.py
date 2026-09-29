# -*- coding: utf-8 -*-
"""第 62 轮验收：连接相机优化（4 项技术 + 布局/流程）。

两部分：
  A. 静态结构：id 一个不少、蓝牙卡搬进折叠并挪到连接详情之后、状态胶囊成一行、新按钮/样式在
  B. 功能：把页面里的 `qrConv` / `om3DecodeQr` / `bleFlagText` / `bleCodeText` / `bleScanTlv` /
     `blePowerOnBlock` **原样抽出来**，在 node 里喂构造样例，断言字段位序/位语义/码表两套不串

跑法：python scripts/dv_r62.py
"""
import io
import os
import re
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'D:\workspace\om3-handbook'
F = K = 0


def A(c, msg):
    global F, K
    K += 1
    print(('  [OK ] ' if c else '  [FAIL] ') + msg)
    if not c:
        F += 1


src = io.open(os.path.join(ROOT, 'app', 'base.html'), encoding='utf-8').read()
OLD = io.open(os.path.join(ROOT, 'app', 'base.before_r62.html'), encoding='utf-8').read()


def ids(t):
    return set(re.findall(r'\bid="([A-Za-z0-9_-]+)"', t))


def block(t, start_marker):
    """按 div/details 平衡取块（从 start_marker 所在的 '<' 起）。"""
    i = t.index(start_marker)
    i = t.rindex('<', 0, i)
    depth = 0
    for m in re.finditer(r'<(div|details)\b|</(div|details)>', t[i:], re.I):
        depth += 1 if m.group(1) else -1
        if depth == 0:
            return t[i:i + m.end()]
    raise AssertionError('块没闭合: ' + start_marker)


print('=== A. 静态结构 ===')
st, so = ids(src), ids(OLD)
missing = sorted(so - st)
A(not missing, '原有 id 一个都没少（少的是：%s）' % (missing if missing else '无'))
A('camLinkCard' in src and 'id="camLinkFold"' in src, '#camLinkCard / #camLinkFold 都在')

fold = block(src, 'id="camLinkFold"')
A(fold.startswith('<details') and 'class="fold cfold"' in fold.split('>')[0] + '>',
  '#camLinkFold 是 <details class="fold cfold">')
A('open' not in re.search(r'<details[^>]*id="camLinkFold"', src).group(0),
  '#camLinkFold 默认收起（没有 open）')
A('id="camLinkCard"' in fold, '#camLinkCard 被包进 #camLinkFold')
for x in ('camLinkWake', 'blePassIn', 'blePassSave', 'blePassClear', 'camLinkRecheck',
          'camLinkStop', 'camLinkBtSet', 'camLinkOut', 'camLinkOut2', 'bleCodeBtn'):
    A(x in fold, '蓝牙卡的 id 仍在折叠里：%s' % x)

A(src.index('id="camLinkFold"') > src.index('id="camV1Fold"'), '#camLinkFold 排在 #camV1Fold 之后')
wrapped = block(src, 'class="camstats"')
for x in ('camStWifi', 'camStCam', 'camStBak'):
    A(x in wrapped, '状态胶囊在同一行容器里：%s' % x)
A('.camstats{display:flex' in src, '.camstats 样式在（一行显示）')
A('id="bleCodeBtn"' in src, '结果码对照按钮在')
A(src.count('id="bleCodeBtn"') == 1, '结果码对照按钮只有 1 个（没重复插）')
A('r62：用官方 App 逆向结论补的三件事' in src, 'r62 标记块在（生成脚本幂等判据）')

print('=== B. 功能（把页面函数抽出来在 node 里跑）===')


def pick(t, start, end):
    i = t.index(start)
    j = t.index(end, i)
    return t[i:j]


js = []
js.append(pick(src, 'var QRMAP = {', 'function qrConv'))
js.append(pick(src, 'function qrConv(s){', 'function om3DecodeQr'))
# 口径修正（第 91 轮）：bleScanTlv 现在调 bleBytes()（认连写十六进制）→ 抽函数时把它一起带上
js.append(pick(src, 'function bleBytes(hex){', 'window.__om3bleBytes'))
js.append(pick(src, 'function bleScanTlv(hex){', 'window.__om3bleScanTlv'))
js.append(pick(src, 'function blePowerOnBlock(){', 'window.__om3blePowerOnBlock'))
js.append(pick(src, 'function om3DecodeQr(raw){', '\n  window.__om3qrConv'))
js.append(pick(src, 'var BLE_CODE_CONN = {', 'function bleCodeText'))
js.append(pick(src, 'function bleCodeText(kind, code){', 'window.__om3bleCodeText'))
js.append(pick(src, 'function bleFlagText(f){', 'window.__om3bleFlagText'))
js.append(pick(src, 'var BLE_STAT = {', 'window.__om3bleFlagText'))

HARNESS = r'''
/* stubs */
function bleRec(){} function bleByte2(n){ var h=(n&255).toString(16).toUpperCase(); return h.length<2?('0'+h):h; }
function om3err(){}
__JS__
function J(o){ return JSON.stringify(o); }
var out = [];
/* ① OIS1：段1 = b（"-P-" 前半=相机名 / 后半=SSID），段2 = 密码 */
var q1 = om3DecodeQr('OIS1,' + qrConv('OM-1-P-12345678') + ',' + qrConv('87654321'));
out.push(['OIS1', q1.ver, q1.verNum, q1.name, q1.ssid, q1.pass, q1.blePass, q1.pick.indexOf('OIS1 字段表') >= 0]);
/* ② OIS2 版本 3（6 段）：段4 = 蓝牙名、段5 = 蓝牙口令 */
var q2 = om3DecodeQr(['OIS2', '3', qrConv('OM-5-P-ABCD1234'), qrConv('PW99887766'),
                      qrConv('OM5-BLE'), qrConv('135790')].join(','));
out.push(['OIS2v3', q2.ver, q2.verNum, q2.name, q2.ssid, q2.pass, q2.bleName + '/' + q2.blePass,
          q2.pick.indexOf('版本 3') >= 0]);
/* ③ OIS2 版本 1（4 段）：不该有蓝牙口令 */
var q3 = om3DecodeQr(['OIS2', '1', qrConv('OM-5-P-ABCD1234'), qrConv('PW99887766')].join(','));
out.push(['OIS2v1', q3.ver, q3.verNum, q3.name, q3.ssid, q3.pass, q3.blePass, q3.secType]);
/* ④ OIS3 版本 3（7 段）：段2 = 安全类型 */
var q4 = om3DecodeQr(['OIS3', '3', '4', qrConv('OM-3-P-ZZZZ9999'), qrConv('PW11223344'),
                      qrConv('OM3-BLE'), qrConv('246810')].join(','));
out.push(['OIS3v3', q4.ver, q4.verNum, q4.name, q4.ssid, q4.pass, q4.bleName + '/' + q4.blePass, q4.secType]);
/* ⑤ 非 OIS 文本：不认，不能抛 */
var q5 = om3DecodeQr('WIFI:S:MyAP;P:12345678;;');
out.push(['非OIS', q5.ver, q5.ssid, q5.pass]);
/* ⑥ 位语义 + 开机前提 */
function mkTLV(flags){
  var pay = [0x04, 0xD0, 0x01, 0x00, 0x00, flags];           // 6 字节数据区，byte[5] = flags
  var tlv = [pay.length + 2, 0xFF].concat(pay);
  return tlv.map(function(x){ return bleByte2(x); }).join(' ');
}
out.push(['标志位0x08', bleFlagText(8), bleScanTlv(mkTLV(8)), blePowerOnBlock()]);
out.push(['标志位0x28', bleFlagText(0x28), bleScanTlv(mkTLV(0x28)), blePowerOnBlock().length > 0]);
out.push(['标志位0x21', bleFlagText(0x21), bleScanTlv(mkTLV(0x21)), blePowerOnBlock().length > 0]);
/* ⑦ 码表：两套不串 */
out.push(['码34', bleCodeText('conn', 34), bleCodeText('detect', 34)]);
out.push(['码128', bleCodeText('conn', 128), bleCodeText('detect', 128)]);
out.push(['码0', bleCodeText('conn', 0), bleCodeText('detect', 0)]);
out.push(['码99', bleCodeText('conn', 99)]);
console.log(J(out));
'''

harness = HARNESS.replace('__JS__', '\n'.join(js))
tmp = os.path.join(tempfile.gettempdir(), '_dv_r62.js')
io.open(tmp, 'w', encoding='utf-8').write(harness)
try:
    r = subprocess.run(['node', tmp], capture_output=True, text=True, encoding='utf-8')
except FileNotFoundError:
    print('  （没装 node，跳过功能部分）')
    r = None
if r is not None:
    if r.returncode != 0:
        A(False, 'node 跑挂了：' + (r.stderr or '')[-500:])
    else:
        import json
        rows = dict((x[0], x[1:]) for x in json.loads(r.stdout.strip().splitlines()[-1]))
        o = rows['OIS1']
        A(o[0] == 'OIS1' and o[1] == 1, 'OIS1 版本号 = 1')
        A(o[2] == 'OM-1' and o[3] == '12345678', 'OIS1：-P- 前半=相机名(%s)、后半=SSID(%s)' % (o[2], o[3]))
        A(o[4] == '87654321', 'OIS1：段2 = 密码(%s)' % o[4])
        A(o[5] == '' and o[6], 'OIS1：没有蓝牙口令（版本1）')
        o = rows['OIS2v3']
        A(o[1] == 3 and o[2] == 'OM-5' and o[3] == 'ABCD1234' and o[4] == 'PW99887766',
          'OIS2v3：版本/名/SSID/密码 = %s/%s/%s/%s' % (o[1], o[2], o[3], o[4]))
        A(o[5] == 'OM5-BLE/135790', 'OIS2v3：段4=蓝牙名、段5=口令 → %s' % o[5])
        o = rows['OIS2v1']
        A(o[1] == 1 and o[4] == 'PW99887766' and o[5] == '', 'OIS2v1：无蓝牙口令，密码仍取到')
        o = rows['OIS3v3']
        A(o[1] == 3 and o[6] == 4, 'OIS3v3：段2 = 安全类型(%s)' % o[6])
        A(o[2] == 'OM-3' and o[3] == 'ZZZZ9999' and o[4] == 'PW11223344' and o[5] == 'OM3-BLE/246810',
          'OIS3v3：名/SSID/密码/蓝牙名+口令都对')
        o = rows['非OIS']
        A(o[0] == '', '非 OIS 文本不认（ver 为空）也不抛')
        o = rows['标志位0x08']
        A('蓝牙连接模式✅' in o[0] and '定位❌' in o[0], '0x08 → 蓝牙连接模式✅/定位❌')
        A(o[1] is True and o[2] == '', '0x08 → 认状态包，且**允许**发开机帧')
        o = rows['标志位0x28']
        A(o[1] is True and o[2] is True, '0x28（定位✅）→ 拦住开机帧并给原因')
        o = rows['标志位0x21']
        A(o[2] is True, '0x21（蓝牙连接模式❌）→ 也拦住')
        A(rows['码34'][0].startswith('PASSCODE_ERROR') and '认不出' in rows['码34'][1],
          '34：连接监听=口令错；检测监听=认不出（两套不串）')
        A('ABNORMAL' in rows['码128'][1] and '认不出' in rows['码128'][0],
          '128：只在检测监听里有（ABNORMAL_CONDITION）')
        A(rows['码0'][0].startswith('SUCCESS') and '検索成功' in rows['码0'][1],
          '0：两套都算成功，但文案各自不同')
        A('认不出' in rows['码99'][0], '认不出的码给"认不出"而不是瞎编')

print()
print('第 62 轮探针：%d/%d 通过%s' % (K - F, K, '' if F == 0 else '  ← 有 %d 条没过' % F))
sys.exit(1 if F else 0)
