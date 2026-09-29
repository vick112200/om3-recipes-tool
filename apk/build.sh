#!/bin/bash
set -e
BASE="/c/Users/82302/AppData/Local/Temp"      # 只放 Android SDK（工具链），源码不在这里
BT="$BASE/sdk/android-14"
AJ="$BASE/sdk/android-34/android.jar"
export JAVA_HOME="C:\\Program Files\\Java\\jdk-20"
export PATH="/c/Program Files/Java/jdk-20/bin:$PATH"
cd "$(dirname "$0")"                          # 在工程自己的 apk/ 目录里构建（以前写死在 Temp/apk → 会打包到旧文件）

echo "== 0/6 版本号自增 + 写入版本徽标"
python bumpver.py

rm -rf build
mkdir -p build/gen build/classes build/dex

echo "== 1/6 aapt2 compile res"
"$BT/aapt2.exe" compile --dir res -o build/res.zip

echo "== 2/6 aapt2 link"
"$BT/aapt2.exe" link \
  -o build/base.apk \
  -I "$AJ" \
  --manifest AndroidManifest.xml \
  -R build/res.zip \
  --java build/gen \
  --min-sdk-version 21 \
  --target-sdk-version 34 \
  -A assets \
  --auto-add-overlay

echo "== 3/6 javac"
javac --release 8 -nowarn -encoding UTF-8 -cp "$AJ" -d build/classes \
  build/gen/com/om3/handbook/R.java \
  java/com/om3/handbook/MainActivity.java

echo "== 4/6 d8"
find build/classes -name '*.class' > build/classlist.txt
"$BT/d8.bat" --release --lib "$AJ" --min-api 21 --output build/dex @build/classlist.txt

echo "== 5/6 打包 dex + zipalign"
python - <<'PY'
import zipfile, shutil, os
shutil.copy('build/base.apk', 'build/withdex.apk')
z = zipfile.ZipFile('build/withdex.apk', 'a', zipfile.ZIP_STORED)
z.write('build/dex/classes.dex', 'classes.dex')
z.close()
print('   classes.dex 已加入 APK')
PY
"$BT/zipalign.exe" -f -p 4 build/withdex.apk build/aligned.apk

echo "== 6/6 签名"
if [ ! -f om3.jks ]; then
  keytool -genkeypair -keystore om3.jks -storepass android -keypass android \
    -alias om3 -keyalg RSA -keysize 2048 -validity 12000 \
    -dname "CN=OM3 Handbook, OU=Personal, O=Personal, L=NA, ST=NA, C=CN"
fi
"$BT/apksigner.bat" sign --ks om3.jks --ks-pass pass:android --key-pass pass:android \
  --out build/om3.apk build/aligned.apk
"$BT/apksigner.bat" verify --print-certs build/om3.apk | head -4
ls -la build/om3.apk
echo "OK"
