# -*- coding: utf-8 -*-
"""导入功能实测：用合成文件走真实路径（#mpFile 的 change 事件），不用真机。

覆盖：v2 多套 JSON / 同一文件**连导两次** / v2 单槽 JSON / 官方 .oes / 坏文件
用法：python scripts/dv_import.py
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
  var o = [];
  function sets(){ try{ return JSON.parse(localStorage.getItem('om3sets')||'[]').length; }catch(e){ return -1; } }
  function logTxt(){ var e=document.getElementById('camOut3'); return e ? (e.textContent||'').replace(/\s+/g,' ') : ''; }
  function lastLog(n){
    var t = logTxt().split(' ').filter(Boolean);
    return t.slice(-n).join(' ');
  }
  function feed(name, text, mime){
    var inp = document.getElementById('mpFile');
    if(!inp){ o.push('  !! #mpFile 还没被创建（导入按钮没被触发过）'); return false; }
    try{
      var dt = new DataTransfer();
      dt.items.add(new File([text], name, { type: mime || 'application/json' }));
      inp.files = dt.files;
      inp.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    }catch(e){ o.push('  !! 派发失败: ' + e.message); return false; }
  }
  function slotUI(){ return document.getElementById('mpImpSlot') ? document.getElementById('mpImpSlot').value : '无 #mpImpSlot'; }

  try{ localStorage.removeItem('om3sets'); }catch(e){}
  document.getElementById('tabMine').click();

  var S = {
    app:'OM-3 色彩配方手册', kind:'om3-colorprofile', version:2, count:2,
    sets:[
      {name:'导入甲', desc:'甲描述', from:'myset1', camera:'OM-3',
       slots:{1:{vivid:[1,2,3,0,0,0,0,0,0,0,0,0], raw:{'MODE_COLOR_CREATOR_2_VIVID_SET1_1':'MODE_STEP_P1'}, used:3},2:null,3:null,4:null}},
      {name:'导入乙', desc:'乙描述', from:'myset2', camera:'OM-3', slots:{1:null,2:null,3:null,4:null}}
    ]
  };
  var ONE = { app:'OM-3 色彩配方手册', kind:'om3-colorprofile', version:2,
              name:'单槽方案', desc:'单槽描述', from:'myset3', camera:'OM-3',
              slots:{1:null,2:{vivid:[0,0,0,0,0,1,1,1,0,0,0,0], raw:{'MODE_COLOR_CREATOR_2_VIVID_SET2_6':'MODE_STEP_P1'}, used:3},3:null,4:null} };
  /* 官方 .oes 的真实结构：解析器找的是 <ColorCreater2 SatValue="...">（厂商就是这么拼的），
     再加 ToneControl / Sharpness / Contrast */
  var OES = '<?xml version="1.0" encoding="UTF-8"?>'
          + '<ImageProcessing Version="1.0"><ColorCreater2 SatValue="1,2,3,0,0,0,0,0,0,0,0,0"/>'
          + '<ToneControl Bright="-1" Mid="1" Dark="2"/><Sharpness Value="0"/><Contrast Value="1"/>'
          + '</ImageProcessing>';

  setTimeout(function(){
    o.push('起点：方案数=' + sets() + '  导入目标槽 UI 值=' + slotUI());
    /* 让页面创建出 #mpFile（等价于点一下「导入方案文件」） */
    var btn = document.getElementById('mpImportFile');
    o.push('导入按钮 存在=' + !!btn);
    if(btn) btn.click();
    setTimeout(function(){
      o.push('#mpFile 已创建=' + !!document.getElementById('mpFile'));
      var before = sets();

      /* ① 第一次导入（多套） */
      feed('multi.json', JSON.stringify(S));
      setTimeout(function(){
        o.push('① 导入多套：' + before + ' → ' + sets() + '（期望 +2）  日志尾：' + lastLog(9));

        /* ② 同一个文件再导一次（用户报的场景） */
        var b2 = sets();
        feed('multi.json', JSON.stringify(S));
        setTimeout(function(){
          o.push('② 同一文件再导一次：' + b2 + ' → ' + sets() + '（期望再 +2）  日志尾：' + lastLog(9));

          /* ③ 单槽 JSON */
          var b3 = sets();
          feed('one.json', JSON.stringify(ONE));
          setTimeout(function(){
            o.push('③ 单槽 JSON：' + b3 + ' → ' + sets() + '（期望 +1）  日志尾：' + lastLog(9));

            /* ④ 官方 .oes */
            var b4 = sets();
            feed('official.oes', OES, 'text/xml');
            setTimeout(function(){
              o.push('④ 官方 .oes：' + b4 + ' → ' + sets() + '（期望 +1）  日志尾：' + lastLog(9));

              /* ⑤ 坏文件 */
              var b5 = sets();
              feed('bad.json', '{"hello":"world"}');
              setTimeout(function(){
                o.push('⑤ 坏文件：' + b5 + ' → ' + sets() + '（应不变）  日志尾：' + lastLog(10));
                o.push('累计 om3errs=' + (window.__om3errs||0)
                     + '  列表条目=' + document.querySelectorAll('#mpList .mpitem').length);
                var p=document.createElement('pre');p.id='DBGOUT';p.textContent=o.join('\n');
                document.body.appendChild(p);
              }, 500);
            }, 500);
          }, 500);
        }, 500);
      }, 500);
    }, 600);
  }, 700);
}, 2800);
"""
tail = '<script>' + JS + '</script>'

k = src.find('<body')
j = src.find('>', k) + 1
out = src[:j] + head + src[j:].replace('</body>', tail + '</body>', 1)
p = TMP + r'\dv_import.html'
open(p, 'w', encoding='utf-8', newline='').write(out)
ud = TMP + r'\oimport'
subprocess.run(['cmd', '/c', 'rmdir', '/s', '/q', ud], capture_output=True)
r = subprocess.run([r'C:\Program Files\Google\Chrome\Application\chrome.exe', '--headless=new',
                    '--disable-gpu', '--no-first-run', '--hide-scrollbars',
                    '--user-data-dir=' + ud, '--window-size=412,900',
                    '--virtual-time-budget=24000', '--dump-dom',
                    'file:///' + p.replace('\\', '/')],
                   capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=240)
dom = r.stdout or ''
kk = dom.find('id="DBGOUT"')
print(dom[kk:].split('>', 1)[1].split('</pre>')[0] if kk > 0 else ('无输出 DOM=%d' % len(dom)))
