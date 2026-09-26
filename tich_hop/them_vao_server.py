"""ĐOẠN GHÉP VÀO server.py (my-office-mcp v7.2.1+) — 3 tool mới, nhóm KIỂM KHỐI LƯỢNG. Tất cả CHỈ ĐỌC.

Đã chỉnh theo phản biện Codex R10 (26/09): decorator `_DECO_DOC` (server không có CHI_DOC),
`_nap_workbook(duong_dan, **kw)` (Codex đã đối chiếu chữ ký dòng 1496), đóng workbook trong finally,
hydrate cả file DXF, kiểm đầu vào trả lỗi 3 ý (đã thử gì · thấy gì · làm gì tiếp).

Việc của Claude Code trên máy khi ghép (skill chuyen-vien-mcp):
  1. Chép thư mục kiem_kl/ cạnh server.py.
  2. Dán 3 hàm dưới vào nhóm Excel / CAD. Tìm tên thật của hàm duyệt ô có thật (_o_co_that) và
     truyền vào kiem_kl.quet_loi._o_co_that nếu chữ ký khác (module có bản thay thế tạm).
  3. Cột: tool nhận cot_map_json; bản dò tiêu đề riêng của kiem_kl chỉ chạy khi KHÔNG có cot_map.
     Việc làm adapter từ _cham_diem_dong_tieu_de sang các vai trò dai/rong/cao/so_luong/kl_rieng/kl_chung
     ghi vào SO_NHAP làm đợt sau (Codex R10: map chung hiện có không cấp đủ các vai trò này).
  4. Thư viện tùy chọn: shapely (+ ezdxf nếu chưa có) — mỗi lib một try riêng; cập nhật
     HUONG_DAN_CAI_MAY_MOI.html + scripts\\dung_lai_may_moi.py (H0). Đo tổng docstring < 50.000 ký tự (G3b).
  5. soat_server.py sạch từ mức CAO, pytest toàn bộ không thụt lùi, rồi CHẠY THẬT trên bản sao GỐC
     trong _sandbox\\kiem-kl-ntt\\ (ca kiểm chứng ở skill kiem-tra-khoi-luong mục 5).
"""
try:
    from kiem_kl import quet_loi as _kl_quet
    from kiem_kl import cad as _kl_cad
    HAS_KIEM_KL = True
except ImportError:
    HAS_KIEM_KL = False

_KL_THIEU = "Thiếu module kiem_kl cạnh server.py. Chép thư mục kiem_kl/ từ bản vá rồi khởi động lại MCP."


@_DECO_DOC  # noqa: F821 — decorator chỉ-đọc có sẵn trong server.py
def excel_quet_loi_khoi_luong(duong_dan_file: str, ten_sheet: str = "", cot_map_json: str = "",
                              dong_bat_dau: int = 0, max_dong: int = 3000, max_ket_qua: int = 150) -> str:
    """Quét bảng khối lượng Excel (KLCT, diễn giải KL) tìm nghi vấn công thức để ưu tiên đối chiếu bản vẽ.

    Bắt: hệ số số lượng bỏ sót, khoản trừ ra dương, nhãn 'a x b' lệch dài/rộng, '(84 hố)' lệch cột
    số lượng, công thức lệch khối, SUM bỏ sót, #REF!/file ngoài, số gõ tay, tên sheet nghi macro.
    Đọc diễn giải font VNI. Kết quả là NGHI VẤN — không cờ ≠ đúng; luôn nêu phạm vi đã/chưa quét.
    cot_map_json ép cột khi tự dò sai, vd {"dien_giai":"C","so_luong":"I","kl_rieng":"J","kl_chung":"K"}.
    Đường lui: bảng không theo mẫu dài/rộng/số lượng → dùng read_sheet_data đọc thô rồi tự xử lý.
    """
    if not HAS_KIEM_KL:
        return _KL_THIEU
    import json
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
    dd = secure_path(duong_dan_file)  # noqa: F821
    ensure_file_hydrated(dd)  # noqa: F821
    wb_ct = wb_gt = None
    try:
        wb_ct = _nap_workbook(dd)                    # noqa: F821 — đọc CÔNG THỨC
        wb_gt = _nap_workbook(dd, data_only=True)    # noqa: F821 — đọc GIÁ TRỊ Excel lưu sẵn
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
            ra += f"\nKHÔNG QUÉT (không thấy cột KL riêng/chung — truyền ten_sheet + cot_map_json nếu cần): {', '.join(bo_qua)}"
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


@_DECO_DOC  # noqa: F821
def cad_dem_doi_tuong(duong_dan_dxf: str, loc_layer: str = "", max_dong: int = 40, he_so_don_vi: float = 0) -> str:
    """Đếm đối tượng bản vẽ DXF theo hình học: block, hình chữ nhật kín theo kích thước, chiều dài theo layer, diện tích hatch (đã trừ lỗ), nhãn chữ.

    Số đo quy đổi ra mét theo $INSUNITS; bản vẽ không khai đơn vị thì truyền he_so_don_vi (0.001 nếu vẽ mm).
    Nhãn chữ chỉ để đối chiếu, KHÔNG dùng làm số lượng. loc_layer: regex. DWG phải chuyển DXF trước.
    Đường lui: kết quả trống/không đúng layer → dùng cad_thong_tin xem cấu trúc bản vẽ rồi tự xử lý.
    """
    if not HAS_KIEM_KL:
        return _KL_THIEU
    dd = secure_path(duong_dan_dxf)  # noqa: F821
    if not dd.lower().endswith(".dxf"):
        return "Chỉ đọc .dxf. DWG: chuyển bằng ODA File Converter (hoặc AutoCAD DXFOUT) vào _sandbox rồi gọi lại."
    if max_dong <= 0 or he_so_don_vi < 0:
        return "max_dong phải > 0; he_so_don_vi ≥ 0 (0 = theo $INSUNITS)."
    ensure_file_hydrated(dd)  # noqa: F821
    try:
        return _kl_cad.dem_doi_tuong(dd, loc_layer or None, max_dong, he_so_don_vi or None)
    except RuntimeError as e:
        return str(e)


@_DECO_DOC  # noqa: F821
def cad_hatch_giao_doi_tuong(duong_dan_dxf: str, layer_hatch: str, loc_doi_tuong: str,
                             dung_sai: float = 0.02, max_dong: int = 60, he_so_don_vi: float = 0) -> str:
    """Đo từng đối tượng (hố ga, bồn cây...) so với vùng hatch lát: phần trên vùng tô, phần rơi vào lỗ khoét — chống trừ lặp diện tích.

    Trả nhóm TRONG_VUNG / DA_KHOET / MOT_PHAN / NGOAI_VUNG và TỔNG diện tích cần trừ = Σ phần nằm trên
    vùng tô (đúng cả khi đối tượng chỉ một phần trong lỗ). layer_hatch, loc_doi_tuong: regex tên
    layer/block. dung_sai trong (0; 0,5). Cần shapely.
    Đường lui: không thấy hatch/đối tượng → dùng cad_dem_doi_tuong xem tên layer/block thật rồi gọi lại.
    """
    if not HAS_KIEM_KL:
        return _KL_THIEU
    dd = secure_path(duong_dan_dxf)  # noqa: F821
    if max_dong <= 0 or he_so_don_vi < 0:
        return "max_dong phải > 0; he_so_don_vi ≥ 0 (0 = theo $INSUNITS)."
    ensure_file_hydrated(dd)  # noqa: F821
    try:
        return _kl_cad.hatch_giao_doi_tuong(dd, layer_hatch, loc_doi_tuong, dung_sai, max_dong, he_so_don_vi or None)
    except RuntimeError as e:
        return str(e)
