# -*- coding: utf-8 -*-
"""第 62 轮：用官方 App 逆向结论优化「连接相机」（4 项技术 + 布局/流程）。

规矩（照 AGENTS.md §2）：
  · 幂等：重跑不会重复插入 / 重复搬块（先看锚点在不在，已在就是"已是目标状态"）
  · 带断言：每个替换必须命中**恰好 1 次**，否则直接报错退出（绝不静默改坏）
  · 不重打内容：搬块只搬、包裹只包，块内一个字符都不改（id / 事件绑定全部保原样）

用法：
  python scripts/gen_r62.py            # 改 app/base.html
  python scripts/gen_r62.py --check    # 只报状态，不写文件
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')

M62 = '[r62]'


def die(msg):
    print('%s ✗ %s' % (M62, msg))
    sys.exit(1)


def sub1(html, old, new, what):
    """恰好替换 1 次（多/少都报错）。"""
    n = html.count(old)
    if n != 1:
        die('%s：锚点命中 %d 次（要求 1 次）—— 先看页面是不是已经被别的东西改过' % (what, n))
    return html.replace(old, new, 1)


TAG = re.compile(r'<(div|details)\b|</(div|details)>', re.I)


def span_end(html, start):
    """从块的开始 '<' 起，返回块结束位置（div/details 平衡扫描）。"""
    depth = 0
    for m in TAG.finditer(html, start):
        if m.group(1):
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return m.end()
    die('块没闭合（从 offset %d 起）' % start)


# ---------------------------------------------------------------- JS：新代码块
JS_BLOCK = r'''
  /* ================= r62：用官方 App 逆向结论补的三件事 =================
     依据 SPEC-round61.md §2.1/§2.2（都是"已确证"，不是猜）：
       · 相机状态包 = 8 字节，byte[5] 是标志位；位语义见 bleFlagText()
       · 开机帧 0x0F01 的前提 = 「蓝牙连接模式已置位」且「定位模式未置位」
       · 结果码两套表（连接监听 / 检测监听）互不通用
     ==================================================================== */
  var BLE_STAT = { at: 0, flags: -1, txt: '' };
  function bleFlagText(f){
    if(typeof f !== 'number' || f < 0) return '（还没收到状态包）';
    return 'ASIC电源' + ((f & 1) ? '✅' : '❌')
         + ' · 分享' + ((f & 2) ? '✅' : '❌')
         + ' · 配对' + ((f & 4) ? '✅' : '❌')
         + ' · 蓝牙连接模式' + ((f & 8) ? '✅' : '❌')
         + ' · 定位' + ((f & 32) ? '✅' : '❌');
  }
  window.__om3bleFlagText = bleFlagText;
  window.__om3bleStat = function(){ return BLE_STAT; };
  /* 把通知的十六进制按 TLV 拆（[长度][类型][数据…]）；type=0xFF 就是状态包。
     认出来就存进 BLE_STAT 并返回 true；返回 false = "这条不是状态包"（交给命令帧那条路）。 */
  function bleScanTlv(hex){
    var t = String(hex || '').trim();
    if(!t) return false;
    var p = t.split(/\s+/), b = [], i;
    for(i = 0; i < p.length; i++){
      if(!/^[0-9a-fA-F]{2}$/.test(p[i])) return false;
      b.push(parseInt(p[i], 16));
    }
    i = 0;
    while(i + 1 < b.length){
      var len = b[i], ty = b[i + 1];
      if(len < 2 || (i + len) > b.length) break;
      if(ty === 0xFF && (len - 2) >= 6){
        var f = b[i + 7] & 0xFF;                     /* 数据区第 6 个字节 = 标志位（数据区从 i+2 起） */
        BLE_STAT.at = Date.now(); BLE_STAT.flags = f; BLE_STAT.txt = bleFlagText(f);
        bleRec('相机状态包：' + BLE_STAT.txt + '　（标志位 0x' + bleByte2(f) + '）', 'ok');
        return true;
      }
      i += len;
    }
    return false;
  }
  window.__om3bleScanTlv = bleScanTlv;
  /* 开机前提：返回 '' = 可以发开机帧；返回字符串 = 不能发的原因。
     没收到状态包 / 状态超过 30 秒 → ''（按老路照发，不因为"不知道"就拦住用户）。 */
  function blePowerOnBlock(){
    if(BLE_STAT.flags < 0 || (Date.now() - BLE_STAT.at) > 30000) return '';
    var f = BLE_STAT.flags;
    if(!(f & 8))
      return '相机没有处在「蓝牙连接模式」（官方在这种状态下根本不会执行开机帧）。'
           + '到相机上：MENU → Wi-Fi/蓝牙 → 连接到智能手机，让相机进入蓝牙连接状态再来。';
    if(f & 32)
      return '相机正在「定位记录」中（官方在这种状态下根本不会执行开机帧）。先在相机上停止定位记录再来。';
    return '';
  }
  window.__om3blePowerOnBlock = blePowerOnBlock;
  /* 结果码两套表（互不通用！第 59/60 轮从官方监听器的 packed-switch 读出，见 SPEC-round60/61） */
  var BLE_CODE_CONN = {0:'SUCCESS（成功）', 1:'ALREADY_CONNECTED（已经连过了）', 2:'NOT_FOUND（没找到相机）',
    3:'DISCONNECTED（连接断了）', 4:'NOT_FOUND（没找到相机）', 5:'SEARCHING（正在搜索）', 6:'CONNECTING（正在连接）',
    33:'BLUETOOTH_OFFON（手机蓝牙被关了）', 34:'PASSCODE_ERROR（蓝牙口令错）', 35:'POWON_ERROR（开机失败）',
    36:'FINALIZE（这一轮结束）'};
  var BLE_CODE_DETECT = {0:'検索成功（找到相机了）', 1:'既に接続済み（已经连过了）', 2:'NOT_FOUND（没找到）',
    5:'検索中（正在搜索）', 36:'FINALIZE（结束）',
    128:'ABNORMAL_CONDITION（蓝牙/定位不可用这类异常状态）'};
  function bleCodeText(kind, code){
    var n = parseInt(code, 10);
    var tab = (String(kind) === 'detect') ? BLE_CODE_DETECT : BLE_CODE_CONN;
    return Object.prototype.hasOwnProperty.call(tab, n) ? tab[n] : ('认不出的码（' + n + '）');
  }
  window.__om3bleCodeText = bleCodeText;
  window.__om3bleCodeAll = function(code){
    var n = parseInt(code, 10);
    if(isNaN(n)) return;
    bleRec('结果码 ' + n + '：连接监听 = ' + bleCodeText('conn', n) + '　／　检测监听 = ' + bleCodeText('detect', n), 'ok');
    bleRec('　（两套表不通用：同一个数字在两个回调里含义可能不同 —— 见 SPEC-round60 §2.1）', 'quiet');
  };
  /* r62：诊断面板加一个「结果码对照」按钮（避免"两套表"被当成 bug 来回试） */
  (function(){
    var b = document.getElementById('bleCodeBtn');
    if(!b) return;
    b.addEventListener('click', function(){
      var v = window.prompt('输入相机回的码（十进制）：', '34');
      if(v === null || String(v).trim() === '') return;
      window.__om3bleCodeAll(String(v).trim());
    });
  })();
'''


def main():
    check_only = ('--check' in sys.argv)
    html = io.open(PAGE, encoding='utf-8').read()
    orig_len = len(html)

    # 幂等判据：用**写进页面里**的锚点，而不是脚本自己的打印标记。
    # （第一次跑的时候就是漏了这条 → 重跑会在"布局②"上误报锚点 0 次；
    #   实际上页面没被写坏，只是幂等判据失效。这里修掉。）
    MARK = 'r62：用官方 App 逆向结论补的三件事'
    if MARK in html:
        print('%s 已经是目标状态（页面里已有 r62 标记块）—— 不重复改。' % M62)
        return 0

    # ---------------------------------------------------------- 技术项 ①：字段表精确取
    old_fn_start = '  function om3DecodeQr(raw){'
    i = html.find(old_fn_start)
    if i < 0:
        die('找不到 om3DecodeQr()')
    j = html.find('\n  window.__om3qrConv = qrConv;', i)
    if j < 0:
        die('找不到 om3DecodeQr() 的结尾（window.__om3qrConv 那行）')
    NEW_FN = '''  /* r62：按官方 APK **确证的字段位序**精确取（不再靠"哪段像 SSID"猜）
     来源 SPEC-round61.md §2.2（oishare.f.c/d/e 的段位序 + J2/d、DeviceWifiActivity$k.j 的 prefs 对照）：
       OIS1（3 段）        ：段1 = b(SSID系)            段2 = f(Wi-Fi 密码)              版本号固定 1
       OIS2（4 或 6 段）   ：段1 = 版本号  段2 = b      段3 = f      版本 3 时 段4 = i(BLE名) 段5 = j(配对码)
       OIS3（5 或 7 段）   ：段1 = 版本号  段2 = a(安全类型)  段3 = b  段4 = f  版本 3 时 段5 = i 段6 = j
       b 是复合串：按 "-P-" 拆 → 后半 = SSID，前半 = 相机名（官方把 b 拆成 PairingCameraName + PairingCameraSsid）
     取不全时**保留原来的启发式兜底**（不倒退）。 */
  function om3DecodeQr(raw){
    var out = {ver:'', verNum:0, conv:[], name:'', ssid:'', pass:'', bleName:'', blePass:'', secType:0, pick:'', raw:String(raw||'')};
    var f = String(raw||'').split(',', 7);
    if(f.length < 2 || !/^OIS\\d$/i.test(f[0])) return out;
    out.ver = f[0].toUpperCase();
    /* ⚠ 官方是**先 parseInt 再置换**：版本号 / 安全类型是**明文数字**，不过置换表；
       只有 b/f/i/j 这些字符串字段要过。这里必须保留原始段（raw）。 */
    var raw = f.slice(1);
    for(var i=1;i<f.length;i++) out.conv.push(qrConv(f[i]));
    var g = function(n){ return (n < out.conv.length) ? String(out.conv[n]) : ''; };
    var gr = function(n){ return (n < raw.length) ? String(raw[n]) : ''; };
    var v3 = false, bField = '', fField = '', iField = '', jField = '', aField = '';
    if(out.ver === 'OIS1'){
      out.verNum = 1; bField = g(0); fField = g(1);
      out.pick = 'OIS1 字段表：段1 = SSID 系(b)、段2 = 密码';
    } else if(out.ver === 'OIS2'){
      out.verNum = parseInt(gr(0), 10) || 0; v3 = (out.verNum === 3);
      bField = g(1); fField = g(2);
      if(v3){ iField = g(3); jField = g(4); }
      out.pick = 'OIS2 字段表：版本 ' + out.verNum + ' → 段2 = b、段3 = 密码' + (v3 ? '、段4 = 蓝牙名、段5 = 蓝牙口令' : '');
    } else {
      out.verNum = parseInt(gr(0), 10) || 0; v3 = (out.verNum === 3);
      aField = gr(1); bField = g(2); fField = g(3);
      if(v3){ iField = g(4); jField = g(5); }
      out.secType = parseInt(aField, 10) || 0;
      out.pick = 'OIS3 字段表：版本 ' + out.verNum + ' → 段2 = 安全类型、段3 = b、段4 = 密码' + (v3 ? '、段5 = 蓝牙名、段6 = 蓝牙口令' : '');
    }
    bField = String(bField || '');
    if(bField){
      var pp = bField.split('-P-');
      if(pp.length >= 2){ out.name = pp[0]; out.ssid = pp[pp.length - 1]; }
      else {
        var sg = bField.split('-');
        if(sg.length >= 2){ out.name = sg.slice(0, sg.length - 1).join('-'); out.ssid = sg[sg.length - 1]; }
        else out.ssid = bField;
      }
    }
    if(fField) out.pass = fField;
    if(iField) out.bleName = iField;
    if(jField) out.blePass = jField;
    if(!out.ssid || !out.pass){
      var all = out.conv.join(' ');
      var cands = out.conv.filter(function (x) { return x.length >= 4; });
      var i2;
      if (!out.ssid)
        for (i2 = 0; i2 < cands.length; i2++)
          if (/^OM[-_ ]?\\d/i.test(cands[i2])) { out.ssid = cands[i2]; break; }
      if (!out.ssid)
        for (i2 = 0; i2 < cands.length; i2++)
          if (/^[0-9A-Za-z][0-9A-Za-z_.-]{5,}$/.test(cands[i2]) && !/^\\d+$/.test(cands[i2])) { out.ssid = cands[i2]; break; }
      if (!out.pass)
        for (i2 = 0; i2 < cands.length; i2++) {
          var x = cands[i2];
          if (x === out.ssid || x === out.name) continue;
          if (/^[0-9A-Za-z]{8,}$/.test(x)) { out.pass = x; break; }
        }
      if (!out.ssid) { var m0 = all.match(/OM[-_ ]?[0-9A-Za-z]{1,4}[-_][0-9A-Za-z]{3,}/i); if (m0) out.ssid = m0[0]; }
      if (!out.pass) { var m1 = /(\\d{8,})/.exec(all.replace(/[^0-9A-Za-z]/g, ' ')); if (m1) out.pass = m1[1]; }
      out.pick = (out.pick || '') + '（字段表没取全 → 已用启发式兜底）';
    }
    return out;
  }'''
    html = html[:i] + NEW_FN + html[j:]
    print('%s ✓ ① om3DecodeQr 换成官方字段表（OIS1/2/3 段位序 + "-P-" 拆 SSID）' % M62)

    # ---------------------------------------------------------- 技术项 ②：扫码自动填蓝牙口令
    anchor2 = """    var q = om3DecodeQr(text);
    if(q.ver){
      line(host, '识别为官方二维码：' + q.ver, 'ok');
      for(var ci=0; ci<q.conv.length; ci++) line(host, '　字段 ' + (ci+1) + ' 还原后：' + q.conv[ci]);
    }
"""
    add2 = anchor2 + """    /* r62：把"凭什么断定这段是 SSID"写进诊断；并自动填蓝牙口令（官方二维码版本 3 里带着） */
    if(q.ver && q.pick) line(host, '判定依据：' + q.pick, 'ok');
    if(q.name) line(host, '　相机名（b 里 "-P-" 前半）：' + q.name);
    if(q.ssid) line(host, '　SSID（b 里 "-P-" 后半）：' + q.ssid, 'ok');
    if(q.blePass){
      line(host, '　二维码里带的蓝牙口令：' + q.blePass + '（版本 ' + q.verNum + ' 的才带）', 'ok');
      try{ localStorage.setItem('om3blename', String(q.bleName || '')); }catch(e){ om3err(e, "silent"); }
      var _cur = blePassGet(), _bp = document.getElementById('blePassIn');
      if(_cur && _cur !== q.blePass){
        line(host, '　你之前手填过口令（' + _cur + '）→ 不覆盖。想用二维码里那串：点「清除口令」再扫一次。', 'warn');
      } else {
        blePassSet(q.blePass);
        if(_bp) _bp.value = q.blePass;
        line(host, '　已自动填进「相机蓝牙口令」—— 蓝牙唤醒不用再手抄了。', 'ok');
      }
    } else if(q.ver && q.verNum && q.verNum !== 3){
      line(host, '　（这个二维码版本 ' + q.verNum + ' 不带蓝牙口令；口令只在相机屏幕蓝牙配对时显示）', 'warn');
    }
"""
    html = sub1(html, anchor2, add2, '② onScan 自动填蓝牙口令')

    # ---------------------------------------------------------- 技术项 ③：状态包解析 + 开机前提
    anchor3 = '  var BLE_AUTO_CAM_MS = 8000;'
    html = sub1(html, anchor3, JS_BLOCK + '\n' + anchor3, '③ 插入 r62 状态包/码表 JS 块')

    anchor3b = """        try{
          var dec = bleDecodeFrame(hx);"""
    add3b = """        try{ bleScanTlv(hx); }catch(e4){ om3err(e4, "ble-stat"); }   /* r62：先看是不是相机状态包 */
        try{
          var dec = bleDecodeFrame(hx);"""
    html = sub1(html, anchor3b, add3b, '③b notify 分支接状态包解析')

    anchor3c = """    bleRec('开始蓝牙唤醒（先发官方的「電源ON」，等相机应答；没成再试「リモコンモード」）…');
    bleAutoWake();"""
    add3c = """    /* r62：开机前提检查（SPEC-round61 §2.1）——
       官方只在「蓝牙连接模式已置位」且「定位模式未置位」时才发开机帧；不满足就不发，并说清原因。 */
    var _blk = blePowerOnBlock();
    if(_blk){
      bleRec('⚠ 先不发开机帧：' + _blk, 'warn');
      bleRec('　（相机状态：' + BLE_STAT.txt + '）想强行试，就在下面「发一帧」里手动发 0F 01 01 02。', 'warn');
      toastMsg('相机当前状态不该发开机帧（原因见日志）');
      return;
    }
    bleRec('开始蓝牙唤醒（先发官方的「電源ON」，等相机应答；没成再试「リモコンモード」）…');
    bleAutoWake();"""
    html = sub1(html, anchor3c, add3c, '③c bleWakeCamera 加开机前提检查')

    # ---------------------------------------------------------- 技术项 ④：单字节 payload 附"若是结果码"
    anchor4 = """    return s;
  }
  /* 发完帧等相机应答："""
    add4 = """    /* r62：payload 只有 1 字节时，顺手附一行"若是结果码"的推测。
       ⚠ 码在帧里的位置**还没确证**（SPEC-round62 §3.4），所以标明【推测】，不当结论用。 */
    if(bodyLen === 1){
      s += '　（若是结果码：' + bleCodeText('conn', b[6]) + ' ／ 检测监听：' + bleCodeText('detect', b[6]) + '）【推测】';
    }
    return s;
  }
  /* 发完帧等相机应答："""
    html = sub1(html, anchor4, add4, '④ bleDecodeFrame 附结果码推测行')

    # ---------------------------------------------------------- 布局 ①：状态胶囊 → 一行
    anchorL1 = """    <span id="camStWifi" class="cs">Wi-Fi：读取中…</span>
    <span id="camStCam" class="cs">相机：未检测</span>
    <span id="camStBak" class="cs">备份：无</span>"""
    addL1 = """    <div class="camstats">
    <span id="camStWifi" class="cs">Wi-Fi：读取中…</span>
    <span id="camStCam" class="cs">相机：未检测</span>
    <span id="camStBak" class="cs">备份：无</span>
    </div>"""
    html = sub1(html, anchorL1, addL1, '布局① 状态胶囊包一行容器')

    # ---------------------------------------------------------- 布局 ②：蓝牙卡加"结果码对照"按钮
    anchorL2 = """    <div class="camout" id="camLinkOut2"></div>
  </div>

"""
    addL2 = """    <!-- r62：结果码两套表不通用，给一个能查的地方（第 59/60 轮从官方监听器读出） -->
    <button type="button" id="bleCodeBtn" class="gho" style="margin-top:6px">结果码对照（输个码看中文）</button>
    <div class="camout" id="camLinkOut2"></div>
  </div>

"""
    html = sub1(html, anchorL2, addL2, '布局② 蓝牙卡加结果码对照按钮')

    # ---------------------------------------------------------- 布局 ③：蓝牙卡搬进折叠、挪到连接详情之后
    card_start = html.find('<div class="camcard" id="camLinkCard"')
    if card_start < 0:
        die('找不到 #camLinkCard')
    card_end = span_end(html, card_start)
    card = html[card_start:card_end]
    html = html[:card_start] + html[card_end:]

    v1_start = html.find('<details class="fold fnote" id="camV1Fold">')
    if v1_start < 0:
        die('找不到 #camV1Fold')
    v1_end = span_end(html, v1_start)

    wrapped = ('  <details class="fold cfold" id="camLinkFold">\n'
               '    <summary>蓝牙唤醒（相机 Wi-Fi 没开时用这个）</summary>\n'
               '    <div class="foldbody">\n' + card + '\n    </div>\n  </details>\n')
    html = html[:v1_end] + '\n' + wrapped + html[v1_end:]
    print('%s ✓ 布局③ #camLinkCard 已包进 #camLinkFold 并挪到 #camV1Fold 之后' % M62)

    # ---------------------------------------------------------- 布局样式
    anchorCss = '.barABC,.barD{display:none;'
    addCss = ('.camstats{display:flex;flex-wrap:wrap;gap:6px;align-items:center}\n'
              '.cfold{margin-top:10px}\n'
              + anchorCss)
    html = sub1(html, anchorCss, addCss, '布局④ 加 .camstats/.cfold 样式')

    if check_only:
        print('%s --check：以上都会做（未写盘）' % M62)
        return 0

    io.open(PAGE, 'w', encoding='utf-8', newline='').write(html)
    print('%s 已写 %s（%d → %d 字节）' % (M62, PAGE, orig_len, len(html)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
