# -*- coding: utf-8 -*-
"""新的数据模型验收（用户 2026-09-23 要求）：

  方案(set) = 一个档位 + 用户自己起的名字（用「＋ 新建方案」创建）
  槽位(slot) = 放一条配方；**配方名成为槽位名**（不是方案名）

验：
  ① 列表页有「＋ 新建方案」；填名字+档位能创建出空方案（4 个空槽、档位是选的那个）
  ② 点配方卡「加入我的方案」→ 弹窗是**选已有方案 + 槽位 + 槽位名**（默认=配方名），
     而且**不会新建方案**
  ③ 选「方案2 · 槽3」→ 配方落进方案2的槽3；**方案2 的名字/档位没变**；槽3 名 = 配方名
  ④ 槽位已有东西时 → 先弹覆盖确认；取消则不覆盖
  ⑤ 一个方案都没有时 → 弹窗默认给「＋ 新建一个方案…」，建完继续填槽
  ⑥ 详情页「改这个槽的名字」只改槽名；「改名/描述」能改方案名+档位

用法：python scripts/dv_model.py
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
SRC = r'D:\workspace\om3-handbook'
src = open(SRC + r'\app\base.html', encoding='utf-8').read()
head = "<script>window.__OM3_APP__=1;</script>"

JS = r"""
setTimeout(function(){
  var o = [], fails = [];
  function ok(c, m){ o.push((c ? '  [OK ] ' : '  [FAIL] ') + m); if(!c) fails.push(m); }
  function sets(){ try{ return JSON.parse(localStorage.getItem('om3sets') || '[]'); }catch(e){ return []; } }
  function fields(){ return document.querySelectorAll('#ofields select, #ofields input, #ofields textarea'); }
  function opts(el){ return el ? [].map.call(el.options, function(x){ return x.value + ':' + (x.textContent || '').slice(0, 22); }) : []; }
  function done(){
    o.push('累计 js 报错=' + (window.__errs ? window.__errs.length : 0) + '  om3errs=' + (window.__om3errs || 0));
    o.push('--- 结果：' + (fails.length ? ('失败 ' + fails.length + ' 项') : '全部通过') + ' ---');
    var d = document.createElement('pre'); d.id = 'DBGOUT'; d.textContent = o.join('\n');
    document.body.appendChild(d);
  }
  function ask(vals, pick){   /* 填弹窗字段并确定；pick 可对下拉指定值 */
    var f = fields();
    if(pick) for(var i = 0; i < f.length; i++) if(pick[i] !== undefined && pick[i] !== null) f[i].value = String(pick[i]);
    if(vals) for(var j = 0; j < f.length && j < vals.length; j++) if(vals[j] !== null) f[j].value = vals[j];
    document.getElementById('ook').click();
  }

  /* ---------- ① 一个方案都没有时：加配方应先引导新建 ---------- */
  document.getElementById('tabMine').click();
  setTimeout(function(){
    var nb = document.getElementById('mpNewSet');
    ok(!!nb, '列表页有「＋ 新建方案」按钮');
    ok(/还没有方案/.test((document.getElementById('mpList') || {}).textContent || ''), '空态文案说明了先建方案');

    var card = document.querySelector('[id^="r-"]');
    var sb = card ? card.querySelector('.omsavebtn') : null;
    ok(!!sb, '配方卡上有「加入我的方案」');
    if(sb) sb.click();
    setTimeout(function(){
      var f = fields();
      ok(f.length === 3, '弹窗三项：方案 / 槽位 / 槽位名（实际 ' + f.length + '）');
      var o0 = opts(f[0]);
      o.push('    方案下拉：' + JSON.stringify(o0));
      ok(o0.length && o0[0].indexOf('__new__') === 0, '没有方案时默认给「＋ 新建一个方案…」');
      ok(String(f[2].value).length > 0, '槽位名默认填了配方名：' + JSON.stringify(f[2].value));
      var recipeName = f[2].value;
      /* 选"新建"，填名字+档位 */
      f[0].value = '__new__';
      document.getElementById('ook').click();
      setTimeout(function(){
        var f2 = fields();
        ok(f2.length === 2, '接着弹「新建方案」（名字 + 档位，实际 ' + f2.length + '）');
        if(f2.length >= 2){ f2[0].value = '人像三卷'; f2[1].value = 'myset2'; }
        document.getElementById('ook').click();
        setTimeout(function(){
          var a = sets();
          ok(a.length === 1, '建出 1 个方案（实际 ' + a.length + '）');
          var s = a[0];
          ok(s.name === '人像三卷', '方案名是**我自己起的**：' + JSON.stringify(s.name));
          ok(s.from === 'myset2', '方案档位是我选的 myset2：' + JSON.stringify(s.from));
          ok(s.slots[1] && s.slots[1].name === recipeName,
             '配方填进了槽1，且**槽位名 = 配方名**：' + JSON.stringify(s.slots[1] ? s.slots[1].name : null));
          ok(!s.slots[2] && !s.slots[3] && !s.slots[4], '其它 3 个槽还是空的');

          /* ---------- ②③ 有方案了：再加一条，应"选已有方案"且不新建 ---------- */
          document.getElementById('tabBuiltin').click();
          setTimeout(function(){
            var cards = document.querySelectorAll('[id^="r-"] .omsavebtn');
            var c2 = cards[1] || cards[0];
            c2.click();
            setTimeout(function(){
              var f3 = fields();
              var o3 = opts(f3[0]);
              o.push('    方案下拉（已有方案后）：' + JSON.stringify(o3));
              ok(o3.length === 2, '下拉 = 1 个已有方案 + 1 个「新建」（实际 ' + o3.length + '）');
              ok(o3[0].indexOf('0:人像三卷') === 0, '第一个选项就是已有方案「人像三卷」');
              ok(o3[0].indexOf('myset2') >= 0 || o3[0].indexOf('C2') >= 0, '选项里带上了档位：' + o3[0]);
              var nm2 = f3[2].value;
              f3[0].value = '0'; f3[1].value = '3';
              document.getElementById('ook').click();
              setTimeout(function(){
                var a2 = sets();
                ok(a2.length === 1, '★没有新建方案（仍是 1 个，实际 ' + a2.length + '）');
                ok(a2[0].name === '人像三卷' && a2[0].from === 'myset2', '方案名/档位都没被改');
                ok(a2[0].slots[3] && a2[0].slots[3].name === nm2, '第 2 条配方进了**同一个方案**的槽3，槽位名=' + JSON.stringify(a2[0].slots[3] ? a2[0].slots[3].name : null));

                /* ---------- ④ 覆盖确认 ---------- */
                var c3 = document.querySelectorAll('[id^="r-"] .omsavebtn')[2];
                c3.click();
                setTimeout(function(){
                  var f4 = fields();
                  f4[0].value = '0'; f4[1].value = '3';
                  document.getElementById('ook').click();
                  setTimeout(function(){
                    var t = (document.getElementById('otitle') || {}).textContent || '';
                    ok(/已经有东西/.test(t), '槽位已占用 → 弹覆盖确认（标题：' + JSON.stringify(t) + '）');
                    document.getElementById('ocancel').click();
                    setTimeout(function(){
                      var a3 = sets();
                      ok(a3[0].slots[3].name === nm2, '取消覆盖后槽3 内容没变：' + JSON.stringify(a3[0].slots[3].name));
                      /* ---------- ⑥ 详情页改名 ---------- */
                      document.getElementById('tabMine').click();
                      setTimeout(function(){
                        var it = document.querySelector('#mpList .mpitem');
                        if(it) it.click();
                        setTimeout(function(){
                          var ren = document.querySelectorAll('button[data-ren]');
                          o.push('    详情页改名按钮数=' + ren.length + '（有内容的槽数应=2）');
                          ok(ren.length === 2, '两个有内容的槽各有一个「改这个槽的名字」');
                          /* 方案名/档位编辑 */
                          var be = document.getElementById('mpEdit');
                          if(be){
                            be.click();
                            setTimeout(function(){
                              var f5 = fields();
                              ok(f5.length === 3, '「改名/描述」弹窗 = 方案名 + 档位 + 描述（实际 ' + f5.length + '）');
                              if(f5.length >= 2){ f5[0].value = '人像三卷（改名版）'; f5[1].value = 'myset4'; }
                              document.getElementById('ook').click();
                              setTimeout(function(){
                                var a4 = sets();
                                ok(a4[0].name === '人像三卷（改名版）' && a4[0].from === 'myset4',
                                   '方案名/档位改成功：' + JSON.stringify(a4[0].name + ' / ' + a4[0].from));
                                ok(a4[0].slots[3].name === nm2, '改方案不影响槽位名');
                                done();
                              }, 400);
                            }, 500);
                          } else { o.push('    ★没有 mpEdit'); done(); }
                        }, 600);
                      }, 600);
                    }, 400);
                  }, 500);
                }, 500);
              }, 500);
            }, 600);
          }, 700);
        }, 600);
      }, 600);
    }, 700);
  }, 2600);
}, 3000);
"""
tail = ('<script>window.__errs=[];'
        "window.addEventListener('error',function(e){window.__errs.push(String(e.message));});"
        "window.addEventListener('unhandledrejection',function(e){window.__errs.push('REJ '+String(e.reason));});"
        '</script><script>' + JS + '</script>')

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_model.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\omodel'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=60000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
