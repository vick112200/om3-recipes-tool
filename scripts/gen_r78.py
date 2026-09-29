# -*- coding: utf-8 -*-
"""第 78 轮：真机日志暴露的两个真 bug（见 SPEC-round78.md）

需求方 2026-09-28 发来真机日志 `logs/OM3-真机-2026-09-28-2232.txt`（v3.29 / 安卓 16 / OM-3）。
日志里有 **16 次** `ERR SocketException: Binding socket to network 254/256 failed: EPERM (Operation not permitted)`，
而且"扫到 N 个热点，像相机的有 0 个"却明明已经连着相机。两个都在真机上才暴露：

**bug 1（致命）**：`Network.openConnection()` 绑在**过期的网络句柄**上 → EPERM。
  时间线证据：22:27:37「相机连接断了」→ 22:28:04~22:28:08 连着 15 条 EPERM（①②③ 全挂）→
  22:28:57 重新 requestNetwork 拿到新句柄后 HTTP 又通了（22:29:01 HTTP 200）。
  修法（Java）：① 绑定时出错 → **丢掉缓存句柄 + 退到默认路由重试一次**（手机连的就是相机热点，默认路由也通）
  ② 结果里带 `"w"` 说明"退了默认路由"，页面写进日志 → 以后一眼就看出来。

**bug 2**：`camDirectConnect()` 只认"扫描结果里像相机的热点"。真机上（安卓 16）
  手机**已经连着**相机热点时，扫描可能被系统限流/过滤 → 日志里"像相机的有 0 个" → 判"直连走不通"，
  白等 30 秒再超时。修法（页面）：① 先看 `wifiState().ssid` 是不是相机（或等于记住的 SSID），是就直接进"检测"；
  ② 扫描节流从 5 秒放宽到 **30 秒**（安卓前台限额 4 次/2 分钟），并在结果为空时写明"可能是系统限流"。

顺带（真机已证实的文案修正）：**`<a download>` 在 WebView 里不落文件**（⑦ 你回了"没有"）→
  「下载日志文件」按钮的文案改成实测结论，引导用「分享」/「复制」。

用法：python scripts/gen_r78.py [--check]
"""
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGE = os.path.join(ROOT, 'app', 'base.html')
JAVA = os.path.join(ROOT, 'apk', 'java', 'com', 'om3', 'handbook', 'MainActivity.java')
MARK = 'r78：真机两个 bug'
STEPS = []


def step(label, target='page'):
    def deco(fn):
        STEPS.append((label, target, fn))
        return fn
    return deco


# ---------------------------------------------------------------- Java：绑定失败 → 丢句柄 + 默认路由重试
@step('① Java：Network.openConnection 失败就丢掉句柄、退到默认路由重试一次（修 EPERM）', 'java')
def s_java_retry(html):
    old = ('''        private String camReq(String path, byte[] body, String method) {
            try {
                java.net.URL u = new java.net.URL("http://192.168.0.10/" + path);
                java.net.HttpURLConnection c = (java.net.HttpURLConnection)
                        ((sCamNet != null) ? sCamNet.openConnection(u) : u.openConnection());''')
    assert html.count(old) == 1, 'camReq 的开头没找到（Java 里）'
    new = ('''        private String camReq(String path, byte[] body, String method) {
            String r = camReqOnce(path, body, method, (sCamNet != null));
            if (r != null && r.startsWith("{\\"s\\":0,")
                    && (r.indexOf("EPERM") >= 0 || r.indexOf("Binding socket") >= 0
                        || r.indexOf("SecurityException") >= 0)) {
                /* r78：**真机日志里出现 16 次**：
                   `ERR SocketException: Binding socket to network 254 failed: EPERM (Operation not permitted)`
                   —— 我们缓存的 sCamNet 在"相机休眠/断开"之后就**过期**了，绑上去内核直接拒。
                   时间线（logs/OM3-真机-2026-09-28-2232.txt）：22:27:37 掉线 → 22:28:04~08 连续 15 条 EPERM
                   → 22:28:57 重新 requestNetwork 后 22:29:01 又 HTTP 200。
                   所以：**丢掉过期句柄 + 退到默认路由重试一次**（手机连的就是相机热点，默认路由也通），
                   并把"退到默认路由"写进结果里，页面上能一眼看出来。 */
                sCamNet = null;
                String r2 = camReqOnce(path, body, method, false);
                if (r2 != null && !r2.startsWith("{\\"s\\":0,")) {
                    return r2.substring(0, r2.length() - 1) + ",\\"w\\":\\"bind_fail→default\\"}";
                }
                return r2;
            }
            return r;
        }

        /** 发一次请求；bound=true 时用 sCamNet（绑在相机那条网络），false 时走默认路由 */
        private String camReqOnce(String path, byte[] body, String method, boolean bound) {
            try {
                java.net.URL u = new java.net.URL("http://192.168.0.10/" + path);
                java.net.HttpURLConnection c = (java.net.HttpURLConnection)
                        ((bound && sCamNet != null) ? sCamNet.openConnection(u) : u.openConnection());''')
    return html.replace(old, new, 1)


# ---------------------------------------------------------------- 页面：已经连着相机就别只看扫描
@step('② 页面：扫描里没有相机热点时，先看"手机现在连的是不是相机"（修"像相机的 0 个"误判）')
def s_scan_fallback(html):
    old = "  function camHotspotVisible(){\n    try{\n      var N = window.OM3Native;\n      if(!N) return false;\n      if(N.wifiState){"
    assert html.count(old) == 1, 'camHotspotVisible 没找到'
    new = ('''  /* r78：真机日志里反复出现「扫到 N 个热点，像相机的有 0 个」—— 但那时手机**其实已经连着相机热点**了
     （同日志里 cameraState 就是 {"connected":true,"ssid":"OM-3-P-BJSA21721","bssid":"34:90:EA:BE:07:F8"}）。
     原因：安卓对前台应用的 Wi-Fi 扫描有**限额（4 次/2 分钟）**，超了会返回空/旧结果；
     而且手机正连着某个热点时，系统也可能不再把它列在扫描结果里。
     所以：**"现在连着的 SSID"是最可信的信号**，扫描只当兜底。 */
  function camIsCameraSsid(ssid){
    try{
      if(!ssid) return false;
      if(camLookLikeCamera(String(ssid))) return true;
      var sv = camSaved() || {};
      return !!(sv.ssid && String(ssid) === String(sv.ssid));     /* 记住的那台也算 */
    }catch(e){ return false; }
  }
  function camHotspotVisible(){
    try{
      var N = window.OM3Native;
      if(!N) return false;
      if(N.wifiState){''')
    html = html.replace(old, new, 1)
    # 把 throttle 从 5 秒放宽到 30 秒，并在没结果时说明"可能被限流"
    old2 = ("        if(_hsForce || (now - _hsAt) >= 5000){\n"
            "          _hsForce = false; _hsAt = now;")
    assert html.count(old2) == 1, '节流判断没找到'
    new2 = ("        /* r78：安卓前台扫描限额约 4 次/2 分钟 → 节流放宽到 30 秒（原来是 5 秒，真机上一路被系统吞结果） */\n"
            "        if(_hsForce || (now - _hsAt) >= 30000){\n"
            "          _hsForce = false; _hsAt = now;")
    html = html.replace(old2, new2, 1)
    old3 = ("          _hsVal = found;\n"
            "          try{ if(_hsSkipped){ log('[热点探测] 之前 ' + _hsSkipped + ' 次轮询没重复扫 Wi-Fi（节流 5 秒）', 'ok'); _hsSkipped = 0; } }catch(e2){}")
    assert html.count(old3) == 1, '节流日志那句没找到'
    new3 = ("          if(!found && camIsCameraSsid(camNowSsid())) found = true;   /* r78：扫描说没有，但手机正连着相机 → 以\"已连\"为准 */\n"
            "          _hsVal = found;\n"
            "          try{ if(_hsSkipped){ log('[热点探测] 之前 ' + _hsSkipped + ' 次轮询没重复扫 Wi-Fi（节流 30 秒）', 'ok'); _hsSkipped = 0; } }catch(e2){}\n"
            "          try{ if(!found){ var _L = []; try{ _L = JSON.parse(raw) || []; }catch(e5){}\n"
            "                 if(_L.length === 0) log('[热点探测] 这次扫描一个热点都没返回 —— 多半是被安卓限流了（前台限额 4 次/2 分钟），不是没热点', 'warn');\n"
            "               } }catch(e6){}")
    html = html.replace(old3, new3, 1)
    return html


@step('② 加 camNowSsid() 小工具（读当前连着的 SSID，给上面用）')
def s_now_ssid(html):
    old = "  function camIsCameraSsid(ssid){"
    assert html.count(old) == 1, 'camIsCameraSsid 没找到'
    new = ('''  function camNowSsid(){
    try{
      var N = window.OM3Native;
      if(!N || !N.wifiState) return '';
      var o = JSON.parse(String(N.wifiState() || '{}') || '{}');
      return (o && o.ssid) ? String(o.ssid).replace(/"/g, '') : '';
    }catch(e){ return ''; }
  }
  function camIsCameraSsid(ssid){''')
    return html.replace(old, new, 1)


@step('③ 直连：扫不到相机热点时，先看"手机现在连的就是相机吗"再下结论')
def s_direct_hint(html):
    # 真正的调用点是带 reason 的这一行（在 camWifiChain 的 wifi() 里）
    old = "        step('第 3/3 步：直连走不通（' + reason + '）→ 改用「记住的凭据」这条路', 'warn');"
    assert html.count(old) == 1, '直连失败那句没找到'
    new = ("""        /* r78：真机上"像相机的 0 个"经常是**假象**（手机正连着相机 / 扫描被安卓限流）。
           下结论之前先问一句"现在连的是不是相机"，是就说清 —— 别甩一句"直连走不通"误导人。 */
        var _uvNow = camNowSsid();
        if(camIsCameraSsid(_uvNow)){
          step('（说明）这次扫描没列出相机热点，但**手机现在就连在 ' + _uvNow + ' 上** —— 先直接检测 HTTP', 'warn');
        }
""" + old)
    return html.replace(old, new, 1)


@step('④ 「下载日志文件」文案改成真机实测结论（WebView 不落文件）')
def s_dl_text(html):
    old = '<span class="camloghint">怎么发我，就这三步：'
    assert html.count(old) == 1, '日志卡文案没找到'
    new = ('<span class="camloghint">怎么发我，就这三步：'
           '（<b>别用「下载日志文件」</b>：2026-09-28 真机实测 —— 安卓 WebView 不接管下载，点了不会有文件）')
    html = html.replace(old, new, 1)
    old2 = "    line(log3, '日志文件已生成（在「下载」文件夹里）。"
    assert html.count(old2) == 1, '下载日志那句没找到'
    new2 = "    line(log3, '（本机实测：安卓 WebView 不接管下载，大概率「下载」里不会有文件 —— 用「分享日志」或「复制全部日志」）日志文件已生成（在「下载」文件夹里）。"
    return html.replace(old2, new2, 1)


def run(html):
    changed = []
    for label, target, fn in STEPS:
        if target != 'page':
            continue                      # Java 那步在 main() 里单独跑（文件不同）
        before = html
        try:
            html = fn(html)
        except AssertionError as e:
            raise AssertionError('第「%s」步失败：%s' % (label, e or '锚点没找到'))
        except ValueError as e:
            raise AssertionError('第「%s」步失败（找不到锚点）：%s' % (label, e))
        if html == before:
            raise AssertionError('这一步什么都没改：' + label)
        changed.append(label)
    html = html.replace('  /* r78：真机日志里反复出现',
                        '  /* %s：真机日志里反复出现' % MARK, 1)
    assert MARK in html, '页面标记没插进去'
    return html, changed


def main():
    html = io.open(PAGE, encoding='utf-8').read()
    java = io.open(JAVA, encoding='utf-8').read()
    if MARK in html:
        print('[r78] 已经是目标状态 —— 不重复改。')
        return 0
    # Java 那一步单独跑（文件不同）
    java_new = None
    for label, target, fn in STEPS:
        if target == 'java':
            try:
                java_new = fn(java)
            except AssertionError as e:
                print('[r78] ✗ Java 那步失败：%s —— **不写盘**' % e)
                return 1
    if java_new is None:
        print('[r78] ✗ 没找到 Java 那一步')
        return 1
    try:
        new, changed = run(html)
    except AssertionError as e:
        print('[r78] ✗ %s —— **不写盘**' % e)
        return 1
    if '--check' in sys.argv:
        print('[r78] --check：Java 1 步 + 页面 %d 步都能跑通（未写盘）：' % len(changed))
        for c in changed:
            print('   · ' + c)
        return 0
    io.open(JAVA, 'w', encoding='utf-8', newline='').write(java_new)
    io.open(PAGE, 'w', encoding='utf-8', newline='').write(new)
    print('[r78] ✓ Java 1 步（EPERM 重试）+ 页面 %d 步' % len(changed))
    print('[r78] 页面净增 %d 字节' % (len(new.encode('utf-8'))
                                     - len(io.open(os.path.join(ROOT, 'app', 'base.before_r78.html'),
                                                   encoding='utf-8').read().encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
