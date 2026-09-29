# -*- coding: utf-8 -*-
"""第 69 轮：连接流程「弹窗 / 浮层」排隐患（见 SPEC-round69.md §2 审计清单）。

需求方 2026-09-28：「弹窗之类的用的安卓组件样式都很丑，而且有的弹窗关不掉……把隐患都排除」。

改前 → 改后：
  ① `window.prompt`（WebView 自带输入框，样式不受我们控制、有的机型还会被拦）→ 自绘 `om3Ask`
  ② `om3Ask` 并发调用会覆盖前一次的按钮处理器 → 前一个 Promise **永挂**（等它的流程永远卡住）→ 串行化 + done 重入保护
  ③ 返回键/Esc 不管浮层：弹窗开着按返回 = 直接退出 App → 统一"先收浮层"（弹窗=取消 / 扫码=关 / 任务=收起 / ☰=关）
  ④ 任务弹窗：运行中只有「后台运行」（用户看不懂）、点框外没反应、任务永不结束时无法收尾 → 改文案 + 点框外=收起 + **总超时 180 秒** + 迟到返回不再改写界面
  ⑤ 任务气泡只能点开、不能清掉 → 加 ✕（清气泡 ≠ 取消任务）
  ⑥ 直连路径没处理原生 `dialog:` 返回码 → 系统「添加网络」页面已经打开却显示成「连接失败」→ 补分支说清楚

规矩：幂等（标记 `r69：弹窗审计`）+ 每处锚点命中恰好 1 次 + **不新增 id**（新加的东西只用 class / data 属性）。

用法：python scripts/gen_r69.py [--check]
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
MARK = 'r69：弹窗审计'
EDITS = []


def E(label, old, new):
    EDITS.append((label, old, new))


# ---------------------------------------------------------------- ① prompt → 自绘
E('① BLE 结果码对照：window.prompt → 自绘 om3Ask',
  """      var v = window.prompt('输入相机回的码（十进制）：', '34');
      if(v === null || String(v).trim() === '') return;
      window.__om3bleCodeAll(String(v).trim());""",
  """      /* r69：原来是 window.prompt —— 那是**安卓 WebView 自带**的输入框：样式不受我们控制（需求方 2026-09-28 说的
         "安卓组件样式很丑"），而且有的机型/版本会把它拦掉（直接回 null）→ 点了像"没反应"。
         换成全站同一个自绘弹窗（om3Ask）。 */
      if(!window.__om3ask){ bleRec('这个版本的弹窗不能用（缺 om3Ask）→ 直接点「结果码」那一列也能看到对照', 'warn'); return; }
      window.__om3ask({
        title: '结果码对照',
        body: '把相机回的**十进制**数字填进来（例如 34）。连接监听 / 检测监听两套表会一起给你。',
        fields: [ { label: '码（十进制）', value: '34', numeric: true } ],
        okText: '查一下'
      }).then(function(v){
        if(v === null || String(v).trim() === '') return;
        window.__om3bleCodeAll(String(v).trim());
      });""")

# ---------------------------------------------------------------- ② om3Ask 串行化
E('② om3Ask：并发调用时先把前一个按"取消"收掉 + done() 重入保护',
  """      var mask = $('omask');
      var hasInput = false;   /* 有输入（fields 或 choices）→ 取消时 resolve(null)，否则 resolve(false) */
      if(!mask){ resolve((opt.fields || opt.choices) ? null : false); return; }""",
  """      var mask = $('omask');
      var hasInput = false;   /* 有输入（fields 或 choices）→ 取消时 resolve(null)，否则 resolve(false) */
      if(!mask){ resolve((opt.fields || opt.choices) ? null : false); return; }
      /* r69：同一时刻**只允许一个**自绘弹窗。以前第二次调用会把第一次的 ok/cancel/mask 处理器**覆盖**掉，
         第一个 Promise 就永远挂着 —— 等它的流程（例如"连接相机"等密码）会一直卡住，界面上却什么都没有。
         现在：新弹窗先把旧的按"取消"收掉（旧调用方拿到 null/false，能正常往下走）。 */
      if(_askCancel){ try{ _askCancel(); }catch(e){ om3err(e, "silent"); } }""")

E('② om3Ask：登记/注销"当前开着的弹窗"+ done 只收一次',
  """      function done(val){
        mask.classList.add('hide'); mask.style.display = 'none';
        ok.onclick = null; cancel.onclick = null; mask.onclick = null;
        resolve(val);
      }""",
  """      function done(val){
        if(doneOnce) return;                       /* r69：只收一次（遮罩与按钮同时点也不会重复 resolve） */
        doneOnce = true;
        _askCancel = null;                         /* r69：注销（下一个弹窗不会再收我） */
        mask.classList.add('hide'); mask.style.display = 'none';
        ok.onclick = null; cancel.onclick = null; mask.onclick = null;
        resolve(val);
      }
      /* r69：登记"当前开着的弹窗"（点它 = 等价于点「取消」） */
      _askCancel = function(){ done(hasInput ? null : false); };""")

E('② om3Ask：声明 doneOnce / _askCancel 与对外出口',
  """  function om3Ask(opt){
    opt = opt || {};
    return new Promise(function(resolve){""",
  """  /* r69：当前开着的自绘弹窗的"取消"函数（返回键 / Esc / 并发调用都用它收；null = 没开着） */
  var _askCancel = null;
  window.__om3askCancel = function(){ if(_askCancel){ try{ _askCancel(); }catch(e){ om3err(e, "silent"); } } };
  function om3Ask(opt){
    opt = opt || {};
    return new Promise(function(resolve){
      var doneOnce = false;""")

E('② om3Ask：数值字段给数字键盘（inputmode）',
  """        }else{
          el = document.createElement(f.multiline ? 'textarea' : 'input');
          if(!f.multiline) el.type = 'text';
          el.value = f.value || '';
        }""",
  """        }else{
          el = document.createElement(f.multiline ? 'textarea' : 'input');
          if(!f.multiline) el.type = 'text';
          /* r69：数值字段给手机数字键盘（原来是普通文本键盘） */
          if(f.numeric) el.setAttribute('inputmode', 'numeric');
          el.value = f.value || '';
        }""")

# ---------------------------------------------------------------- ③ 浮层统一收口（返回键 / Esc）
E('③ 新增 __om3escClose（浮层统一收口，返回键与 Esc 共用）',
  """    else { taskModalShow(true); taskPaint(); }
  }, true);""",
  """    else { taskModalShow(true); taskPaint(); }
  }, true);
  /* r69：点任务弹窗的**框外**（遮罩）= 收起 —— 用户直觉是"点外面就能关"，原来点外面毫无反应。 */
  document.addEventListener('click', function(ev){
    var t = ev.target;
    if(t && t.id === 'taskMask'){ try{ window.__om3taskBg(); }catch(e){ om3err(e, "silent"); } }
  }, true);
  /* r69：把"浮层"统一收掉（**返回键与 Esc 共用这一份逻辑**，别再各写一套）。
     顺序 = 从最上面的模态往下：自绘弹窗 → 扫码 → 任务 → ☰菜单。收掉一个就返回 true。
     不这么做的话：弹窗开着按返回键 → 页面不管 → WebView 不能 goBack → **直接退出 App**（用户以为"关不掉"）。 */
  window.__om3escClose = function(){
    var om = document.getElementById('omask');
    if(om && !om.classList.contains('hide')){ window.__om3askCancel(); return true; }
    var sm = document.getElementById('scanMask');
    if(sm && !sm.classList.contains('hide')){ try{ stopScan(); }catch(e){ om3err(e, "silent"); } return true; }
    var tm = document.getElementById('taskMask');
    if(tm && !tm.classList.contains('hide')){ try{ window.__om3taskBg(); }catch(e){ om3err(e, "silent"); } return true; }
    var md = document.getElementById('camMenuDrop');
    if(md && !md.classList.contains('hide')){ md.classList.add('hide'); return true; }
    return false;
  };""")

E('③ 返回键：先收浮层（__handleBack 第 1 步）',
  """      // 1) 全屏看图开着 → 先关它
      if (lb && lb.classList.contains('on')) { closeLB(); return true; }""",
  """      // 0) r69：自绘弹窗 / 扫码浮层 / 任务弹窗 / ☰菜单 开着 → 先收掉它们
      //    （以前不管这些 → 弹窗开着按返回键会**直接退出 App**，用户的感觉就是"关不掉"）
      if (window.__om3escClose && window.__om3escClose()) return true;
      // 1) 全屏看图开着 → 先关它
      if (lb && lb.classList.contains('on')) { closeLB(); return true; }""")

E('③ Esc 键：先收浮层，再关目录',
  " document.addEventListener('keydown',function(e){if(e.key==='Escape')close();});",
  " document.addEventListener('keydown',function(e){if(e.key!=='Escape')return;/* r69：Esc 先收浮层（弹窗=取消…），没有再关目录 */try{if(window.__om3escClose&&window.__om3escClose())return;}catch(e2){}close();});")

# ---------------------------------------------------------------- ④ 任务弹窗：文案 / 点框外 / 超时
E('④ 任务弹窗：加一行说明（点框外或"收起"都会收，任务照旧跑）',
  """    <div class="tbtns">
      <button type="button" id="taskBg">后台运行</button>""",
  """    <div style="color:#9aa3b2;font-size:12px;line-height:1.6;margin:2px 0 8px">
      不想看这个框？<b>点框外面</b>或下面「收起到后台」都会收起来 —— <b>任务照旧在跑</b>（跑完右下角气泡会告诉你）。
    </div>
    <div class="tbtns">
      <button type="button" id="taskBg">收起到后台（任务继续跑）</button>""")

E('④ 任务弹窗：运行中也把「关闭」放出来（点了=收起，不再"只有后台运行一个按钮"）',
  """    var bg = taskEl('taskBg'), cl = taskEl('taskClose');
    if(bg) bg.style.display = (_run.ok === null) ? '' : 'none';
    /* 「关闭」按钮的标记里带 hide 类（class="primary hide"），光改 inline display 是没用的
       —— 类规则照样把它藏住 → 任务跑完后\"关闭\"永远不出现。必须改类。 */
    if(cl) cl.classList.toggle('hide', _run.ok === null);""",
  """    var bg = taskEl('taskBg'), cl = taskEl('taskClose');
    if(bg) bg.style.display = (_run.ok === null) ? '' : 'none';
    /* 「关闭」按钮的标记里带 hide 类（class="primary hide"），光改 inline display 是没用的
       —— 类规则照样把它藏住 → 任务跑完后\"关闭\"永远不出现。必须改类。
       r69：**运行中也不再藏它** —— 用户看到"只有一个后台运行"会以为关不掉；
       运行中点它 = 收起（和「收起到后台」一样），任务照旧在跑。 */
    if(cl){
      cl.classList.remove('hide');
      cl.textContent = (_run.ok === null) ? '收起（任务继续跑）' : '关闭';
    }""")

E('④ 任务：总超时（默认 180 秒，可用 window.__om3taskMaxMs 覆盖）+ 迟到返回不再改写界面',
  """  async function runTask(label, fn){
    if(_run.busy){ toastMsg('还有一个任务在跑：' + _run.label + '（点右下角气泡看进度）'); taskModalShow(true); return false; }
    _run.busy = true; _run.t0 = Date.now(); _run.label = label; _run.last = '准备中…'; _run.ok = null;
    taskModalShow(true); taskPillHide(); taskPaint();""",
  """  /* r69：任务**总超时** —— 等系统回调 / 等相机应答都可能一直不回来，界面必须能自己收尾
     （不然弹窗+气泡永远转着，用户只能杀 App）。可用 window.__om3taskMaxMs 覆盖（探针就靠它测）。 */
  var TASK_MAX_MS = 180000;
  function taskMaxMs(){ try{ return Number(window.__om3taskMaxMs) || TASK_MAX_MS; }catch(e){ return TASK_MAX_MS; } }
  async function runTask(label, fn){
    if(_run.busy){ toastMsg('还有一个任务在跑：' + _run.label + '（点右下角气泡看进度）'); taskModalShow(true); return false; }
    _run.busy = true; _run.t0 = Date.now(); _run.label = label; _run.last = '准备中…'; _run.ok = null;
    _run.timedOut = false;
    taskModalShow(true); taskPillHide(); taskPaint();
    clearTimeout(_run.to);
    _run.to = setTimeout(function(){
      if(_run.ok !== null) return;                  /* 已经结束了 */
      _run.timedOut = true; _run.ok = false;
      _run.last = '超时未完成（已等 ' + Math.round(taskMaxMs() / 1000) + ' 秒）—— 相机可能没应答或没连上。'
                + '点「关闭」收起，检查连接后重试一次。';
      clearInterval(_run.timer);
      taskPaint();
      taskPill('err', '⏱ 超时未完成：' + _run.label + '（点这里看详情）');
      _run.busy = false; _run.t0 = 0;
      try{ delete _run.to; }catch(e){ _run.to = 0; }
      try{ log('[任务] 超时收尾：' + _run.label + '（' + Math.round(taskMaxMs() / 1000) + ' 秒）—— 界面已经可以操作，任务如果后来回来了只会写日志。', 'warn'); }catch(e2){}
    }, taskMaxMs());""")

E('④ 任务：await 回来先清超时；若是"超时后迟到"，只写日志不改界面',
  """    catch(e){ ok = false; msg = (e && e.message) ? e.message : String(e); }
    clearInterval(_run.timer);
    _run.ok = ok;""",
  """    catch(e){ ok = false; msg = (e && e.message) ? e.message : String(e); }
    clearTimeout(_run.to); _run.to = 0;
    if(_run.timedOut){                              /* r69：已经按超时收过尾了 —— 只留日志，别再把界面翻回来 */
      try{ log('[任务] 超时后才返回（' + (ok ? '成功' : '失败：' + msg) + '）：' + label, 'warn'); }catch(e3){}
      _run.timedOut = false;
      return false;
    }
    clearInterval(_run.timer);
    _run.ok = ok;""")

E('④ _run 多两个字段（超时句柄 / 是否已超时收尾）',
  "  var _run = { busy: false, t0: 0, timer: 0, label: '', last: '', ok: null };",
  "  var _run = { busy: false, t0: 0, timer: 0, to: 0, timedOut: false, label: '', last: '', ok: null };")

E('④ 任务：导出"收起 / 关闭"两个动作（返回键、遮罩点击、按钮共用一份实现）',
  "  window.__om3runTask = runTask;",
  """  window.__om3runTask = runTask;
  /* r69：这两个动作**只写一份**（返回键 / 点遮罩 / 点按钮都调它们）—— 省得以后改了按钮忘了别处 */
  window.__om3taskBg = function(){ taskModalShow(false); taskPill(null, _run.last.slice(0, 40) || '任务运行中'); };
  window.__om3taskClose = function(){ taskModalShow(false); taskPillHide(); };""")

E('④ 任务按钮：走导出的函数（不再各写一遍）',
  """    if(hit === 'taskBg'){ taskModalShow(false); taskPill(null, _run.last.slice(0, 40) || '任务运行中'); }
    else if(hit === 'taskClose'){ taskModalShow(false); taskPillHide(); }
    else { taskModalShow(true); taskPaint(); }""",
  """    if(hit === 'taskBg'){ window.__om3taskBg(); }
    else if(hit === 'taskClose'){ window.__om3taskClose(); }   /* r69：运行中点它 = 收起（任务继续跑） */
    else if(hit === '@clear'){ taskPillHide(); }              /* r69：气泡上的 ✕ = 清掉气泡（不取消任务） */
    else { taskModalShow(true); taskPaint(); }""")

# ---------------------------------------------------------------- ⑤ 气泡加 ✕
E('⑤ 气泡：加一个 ✕（清掉气泡；任务本身不受影响）',
  """<button type="button" id="taskPill" class="taskpill hide">⟳ <span id="taskPillTxt">任务运行中</span></button>""",
  """<button type="button" id="taskPill" class="taskpill hide">⟳ <span id="taskPillTxt">任务运行中</span><span data-task="clear" title="清掉这个气泡（任务不受影响）" style="margin-left:7px;opacity:.8;font-weight:700">✕</span></button>""")

E('⑤ 气泡 ✕ 的点击识别（data-task=clear，不用新增 id）',
  """    while(t && t !== document){
      if(t.id === 'taskBg' || t.id === 'taskClose' || t.id === 'taskPill'){ hit = t.id; break; }
      t = t.parentNode;
    }""",
  """    while(t && t !== document){
      /* r69：气泡里的 ✕ 用 data-task 标记（不新增 id）—— 点它是"清掉气泡"，不是"打开弹窗" */
      if(t.getAttribute && t.getAttribute('data-task') === 'clear'){ hit = '@clear'; break; }
      if(t.id === 'taskBg' || t.id === 'taskClose' || t.id === 'taskPill'){ hit = t.id; break; }
      t = t.parentNode;
    }""")

# ---------------------------------------------------------------- ⑥ 直连的 dialog: 分支
E('⑥ 直连路径：补原生 `dialog:` 返回码的分支（系统页面已经打开了，别说成"连接失败"）',
  """      else if(r.indexOf('need:') === 0){ say('系统要求先给权限：' + r.slice(5) + '（到「设置 → 应用 → 权限」里允许后重试）', 'err'); }""",
  """      else if(r.indexOf('dialog') === 0){
        /* r69：原生在 requestNetwork 被系统拒时会**打开系统的「添加网络」页面**（返回 dialog:…）。
           以前这里落到最后那个 else → 显示「连接失败：dialog:…」，其实系统页面已经开了 —— 完全误导。 */
        say('系统那个「添加网络」页面已经打开了 —— 在里面点「连接 / 保存」，然后回到本 App 点「检测相机」确认。'
            + '（那是系统自己的页面，我们没法在 App 里重画。）', 'ok');
      }
      else if(r.indexOf('need:') === 0){ say('系统要求先给权限：' + r.slice(5) + '（到「设置 → 应用 → 权限」里允许后重试）', 'err'); }""")


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    if MARK in html:
        print('[r69] 已经是目标状态（页面里有 "%s"）—— 不重复改。' % MARK)
        return 0
    bad = []
    for label, old, new in EDITS:
        n = html.count(old)
        if n != 1:
            bad.append('%s：锚点命中 %d 次（要求 1 次）' % (label, n))
    if bad:
        print('[r69] ✗ 以下锚点不匹配，页面可能已被改过 —— **不写盘**：')
        for b in bad:
            print('   · ' + b)
        return 1
    if '--check' in sys.argv:
        print('[r69] --check：%d 处锚点都命中 1 次（未写盘）：' % len(EDITS))
        for label, old, new in EDITS:
            print('   · ' + label)
        return 0
    for label, old, new in EDITS:
        html = html.replace(old, new, 1)
    html = html.replace("  var _askCancel = null;",
                        "  var _askCancel = null;   /* %s */" % MARK, 1)
    assert MARK in html, '替换后标记不在页面里'
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(html)
    print('[r69] ✓ 已改 %d 处：原生弹窗换自绘 / 每个浮层都有"关"的路 / 任务加超时与可关闭 / dialog: 分支' % len(EDITS))
    before = io.open(os.path.join(ROOT, 'app', 'base.before_r69.html'), encoding='utf-8').read()
    print('[r69] 页面净增 %d 字节' % (len(html.encode('utf-8')) - len(before.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
