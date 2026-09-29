# -*- coding: utf-8 -*-
"""① 原生补 onShowFileChooser + onActivityResult → 唤醒安卓文件管理器（导入文件）
   ② 方案列表条目：档位 + 名称，且固定显示"N / 4 个槽位有内容"
   ③ JS 侧放开 accept（*/*），免得文件管理器把 .oes/.json 过滤掉
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
J = r'C:\Users\82302\AppData\Local\Temp\apk\java\com\om3\handbook\MainActivity.java'
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'

# ---------- ① Java ----------
j = open(J, encoding='utf-8').read()
if 'onShowFileChooser' not in j:
    old = """        wv.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {"""
    assert j.count(old) == 1, j.count(old)
    new = """        wv.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, android.webkit.ValueCallback<android.net.Uri[]> cb,
                                             FileChooserParams params) {
                try {
                    if (fileCb != null) { fileCb.onReceiveValue(null); }
                    fileCb = cb;
                    android.content.Intent i = new android.content.Intent(android.content.Intent.ACTION_GET_CONTENT);
                    i.addCategory(android.content.Intent.CATEGORY_OPENABLE);
                    i.setType("*/*");
                    startActivityForResult(android.content.Intent.createChooser(i, "选择方案文件"), 4714);
                    return true;
                } catch (Throwable t) {
                    fileCb = null;
                    Toast.makeText(MainActivity.this, "打不开文件选择器：" + t.getMessage(), Toast.LENGTH_SHORT).show();
                    return false;
                }
            }

            @Override
            public void onPermissionRequest(final PermissionRequest request) {"""
    j = j.replace(old, new, 1)

    # 字段 + onActivityResult
    anchor = "    public class Bridge {"
    assert j.count(anchor) == 1
    j = j.replace(anchor, """    private android.webkit.ValueCallback<android.net.Uri[]> fileCb = null;

    @Override
    protected void onActivityResult(int req, int res, android.content.Intent data) {
        if (req == 4714) {
            android.net.Uri[] out = null;
            if (res == android.app.Activity.RESULT_OK && data != null) {
                if (data.getData() != null) {
                    out = new android.net.Uri[]{ data.getData() };
                } else if (data.getClipData() != null) {
                    int n = data.getClipData().getItemCount();
                    out = new android.net.Uri[n];
                    for (int k = 0; k < n; k++) out[k] = data.getClipData().getItemAt(k).getUri();
                }
            }
            if (fileCb != null) { fileCb.onReceiveValue(out); fileCb = null; }
            return;
        }
        super.onActivityResult(req, res, data);
    }

""" + anchor, 1)
    open(J, 'w', encoding='utf-8', newline='').write(j)
    print('Java: onShowFileChooser + onActivityResult 已加')
else:
    print('Java: 已有，跳过')

# ---------- ②③ 页面 ----------
h = open(P, encoding='utf-8').read()
n0 = len(h)
old_item = """      d.innerHTML = '<div class="t">' + (s.name || '未命名方案') +
        '<span class="mpbadge">' + tierLabel(s.from || 'current') + '</span></div>' +
        '<div class="s">' + (s.desc ? s.desc : (used + ' / 4 个槽位有内容')) + '</div>';"""
assert h.count(old_item) == 1, h.count(old_item)
new_item = """      d.innerHTML = '<div class="t"><span class="mpbadge">' + tierLabel(s.from || 'current') + '</span>' +
        (s.name || '未命名方案') + '</div>' +
        '<div class="s">' + (s.desc ? (s.desc + '　·　') : '') + used + ' / 4 个槽位有内容</div>';"""
h = h.replace(old_item, new_item, 1)

# 导入接受任意文件（避免文件管理器过滤掉 .oes/.json）
h = h.replace("inp.accept = '.json,.oes,application/json,text/xml';", "inp.accept = '*/*';", 1)
# 原生文件选择失败时的可见提示
anchor2 = "  function mpImportAny(){"
assert h.count(anchor2) == 1
h = h.replace(anchor2, """  function mpImportAny(){
    if(!(window.OM3Native && window.OM3Native.shareText) && !window.__OM3_APP__){
      log('（提示：导入文件需要在 app 里运行；网页版请用下载/上传文件的方式）', 'warn');
    }""", 1)

open(P, 'w', encoding='utf-8', newline='').write(h)
print('页面：档位+名称 / 槽位数 / accept 放开（%+d 字节）' % (len(h) - n0))
