# -*- coding: utf-8 -*-
"""加一个「探测相机接口」诊断：按顺序试一批只读端点，把 HTTP 状态记进日志。
用来搞清楚 OM-3 到底支持哪些 my-set 接口（备份读失败 errorcode 1001 的定位）。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()

# 菜单项
old_item = '      <button type="button" data-act="perm">检查权限</button>'
assert h.count(old_item) == 1
h = h.replace(old_item, old_item + '\n      <button type="button" data-act="probe">探测相机接口</button>', 1)

# 处理逻辑
old_act = "      else if(a === 'perm'){"
assert h.count(old_act) == 1
NEW = """      else if(a === 'probe'){ probeEndpoints(); }
""" + old_act
h = h.replace(old_act, NEW, 1)

# 探测函数：挂在 setConn 前面
anchor = "  var _camOn = false;"
assert h.count(anchor) == 1
PROBE = """  /* ============ 只读探测：看看相机支持哪些 my-set 接口（不写任何东西） ============ */
  var PROBE_LIST = [
    'get_caminfo.cgi',
    'request_getmysetdata.cgi?mode=current',
    'request_getmysetdata.cgi?mode=1',
    'request_getmysetdata.cgi',
    'getmysetdata.cgi?mode=current',
    'get_mysetdatasize.cgi?kind=current',
    'get_mysetdatasize.cgi?kind=1',
    'get_mysetbackupstate.cgi',
    'get_mysetrestorestate.cgi',
    'get_mysetdata.cgi?mode=current',
    'get_mysetdatasize.cgi',
    'get_mysetbackupstate.cgi?kind=current'
  ];
  async function probeEndpoints(){
    showStep(3);
    log('===== 开始探测相机接口（只读，不会改任何设置）');
    for(var i=0;i<PROBE_LIST.length;i++){
      var pth = PROBE_LIST[i];
      try{
        var r = await req(pth, {timeout: 6000});
        log('　HTTP ' + r.status + '　' + pth + (r.text ? '　→　' + r.text.replace(/\\s+/g,' ').slice(0, 120) : ''),
            r.status === 200 ? 'ok' : 'warn');
      }catch(e){
        log('　失败　' + pth + '　→　' + e.message, 'err');
      }
    }
    log('===== 探测结束。把上面这段复制给我。', 'ok');
    toastMsg('探测完成，看图日志');
  }
  window.__om3probe = probeEndpoints;

"""
h = h.replace(anchor, PROBE + anchor, 1)
open(P, 'w', encoding='utf-8', newline='').write(h)
print('已加「探测相机接口」（菜单里）')
