# -*- coding: utf-8 -*-
"""纯 Python 解包 APK 里的 resources.arsc（本机没有 aapt/aapt2/java，所以自己写）。

用途：官方 App（OI.Share）里 `str.PairingCameraSsid` / `str.bleName` 这类是
SharedPreferences 的 key，真正的中文/日文文案和「相机一览表」都在资源里；
要拿到真值必须解 resources.arsc。

用法（默认读工程根目录的 `om share.apk`）：
  python official_app/arsc.py --list                       # 全部条目（TSV：id/config/type/name/value）
  python official_app/arsc.py --name blePass               # 名字含子串的条目
  python official_app/arsc.py --value 4f3ec7b8             # 值含子串的条目
  python official_app/arsc.py --type string                # 只看某类型（string/string-array/array/color…）
  python official_app/arsc.py --locale ja                  # 只看某语言配置（default/en/ja/zh…）
  python official_app/arsc.py --stats                      # 类型/包统计

实现说明（AOSP 结构，全部小端）：
  ResChunk_header     type u16, headerSize u16, size u32
  0x0002 RES_TABLE    headerSize 12：packageCount u32，随后是若干 chunk
  0x0001 STRING_POOL  stringCount/styleCount/flags/stringsStart/stylesStart
  0x0200 PACKAGE      id u32, name 128*u16, typeStrings u32, lastPublicType u32,
                      keyStrings u32, lastPublicKey u32
  0x0201 TYPE         id u8, flags u8, reserved u16, entryCount u32, entriesStart u32, config
                      flags&0x01 = SPARSE(u16 idx + u16 offset/4)，flags&0x02 = OFFSET16(u16，0xFFFF=空)
  0x0202 TYPE_SPEC    同上但不含值
  ResTable_entry      size u16, flags u16, key u32；flags&1 = 复杂条目(数组)
  Res_value           size u16, res0 u8, dataType u8, data u32
"""
import io
import os
import re
import struct
import sys
import zipfile
import collections

sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_APK = os.path.join(ROOT, 'om share.apk')

RES_STRING_POOL = 0x0001
RES_TABLE = 0x0002
RES_TABLE_PACKAGE = 0x0200
RES_TABLE_TYPE = 0x0201
RES_TABLE_TYPE_SPEC = 0x0202

FLAG_SPARSE = 0x01
FLAG_OFFSET16 = 0x02

ENTRY_FLAG_COMPLEX = 0x0001
ENTRY_FLAG_COMPACT = 0x0008

DT = {0x00: 'null', 0x01: 'ref', 0x02: 'attr', 0x03: 'string', 0x04: 'float', 0x05: 'dim',
      0x06: 'frac', 0x07: 'dynref', 0x08: 'dynattr', 0x10: 'int', 0x11: 'hex',
      0x12: 'bool', 0x1c: 'argb8', 0x1d: 'rgb8', 0x1e: 'argb4', 0x1f: 'rgb4'}


def u16(b, o):
    return struct.unpack_from('<H', b, o)[0]


def u32(b, o):
    return struct.unpack_from('<I', b, o)[0]


class Pool(object):
    """ResStringPool：UTF-8 / UTF-16 两种编码都要处理。"""

    def __init__(self, buf, off):
        self.buf = buf
        self.off = off
        hdr = off
        count = u32(buf, hdr + 8)
        flags = u32(buf, hdr + 16)
        strings_start = u32(buf, hdr + 20)
        self.utf8 = bool(flags & 0x100)
        self.strings = []
        self._base = hdr + strings_start
        offs = hdr + u16(buf, hdr + 2)  # headerSize
        for i in range(count):
            so = offs + 4 * i
            if so + 4 > len(buf):
                break
            self.strings.append(self._read(u32(buf, so)))

    def _len8(self, p):
        b0 = self.buf[p]
        if b0 & 0x80:
            return ((b0 & 0x7f) << 8) | self.buf[p + 1], p + 2
        return b0, p + 1

    def _len16(self, p):
        v = u16(self.buf, p)
        if v & 0x8000:
            v = ((v & 0x7fff) << 16) | u16(self.buf, p + 2)
            return v, p + 4
        return v, p + 2

    def _read(self, off):
        """off = 相对字符串数据区（stringsStart）的字节偏移。"""
        if off is None or off < 0:
            return ''
        p = self._base + off
        if p < 0 or p >= len(self.buf):
            return ''
        try:
            if self.utf8:
                _, p = self._len8(p)          # 字符数（用不到）
                n, p = self._len8(p)          # 字节数
                return self.buf[p:p + n].decode('utf-8', 'replace')
            n, p = self._len16(p)
            return self.buf[p:p + 2 * n].decode('utf-16le', 'replace')
        except Exception:
            return ''

    def get(self, idx):
        if idx is None or idx < 0 or idx >= len(self.strings):
            return None
        return self.strings[idx]

    def __len__(self):
        return len(self.strings)


def _fix_pool_read(pool, idx):
    return pool.get(idx)


def config_str(buf, off, size):
    """ResTable_config → 'default' / 'ja' / 'en-rUS' / 'xxhdpi' 这样的可读名。"""
    lang = buf[off + 8:off + 10]
    country = buf[off + 10:off + 12]
    parts = []
    try:
        l = lang.decode('ascii').rstrip('\x00')
        c = country.decode('ascii').rstrip('\x00')
    except Exception:
        l, c = '', ''
    if l:
        parts.append(l + (('-r' + c) if c else ''))
    if size >= 16:
        density = u16(buf, off + 14)
        dmap = {0: 'default', 120: 'ldpi', 160: 'mdpi', 213: 'tvdpi', 240: 'hdpi',
                320: 'xhdpi', 480: 'xxhdpi', 640: 'xxxhdpi', 0xFFFE: 'anydpi'}
        if density:
            parts.append(dmap.get(density, 'dpi%d' % density))
    return '-'.join(parts) if parts else 'default'


def parse(path):
    """返回 (entries, stats)；entries 元素：dict(id, config, type, name, value, kind, extra)"""
    z = zipfile.ZipFile(path)
    data = z.read('resources.arsc')
    total = u32(data, 4)
    global_pool = None
    entries = []
    pkg_names = {}
    off = u16(data, 2)
    while off < min(total, len(data)):
        ctype = u16(data, off)
        hsize = u16(data, off + 2)
        csize = u32(data, off + 4)
        if csize <= 0:
            break
        if ctype == RES_STRING_POOL and global_pool is None:
            global_pool = Pool(data, off)
        elif ctype == RES_TABLE_PACKAGE:
            pkg_id = u32(data, off + 8)
            name = data[off + 12:off + 12 + 256].decode('utf-16le', 'replace').rstrip('\x00')
            pkg_names[pkg_id] = name
            type_off = off + u32(data, off + 268)
            key_off = off + u32(data, off + 276)
            types = Pool(data, type_off)
            keys = Pool(data, key_off)
            p = off + hsize
            end = off + csize
            while p < end:
                t = u16(data, p)
                ts = u32(data, p + 4)
                if ts <= 0:
                    break
                if t == RES_TABLE_TYPE:
                    _parse_type(data, p, pkg_id, types, keys, global_pool, entries)
                p += ts
        off += csize
    return entries, pkg_names


def _parse_type(data, off, pkg_id, types, keys, gpool, out):
    hsize = u16(data, off + 2)
    tid = data[off + 8]
    flags = data[off + 9]
    entry_count = u32(data, off + 12)
    entries_start = u32(data, off + 16)
    cfg_off = off + 20
    cfg = config_str(data, cfg_off, hsize - 20)
    type_name = _fix_pool_read(types, tid - 1) or ('type%d' % tid)
    if flags & FLAG_SPARSE:
        idxs = []
        for i in range(entry_count):
            so = off + hsize + 4 * i
            if so + 4 > len(data):
                break
            eid = u16(data, so)
            eoff = u16(data, so + 2) * 4
            idxs.append((eid, eoff))
    else:
        idxs = []
        for i in range(entry_count):
            so = off + hsize + (2 if flags & FLAG_OFFSET16 else 4) * i
            if so + 4 > len(data):
                break
            eoff = u16(data, so) * 4 if flags & FLAG_OFFSET16 else u32(data, so)
            if eoff == 0xFFFFFFFF or (flags & FLAG_OFFSET16 and u16(data, so) == 0xFFFF):
                continue
            idxs.append((i, eoff))
    for eid, eoff in idxs:
        ep = off + entries_start + eoff
        if ep + 8 > len(data):
            continue
        size = u16(data, ep)
        eflags = u16(data, ep + 2)
        keyidx = u32(data, ep + 4)
        name = _fix_pool_read(keys, keyidx) or '?'
        rid = 0x01000000 | (pkg_id << 24) | (tid << 16) | eid  # 仅备用
        rid = '%d:%d:%d' % (pkg_id, tid, eid) if False else '0x%02x%02x%04x' % (pkg_id, tid, eid)
        if eflags & ENTRY_FLAG_COMPLEX:
            cnt = u32(data, ep + 12)
            mp = ep + u16(data, ep)
            vals = []
            for i in range(cnt):
                q = mp + 12 * i
                if q + 12 > len(data):
                    break
                mname = u32(data, q)
                dt = data[q + 7]
                dv = u32(data, q + 8)
                v, kind = _value(dt, dv, gpool)
                vals.append('%02x:%s' % ((mname >> 24) & 0xff, v))
            out.append(dict(id=rid, config=cfg, type=type_name, name=name,
                            value=' | '.join(vals), kind='complex'))
        elif eflags & ENTRY_FLAG_COMPACT:
            dt = (size >> 8) & 0xff
            v, kind = _value(dt, keyidx, gpool)
            out.append(dict(id=rid, config=cfg, type=type_name, name=name,
                            value=v, kind='compact:' + kind))
        else:
            vp = ep + size
            if vp + 8 > len(data):
                continue
            dt = data[vp + 3]
            dv = u32(data, vp + 4)
            v, kind = _value(dt, dv, gpool)
            out.append(dict(id=rid, config=cfg, type=type_name, name=name, value=v, kind=kind))


def _value(dt, dv, gpool):
    k = DT.get(dt, 'dt%02x' % dt)
    if dt == 0x03:
        return (_fix_pool_read(gpool, dv) or ''), k
    if dt == 0x01:
        return '@0x%08x' % dv, k
    if dt == 0x12:
        return ('true' if dv else 'false'), k
    if dt == 0x1c:
        return '#%08x' % dv, k
    if dt in (0x04,):
        import struct as _s
        return str(_s.unpack('<f', _s.pack('<I', dv))[0]), k
    return str(dv), k


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 1
    apk = DEFAULT_APK
    if len(a) >= 2 and a[0] == '--apk':
        apk = a[1]
        a = a[2:]
    if not a:
        print(__doc__)
        return 1
    entries, pkgs = parse(apk)
    print('# %s：包 %s，条目 %d' % (os.path.basename(apk), pkgs, len(entries)), file=sys.stderr)
    if a[0] == '--stats':
        c = collections.Counter(e['type'] for e in entries)
        for t, n in c.most_common():
            print('%6d  %s' % (n, t))
        return 0
    rows = entries
    if a[0] == '--name':
        rows = [e for e in rows if a[1] in e['name']]
    elif a[0] == '--value':
        rows = [e for e in rows if a[1] in (e['value'] or '')]
    elif a[0] == '--type':
        rows = [e for e in rows if a[1] in e['type']]
    elif a[0] == '--locale':
        rows = [e for e in rows if a[1] in e['config']]
    elif a[0] != '--list':
        print(__doc__)
        return 1
    for e in rows:
        print('%s\t%s\t%s\t%s\t%s' % (e['id'], e['config'], e['type'], e['name'], e['value']))
    print('# %d 条' % len(rows), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
