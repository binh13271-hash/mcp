"""Đọc bản vẽ DXF để đối chiếu khối lượng: đếm đối tượng, đo phần giao đối tượng với vùng hatch.

Rút từ đợt kiểm KL một dự án đường đô thị (25/09/2026):
  - Đếm theo HÌNH HỌC (block, hình chữ nhật kín), không đếm nhãn chữ: nhãn "1.2x1.6" đếm ra
    90 trong khi KLCT ghi 84 — đúng là thiếu 6 hố nhánh, nhưng nhãn cũng có thể lặp/thiếu.
  - Diện tích lát theo nhãn Slg có thể ĐÃ khoét bồn cây trong hatch; trừ thêm đủ 239 bồn ở bảng
    tính là trừ lặp. Phải đo từng đối tượng: nằm trong vùng lát bao nhiêu %, có trùng lỗ khoét không.

Chỉ ĐỌC. DWG phải chuyển DXF trước (ODA File Converter / AutoCAD DXFOUT).
"""
import math
import re
from collections import Counter

try:
    import ezdxf
    from ezdxf import bbox as _bbox
    from ezdxf import path as _path
    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False

try:
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

_NHAN = re.compile(r"(HG\s*\d+'?|HTBS\s*\d+|HCQ\s*\d+|\d[.,]\d+\s*[xX]\s*\d[.,]\d+)")


def _can(ezdxf_=True, shapely_=False):
    thieu = []
    if ezdxf_ and not HAS_EZDXF:
        thieu.append("ezdxf")
    if shapely_ and not HAS_SHAPELY:
        thieu.append("shapely")
    if thieu:
        raise RuntimeError(f"Thiếu thư viện {', '.join(thieu)}: pip install {' '.join(thieu)}")


def _do_dai(e):
    t = e.dxftype()
    try:
        if t == "LINE":
            return e.dxf.start.distance(e.dxf.end)
        if t == "ARC":
            return math.radians((e.dxf.end_angle - e.dxf.start_angle) % 360) * e.dxf.radius
        if t in ("LWPOLYLINE", "POLYLINE"):
            v = list(_path.make_path(e).flattening(0.01))
            return sum(p.distance(q) for p, q in zip(v, v[1:]))
    except Exception:
        return 0.0
    return 0.0


def _chu_nhat(e):
    """Kích thước 'axb' (a<=b, làm tròn 0,01) nếu là LWPOLYLINE kín 4 cạnh vuông; không thì None."""
    if e.dxftype() != "LWPOLYLINE" or not e.closed:
        return None
    p = [tuple(x[:2]) for x in e.get_points()]
    if len(p) == 5 and math.dist(p[0], p[-1]) < 1e-6:
        p = p[:-1]
    if len(p) != 4:
        return None
    c = [math.dist(p[i], p[(i + 1) % 4]) for i in range(4)]
    cheo = [math.dist(p[0], p[2]), math.dist(p[1], p[3])]
    if abs(c[0] - c[2]) > 0.01 or abs(c[1] - c[3]) > 0.01 or abs(cheo[0] - cheo[1]) > 0.01:
        return None
    return "%.2fx%.2f" % tuple(sorted((c[0], c[1])))


def dem_doi_tuong(duong_dan_dxf, loc_layer=None, max_dong=40):
    """Đếm đối tượng trong model space: block, hình chữ nhật kín, chiều dài, diện tích hatch, nhãn.

    loc_layer: regex lọc tên layer (None = tất cả). Trả chuỗi bảng gọn.
    """
    _can()
    d = ezdxf.readfile(duong_dan_dxf)
    m = d.modelspace()
    loc = re.compile(loc_layer, re.I) if loc_layer else None
    ins, cn, dai, hat, nhan = Counter(), Counter(), Counter(), Counter(), Counter()
    for e in m:
        L = e.dxf.layer
        if loc and not loc.search(L):
            continue
        t = e.dxftype()
        if t == "INSERT":
            ins[(e.dxf.name, L)] += 1
        elif t in ("LINE", "ARC", "LWPOLYLINE", "POLYLINE"):
            dai[L] += _do_dai(e)
            r = _chu_nhat(e)
            if r:
                cn[(r, L)] += 1
        elif t == "HATCH":
            try:
                hat[L] += _dien_tich_hatch(e)
            except Exception:
                pass
        elif t in ("TEXT", "MTEXT"):
            s = e.plain_text() if t == "MTEXT" else e.dxf.text
            for k in _NHAN.findall(s or ""):
                nhan[re.sub(r"\s+", "", k.replace(",", "."))] += 1
    dv = d.header.get("$INSUNITS", 0)
    ra = [f"File {duong_dan_dxf} · đơn vị $INSUNITS={dv} (6 = mét, 4 = mm)"]

    def bang(tieu_de, cot, du_lieu, fmt):
        ra.append(f"# {tieu_de}: {cot}")
        items = du_lieu.most_common()
        for k, v in items[:max_dong]:
            ra.append(fmt(k, v))
        if len(items) > max_dong:
            ra.append(f"... còn {len(items) - max_dong} dòng (tăng max_dong hoặc dùng loc_layer)")

    bang("BLOCK", "ten|layer|so_luong", ins, lambda k, v: f"I|{k[0]}|{k[1]}|{v}")
    bang("HÌNH CHỮ NHẬT KÍN", "kich_thuoc|layer|so_luong", cn, lambda k, v: f"R|{k[0]}|{k[1]}|{v}")
    bang("CHIỀU DÀI theo layer", "layer|dai", dai, lambda k, v: f"L|{k}|{v:.2f}")
    bang("DIỆN TÍCH HATCH (đã trừ lỗ khoét)", "layer|dien_tich", hat, lambda k, v: f"H|{k}|{v:.2f}")
    bang("NHÃN CHỮ — chỉ để đối chiếu, KHÔNG dùng làm số lượng", "nhan|so_lan", nhan, lambda k, v: f"T|{k}|{v}")
    return "\n".join(ra)


def _vong_hatch(h):
    """Các vòng biên của hatch -> list Polygon shapely (chưa xử lý lỗ)."""
    vong = []
    for p in _path.from_hatch(h):
        pts = [(v.x, v.y) for v in p.flattening(0.01)]
        if len(pts) >= 3:
            pg = Polygon(pts)
            if not pg.is_valid:
                pg = pg.buffer(0)
            if pg.area > 0:
                vong.append(pg)
    return vong


def vung_hatch(h):
    """Vùng tô thật của hatch: quy tắc chẵn-lẻ (vòng lồng trong vòng = lỗ khoét)."""
    _can(shapely_=True)
    vung = None
    for pg in sorted(_vong_hatch(h), key=lambda x: -x.area):
        vung = pg if vung is None else vung.symmetric_difference(pg)
    return vung


def _dien_tich_hatch(h):
    if HAS_SHAPELY:
        v = vung_hatch(h)
        return v.area if v is not None else 0.0
    vong = sorted((abs(ezdxf.math.area(list(p.flattening(0.01)))) for p in _path.from_hatch(h)), reverse=True)
    return (vong[0] - sum(vong[1:])) if vong else 0.0  # xấp xỉ: vòng ngoài trừ các vòng trong


def _hinh_doi_tuong(e):
    if e.dxftype() == "INSERT":
        # chỉ lấy hình, bỏ chữ/thuộc tính (ATTRIB làm phình khung bao)
        hinh = [v for v in e.virtual_entities() if v.dxftype() not in ("TEXT", "MTEXT", "ATTDEF", "ATTRIB")]
        bb = _bbox.extents(hinh)
        if not bb.has_data:
            return None
        return box(bb.extmin.x, bb.extmin.y, bb.extmax.x, bb.extmax.y)
    if e.dxftype() == "LWPOLYLINE" and e.closed:
        pg = Polygon([tuple(x[:2]) for x in e.get_points()])
        return pg if pg.is_valid and pg.area > 0 else pg.buffer(0)
    return None


def hatch_giao_doi_tuong(duong_dan_dxf, layer_hatch, loc_doi_tuong, nguong=0.5, max_dong=60):
    """Đo từng đối tượng (hố ga, bồn cây...) nằm trong vùng hatch (vùng lát) bao nhiêu %.

    layer_hatch: regex layer của hatch vùng lát (vd 'LAT|LG').
    loc_doi_tuong: regex khớp TÊN BLOCK hoặc LAYER của đối tượng (vd 'HGA|HOGA', 'BONCAY').
    nguong: tỉ lệ diện tích nằm trong vùng lát để coi là 'cần trừ' (mặc định 0,5).
    Phân loại mỗi đối tượng: DA_KHOET (trùng lỗ khoét của hatch — vùng lát đã trừ sẵn, KHÔNG trừ nữa),
    TRONG_VUNG (≥ ngưỡng — cần trừ), CHAM_MEP (0 < tỉ lệ < ngưỡng), NGOAI_VUNG.
    """
    _can(shapely_=True)
    d = ezdxf.readfile(duong_dan_dxf)
    m = d.modelspace()
    re_h, re_o = re.compile(layer_hatch, re.I), re.compile(loc_doi_tuong, re.I)
    vung, vo_ngoai = [], []
    for h in m.query("HATCH"):
        if re_h.search(h.dxf.layer):
            v = vung_hatch(h)
            if v is not None and not v.is_empty:
                vung.append(v)
                vo = _vong_hatch(h)
                vo_ngoai.append(max(vo, key=lambda x: x.area))
    if not vung:
        return f"Không thấy HATCH nào có layer khớp '{layer_hatch}'. Dùng cad_dem_doi_tuong xem danh sách layer rồi gọi lại."
    lat = unary_union(vung)
    bao = unary_union(vo_ngoai)  # vùng bao ngoài, gồm cả lỗ khoét
    loai, dong = Counter(), []
    for e in m:
        ten = e.dxf.name if e.dxftype() == "INSERT" else ""
        if not (re_o.search(e.dxf.layer) or (ten and re_o.search(ten))):
            continue
        hinh = _hinh_doi_tuong(e)
        if hinh is None or hinh.area <= 0:
            continue
        ti_le = lat.intersection(hinh).area / hinh.area
        trong_bao = bao.intersection(hinh).area / hinh.area
        if trong_bao >= nguong and ti_le < 1 - nguong:
            nhom = "DA_KHOET"
        elif ti_le >= nguong:
            nhom = "TRONG_VUNG"
        elif ti_le > 0:
            nhom = "CHAM_MEP"
        else:
            nhom = "NGOAI_VUNG"
        loai[nhom] += 1
        c = hinh.centroid
        dong.append(f"{nhom}|{e.dxf.handle}|{ten or e.dxftype()}|{e.dxf.layer}|{c.x:.2f}|{c.y:.2f}|{hinh.area:.3f}|{ti_le:.0%}")
    tong = sum(loai.values())
    ra = [f"Vùng lát (layer ~ '{layer_hatch}'): {lat.area:.2f} m² · {len(vung)} hatch",
          f"Đối tượng khớp '{loc_doi_tuong}': {tong} — CẦN TRỪ (TRONG_VUNG, ≥{nguong:.0%}) {loai['TRONG_VUNG']} · "
          f"ĐÃ KHOÉT sẵn trong hatch {loai['DA_KHOET']} · CHẠM MÉP {loai['CHAM_MEP']} · NGOÀI VÙNG {loai['NGOAI_VUNG']}",
          "nhom|handle|block|layer|x|y|dien_tich|ti_le_trong_vung_lat"]
    thu_tu = {"TRONG_VUNG": 0, "DA_KHOET": 1, "CHAM_MEP": 2, "NGOAI_VUNG": 3}
    dong.sort(key=lambda s: thu_tu[s.split("|", 1)[0]])
    ra += dong[:max_dong]
    if len(dong) > max_dong:
        ra.append(f"Đã trả {max_dong}/{len(dong)} dòng. Tăng max_dong nếu cần danh sách đủ.")
    if tong == 0:
        ra.append(f"Không đối tượng nào khớp '{loc_doi_tuong}' theo tên block hoặc layer. Dùng cad_dem_doi_tuong xem tên block/layer thật.")
    return "\n".join(ra)
