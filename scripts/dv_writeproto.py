# -*- coding: utf-8 -*-
"""写入协议护栏验收（第二十八轮：把顺序改成官方 APK 的真实顺序）。

为什么改：2026-09-24 重新反汇编官方 APK 的写入实现 `com.omdigitalsolutions.oishare.settings.myset.a`，
按调用链走出来的顺序是：

    doInBackground → n()  set_mysetdatasize?size=N          （先声明大小）
    a$a 回调     → b()  send_partialmysetdata?offset=&size=  （分块传完，最后一块传完才往下走）
    a$b 回调     → i()  request_restoremysetdata?action=restore（传完才请求恢复）
    a$c 回调     → j()  get_mysetrestorestate（轮询；status=busy → 1 秒后再问）
    a$d 回调     → 就绪 → 结束（UI 侧再 exec_reboot.cgi）

而 HANDOVER 里记的「restore → 轮询 → 声明大小 → 传」是**读反了**（大概是照方法定义顺序 l/m/n/o 猜的调用
顺序）；我们 app 一直照那个反了的顺序做 —— 相机在还没暂存任何数据时就被要求 restore，回 `generalerror`
完全说得通。

本脚本用假相机逐条断言**顺序**和**会不会被骗**：

  A  restore=generalerror（传完之后）      → 明确报失败、**不重启**、给出关机再开机建议
  B  开工前 = 真机的**常态**（result=ok + status=generalerror）→ **不重置通道**、照常写完
     （2026-09-24 真机确认：这台相机空闲时就是这个值，把它当"卡住"会每次白重置一次通道）
  C  声明大小回的 size 与本地不一致        → 一块都不传、也不 restore、不重启
  D  restore ok 但轮询回 generalerror      → 报"没有成功"、不重启
  E  正常路径 + **顺序断言**（声明大小 → 传 → restore → 轮询 → 重启；reboot 202 算接受）
  F  开工前 result=generalerror、重置后**依旧**报错 → 只 warn，**不拦着写**（不能因为认不出就卡死）
  G  某一块一直失败                        → 传不完就中止，**绝不** request_restoremysetdata、不重启
  H  开工前 result=generalerror（真报错）  → **才**重置通道（play→maintenance）→ 重置后正常 → 写完

用法：python scripts/dv_writeproto.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

PRE = r"""<script>
window.__OM3_APP__=1;
window.__errs=[];
window.addEventListener('error', function(e){ window.__errs.push('ERR ' + (e.message||'')); });
window.addEventListener('unhandledrejection', function(e){ window.__errs.push('REJ ' + String(e.reason)); });

/* ===== 假相机：按 scenario 决定每个接口怎么回 ===== */
window.__cam = { scen:'A', calls:[], dumps:{} };
function mkdump(){
  var L = [];
  var keys = [];
  for (var k1 = 1; k1 <= 12; k1++) keys.push('MODE_COLOR_CREATOR_2_VIVID_SET1_' + k1);
  var vals = ['MODE_STEP_P1','MODE_STEP_P1','MODE_STEP_0','MODE_STEP_0','MODE_STEP_0','MODE_STEP_P2',
              'MODE_STEP_P2','MODE_STEP_P2','MODE_STEP_P2','MODE_STEP_P2','MODE_STEP_P1','MODE_STEP_P1'];
  for (var i=0;i<12;i++) L.push('2,' + keys[i] + ',' + vals[i]);
  L.push('2,MODE_COLOR_CREATOR_2_TONE_CONTROL_HIGH_SET1,MODE_STEP_M2');
  L.push('2,MODE_COLOR_CREATOR_2_TONE_CONTROL_MIDDLE_SET1,MODE_STEP_0');
  L.push('2,MODE_COLOR_CREATOR_2_TONE_CONTROL_LOW_SET1,MODE_STEP_M1');
  L.push('2,MODE_COLOR_CREATOR_2_SHADING_SET1,MODE_STEP_0');
  L.push('2,MODE_COLOR_CREATOR_2_SHARP_SET1,MODE_SHARP_0');
  L.push('2,MODE_COLOR_CREATOR_2_CONTRAST_SET1,MODE_CONTRAST_P1');
  return L.join('\r\n') + '\r\n';
}
(function(){
  var dump = mkdump();
  window.__cam.dump = dump;
  var realOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(m, u){ this.__u = String(u); this.__m = String(m); return realOpen.apply(this, arguments); };
  var realSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function(b){
    var self = this, u = this.__u || '';
    window.__cam.calls.push(u);
    function fin(status, text){
      try{
        Object.defineProperty(self, 'status', { value: status, configurable: true });
        Object.defineProperty(self, 'readyState', { value: 4, configurable: true });
        Object.defineProperty(self, 'responseText', { value: text, configurable: true });
        Object.defineProperty(self, 'response', { value: text, configurable: true });
      }catch(e){}
      if(self.onreadystatechange) self.onreadystatechange();
      if(self.onload) self.onload();
    }
    var s = window.__cam.scen;
    function okXml(extra){ return '<?xml version="1.0"?><response><result>ok</result>' + (extra || '') + '</response>'; }
    function genErr(){ return '<?xml version="1.0"?><response><result>generalerror</result></response>'; }
    setTimeout(function(){
      if(/switch_cammode/.test(u)){
        if(/mode=play/.test(u)) window.__cam.resetDone = true;   /* B/F：退出维护模式 = 通道被重置过 */
        return fin(200, okXml());
      }
      if(/get_mysetdatasize/.test(u)) return fin(200, okXml('<datasize>' + dump.length + '</datasize>'));
      if(/get_mysetbackupstate/.test(u)) return fin(200, okXml('<status>success</status>'));
      if(/request_getmysetdata/.test(u)) return fin(200, okXml('<status>success</status><datasize>' + dump.length + '</datasize>'));
      if(/get_partialmysetdata/.test(u)){
        var m = /offset=(\d+)/.exec(u), off = m ? Number(m[1]) : 0;
        var sz = 4096;
        return fin(200, dump.slice(off, off + sz));
      }
      if(/request_restoremysetdata/.test(u)){
        window.__cam.restores = (window.__cam.restores || 0) + 1;   /* 计数要在分支之前，否则 A 场景数不到 */
        if(s === 'A') return fin(200, genErr());          /* A：传完之后 restore 被拒 */
        return fin(200, okXml());
      }
      if(/get_mysetrestorestate/.test(u)){
        /* B：真机的常态 —— <result>ok</result><status>generalerror</status>（= 空闲，不是错误）
           H/F：<result>generalerror</result>（= result 层面真报错）→ 才该重置通道；
                H 重置后正常、F 重置后仍报错（页面不许卡死）
           D：传数据之前 idle、传完之后 status=generalerror；A/C/E/G：idle */
        /* B：开工前 = 空闲（ok+generalerror）；传完数据之后相机在应用 → idle
              （真机这次写入成功，说明传完之后的轮询不会回 generalerror） */
        if(s === 'B') return fin(200, okXml('<status>' + (window.__cam.chunked ? 'idle' : 'generalerror') + '</status>'));
        if(s === 'H' || s === 'F'){
          if(!window.__cam.resetDone || s === 'F'){
            return fin(200, '<?xml version="1.0"?><response><result>generalerror</result></response>');
          }
          return fin(200, okXml('<status>idle</status>'));
        }
        if(s === 'D') return fin(200, okXml('<status>' + (window.__cam.chunked ? 'generalerror' : 'idle') + '</status>'));
        return fin(200, okXml('<status>idle</status>'));
      }
      if(/set_mysetdatasize/.test(u)){
        var mm = /size=(\d+)/.exec(u), want = mm ? Number(mm[1]) : 0;
        if(s === 'C') return fin(200, okXml('<size>' + (want - 100) + '</size>'));
        return fin(200, okXml('<size>' + want + '</size>'));
      }
      if(/send_partialmysetdata/.test(u)){
        if(s === 'G') return fin(500, 'boom');       /* G：这一块永远失败 */
        window.__cam.chunked = true;
        return fin(200, okXml());
      }
      if(/exec_reboot/.test(u)) return fin(202, okXml('<status>success</status>'));
      return fin(200, okXml());
    }, 3);
  };
})();
</script>"""

JS = r"""
setTimeout(function(){
  var o = [], fails = [];
  function ok(c, m){ o.push((c ? '  [OK ] ' : '  [FAIL] ') + m); if(!c) fails.push(m); }
  function el(id){ return document.getElementById(id); }
  function allLog(){ var s = ''; document.querySelectorAll('.log, #camOut1, #camOut2, #camOut3, pre').forEach(function(e){ s += String(e.textContent || '') + '\n'; }); return s; }
  function fin(){
    o.push('累计 js 报错=' + window.__errs.length + '  om3errs=' + (window.__om3errs || 0));
    if(window.__errs.length) o.push('  ' + window.__errs.slice(0, 3).join(' | '));
    o.push('--- 结果：' + (fails.length ? ('失败 ' + fails.length + ' 项') : '全部通过') + ' ---');
    var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
    document.body.appendChild(d);
  }
  var steps = [], si = 0;
  function step(f){ steps.push(f); }
  function run(){ if(!steps.length) return fin(); var f = steps.shift();
    try{ f(run); }catch(e){ o.push('  !! 步骤抛错：' + (e && e.message ? e.message : e)); fin(); } }
  function sleep(ms, cb){ setTimeout(cb, ms); }

  /* 用真实入口：我的配方 → 写入相机（内部就是 writeRecipeCore） */
  function putFix(){
    localStorage.setItem('om3sets', JSON.stringify([
      { id:'S1', name:'协议探针', from:'myset1', slots:{ 1:{ vivid:[1,1,0,0,0,2,2,2,2,2,1,1], used:8,
        hi:-2, mid:0, lo:2, eff:0, shp:1, con:1, name:'探针槽' }, 2:null, 3:null, 4:null } }
    ]));
  }
  function prep(scen){
    window.__cam.scen = scen; window.__cam.calls = []; window.__cam.chunked = false;
    window.__cam.resetDone = false; window.__cam.restores = 0;
    putFix();
    try{ if(window.__om3setConn) window.__om3setConn(true); }catch(e){}
    document.body.classList.add('cam-on');
    el('tabMine').click();
  }
  function clickWrite(cb){
    window.__om3mpRender();
    window.__om3mpDetail(0);
    sleep(400, function(){
      var b = null;
      document.querySelectorAll('#mpList button').forEach(function(x){ if(/写入/.test(String(x.textContent)) && !/改|删|状态/.test(String(x.textContent))) b = x; });
      ok(!!b, '详情页有「写入相机」按钮');
      if(b) b.click();
      sleep(9000, cb);
    });
  }
  function tryWrite(scen, cb){
    prep(scen);
    sleep(400, function(){ clickWrite(cb); });
  }
  function count(pat){ var c = 0; window.__cam.calls.forEach(function(u){ if(pat.test(u)) c++; }); return c; }
  /* 把请求序列翻译成"动作序列"，用来断言**顺序** */
  function kinds(){
    return window.__cam.calls.map(function(u){
      if(/switch_cammode/.test(u)) return /mode=play/.test(u) ? 'EXIT' : 'MAINT';
      if(/request_getmysetdata/.test(u)) return 'GET';
      if(/get_mysetbackupstate/.test(u)) return 'BSTATE';
      if(/get_mysetdatasize/.test(u)) return 'DSIZE';
      if(/get_partialmysetdata/.test(u)) return 'PGET';
      if(/get_mysetrestorestate/.test(u)) return 'RSTATE';
      if(/set_mysetdatasize/.test(u)) return 'SETSIZE';
      if(/send_partialmysetdata/.test(u)) return 'CHUNK';
      if(/request_restoremysetdata/.test(u)) return 'RESTORE';
      if(/exec_reboot/.test(u)) return 'REBOOT';
      return 'OTHER';
    });
  }
  function firstIdx(k, K){ for(var i=0;i<K.length;i++) if(K[i]===k) return i; return -1; }
  function lastIdx(k, K){ for(var i=K.length-1;i>=0;i--) if(K[i]===k) return i; return -1; }

  /* A：传完之后 restore 被拒 → 明确报失败、不重启 */
  step(function(next){
    tryWrite('A', function(){
      var t = allLog(), K = kinds();
      o.push('  A：序列=' + K.join('>'));
      o.push('  A：声明大小=' + count(/set_mysetdatasize/) + ' 块数=' + count(/send_partialmysetdata/) + ' restore=' + window.__cam.restores + ' 重启=' + count(/exec_reboot/));
      ok(count(/set_mysetdatasize/) === 1, '★A：先声明了大小（官方顺序的第一步）');
      ok(count(/send_partialmysetdata/) > 0, 'A：数据确实传了（新顺序下这是必然的，官方也这样）');
      ok(window.__cam.restores === 1, '★A：传完之后请求了一次 restore');
      ok(count(/exec_reboot/) === 0, '★A：restore 被拒 → **不请求重启**');
      ok(/拒绝|没有成功|generalerror/.test(t), '★A：日志明确写出 restore 被相机拒绝');
      ok(/关机再开机/.test(t), 'A：并给出可执行建议（关机再开机）');
      ok(lastIdx('CHUNK', K) < firstIdx('RESTORE', K), '★A：restore 确实在所有分块之后');
      next();
    });
  });

  /* B：开工前是真机的**常态**（result=ok + status=generalerror）→ **不重置通道**、照常写完 */
  step(function(next){
    tryWrite('B', function(){
      var t = allLog(), K = kinds();
      o.push('  B：序列=' + K.join('>'));
      o.push('  B：play=' + count(/switch_cammode\.cgi\?mode=play/) + ' 块数=' + count(/send_partialmysetdata/) + ' 重启=' + count(/exec_reboot/));
      ok(count(/switch_cammode\.cgi\?mode=play/) === 0, '★★B：result=ok + status=generalerror 是**空闲**（真机实测）→ **不做**多余的通道重置');
      ok(/直接开写/.test(t), '★B：日志说清"状态正常、直接开写"');
      ok(/不是.{0,4}错误|空闲/.test(t), 'B：并说明这台相机空闲时就是 generalerror，不是错误');
      ok(count(/send_partialmysetdata/) > 0, '★B：照常写完（' + count(/send_partialmysetdata/) + ' 块）');
      ok(window.__cam.restores === 1, '★B：传完才 restore');
      ok(count(/exec_reboot/) === 1, '★B：最后请求了重启');
      next();
    });
  });

  /* H：开工前 result=generalerror（result 层面真报错）→ **才**重置通道 → 重置后正常 → 写完 */
  step(function(next){
    tryWrite('H', function(){
      var t = allLog(), K = kinds();
      o.push('  H：序列=' + K.join('>'));
      o.push('  H：play=' + count(/switch_cammode\.cgi\?mode=play/) + ' 块数=' + count(/send_partialmysetdata/) + ' 重启=' + count(/exec_reboot/));
      ok(count(/switch_cammode\.cgi\?mode=play/) === 1, '★H：result=generalerror（真报错）→ 重置一次通道（mode=play 再回维护模式）');
      ok(/重置通道/.test(t) && /通道干净/.test(t), 'H：日志写清重置 + 重置后干净');
      ok(firstIdx('EXIT', K) < firstIdx('SETSIZE', K), '★H：重置发生在**声明大小之前**（此时重传代价为零）');
      ok(count(/send_partialmysetdata/) > 0, '★H：重置后照常写完（' + count(/send_partialmysetdata/) + ' 块）');
      ok(window.__cam.restores === 1, '★H：传完才 restore');
      ok(count(/exec_reboot/) === 1, '★H：最后请求了重启');
      next();
    });
  });

  /* C：相机回的 size 与本地不一致 → 中止（不传、不 restore、不重启） */
  step(function(next){
    tryWrite('C', function(){
      var t = allLog();
      o.push('  C：声明大小=' + count(/set_mysetdatasize/) + ' 块数=' + count(/send_partialmysetdata/) + ' restore=' + window.__cam.restores + ' 重启=' + count(/exec_reboot/));
      ok(count(/set_mysetdatasize/) === 1, 'C：先声明大小');
      ok(count(/send_partialmysetdata/) === 0, '★C：相机接受的大小与本地不一致 → 一块都不传');
      ok(window.__cam.restores === 0, '★C：也不 request_restoremysetdata');
      ok(count(/exec_reboot/) === 0, 'C：不请求重启');
      ok(/不一致/.test(t), 'C：日志说清"size 不一致"');
      next();
    });
  });

  /* D：restore ok 但轮询回 generalerror → 报"没有成功"、不重启 */
  step(function(next){
    tryWrite('D', function(){
      var t = allLog();
      o.push('  D：块数=' + count(/send_partialmysetdata/) + ' restore=' + window.__cam.restores + ' 重启=' + count(/exec_reboot/));
      ok(count(/send_partialmysetdata/) > 0, 'D：这次确实传了数据（' + count(/send_partialmysetdata/) + ' 块）');
      ok(window.__cam.restores === 1, 'D：传完后 restore 一次');
      ok(/没有成功|状态错误|拒绝这份数据/.test(t), '★D：轮询到 generalerror → 明确说"这次写入没有成功"');
      ok(count(/exec_reboot/) === 0, '★D：没成功就不请求重启');
      next();
    });
  });

  /* E：正常路径 + **顺序断言**（reboot 202 算接受） */
  step(function(next){
    tryWrite('E', function(){
      var t = allLog(), K = kinds();
      o.push('  E：序列=' + K.join('>'));
      ok(count(/send_partialmysetdata/) > 0, 'E：传了数据（' + count(/send_partialmysetdata/) + ' 块）');
      ok(firstIdx('SETSIZE', K) >= 0 && firstIdx('SETSIZE', K) < firstIdx('CHUNK', K), '★E：先声明大小 → 再传数据');
      ok(lastIdx('CHUNK', K) < firstIdx('RESTORE', K), '★E：**全部传完**才请求 restore（本轮改的核心）');
      ok(firstIdx('RESTORE', K) < lastIdx('RSTATE', K), '★E：restore 之后才轮询就绪状态');
      ok(lastIdx('RSTATE', K) < firstIdx('REBOOT', K), '★E：最后才请求重启');
      ok(count(/exec_reboot/) === 1, '★E：走到重启这一步');
      ok(/已请求重启（相机）：HTTP 202/.test(t), '★E：HTTP 202 被当成"已请求重启"（不再误报"没接受重启请求"）');
      ok(!/没有接受重启请求/.test(t), '★E：不再误报');
      ok(/自动核对/.test(t), 'E：并提示重启后会自动核对');
      next();
    });
  });

  /* F：开工前 result=generalerror、重置后**依旧**报错 → 只 warn，不拦着写 */
  step(function(next){
    tryWrite('F', function(){
      var t = allLog();
      o.push('  F：play=' + count(/switch_cammode\.cgi\?mode=play/) + ' 块数=' + count(/send_partialmysetdata/) + ' restore=' + window.__cam.restores);
      ok(count(/switch_cammode\.cgi\?mode=play/) === 1, 'F：还是尝试了重置通道');
      ok(/还是|依旧|可能/.test(t), 'F：日志提醒"重置后还是报错"');
      ok(count(/send_partialmysetdata/) > 0, '★F：**不因为状态认不出就卡死** —— 照样往下传');
      ok(window.__cam.restores === 1, 'F：传完也照样 restore');
      next();
    });
  });

  /* G：某一块一直失败 → 传不完就中止，绝不 restore、不重启 */
  step(function(next){
    tryWrite('G', function(){
      var t = allLog(), K = kinds();
      o.push('  G：块尝试=' + count(/send_partialmysetdata/) + ' restore=' + window.__cam.restores + ' 重启=' + count(/exec_reboot/));
      ok(count(/set_mysetdatasize/) === 1, 'G：先声明大小');
      ok(count(/send_partialmysetdata/) === 3, '★G：同一块重试 3 次（实际 ' + count(/send_partialmysetdata/) + ' 次）');
      ok(window.__cam.restores === 0, '★★G：数据没传完 → **绝不** request_restoremysetdata');
      ok(count(/exec_reboot/) === 0, '★G：也不请求重启');
      ok(/中止/.test(t), 'G：日志明确"已中止"');
      next();
    });
  });

  run();
}, 2600);
"""

tail = '<script>' + JS + '</script>'
i = src.find('<body'); j = src.find('>', i) + 1
out = src[:j] + PRE + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_writeproto.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\owriteproto'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=240000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
