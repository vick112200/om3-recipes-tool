# -*- coding: utf-8 -*-
"""档位映射诊断（只读）：先问相机支持哪些 my-set（mode/kind），再逐个读名字+数据，列出各槽占用情况。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()
n0 = len(h)

# 菜单项
old = '      <button type="button" data-act="keys">列出色彩相关键（诊断）</button>'
assert h.count(old) == 1
h = h.replace(old, old + '\n      <button type="button" data-act="map">档位映射诊断（只读）</button>', 1)
old_a = "      else if(a === 'keys'){ listColorKeys(); }"
assert h.count(old_a) == 1
h = h.replace(old_a, old_a + "\n      else if(a === 'map'){ mapModes(); }", 1)

anchor = "  /* ============ 只读探测"
assert h.count(anchor) == 1

FUNC = '''  /* ============ 档位映射（只读）：搞清"哪一份数据 = 相机上哪个档位" ============
     ① 问相机支持哪些 my-set：get_mysetdatamodekind.cgi
     ② 逐个读名字：get_mysetname.cgi?mode=<X>
     ③ 逐个读数据：维护模式 → request_getmysetdata?mode=<X>&kind=current → 轮询 → 大小 → 一次读完
     ④ 汇报：名字 / 字节数 / 头部行 / 槽1..4 哪些非空
     全程只读，不写入任何东西；结束时重启退出维护模式。 */
  function om3slotSummary(txt){
    var m = om3map(txt), out = [], CR = String.fromCharCode(13);
    function cnt(prefix){
      var n = 0, keys = Object.keys(m);
      for(var i=0;i<keys.length;i++){
        if(keys[i].indexOf(prefix) === 0){
          var v = m[keys[i]];
          if(v && !/MODE_(STEP_0|SHARP_0|CONTRAST_0)$/.test(v)) n++;
        }
      }
      return n;
    }
    for(var s=1;s<=4;s++){
      var c = cnt('MODE_COLOR_CREATOR_2_VIVID_SET' + s + '_');
      var mo = cnt('MODE_MONOCHROME_CREATOR_GRANULAR_SET' + s);
      out.push('槽' + s + (c ? (' 彩色项 ' + c + ' 个非默认') : (mo ? ' 黑白项非默认' : ' 空/默认')));
    }
    return out.join('｜');
  }
  async function mapModes(){
    showStep(3);
    log('===== 档位映射诊断开始（全程只读，不改任何设置）');
    var modes = [];
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

    for(var k=0;k<modes.length;k++){
      var X = modes[k];
      try{
        var nm = '';
        try{
          var rn = await req('get_mysetname.cgi?mode=' + encodeURIComponent(X), {timeout: 8000});
          nm = (rn.text || '').replace(/\\s+/g, ' ').slice(0, 60);
        }catch(e){ nm = '（名字读取失败）'; }
        var rq = await req('request_getmysetdata.cgi?mode=' + encodeURIComponent(X) + '&kind=current', {timeout: 20000});
        var okq = (rq.status === 200) && !/generalerror/i.test(rq.text || '');
        if(!okq){
          log('　mode=' + X + '　名字：' + nm + '　→ 不支持（HTTP ' + rq.status + ' ' + (rq.text || '').replace(/\\s+/g, ' ').slice(0, 60) + '）', 'warn');
          continue;
        }
        var ready = false;
        for(var t=0;t<40 && !ready;t++){
          await sleep(500);
          var rs = await req('get_mysetbackupstate.cgi', {timeout: 8000});
          var tx = rs.text || '';
          if(!/busy/i.test(tx) && /success|idle|complete|ready/i.test(tx)) ready = true;
        }
        var rz = await req('get_mysetdatasize.cgi?kind=current', {timeout: 8000});
        var sz = sizeFrom(rz.text);
        if(!(sz > 0)){ log('　mode=' + X + '　→ 拿不到大小：' + (rz.text || '').slice(0, 60), 'warn'); continue; }
        var rd = await req('get_partialmysetdata.cgi?kind=current&offset=0&size=' + sz, {timeout: 40000});
        var body = (rd.status === 200) ? om3CsvPart(rd.text).slice(0, sz) : '';
        var head = (body.split(String.fromCharCode(10))[0] || '').slice(0, 80);
        log('　★ mode=' + X + '　名字：' + nm + '　字节 ' + sz + '　头部：' + head, 'ok');
        log('　　 槽位占用：' + om3slotSummary(body));
      }catch(e){ log('　mode=' + X + ' 出错：' + e.message, 'err'); }
    }
    try{
      var rr = await req('exec_reboot.cgi', {timeout: 8000});
      log('④ 已请求相机重启（退出维护模式）：HTTP ' + rr.status, 'ok');
    }catch(e){ log('④ 重启请求失败：' + e.message + '（可手动关机再开）', 'warn'); }
    log('===== 映射诊断结束。把这一段复制给我（含 ★ 行和"槽位占用"）。', 'ok');
    toastMsg('档位映射跑完，看日志');
  }
  window.__om3mapModes = mapModes;

'''
h = h.replace(anchor, FUNC + anchor, 1)
open(P, 'w', encoding='utf-8', newline='').write(h)
print('已加「档位映射诊断（只读）」（+%d 字节）' % (len(h) - n0))
