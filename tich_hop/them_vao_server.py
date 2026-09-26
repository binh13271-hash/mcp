"""ĐOẠN GHÉP VÀO server.py (my-office-mcp) — 3 tool mới, nhóm KIỂM KHỐI LƯỢNG. Tất cả CHỈ ĐỌC.

Việc của Claude Code trên máy công ty khi ghép (đúng quy trình skill chuyen-vien-mcp):
  1. Chép thư mục kiem_kl/ vào cạnh server.py (hoặc gộp hàm vào server.py nếu NGUYEN_TAC bắt buộc 1 file).
  2. Dán 3 hàm dưới vào nhóm tool Excel / CAD. KIỂM CHỮ KÝ THẬT của _nap_workbook, secure_path,
     ensure_file_hydrated trong server.py trước — đoạn này viết theo mô tả trong skill, chưa thấy code gốc.
  3. Thay kiem_kl.quet_loi.do_cot bằng _cham_diem_dong_tieu_de/_map_loai_cot + du-lieu\\tu_khoa_cot.json
     (không để 2 bộ dò tiêu đề song song — NGUYEN_TAC G6). Tạm thời có thể truyền cot_map tay.
  4. Thư viện tùy chọn mới: shapely (cad_hatch_giao_doi_tuong). ezdxf nếu máy chưa có.
     Cập nhật HUONG_DAN_CAI_MAY_MOI.html + scripts\\dung_lai_may_moi.py (NGUYEN_TAC H0).
  5. Chạy soat_server.py, pytest, rồi CHẠY THẬT trên bản sao KL DUONG ...TKBVTC--.xls và 6 DXF
     trong _sandbox\\kiem-kl-ntt\\: kết quả phải ra đúng các lỗi đã chốt (xem SKILL kiem-tra-khoi-luong,
     mục "Ca kiểm chứng").
"""
# ---- import (đặt ở khối import tùy chọn, MỖI lib một try riêng) -------------------------------
try:
    from kiem_kl import quet_loi as _kl_quet
    from kiem_kl import cad as _kl_cad
    HAS_KIEM_KL = True
except ImportError:
    HAS_KIEM_KL = False


@mcp.tool(annotations=CHI_DOC)  # noqa: F821 — mcp, CHI_DOC có sẵn trong server.py
def excel_quet_loi_khoi_luong(duong_dan_file: str, ten_sheet: str = "", cot_map_json: str = "",
                              dong_bat_dau: int = 0, max_ket_qua: int = 150) -> str:
    """Quét bảng khối lượng Excel (KLCT, diễn giải KL) tìm 9 kiểu lỗi công thức hay gặp, trả danh sách nghi vấn.

    Bắt: hệ số số lượng bị bỏ sót, khoản 'trừ' mà dương, nhãn 'a x b' lệch dài/rộng, '(84 hố)' lệch cột
    số lượng, công thức lệch dạng trong khối, SUM bỏ sót dòng cuối, #REF!/liên kết file ngoài, công thức
    toàn hằng số, sheet tên lạ (dấu vết virus macro). Đọc được diễn giải gõ font VNI.
    duong_dan_file: .xlsx/.xls (.xls tự chuyển tạm qua Excel ẩn). ten_sheet: bỏ trống = quét mọi sheet có
    cột khối lượng. cot_map_json: ép cột khi tự dò sai, vd '{"dien_giai":"C","so_luong":"I","kl_rieng":"J"}'.
    Kết quả là NGHI VẤN — chốt bằng bản vẽ trước khi sửa. Chỉ đọc, không ghi file.
    Đường lui: dò cột sai hoặc bảng không theo mẫu dài/rộng/cao/số lượng → dùng read_sheet_data đọc thô rồi tự xử lý.
    """
    if not HAS_KIEM_KL:
        return "Thiếu module kiem_kl cạnh server.py. Chép thư mục kiem_kl/ từ bản vá rồi khởi động lại MCP."
    import json
    dd = secure_path(duong_dan_file)  # noqa: F821
    ensure_file_hydrated(dd)  # noqa: F821
    wb_ct = _nap_workbook(dd)                    # noqa: F821 — KIỂM chữ ký: cần bản đọc CÔNG THỨC
    wb_gt = _nap_workbook(dd, data_only=True)    # noqa: F821 — và bản đọc GIÁ TRỊ lưu sẵn
    try:
        cot_map = json.loads(cot_map_json) if cot_map_json else None
    except ValueError as e:
        return f"cot_map_json không phải JSON hợp lệ ({e}). Ví dụ: {{\"dien_giai\":\"C\",\"so_luong\":\"I\"}}"
    ten = [ten_sheet] if ten_sheet else wb_ct.sheetnames
    if ten_sheet and ten_sheet not in wb_ct.sheetnames:
        return f"Không có sheet '{ten_sheet}'. Các sheet: {wb_ct.sheetnames}"
    loi, bo_qua = [], []
    for t in ten:
        cot = _kl_quet.do_cot(wb_ct[t])[0] if not cot_map else cot_map
        if not ten_sheet and not ({"kl_rieng", "kl_chung"} & set(cot)):
            bo_qua.append(t)
            continue
        l, _ = _kl_quet.quet_loi_sheet(wb_ct[t], wb_gt[t], cot_map=cot_map, dong_bat_dau=dong_bat_dau or None)
        loi += l
    la, khong_goi = _kl_quet.quet_sheet_la(wb_ct)
    loi = la + loi
    ra = _kl_quet.dinh_dang_ket_qua(loi, max_ket_qua)
    if bo_qua:
        ra += f"\nBỏ qua (không thấy cột khối lượng riêng/chung): {', '.join(bo_qua)}"
    if khong_goi:
        ra += f"\nSheet không được công thức nào tham chiếu (xem có phải chép từ dự án khác): {', '.join(khong_goi)}"
    return ra


@mcp.tool(annotations=CHI_DOC)  # noqa: F821
def cad_dem_doi_tuong(duong_dan_dxf: str, loc_layer: str = "", max_dong: int = 40) -> str:
    """Đếm đối tượng bản vẽ DXF theo hình học: block theo tên/layer, hình chữ nhật kín theo kích thước, tổng chiều dài theo layer, diện tích hatch (đã trừ lỗ), nhãn chữ.

    Dùng đối chiếu số lượng hố ga/bồn cây/chiều dài bó vỉa/diện tích lát với bảng khối lượng. Nhãn chữ
    chỉ để đối chiếu, KHÔNG dùng làm số lượng. loc_layer: regex lọc layer. DWG phải chuyển DXF trước.
    Chỉ đọc. Đường lui: kết quả trống/không đúng layer → dùng cad_thong_tin xem cấu trúc bản vẽ rồi tự xử lý.
    """
    if not HAS_KIEM_KL:
        return "Thiếu module kiem_kl cạnh server.py."
    dd = secure_path(duong_dan_dxf)  # noqa: F821
    if not dd.lower().endswith(".dxf"):
        return "Chỉ đọc .dxf. DWG: chuyển bằng ODA File Converter (hoặc AutoCAD DXFOUT) vào _sandbox rồi gọi lại."
    try:
        return _kl_cad.dem_doi_tuong(dd, loc_layer or None, max_dong)
    except RuntimeError as e:
        return str(e)


@mcp.tool(annotations=CHI_DOC)  # noqa: F821
def cad_hatch_giao_doi_tuong(duong_dan_dxf: str, layer_hatch: str, loc_doi_tuong: str,
                             nguong: float = 0.5, max_dong: int = 60) -> str:
    """Đo từng đối tượng (hố ga, bồn cây...) nằm trong vùng hatch (vùng lát) bao nhiêu %, để biết cái nào phải trừ diện tích, cái nào hatch đã khoét sẵn.

    Chống TRỪ LẶP: diện tích lát lấy theo hatch/nhãn có thể đã khoét bồn cây; bảng tính lại trừ đủ số
    bồn là trừ hai lần. Phân nhóm: TRONG_VUNG (≥ nguong, cần trừ) · DA_KHOET (trùng lỗ hatch, không trừ
    nữa) · CHAM_MEP · NGOAI_VUNG. layer_hatch, loc_doi_tuong: regex (tên block hoặc layer).
    Cần thư viện shapely. Chỉ đọc.
    Đường lui: không thấy hatch/đối tượng → dùng cad_dem_doi_tuong xem tên layer/block thật rồi gọi lại.
    """
    if not HAS_KIEM_KL:
        return "Thiếu module kiem_kl cạnh server.py."
    dd = secure_path(duong_dan_dxf)  # noqa: F821
    try:
        return _kl_cad.hatch_giao_doi_tuong(dd, layer_hatch, loc_doi_tuong, nguong, max_dong)
    except RuntimeError as e:
        return str(e)
