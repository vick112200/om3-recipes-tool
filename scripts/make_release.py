# -*- coding: utf-8 -*-
"""发布到 GitHub Releases（一键）。

用法：
    python scripts/make_release.py              # 用 apk/AndroidManifest.xml 里的 versionName
    python scripts/make_release.py --list       # 看现有 release
    python scripts/make_release.py --ver 3.46   # 手动指定版本（不如自动可靠）

它做什么：
  1. 从 apk/AndroidManifest.xml 读 versionName（3.45）→ tag `v3.45`、资产名 `om3-recipes-tool-v3.45.apk`
  2. release 不存在就建（标题/正文自动生成），已存在就复用
  3. 同名资产先删再传（所以重跑是幂等的，不会堆一串重复文件）
  4. 打印 release 页面 + 直链

凭据：用 git 凭据助手里已经存好的 GitHub token（本机 push 过就有），不需要另配 PAT，
      也不会把 token 打印出来。没有凭据时会提示先 `git push` 一次登录。
"""
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = 'vick112200/om3-recipes-tool'
MANIFEST = os.path.join(ROOT, 'apk', 'AndroidManifest.xml')
APK = os.path.join(ROOT, 'apk', 'build', 'om3.apk')

BODY_TMPL = '''把 **80 条 OM-3 / OM System 彩色配方**装进手机：离线查、按场景挑、直接写进相机。

**下载**：`{asset}`（{mb:.1f} MB，Android 8.0+）

**安装**：下载后在手机上直接打开安装（首次需在系统设置里允许"安装未知来源应用"）。
签名固定，以后新版本可以**直接覆盖升级**，数据不会丢。

### 第一次用（连相机三步）
1. 相机上开 Wi-Fi：`MENU → Wi-Fi/蓝牙 → 连接到智能手机`（屏幕会显示 SSID / 密码 / 二维码）
2. App 里点「**连接相机**」；相机屏幕上有二维码就点「**扫码连接**」扫它
3. 「检测相机」→ 导入配方 / 写配方；写完在相机上选 C1–C4

> 相机 Wi-Fi 请在相机上开（App 不会替你开）。
> 纯浏览器也能用：仓库里的 `app/base.html` 双击打开就是完整手册（连接相机功能只在 App 里可用）。
'''


def ver_from_manifest():
    m = re.search(r'android:versionName="([0-9.]+)"', io_open(MANIFEST))
    if not m:
        raise SystemExit('apk/AndroidManifest.xml 里没找到 versionName')
    return m.group(1)


def io_open(p):
    import io
    return io.open(p, encoding='utf-8').read()


def token():
    p = subprocess.run(['git', 'credential', 'fill'], cwd=ROOT, input='protocol=https\nhost=github.com\n\n',
                       capture_output=True, text=True)
    for line in (p.stdout or '').splitlines():
        if line.startswith('password='):
            return line[len('password='):]
    raise SystemExit('拿不到 GitHub 凭据：先在本仓库 git push 一次（会弹登录）')


def api(method, url, data=None, ctype='application/json'):
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', 'Bearer ' + TOKEN)
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('User-Agent', 'om3-release')
    req.add_header('Content-Type', ctype)
    try:
        with urllib.request.urlopen(req, timeout=3600) as r:
            return r.status, json.loads(r.read().decode('utf-8') or '{}')
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8') or '{}')


TOKEN = token()

if '--list' in sys.argv:
    st, rel = api('GET', 'https://api.github.com/repos/%s/releases' % REPO)
    for r in (rel if isinstance(rel, list) else []):
        print('%-8s %-34s %s' % (r['tag_name'], r['name'], r['html_url']))
    sys.exit(0)

ver = None
if '--ver' in sys.argv:
    ver = sys.argv[sys.argv.index('--ver') + 1]
ver = ver or ver_from_manifest()
TAG, ASSET = 'v' + ver, 'om3-recipes-tool-v%s.apk' % ver
if not os.path.exists(APK):
    raise SystemExit('没有 apk/build/om3.apk —— 先出包（cd apk && bash build.sh）')
mb = os.path.getsize(APK) / 1048576.0
print('版本 %s → tag %s，资产 %s（%.1f MB）' % (ver, TAG, ASSET, mb))

st, rel = api('GET', 'https://api.github.com/repos/%s/releases/tags/%s' % (REPO, TAG))
if st == 200:
    print('release %s 已存在（id=%s）→ 复用' % (TAG, rel['id']))
else:
    st, rel = api('POST', 'https://api.github.com/repos/%s/releases' % REPO,
                  json.dumps({'tag_name': TAG, 'target_commitish': 'main',
                              'name': 'om3 recipes tool %s' % TAG,
                              'body': BODY_TMPL.format(asset=ASSET, mb=mb),
                              'draft': False, 'prerelease': False},
                             ensure_ascii=False).encode('utf-8'))
    print('创建 release：HTTP %s' % st)
    if st not in (200, 201):
        raise SystemExit('创建失败：%s' % json.dumps(rel, ensure_ascii=False)[:400])

st, assets = api('GET', 'https://api.github.com/repos/%s/releases/%s/assets' % (REPO, rel['id']))
for a in (assets if isinstance(assets, list) else []):
    if a['name'] == ASSET:
        api('DELETE', 'https://api.github.com/repos/%s/releases/assets/%s' % (REPO, a['id']))
        print('删掉同名旧资产（重跑幂等）')

print('上传中 …')
st, res = api('POST', 'https://uploads.github.com/repos/%s/releases/%s/assets?name=%s' % (REPO, rel['id'], ASSET),
              open(APK, 'rb').read(), 'application/vnd.android.package-archive')
print('上传结果：HTTP %s' % st)
if st not in (200, 201):
    raise SystemExit('上传失败：%s' % json.dumps(res, ensure_ascii=False)[:400])
print('  · 直链：%s' % res['browser_download_url'])
print('  · 大小：%.1f MB（state=%s）' % (res['size'] / 1048576.0, res['state']))
print('  · 页面：%s' % rel['html_url'])
