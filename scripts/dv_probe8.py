# -*- coding: utf-8 -*-
"""验收「导入相机」页：页签出现、payload 生成与逆向出的格式逐字一致。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'

PROBE = '''<script>
window.__errs=[];
window.onerror=function(m){window.__errs.push(String(m));};
setTimeout(function(){
  var o=[];
  o.push('app标记='+!!window.__OM3_APP__);
  var tb=document.getElementById('tabD');
  o.push('页签按钮显示='+(tb?tb.style.display:'无')+' 文案='+(tb?tb.textContent:'-'));
  tb.click();
  setTimeout(function(){
    var pd=document.getElementById('paneD');
    o.push('paneD 可见='+(!pd.classList.contains('hide')));
    o.push('目录按钮隐藏='+(document.getElementById('tocbtn').style.display==='none'));
    var sel=document.getElementById('camRecipe');
    o.push('配方下拉 组数='+sel.querySelectorAll('optgroup').length
           +' 优化版组='+sel.querySelectorAll('optgroup')[0].children.length
           +' 全部组='+sel.querySelectorAll('optgroup')[1].children.length);
    // 选 PNW
    var idx=-1;
    for(var i=0;i<sel.options.length;i++){ if(sel.options[i].textContent.indexOf('PNW')===0){ idx=i; break; } }
    sel.value=sel.options[idx].value;
    document.getElementById('camSlot').value='1';
    document.getElementById('camTarget').value='current';
    document.getElementById('camModel').value='OM-3';
    sel.dispatchEvent(new Event('change'));
    document.getElementById('camModel').dispatchEvent(new Event('input'));
    o.push('选中='+sel.options[idx].textContent);
    var txt=document.getElementById('camPreview').textContent;
    var lines=txt.split('\\n');
    o.push('预览行数='+lines.length);
    o.push('头='+lines[1]);
    o.push('第1色='+lines[2]);
    o.push('第12色='+lines[13]);
    o.push('影调高='+lines[14]+' 影调低='+lines[15]+' 影调中='+lines[16]);
    o.push('锐度='+lines[18]+' 对比='+lines[19]);
    // 切到槽 3 再试
    document.getElementById('camSlot').value='3';
    document.getElementById('camTarget').value='myset2';
    document.getElementById('camSlot').dispatchEvent(new Event('change'));
    var t2=document.getElementById('camPreview').textContent.split('\\n');
    o.push('换槽位后 头='+t2[1]+' 第1色='+t2[2]);
    o.push('JS 错误='+(window.__errs.length?window.__errs.join('|'):'无'));
    var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');
    document.body.appendChild(d);
  },400);
},2200);
</script>'''


def build(src, out, flag):
    h = open(src, encoding='utf-8').read()
    if flag:
        i = h.find('<body')
        j = h.find('>', i) + 1
        h = h[:j] + '<script>window.__OM3_APP__=1;</script>\n' + h[j:]
    open(out, 'w', encoding='utf-8', newline='').write(h.replace('</body>', PROBE + '</body>', 1))


build(TMP + r'\app\base.html', TMP + r'\dv_cam_app.html', True)
build(TMP + r'\app\base.html', TMP + r'\dv_cam_desk.html', False)
print('已生成 dv_cam_app.html / dv_cam_desk.html')
