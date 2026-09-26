"""ĐOẠN ĐÃ GHÉP VÀO server.py my-office-mcp v7.3 (26/09/2026, Claude Code trên máy) — 3 tool CHỈ ĐỌC.

Bản này CHÉP LẠI đúng khối đang chạy trong server.py (mục 20.2b) để repo phối hợp theo dõi; sửa ở
server.py rồi chép lại, không sửa riêng ở đây. Tên thật đã kiểm trong server.py: _DECO_DOC, _nap_workbook,
secure_path, ensure_file_hydrated, _o_co_that (generator ô -> nối sang dạng dict kiem_kl cần bằng
_kl_o_co_that). json/os đã import ở đầu server.py.

Còn nợ (SO_NHAP my-office-mcp): adapter _cham_diem_dong_tieu_de -> vai trò dai/rong/cao/so_luong/kl_rieng/
kl_chung (Codex R10); R11 viewport/layout (hiện chỉ có vung = khung chữ nhật).
"""
# noqa: F821 — các tên dưới có sẵn trong server.py
try:
    from kiem_kl import quet_loi as _kl_quet
    from kiem_kl import cad as _kl_cad
    HAS_KIEM_KL = True
except ImportError:
    HAS_KIEM_KL = False

_KL_THIEU = "Thiếu thư mục kiem_kl\\ cạnh server.py. Chép lại từ bản vá rồi khởi động lại MCP."


def _kl_o_co_that(ws, d1, d2):
    """Nối _o_co_that() của server (G6) sang dạng kiem_kl cần: {dòng: [(chữ cột, giá trị)]}."""
    ra = {}
    for o in _o_co_that(ws, d1, d2):
        if o.value is not None:
            ra.setdefault(o.row, []).append((o.column_letter, o.value))
    return ra


if HAS_KIEM_KL:
    _kl_quet._o_co_that = _kl_o_co_that


@_DECO_DOC
def excel_quet_loi_khoi_luong(duong_dan_file: str, ten_sheet: str = "", cot_map_json: str = "",
                              dong_bat_dau: int = 0, max_dong: int = 3000, max_ket_qua: int = 150) -> str:
    """Quét bảng khối lượng Excel (KLCT, diễn giải KL) tìm nghi vấn công thức để ưu tiên đối chiếu bản vẽ.
    Bắt: quên nhân số lượng, khoản trừ ra dương, nhãn 'a x b'/'(84 hố)' lệch cột nhập, công thức lệch khối,
    SUM sót, #REF!/file ngoài, số gõ tay, sheet nghi macro; đọc font VNI. Kết quả là NGHI VẤN — không cờ ≠ đúng.
    cot_map_json ép cột khi tự dò sai, vd {"dien_giai":"C","so_luong":"I","kl_rieng":"J","kl_chung":"K"}.
    KHÁC excel_recalc_va_soat_loi: cái đó chỉ tìm ô đang báo lỗi.
    Đường lui: bảng không theo mẫu dài/rộng/số lượng → read_sheet_data đọc thô."""
    if not HAS_KIEM_KL:
        return _KL_THIEU
    cot_map = None
    if cot_map_json:
        try:
            cot_map = json.loads(cot_map_json)
        except ValueError as e:
            return f"cot_map_json không phải JSON ({e}). Ví dụ: {{\"so_luong\":\"I\",\"kl_rieng\":\"J\"}}"
        loi_map = _kl_quet.kiem_cot_map(cot_map)
        if loi_map:
            return loi_map
    if max_dong <= 0 or max_ket_qua <= 0:
        return "max_dong và max_ket_qua phải > 0."
    dd = secure_path(duong_dan_file)
    ensure_file_hydrated(dd)
    wb_ct = wb_gt = None
    try:
        wb_ct = _nap_workbook(dd)                    # đọc CÔNG THỨC
        wb_gt = _nap_workbook(dd, data_only=True)    # đọc GIÁ TRỊ Excel lưu sẵn
        if ten_sheet and ten_sheet not in wb_ct.sheetnames:
            return f"Không có sheet '{ten_sheet}'. Các sheet: {wb_ct.sheetnames}"
        loi, pham_vi, bo_qua = [], [], []
        for t in ([ten_sheet] if ten_sheet else wb_ct.sheetnames):
            if not ten_sheet and not cot_map:
                cot = _kl_quet.do_cot(wb_ct[t])[0]
                if not ({"kl_rieng", "kl_chung"} & set(cot)):
                    bo_qua.append(t)
                    continue
            l, _, pv = _kl_quet.quet_loi_sheet(wb_ct[t], wb_gt[t], cot_map=cot_map,
                                               dong_bat_dau=dong_bat_dau or None, max_dong=max_dong)
            loi += l
            pham_vi.append(pv)
        la, khong_goi = _kl_quet.quet_sheet_la(wb_ct)
        ra = _kl_quet.dinh_dang_ket_qua(la + loi, max_ket_qua, pham_vi)
        if bo_qua:
            ra += ("\nKHÔNG QUÉT (không thấy cột KL riêng/chung — truyền ten_sheet + cot_map_json nếu cần): "
                   + ", ".join(bo_qua))
        if khong_goi:
            ra += ("\nSheet không thấy tham chiếu trực tiếp (chưa xét named range/INDIRECT — không kết luận thừa): "
                   + ", ".join(khong_goi))
        return ra
    except Exception as e:
        return (f"Lỗi khi quét {duong_dan_file}: {type(e).__name__}: {e}. Đã thử nạp công thức + giá trị lưu sẵn. "
                "Thử lại với ten_sheet cụ thể, hoặc dùng read_sheet_data đọc thô.")
    finally:
        for wb in (wb_ct, wb_gt):
            try:
                if wb is not None:
                    wb.close()
            except Exception:
                pass


def _kl_dxf(duong_dan_dxf: str):
    """(đường dẫn đã chuẩn hoá, câu lỗi hoặc None) — dùng chung cho 2 tool DXF."""
    dd = secure_path(duong_dan_dxf)
    if not dd.lower().endswith(".dxf"):
        return dd, "Chỉ đọc .dxf. DWG: chuyển bằng ODA File Converter (hoặc AutoCAD DXFOUT) vào _sandbox rồi gọi lại."
    if not os.path.isfile(dd):
        return dd, f"Không thấy file {dd}. Kiểm tra đường dẫn (list_directory) rồi gọi lại."
    ensure_file_hydrated(dd)
    return dd, None


@_DECO_DOC
def cad_dem_doi_tuong(duong_dan_dxf: str, loc_layer: str = "", max_dong: int = 40, he_so_don_vi: float = 0,
                      vung: str = "") -> str:
    """Đếm đối tượng bản vẽ DXF theo hình học: block, hình chữ nhật kín theo cỡ, dài theo layer, diện tích hatch, nhãn.
    DXF hay chứa nhiều bản sao mặt bằng + nháp: vung='xmin,ymin,xmax,ymax' (đơn vị bản vẽ) = khung một bản sao,
    không thì số bị nhân. Số đo ra mét theo $INSUNITS; bản vẽ không khai thì he_so_don_vi (0.001 nếu vẽ mm).
    Nhãn chữ chỉ để đối chiếu. KHÁC cad_do_khoi_luong: đọc DXF không cần AutoCAD, đếm theo hình. loc_layer: regex.
    Đường lui: trống/sai layer → cad_thong_tin xem cấu trúc bản vẽ."""
    if not HAS_KIEM_KL:
        return _KL_THIEU
    dd, loi = _kl_dxf(duong_dan_dxf)
    if loi:
        return loi
    if max_dong <= 0 or he_so_don_vi < 0:
        return "max_dong phải > 0; he_so_don_vi ≥ 0 (0 = theo $INSUNITS)."
    try:
        return _kl_cad.dem_doi_tuong(dd, loc_layer or None, max_dong, he_so_don_vi or None, vung or None)
    except RuntimeError as e:
        return str(e)


@_DECO_DOC
def cad_hatch_giao_doi_tuong(duong_dan_dxf: str, layer_hatch: str, loc_doi_tuong: str, dung_sai: float = 0.02,
                             max_dong: int = 60, he_so_don_vi: float = 0, mau_hatch: str = "",
                             kich_thuoc: str = "", vung: str = "") -> str:
    """Đo từng đối tượng (hố ga, bồn cây...) so với vùng hatch lát: phần trên vùng tô, phần trong lỗ khoét — chống trừ lặp.
    Nhóm TRONG_VUNG/DA_KHOET/MOT_PHAN/NGOAI_VUNG; lấy TỔNG CẦN TRỪ (Σ phần trên vùng tô), không số cái × 1 cái.
    layer_hatch, loc_doi_tuong (layer/block), mau_hatch (vd '^ANGLE$' khi cùng layer có hatch vuốt nối): regex.
    kich_thuoc 'axb' (m) chỉ lấy hình chữ nhật đúng cỡ; vung như cad_dem_doi_tuong. dung_sai (0; 0,5). Cần shapely.
    Đường lui: không thấy hatch/đối tượng → cad_dem_doi_tuong xem tên layer/block thật."""
    if not HAS_KIEM_KL:
        return _KL_THIEU
    dd, loi = _kl_dxf(duong_dan_dxf)
    if loi:
        return loi
    if max_dong <= 0 or he_so_don_vi < 0:
        return "max_dong phải > 0; he_so_don_vi ≥ 0 (0 = theo $INSUNITS)."
    try:
        return _kl_cad.hatch_giao_doi_tuong(dd, layer_hatch, loc_doi_tuong, dung_sai, max_dong, he_so_don_vi or None,
                                            mau_hatch or None, kich_thuoc or None, vung or None)
    except RuntimeError as e:
        return str(e)

