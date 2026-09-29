# -*- coding: utf-8 -*-
"""C4 换配方后的渲染验收：切到优化版 → C4，看四格名字/色轮/档位说明。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\82302\AppData\Local\Temp'

PROBE = '''<script>
setTimeout(function(){
  var o=[];
  document.querySelector('.tabs button[data-p="B"]').click();
  setTimeout(function(){
    var b=document.querySelector('#modetabs button[data-m="oC4"]');
    o.push('C4 按钮='+(b?b.textContent:'缺失'));
    if(b) b.click();
    setTimeout(function(){
      var om=document.getElementById('oC4');
      o.push('C4 显示='+(om.style.display===''||om.style.display==='block'));
      var names=[];
      om.querySelectorAll('.oslot').forEach(function(s){
        names.push(s.querySelector('.osname').textContent+'/'+s.querySelector('.osauth').textContent
                   +'[轮'+(s.querySelector('.oswheel svg')?'✓':'✗')+' 图'+s.querySelectorAll('figure').length+']');
      });
      o.push('四格: '+names.join(' | '));
      o.push('说明折标题='+om.querySelector('details.fomwb summary').textContent);
      o.push('C4 里还剩的 5300K 提及='+(om.innerHTML.split('5300K').length-1));
      o.push('夜景人像折='+(om.querySelectorAll('details.fobox').length)+' 个');
      var p=document.querySelectorAll('.pane')[1];
      other=p?p.querySelectorAll('details.fold').length:-1;
      var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');
      document.body.appendChild(d);
    },500);
  },700);
},2200);
</script>'''


def make(src, out, extra=''):
    h = open(src, encoding='utf-8').read()
    open(out, 'w', encoding='utf-8', newline='').write(h.replace('</body>', PROBE + extra + '</body>', 1))


make(BASE + r'\app\base.html', BASE + r'\dv_c4.html')
make(BASE + r'\dvsf.html', BASE + r'\dv_c4v.html', '')
print('已生成 dv_c4.html / dv_c4v.html')
