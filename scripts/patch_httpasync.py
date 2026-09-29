# -*- coding: utf-8 -*-
"""最后一块同步阻塞也去掉：相机 HTTP 改成异步（Java 后台线程 + 回调推回页面）。
之前 camGet/camPost 是同步桥，一次请求最长会占住 JS 线程 8~20 秒（写入分块时尤其明显）。
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
TMP = r'C:\Users\82302\AppData\Local\Temp'

# ---------------- Java ----------------
p = TMP + r'\apk\java\com\om3\handbook\MainActivity.java'
j = open(p, encoding='utf-8').read()
if 'camGetAsync' not in j:
    anchor = '        @JavascriptInterface\n        public String camGet(String path) {'
    assert j.count(anchor) == 1
    ADD = '''        private int sReqId = 0;

        /** 异步版：立刻返回请求号，结果由后台线程推回页面（页面不再被 HTTP 阻塞） */
        @JavascriptInterface
        public String camGetAsync(final String path) { return camAsync(path, null, "GET"); }

        @JavascriptInterface
        public String camPostAsync(final String path, final String b64) {
            byte[] body = null;
            try { body = android.util.Base64.decode(b64, android.util.Base64.DEFAULT); } catch (Throwable t) { }
            return camAsync(path, body, "POST");
        }

        private String camAsync(final String path, final byte[] body, final String method) {
            final String id = "r" + (++sReqId);
            POOL.execute(new Runnable() {
                @Override public void run() {
                    String json;
                    try { json = camReq(path, body, method); }
                    catch (Throwable t) { json = "{\\"s\\":0,\\"t\\":\\"ERR " + t.getClass().getSimpleName() + "\\"}"; }
                    jsCall("window.__om3http&&window.__om3http(" + jsonStr(id) + "," + json + ")");
                }
            });
            return id;
        }

'''
    j = j.replace(anchor, ADD + anchor, 1)
    open(p, 'w', encoding='utf-8', newline='').write(j)
    print('Java: camGetAsync / camPostAsync 已加（HTTP 走后台线程）')
else:
    print('Java: 已应用过，跳过')

# ---------------- 页面 ----------------
P = TMP + r'\app\base.html'
h = open(P, encoding='utf-8').read()
if '__om3http' not in h:
    old = """  function req(path, opt){
    opt = opt || {};
    if(Native && Native.camGet){
      return new Promise(function(resolve, reject){
        var raw = '';
        try{
          raw = opt.body ? String(Native.camPost(path, b64(opt.body)))
                         : String(Native.camGet(path));
        }catch(e){ reject(new Error(String(e))); return; }
        var j = {};
        try{ j = JSON.parse(raw); }catch(e){ reject(new Error('原生桥返回异常')); return; }
        if(!j || !j.s) reject(new Error((j && j.t) ? j.t : '连不上相机'));
        else resolve({status:j.s, text:j.t || '', url:BASE + path});
      });
    }"""
    assert h.count(old) == 1, h.count(old)
    new = """  /* 相机请求：手机端走"异步桥"（原生后台线程发 HTTP，结果推回来）——不占 JS 线程
     桌面/浏览器退回 XHR */
  var _httpCbs = {}, _httpEarly = {};
  window.__om3http = function(id, res){
    var j = {};
    try{ j = (typeof res === 'string') ? JSON.parse(res) : res; }catch(e){ j = {}; }
    var cb = _httpCbs[id];
    if(!cb){ _httpEarly[id] = j; return; }          /* 抢占：回调比注册快，先存着 */
    delete _httpCbs[id];
    if(!j || !j.s) cb.reject(new Error((j && j.t) ? j.t : '连不上相机'));
    else cb.resolve({status:j.s, text:j.t || '', url:BASE});
  };
  function req(path, opt){
    opt = opt || {};
    if(Native && Native.camGetAsync){
      return new Promise(function(resolve, reject){
        var id = '';
        try{
          id = String(opt.body ? Native.camPostAsync(path, b64(opt.body))
                               : Native.camGetAsync(path));
        }catch(e){ reject(new Error(String(e))); return; }
        if(_httpEarly[id]){
          var e0 = _httpEarly[id]; delete _httpEarly[id];
          if(e0 && e0.s) resolve({status:e0.s, text:e0.t || '', url:BASE});
          else reject(new Error((e0 && e0.t) ? e0.t : '连不上相机'));
          return;
        }
        _httpCbs[id] = {resolve:resolve, reject:reject, url:BASE + path};
        setTimeout(function(){
          if(_httpCbs[id]){ delete _httpCbs[id]; reject(new Error('超时（相机没应答）')); }
        }, (opt.timeout || 20000) + 5000);
      });
    }
    if(Native && Native.camGet){
      return new Promise(function(resolve, reject){
        var raw = '';
        try{
          raw = opt.body ? String(Native.camPost(path, b64(opt.body)))
                         : String(Native.camGet(path));
        }catch(e){ reject(new Error(String(e))); return; }
        var j = {};
        try{ j = JSON.parse(raw); }catch(e){ reject(new Error('原生桥返回异常')); return; }
        if(!j || !j.s) reject(new Error((j && j.t) ? j.t : '连不上相机'));
        else resolve({status:j.s, text:j.t || '', url:BASE + path});
      });
    }"""
    h = h.replace(old, new, 1)
    open(P, 'w', encoding='utf-8', newline='').write(h)
    print('页面: req() 改走异步桥（含抢占缓冲 + 超时）')
else:
    print('页面: 已应用过，跳过')
