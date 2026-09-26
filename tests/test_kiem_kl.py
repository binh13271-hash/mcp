"""Test bộ kiem_kl trên dữ liệu TỰ DỰNG (không chứa số liệu dự án thật).

Mỗi ca mô phỏng đúng một kiểu lỗi đã gặp thật ở đợt kiểm KL 25/09/2026, kèm ca đối chứng
phải KHÔNG bị báo (báo nhầm cũng là lỗi của tool).
"""
import ezdxf
import pytest
from openpyxl import Workbook

from kiem_kl.cad import dem_doi_tuong, hatch_giao_doi_tuong
from kiem_kl.quet_loi import dinh_dang_ket_qua, quet_loi_sheet, quet_sheet_la
from kiem_kl.vni import bo_dau, giai_ma_vni, trong_nhu_vni


# ---------------------------------------------------------------- VNI
@pytest.mark.parametrize("vni,unicode_", [
    (" + Tröø caùc hoá ga 1.0x2.0 chieám choã (10 hoá) ", " + Trừ các hố ga 1.0x2.0 chiếm chỗ (10 hố) "),
    ("BAÛNG KHOÁI LÖÔÏNG COÂNG TAÙC", "BẢNG KHỐI LƯỢNG CÔNG TÁC"),
    ("ÑÒA ÑIEÅM: PHÖÔØNG", "ĐỊA ĐIỂM: PHƯỜNG"),
    ("ÑAØ GIAÈNG", "ĐÀ GIẰNG"),
    ("ROÄNG", "RỘNG"),
    ("Toång soá hoá ga döôùi loøng ñöôøng", "Tổng số hố ga dưới lòng đường"),
    ("Chieàu daøi gôø boù væa heø", "Chiều dài gờ bó vỉa hè"),
])
def test_giai_ma_vni(vni, unicode_):
    assert giai_ma_vni(vni) == unicode_


@pytest.mark.parametrize("chuoi", ["Gia công và lắp đặt ván khuôn", "rõ ràng", "Hoá đơn", "TÍCH", "CHUNG", ""])
def test_unicode_that_giu_nguyen(chuoi):
    assert giai_ma_vni(chuoi) == chuoi


def test_bo_dau_ca_vni_lan_unicode():
    assert bo_dau("Tröø caùc boàn caây") == "tru cac bon cay"
    assert bo_dau("Trừ các bồn cây") == "tru cac bon cay"
    assert not trong_nhu_vni("Đường")


# ---------------------------------------------------------------- Excel
def _bang(dong):
    """Bảng KL kiểu mẫu: tiêu đề VNI 2 dòng, cột B TT, C diễn giải, E dài, F rộng, G cao, H diện tích,
    I số lượng, J KL riêng, K KL chung."""
    wb = Workbook()
    ws = wb.active
    ws.title = "KLCT"
    for o, v in {"B6": "TT", "C6": "HAÏNG MUÏC COÂNG TAÙC", "F6": "KÍCH THÖÔÙC", "H6": "DIEÄN",
                 "I6": "PHAÀN ", "J6": "KHOÁI LÖÔÏNG", "E7": "DAØI", "F7": "ROÄNG", "G7": "CAO",
                 "H7": "TÍCH", "I7": "G/ NHAU", "J7": "RIEÂNG", "K7": "CHUNG"}.items():
        ws[o] = v
    for o, v in dong.items():
        ws[o] = v
    return wb, ws


def _loai(loi):
    return {(x["loai"], x["o"].split("!")[1]) for x in loi}


def test_do_cot_tu_tieu_de_vni():
    _, ws = _bang({})
    loi, cot = quet_loi_sheet(ws)
    assert cot["dien_giai"] == "C" and cot["so_luong"] == "I"
    assert cot["kl_rieng"] == "J" and cot["kl_chung"] == "K"
    assert cot["dai"] == "E" and cot["rong"] == "F" and cot["dien_tich"] == "H"


def test_he_so_bo_sot_va_dau_khoan_tru():
    wb, ws = _bang({
        "B10": 1, "C10": "Lát gạch", "K10": "=SUM(J11:J15)",
        "C11": "Diện tích lát", "J11": 500,
        "C12": " + Tröø caùc hoá ga 1.0x2.0 chieám choã (10 hoá)", "E12": 1.0, "F12": 2.0, "I12": 10, "J12": "=-E12*F12",
        "C13": " + Tröø hố thu 0.5x1.0 (4 hố)", "E13": 0.5, "F13": 1.0, "I13": 4, "J13": "=-E13*F13*I13",
        "C14": " + Tröø hố kỹ thuật 1.0x1.0 (1 hố)", "E14": 1.0, "F14": 1.0, "I14": 1, "J14": "=-E14*F14",
        "C15": " + Tröø caùc boàn caây chieám choã (20 caùi)", "E15": 1.0, "F15": 1.0, "I15": 20, "J15": "=E15*F15*I15",
    })
    loi, _ = quet_loi_sheet(ws)
    l = _loai(loi)
    assert ("HE_SO_BO_SOT", "J12") in l          # 10 hố mà chỉ trừ 1
    assert ("DAU_KHOAN_TRU", "J15") in l         # khoản trừ ra dương
    assert ("HE_SO_BO_SOT", "J13") not in l      # đã nhân I
    assert ("HE_SO_BO_SOT", "J14") not in l      # I = 1: không đổi số
    x = next(x for x in loi if x["loai"] == "HE_SO_BO_SOT")
    assert x["hien"] == pytest.approx(-2.0) and x["de_xuat"] == pytest.approx(-20.0)


def test_khong_bao_nham_khi_so_luong_nhan_o_cot_chung():
    # Kiểu K = I*J: J là KL 1 cái, K nhân số lượng -> KHÔNG phải lỗi
    wb, ws = _bang({"B10": 1, "C10": "Đất hữu cơ bồn cây", "E10": 1.2, "F10": 1.2, "G10": 0.7,
                    "I10": 50, "J10": "=E10*F10*G10", "K10": "=I10*J10"})
    loi, _ = quet_loi_sheet(ws)
    assert not any(x["loai"] == "HE_SO_BO_SOT" for x in loi)


def test_nhan_lech_kich_thuoc_chi_trong_khoi_da_so_khop():
    d = {"B10": 1, "C10": "Đắp cát", "K10": "=SUM(J11:J14)"}
    for r, (nhan, e, f) in zip(range(11, 15), [("1.0x2.0", 1.0, 2.0), ("1.5x1.5", 1.5, 1.5),
                                                 ("2.0x3.0", 2.0, 3.0), ("1.0x3.0", 1.5, 2.0)]):
        d.update({f"C{r}": f" + Trừ hố {nhan} (1 hố)", f"E{r}": e, f"F{r}": f, f"I{r}": 1, f"J{r}": f"=-E{r}*F{r}*I{r}"})
    # Khối nắp đan: nhãn là kích thước HỐ, E/F là kích thước NẮP -> không khối nào khớp -> không báo
    d.update({"B20": 2, "C20": "Nắp đan", "K20": "=SUM(J21:J23)"})
    for r in (21, 22, 23):
        d.update({f"C{r}": " + Hố ga 1.2x1.6 (nắp 0.7x1.0)", f"E{r}": 0.7, f"F{r}": 1.0, f"J{r}": f"=E{r}*F{r}"})
    wb, ws = _bang(d)
    loi, _ = quet_loi_sheet(ws)
    lech = {x["o"].split("!")[1] for x in loi if x["loai"] == "NHAN_LECH_KT"}
    assert lech == {"E14"}


def test_so_luong_trong_dien_giai_khac_cot_so_luong():
    wb, ws = _bang({"B10": 1, "K10": "=SUM(J11:J11)",
                    "C11": " + Trừ hố ga 1.0x1.0 (12 hố)", "E11": 1.0, "F11": 1.0, "I11": 10, "J11": "=-E11*F11*I11"})
    loi, _ = quet_loi_sheet(ws)
    assert ("SO_LUONG_LECH", "I11") in _loai(loi)


def test_sum_bo_sot_dong_cuoi():
    wb, ws = _bang({"B10": 1, "C10": "Hạng mục", "K10": "=SUM(J11:J12)",
                    "J11": 5, "J12": 6, "C13": " + dòng con bị sót", "J13": 7,
                    "B14": 2, "C14": "Hạng mục sau", "K14": "=SUM(J15:J15)", "J15": 1, "B16": 3})
    loi, _ = quet_loi_sheet(ws)
    l = _loai(loi)
    assert ("SUM_BO_SOT", "K10") in l
    assert ("SUM_BO_SOT", "K14") not in l  # dòng sau là đầu mục mới


def test_ref_va_lien_ket_ngoai_va_hang_so():
    wb, ws = _bang({"B10": 1, "K10": "=#REF!*2", "B11": 2, "K11": "=K10-'[old.xls]KLCT'!$K$67",
                    "B12": 3, "K12": "=180.434+23.56"})
    loi, _ = quet_loi_sheet(ws)
    l = _loai(loi)
    assert ("THAM_CHIEU", "K10") in l and ("THAM_CHIEU", "K11") in l
    assert ("HANG_SO", "K12") in l


def test_cong_thuc_lech_bo_qua_cot_trong():
    d = {"B10": 1, "K10": "=SUM(J11:J15)"}
    for r in (11, 12, 13, 14):
        d.update({f"E{r}": 1.0, f"F{r}": 2.0, f"G{r}": 0.5, f"I{r}": 2, f"J{r}": f"=-E{r}*F{r}*I{r}*G{r}"})
    d.update({"E15": 3.0, "F15": 0.2, "G15": 0.5, "J15": "=-E15*F15*G15"})  # I15 trống -> hợp lệ
    wb, ws = _bang(d)
    loi, _ = quet_loi_sheet(ws)
    assert not any(x["loai"] == "CONG_THUC_LECH" for x in loi)


def test_sheet_la_va_dinh_dang():
    wb, ws = _bang({"B10": 1, "K10": "=Phu!A1"})
    wb.create_sheet("Phu")
    wb.create_sheet("xxxxxxxx")
    wb.create_sheet("Cu")
    loi, khong_goi = quet_sheet_la(wb)
    assert [x["o"] for x in loi] == ["xxxxxxxx"]
    assert "Cu" in khong_goi and "Phu" not in khong_goi
    txt = dinh_dang_ket_qua(loi, max_ket_qua=5)
    assert txt.startswith("Tổng 1 nghi vấn: CAO 1")


# ---------------------------------------------------------------- DXF
@pytest.fixture
def dxf_mau(tmp_path):
    d = ezdxf.new()
    d.header["$INSUNITS"] = 6
    m = d.modelspace()
    b = d.blocks.new("HOGA")
    b.add_lwpolyline([(0, 0), (1.2, 0), (1.2, 1.6), (0, 1.6)], close=True)
    # Vùng lát 20x4 có 1 lỗ khoét 1x1 tại (10,1)-(11,2)
    h = m.add_hatch(dxfattribs={"layer": "LAT"})
    h.paths.add_polyline_path([(0, 0), (20, 0), (20, 4), (0, 4)], is_closed=True, flags=1)
    h.paths.add_polyline_path([(10, 1), (11, 1), (11, 2), (10, 2)], is_closed=True, flags=16)
    # Bồn cây (polyline kín 1x1): 1 trùng lỗ khoét, 1 nằm trong vùng lát, 1 ngoài
    for x, y in [(10, 1), (3, 1), (30, 1)]:
        m.add_lwpolyline([(x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1)], close=True, dxfattribs={"layer": "BONCAY"})
    # Hố ga (block): 1 trong vùng, 1 chạm mép (chỉ 25% trong vùng)
    m.add_blockref("HOGA", (5, 1), dxfattribs={"layer": "HG"})
    m.add_blockref("HOGA", (19.7, 1), dxfattribs={"layer": "HG"})
    m.add_line((0, -1), (10, -1), dxfattribs={"layer": "BOVIA"})
    m.add_arc((0, 0), 10, 0, 90, dxfattribs={"layer": "BOVIA"})
    m.add_text("HG 12", dxfattribs={"layer": "TEXT"})
    p = tmp_path / "mau.dxf"
    d.saveas(p)
    return str(p)


def test_dem_doi_tuong(dxf_mau):
    txt = dem_doi_tuong(dxf_mau)
    assert "I|HOGA|HG|2" in txt
    assert "R|1.00x1.00|BONCAY|3" in txt
    assert "L|BOVIA|25.71" in txt          # 10 + cung pi/2*10
    assert "H|LAT|79.00" in txt            # 80 - lỗ 1 m²
    assert "T|HG12|1" in txt


def test_hatch_giao_doi_tuong(dxf_mau):
    bon = hatch_giao_doi_tuong(dxf_mau, "LAT", "BONCAY")
    assert "CẦN TRỪ (TRONG_VUNG, ≥50%) 1 · ĐÃ KHOÉT sẵn trong hatch 1 · CHẠM MÉP 0 · NGOÀI VÙNG 1" in bon
    hg = hatch_giao_doi_tuong(dxf_mau, "LAT", "HOGA")
    assert "CẦN TRỪ (TRONG_VUNG, ≥50%) 1" in hg and "CHẠM MÉP 1" in hg


def test_hatch_khong_thay_layer(dxf_mau):
    assert "Không thấy HATCH" in hatch_giao_doi_tuong(dxf_mau, "KHONGCO", "BONCAY")
