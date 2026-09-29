# -*- coding: utf-8 -*-
"""给 app 加「导入相机」页：直连 OM-3（相机 Wi-Fi HTTP），
① 检测相机 ② 备份当前设置（只读） ③ 一次写入一个配方到指定 Color Profile 槽位。

协议来自逆向官方 OM Image Share 1.5.0（见 协议笔记-OM3相机直连.md）。
"""
import json
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
P = TMP + r'\app\base.html'
h = open(P, encoding='utf-8').read()
open(TMP + r'\app\base.before_camera.html', 'w', encoding='utf-8', newline='').write(h)

# ---------------------------------------------------------------- 配方数据
res = json.load(open(TMP + r'\all_recipes.json', encoding='utf-8'))['results']
FIELDS = ['yellow', 'orange', 'orangeRed', 'red', 'magenta', 'violet', 'blue', 'blueCyan',
          'cyan', 'greenCyan', 'green', 'yellowGreen']
RECIPES = []
for r in res:
    if not r.get('recipeName'):
        continue
    RECIPES.append({
        'n': r['recipeName'], 'a': r.get('authorName') or '', 'slug': r.get('slug') or '',
        't': r.get('type') or 'COLOR',
        'v': [int(r.get(f) or 0) for f in FIELDS],
        'hi': int(r.get('highlights') or 0), 'sh': int(r.get('shadows') or 0),
        'mid': int(r.get('midtones') or 0), 'con': int(r.get('contrast') or 0),
        'shp': int(r.get('sharpness') or 0), 'eff': int(r.get('shadingEffect') or 0),
        'wb': r.get('whiteBalance2') or '', 'wbt': r.get('whiteBalanceTemperature'),
        'wba': int(r.get('whiteBalanceAmberOffset') or 0), 'wbg': int(r.get('whiteBalanceGreenOffset') or 0),
        'monoColor': r.get('monochromeColor') or '', 'monoStr': r.get('monochromeColorStrength'),
        'grain': r.get('filmGrain') or '', 'hue': r.get('filmHue') or '',
    })
print('配方数据 %d 条（COLOR %d / MONO %d / 其他 %d）' % (
    len(RECIPES), sum(1 for x in RECIPES if x['t'] == 'COLOR'),
    sum(1 for x in RECIPES if x['t'] == 'MONO'), sum(1 for x in RECIPES if x['t'] not in ('COLOR', 'MONO'))))

# 「优化版」里用到的配方（按名字+作者对上 all_recipes），放在下拉框前面一组
opt = set()
for m in re.finditer(r'<span class="osname">(.*?)</span><span class="osauth">(.*?)</span>', h):
    nm, au = m.group(1).strip(), m.group(2).strip()
    for r in RECIPES:
        if r['n'] == nm and r['a'] == au:
            opt.add(r['slug'])
print('其中出现在优化版里的：%d 个' % len(opt))

# ---------------------------------------------------------------- CSS
CSS = '''
/* ---------- 导入相机页 ---------- */
.camcard,.camstep{background:#1e1e1e;border:1px solid #2e2e2e;border-radius:12px;padding:14px 16px;margin-bottom:14px}
.camhd{font-size:15px;font-weight:700;color:#fff;margin-bottom:10px}
.camcard b{color:#8fd8c2}
.camcard ol{margin:8px 0 0 20px;padding:0}
.camcard li{font-size:13px;line-height:1.75;color:#c8c8c8}
.camcard code,.camout code{background:#2a2a2a;color:#8fd8c2;border-radius:4px;padding:1px 5px;font-size:12px}
.camstep label{display:block;font-size:13px;color:#bbb;margin:8px 0}
.camstep select,.camstep input[type=text],.camstep input[type=number]{background:#262626;color:#e8e8e8;border:1px solid #3a3a3a;border-radius:8px;padding:7px 10px;font-size:13px;font-family:inherit;max-width:100%}
.camstep select{min-width:210px}
.camstep button{background:#2a2a2a;color:#e8e8e8;border:1px solid #3a3a3a;border-radius:8px;padding:9px 14px;font-size:13.5px;font-family:inherit;cursor:pointer;margin-right:8px}
.camstep button:hover{background:#333}
.camstep button.camprimary{background:#2f8f74;color:#fff;border-color:#2f8f74;font-weight:700}
.camstep button:disabled{opacity:.45;cursor:default}
.camout{font-size:12.5px;color:#9a9a9a;line-height:1.7;margin-top:10px;white-space:pre-wrap;word-break:break-all}
.camout .ok{color:#7ed3bd}
.camout .err{color:#e08a8a}
.camout .warn{color:#dcb98a}
.camchk{font-size:13px;color:#bbb}
.camchk input{vertical-align:-2px;margin-right:6px}
.camstep pre{background:#151515;border:1px solid #2e2e2e;border-radius:8px;padding:10px;font-size:11.5px;line-height:1.6;color:#cfe8dd;overflow-x:auto;white-space:pre}
.camstep details{margin:10px 0}
.camstep summary{cursor:pointer;font-size:13px;color:#8fd8c2}
.camwarn{background:#2b2118;border-left:3px solid #a8763c;color:#dcb98a;font-size:12.5px;line-height:1.7;padding:9px 12px;border-radius:8px;margin-top:10px}
'''

# ---------------------------------------------------------------- 页签按钮
TAB_OLD = '<button type="button" data-p="C">场景对比</button>'
assert h.count(TAB_OLD) == 1
h = h.replace(TAB_OLD, TAB_OLD + '<button type="button" data-p="D" id="tabD" style="display:none">导入相机</button>', 1)

# ---------------------------------------------------------------- 面板 D
PANE = '''
<div id="paneD" class="pane hide"><div class="wrap">
<h1>导入相机</h1>
<p class="sub">把配方直接写进 OM-3 的 Color Profile 槽位 · 走相机自带 Wi-Fi（不需要电脑、不需要 OM Workspace）</p>

<div class="camcard"><b>前置条件（只做一次）</b>
<ol>
<li>相机上：<code>MENU → Wi-Fi/蓝牙</code> 打开 Wi-Fi，屏幕上选「连接智能手机」，让它进入热点模式。</li>
<li>手机上：到系统 Wi-Fi 设置里连上相机的热点 <code>OM-3-xxxxxx</code>（会提示「无网络」，这是正常的，别断开）。</li>
<li>回到本页，按下面 ①②③ 的顺序操作。全程不用电脑。</li>
</ol>
<div class="camwarn"><b>写之前</b>：建议先点 ② 备份一次（只读、不会改相机）。万一写乱了，用手机里的官方 OM Image Share 恢复设置即可；配方只影响 Creative Dial 的 COLOR 档，不会动曝光/对焦。</div>
</div>

<div class="camstep"><div class="camhd">① 检测相机</div>
<button type="button" id="camCheck">检测相机</button>
<button type="button" id="camWifi" class="camghost">复制相机地址</button>
<div class="camout" id="camOut1">未连接。</div>
</div>

<div class="camstep"><div class="camhd">② 备份当前设置（只读）</div>
<button type="button" id="camBackup">读取并备份</button>
<button type="button" id="camDl" disabled>下载备份文件</button>
<div class="camout" id="camOut2">还没备份。备份会读相机当前的整套设置，存成文件留底，随时可以让我做回滚。</div>
</div>

<div class="camstep"><div class="camhd">③ 导入一个配方（一次一个）</div>
<label>写入到：<select id="camTarget">
  <option value="current" selected>当前状态（current）— 立刻生效，最常用</option>
  <option value="myset1">C1 自定义档</option>
  <option value="myset2">C2 自定义档</option>
  <option value="myset3">C3 自定义档</option>
  <option value="myset4">C4 自定义档</option>
  <option value="myset5">C5 自定义档</option>
</select></label>
<label>Color Profile 槽位：<select id="camSlot">
  <option value="1" selected>槽 1</option><option value="2">槽 2</option>
  <option value="3">槽 3</option><option value="4">槽 4</option>
</select></label>
<label>配方：<select id="camRecipe"></select></label>
<label>相机型号（自动从①读，一般不用改）：<input type="text" id="camModel" placeholder="例如 OM-3" style="width:160px"></label>
<details><summary>预览将要写入相机的数据</summary><pre id="camPreview"></pre></details>
<label class="camchk"><input type="checkbox" id="camReboot"> 写完后重启相机（官方 app 也这么做，重启后设置才完全生效）</label>
<button type="button" id="camWrite" class="camprimary">写入相机</button>
<div class="camout" id="camOut3">选择配方和槽位，点「写入相机」。写入前会自动先备份一次。</div>
</div>
</div></div>
'''

# ---------------------------------------------------------------- JS
JS = r'''
/* ================= 导入相机（相机 Wi-Fi 直连） ================= */
(function(){
  var REC = window.__OM3RECIPES__ || [];
  var BASE = 'http://192.168.0.10/';
  var App = window.__OM3_APP__ ? true : false;
  if(!App) return;                                  /* 桌面版没有这个页签 */

  var tabBtn = document.getElementById('tabD');
  if(tabBtn) tabBtn.style.display = '';
  if(!document.getElementById('paneD')) return;

  var ORDER = ['yellow','orange','orangeRed','red','magenta','violet','blue','blueCyan',
               'cyan','greenCyan','green','yellowGreen'];
  var MFILTER = {0:'MODE_MONOTONEFILTER_NORMAL',1:'MODE_MONOTONEFILTER_GREEN_YELLOW',2:'MODE_MONOTONEFILTER_GREEN',
                 3:'MODE_MONOTONEFILTER_CYAN',4:'MODE_MONOTONEFILTER_BLUE',5:'MODE_MONOTONEFILTER_MAGENTA',
                 6:'MODE_MONOTONEFILTER_RED',7:'MODE_MONOTONEFILTER_ORANGE',8:'MODE_MONOTONEFILTER_YELLOW'};
  var MNAME  = {'no filter':0,'green_yellow':1,'green-yellow':1,'green':2,'cyan':3,'blue':4,
                'magenta':5,'red':6,'orange':7,'yellow':8,'yellow filter':8};
  var MHUE   = {'normal':1,'sepia':5,'green':2,'purple':3,'blue':4};
  var GRAIN  = {'off':0,'low':1,'medium':2,'mid':2,'high':3};

  function step(v){ v = Math.round(+v||0); return 'MODE_STEP_' + (v>0 ? 'P'+v : v<0 ? 'M'+(-v) : '0'); }
  function sharp(v){ v = Math.round(+v||0); return 'MODE_SHARP_' + (v>0 ? 'P'+v : v<0 ? 'M'+(-v) : '0'); }
  function contr(v){ v = Math.round(+v||0); return 'MODE_CONTRAST_' + (v>0 ? 'P'+v : v<0 ? 'M'+(-v) : '0'); }

  /* 按官方 app 的格式拼数据：一行一个属性，\r\n 结尾 */
  function buildPayload(rec, slot, target, model){
    var L = [], i;
    L.push('1,' + (model||'') + ',0000,00000000,' + target + ',current');
    var pre = '2,MODE_COLOR_CREATOR_2_';
    if(rec.t === 'MONO'){
      var mc = (rec.monoColor||'').toLowerCase(), mi = MNAME[mc];
      if(mi === undefined){ for(var k in MNAME){ if(mc.indexOf(k)>=0){ mi = MNAME[k]; break; } } }
      L.push('2,MODE_MONOCHROME_CREATOR_MONOTONEFILTER_SET'+slot+','+MFILTER[mi===undefined?0:mi]);
      L.push('2,MODE_MONOCHROME_CREATOR_LEVEL_SET'+slot+','+step(rec.monoStr||0));
      L.push('2,MODE_MONOCHROME_CREATOR_TONE_CONTROL_HIGH_SET'+slot+','+step(rec.hi));
      L.push('2,MODE_MONOCHROME_CREATOR_TONE_CONTROL_LOW_SET'+slot+','+step(rec.sh));
      L.push('2,MODE_MONOCHROME_CREATOR_TONE_CONTROL_MIDDLE_SET'+slot+','+step(rec.mid));
      L.push('2,MODE_MONOCHROME_CREATOR_SHADING_SET'+slot+','+step(rec.eff));
      L.push('2,MODE_MONOCHROME_CREATOR_SHARP_SET'+slot+','+sharp(rec.shp));
      L.push('2,MODE_MONOCHROME_CREATOR_CONTRAST_SET'+slot+','+contr(rec.con));
      L.push('2,MODE_MONOCHROME_CREATOR_GRANULAR_SET'+slot+','+step(GRAIN[(rec.grain||'').toLowerCase()]||0));
      L.push('2,MODE_MONOCHROME_CREATOR_MONOTONECOLOR_SET'+slot+',MODE_MONOTONECOLOR_'+
             (['NORMAL','LIKE_GREEN','LIKE_PURPLE','LIKE_BLUE','LIKE_SEPIA'][(MHUE[(rec.hue||'').toLowerCase()]||1)-1]));
      return L.join('\r\n') + '\r\n';
    }
    for(i=0;i<12;i++) L.push(pre+'VIVID_SET'+slot+'_'+(i+1)+','+step(rec.v[i]));
    L.push(pre+'TONE_CONTROL_HIGH_SET'+slot+','+step(rec.hi));
    L.push(pre+'TONE_CONTROL_LOW_SET'+slot+','+step(rec.sh));
    L.push(pre+'TONE_CONTROL_MIDDLE_SET'+slot+','+step(rec.mid));
    L.push(pre+'SHADING_SET'+slot+','+step(rec.eff));
    L.push(pre+'SHARP_SET'+slot+','+sharp(rec.shp));
    L.push(pre+'CONTRAST_SET'+slot+','+contr(rec.con));
    return L.join('\r\n') + '\r\n';
  }
  window.__om3buildPayload = buildPayload;              /* 供自检脚本调用 */

  var o1 = document.getElementById('camOut1'), o2 = document.getElementById('camOut2'),
      o3 = document.getElementById('camOut3'), log3 = o3;

  function esc(s){ return String(s).replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c];}); }
  function line(el, msg, cls){
    var d = document.createElement('div');
    if(cls) d.className = cls;
    d.innerHTML = esc(msg);
    el.appendChild(d);
    el.scrollTop = el.scrollHeight;
  }
  function log(msg, cls){ line(log3, msg, cls); }

  /* 相机 API 是明文 HTTP；桌面版没有这个页签，所以不用考虑 CORS */
  function req(path, opt){
    opt = opt || {};
    return new Promise(function(resolve, reject){
      var x = new XMLHttpRequest(), done = false;
      var url = BASE + path;
      x.open(opt.method || 'GET', url, true);
      x.timeout = opt.timeout || 8000;
      x.onreadystatechange = function(){
        if(x.readyState !== 4 || done) return;
        done = true;
        resolve({status:x.status, text:x.responseText||'', url:url});
      };
      x.ontimeout = function(){ if(!done){ done = true; reject(new Error('超时（相机没应答）')); } };
      x.onerror = function(){ if(!done){ done = true; reject(new Error('连不上 '+BASE)); } };
      if(opt.body){
        x.setRequestHeader('Content-Type','application/octet-stream');
        x.send(opt.body);
      } else x.send();
    });
  }
  function sleep(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
  function sizeFrom(text){
    var m = String(text).match(/(?:size|Size|SIZE)[^0-9]{0,12}(\d+)/);
    if(m) return +m[1];
    m = String(text).match(/>\s*(\d+)\s*</);
    return m ? +m[1] : NaN;
  }
  function modelFrom(text){
    var m = String(text).match(/(?:model|Model|MODEL|cameraname|camera_name)[^A-Za-z0-9]{0,12}([A-Za-z0-9\-]+)/);
    return m ? m[1] : '';
  }

  /* ---------- ① 检测相机 ---------- */
  document.getElementById('camCheck').addEventListener('click', async function(){
    o1.innerHTML = ''; this.disabled = true;
    try{
      line(o1, '正在连 ' + BASE + 'get_caminfo.cgi …');
      var r = await req('get_caminfo.cgi');
      if(r.status === 200){
        line(o1, '相机应答（HTTP ' + r.status + '）', 'ok');
        line(o1, '原始返回：' + r.text.slice(0, 600));
        var md = modelFrom(r.text);
        if(md){ document.getElementById('camModel').value = md; line(o1, '识别到型号：' + md, 'ok'); }
        else line(o1, '没自动认出型号——请照相机机身上写的填一下上面的「相机型号」（例如 OM-3），它要写进数据头部。', 'warn');
        line(o1, '结果：相机在线，可以做 ② 备份了。', 'ok');
      } else {
        line(o1, '相机返回 HTTP ' + r.status + '：' + r.text.slice(0, 200), 'err');
      }
    }catch(e){
      line(o1, '失败：' + e.message, 'err');
      line(o1, '检查：①相机 Wi-Fi 开了吗 ②手机连的是相机热点吗（不是家里的 Wi-Fi）③手机系统设置里对浏览器/本 app 有没有限制「本地网络」权限。', 'warn');
    }
    this.disabled = false;
  });

  document.getElementById('camWifi').addEventListener('click', function(){
    try{ navigator.clipboard.writeText(BASE); }catch(e){}
    line(o1, '相机地址：' + BASE + '（已尝试复制）');
  });

  /* ---------- ② 备份 ---------- */
  var backupText = '';
  document.getElementById('camBackup').addEventListener('click', async function(){
    o2.innerHTML = ''; this.disabled = true;
    var t0 = document.getElementById('camTarget') ? document.getElementById('camTarget').value : 'current';
    try{
      line(o2, '① 让相机准备数据：request_getmysetdata.cgi?mode=current');
      var r1 = await req('request_getmysetdata.cgi?mode=current');
      line(o2, '   HTTP ' + r1.status + ' ' + r1.text.slice(0, 200));
      var size = NaN, tries = 0, ready = false;
      while(tries++ < 15 && !ready){
        await sleep(400);
        var r2 = await req('get_mysetbackupstate.cgi');
        line(o2, '② 状态 ' + tries + '：HTTP ' + r2.status + ' ' + r2.text.slice(0, 120));
        if(/1|ready|complete|finish|done/i.test(r2.text)) ready = true;
      }
      var r3 = await req('get_mysetdatasize.cgi?kind=current');
      line(o2, '③ 数据大小：HTTP ' + r3.status + ' ' + r3.text.slice(0, 200));
      size = sizeFrom(r3.text);
      if(!isNaN(size) && size > 0){
        var parts = [], off = 0, guard = 0;
        var CHUNK = 20000;
        while(off < size && guard++ < 400){
          var n = Math.min(CHUNK, size - off);
          var r4 = await req('get_partialmysetdata.cgi?kind=current&offset=' + off + '&size=' + n);
          if(r4.status !== 200){ line(o2, '   第 ' + guard + ' 块 HTTP ' + r4.status, 'err'); break; }
          parts.push(r4.text); off += n;
        }
        backupText = parts.join('');
        line(o2, '④ 备份完成：声明 ' + size + ' 字节，实收 ' + backupText.length + ' 字符', 'ok');
        line(o2, '前 400 字符预览：' + backupText.slice(0, 400));
        document.getElementById('camDl').disabled = false;
      } else {
        line(o2, '没读到数据大小——把上面的原始返回发我，我据此调整。', 'warn');
        backupText = '';
      }
    }catch(e){
      line(o2, '失败：' + e.message, 'err');
    }
    this.disabled = false;
  });

  document.getElementById('camDl').addEventListener('click', function(){
    if(!backupText) return;
    var blob = new Blob([backupText], {type:'text/plain'});
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'OM3-相机设置备份-' + new Date().toISOString().slice(0,16).replace(/[:T]/g,'-') + '.txt';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    line(o2, '已生成备份文件（在「下载」文件夹里）。', 'ok');
  });

  /* ---------- ③ 写入 ---------- */
  function currentSel(){
    var rec = REC[+document.getElementById('camRecipe').value] || REC[0];
    var slot = +document.getElementById('camSlot').value;
    var target = document.getElementById('camTarget').value;
    var model = document.getElementById('camModel').value.trim();
    return {rec:rec, slot:slot, target:target, model:model};
  }
  function refreshPreview(){
    var s = currentSel();
    if(!s.rec) return;
    document.getElementById('camPreview').textContent =
      '# ' + s.rec.n + '（' + s.rec.a + '）→ ' + s.target + ' · Color Profile 槽 ' + s.slot + '\n' +
      buildPayload(s.rec, s.slot, s.target, s.model || '<相机型号>');
  }
  ['camRecipe','camSlot','camTarget','camModel'].forEach(function(id){
    var el = document.getElementById(id);
    el.addEventListener('change', refreshPreview);
    el.addEventListener('input', refreshPreview);
  });

  document.getElementById('camWrite').addEventListener('click', async function(){
    var s = currentSel();
    if(!s.rec){ log('没选配方。','err'); return; }
    if(!s.model){ log('请先点 ① 检测相机（或手动填相机型号），型号要写进数据头部。','err'); return; }
    var text = buildPayload(s.rec, s.slot, s.target, s.model);
    var bytes = new TextEncoder().encode(text);
    if(!confirm('把「' + s.rec.n + '」写进 ' + s.target + ' 的 Color Profile 槽 ' + s.slot + '？\n\n共 ' + bytes.length + ' 字节。\n写入前请确认已经备份过（②）。')) return;
    this.disabled = true;
    log('===== 开始写入：' + s.rec.n + ' → ' + s.target + ' / 槽 ' + s.slot + '（' + bytes.length + ' 字节）');
    try{
      log('① 先自动备份一次…');
      try{
        var rb = await req('request_getmysetdata.cgi?mode=current');
        var rbs = await req('get_mysetdatasize.cgi?kind=current');
        log('   备份可用性：HTTP ' + rb.status + ' / ' + rbs.text.slice(0,80) + '（正式回滚用 ② 的完整备份）');
      }catch(e){ log('   自动备份跳过：' + e.message, 'warn'); }

      var r1 = await req('request_restoremysetdata.cgi?action=restore');
      log('② 进入恢复模式：HTTP ' + r1.status + ' ' + r1.text.slice(0,120), r1.status===200?'ok':'err');
      if(r1.status !== 200) throw new Error('相机拒绝进入恢复模式');

      var r2 = await req('set_mysetdatasize.cgi?size=' + bytes.length);
      log('③ 声明大小 ' + bytes.length + '：HTTP ' + r2.status + ' ' + r2.text.slice(0,120), r2.status===200?'ok':'err');
      if(r2.status !== 200) throw new Error('声明大小失败');

      var CH = 4096, off = 0, i = 0;
      while(off < bytes.length){
        var part = bytes.slice(off, Math.min(off + CH, bytes.length));
        var r3 = await req('send_partialmysetdata.cgi?offset=' + off + '&size=' + part.length,
                           {method:'POST', body:part, timeout:12000});
        i++;
        log('④ 上传第 ' + i + ' 块 offset=' + off + ' size=' + part.length + '：HTTP ' + r3.status +
            (r3.text ? ' ' + r3.text.slice(0,80) : ''), r3.status===200?'ok':'err');
        if(r3.status !== 200) throw new Error('第 ' + i + ' 块上传失败');
        off += part.length;
      }

      var okState = false;
      for(var t=0;t<20;t++){
        await sleep(500);
        var r4 = await req('get_mysetrestorestate.cgi');
        log('⑤ 进度 ' + (t+1) + '：HTTP ' + r4.status + ' ' + r4.text.slice(0,120));
        if(r4.status === 200 && /(^|[^0-9])1([^0-9]|$)|ok|finish|complete|done/i.test(r4.text)){ okState = true; break; }
      }
      log(okState ? '⑥ 相机报告写入完成。' : '⑥ 没读到明确的完成状态——请到相机上确认。', okState?'ok':'warn');

      if(document.getElementById('camReboot').checked){
        var r5 = await req('exec_reboot.cgi');
        log('⑦ 已请求相机重启：HTTP ' + r5.status, r5.status===200?'ok':'warn');
      }
      log('完成。到相机上：Creative Dial 转到 COLOR → OK 键调出超级控制面板 → 找到 Color Profile 槽 ' + s.slot + ' 看是不是这个配方。','ok');
    }catch(e){
      log('中断：' + e.message, 'err');
      log('如果相机状态不对：用官方 OM Image Share 的「恢复设置」，或用 ② 的备份找我回滚。','warn');
    }
    this.disabled = false;
  });

  /* 配方下拉：优化版那 21 个排前面 */
  var sel = document.getElementById('camRecipe');
  function fill(){
    var o = [], i;
    sel.innerHTML = '';
    var g1 = document.createElement('optgroup'); g1.label = '优化版里用到的（' + window.__OM3OPT__.length + '）';
    var g2 = document.createElement('optgroup'); g2.label = '全部配方（' + REC.length + '）';
    var opt = window.__OM3OPT__;
    for(i=0;i<REC.length;i++){
      var r = REC[i];
      var op = document.createElement('option');
      op.value = i;
      op.textContent = r.n + ' · ' + r.a + (r.t === 'MONO' ? '（黑白）' : '');
      (opt.indexOf(r.slug) >= 0 ? g1 : g2).appendChild(op);
    }
    sel.appendChild(g1); sel.appendChild(g2);
    sel.value = '0';
    refreshPreview();
  }
  fill();
})();
'''

# ---------------------------------------------------------------- 注入
# 数据放在 IDX 脚本之前（同一段 script 里需要 window 变量先有）
DATA = ('<script>window.__OM3RECIPES__=' + json.dumps(RECIPES, ensure_ascii=False, separators=(',', ':')) +
        ';window.__OM3OPT__=' + json.dumps(sorted(opt), ensure_ascii=False, separators=(',', ':')) + ';</script>\n')

h = h.replace('<div id="paneC" class="pane hide">', DATA + PANE + '<div id="paneC" class="pane hide">', 1)
assert 'id="paneD"' in h

# CSS 塞进第一个 </style>
i = h.find('</style>')
assert i > 0
h = h[:i] + CSS + h[i:]

# 页签切换要认识 paneD（这段监听器在 app_extra 脚本里，同时负责隐藏目录按钮）
OLD_PANE = """    var p = b.getAttribute('data-p');
    var c = document.getElementById('paneC');
    var tc = document.getElementById('tocbtn');
    if (c) c.classList.toggle('hide', p !== 'C');
    if (tc) tc.style.display = (p === 'C') ? 'none' : '';"""
assert h.count(OLD_PANE) == 1, h.count(OLD_PANE)
h = h.replace(OLD_PANE, """    var p = b.getAttribute('data-p');
    var c = document.getElementById('paneC');
    var d4 = document.getElementById('paneD');
    var tc = document.getElementById('tocbtn');
    if (c) c.classList.toggle('hide', p !== 'C');
    if (d4) d4.classList.toggle('hide', p !== 'D');
    if (tc) tc.style.display = (p === 'C' || p === 'D') ? 'none' : '';""", 1)

# JS 放到页面最后（在 app_extra 脚本之后，保证 DOM 就绪）
j = h.rfind('</body>')
h = h[:j] + '<script>' + JS + '</script>\n' + h[j:]

open(P, 'w', encoding='utf-8', newline='').write(h)
print('已加入「导入相机」页，base.html %.1f KB' % (len(h.encode('utf-8')) / 1024))
