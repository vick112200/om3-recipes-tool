# -*- coding: utf-8 -*-
"""第 64 轮：给「连接相机」加 **BSSID**（照官方 SSID+BSSID 精连那一个热点）。

为什么这么改（证据都在工程内，见 SPEC-round64.md §2）：
  · 官方 APK 连相机热点时用 `WifiNetworkSpecifier.Builder.setBssid(MacAddress.fromString(prefBSSID))`
    （official_app/dis.txt 16452c~164576），且**只在 SDK_INT > 30 时**设；
  · BSSID 的来源官方有两条：① 扫 `ScanResult.BSSID` ② 连上后 `onCapabilitiesChanged` 里读
    `WifiInfo.getBSSID()`（dis.txt 51570~51635）—— 两条我们都已经在做，只是没把 BSSID 用起来。

本脚本只改页面（Java 侧在 MainActivity.java 里直接改，见规格 §4）。规矩：
  · 幂等：写进页面的标记 `r64：BSSID` 作判据，重跑不重复改；
  · 每处锚点必须**命中恰好 1 次**，否则直接报错退出（不写盘）；
  · 只动这几个函数/调用点，不新增/不改任何 id。

用法：python scripts/gen_r64.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')

MARK = 'r64：BSSID'

# ---------------------------------------------------------------- 新增的公共函数块
HELPERS = '''  /* ================= r64：BSSID（照官方 SSID+BSSID 精连那一个热点） =================
     为什么：只给 SSID 时，系统可以在"所有叫这个名字的 AP"里挑（扫到过同名残留热点/邻居同名热点就会
     连错），连错了相机 HTTP（192.168.0.10）自然不通。官方连相机热点用的是 SSID **+ BSSID**
     （official_app/dis.txt 16452c~164576）。下面三个纯函数 + 一个连接入口是**唯一**的实现，
     页面里所有"连相机"都走它们。 */
  var BSSID_RE = /^[0-9A-F]{2}(:[0-9A-F]{2}){5}$/;
  /* 合法 BSSID 才返回大写形式，否则 ''。系统拿不到真值时会给 02:00:00:00:00:00 这类占位值 → 当没有。 */
  function camBssidOk(b){
    var s = String(b === null || b === undefined ? '' : b).trim().toUpperCase();
    if(!BSSID_RE.test(s)) return '';
    if(s === '00:00:00:00:00:00' || s === 'FF:FF:FF:FF:FF:FF' || s === '02:00:00:00:00:00') return '';
    return s;
  }
  /* 统一构造「记住的相机」记录（r64 起带 bssid）。
     keep = 现有记录：**SSID 相同时**才继承 机型/序列号/上次连接/BSSID（SSID 换了就不许继承 —— 沿用第 34 轮的规矩）；
     opt  = {bssid,model,serial,at} 需要覆盖的可选项（页面上刚扫到的 BSSID 比旧的准）。 */
  function camRec(ssid, pass, keep, opt){
    opt = opt || {};
    var same = !!(keep && keep.ssid && keep.ssid === ssid);
    var o = { ssid: ssid, pass: pass || '',
              model: opt.model || (same ? (keep.model || '') : ''),
              serial: opt.serial || (same ? (keep.serial || '') : ''),
              at: opt.at || (same ? (keep.at || '') : '') };
    var b = camBssidOk(opt.bssid) || (same ? camBssidOk(keep.bssid) : '');
    if(b) o.bssid = b;                       /* 不合法就不写这个字段（也不写空串） */
    return o;
  }
  /* 把"新学到/新扫到"的 BSSID 合进现有记录：返回新记录对象，或 null（= 不用改）。
     只在 SSID 对得上、BSSID 合法、且确实变了的时候才动 —— 绝不把已有值覆盖成空。 */
  function camBssidMerge(rec, ssid, bssid){
    var b = camBssidOk(bssid);
    if(!rec || !rec.ssid || !b) return null;
    if(String(ssid || '') !== String(rec.ssid)) return null;
    if(camBssidOk(rec.bssid) === b) return null;
    var o = {};
    for(var k in rec) if(Object.prototype.hasOwnProperty.call(rec, k)) o[k] = rec[k];
    o.bssid = b;
    return o;
  }
  /* 发起连接：有 BSSID 且原生支持就按 SSID+BSSID 精连，否则退回只按 SSID 连。
     返回 { r: 原生返回码（已去掉 @bssid 后缀）, via: 'ssid+bssid'|'ssid'|'bssid'|'none', bssid: 真正生效的 }。
     ⚠ via 认的是**原生回的 @bssid 后缀**（原生可能因为"安卓 11 及以下"而没用 BSSID）——
        不让页面替原生吹牛。 */
  function camConnectRaw(ssid, pass, bssid){
    if(!Native || !Native.connectCamera) return { r: 'unsupported', via: 'none', bssid: '' };
    var b = camBssidOk(bssid);
    var raw;
    if(b && Native.connectCamera2){
      try{ raw = String(Native.connectCamera2(ssid, pass, b) || ''); }
      catch(e){ return { r: 'error:' + e.message, via: 'bssid', bssid: b }; }
      var pinned = raw.indexOf('@bssid') >= 0;
      raw = raw.replace('@bssid', '');
      return { r: raw, via: pinned ? 'ssid+bssid' : 'ssid', bssid: pinned ? b : '' };
    }
    if(b) log('[连相机] 有 BSSID(' + b + ') 但这个版本的原生没有 connectCamera2 → 退回只按 SSID 连', 'warn');
    try{ raw = String(Native.connectCamera(ssid, pass) || ''); }
    catch(e){ return { r: 'error:' + e.message, via: 'ssid', bssid: '' }; }
    return { r: raw, via: 'ssid', bssid: '' };
  }
'''

# ---------------------------------------------------------------- 逐处替换
EDITS = []


def E(label, old, new):
    EDITS.append((label, old, new))


# ① 三个纯函数 + 连接入口（插在 camForget() 之后）
E('新增 BSSID 公共函数块',
  "  function camForget(){ try{ localStorage.removeItem(CKEY); }catch(e){ om3err(e, \"silent\"); } }\n"
  "  function renderSaved(){",
  "  function camForget(){ try{ localStorage.removeItem(CKEY); }catch(e){ om3err(e, \"silent\"); } }\n"
  + HELPERS +
  "  function renderSaved(){")

# ② 记住的相机那一行显示 BSSID
E('renderSaved 显示 BSSID',
  "    if(s && s.ssid){\n"
  "      el.innerHTML = '记住的相机：<b>' + esc(s.ssid) + '</b>' + (s.pass ? '（密码已存）' : '（没存密码）') +\n"
  "        (s.model ? '\u3000' + esc(s.model) : '') +\n"
  "        '\u3000<span style=\"color:#8fd8c2\">点这一行直接连 →</span>';",
  "    if(s && s.ssid){\n"
  "      var bs = camBssidOk(s.bssid);\n"
  "      el.innerHTML = '记住的相机：<b>' + esc(s.ssid) + '</b>' + (s.pass ? '（密码已存）' : '（没存密码）') +\n"
  "        (s.model ? '\u3000' + esc(s.model) : '') +\n"
  "        (bs ? '\u3000<span style=\"color:#9aa3b2;font-size:12px\">BSSID ' + esc(bs)\n"
  "              + '（记住它，连接时优先钉住这一个）</span>' : '') +\n"
  "        '\u3000<span style=\"color:#8fd8c2\">点这一行直接连 →</span>';")

# ③ 检测相机里"顺手记机型"那处 → 走 camRec（保住 bssid）
E('检测相机：改走 camRec',
  "            if(sv0 && sv0.ssid){ camSave({ ssid: sv0.ssid, pass: sv0.pass || '', model: md, serial: sv0.serial || '', at: sv0.at || '' }); renderSaved(); }",
  "            if(sv0 && sv0.ssid){ camSave(camRec(sv0.ssid, sv0.pass, sv0, {model: md})); renderSaved(); }   /* r64：统一构造（顺带保住 bssid） */")

# ④ 连不上→重填密码那处
E('重填密码：改走 camRec',
  "              try{ camSave({ ssid: s2.ssid, pass: pw, model: s2.model || '', serial: s2.serial || '' }); }catch(e){ om3err(e, \"silent\"); }",
  "              try{ camSave(camRec(s2.ssid, pw, s2)); }catch(e){ om3err(e, \"silent\"); }   /* r64：bssid 一起继承 */")

# ⑤ connectNow：camRec + camConnectRaw + 文案
E('connectNow：走 camConnectRaw',
  "    var keep = camSaved() || {};\n"
  "    camSave({ ssid: ssid, pass: pass, model: keep.model || '', serial: keep.serial || '', at: keep.at || '' });\n"
  "    renderSaved();\n"
  "    camOut('正在请系统连接 ' + ssid + ' …（如果弹窗，请点「连接」）');\n"
  "    var r = '';\n"
  "    try{ r = String(Native.connectCamera(ssid, pass)); }catch(e){ r = 'error:' + e.message; }",
  "    var keep = camSaved() || {};\n"
  "    camSave(camRec(ssid, pass, keep));                 /* r64：统一构造（保住已学的 bssid） */\n"
  "    renderSaved();\n"
  "    var cc = camConnectRaw(ssid, pass, keep.bssid);    /* r64：有 BSSID 就按 SSID+BSSID 精连 */\n"
  "    camOut('正在请系统连接 ' + ssid + (cc.bssid ? '（钉住 BSSID ' + cc.bssid + '）' : '') +\n"
  "           ' …（如果弹窗，请点「连接」）');\n"
  "    var r = cc.r;")

E('connectNow：asking 文案标明走哪条路',
  "    if(r === 'asking') camOut('等系统确认中…连上后这里会显示「已连上相机热点」。', 'ok');",
  "    if(r === 'asking') camOut('等系统确认中…连上后这里会显示「已连上相机热点」。'\n"
  "        + (cc.via === 'ssid+bssid' ? '（按 SSID+BSSID 精连）' : ''), 'ok');")

# ⑥ 扫码成功那处（原来会清掉机型/序列号）
E('扫码成功：改走 camRec',
  "    camSave({ ssid: p.ssid, pass: p.pass });",
  "    camSave(camRec(p.ssid, p.pass, camSaved()));   /* r64：统一构造（以前这里会清掉机型/序列号） */")

# ⑦ 直连：候选里优先挑"记住过 BSSID 的那一台"
E('直连：优先挑记住过 BSSID 的那台',
  "    var pick = cands[0];\n"
  "    var pass = (sv.ssid && sv.ssid === pick.ssid && sv.pass) ? sv.pass : '';",
  "    /* r64：优先挑\"记住过 BSSID 的那一个\"（同名热点/扫到残留时别连错）；挑不到就还是信号最强的那个 */\n"
  "    var svB = camBssidOk(sv.bssid);\n"
  "    var pick = cands[0];\n"
  "    if(svB){\n"
  "      for(var ci = 0; ci < cands.length; ci++){\n"
  "        if(camBssidOk(cands[ci].bssid) === svB){ pick = cands[ci]; break; }\n"
  "      }\n"
  "    }\n"
  "    var pass = (sv.ssid && sv.ssid === pick.ssid && sv.pass) ? sv.pass : '';\n"
  "    /* r64：把扫到的 BSSID 记下来（下次连接/挑热点都靠它） */\n"
  "    try{\n"
  "      var mergedB = camBssidMerge(camSaved(), pick.ssid, pick.bssid);\n"
  "      if(mergedB){ camSave(mergedB); renderSaved(); log('[直连] 记下 BSSID ' + mergedB.bssid, 'ok'); }\n"
  "    }catch(e){ om3err(e, \"silent\"); }")

# ⑧ 直连：go() 用 camConnectRaw（并修「asking 被当成失败」）
E('直连 go()：走 camConnectRaw',
  "    function go(pw){\n"
  "      say('连接 ' + pick.ssid + '…（系统可能弹一次\"加入网络\"）');\n"
  "      var r = '';\n"
  "      try{ r = String(window.OM3Native.connectCamera(pick.ssid, pw) || ''); }catch(e){ r = 'err:' + e.message; }\n"
  "      if(r === 'ok'){ say('已发起连接 —— 连上后这里会自动变成\"已连接：' + pick.ssid + '\"', 'ok'); toastMsg('正在连 ' + pick.ssid); }",
  "    function go(pw){\n"
  "      var cc = camConnectRaw(pick.ssid, pw, pick.bssid);      /* r64：扫到的 BSSID 一起带上 */\n"
  "      say('连接 ' + pick.ssid + (cc.bssid ? '（按 BSSID ' + cc.bssid + ' 钉住这一个）' : '') + '…（系统可能弹一次\"加入网络\"）');\n"
  "      var r = cc.r;\n"
  "      /* r64 顺手修：原生成功时回的是 'asking'（不是 'ok'）→ 原来这里会把成功显示成「连接失败：asking」 */\n"
  "      if(r === 'ok' || r === 'asking'){ say('已发起连接 —— 连上后这里会自动变成\"已连接：' + pick.ssid + '\"', 'ok'); toastMsg('正在连 ' + pick.ssid); }")

# ⑨ 直连：问完密码那处 camSave → camRec（带扫到的 BSSID）
E('直连：记住时带上 BSSID',
  "      var keep = camSaved() || {};\n"
  "      var same = !!(keep.ssid && keep.ssid === pick.ssid);\n"
  "      camSave({ ssid: pick.ssid, pass: pw,\n"
  "                model: same ? (keep.model || '') : '',\n"
  "                serial: same ? (keep.serial || '') : '',\n"
  "                at: same ? (keep.at || '') : '' });",
  "      var keep = camSaved() || {};\n"
  "      /* r64：统一构造 —— 机型/序列号/上次连接按老规矩继承，**BSSID 用刚扫到的**（比旧的准） */\n"
  "      camSave(camRec(pick.ssid, pw, keep, {bssid: pick.bssid}));")

# ⑩ 连上时把 BSSID 说出来 + 新增原生回调 __om3camBssid
E('__om3camState：连上时带 BSSID',
  "    if(state === 'connected'){ camOut('已连上相机热点。', 'ok'); st('camStCam', '相机：已连接', 'ok'); }",
  "    if(state === 'connected'){\n"
  "      var bs0 = camBssidOk((camSaved() || {}).bssid);\n"
  "      camOut('已连上相机热点。' + (bs0 ? '（BSSID ' + bs0 + '）' : ''), 'ok');\n"
  "      st('camStCam', '相机：已连接', 'ok');\n"
  "    }")

E('新增 window.__om3camBssid 回调',
  "    var so = $('camOut1');\n"
  "    if(state === 'connected'){ o1.innerHTML = ''; line(o1, '手机已连上相机热点，可以点「检测相机」。', 'ok'); }\n"
  "    else if(so && state === 'lost'){ /* 保留日志 */ }\n"
  "  };",
  "    var so = $('camOut1');\n"
  "    if(state === 'connected'){ o1.innerHTML = ''; line(o1, '手机已连上相机热点，可以点「检测相机」。', 'ok'); }\n"
  "    else if(so && state === 'lost'){ /* 保留日志 */ }\n"
  "  };\n"
  "  /* r64：原生连上之后回报\"实际连到哪个 AP\"（MainActivity.camNoteBssid）。只更新已记住的那一台。 */\n"
  "  window.__om3camBssid = function(ssid, bssid, src){\n"
  "    try{\n"
  "      var merged = camBssidMerge(camSaved(), ssid, bssid);\n"
  "      if(!merged) return;\n"
  "      camSave(merged); renderSaved();\n"
  "      log('[连相机] 学到 BSSID ' + merged.bssid + '（' + (src === 'cap' ? '连接后系统报告' : '扫描') + '）'\n"
  "          + ' —— 以后连接就钉住这一个热点，不会连到同名的别的 AP', 'ok');\n"
  "    }catch(e){ om3err(e, \"silent\"); }\n"
  "  };")

# ⑪「已连接」卡的信息行加 BSSID
E('camOnInfoFill 显示 BSSID',
  "    bits.push('热点：<b>' + esc(ssid || '已连上') + '</b>');\n"
  "    if(model) bits.push('机型：<b>' + esc(model) + '</b>');",
  "    bits.push('热点：<b>' + esc(ssid || '已连上') + '</b>');\n"
  "    var bs1 = camBssidOk((cs && cs.bssid) || (sv && sv.bssid) || '');   /* r64：连上后显示实际那个 AP */\n"
  "    if(bs1) bits.push('BSSID：' + esc(bs1));\n"
  "    if(model) bits.push('机型：<b>' + esc(model) + '</b>');")


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r64] 已经是目标状态（页面里有 "%s"）—— 不重复改。' % MARK)
        return 0

    bad = []
    for label, old, new in EDITS:
        n = html.count(old)
        if n != 1:
            bad.append('%s：锚点命中 %d 次（要求 1 次）' % (label, n))
    if bad:
        print('[r64] ✗ 以下锚点不匹配，页面可能已被改过 —— **不写盘**：')
        for b in bad:
            print('   · ' + b)
        return 1

    if '--check' in sys.argv:
        print('[r64] --check：%d 处锚点都命中 1 次，会做以下替换（未写盘）：' % len(EDITS))
        for label, old, new in EDITS:
            print('   · ' + label)
        return 0

    for label, old, new in EDITS:
        html = html.replace(old, new, 1)
    assert MARK in html, '替换后标记不在页面里'

    io.open(PAGE, 'w', encoding='utf-8', newline='').write(html)
    print('[r64] ✓ 已改 %d 处：BSSID 精连（scan 返回 bssid / connectCamera2 / camRec / camConnectRaw / 显示）' % len(EDITS))
    deltas = len(html.encode('utf-8')) - len(io.open(os.path.join(ROOT, 'app', 'base.before_r64.html'),
                                                     encoding='utf-8').read().encode('utf-8'))
    print('[r64] 页面净增 %d 字节' % deltas)
    return 0


if __name__ == '__main__':
    sys.exit(main())
