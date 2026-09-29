# -*- coding: utf-8 -*-
"""维护模式打通后的正式实现：
② 备份：maintenance → request_getmysetdata?mode=..&kind=current → 轮询 backupstate(等非 busy)
        → get_mysetdatasize?kind=current → 分块 get_partialmysetdata → 存盘 → exec_reboot
③ 写入：maintenance → request_restoremysetdata?action=restore → 其余照旧 → 完成后强制重启
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()

# ---------- ② 备份：开头加维护模式 + 官方参数 ----------
old = """      line(o2, '① 让相机准备数据：request_getmysetdata.cgi?mode=current');
      var r1 = await req('request_getmysetdata.cgi?mode=current');
      line(o2, '   HTTP ' + r1.status + ' ' + r1.text.slice(0, 200));"""
assert h.count(old) == 1, h.count(old)
new = """      line(o2, '① 进维护模式：switch_cammode.cgi?mode=maintenance');
      var rM = await req('switch_cammode.cgi?mode=maintenance', {timeout: 10000});
      line(o2, '   HTTP ' + rM.status + ' ' + (rM.text || '').slice(0, 120), rM.status === 200 ? 'ok' : 'err');
      if(rM.status !== 200) throw new Error('相机不接受维护模式');
      line(o2, '② 让相机准备数据（官方参数）：request_getmysetdata.cgi?mode=' + t0 + '&kind=current');
      var r1 = await req('request_getmysetdata.cgi?mode=' + t0 + '&kind=current', {timeout: 20000});
      line(o2, '   HTTP ' + r1.status + ' ' + r1.text.slice(0, 200), r1.status === 200 ? 'ok' : 'err');"""
h = h.replace(old, new, 1)

# ---------- ② 轮询：等"非 busy" ----------
old_poll = """      var size = NaN, tries = 0, ready = false;
      while(tries++ < 15 && !ready){
        await sleep(400);
        var r2 = await req('get_mysetbackupstate.cgi');
        line(o2, '② 状态 ' + tries + '：HTTP ' + r2.status + ' ' + r2.text.slice(0, 120));
        if(/1|ready|complete|finish|done/i.test(r2.text)) ready = true;
      }"""
assert h.count(old_poll) == 1
new_poll = """      var size = NaN, tries = 0, ready = false;
      while(tries++ < 40 && !ready){
        await sleep(500);
        var r2 = await req('get_mysetbackupstate.cgi', {timeout: 8000});
        var tx = r2.text || '';
        var busy = /busy/i.test(tx);
        if(tries % 4 === 1 || !busy) line(o2, '③ 状态 ' + tries + '：HTTP ' + r2.status + ' ' + tx.slice(0, 90), busy ? '' : 'ok');
        if(!busy && /(<status>\\s*)?(idle|ready|complete|finish|done|0\\s*<)/i.test(tx)) ready = true;
        if(!busy && r2.status === 200 && tries > 2 && !/generalerror/i.test(tx)) ready = true;
      }
      if(!ready) line(o2, '（状态一直 busy：可能数据量大或相机忙，继续尝试读大小）', 'warn');"""
h = h.replace(old_poll, new_poll, 1)

# ---------- ② 大小行编号 & 末尾重启 ----------
h = h.replace("line(o2, '③ 数据大小：HTTP '", "line(o2, '④ 数据大小：HTTP '", 1)
h = h.replace("line(o2, '④ 备份完成：声明 '", "line(o2, '⑤ 备份完成：声明 '", 1)
old_tail = """    }catch(e){
      line(o2, '失败：' + e.message, 'err');
    }
    this.disabled = false;
  });"""
assert h.count(old_tail) == 1
new_tail = """    }catch(e){
      line(o2, '失败：' + e.message, 'err');
    }
    /* 无论成败都要退出维护模式：官方也是靠重启收尾（相机会重启，正常） */
    try{
      var rR = await req('exec_reboot.cgi', {timeout: 8000});
      line(o2, '⑥ 已请求相机重启以退出维护模式（相机重启后 Wi-Fi 会断一下）', rR.status === 200 ? 'ok' : 'warn');
    }catch(e){ line(o2, '重启请求失败：' + e.message, 'warn'); }
    this.disabled = false;
  });"""
h = h.replace(old_tail, new_tail, 1)

# ---------- ③ 写入：开头加维护模式 + 末尾强制重启 ----------
old_w = """    var r1 = await req('request_restoremysetdata.cgi?action=restore');"""
assert h.count(old_w) == 1
h = h.replace(old_w, """    lg('① 进维护模式：switch_cammode.cgi?mode=maintenance');
    var rM = await req('switch_cammode.cgi?mode=maintenance', {timeout: 10000});
    lg('   HTTP ' + rM.status + ' ' + (rM.text || '').slice(0, 120), rM.status === 200 ? 'ok' : 'err');
    if(rM.status !== 200) throw new Error('相机不接受维护模式');
    var r1 = await req('request_restoremysetdata.cgi?action=restore');""", 1)

old_reb = """      if(document.getElementById('camReboot').checked){
        var r5 = await req('exec_reboot.cgi');
        lg('⑦ 已请求相机重启：HTTP ' + r5.status, r5.status===200?'ok':'warn');
      }"""
assert h.count(old_reb) == 1
h = h.replace(old_reb, """      var r5 = await req('exec_reboot.cgi', {timeout: 8000});
      lg('⑦ 已请求相机重启（退出维护模式，必需）：HTTP ' + r5.status, r5.status===200?'ok':'warn');""", 1)

# ---------- ③ 卡片提示补一句 ----------
old_note = '<div class="camhd">③ 写入配方（一次一个，选槽位）</div>'
if h.count(old_note) == 1:
    h = h.replace(old_note, old_note + '\n    <div class="camout">写入流程：相机进<b>维护模式</b> → 分块上传 → <b>相机自动重启</b>（跟你用官方 app 的现象一样，属正常）。</div>', 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('② 备份 / ③ 写入 已改成维护模式流程')
