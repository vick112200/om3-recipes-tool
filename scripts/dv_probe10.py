# -*- coding: utf-8 -*-
"""验收界面重构：版本开关 / 折叠 / 跳转 / 搜索与对比页跳转。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'

PROBE = '''<script>
window.__errs=[]; window.onerror=function(m){window.__errs.push(String(m));};
function vw(){ var out=[], p=document.getElementById('paneA'); 
  var off=function(id){var e=document.getElementById(id);return !e||!e.classList.contains('hide');};
  return {A:off('paneA'),B:off('paneB'),C:off('paneC'),D:off('paneD')};
}
setTimeout(function(){
  var o=[];
  var ver=document.querySelector('.tabs.ver');
  o.push('版本开关存在='+(!!ver)+' 按钮='+(ver?ver.textContent:'-'));
  o.push('初始显示='+JSON.stringify(vw()));
  document.querySelector('.tabs.ver button[data-p="B"]').click();
  setTimeout(function(){
    o.push('切到B后='+JSON.stringify(vw()));
    var dsB=document.querySelectorAll('#paneB details.sec');
    var opens=[].slice.call(document.querySelectorAll('#paneB details.sec[open]')).map(function(d){return d.id;});
    o.push('B折叠块='+dsB.length+' 默认展开='+opens.join(','));
    var b1=document.querySelector('#oC1 .ombody'), b2=document.querySelector('#oC2 .ombody');
    o.push('C1体可见='+(b1&&b1.style.display!=='none')+' C2体可见='+(b2&&b2.style.display!=='none'));
    document.querySelector('#paneB [data-goto="oC3"]').click();
    setTimeout(function(){
      var b3=document.querySelector('#oC3 .ombody');
      o.push('点C3跳转后: C3可见='+(b3&&b3.style.display!=='none')+' C1可见='+(b1&&b1.style.display!=='none'));
      document.querySelector('#paneB [data-all="B"][data-open="1"]').click();
      var n1=document.querySelectorAll('#paneB details.sec[open]').length;
      var n2=document.querySelectorAll('#paneB .ombody').length;
      var vis=[].slice.call(document.querySelectorAll('#paneB .ombody')).filter(function(x){return x.style.display!=='none';}).length;
      o.push('B全部展开: sec展开='+n1+'/'+document.querySelectorAll('#paneB details.sec').length+' 档位体可见='+vis+'/'+n2);
      document.querySelector('#paneB [data-all="B"][data-open="0"]').click();
      o.push('B全部折叠后: sec展开='+document.querySelectorAll('#paneB details.sec[open]').length
             +' 档位体可见='+[].slice.call(document.querySelectorAll('#paneB .ombody')).filter(function(x){return x.style.display!=='none';}).length);
      // 回到 A
      document.querySelector('.tabs.ver button[data-p="A"]').click();
      setTimeout(function(){
        o.push('切回A='+JSON.stringify(vw()));
        var dsA=document.querySelectorAll('#paneA details.sec');
        var openA=[].slice.call(document.querySelectorAll('#paneA details.sec[open]')).map(function(d){return d.id;});
        o.push('A折叠块='+dsA.length+' 默认展开='+openA.join(','));
        document.querySelector('#paneA [data-goto="mode-C3"]').click();
        setTimeout(function(){
          var d3=document.getElementById('mode-C3');
          o.push('点C3跳转: open='+d3.open+' 其他档位展开='+[].slice.call(document.querySelectorAll('#paneA details.sec[open]')).map(function(d){return d.id;}).join(','));
          document.querySelector('#paneA [data-all="A"][data-open="1"]').click();
          o.push('A全部展开='+document.querySelectorAll('#paneA details.sec[open]').length+'/'+dsA.length);
          // 搜索跳转：PNW 卡片在 pool 里（折叠状态）
          document.querySelector('#paneA [data-all="A"][data-open="0"]').click();
          var q=document.getElementById('tocq'); q.value='PNW';
          q.dispatchEvent(new Event('input'));
          setTimeout(function(){
            var res=document.getElementById('tocres');
            var a=res.querySelector('a[href="#r-ian-will_pnw"]') || res.querySelector('a');
            o.push('搜索结果='+res.querySelectorAll('a').length+' 目标='+(a?a.getAttribute('href'):'无'));
            if(a) a.click();
            setTimeout(function(){
              var pool=document.getElementById('pool');
              o.push('搜索跳转后 pool 展开='+pool.open+' 高亮='+document.getElementById('r-ian-will_pnw').className.indexOf('flashcard')>=0);
              // 对比页跳优化版槽位
              document.querySelector('.tabs button[data-p="C"]').click();
              setTimeout(function(){
                var pg=document.getElementById('scpager');
                var all=pg.querySelectorAll('.scslide'), tgt=null;
                for(var i=0;i<all.length;i++){ if(all[i].querySelector('.scjump2')){ tgt=all[i]; break; } }
                if(tgt){
                  var jb=tgt.querySelector('.scjump2'); jb.click();
                  setTimeout(function(){
                    var id=jb.getAttribute('data-jump');
                    var el=document.getElementById(id);
                    var om=el.closest('.omode');
                    o.push('对比页跳 '+id+': 页签B='+vw().B+' 档位体可见='+(om.querySelector('.ombody').style.display!=='none')+' 高亮='+el.className.indexOf('flashcard')>=0);
                    done(o);
                  },700);
                } else { o.push('本场没有优化版条目'); done(o); }
              },500);
            },700);
          },500);
        },300);
      },400);
    },300);
  },400);
  function done(o){
    o.push('JS错误='+(window.__errs.length?window.__errs.join('|'):'无'));
    var d=document.createElement('div');d.id='DBGOUT';d.textContent=o.join(' ;; ');document.body.appendChild(d);
  }
},2200);
</script>'''

h = open(TMP + r'\app\base.html', encoding='utf-8').read()
i = h.find('<body')
j = h.find('>', i) + 1
h = h[:j] + '<script>window.__OM3_APP__=1;</script>\n' + h[j:]
open(TMP + r'\dv_ui.html', 'w', encoding='utf-8', newline='').write(h.replace('</body>', PROBE + '</body>', 1))
print('已生成 dv_ui.html')
