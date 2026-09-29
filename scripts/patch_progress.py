# -*- coding: utf-8 -*-
"""① 运行时反馈：顶部"任务条"（正在执行什么、进度 n/N、已用秒数、完成/失败）
   ② 相机档案：把学到的档位/mode/大小/槽位占用按序列号存起来，换机时可复用/重学
   ③ 菜单加「查看相机档案」
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# ---------- CSS ----------
k = h.find('</style>')
h = h[:k] + """
/* ---------- 任务条：一眼看出"在跑步、跑到哪、跑完没" ---------- */
.camrun{display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:8px;background:#1b2130;border:1px solid #2b3a55;color:#cfe0ff;font-size:12.5px;margin:6px 0}
.camrun.busy{border-color:#3f6ea8;background:#16233a}
.camrun.ok{border-color:#2f7d4f;background:#16261c;color:#bdf0cf}
.camrun.err{border-color:#8a3b3b;background:#2a1717;color:#ffc9c9}
.camrun .spin{width:12px;height:12px;border:2px solid #4a7ac0;border-top-color:transparent;border-radius:50%;animation:om3spin .8s linear infinite;flex:none}
@keyframes om3spin{to{transform:rotate(360deg)}}
.camrun .t{margin-left:auto;opacity:.75;flex:none}
""" + h[k:]

# ---------- 任务条 DOM（放在 pane D 顶部） ----------
old_top = '<div class="camhd">① 连接相机（扫码或手动）</div>'
assert h.count(old_top) == 1
h = h.replace(old_top, '<div class="camrun hide" id="camRun"><span class="spin"></span><span id="camRunTxt">待机</span><span class="t" id="camRunTime"></span></div>\n  ' + old_top, 1)

# ---------- runTask 包装 + 档案存取 ----------
anchor = "  /* ============ 档位映射（只读）"
assert h.count(anchor) == 1
FUNC = '''  /* ============ 任务条 + 相机档案 ============ */
  var _run = { busy: false, t0: 0, timer: 0 };
  function runBanner(state, txt){
    var el = document.getElementById('camRun'), tx = document.getElementById('camRunTxt'), tm = document.getElementById('camRunTime');
    if(!el) return;
    el.classList.remove('hide', 'busy', 'ok', 'err');
    el.classList.add(state);
    tx.textContent = txt;
    var sp = el.querySelector('.spin');
    if(sp) sp.style.display = (state === 'busy') ? '' : 'none';
  }
  function runTick(){
    var tm = document.getElementById('camRunTime');
    if(tm && _run.t0) tm.textContent = '已用 ' + Math.round((Date.now() - _run.t0) / 1000) + ' 秒';
  }
  /** 把长任务包起来：顶部显示"正在执行什么 + 进度 + 用时"，结束显示成功/失败 */
  async function runTask(label, fn){
    if(_run.busy){ toastMsg('还有一个任务在跑，等它跑完'); return; }
    _run.busy = true; _run.t0 = Date.now();
    runBanner('busy', '正在执行：' + label);
    clearInterval(_run.timer); _run.timer = setInterval(runTick, 1000); runTick();
    var ok = true, err = '';
    try{ await fn(function(step, total){ runBanner('busy', '正在执行：' + label + '（' + step + '/' + total + '）'); }); }
    catch(e){ ok = false; err = e && e.message ? e.message : String(e); }
    clearInterval(_run.timer);
    var sec = Math.round((Date.now() - _run.t0) / 1000);
    runBanner(ok ? 'ok' : 'err', (ok ? '✅ 完成：' : '❌ 失败：') + label + '（用时 ' + sec + ' 秒）' + (ok ? '' : '　' + err));
    _run.busy = false; _run.t0 = 0;
    return ok;
  }
  window.__om3runTask = runTask;

  /* ---- 相机档案：按序列号存 ---- */
  var PKEY = 'om3profile';
  function profAll(){ try{ return JSON.parse(localStorage.getItem(PKEY) || '{}'); }catch(e){ return {}; } }
  function profGet(serial){ return profAll()[serial] || null; }
  function profSave(serial, obj){ var a = profAll(); a[serial] = obj; try{ localStorage.setItem(PKEY, JSON.stringify(a)); }catch(e){} }
  function profShow(){
    showStep(3);
    var a = profAll(), ks = Object.keys(a);
    if(!ks.length){ log('还没有相机档案：先在 ☰ 里跑一次「档位映射诊断（只读）」。', 'warn'); return; }
    for(var i=0;i<ks.length;i++){
      var p = a[ks[i]];
      log('===== 相机 ' + p.model + '（序列 ' + ks[i] + '）　学习于 ' + p.learned);
      for(var j=0;j<(p.modes || []).length;j++){
        var m = p.modes[j];
        log('　' + m.mode + '（' + m.name + '）　' + m.size + ' 字节　槽：' + (m.slots || []).join(' / '));
      }
    }
    log('===== 档案结束', 'ok');
  }
  window.__om3profShow = profShow;

'''
h = h.replace(anchor, FUNC + anchor, 1)

# ---------- 菜单：查看档案 ----------
old = '      <button type="button" data-act="map">档位映射诊断（只读）</button>'
assert h.count(old) == 1
h = h.replace(old, old + '\n      <button type="button" data-act="prof">查看相机档案</button>', 1)
old_a = "      else if(a === 'map'){ mapModes(); }"
assert h.count(old_a) == 1
h = h.replace(old_a, old_a + "\n      else if(a === 'prof'){ profShow(); }", 1)

# ---------- mapModes：包任务条 + 存档案 + 进度 ----------
old_call = "      else if(a === 'map'){ mapModes(); }"
h = h.replace(old_call, "      else if(a === 'map'){ runTask('档位映射诊断', function(pg){ return mapModes(pg); }); }", 1)
old_sig = "  async function mapModes(){"
assert h.count(old_sig) == 1
h = h.replace(old_sig, "  async function mapModes(pg){\n    pg = pg || function(){};\n    var _learned = { model: '', serial: '', learned: new Date().toLocaleString('zh-CN'), modes: [] };", 1)
old_loop = "    for(var k=0;k<modes.length;k++){\n      var X = modes[k];"
assert h.count(old_loop) == 1
h = h.replace(old_loop, "    for(var k=0;k<modes.length;k++){\n      var X = modes[k];\n      try{ pg(k + 1, modes.length); }catch(e){}", 1)
# 记名字与槽位（解析 <mysetname>…</mysetname>）
old_nm = "          nm = (rn.text || '').replace(/\\s+/g, ' ').slice(0, 60);"
assert h.count(old_nm) == 1
h = h.replace(old_nm, "          nm = (rn.text || '').replace(/\\s+/g, ' ').slice(0, 60);\n          var mnm = (rn.text || '').match(/<mysetname>([^<]*)<\\/mysetname>/i);\n          if(mnm) nm = mnm[1];", 1)
old_log = "        log('　　 槽位占用：' + om3slotSummary(body));"
assert h.count(old_log) == 1
h = h.replace(old_log, """        log('　　 槽位占用：' + om3slotSummary(body));
        _learned.modes.push({ mode: X, name: nm, size: sz, slots: om3slotSummary(body).split('｜') });
        var hi = (head.split(',') || []);
        if(hi.length > 1){ _learned.model = hi[1]; _learned.serial = hi[3] || ''; }""", 1)
old_end = "    log('===== 映射诊断结束。把这一段复制给我（含 ★ 行和\"槽位占用\"）。', 'ok');"
assert h.count(old_end) == 1
h = h.replace(old_end, """    if(_learned.serial){
      profSave(_learned.serial, _learned);
      log('⑤ 已保存相机档案：' + _learned.model + '（序列 ' + _learned.serial + '），共 ' + _learned.modes.length + ' 份 my-set', 'ok');
      log('　　以后换电脑/重装也能在 ☰ →「查看相机档案」里看到；换一台新相机就再跑一次这个诊断即可。', 'ok');
    }
    log('===== 映射诊断结束（跑完了）。把这一段复制给我即可。', 'ok');""", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('已加：任务条 + 相机档案 + 菜单项（+%d 字节）' % (len(h) - n0))
