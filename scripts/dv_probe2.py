# -*- coding: utf-8 -*-
"""场景对比新功能的验收探针。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
SRC = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(SRC, encoding='utf-8').read()

PROBE = '''<script>
function go(){document.querySelector('.tabs button[data-p="C"]').click();}
setTimeout(function(){
  var o=[];
  go();
  setTimeout(function(){
    var pg=document.getElementById('scpager');
    var s=pg.querySelector('.scslide');
    var imgs=pg.querySelectorAll('.scslide img');
    o.push('对比卡: 详情按钮='+(!!s.querySelector('.scjump'))+' 优化版按钮='+(!!s.querySelector('.scjump2')));
    o.push('描述长度='+s.querySelector('.scdesc').textContent.length+' 折叠块='+s.querySelectorAll('details.fold').length);
    o.push('参数摘要='+s.querySelector('details.fpar summary').textContent.slice(0,42));
    o.push('折叠条 on='+document.getElementById('foldbar').classList.contains('on')+' ['+document.querySelector('#foldbtn .fb1').textContent+' / '+document.querySelector('#foldbtn .fb2').textContent+']');
    imgs[1].click();
    setTimeout(function(){
      o.push('全屏开='+document.getElementById('lb').classList.contains('on')+' 标题='+document.getElementById('lbtitle').textContent);
      o.push('全屏详情按钮='+(!!document.querySelector('#lbbot .lbdetail'))+' 张数提示='+document.querySelector('#lbbot .lbhint').textContent.slice(-8));
      document.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight'}));
      setTimeout(function(){
        o.push('右滑后标题='+document.getElementById('lbtitle').textContent);
        document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}));
        setTimeout(function(){
          var sw = imgs[0].parentNode.getBoundingClientRect().width + 12;
          o.push('关闭后 位置='+document.getElementById('scpos').textContent+' scrollLeft='+Math.round(pg.scrollLeft)+' 期望≈'+Math.round(sw*2));
          var b=s.querySelector('.scjump');
          var target=b.getAttribute('data-jump');
          b.click();
          setTimeout(function(){
            var card=document.getElementById(target);
            o.push('详情 target='+target+' 命中='+(!!card)+' 高亮='+(card?card.className.indexOf('flashcard')>=0:'-')+' 当前页签='+(document.querySelector('.tabs button.on')||{}).textContent);
            var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');
            document.body.appendChild(d);
          },700);
        },400);
      },400);
    },700);
  },900);
},2200);
</script>'''

open(r'C:\Users\82302\AppData\Local\Temp\dv2.html', 'w', encoding='utf-8', newline='').write(h.replace('</body>', PROBE + '</body>', 1))
print('已生成 dv2.html')
