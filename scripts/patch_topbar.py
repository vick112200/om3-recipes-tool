# -*- coding: utf-8 -*-
"""① 顶栏重排：三个版本（原版/优化版/场景对比）合成一个开关；目录按钮挪到「导入相机」左边、只留图标
② OIS3 二维码按字段定位 SSID / 密码（用真机样本校准）
"""
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
P = TMP + r'\app\base.html'
h = open(P, encoding='utf-8').read()
open(TMP + r'\app\base.before_topbar.html', 'w', encoding='utf-8', newline='').write(h)

# ============================================================ 1. 顶栏结构
i = h.find('<span class="tabs ver">')
j = h.find('</span>', h.find('id="tabD"')) + 7
assert 0 < i < j
old = h[i:j]
assert 'tabD' in old and 'data-p="C"' in old
NEW = ('<span class="tabs ver">'
       '<button type="button" data-p="A" class="on">原版方案</button>'
       '<button type="button" data-p="B">优化版</button>'
       '<button type="button" data-p="C">场景对比</button>'
       '</span>'
       '<span class="tabs rest">'
       '<button id="tocbtn" class="iconbtn" type="button" title="目录 / 搜配方">🔍</button>'
       '<button type="button" data-p="D" id="tabD" style="display:none">导入相机</button>'
       '</span>')
h = h[:i] + NEW + h[j:]
print('顶栏：三个版本合成开关；目录按钮移到「导入相机」左边（图标）')

# ============================================================ 2. CSS
OLD_CSS = ".tabs.ver{background:#232323;border:1px solid #3a3a3a;border-radius:999px;padding:3px;gap:2px;margin-left:auto}\n.tabs.ver button{border:0;background:transparent;border-radius:999px;padding:6px 15px;font-weight:700;color:#9a9a9a}"
assert h.count(OLD_CSS) == 1
NEW_CSS = (".tabs.ver{background:#232323;border:1px solid #3a3a3a;border-radius:999px;padding:3px;gap:2px;margin-left:auto}\n"
           ".tabs.ver button{border:0;background:transparent;border-radius:999px;padding:6px 12px;font-weight:700;color:#9a9a9a;font-size:13px}\n"
           ".iconbtn{width:40px;height:36px;padding:0 !important;font-size:17px;line-height:1;display:inline-flex;align-items:center;justify-content:center}")
h = h.replace(OLD_CSS, NEW_CSS, 1)

# ============================================================ 3. 按钮文字：只留图标
for old_t, new_t in [("btn.textContent='\\u2630 \\u76ee\\u5f55 / \\u641c\\u914d\\u65b9'", "btn.textContent='\\ud83d\\udd0d'"),
                     ("btn.textContent='\\\\u2630 \\\\u76ee\\\\u5f55 / \\\\u641c\\\\u914d\\\\u65b9'", "btn.textContent='\\\\ud83d\\\\udd0d'"),
                     ("btn.textContent=o?'\\u2715 \\u5173\\u95ed':'\\u2630 \\u76ee\\u5f55 / \\u641c\\u914d\\u65b9'",
                      "btn.textContent=o?'\\u2715':'\\ud83d\\udd0d'"),
                     ("btn.textContent=o?'\\\\u2715 \\\\u5173\\\\u95ed':'\\\\u2630 \\\\u76ee\\\\u5f55 / \\\\u641c\\\\u914d\\\\u65b9'",
                      "btn.textContent=o?'\\\\u2715':'\\\\ud83d\\\\udd0d'")]:
    if old_t in h:
        h = h.replace(old_t, new_t, 1)
        print('按钮文字已改成图标:', old_t[:34])
n_text = h.count('目录 / 搜配方')
print('页面里还残留「目录 / 搜配方」字样次数:', n_text)

# ============================================================ 4. OIS3 字段定位
OLD_DEC = """    var all = out.conv.join(' ');
    var m = all.match(/OM[-_ ]?[0-9A-Za-z]{1,4}[-_][0-9A-Za-z]{3,}/i);
    if(m) out.ssid = m[0];
    m = /(\\d{8,12})/.exec(all.replace(/[^0-9A-Za-z]/g, ' '));
    if(m) out.pass = m[1];
    if(!out.ssid){
      var parts = all.split(/[\\s,;|]+/);
      for(var k=0;k<parts.length;k++){
        var p = parts[k];
        if(p.length >= 6 && /^[0-9A-Za-z_.-]+$/.test(p) && !/^\\d+$/.test(p)){ out.ssid = p; break; }
      }
    }
    return out;"""
assert h.count(OLD_DEC) == 1
NEW_DEC = """    /* 官方布局（OIS1 已确认）：字段里还原后，SSID 是带 OM- 的那一段，密码是另一段较长的 */
    var all = out.conv.join(' ');
    var cands = out.conv.filter(function (x) { return x.length >= 4; });
    var i2;
    for (i2 = 0; i2 < cands.length; i2++)                       /* SSID：优先 OM- 开头 */
      if (/^OM[-_ ]?\\d/i.test(cands[i2])) { out.ssid = cands[i2]; break; }
    if (!out.ssid)
      for (i2 = 0; i2 < cands.length; i2++)
        if (/^[0-9A-Za-z][0-9A-Za-z_.-]{5,}$/.test(cands[i2]) && !/^\\d+$/.test(cands[i2])) { out.ssid = cands[i2]; break; }
    for (i2 = 0; i2 < cands.length; i2++) {                     /* 密码：另一段，8 位以上 */
      var x = cands[i2];
      if (x === out.ssid) continue;
      if (/^[0-9A-Za-z]{8,}$/.test(x)) { out.pass = x; break; }
    }
    /* 通用兜底 */
    if (!out.ssid) {
      var m0 = all.match(/OM[-_ ]?[0-9A-Za-z]{1,4}[-_][0-9A-Za-z]{3,}/i);
      if (m0) out.ssid = m0[0];
    }
    if (!out.pass) {
      var m1 = /(\\d{8,})/.exec(all.replace(/[^0-9A-Za-z]/g, ' '));
      if (m1) out.pass = m1[1];
    }
    return out;"""
h = h.replace(OLD_DEC, NEW_DEC, 1)
print('OIS3 字段定位逻辑已更新')

open(P, 'w', encoding='utf-8', newline='').write(h)
print('完成，base.html %.1f KB' % (len(h.encode('utf-8')) / 1024))
