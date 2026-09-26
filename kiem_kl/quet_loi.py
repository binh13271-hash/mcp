"""Quét lỗi công thức trong bảng khối lượng Excel (KLCT, bảng diễn giải khối lượng).

Rút từ đợt kiểm KL một dự án đường đô thị (25/09/2026): 70% lỗi thật tìm ra bằng
đọc công thức thuộc 8 kiểu dưới đây — lặp lại được, nên giao máy dò trước, người/AI chỉ
đọc bản vẽ cho các dòng bị gắn cờ.

  HE_SO_BO_SOT      cột số lượng có số > 1 nhưng công thức khối lượng cùng dòng không nhân nó
  DAU_KHOAN_TRU     diễn giải ghi "trừ" mà khối lượng dương
  NHAN_LECH_KT      diễn giải ghi "a x b" khác kích thước nhập ở 2 cột dài/rộng
                    (chỉ xét trong khối dòng mà đa số dòng khớp nhãn -> ít báo nhầm)
  SO_LUONG_LECH     diễn giải ghi "(84 hố)" khác cột số lượng
  CONG_THUC_LECH    công thức khác dạng đa số trong cùng khối dòng liền nhau
  SUM_BO_SOT        =SUM(Xa:Xb) dừng trước một dòng con vẫn còn số liệu
  THAM_CHIEU        #REF!, liên kết ra file ngoài
  HANG_SO           công thức chỉ gồm hằng số / số lẻ nhập tay, không dẫn nguồn
  SHEET_LA          sheet tên lạ (xxxxxxxx, HelpMe, Recovered_...) — dấu vết virus macro cũ

Chỉ ĐỌC. Kết luận cuối cùng thuộc người/skill đối chiếu bản vẽ: đây là danh sách nghi vấn.
"""
import re
from collections import Counter

from openpyxl.formula import Tokenizer
from openpyxl.utils import column_index_from_string, get_column_letter

from .vni import bo_dau, giai_ma_vni

MUC_CAO, MUC_TB, MUC_THAP = "CAO", "TB", "THAP"
_THU_TU_MUC = {MUC_CAO: 0, MUC_TB: 1, MUC_THAP: 2}

# Từ khóa tiêu đề cột (so trên chuỗi đã bỏ dấu, ghép nhiều dòng tiêu đề).
# CHỈ dùng khi chạy độc lập. Ghép vào server.py thì thay bằng _map_loai_cot/_cham_diem_dong_tieu_de
# + du-lieu\tu_khoa_cot.json — không được để 2 bộ dò tiêu đề song song (NGUYEN_TAC G6).
_TU_KHOA_COT = [
    ("kl_rieng", ("rieng",)),
    ("kl_chung", ("chung",)),
    ("so_luong", ("g/ nhau", "g/nhau", "giao nhau", "so luong", "sl")),
    ("dien_tich", ("dien tich",)),
    ("dien_giai", ("hang muc", "dien giai", "noi dung", "ten cong tac")),
    ("dai", ("dai",)),
    ("rong", ("rong",)),
    ("cao", ("cao", "day")),
    ("tt", ("tt", "stt")),
]
_KT = re.compile(r"(\d+(?:[.,]\d+)?)\s*[xX×]\s*(\d+(?:[.,]\d+)?)")
_DEM = re.compile(r"\(\s*(\d+)\s*(ho|cai|cay|bon|tam|bo|coc|vi tri)\b")
_SHEET_LA = re.compile(r"^(x{4,}|helpme.*|recovered_sheet\d*|macro\d*)$", re.I)


def _so(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def do_cot(ws, dong_tieu_de_toi_da=15):
    """Dò map {loai: chữ cột} từ các dòng tiêu đề. Trả (map, dong_cuoi_tieu_de).

    Vùng tiêu đề = các dòng TRƯỚC dòng số liệu đầu tiên (dòng có ≥2 ô số/công thức) — bảng
    bắt đầu ngay dòng 9 thì chữ diễn giải dòng 9-15 không được lẫn vào tiêu đề.
    """
    dau_so = dong_tieu_de_toi_da + 1
    for hang in ws.iter_rows(min_row=1, max_row=dong_tieu_de_toi_da):
        if sum(1 for o in hang if _so(o.value) or (isinstance(o.value, str) and o.value.startswith("="))) >= 2:
            dau_so = hang[0].row
            break
    chu = {}
    for hang in ws.iter_rows(min_row=1, max_row=dau_so - 1):
        for o in hang:
            if isinstance(o.value, str) and o.value.strip():
                chu.setdefault(o.column_letter, []).append((o.row, bo_dau(o.value)))

    def khop(chuoi, khoa):
        return any(re.search(r"(^|[^a-z])" + re.escape(k) + r"($|[^a-z])", chuoi) for k in khoa)

    cot_map, dong_cuoi = {}, 0
    for cot, cac in chu.items():
        ghep = " ".join(" ".join(t for _, t in cac).split())
        for loai, khoa in _TU_KHOA_COT:
            if loai not in cot_map and khop(ghep, khoa):
                cot_map[loai] = cot
                dong_cuoi = max([dong_cuoi] + [r for r, t in cac if any(khop(t, k) for _, k in _TU_KHOA_COT)])
                break
    return cot_map, dong_cuoi


def _tham_chieu(cong_thuc):
    """Liệt kê tham chiếu trong công thức: [(sheet|None, cot, dong), ...] (dải được bung 2 đầu)."""
    ra = []
    try:
        tok = Tokenizer(cong_thuc)
    except Exception:
        return ra
    for t in tok.items:
        if t.type != "OPERAND" or t.subtype != "RANGE":
            continue
        s = t.value
        sheet = None
        if "!" in s:
            sheet, s = s.rsplit("!", 1)
            sheet = sheet.strip("'")
        for phan in s.replace("$", "").split(":"):
            m = re.fullmatch(r"([A-Z]{1,3})(\d+)", phan)
            if m:
                ra.append((sheet, m.group(1), int(m.group(2))))
    return ra


def _mau_cong_thuc(cong_thuc, dong):
    """Chuẩn hóa công thức để so dạng: E76 trên dòng 76 -> E[0]; sheet khác giữ nguyên."""
    try:
        tok = Tokenizer(cong_thuc)
    except Exception:
        return cong_thuc
    phan = []
    for t in tok.items:
        v = t.value
        if t.type == "OPERAND" and t.subtype == "RANGE" and "!" not in v:
            v = re.sub(r"\$?([A-Z]{1,3})\$?(\d+)", lambda m: f"{m.group(1)}[{int(m.group(2)) - dong}]", v)
        elif t.type == "OPERAND" and t.subtype == "NUMBER":
            v = "#"
        phan.append(v)
    return "=" + "".join(phan)


class _BoTinh:
    """Lấy giá trị ô: ưu tiên giá trị Excel lưu sẵn; thiếu thì tự tính công thức số học đơn giản."""

    def __init__(self, ws_ct, ws_gt=None):
        self.ws_ct, self.ws_gt, self.nho = ws_ct, ws_gt, {}

    def lay(self, cot, dong, sau=0):
        k = (cot, dong)
        if k in self.nho:
            return self.nho[k]
        v = self.ws_ct[f"{cot}{dong}"].value
        self.nho[k] = None  # chặn vòng tham chiếu A->B->A
        if isinstance(v, str) and v.startswith("="):
            gt = self.ws_gt[f"{cot}{dong}"].value if self.ws_gt is not None else None
            v = gt if gt is not None else (self._tinh(v, sau) if sau < 30 else None)
        self.nho[k] = v
        return v

    def _tinh(self, cong_thuc, sau):
        bt = cong_thuc[1:]
        if "!" in bt or "[" in bt:
            return None

        def tong(m):
            c1, d1, c2, d2 = m.group(1), int(m.group(2)), m.group(3), int(m.group(4))
            s = 0.0
            for ci in range(column_index_from_string(c1), column_index_from_string(c2) + 1):
                for d in range(d1, d2 + 1):
                    x = self.lay(get_column_letter(ci), d, sau + 1)
                    if _so(x):
                        s += x
            return repr(s)

        bt = re.sub(r"SUM\(\$?([A-Z]{1,3})\$?(\d+):\$?([A-Z]{1,3})\$?(\d+)\)", tong, bt, flags=re.I)

        def o(m):
            x = self.lay(m.group(1), int(m.group(2)), sau + 1)
            return repr(float(x)) if _so(x) else ("0" if x is None else "None")

        bt = re.sub(r"\$?([A-Z]{1,3})\$?(\d+)", o, bt)
        if "None" in bt or not re.fullmatch(r"[\d\s.eE+\-*/()]*", bt):
            return None
        try:
            return eval(bt, {"__builtins__": {}}, {})  # chỉ còn số và + - * / ( )
        except Exception:
            return None


def quet_loi_sheet(ws_ct, ws_gt=None, cot_map=None, dong_bat_dau=None, max_dong=5000):
    """Quét một sheet. ws_ct: sheet đọc công thức; ws_gt: cùng sheet đọc giá trị lưu sẵn (data_only).

    Trả (danh_sach_loi, cot_map). Mỗi lỗi: dict(muc, loai, o, mo_ta, hien, de_xuat).
    """
    tu_do, dong_td = do_cot(ws_ct)
    cot_map = {**tu_do, **(cot_map or {})}
    bt = _BoTinh(ws_ct, ws_gt)
    dong_dau = dong_bat_dau or (dong_td + 1)
    dong_cuoi = min(ws_ct.max_row, dong_dau + max_dong)
    C = cot_map.get
    loi = []

    def them(muc, loai, o, mo_ta, hien=None, de_xuat=None):
        loi.append(dict(muc=muc, loai=loai, o=f"{ws_ct.title}!{o}", mo_ta=mo_ta, hien=hien, de_xuat=de_xuat))

    def ct(cot, d):
        v = ws_ct[f"{cot}{d}"].value if cot else None
        return v if isinstance(v, str) and v.startswith("=") else None

    cot_kq = [c for c in (C("kl_rieng"), C("kl_chung")) if c]
    cot_kt = [c for c in (C("dai"), C("rong"), C("cao"), C("dien_tich")) if c]
    nhan = {}      # dong -> (khop_nhan: bool) cho dòng có nhãn a x b và dài/rộng là số nhập tay
    mau = {c: {} for c in cot_kq}

    for d in range(dong_dau, dong_cuoi + 1):
        dg = ws_ct[f"{C('dien_giai')}{d}"].value if C("dien_giai") else None
        dg_u = giai_ma_vni(dg) if isinstance(dg, str) else ""
        dg_k = bo_dau(dg_u)
        sl = bt.lay(C("so_luong"), d) if C("so_luong") else None

        for c in cot_kq:
            f = ct(c, d)
            v = bt.lay(c, d)
            if isinstance(v, str) and v.startswith("#REF") or (f and "#REF!" in f):
                them(MUC_CAO, "THAM_CHIEU", f"{c}{d}", "Ô lỗi #REF! — tham chiếu bị xóa/dời, số tổng hợp sai.", f)
            if not f:
                continue
            mau[c][d] = _mau_cong_thuc(f, d)
            if "[" in f or "http" in f.lower():
                them(MUC_TB, "THAM_CHIEU", f"{c}{d}", "Công thức lấy số từ FILE NGOÀI — mất liên kết là sai số; nên thay bằng giá trị/nguồn trong file.", f)
            ref = [(None, co, dd) for s, co, dd in _tham_chieu(f) if s in (None, ws_ct.title)]
            ref_dong = {co for _, co, dd in ref if dd == d}
            # 1. Hệ số số lượng bị bỏ sót
            nhan_o_cot_khac = any(
                C("so_luong") in {co for s2, co, dd in _tham_chieu(ct(c2, d) or "") if s2 is None and dd == d}
                for c2 in cot_kq if c2 != c)
            if (_so(sl) and sl not in (0, 1) and C("so_luong") not in ref_dong and not nhan_o_cot_khac
                    and ref_dong & set(cot_kt) and not any(dd != d for _, co, dd in ref)):
                de = v * sl if _so(v) else None
                them(MUC_CAO, "HE_SO_BO_SOT", f"{c}{d}",
                     f"Cột số lượng {C('so_luong')}{d}={sl:g} nhưng công thức không nhân. Diễn giải: {dg_u.strip()[:70]}",
                     v, de)
            # 2. Khoản trừ mà dương
            if re.match(r"^[\s+\-–]*tru\b", dg_k) and _so(v) and v > 0:
                them(MUC_CAO, "DAU_KHOAN_TRU", f"{c}{d}",
                     f"Diễn giải là khoản TRỪ nhưng khối lượng dương. Diễn giải: {dg_u.strip()[:70]}", v, -v)
            # 7. Hằng số nhập tay trong công thức
            if not ref and re.search(r"\d", f):
                so_le = re.findall(r"\d+\.(\d+)", f)
                if len(f) > 4:
                    them(MUC_THAP, "HANG_SO", f"{c}{d}",
                         "Công thức chỉ gồm hằng số — cần ghi nguồn (bản vẽ/bảng thống kê) ở cột ghi chú."
                         + (" Có số lẻ ≥3 chữ số, dễ chép tay sai." if any(len(x) >= 3 for x in so_le) else ""), f)
            # 6. SUM dừng trước dòng con còn số liệu
            m = re.fullmatch(r"=SUM\(\$?([A-Z]{1,3})\$?(\d+):\$?([A-Z]{1,3})\$?(\d+)\)", f.replace(" ", ""), re.I)
            if m and int(m.group(2)) == d + 1:
                if m.group(1) != m.group(3):
                    them(MUC_THAP, "SUM_BO_SOT", f"{c}{d}", f"SUM trải 2 cột {m.group(1)}:{m.group(3)} — kiểm lại có cố ý không.", f)
                n = int(m.group(4)) + 1
                o_con = ws_ct[f"{m.group(1)}{n}"].value
                la_dau_muc = (C("tt") and ws_ct[f"{C('tt')}{n}"].value not in (None, "")) or any(
                    ws_ct[f"{k}{n}"].value not in (None, "") for k in cot_kq if k != m.group(1))
                if o_con not in (None, "") and not la_dau_muc:
                    them(MUC_TB, "SUM_BO_SOT", f"{c}{d}",
                         f"SUM dừng ở dòng {m.group(4)} nhưng dòng {n} ngay dưới vẫn có số ({m.group(1)}{n}) và không phải đầu mục mới.", f)

        # 3. Nhãn a x b so với dài/rộng nhập tay
        if C("dai") and C("rong"):
            kt = _KT.findall(dg_u.replace(",", "."))
            e, fr = ws_ct[f"{C('dai')}{d}"].value, ws_ct[f"{C('rong')}{d}"].value
            if len(kt) == 1 and _so(e) and _so(fr):
                a, b = float(kt[0][0]), float(kt[0][1])
                nhan[d] = (sorted((round(a, 4), round(b, 4))) == sorted((round(float(e), 4), round(float(fr), 4))),
                           f"{a:g}x{b:g}", f"{float(e):g}x{float(fr):g}")
        # 4. "(84 hố)" so với cột số lượng
        m = _DEM.search(dg_k)
        if m and _so(sl) and int(m.group(1)) != sl:
            them(MUC_TB, "SO_LUONG_LECH", f"{C('so_luong')}{d}",
                 f"Diễn giải ghi {m.group(1)} {m.group(2)} nhưng cột số lượng = {sl:g}.", sl, int(m.group(1)))

    # 3b. Chỉ báo lệch nhãn trong khối mà đa số dòng khớp (khối đo kích thước thật của đối tượng)
    for khoi in _khoi_lien(sorted(nhan)):
        if len(khoi) < 3:
            continue
        khop = [d for d in khoi if nhan[d][0]]
        if len(khop) * 2 >= len(khoi):
            for d in khoi:
                if not nhan[d][0]:
                    them(MUC_CAO, "NHAN_LECH_KT", f"{C('dai')}{d}",
                         f"Diễn giải ghi {nhan[d][1]} nhưng dài×rộng nhập {nhan[d][2]} ({len(khop)}/{len(khoi)} dòng cùng khối khớp nhãn).",
                         nhan[d][2], nhan[d][1])

    # 5. Công thức lệch dạng đa số trong khối liền nhau (khối cắt tại dòng đầu mục có số TT)
    dau_muc = set()
    if C("tt"):
        dau_muc = {d for d in range(dong_dau, dong_cuoi + 1) if ws_ct[f"{C('tt')}{d}"].value not in (None, "")}

    def cot_cung_dong(mau_ct):
        return set(re.findall(r"([A-Z]{1,3})\[0\]", mau_ct))

    for c, m in mau.items():
        for khoi in _khoi_lien(sorted(m), cat=dau_muc):
            if len(khoi) < 3:
                continue
            dem = Counter(m[d] for d in khoi)
            chinh, sl_chinh = dem.most_common(1)[0]
            if sl_chinh * 2 <= len(khoi) or sl_chinh == len(khoi):
                continue
            for d in khoi:
                if m[d] == chinh:
                    continue
                ly_do = []
                if m[d].startswith("=-") != chinh.startswith("=-"):
                    ly_do.append("đổi dấu")
                thieu = [co for co in cot_cung_dong(chinh) - cot_cung_dong(m[d]) if _so(bt.lay(co, d)) and bt.lay(co, d) != 1]
                if thieu:
                    ly_do.append("không nhân cột " + ",".join(sorted(thieu)) + " dù ô có số")
                if ly_do:
                    them(MUC_TB, "CONG_THUC_LECH", f"{c}{d}",
                         f"{' + '.join(ly_do)[:1].upper() + ' + '.join(ly_do)[1:]} so với {sl_chinh}/{len(khoi)} dòng cùng khối ({chinh}).",
                         ws_ct[f"{c}{d}"].value)

    return _loc_trung(loi), cot_map


def _khoi_lien(dong_sx, khe=1, cat=()):
    khoi, cu = [], None
    for d in dong_sx:
        if cu is not None and d - cu <= khe + 1 and d not in cat:
            khoi[-1].append(d)
        else:
            khoi.append([d])
        cu = d
    return khoi


def _loc_trung(loi):
    thay, ra = set(), []
    for x in loi:
        k = (x["loai"], x["o"])
        if k not in thay:
            thay.add(k)
            ra.append(x)
    ra.sort(key=lambda x: (_THU_TU_MUC[x["muc"]], x["loai"], x["o"]))
    return ra


def quet_sheet_la(wb):
    """Sheet tên lạ (dấu vết virus macro XLM kiểu Classic.Poppy) + sheet không ai tham chiếu."""
    loi = []
    ten = [ws.title for ws in wb.worksheets]
    duoc_goi = set()
    for ws in wb.worksheets:
        for hang in ws.iter_rows(max_row=min(ws.max_row, 5000)):
            for o in hang:
                if isinstance(o.value, str) and o.value.startswith("=") and "!" in o.value:
                    for s, _, _ in _tham_chieu(o.value):
                        if s and s != ws.title:
                            duoc_goi.add(s)
    for t in ten:
        if _SHEET_LA.match(t):
            loi.append(dict(muc=MUC_CAO, loai="SHEET_LA", o=t, hien=None, de_xuat=None,
                            mo_ta="Tên sheet lạ — dấu vết virus macro Excel 4.0 cũ. Mở file khi TẮT macro, xóa sheet trước khi trình, quét virus."))
    return loi, sorted(set(ten) - duoc_goi)


def dinh_dang_ket_qua(loi, max_ket_qua=150):
    """Trả bảng gọn dạng 'mức|loại|ô|hiện tại|đề xuất|mô tả' + dòng tổng."""
    dem = Counter(x["muc"] for x in loi)
    dong = [f"Tổng {len(loi)} nghi vấn: CAO {dem.get(MUC_CAO, 0)} · TB {dem.get(MUC_TB, 0)} · THẤP {dem.get(MUC_THAP, 0)}",
            "muc|loai|o|hien|de_xuat|mo_ta"]

    def g(v):
        return "" if v is None else (f"{v:.6g}" if _so(v) else str(v))

    for x in loi[:max_ket_qua]:
        dong.append("|".join([x["muc"], x["loai"], x["o"], g(x["hien"]), g(x["de_xuat"]), x["mo_ta"].replace("|", "/")]))
    if len(loi) > max_ket_qua:
        dong.append(f"Đã trả {max_ket_qua}/{len(loi)} dòng (mức CAO xếp trước). Tăng max_ket_qua hoặc lọc theo sheet.")
    return "\n".join(dong)
