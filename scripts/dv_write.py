# -*- coding: utf-8 -*-
"""写相机路径实测（不接真相机）：用一个假 XMLHttpRequest 顶替相机 HTTP。

被测函数：writeSlotRecipe / om3WriteViaSlot（就是「导入相机」「写入相机」走的那个）

四个场景：
  A 正常            → 分块全成功，相机拿到的数据长度 == 声明长度，申请重启
  B 某块偶发失败    → 应重试后成功，数据仍然完整
  C 某块一直失败    → 应**中止**、不重启、明确报错（修前是"照旧往下传 → 数据缺一段 → 还报成功"）
  D 配方与槽位一样  → 应明确说"完全一样，相机不会变"

用法：python scripts/dv_write.py [new|old]      old = 用临时副本还原修复前的写法做对照
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
mode = sys.argv[1] if len(sys.argv) > 1 else 'new'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

if mode == 'old':
    # 还原修复前的行为：失败不中止（bad<=1 照样往下传）+ 只用 bad>1 判断
    # ① 失败不再中止：还原成"只记 bad，照旧往下传"
    old_break = ("      if(rr && rr.status !== 200){\n"
                 "        bad++;\n"
                 "        lg('\u2466 \u7b2c ' + n + ' \u5757 offset=' + off + ' \u91cd\u8bd5 3 \u6b21\u4ecd\u5931\u8d25 \u2192 \u4e2d\u6b62\uff0c\u4e0d\u518d\u5f80\u4e0b\u4f20\uff08\u5426\u5219\u6570\u636e\u4f1a\u7f3a\u4e00\u6bb5\uff09', 'err');\n"
                 "        break;\n"
                 "      }")
    assert old_break in src, '找不到新的中止分支，无法做 old 对照'
    src = src.replace(old_break, "      if(rr && rr.status !== 200){ bad++; }", 1)
    # ② 末尾判断还原成旧的 bad > 1（原来"只错一块"就不算失败）
    import re as _re
    src2, cnt = _re.subn(r"    if\(bad \|\| off < after\.length\)\{.*?\n    \}\n",
                         "    if(bad > 1){\n      throw new Error('\u4e0a\u4f20\u6709\u5757\u5931\u8d25\uff0c\u672a\u5b8c\u6210');\n    }\n",
                         src, count=1, flags=_re.S)
    assert cnt == 1, '找不到新的中止判断'
    src = src2
    print('（对照模式：已还原成修复前的"失败照旧往下传 / 只认 bad>1"）\n')

head = r"""<script>
window.__OM3_APP__=1;
window.__errs = [];
window.addEventListener('error', function(e){ window.__errs.push('ERR ' + e.message); });
window.addEventListener('unhandledrejection', function(e){ window.__errs.push('REJ ' + (e.reason && e.reason.message ? e.reason.message : e.reason)); });
window.__cam = { text:'', buf:'', calls:[], rebooted:false, declared:0, commits:0 };
window.__fail = {};
/* ---- 假相机：顶替 XMLHttpRequest ---- */
window.XMLHttpRequest = function(){
  var self = this;
  self.readyState = 0; self.status = 0; self.responseText = '';
  self.open = function(m, u){ self._u = String(u); };
  self.setRequestHeader = function(){};
  self.send = function(body){
    var u = self._u, q = (u.split('?')[1] || ''), path = u.replace(/^https?:\/\/[^\/]+\//, '');
    var st = 200, txt = '';
    if(/^send_partialmysetdata/.test(path)){
      var off = +((/offset=(\d+)/.exec(q)) || [])[1];
      var left = window.__fail[off] || 0;
      window.__cam.calls.push('chunk@' + off + ' len=' + (body ? body.length : 0) + (left ? ' <FAIL>' : ''));
      if(left > 0){ window.__fail[off] = left - 1; st = 500; txt = 'busy'; }
      else { window.__cam.buf = (window.__cam.buf || '').slice(0, off) + String(body || ''); }
    }
    else if(/^switch_cammode/.test(path)){ st = 200; txt = 'ok'; }
    else if(/^request_restoremysetdata/.test(path)){ st = 200; txt = 'restore'; }
    else if(/^set_mysetdatasize/.test(path)){
      window.__cam.declared = +((/size=(\d+)/.exec(q)) || [])[1]; st = 200; txt = 'ok';
      window.__cam.calls.push('declare=' + window.__cam.declared);
    }
    else if(/^get_mysetrestorestate/.test(path)){
      st = 200; txt = '<status>success</status>';
      if(window.__cam.buf){ window.__cam.text = window.__cam.buf; window.__cam.commits++; }
    }
    else if(/^request_getmysetdata/.test(path)){ st = 200; txt = 'ok'; }
    else if(/^get_mysetbackupstate/.test(path)){ st = 200; txt = '<status>idle</status>'; }
    else if(/^get_mysetdatasize/.test(path)){ st = 200; txt = '<size>' + window.__cam.text.length + '</size>'; }
    else if(/^get_partialmysetdata/.test(path)){ st = 200; txt = window.__cam.text; }
    else if(/^exec_reboot/.test(path)){ st = 200; txt = 'rebooting'; window.__cam.rebooted = true; window.__cam.calls.push('REBOOT'); }
    else { st = 200; txt = ''; }
    self.status = st; self.responseText = txt; self.readyState = 4;
    setTimeout(function(){ if(self.onreadystatechange) self.onreadystatechange(); }, 0);
  };
};
</script>"""

JS = r"""
setTimeout(function(){
  var o = [], R = [];
  var recA = { n:'甲', a:'t', v:[1,2,3,0,0,0,0,0,0,0,0,0], hi:1, mid:-1, sh:2, eff:0, shp:0, con:1 };
  var recB = { n:'乙', a:'t', v:[0,0,0,0,0,0,3,3,3,0,0,0], hi:0, mid:0, sh:0, eff:0, shp:0, con:0 };
  function pad(t){
    var CRLF = String.fromCharCode(13) + String.fromCharCode(10), i = 0;
    while(t.length < 12000){ i++; t += '2,FILLER_' + ('' + i).padStart ? '' : ''; break; }
    return t;
  }
  /* 用 app 自己的 buildPayload 造"相机里现有的数据"，再用填充行撑到 >4096 字节（多块） */
  function makeCamera(rec){
    var base = window.__om3buildPayload(rec, 1, 'C1', 'OM-3');
    var CRLF = String.fromCharCode(13) + String.fromCharCode(10);
    while(base.length < 12000) base += '2,MODE_COLOR_CREATOR_2_VIVID_SET4_1,MODE_STEP_0' + CRLF
                                    + '2,MODE_COLOR_CREATOR_2_VIVID_SET4_2,MODE_STEP_0' + CRLF;
    return base;
  }
  function logTxt(){ var e = document.getElementById('camOut3'); return e ? (e.textContent || '') : ''; }
  function logHas(s){ return logTxt().indexOf(s) >= 0; }
  function camHasA(){ return window.__cam.text.indexOf('MODE_COLOR_CREATOR_2_VIVID_SET1_1,MODE_STEP_' + 'P1') >= 0; }
  function reset(text){ window.__cam.text = text; window.__cam.buf = ''; window.__cam.declared = 0;
                        window.__cam.rebooted = false; window.__cam.calls = []; window.__cam.commits = 0; }

  var CAM_B = makeCamera(recB);
  R.push('相机初始数据长度=' + CAM_B.length + ' 字节（应 >4096，会分多块）');

  var seq = [];
  function step(fn){ seq.push(fn); }
  function dump(tag){
    if(document.getElementById('DBGOUT')) return;
    o.push('--- 结束（' + tag + '）---');
    o.push('__om3writeSlot 存在=' + (typeof window.__om3writeSlot) + '  __om3buildPayload=' + (typeof window.__om3buildPayload));
    o.push('js 报错=' + JSON.stringify(window.__errs));
    var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
    document.body.appendChild(d);
  }
  function run(){
    if(!seq.length){ dump('正常走完'); return; }
    var f = seq.shift();
    try{ f(run); }catch(e){ o.push('!! 场景抛错：' + e.message); dump('异常'); }
  }
  /* 保险：无论如何 20 秒后要把结果写出来 */
  setTimeout(function(){ dump('保险超时'); }, 20000);

  /* A 正常 */
  step(function(next){
    reset(CAM_B);
    window.__om3write(recA, 1, 'C1', 'OM-3').then(function(r){
      o.push('【A 正常】ok=' + r.ok);
      o.push('   分块数=' + window.__cam.calls.filter(function(x){ return x.indexOf('chunk')===0; }).length
           + '  声明=' + window.__cam.declared + '  相机实际收到=' + (window.__cam.buf||'').length
           + '  → 完整=' + ((window.__cam.buf||'').length === window.__cam.declared));
      o.push('   申请重启=' + window.__cam.rebooted + '  相机数据已含新配方=' + camHasA());
      next();
    });
  });
  /* B 偶发失败 2 次 */
  step(function(next){
    reset(CAM_B);
    window.__fail[8192] = 2;
    window.__om3write(recA, 1, 'C1', 'OM-3').then(function(r){
      o.push('【B 第3块偶发失败2次】ok=' + r.ok);
      o.push('   重试过（日志里有"重试"）=' + logHas('重试')
           + '  声明=' + window.__cam.declared + '  收到=' + (window.__cam.buf||'').length
           + '  → 完整=' + ((window.__cam.buf||'').length === window.__cam.declared));
      o.push('   申请重启=' + window.__cam.rebooted + '  相机数据已含新配方=' + camHasA());
      next();
    });
  });
  /* C 一直失败 */
  step(function(next){
    reset(CAM_B);
    var mark = logTxt().length;
    window.__fail[8192] = 99;
    window.__om3write(recA, 1, 'C1', 'OM-3').then(function(r){
      o.push('【C 第3块一直失败】ok=' + r.ok + '（期望 false）');
      o.push('   声明=' + window.__cam.declared + '  收到=' + (window.__cam.buf||'').length
           + '  → 完整=' + ((window.__cam.buf||'').length === window.__cam.declared) + '（期望 false）');
      o.push('   申请重启=' + window.__cam.rebooted + '（期望 false）');
      o.push('   日志有"已中止"=' + logHas('已中止') + '  有"写入没有完成"=' + logHas('写入没有完成'));
      next();
    });
  });
  /* D 与槽位现有的完全一样 */
  step(function(next){
    reset(window.__om3buildPayload(recB, 1, 'C1', 'OM-3'));   /* 相机里就是 recB，再写 recB */
    window.__om3write(recB, 1, 'C1', 'OM-3').then(function(r){
      o.push('【D 配方与槽位一样】ok=' + r.ok);
      o.push('   日志有"完全一样"=' + logHas('完全一样'));
      next();
    });
  });

  run();
}, 3000);
"""
tail = '<script>' + JS + '</script>'

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_write.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\owrite'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=40000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
