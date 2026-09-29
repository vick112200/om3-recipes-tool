# -*- coding: utf-8 -*-
"""修档位映射诊断的两个 bug：
1) 顺序错了：get_mysetdatamodekind.cgi 必须在"进维护模式之后"才有效（之前 520/1001）
2) 候选解析错了：错误返回里也能抠出 '1'，导致只试了 mode=1；现在只在 200 且无 errorcode 时解析
另外：把每次读的超时收短、默认候选收窄，整体更快；跑完会明确打印"结束"行。
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()

OLD = """    var modes = [];
    try{
      var mk = await req('get_mysetdatamodekind.cgi', {timeout: 10000});
      log('① 相机支持的 my-set（原始返回）：HTTP ' + mk.status + ' ' + (mk.text || '').replace(/\\s+/g, ' ').slice(0, 400), mk.status === 200 ? 'ok' : 'err');
      var mm = (mk.text || '').match(/[A-Za-z0-9_]+/g) || [];
      for(var i=0;i<mm.length;i++){
        var t = mm[i];
        if(/^(current|myset[0-9]|my_set[0-9]|[1-5])$/i.test(t) && modes.indexOf(t) < 0) modes.push(t);
      }
    }catch(e){ log('① 失败：' + e.message, 'err'); }
    if(!modes.length) modes = ['current', '1', '2', '3', '4', '5', 'MySet1', 'MySet2', 'MySet3', 'MySet4', 'MySet5'];
    log('② 将逐个尝试这些取值：' + modes.join(' / '));

    try{
      var rM = await req('switch_cammode.cgi?mode=maintenance', {timeout: 10000});
      log('③ 进维护模式：HTTP ' + rM.status, rM.status === 200 ? 'ok' : 'err');
    }catch(e){ log('③ 进维护模式失败：' + e.message, 'err'); }
"""
assert h.count(OLD) == 1, h.count(OLD)

NEW = """    /* ① 必须先进维护模式，my-set 相关接口才会被受理 */
    var modes = [];
    try{
      var rM = await req('switch_cammode.cgi?mode=maintenance', {timeout: 10000});
      log('① 进维护模式：HTTP ' + rM.status, rM.status === 200 ? 'ok' : 'err');
    }catch(e){ log('① 进维护模式失败：' + e.message, 'err'); }

    /* ② 在维护模式里问"支持哪些 my-set" */
    try{
      var mk = await req('get_mysetdatamodekind.cgi', {timeout: 10000});
      var tx = mk.text || '';
      log('② 相机支持的 my-set：HTTP ' + mk.status + ' ' + tx.replace(/\\s+/g, ' ').slice(0, 400), mk.status === 200 ? 'ok' : 'err');
      if(mk.status === 200 && !/errorcode/i.test(tx)){
        var mm = tx.match(/[A-Za-z0-9_]+/g) || [];
        for(var i=0;i<mm.length;i++){
          var t = mm[i];
          if(/^(current|myset[0-9]|my_set[0-9]|[1-9])$/i.test(t) && modes.indexOf(t) < 0) modes.push(t);
        }
      }
    }catch(e){ log('② 失败：' + e.message, 'err'); }
    if(!modes.length) modes = ['current', '1', '2', '3', '4', '5'];
    log('③ 将逐个尝试这些取值（共 ' + modes.length + ' 个）：' + modes.join(' / '));
"""
h = h.replace(OLD, NEW, 1)

# 每份的超时收短 + 轮询上限降一点，避免整体太慢
h = h.replace("for(var t=0;t<40 && !ready;t++){", "for(var t=0;t<24 && !ready;t++){", 1)
h = h.replace("var rd = await req('get_partialmysetdata.cgi?kind=current&offset=0&size=' + sz, {timeout: 40000});",
              "var rd = await req('get_partialmysetdata.cgi?kind=current&offset=0&size=' + sz, {timeout: 30000});", 1)
h = h.replace("var rrz = 0;", "var rrz = 0;", 1)
open(P, 'w', encoding='utf-8', newline='').write(h)
print('档位映射诊断已修（顺序 + 候选解析 + 超时）')
