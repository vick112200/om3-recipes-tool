# -*- coding: utf-8 -*-
"""给「导入相机」页的日志加：复制 / 下载 / 清空 按钮（方便把日志发回来排查）。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'
P = TMP + r'\app\base.html'
h = open(P, encoding='utf-8').read()
open(TMP + r'\app\base.before_camlog.html', 'w', encoding='utf-8', newline='').write(h)

# ---------- 1. ③ 区块底部加按钮 ----------
OLD = '<div class="camout" id="camOut3">选择配方和槽位，点「写入相机」。写入前会自动先备份一次。</div>'
assert h.count(OLD) == 1
NEW = (OLD + '\n<div class="camlogbtns">'
       '<button type="button" id="camCopyLog">复制全部日志</button>'
       '<button type="button" id="camDlLog">下载日志文件</button>'
       '<button type="button" id="camClearLog" class="camghost">清空日志</button>'
       '<span class="camloghint">①②③ 的每一步都会记在这里，跑完复制给我就行</span>'
       '</div>')
h = h.replace(OLD, NEW, 1)

# ---------- 2. CSS ----------
OLD_CSS = '.camout{font-size:12.5px;color:#9a9a9a;line-height:1.7;margin-top:10px;white-space:pre-wrap;word-break:break-all}'
assert h.count(OLD_CSS) == 1
h = h.replace(OLD_CSS, OLD_CSS + '\n'
              '.camlogbtns{margin-top:12px}\n'
              '.camlogbtns button{padding:7px 12px;font-size:12.5px}\n'
              '.camloghint{display:block;font-size:11.5px;color:#7a7a7a;margin-top:8px}\n'
              '.camout{border-left:2px solid #2f2f2f;padding-left:10px}', 1)

# ---------- 3. JS：收集日志 + 三个按钮 ----------
OLD_LINE = """  function line(el, msg, cls){
    var d = document.createElement('div');
    if(cls) d.className = cls;
    d.innerHTML = esc(msg);
    el.appendChild(d);
    el.scrollTop = el.scrollHeight;
  }"""
assert h.count(OLD_LINE) == 1
NEW_LINE = """  var ALLLOG = [];
  function line(el, msg, cls){
    var d = document.createElement('div');
    if(cls) d.className = cls;
    d.innerHTML = esc(msg);
    el.appendChild(d);
    el.scrollTop = el.scrollHeight;
    var tag = el === log3 ? '③写入' : (el === o1 ? '①检测' : '②备份');
    ALLLOG.push('[' + new Date().toLocaleTimeString() + '] ' + tag + ' ' + msg);
  }
  function logText(){
    return 'OM-3 导入相机 日志\\n生成时间：' + new Date().toLocaleString() + '\\n' +
           '页面：' + (location.href || '') + '\\n\\n' + ALLLOG.join('\\n') + '\\n';
  }"""
h = h.replace(OLD_LINE, NEW_LINE, 1)

OLD_END = """  fill();
})();"""
assert h.count(OLD_END) == 1
NEW_END = """  fill();

  /* ---------- 日志：复制 / 下载 / 清空 ---------- */
  document.getElementById('camCopyLog').addEventListener('click', function(){
    var t = logText();
    function fallbackCopy(){
      var ta = document.createElement('textarea');
      ta.value = t;
      ta.style.position = 'fixed'; ta.style.top = '0'; ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.focus(); ta.select();
      var ok = false;
      try{ ok = document.execCommand('copy'); }catch(e){}
      document.body.removeChild(ta);
      return ok;
    }
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(t).then(function(){
        line(log3, '日志已复制到剪贴板（' + ALLLOG.length + ' 行），直接粘给我就行。', 'ok');
      }, function(){
        line(log3, fallbackCopy() ? '日志已复制（' + ALLLOG.length + ' 行）。' : '复制失败——请长按下面的日志文字手动全选复制。',
             fallbackCopy() ? 'ok' : 'warn');
      });
    } else {
      line(log3, fallbackCopy() ? '日志已复制（' + ALLLOG.length + ' 行）。' : '复制失败——请长按日志文字手动复制。',
           fallbackCopy() ? 'ok' : 'warn');
    }
  });

  document.getElementById('camDlLog').addEventListener('click', function(){
    var blob = new Blob([logText()], {type:'text/plain'});
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'OM3-导入相机-日志-' + new Date().toISOString().slice(0,16).replace(/[:T]/g,'-') + '.txt';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    line(log3, '日志文件已生成（在「下载」文件夹里）。', 'ok');
  });

  document.getElementById('camClearLog').addEventListener('click', function(){
    o1.innerHTML = ''; o2.innerHTML = ''; o3.innerHTML = '';
    ALLLOG.length = 0;
    o1.textContent = '未连接。';
    o2.textContent = '还没备份。';
    o3.textContent = '日志已清空。';
  });
})();"""
h = h.replace(OLD_END, NEW_END, 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('日志按钮已加入，base.html %.1f KB' % (len(h.encode('utf-8')) / 1024))
