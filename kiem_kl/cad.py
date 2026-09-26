"""Đọc bản vẽ DXF để đối chiếu khối lượng: đếm đối tượng, đo phần giao đối tượng với vùng hatch.

Rút từ đợt kiểm KL một dự án đường đô thị (25/09/2026):
  - Đếm theo HÌNH HỌC (block, hình chữ nhật kín), không đếm nhãn chữ.
  - Diện tích lát lấy theo hatch/nhãn có thể ĐÃ khoét bồn cây; trừ thêm đủ số bồn ở bảng tính là
    trừ lặp. Phải đo từng đối tượng: phần nằm trên vùng tô, phần rơi vào lỗ khoét, phần ngoài.

Mọi số đo đã quy đổi theo $INSUNITS (mm -> m...). Bản vẽ không khai đơn vị thì báo rõ và trả
theo đơn vị bản vẽ — truyền he_so_don_vi (vd 0.001 nếu vẽ bằng mm) để quy đổi.
Chỉ ĐỌC. DWG phải chuyển DXF trước (ODA File Converter / AutoCAD DXFOUT).
"""
import math
import re
from collections import Counter

try:
    import ezdxf
    from ezdxf import path as _path
    from ezdxf import bbox as _bbox
    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False

try:
    from shapely.geometry import MultiPoint, Polygon
    from shapely.ops import unary_union
    HAS_SHAPELY = True
except ImportError:
    HAS_SHAPELY = False

_NHAN = re.compile(r"(HG\s*\d+'?|HTBS\s*\d+|HCQ\s*\d+|\d[.,]\d+\s*[xX]\s*\d[.,]\d+)")
# $INSUNITS -> mét
_DON_VI = {1: (0.0254, "inch"), 2: (0.3048, "feet"), 4: (0.001, "mm"), 5: (0.01, "cm"),
           6: (1.0, "m"), 7: (1000.0, "km")}
_BO_QUA = {"TEXT", "MTEXT", "ATTRIB", "ATTDEF", "DIMENSION", "LEADER", "MLEADER", "POINT"}


def _can(shapely_=False):
    thieu = [n for n, co in (("ezdxf", HAS_EZDXF), ("shapely", HAS_SHAPELY or not shapely_)) if not co]
    if thieu:
        raise RuntimeError(f"Thiếu thư viện {', '.join(thieu)}: pip install {' '.join(thieu)}")


def _mo_dxf(duong_dan):
    try:
        return ezdxf.readfile(duong_dan)
    except IOError as e:
        raise RuntimeError(f"Không mở được {duong_dan} ({e}). Kiểm tra đường dẫn / file đã tải về từ OneDrive chưa.")
    except ezdxf.DXFStructureError as e:
        raise RuntimeError(f"File DXF hỏng cấu trúc ({e}). Xuất lại DXF từ DWG (ODA File Converter, bản R2013+).")


def _regex(mau, ten):
    try:
        return re.compile(mau, re.I)
    except re.error as e:
        raise RuntimeError(f"{ten}='{mau}' không phải regex hợp lệ ({e}). Ví dụ: 'LAT|LG' hoặc 'HGA.*'.")


def doc_vung(vung):
    """'xmin,ymin,xmax,ymax' (đơn vị bản vẽ) -> tuple; rỗng -> None. Sai dạng -> RuntimeError nói rõ.
    Dùng khi một DXF chứa nhiều BẢN SAO mặt bằng (bình đồ, bố trí, lát gạch...) — đếm cả file là nhân 3–5 lần."""
    if not vung:
        return None
    try:
        so = [float(x) for x in str(vung).replace(";", ",").split(",")]
    except ValueError:
        so = []
    if len(so) != 4 or so[0] >= so[2] or so[1] >= so[3]:
        raise RuntimeError(f"vung='{vung}' phải là 'xmin,ymin,xmax,ymax' (đơn vị bản vẽ, xmin<xmax, ymin<ymax). "
                           "Lấy tọa độ khung tờ/bản sao cần đếm từ CAD (lệnh ID hoặc khung in).")
    return tuple(so)


def _trong_vung(e, v):
    """Tâm hộp bao của đối tượng nằm trong vùng v (None = mọi nơi)."""
    if v is None:
        return True
    try:
        hop = _bbox.extents([e], fast=True)
    except Exception:
        return False
    if not hop.has_data:
        return False
    c = hop.center
    return v[0] <= c.x <= v[2] and v[1] <= c.y <= v[3]


def don_vi(doc, he_so_don_vi=None):
    """(hệ số ra mét, nhãn đơn vị, đã xác định?)."""
    if he_so_don_vi:
        return float(he_so_don_vi), f"m (quy đổi tay ×{he_so_don_vi:g})", True
    ma = doc.header.get("$INSUNITS", 0)
    if ma in _DON_VI:
        k, ten = _DON_VI[ma]
        return k, f"m (bản vẽ vẽ bằng {ten})", True
    return 1.0, f"ĐƠN VỊ BẢN VẼ ($INSUNITS={ma}, chưa xác định)", False


def _diem(e):
    try:
        return [(v.x, v.y) for v in _path.make_path(e).flattening(0.01)]
    except Exception:
        return []


def _do_dai(e):
    t = e.dxftype()
    if t == "LINE":
        return e.dxf.start.distance(e.dxf.end)
    if t == "ARC":
        return math.radians((e.dxf.end_angle - e.dxf.start_angle) % 360) * e.dxf.radius
    if t in ("LWPOLYLINE", "POLYLINE", "CIRCLE", "ELLIPSE", "SPLINE"):
        p = _diem(e)
        return sum(math.dist(a, b) for a, b in zip(p, p[1:]))
    return 0.0


def _chu_nhat(e, k):
    """'axb' (m, a<=b, làm tròn 0,01) nếu là LWPOLYLINE kín 4 cạnh thẳng, góc vuông; không thì None."""
    if e.dxftype() != "LWPOLYLINE" or not e.closed:
        return None
    p = [tuple(x) for x in e.get_points(format="xyb")]
    if any(abs(b) > 1e-9 for _, _, b in p):
        return None  # có cung (bulge) -> không phải chữ nhật
    p = [(x, y) for x, y, _ in p]
    if len(p) == 5 and math.dist(p[0], p[-1]) < 1e-9:
        p = p[:-1]
    if len(p) != 4:
        return None
    c = [math.dist(p[i], p[(i + 1) % 4]) for i in range(4)]
    cheo = [math.dist(p[0], p[2]), math.dist(p[1], p[3])]
    tol = 0.005 / k  # 5 mm
    if abs(c[0] - c[2]) > tol or abs(c[1] - c[3]) > tol or abs(cheo[0] - cheo[1]) > tol:
        return None
    return "%.2fx%.2f" % tuple(sorted((c[0] * k, c[1] * k)))


def _vong_hatch(h):
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
    """Vùng tô thật theo chẵn-lẻ (vòng lồng = lỗ, đảo trong lỗ = tô lại). Trả (vùng tô, vùng bao gồm lỗ)."""
    _can(shapely_=True)
    vong = _vong_hatch(h)
    if not vong:
        return None, None
    # Tầng lồng của mỗi vòng = số vòng LỚN hơn chứa quá nửa diện tích nó. Không dùng XOR hình học:
    # lỗ khoét vẽ LẤN ra ngoài biên ngoài (bồn cây sát bó vỉa) thì XOR tô lại phần lấn ra ngoài.
    # Đảo trong lỗ (tầng chẵn) vẫn được tô như kiểu hatch Normal của CAD (chạy thật 26/09).
    tang = []
    for i, q in enumerate(vong):
        n = 0
        for j, r in enumerate(vong):
            if j != i and r.area > q.area and r.intersects(q) and r.intersection(q).area > 0.5 * q.area:
                n += 1
        tang.append(n)
    vung = None
    for n, q in sorted(zip(tang, vong), key=lambda x: x[0]):
        if n % 2 == 0:
            vung = q if vung is None else vung.union(q)
        elif vung is not None:
            vung = vung.difference(q)
    if vung is None or vung.is_empty:
        return None, None
    # Vùng bao = hợp MỌI vòng biên: lỗ chạm biên ngoài (XOR biến thành chỗ lõm) vẫn tính là lỗ — đối tượng
    # trong đó là DA_KHOET, không phải NGOAI_VUNG (chạy thật 26/09).
    bao = unary_union(vong)
    return vung, bao


def dem_doi_tuong(duong_dan_dxf, loc_layer=None, max_dong=40, he_so_don_vi=None, vung=None):
    """Đếm đối tượng model space: block, hình chữ nhật kín, chiều dài, diện tích hatch, nhãn. Trả bảng gọn.
    vung 'xmin,ymin,xmax,ymax' (đơn vị bản vẽ): chỉ đếm đối tượng có tâm hộp bao trong vùng."""
    khung = doc_vung(vung)
    _can()
    d = _mo_dxf(duong_dan_dxf)
    k, ten_dv, ro = don_vi(d, he_so_don_vi)
    loc = _regex(loc_layer, "loc_layer") if loc_layer else None
    ins, cn, dai, hat, nhan, loi = Counter(), Counter(), Counter(), Counter(), Counter(), []
    for e in d.modelspace():
        L = e.dxf.layer
        if loc and not loc.search(L):
            continue
        if not _trong_vung(e, khung):
            continue
        t = e.dxftype()
        try:
            if t == "INSERT":
                ins[(e.dxf.name, L)] += 1
            elif t in ("LINE", "ARC", "LWPOLYLINE", "POLYLINE", "CIRCLE", "ELLIPSE", "SPLINE"):
                dai[L] += _do_dai(e) * k
                r = _chu_nhat(e, k)
                if r:
                    cn[(r, L)] += 1
            elif t == "HATCH" and HAS_SHAPELY:
                v, _ = vung_hatch(e)
                hat[L] += (v.area if v is not None else 0.0) * k * k
            elif t in ("TEXT", "MTEXT"):
                s = e.plain_text() if t == "MTEXT" else e.dxf.text
                for x in _NHAN.findall(s or ""):
                    nhan[re.sub(r"\s+", "", x.replace(",", "."))] += 1
        except Exception as ex:  # không nuốt im lặng: đếm + nêu handle
            loi.append(f"{t} {e.dxf.handle}: {ex}")
    ra = [f"File {duong_dan_dxf} · đơn vị số đo: {ten_dv}"
          + (f" · CHỈ vùng x {khung[0]:g}–{khung[2]:g}, y {khung[1]:g}–{khung[3]:g}" if khung else "")]
    if not khung:
        ra.append("Phạm vi: CẢ FILE. Bản vẽ có nhiều bản sao mặt bằng (bình đồ/bố trí/lát/ATGT) thì số đếm bị nhân — "
                  "truyền vung = khung một bản sao.")
    if not ro:
        ra.append("⚠ Chưa biết đơn vị bản vẽ: số đo là ĐƠN VỊ BẢN VẼ. Truyền he_so_don_vi (0.001 nếu vẽ mm) để ra mét.")

    def bang(tieu_de, cot, du_lieu, fmt):
        ra.append(f"# {tieu_de}: {cot}")
        items = du_lieu.most_common()
        for kk, v in items[:max_dong]:
            ra.append(fmt(kk, v))
        if len(items) > max_dong:
            ra.append(f"... còn {len(items) - max_dong} dòng (tăng max_dong hoặc dùng loc_layer)")

    bang("BLOCK", "ten|layer|so_luong", ins, lambda kk, v: f"I|{kk[0]}|{kk[1]}|{v}")
    bang("HÌNH CHỮ NHẬT KÍN (cạnh thẳng, góc vuông)", "kich_thuoc|layer|so_luong", cn, lambda kk, v: f"R|{kk[0]}|{kk[1]}|{v}")
    bang("CHIỀU DÀI theo layer", "layer|dai", dai, lambda kk, v: f"L|{kk}|{v:.2f}")
    if HAS_SHAPELY:
        bang("DIỆN TÍCH HATCH (đã trừ lỗ khoét)", "layer|dien_tich", hat, lambda kk, v: f"H|{kk}|{v:.2f}")
    else:
        ra.append("# DIỆN TÍCH HATCH: KHÔNG TÍNH (thiếu shapely — pip install shapely). Số hatch theo layer: "
                  + ", ".join(f"{kk}={v}" for kk, v in Counter(h.dxf.layer for h in d.modelspace().query("HATCH")).items()))
    bang("NHÃN CHỮ — chỉ để đối chiếu, KHÔNG dùng làm số lượng", "nhan|so_lan", nhan, lambda kk, v: f"T|{kk}|{v}")
    if loi:
        ra.append(f"⚠ {len(loi)} đối tượng đọc lỗi (không tính vào bảng trên): " + "; ".join(loi[:5]))
    return "\n".join(ra)


def _hinh_block(e, sau=0):
    """Hình đã biến đổi (xoay/tỉ lệ) của block: (danh sách polygon kín, danh sách điểm nét hở)."""
    kin, diem = [], []
    if sau > 8:
        return kin, diem
    nhieu = e.dxftype() == "INSERT" and (e.dxf.get("row_count", 1) > 1 or e.dxf.get("column_count", 1) > 1)
    for ins in (list(e.multi_insert()) if nhieu else [e]):
        for v in ins.virtual_entities():
            t = v.dxftype()
            if t in _BO_QUA:
                continue
            if t == "INSERT":
                k2, d2 = _hinh_block(v, sau + 1)
                kin += k2
                diem += d2
            elif t == "HATCH":
                vv, _ = vung_hatch(v)
                if vv is not None:
                    kin.append(vv)
            elif (t in ("LWPOLYLINE", "POLYLINE") and v.closed) or t == "CIRCLE":
                p = _diem(v)
                if len(p) >= 3:
                    pg = Polygon(p)
                    kin.append(pg if pg.is_valid else pg.buffer(0))
            else:
                diem += _diem(v)
    return kin, diem


def _hinh_doi_tuong(e):
    """(polygon, uoc_luong). uoc_luong=True khi chỉ dựng được bao lồi từ nét hở — không dùng kết luận trừ."""
    t = e.dxftype()
    if (t in ("LWPOLYLINE", "POLYLINE") and e.closed) or t == "CIRCLE":
        p = _diem(e)  # make_path xử lý cung (bulge) và hệ tọa độ OCS
        if len(p) < 3:
            return None, False
        pg = Polygon(p)
        return (pg if pg.is_valid else pg.buffer(0)), False
    if t == "INSERT":
        kin, diem = _hinh_block(e)
        kin = [x for x in kin if x.area > 0]
        if kin:
            return unary_union(kin), False
        if len(diem) >= 3:
            return MultiPoint(diem).convex_hull, True
    return None, False


def hatch_giao_doi_tuong(duong_dan_dxf, layer_hatch, loc_doi_tuong, dung_sai=0.02, max_dong=60, he_so_don_vi=None,
                         mau_hatch=None, kich_thuoc=None, vung=None):
    """Đo từng đối tượng (hố ga, bồn cây...) so với vùng hatch (vùng lát): phần trên vùng tô, phần rơi vào lỗ khoét.

    Nhóm: TRONG_VUNG (≥1-dung_sai trên vùng tô: trừ toàn bộ) · DA_KHOET (≥1-dung_sai trong lỗ: hatch đã
    trừ, KHÔNG trừ nữa) · NGOAI_VUNG (≤dung_sai chạm vùng bao) · MOT_PHAN (còn lại: chỉ trừ đúng phần
    trên vùng tô, cột dt_tren_vung_to). Tổng cần trừ = Σ dt_tren_vung_to của mọi đối tượng — không dùng
    đếm × diện tích 1 cái. Đối tượng '~' (ước lượng) chỉ dựng được bao lồi: phải xem bản vẽ.
    mau_hatch: regex tên mẫu hatch (vd '^ANGLE$') — cùng layer hay có cả hatch vuốt nối/ký hiệu khác.
    kich_thuoc: 'axb' (m) — chỉ lấy hình chữ nhật kín đúng cỡ (bồn cây 1.40x1.40), bỏ block và nét khác cùng layer.
    vung: 'xmin,ymin,xmax,ymax' (đơn vị bản vẽ) — chỉ xét đối tượng có tâm hộp bao trong vùng.
    Nét hở (LINE, polyline mở...) trên layer khớp bị BỎ QUA và đếm riêng, không coi là lỗi.
    """
    # Kiểm đầu vào TRƯỚC khi đòi thư viện: máy thiếu shapely vẫn nhận đúng lỗi tham số (chạy thật 26/09).
    if not (0 < dung_sai < 0.5):
        raise RuntimeError(f"dung_sai={dung_sai} ngoài miền (0; 0,5). Mặc định 0,02 = 2% diện tích đối tượng.")
    re_h, re_o = _regex(layer_hatch, "layer_hatch"), _regex(loc_doi_tuong, "loc_doi_tuong")
    re_m = _regex(mau_hatch, "mau_hatch") if mau_hatch else None
    kt = None
    if kich_thuoc:
        so = re.findall(r"\d+(?:[.,]\d+)?", str(kich_thuoc))
        if len(so) != 2:
            raise RuntimeError(f"kich_thuoc='{kich_thuoc}' phải dạng 'axb' theo mét, vd '1.40x1.40'.")
        kt = "%.2fx%.2f" % tuple(sorted(float(x.replace(",", ".")) for x in so))
    khung = doc_vung(vung)
    _can(shapely_=True)
    d = _mo_dxf(duong_dan_dxf)
    k, ten_dv, ro = don_vi(d, he_so_don_vi)
    m = d.modelspace()
    to, bao, mau_bo = [], [], Counter()
    for h in m.query("HATCH"):
        if re_h.search(h.dxf.layer):
            if re_m and not re_m.search(h.dxf.pattern_name or ""):
                mau_bo[h.dxf.pattern_name] += 1
                continue
            vv, b = vung_hatch(h)
            if vv is not None:
                to.append(vv)
                bao.append(b)
    if not to:
        return (f"Không thấy HATCH nào có layer khớp '{layer_hatch}'"
                + (f" và mẫu khớp '{mau_hatch}' (mẫu cùng layer: {dict(mau_bo)})" if re_m else "")
                + ". Dùng cad_dem_doi_tuong xem danh sách layer rồi gọi lại.")
    vung_to = unary_union(to)
    lo = unary_union(bao).difference(vung_to)
    k2 = k * k
    dem, dong, loi = Counter(), [], []
    tong_tru, tong_uoc, net_ho, khac_co = 0.0, 0, 0, 0
    for e in m:
        t = e.dxftype()
        ten = e.dxf.name if t == "INSERT" else ""
        if not (re_o.search(e.dxf.layer) or (ten and re_o.search(ten))):
            continue
        if t in _BO_QUA or t == "HATCH":
            continue
        if kt is not None:
            if _chu_nhat(e, k) != kt:
                khac_co += 1
                continue
        elif not (t == "INSERT" or t == "CIRCLE" or (t in ("LWPOLYLINE", "POLYLINE") and e.closed)):
            net_ho += 1
            continue
        if not _trong_vung(e, khung):
            continue
        try:
            hinh, uoc = _hinh_doi_tuong(e)
        except Exception as ex:
            loi.append(f"{e.dxftype()} {e.dxf.handle}: {ex}")
            continue
        if hinh is None or hinh.area <= 0:
            loi.append(f"{e.dxftype()} {e.dxf.handle}: không dựng được hình kín")
            continue
        A = hinh.area
        a_to, a_lo = hinh.intersection(vung_to).area, hinh.intersection(lo).area
        if a_to / A >= 1 - dung_sai:
            nhom = "TRONG_VUNG"
        elif a_lo / A >= 1 - dung_sai:
            nhom = "DA_KHOET"
        elif (a_to + a_lo) / A <= dung_sai:
            nhom = "NGOAI_VUNG"
        else:
            nhom = "MOT_PHAN"
        tong_uoc += bool(uoc)
        dem[nhom] += 1
        tong_tru += a_to * k2
        c = hinh.centroid
        dong.append(f"{nhom}{'~' if uoc else ''}|{e.dxf.handle}|{ten or e.dxftype()}|{e.dxf.layer}|"
                    f"{c.x * k:.2f}|{c.y * k:.2f}|{A * k2:.3f}|{a_to * k2:.3f}|{a_lo * k2:.3f}")
    tong = sum(dem.values())
    ra = [f"Đơn vị: {ten_dv}" + ("" if ro else " — ⚠ truyền he_so_don_vi để ra m²")
          + (f" · CHỈ đối tượng trong vùng x {khung[0]:g}–{khung[2]:g}, y {khung[1]:g}–{khung[3]:g}" if khung else ""),
          f"Vùng tô (layer ~ '{layer_hatch}'" + (f", mẫu ~ '{mau_hatch}'" if re_m else "")
          + f"): {vung_to.area * k2:.2f} · lỗ khoét: {lo.area * k2:.2f} · {len(to)} hatch"
          + (f" · bỏ {sum(mau_bo.values())} hatch khác mẫu {dict(mau_bo)}" if mau_bo else ""),
          f"Đối tượng khớp '{loc_doi_tuong}': {tong} — TRONG_VUNG {dem['TRONG_VUNG']} · DA_KHOET {dem['DA_KHOET']} · "
          f"MOT_PHAN {dem['MOT_PHAN']} · NGOAI_VUNG {dem['NGOAI_VUNG']}",
          f"TỔNG DIỆN TÍCH CẦN TRỪ khỏi vùng lát = {tong_tru:.3f} (Σ phần nằm trên vùng tô)"
          + (f" · ⚠ {tong_uoc} đối tượng '~' ước lượng bằng bao lồi — xem bản vẽ" if tong_uoc else ""),
          "nhom|handle|block|layer|x|y|dt_doi_tuong|dt_tren_vung_to|dt_trong_lo"]
    thu_tu = {"TRONG_VUNG": 0, "MOT_PHAN": 1, "DA_KHOET": 2, "NGOAI_VUNG": 3}
    dong.sort(key=lambda s: thu_tu[s.split("|", 1)[0].rstrip("~")])
    ra += dong[:max_dong]
    if len(dong) > max_dong:
        ra.append(f"Đã trả {max_dong}/{len(dong)} dòng. Tăng max_dong nếu cần danh sách đủ.")
    if net_ho or khac_co:
        ra.append(f"Bỏ qua (không phải đối tượng cần đo): {net_ho} nét hở"
                  + (f" · {khac_co} hình khác cỡ {kt}" if kt else ""))
    if loi:
        ra.append(f"⚠ {len(loi)} đối tượng không đo được (KHÔNG tính vào tổng): " + "; ".join(loi[:5]))
    if tong == 0 and not loi:
        ra.append(f"Không đối tượng nào khớp '{loc_doi_tuong}' theo tên block hoặc layer. Dùng cad_dem_doi_tuong xem tên thật.")
    return "\n".join(ra)
