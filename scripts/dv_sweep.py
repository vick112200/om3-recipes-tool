# -*- coding: utf-8 -*-
"""全量运行时巡检（app 模式）：
  ① 每个页签/子页签切过去后，**是否真的可见、有没有内容**（严格可见性判定）
  ② 逐个点按钮，记录**每一步新增的报错**（带步骤名，能定位到是哪个按钮）
  ③ 统计 $() 缺元素次数 / 监听器数量 / 定时器数量
用法：python scripts/dv_sweep.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()

# 在被测页面最前面装：app 标记（必须！否则主模块直接 return，全是假象）+ 错误记录 + 监听器计数
head = ("<script>window.__OM3_APP__=1;window.__sweepErr=[];window.__sweepStep='(load)';window.__warns=[];"
        "(function(){var w=console.warn;console.warn=function(){try{window.__warns.push(Array.prototype.join.call(arguments,' '));}catch(e){}return w.apply(console,arguments);};})();"
        "window.addEventListener('error',function(e){window.__sweepErr.push(window.__sweepStep+' :: '+String(e.message));});"
        "window.addEventListener('unhandledrejection',function(e){window.__sweepErr.push(window.__sweepStep+' :: REJ '+String(e.reason));});"
        "window.__listeners=0;(function(){var a=EventTarget.prototype.addEventListener;"
        "EventTarget.prototype.addEventListener=function(){window.__listeners++;return a.apply(this,arguments);};})();"
        "</script>")

JS = r"""
setTimeout(function(){
  var o = [], errs = window.__sweepErr;
  function step(s){ window.__sweepStep = s; }
  function errNow(){ return errs.length; }
  function vis(el){
    if(!el) return false;
    if(el.classList && el.classList.contains('hide')) return false;
    var s = getComputedStyle(el);
    return s.display !== 'none' && s.visibility !== 'hidden' && el.offsetHeight > 0;
  }
  function info(id){
    var e = document.getElementById(id);
    if(!e) return id + '=不存在!';
    return id + '=' + (vis(e) ? '可见' : '不可见') + '(高' + e.offsetHeight
         + ',字' + (e.textContent||'').replace(/\s+/g,'').length + ')';
  }
  /* 给个测试方案，才能验「我的配方」渲染 */
  try{ localStorage.setItem('om3sets', JSON.stringify([
    {id:'s1',name:'测试方案甲',desc:'描述A',from:'myset1',camera:'OM-3',
     slots:{1:{vivid:[1,2,3,0,0,0,0,0,0,0,0,0],raw:{'MODE_COLOR_CREATOR_2_VIVID_SET1_1':'MODE_STEP_P1'},used:3},2:null,3:null,4:null}},
    {id:'s2',name:'测试方案乙',desc:'描述B',from:'myset2',camera:'OM-3',
     slots:{1:null,2:null,3:null,4:null}}
  ])); }catch(e){}
  o.push('诊断：__OM3_APP__=' + window.__OM3_APP__
         + '  __om3mpInit=' + (typeof window.__om3mpInit)
         + '  __om3mpRender=' + (typeof window.__om3mpRender)
         + '  #camOut3存在=' + !!document.getElementById('camOut3')
         + '  全篇「已就绪」出现=' + ((document.body.textContent||'').match(/「我的配方」已就绪/g)||[]).length + ' 次');

  var tabs = [
    ['内置配方(顶部 data-p=A)', "document.querySelector('.tabs.mod button[data-p=\"A\"]')"],
    ['优化版(子页签 B)',        "document.querySelector('.tabs.mod button[data-p=\"B\"]')"],
    ['场景对比(子页签 C)',      "document.querySelector('.tabs.mod button[data-p=\"C\"]')"],
    ['我的配方(顶部 tabMine)',  "document.getElementById('tabMine')"],
    ['连接相机(顶部 tabCam)',   "document.getElementById('tabCam')"]
  ];
  var i = 0;
  function nextTab(){
    if(i >= tabs.length){
      o.push('--- 收尾统计 ---');
      try{
        var raw = localStorage.getItem('om3sets') || '';
        var n2 = 0; try{ n2 = JSON.parse(raw).length; }catch(e){ n2 = -1; }
        o.push('localStorage om3sets: 字节=' + raw.length + ' 套数=' + n2);
      }catch(e){ o.push('读 localStorage 失败:' + e.message); }
      o.push('$() 缺元素次数 __om3miss=' + (window.__om3miss || 0));
      o.push('om3err 内部计数 __om3errs=' + (window.__om3errs || 0));
      o.push('addEventListener 绑定总数=' + window.__listeners);
      o.push('累计报错=' + errs.length);
      for(var k=0;k<errs.length;k++) o.push('   ERR: ' + errs[k]);
      var lb = document.getElementById('camOut3');
      o.push('--- 相机日志尾 ---');
      o.push(lb ? (lb.textContent||'').replace(/\s+/g,' ').slice(-300) : '(无)');
      var uniq = {}, miss = [];
      for(var w2 = 0; w2 < window.__warns.length; w2++){
        var m2 = /缺元素 #([^ \n]+)/.exec(window.__warns[w2]);
        if(m2 && !uniq[m2[1]]){ uniq[m2[1]] = 1; miss.push(m2[1]); }
      }
      o.push('--- 缺元素的 id（去重）---');
      o.push(JSON.stringify(miss));
      var d = document.createElement('pre'); d.id='DBGOUT'; d.textContent = o.join('\n');
      document.body.appendChild(d);
      return;
    }
    var name = tabs[i][0], sel = tabs[i][1]; i++;
    function initRuns(){
      var lb = document.getElementById('camOut3');
      var t = lb ? (lb.textContent||'') : '';
      return (t.match(/「我的配方」已就绪/g) || []).length;
    }
    step('切到 ' + name);
    var before = errNow();
    try{ var b = eval(sel); if(b) b.click(); else o.push('!! 找不到页签 ' + name); }
    catch(e){ o.push('!! 点页签异常 ' + name + ' : ' + e.message); }
    setTimeout(function(){
      var paneOf = {
        '内置配方(顶部 data-p=A)':'paneA', '优化版(子页签 B)':'paneB',
        '场景对比(子页签 C)':'paneC', '我的配方(顶部 tabMine)':'paneE',
        '连接相机(顶部 tabCam)':'paneD'
      };
      var pid = paneOf[name];
      o.push(name + ' → ' + info(pid) + '  新增报错=' + (errNow()-before)
             + '  mpInit已跑=' + initRuns() + '次');
      if(pid === 'paneE') o.push('   ' + info('mpList') + ' 方案条目数=' +
        (document.getElementById('mpList') ? document.getElementById('mpList').querySelectorAll('.mpitem').length : -1));
      if(pid === 'paneD') o.push('   底栏置灰数=' + document.querySelectorAll('#barD button.dis').length
        + ' / 4（未连接时应为 3）');
      nextTab();
    }, 700);
  }
  nextTab();
}, 2800);
"""
tail = '<script>' + JS + '</script>'

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_sweep.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\osweep'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=20000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=220)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
