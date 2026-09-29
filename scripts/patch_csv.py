# -*- coding: utf-8 -*-
"""备份读分块修好：
- 相机返回的是 multipart（OIShareFormBoundary + text/xml 头 + text/csv 数据）→ 要解析出 CSV 部分
- 第二块 520 的原因候选：需要重新 request_getmysetdata 重新武装 / 需要小块间隔 → 加"每块前重新 request + 间隔 + 失败重试一次"
"""
import sys

sys.stdout.reconfigure(encoding='utf-8')
P = r'C:\Users\82302\AppData\Local\Temp\app\base.html'
h = open(P, encoding='utf-8').read()

OLD = """        var parts = [], off = 0, guard = 0;
        var CHUNK = 20000;
        while(off < size && guard++ < 400){
          var n = Math.min(CHUNK, size - off);
          var r4 = await req('get_partialmysetdata.cgi?kind=current&offset=' + off + '&size=' + n);
          if(r4.status !== 200){ line(o2, '   第 ' + guard + ' 块 HTTP ' + r4.status, 'err'); break; }
          parts.push(r4.text); off += n;
        }
        backupText = parts.join('');"""
assert h.count(OLD) == 1, h.count(OLD)

NEW = """        var parts = [], off = 0, guard = 0;
        var CHUNK = 20000;
        while(off < size && guard++ < 400){
          var n = Math.min(CHUNK, size - off);
          var r4 = await req('get_partialmysetdata.cgi?kind=current&offset=' + off + '&size=' + n, {timeout: 20000});
          if(r4.status !== 200){
            /* 相机偶尔对连续分块回 520：重新武装一次 + 等 0.8 秒 再试一次 */
            line(o2, '   第 ' + guard + ' 块 HTTP ' + r4.status + '（重新请求后再试）', 'warn');
            try{ await req('request_getmysetdata.cgi?mode=' + t0 + '&kind=current', {timeout: 20000}); }catch(e){}
            await sleep(800);
            r4 = await req('get_partialmysetdata.cgi?kind=current&offset=' + off + '&size=' + n, {timeout: 20000});
          }
          if(r4.status !== 200){ line(o2, '   第 ' + guard + ' 块 HTTP ' + r4.status + '，停止', 'err'); break; }
          var csv = om3CsvPart(r4.text);
          parts.push(csv);
          off += n;
          if(guard % 1 === 0) line(o2, '   第 ' + guard + ' 块：HTTP 200，原始 ' + r4.text.length + ' 字符，取出数据 ' + csv.length + ' 字符，累计 ' + parts.join('').length);
          if(csv.length === 0) { line(o2, '   （这块没解析出数据，可能是空块或格式变了）', 'warn'); }
          await sleep(120);
        }
        backupText = parts.join('');"""
h = h.replace(OLD, NEW, 1)

# 解析器：从 multipart 里取出 text/csv（没有就取最大的一段）
ANCHOR = "  function sizeFrom("
assert h.count(ANCHOR) == 1
PARSER = """  /* 相机返回的是 multipart：OIShareFormBoundary + text/xml 头 + text/csv 数据 */
  function om3CsvPart(txt){
    txt = String(txt || '');
    try{
      /* 按 boundary 切段，挑出声明 text/csv 的那一段 */
      var m = txt.match(/^--+(\\S+)/m);
      if(m){
        var segs = txt.split('--' + m[1]);
        var best = '';
        for(var i=0;i<segs.length;i++){
          var s0 = segs[i];
          var head = s0.split(/\\r?\\n\\r?\\n/)[0] || '';
          var body = s0.split(/\\r?\\n\\r?\\n/).slice(1).join('\\r\\n\\r\\n');
          if(/text\\/csv/i.test(head) && body.length > best.length) best = body;
          else if(!best && body.length > 0) best = body;
        }
        if(best) return best.replace(/\\r?\\n$/, '');
      }
    }catch(e){}
    return txt;
  }
  window.__om3csvPart = om3CsvPart;
"""
h = h.replace(ANCHOR, PARSER + ANCHOR, 1)

# 预览改成"解析后的前 400 字符"，方便核对真是 CSV
h = h.replace("line(o2, '前 400 字符预览：' + backupText.slice(0, 400));",
              "line(o2, '前 400 字符预览：' + om3CsvPart(backupText).slice(0, 400));", 1)
open(P, 'w', encoding='utf-8', newline='').write(h)
print('备份分块：加 multipart 解析 + 失败重新武装/重试 + 每块明细')
