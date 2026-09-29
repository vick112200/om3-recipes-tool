# -*- coding: utf-8 -*-
"""备份读取策略改进：先试"一次读完"，不行再分块；分块失败时再试另一种 offset 口径。"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()

OLD_START = "        var parts = [], off = 0, guard = 0;\n        var CHUNK = 20000;"
i = h.find(OLD_START)
assert i > 0
j = h.find("        backupText = parts.join('');", i)
assert j > i
j += len("        backupText = parts.join('');")

NEW = """        /* 策略：先试一次读完（相机一次能吐完就最省事）；不行再分块，分块失败再换 offset 口径 */
        var fullR = await req('get_partialmysetdata.cgi?kind=current&offset=0&size=' + size, {timeout: 40000});
        line(o2, '   一次读完尝试：HTTP ' + fullR.status + '，原始 ' + fullR.text.length + ' 字符');
        var full = (fullR.status === 200) ? om3CsvPart(fullR.text) : '';
        if(full.length >= size - 200){
          backupText = full;
          line(o2, '   一次读完成功：拿到 ' + full.length + ' 字符', 'ok');
        } else {
          if(full) line(o2, '   一次读只拿到 ' + full.length + '（不足 ' + size + '），转分块', 'warn');
          var parts = [], off = 0, guard = 0, rawAvail = 0;
          var CHUNK = 20000;
          while(off < size && guard++ < 400){
            var n = Math.min(CHUNK, size - off);
            var r4 = await req('get_partialmysetdata.cgi?kind=current&offset=' + off + '&size=' + n, {timeout: 20000});
            if(r4.status !== 200){
              line(o2, '   第 ' + guard + ' 块 offset=' + off + ' HTTP ' + r4.status + '（重装请求后重试）', 'warn');
              try{ await req('request_getmysetdata.cgi?mode=' + t0 + '&kind=current', {timeout: 20000}); }catch(e){}
              await sleep(900);
              r4 = await req('get_partialmysetdata.cgi?kind=current&offset=' + off + '&size=' + n, {timeout: 20000});
            }
            if(r4.status !== 200 && rawAvail){
              /* 换一种 offset 口径再试（把 multipart 头也算进去的那一种） */
              var alt = rawAvail;
              line(o2, '   第 ' + guard + ' 块换 offset=' + alt + ' 再试', 'warn');
              r4 = await req('get_partialmysetdata.cgi?kind=current&offset=' + alt + '&size=' + n, {timeout: 20000});
              if(r4.status === 200) off = alt;
            }
            if(r4.status !== 200){ line(o2, '   第 ' + guard + ' 块 HTTP ' + r4.status + '，停止', 'err'); break; }
            rawAvail += r4.text.length;
            var csv = om3CsvPart(r4.text);
            parts.push(csv);
            off += n;
            line(o2, '   第 ' + guard + ' 块：HTTP 200，原始 ' + r4.text.length + '，取出 ' + csv.length + '，累计 ' + parts.join('').length);
            await sleep(120);
          }
          backupText = parts.join('');
        }"""
h = h[:i] + NEW + h[j:]

open(P, 'w', encoding='utf-8', newline='').write(h)
print('备份读取：一次读完优先 + 分块兜底 + offset 口径切换')
