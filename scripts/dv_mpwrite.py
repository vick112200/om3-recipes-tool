# -*- coding: utf-8 -*-
"""「我的配方 → 写入相机」实测（不接真相机）：假 XMLHttpRequest 顶替相机 HTTP。

用户 2026-09-23 反馈的三件事，逐条验：
  ① 没连相机也能点写入、要等很久才报错 → **必须秒回**，且**一个请求都不发**、相机毫不知情
  ② 点写入后小字一直停在"初始化/准备中" → 必须一路更新进度
  ③ 相机重启前读回还是旧值（正常现象）→ **不能**报失败（曾经假报过 ❌）

2026-09-24 追加（HANDOVER §2 写入收尾）：
  ④ 槽位**没有 raw**（官方 .oes 导入 / 新的紧凑分享格式故意不存 raw）也要能写进去
  ⑤ 槽位只有 raw、没有影调字段（老数据/半成品数据）→ 影调要从 raw 解出来，不能写成 0
  ⑥ 槽位既没 vivid 也没 raw → 明确报"没有可写入的数据"，**零请求**

场景各自独立跑（不同浏览器实例），避免互相影响：
  online ：A 正常写入（上传完整/请求重启/进度更新） + B 重启前读回是旧值（不算失败）
  offline：C 未连接就点写入 → 秒回 + 零请求 + 明确报错
  noraw  ：D 槽位没有 raw → 仍然能写（回归 §2 的"第二个原因"）
  rawonly：E 槽位只有 raw → 影调从 raw 解出来
  empty  ：F 槽位啥都没有 → 明确拒绝、零请求

用法：python scripts/dv_mpwrite.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

PRE = r"""<script>
window.__OM3_APP__=1;
window.__errs = [];
window.addEventListener('error', function(e){ window.__errs.push('ERR ' + e.message); });
window.addEventListener('unhandledrejection', function(e){ window.__errs.push('REJ ' + String(e.reason)); });
window.__cam = { text:'', buf:'', calls:[], rebooted:false, declared:0 };
window.__offline = false;      /* true = 相机根本连不上（网络层失败） */
window.__noCommit = false;     /* true = 模拟"相机没接受"：restore 状态回来也不换数据 */
window.XMLHttpRequest = function(){
  var self = this;
  self.readyState = 0; self.status = 0; self.responseText = '';
  self.open = function(m, u){ self._u = String(u); };
  self.setRequestHeader = function(){};
  self.send = function(body){
    if(window.__offline){
      self.status = 0; self.responseText = ''; self.readyState = 4;
      setTimeout(function(){ if(self.onerror) self.onerror(); }, 0);
      return;
    }
    var u = self._u, q = (u.split('?')[1] || ''), path = u.replace(/^https?:\/\/[^\/]+\//, '');
    var st = 200, txt = '';
    if(/^send_partialmysetdata/.test(path)){
      var off = +((/offset=(\d+)/.exec(q)) || [])[1];
      window.__cam.calls.push('chunk@' + off);
      window.__cam.buf = (window.__cam.buf || '').slice(0, off) + String(body || '');
    }
    else if(/^set_mysetdatasize/.test(path)){ window.__cam.declared = +((/size=(\d+)/.exec(q)) || [])[1];
      window.__cam.szCount = (window.__cam.szCount || 0) + 1; txt = 'ok'; }
    else if(/^get_mysetrestorestate/.test(path)){
      txt = '<status>success</status>';
      if(!window.__noCommit && window.__cam.buf) window.__cam.text = window.__cam.buf;
    }
    else if(/^get_mysetdatasize/.test(path)){ txt = '<size>' + window.__cam.text.length + '</size>'; }
    else if(/^get_partialmysetdata/.test(path)){ txt = window.__cam.text; }
    else if(/^get_mysetbackupstate/.test(path)){ txt = '<status>idle</status>'; }
    else if(/^exec_reboot/.test(path)){ txt = 'rebooting'; window.__cam.rebooted = true; }
    else { txt = 'ok'; }
    self.status = st; self.responseText = txt; self.readyState = 4;
    setTimeout(function(){ if(self.onreadystatechange) self.onreadystatechange(); }, 0);
  };
};
</script>"""

COMMON = r"""
var o = [], fails = [];
function ok(c, m){ o.push((c ? '  [OK ] ' : '  [FAIL] ') + m); if(!c) fails.push(m); }
function modal(){ var e = document.getElementById('taskTitle'); return e ? (e.textContent || '') : ''; }
function prog(){ var e = document.getElementById('taskProg'); return e ? (e.textContent || '') : ''; }
function logTxt(){ var e = document.getElementById('camOut3'); return e ? (e.textContent || '') : ''; }
function dump(){
  o.push('累计 js 报错=' + window.__errs.length + '  om3errs=' + (window.__om3errs || 0));
  o.push('--- 结果：' + (fails.length ? ('失败 ' + fails.length + ' 项') : '全部通过') + ' ---');
  var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
  document.body.appendChild(d);
}
var CRLF = String.fromCharCode(13) + String.fromCharCode(10);
var recA = { n:'甲', a:'t', v:[1,2,3,0,0,0,0,0,0,0,0,0], hi:1, mid:-1, sh:2, eff:0, shp:0, con:1 };
var recB = { n:'乙', a:'t', v:[0,0,0,0,0,0,3,3,3,0,0,0], hi:0, mid:0, sh:0, eff:0, shp:0, con:0 };
function rawOf(rec){
  var raw = {}, t = window.__om3buildPayload(rec, 1, 'C1', 'OM-3');
  t.split(String.fromCharCode(10)).forEach(function(l){
    l = l.replace(String.fromCharCode(13), '');
    var p = l.split(',');
    if(p.length >= 3 && p[0] === '2' && p[1]) raw[p[1]] = p.slice(2).join(',');
  });
  return raw;
}
function camTextOf(rec){
  var t = window.__om3buildPayload(rec, 1, 'C1', 'OM-3');
  while(t.length < 12000) t += '2,MODE_COLOR_CREATOR_2_VIVID_SET4_1,MODE_STEP_0' + CRLF;
  return t;
}
/* 跑一次「我的配方 → 写入相机」，等任务弹窗进入终态（完成/失败）再回调。
   slot = 可选：直接指定槽位对象（测"没有 raw""只有 raw"这些变体） */
function runWrite(cb, offline, noCommit, slot){
  window.__offline = !!offline; window.__noCommit = !!noCommit;
  window.__cam.text = camTextOf(recB); window.__cam.buf = '';
  window.__cam.declared = 0; window.__cam.rebooted = false; window.__cam.calls = [];
  try{ if(window.__om3setConn) window.__om3setConn(!offline); }catch(e){}
  document.body.classList.toggle('cam-on', !offline);
  var ttl = document.getElementById('taskTitle'); if(ttl) ttl.textContent = '';
  window.__progSeen = [];
  var iv = setInterval(function(){
    var t = prog();
    if(t && window.__progSeen.indexOf(t) < 0) window.__progSeen.push(t);
  }, 60);
  var t0 = Date.now();
  var setA = { id:'t1', name:'写入测试甲', desc:'', from:'myset1', camera:'OM-3',
               slots:{ 1: slot || { vivid: recA.v, raw: rawOf(recA), used: 9, name: '甲' } } };
  setTimeout(function(){ window.__om3mpWriteOne(JSON.parse(JSON.stringify(setA)), 1); }, 250);
  var w = setInterval(function(){
    var t = modal();
    if(t.indexOf('完成') >= 0 || t.indexOf('失败') >= 0){
      clearInterval(w);
      setTimeout(function(){ clearInterval(iv); cb(Date.now() - t0); }, 600);
    }else if(Date.now() - t0 > 60000){ clearInterval(w); clearInterval(iv); cb(-1); }
  }, 150);
}
"""

SCEN_ONLINE = r"""
setTimeout(function(){
  document.getElementById('tabMine').click();
  setTimeout(function(){
    runWrite(function(ms){
      o.push('【A 正常写入】用时 ' + ms + 'ms');
      ok(window.__cam.buf.length === window.__cam.declared && window.__cam.declared > 0,
         '上传数据完整：' + (window.__cam.buf || '').length + '/' + window.__cam.declared + ' 字节（'
         + window.__cam.calls.length + ' 块）');
      ok(window.__cam.rebooted, '申请了相机重启');
      ok(window.__cam.text.indexOf('MODE_COLOR_CREATOR_2_VIVID_SET1_1,MODE_STEP_P1') >= 0, '相机里已经是甲的值');
      ok(modal().indexOf('失败') < 0, '没有报失败（标题：' + JSON.stringify(modal()) + '）');
      var ps = window.__progSeen;
      o.push('    进度小字 ' + ps.length + ' 条：' + JSON.stringify(ps.slice(0, 5)));
      var real = ps.filter(function(x){ return x.indexOf('准备中') < 0; });
      ok(real.length >= 2 && ps[ps.length - 1].indexOf('准备中') < 0,
         '小字一路更新、最后不再停在"准备中/初始化"（' + real.length + ' 条实质进度 + 初始的"准备中…"）');
      ok(logTxt().indexOf('已请求重启') >= 0, '日志里有"已请求重启"');
      runWrite(function(ms2){
        o.push('【B 重启前读回还是旧值（正常现象）】用时 ' + ms2 + 'ms');
        ok(modal().indexOf('失败') < 0, '★没有假报失败（标题：' + JSON.stringify(modal()) + '）');
        var lg = logTxt().slice(-3000);
        ok(lg.indexOf('重启前读回') >= 0, '日志说明了"重启前读回"');
        ok(lg.indexOf('正常的') >= 0 || lg.indexOf('属正常') >= 0, '并说明读到旧值属正常');
        ok(lg.indexOf('校验上次写入') >= 0, '指引了重启后用「校验上次写入」确认');
        o.push('    相机重启前仍是旧值=' + (window.__cam.text.indexOf(',MODE_STEP_P1') < 0) + '（正常）');
        dump();
      }, false, true);
    }, false, false);
  }, 2200);
}, 3000);
"""

SCEN_OFFLINE = r"""
setTimeout(function(){
  document.getElementById('tabMine').click();
  setTimeout(function(){
    runWrite(function(ms){
      o.push('【C 未连接相机就点写入】用时 ' + ms + 'ms');
      ok(ms < 6000, '很快返回（含 harness 轮询开销：' + ms + 'ms）');
      ok(window.__cam.calls.length === 0, '★一个请求都没发（calls=' + window.__cam.calls.length + '）');
      ok(window.__cam.rebooted === false && (window.__cam.buf || '').length === 0, '没有动过相机');
      ok(modal().indexOf('失败') >= 0, '任务弹窗明确报失败：' + JSON.stringify(modal()));
      var lg = logTxt().slice(-600);
      o.push('    日志尾：' + lg.replace(/\s+/g, ' ').slice(-200));
      ok(lg.indexOf('相机没连上') >= 0, '日志说清了原因（相机没连上）');
      ok(lg.indexOf('连接相机') >= 0, '并告诉他去哪连');
      dump();
    }, true, false);
  }, 2200);
}, 3000);
"""

SCEN_NORAW = r"""
setTimeout(function(){
  document.getElementById('tabMine').click();
  setTimeout(function(){
    /* 没有 raw：模拟官方 .oes 导入 / 新的紧凑分享格式导入（这些槽存的是 raw:{}） */
    var slot = { vivid: recA.v, raw: {}, used: 9, name: '甲',
                 hi: 1, mid: -1, lo: 2, eff: 0, shp: 0, con: 1 };
    runWrite(function(ms){
      o.push('【D 槽位没有 raw（.oes / 新紧凑格式导入的情形）】用时 ' + ms + 'ms');
      ok(window.__cam.calls.length > 0, '确实发起了写入（calls=' + window.__cam.calls.length + '）');
      ok(window.__cam.buf.length === window.__cam.declared && window.__cam.declared > 0,
         '★仍然完整上传：' + (window.__cam.buf || '').length + '/' + window.__cam.declared + ' 字节');
      ok(window.__cam.rebooted, '申请了相机重启');
      ok(window.__cam.text.indexOf('MODE_COLOR_CREATOR_2_VIVID_SET1_1,MODE_STEP_P1') >= 0,
         '相机会收到甲的值（**没有 raw 也写进去了** —— 修前这里直接拒"没有数据"）');
      ok(logTxt().indexOf('没有可写入的数据') < 0, '没有被"没有可写入的数据"拦下来');
      ok(modal().indexOf('失败') < 0, '没有报失败（标题：' + JSON.stringify(modal()) + '）');
      /* 影调字段的名字对齐：槽位里叫 lo，配方/键名里叫 LOW */
      ok(window.__cam.text.indexOf('MODE_COLOR_CREATOR_2_TONE_CONTROL_LOW_SET1,MODE_STEP_P2') >= 0,
         '槽位的 lo（阴影）被正确写成 TONE_CONTROL_LOW=P2');
      ok(window.__cam.text.indexOf('MODE_COLOR_CREATOR_2_TONE_CONTROL_MIDDLE_SET1,MODE_STEP_M1') >= 0,
         '中间调被正确写成 M1');
      ok(window.__cam.text.indexOf('MODE_COLOR_CREATOR_2_CONTRAST_SET1,MODE_CONTRAST_P1') >= 0,
         '对比被正确写成 CONTRAST_P1');
      dump();
    }, false, false, slot);
  }, 2200);
}, 3000);
"""

SCEN_RAWONLY = r"""
setTimeout(function(){
  document.getElementById('tabMine').click();
  setTimeout(function(){
    /* 只有 raw、没有影调字段：老数据 / 半成品数据。影调必须从 raw 解出来，不能写成 0。 */
    var slot = { vivid: recA.v, raw: rawOf(recA), used: 9, name: '甲' };
    runWrite(function(ms){
      o.push('【E 槽位只有 raw、没有影调字段】用时 ' + ms + 'ms');
      ok(window.__cam.buf.length === window.__cam.declared && window.__cam.declared > 0,
         '完整上传：' + (window.__cam.buf || '').length + '/' + window.__cam.declared + ' 字节');
      ok(window.__cam.text.indexOf('MODE_COLOR_CREATOR_2_TONE_CONTROL_HIGH_SET1,MODE_STEP_P1') >= 0,
         'hi 从 raw 解出来（=P1），没被写成 0');
      ok(window.__cam.text.indexOf('MODE_COLOR_CREATOR_2_TONE_CONTROL_LOW_SET1,MODE_STEP_P2') >= 0,
         'lo/sh 从 raw 解出来（=P2）');
      ok(modal().indexOf('失败') < 0, '没有报失败（标题：' + JSON.stringify(modal()) + '）');
      dump();
    }, false, false, slot);
  }, 2200);
}, 3000);
"""

SCEN_EMPTY = r"""
setTimeout(function(){
  document.getElementById('tabMine').click();
  setTimeout(function(){
    window.__cam.text = camTextOf(recB); window.__cam.buf = ''; window.__cam.declared = 0;
    window.__cam.rebooted = false; window.__cam.calls = [];
    try{ if(window.__om3setConn) window.__om3setConn(true); }catch(e){}
    document.body.classList.add('cam-on');            /* 故意"已连接"：证明拒绝是因为没数据，不是因为没连相机 */
    var setA = { id:'t1', name:'空槽测试', desc:'', from:'myset1', camera:'OM-3',
                 slots:{ 1: { vivid: null, raw: {}, used: 0, name: '空' } } };
    window.__om3mpWriteOne(JSON.parse(JSON.stringify(setA)), 1);
    setTimeout(function(){
      o.push('【F 槽位既没 vivid 也没 raw】');
      ok(window.__cam.calls.length === 0, '★一个请求都没发（calls=' + window.__cam.calls.length + '）');
      ok(window.__cam.rebooted === false && (window.__cam.buf || '').length === 0, '没有动过相机');
      var lg = logTxt().slice(-500);
      o.push('    日志尾：' + lg.replace(/\s+/g, ' ').slice(-160));
      ok(lg.indexOf('没有可写入的数据') >= 0, '日志明确说"没有可写入的数据"');
      ok(modal().indexOf('完成') < 0 && modal().indexOf('失败') < 0,
         '没有起任务弹窗（不是"跑一半才发现不行"）');
      dump();
    }, 1500);
  }, 2200);
}, 3000);
"""

SCEN_TIER = r"""
setTimeout(function(){
  document.getElementById('tabMine').click();
  setTimeout(function(){
    /* 假相机里的基线必须是"4 个槽的键都在"的整份 my-set（真相机的 dump 就是这样；camTextOf 只给 SET1） */
    var zero = { v:[0,0,0,0,0,0,0,0,0,0,0,0], hi:0, mid:0, sh:0, eff:0, shp:0, con:0 };
    var bl = [];
    for(var sN = 1; sN <= 4; sN++){
      var tt = window.__om3buildPayload(sN === 1 ? recB : zero, sN, 'C1', 'OM-3');
      var ls = tt.split(String.fromCharCode(10));
      for(var li = 0; li < ls.length; li++){
        var ll = ls[li].replace(String.fromCharCode(13), '');
        if(!ll) continue;
        if(sN > 1 && !/^2,/.test(ll)) continue;
        bl.push(ll);
      }
    }
    window.__cam.text = bl.join(String.fromCharCode(10));
    window.__cam.buf = ''; window.__cam.declared = 0;
    window.__cam.szCount = 0; window.__cam.rebooted = false; window.__cam.calls = [];
    try{ if(window.__om3setConn) window.__om3setConn(true); }catch(e){}
    document.body.classList.add('cam-on');
    /* 4 个槽：1、3 有数据，2、4 空 → 整套写入应该只写 2 个槽、**只声明一次大小 / 只重启一次** */
    var setA = { id:'t2', name:'整套测试', desc:'', from:'myset1', camera:'OM-3',
                 slots:{ 1: { vivid: recA.v, raw: rawOf(recA), used: 9, name:'甲槽' },
                         2: null,
                         3: { vivid: recB.v, raw: rawOf(recB), used: 9, name:'丙槽' },
                         4: { vivid: null, raw: {}, used: 0, name:'空' } } };
    try{ localStorage.setItem('om3sets', JSON.stringify([JSON.parse(JSON.stringify(setA))])); }catch(e){}
    window.__om3mpWriteTier(JSON.parse(JSON.stringify(setA)), 'myset1', [1,2,3,4], '整套 2 个槽');
    setTimeout(function(){
      o.push('【G 整套写入（4 个槽合并成一次上传）】');
      var lg = logTxt().slice(-9000).replace(/\s+/g, ' ');   /* 合并/跳过那两行在日志前半段，窗口要够大 */
      o.push('    日志尾：' + lg.slice(-220));
      ok(window.__cam.szCount === 1, '★★只声明过一次大小 = 只有**一次**上传（实际 ' + window.__cam.szCount + ' 次；逐个写会是 2 次）');
      ok(window.__cam.rebooted === true, '请求过重启');
      ok(window.__cam.calls.length > 0, '真的往相机传了数据（块数 ' + window.__cam.calls.length + '）');
      ok(lg.indexOf('合并成') >= 0, '★日志写明"合并成一次上传"');
      ok(lg.indexOf('跳过') >= 0, '★空槽自动跳过（日志里有）');
      ok((window.__cam.text || '').indexOf('SET1_') >= 0 && (window.__cam.text || '').indexOf('SET3_') >= 0,
         '★★这一份上传里**同时**有槽1（SET1）和槽3（SET3）的数据 —— 这就是"合并"的证据');
      ok(modal().indexOf('失败') < 0, '没有报失败（标题：' + JSON.stringify(modal()) + '）');
      var st = null; try{ st = JSON.parse(localStorage.getItem('om3sets') || '[]'); }catch(e){}
      var got = null; for(var i = 0; st && i < st.length; i++) if(st[i].id === 't2') got = st[i];
      o.push('    写入后状态：' + JSON.stringify(got ? [got.mount, got.mountTier, got.mountSlots] : null));
      ok(!!got && got.mount === 'on' && String(got.mountSlots) === '1,3',
         '★写完标成「已挂载」，槽位记成 1、3（实际 ' + JSON.stringify(got ? [got.mount, got.mountSlots] : null) + '）');
      dump();
    }, 3200);
  }, 2200);
}, 3000);
"""

k = src.find('<body')
j = src.find('>', k) + 1
ud = TMP + r'\ompwrite'


def run_once(scen, body_js):
    flag = "<script>window.__SCEN='" + scen + "';</script>"
    tail = '<script>' + COMMON + body_js + '</script>'
    out = src[:j] + flag + PRE + src[j:].replace('</body>', tail + '</body>', 1)
    p = TMP + r'\dv_mpwrite_' + scen + '.html'
    open(p, 'w', encoding='utf-8', newline='').write(out)
    subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
    r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                        '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                        '--user-data-dir=' + ud, '--window-size=412,900',
                        '--virtual-time-budget=60000', '--dump-dom',
                        'file:///' + p.replace('\\', '/')],
                       capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
    dom = r.stdout or ''
    kk = dom.find('id="DBGOUT"')
    return dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('（无输出）DOM=%d' % len(dom))


allfail = 0
for scen, js in (('online', SCEN_ONLINE), ('offline', SCEN_OFFLINE),
                 ('noraw', SCEN_NORAW), ('rawonly', SCEN_RAWONLY), ('empty', SCEN_EMPTY),
                 ('tier', SCEN_TIER)):
    txt = run_once(scen, js)
    print(txt)
    allfail += sum(1 for l in txt.split('\n') if l.startswith('  [FAIL]'))
print()
print('===== 六个场景合计失败 ' + str(allfail) + ' 项 =====')
