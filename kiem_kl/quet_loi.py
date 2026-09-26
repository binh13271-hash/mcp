"""Quét NGHI VẤN công thức trong bảng khối lượng Excel (KLCT, bảng diễn giải khối lượng).

Rút từ đợt kiểm KL một dự án đường đô thị (25/09/2026). Máy dò các kiểu lỗi lặp lại được để
ƯU TIÊN thứ tự đối chiếu bản vẽ — không thay việc đối chiếu, "không cờ" KHÔNG có nghĩa là đúng.

  HE_SO_BO_SOT      cột số lượng có số ≠ 0/1 nhưng không công thức nào trên dòng nhân nó vào kết quả
  DAU_KHOAN_TRU     diễn giải ghi "trừ" mà kết quả CUỐI của dòng dương
  NHAN_LECH_KT      diễn giải "a x b" khác dài/rộng nhập tay (chỉ xét khối mà đa số dòng khớp nhãn)
  SO_LUONG_LECH     diễn giải "(84 hố)" khác cột số lượng
  CONG_THUC_LECH    công thức khác đa số trong cùng khối: đổi dấu / thiếu cột có số / khác phép toán
  SUM_BO_SOT        =SUM(Xa:Xb) dừng trước một dòng con vẫn còn số liệu
  THAM_CHIEU        #REF!/lỗi ở BẤT KỲ ô nào của dòng; liên kết ra file ngoài
  HANG_SO           công thức toàn hằng số / số gõ tay trong cột khối lượng — cần ghi nguồn
  SHEET_LA          tên sheet giống dấu vết macro XLM cũ — NGHI VẤN, phải quét bằng phần mềm diệt virus
  CAU_TRUC          không dò đủ cột / hết ngân sách / quét chưa hết — kết quả KHÔNG đầy đủ

Chỉ ĐỌC. Không dùng eval: công thức được phân tích bằng Tokenizer của openpyxl, chỉ hỗ trợ
+ - * / ( ), SUM, ROUND; mọi thứ khác là CHƯA TÍNH ĐƯỢC (không bao giờ đoán thành 0).
"""
import math
import re
import time
from collections import Counter

from openpyxl.formula import Tokenizer
from openpyxl.utils import column_index_from_string, get_column_letter

from .vni import bo_dau, giai_ma_vni

MUC_CAO, MUC_TB, MUC_THAP = "CAO", "TB", "THAP"
_THU_TU_MUC = {MUC_CAO: 0, MUC_TB: 1, MUC_THAP: 2}
CHUA = type("ChuaTinh", (), {"__repr__": lambda s: "CHUA_TINH"})()  # giá trị không xác định

# Từ khóa tiêu đề — CHỈ dùng khi chạy độc lập. Ghép vào server.py thì truyền cot_map dựng từ bộ dò
# sẵn có (_cham_diem_dong_tieu_de + du-lieu\tu_khoa_cot.json); có cot_map thì do_cot KHÔNG được gọi.
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
LOAI_COT = {k for k, _ in _TU_KHOA_COT}
_KT = re.compile(r"(\d+(?:[.,]\d+)?)\s*[xX×]\s*(\d+(?:[.,]\d+)?)")
_DEM = re.compile(r"\(\s*(\d+)\s*(ho|cai|cay|bon|tam|bo|coc|vi tri)\b")
_SHEET_LA = re.compile(r"^(x{4,}|helpme.*|recovered_sheet\d*|macro\d*)$", re.I)
_O = re.compile(r"^(\$?)([A-Z]{1,3})(\$?)(\d+)$")


def _so(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


class _HetNganSach(Exception):
    pass


class _KhongHoTro(Exception):
    pass


# ------------------------------------------------------------------ dò cột (chạy độc lập)
def do_cot(ws, dong_tieu_de_toi_da=15):
    """Dò {loai: chữ cột} từ vùng tiêu đề = các dòng TRƯỚC dòng số liệu đầu tiên. Trả (map, dong_cuoi)."""
    dau_so = dong_tieu_de_toi_da + 1
    for hang in ws.iter_rows(min_row=1, max_row=dong_tieu_de_toi_da, max_col=min(ws.max_column, 60)):
        if sum(1 for o in hang if _so(o.value) or (isinstance(o.value, str) and o.value.startswith("="))) >= 2:
            dau_so = hang[0].row
            break
    chu = {}
    for hang in ws.iter_rows(min_row=1, max_row=dau_so - 1, max_col=min(ws.max_column, 60)):
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


def kiem_cot_map(cot_map):
    """Trả None nếu hợp lệ, không thì câu lỗi nêu đúng chỗ sai."""
    if not isinstance(cot_map, dict):
        return "cot_map phải là object {loai: chữ cột}."
    sai_loai = [k for k in cot_map if k not in LOAI_COT]
    sai_cot = [f"{k}={v}" for k, v in cot_map.items() if not (isinstance(v, str) and re.fullmatch(r"[A-Z]{1,3}", v))]
    if sai_loai or sai_cot:
        return (f"cot_map sai: loại không biết {sai_loai}, cột không hợp lệ {sai_cot}. "
                f"Loại hợp lệ: {sorted(LOAI_COT)}; cột viết hoa, vd \"J\".")
    return None


# ------------------------------------------------------------------ tham chiếu & mẫu công thức
def _tach_token(cong_thuc):
    try:
        return [t for t in Tokenizer(cong_thuc).items if t.type != "WHITE-SPACE"]
    except Exception:
        return None


def _tham_chieu(cong_thuc):
    """[(sheet|None, cot, dong), ...] — dải được bung 2 đầu."""
    ra = []
    for t in _tach_token(cong_thuc) or []:
        if t.type != "OPERAND" or t.subtype != "RANGE":
            continue
        s, sheet = t.value, None
        if "!" in s:
            sheet, s = s.rsplit("!", 1)
            sheet = sheet.strip("'")
        for phan in s.split(":"):
            m = _O.match(phan)
            if m:
                ra.append((sheet, m.group(2), int(m.group(4))))
    return ra


def _mau_cong_thuc(cong_thuc, dong):
    """E76 trên dòng 76 -> E[0]; $I$1 (tuyệt đối) giữ nguyên; số -> #; sheet khác giữ nguyên."""
    tok = _tach_token(cong_thuc)
    if tok is None:
        return cong_thuc
    phan = []
    for t in tok:
        v = t.value
        if t.type == "OPERAND" and t.subtype == "RANGE" and "!" not in v:
            def doi(m):
                if m.group(3) == "$":
                    return m.group(0)
                return f"{m.group(2)}[{int(m.group(4)) - dong}]"
            v = ":".join(_O.sub(doi, p) if _O.match(p) else p for p in v.split(":"))
        elif t.type == "OPERAND" and t.subtype == "NUMBER":
            v = "#"
        phan.append(v)
    return "=" + "".join(phan)


def _cot_cung_dong(mau):
    return set(re.findall(r"([A-Z]{1,3})\[0\]", mau))


def _phep_toan(mau):
    return re.sub(r"\$?[A-Z]{1,3}(\[-?\d+\]|\$\d+)|#", "", mau)


def _la_tich(cong_thuc, dong, cot_can, ten_sheet):
    """True nếu công thức chỉ là TÍCH (dấu - đầu tùy chọn) và có đủ các cột cot_can cùng dòng."""
    tok = _tach_token(cong_thuc)
    if not tok:
        return False
    thay = set()
    for t in tok:
        if t.type == "OPERAND" and t.subtype == "RANGE":
            s = t.value.rsplit("!", 1)
            if len(s) == 2 and s[0].strip("'") != ten_sheet:
                return False
            m = _O.match(s[-1])
            if not m:
                return False
            if int(m.group(4)) == dong:
                thay.add(m.group(2))
        elif t.type == "OPERAND" and t.subtype == "NUMBER":
            continue
        elif t.type == "OPERATOR-INFIX" and t.value == "*":
            continue
        elif t.type == "OPERATOR-PREFIX" and t.value in "-+":
            continue
        else:
            return False
    return set(cot_can) <= thay


# ------------------------------------------------------------------ bộ tính (không eval)
class _BoTinh:
    """Giá trị ô: số Excel lưu sẵn nếu có; không thì tự tính công thức + - * / ( ) SUM ROUND.

    Trả số | None (ô trống) | str (chữ) | CHUA (lỗi, vòng, hàm chưa hỗ trợ, hết ngân sách).
    """

    def __init__(self, ws_ct, ws_gt=None, max_o=200_000, han_giay=40.0, max_dai=20_000):
        self.ws_ct, self.ws_gt, self.nho = ws_ct, ws_gt, {}
        self.con_o, self.max_dai = max_o, max_dai
        self.het_gio = time.monotonic() + han_giay
        self.het_ngan_sach = False
        self.tu_tinh = 0

    def _tieu(self, so_o=1):
        self.con_o -= so_o
        if self.con_o < 0 or time.monotonic() > self.het_gio:
            self.het_ngan_sach = True
            raise _HetNganSach()

    def lay(self, cot, dong):
        k = (cot, dong)
        if k in self.nho:
            return self.nho[k]
        self.nho[k] = CHUA  # đang tính: gặp lại = vòng tham chiếu
        try:
            self._tieu()
            v = self.ws_ct[f"{cot}{dong}"].value
            if isinstance(v, str) and v.startswith("="):
                gt = self.ws_gt[f"{cot}{dong}"].value if self.ws_gt is not None else None
                if gt is not None:
                    v = CHUA if isinstance(gt, str) and gt.startswith("#") else gt
                else:
                    self.tu_tinh += 1
                    v = self._tinh(v)
            elif isinstance(v, str) and v.startswith("#"):
                v = CHUA
            elif v is not None and not isinstance(v, (int, float, str)):
                v = CHUA  # ngày tháng, bool... không phải khối lượng
            if isinstance(v, float) and not math.isfinite(v):
                v = CHUA
        except _HetNganSach:
            v = CHUA
        self.nho[k] = v
        return v

    def _tinh(self, cong_thuc):
        if len(cong_thuc) > self.max_dai:
            return CHUA
        tok = _tach_token(cong_thuc)
        if not tok:
            return CHUA
        p = _PhanTich(tok, self)
        try:
            v = p.bieu_thuc()
            if p.i != len(tok):
                return CHUA
        except (_KhongHoTro, ZeroDivisionError, OverflowError):
            return CHUA
        return v if _so(v) and abs(v) < 1e15 else CHUA

    def tong_dai(self, dai):
        s, _, e = dai.partition(":")
        m1, m2 = _O.match(s), _O.match(e or s)
        if not m1 or not m2:
            raise _KhongHoTro()
        c1, c2 = sorted((column_index_from_string(m1.group(2)), column_index_from_string(m2.group(2))))
        d1, d2 = sorted((int(m1.group(4)), int(m2.group(4))))
        n = (c2 - c1 + 1) * (d2 - d1 + 1)
        if n > 50_000:            # chặn TRƯỚC khi bung dải
            raise _KhongHoTro()
        self._tieu(n)
        tong = 0.0
        for ci in range(c1, c2 + 1):
            for d in range(d1, d2 + 1):
                x = self.lay(get_column_letter(ci), d)
                if x is CHUA:
                    raise _KhongHoTro()
                if _so(x):
                    tong += x
        return tong


class _PhanTich:
    """Phân tích đệ quy: bt := hang (± hang)* ; hang := nhan (*|/ nhan)* ; nhan := ±nhan | số | ô | hàm | (bt)."""

    def __init__(self, tok, bo_tinh):
        self.tok, self.i, self.bt = tok, 0, bo_tinh

    def _xem(self):
        return self.tok[self.i] if self.i < len(self.tok) else None

    def _lay(self):
        t = self._xem()
        self.i += 1
        return t

    def bieu_thuc(self):
        v = self.hang()
        while (t := self._xem()) is not None and t.type == "OPERATOR-INFIX" and t.value in ("+", "-"):
            self._lay()
            r = self.hang()
            v = v + r if t.value == "+" else v - r
        return v

    def hang(self):
        v = self.nhan()
        while (t := self._xem()) is not None and t.type == "OPERATOR-INFIX" and t.value in ("*", "/"):
            self._lay()
            r = self.nhan()
            v = v * r if t.value == "*" else v / r
            if abs(v) > 1e15:
                raise _KhongHoTro()
        return v

    def nhan(self):
        t = self._lay()
        if t is None:
            raise _KhongHoTro()
        if t.type == "OPERATOR-PREFIX" and t.value in ("+", "-"):
            v = self.nhan()
            return -v if t.value == "-" else v
        if t.type == "OPERAND" and t.subtype == "NUMBER":
            v = float(t.value)
            if not math.isfinite(v) or abs(v) > 1e15:
                raise _KhongHoTro()
            return v
        if t.type == "OPERAND" and t.subtype == "RANGE":
            dai = t.value
            if "!" in dai:
                sh, dai = dai.rsplit("!", 1)
                if sh.strip("'") != self.bt.ws_ct.title:
                    raise _KhongHoTro()  # sheet khác: không tự tính xuyên sheet
            m = _O.match(dai)
            if not m:
                raise _KhongHoTro()
            x = self.bt.lay(m.group(2), int(m.group(4)))
            if x is None:
                return 0.0           # Excel: ô trống trong phép tính = 0
            if not _so(x):
                raise _KhongHoTro()  # chữ, lỗi, chưa tính được -> lan truyền CHUA
            return float(x)
        if t.type == "PAREN" and t.subtype == "OPEN":
            v = self.bieu_thuc()
            d = self._lay()
            if d is None or d.type != "PAREN":
                raise _KhongHoTro()
            return v
        if t.type == "FUNC" and t.subtype == "OPEN":
            ten = t.value.upper().rstrip("(")
            if ten == "SUM":
                return self._sum()
            if ten == "ROUND":
                x = self.bieu_thuc()
                self._can("SEP")
                n = self.bieu_thuc()
                self._can("FUNC")
                if abs(n) > 15:
                    raise _KhongHoTro()
                return float(round(x, int(n)))
            raise _KhongHoTro()
        raise _KhongHoTro()

    def _can(self, loai):
        t = self._lay()
        if t is None or t.type != loai:
            raise _KhongHoTro()

    def _sum(self):
        tong = 0.0
        while True:
            t = self._xem()
            if t is not None and t.type == "OPERAND" and t.subtype == "RANGE" and ":" in t.value:
                self._lay()
                dai = t.value
                if "!" in dai:
                    sh, dai = dai.rsplit("!", 1)
                    if sh.strip("'") != self.bt.ws_ct.title:
                        raise _KhongHoTro()
                tong += self.bt.tong_dai(dai)
            else:
                tong += self.bieu_thuc()
            t = self._lay()
            if t is None:
                raise _KhongHoTro()
            if t.type == "FUNC" and t.subtype == "CLOSE":
                return tong
            if t.type != "SEP":
                raise _KhongHoTro()


# ------------------------------------------------------------------ quét
def _o_co_that(ws, d1, d2):
    """{dong: [(cot, gia_tri)]} chỉ các ô có thật (không duyệt hình chữ nhật tới XFD).
    Ghép vào server.py: thay bằng _o_co_that() của server."""
    ra = {}
    for (r, c), o in getattr(ws, "_cells", {}).items():
        if d1 <= r <= d2 and o.value is not None:
            ra.setdefault(r, []).append((get_column_letter(c), o.value))
    return ra


def quet_loi_sheet(ws_ct, ws_gt=None, cot_map=None, dong_bat_dau=None, max_dong=3000, han_giay=40.0):
    """Quét một sheet. ws_ct: đọc công thức; ws_gt: cùng sheet đọc giá trị lưu sẵn (data_only), có thể None.

    cot_map: {loai: cột}. Có cot_map thì KHÔNG tự dò. Trả (loi, cot_map, pham_vi).
    pham_vi = dict(sheet, dau, cuoi, max_row, het_ngan_sach, tu_tinh).
    """
    if max_dong is None or max_dong <= 0:
        raise ValueError("max_dong phải > 0")
    if cot_map:
        dong_td = 0
    else:
        cot_map, dong_td = do_cot(ws_ct)
    C = cot_map.get
    dong_dau = dong_bat_dau or (dong_td + 1)
    dong_cuoi = min(ws_ct.max_row, dong_dau + max_dong - 1)
    bt = _BoTinh(ws_ct, ws_gt, han_giay=han_giay)
    loi = []
    pham_vi = dict(sheet=ws_ct.title, dau=dong_dau, cuoi=dong_cuoi, max_row=ws_ct.max_row,
                   het_ngan_sach=False, tu_tinh=0)

    def them(muc, loai, o, mo_ta, hien=None, de_xuat=None):
        loi.append(dict(muc=muc, loai=loai, o=f"{ws_ct.title}!{o}", mo_ta=mo_ta, hien=hien, de_xuat=de_xuat))

    cot_kq = [c for c in (C("kl_rieng"), C("kl_chung")) if c]
    if not cot_kq:
        them(MUC_CAO, "CAU_TRUC", "(sheet)",
             f"Không thấy cột khối lượng riêng/chung — CHƯA QUÉT được. Cột dò được: {cot_map or 'không'}. "
             "Truyền cot_map_json, hoặc đọc thô bằng read_sheet_data.")
        return loi, cot_map, pham_vi
    thieu = [k for k in ("dien_giai", "so_luong", "dai", "rong") if not C(k)]

    def ct(cot, d):
        v = ws_ct[f"{cot}{d}"].value if cot else None
        return v if isinstance(v, str) and v.startswith("=") else None

    cot_kt = {c for c in (C("dai"), C("rong"), C("cao"), C("dien_tich")) if c}
    o_that = _o_co_that(ws_ct, dong_dau, dong_cuoi)
    dau_muc = {d for d in range(dong_dau, dong_cuoi + 1)
               if C("tt") and ws_ct[f"{C('tt')}{d}"].value not in (None, "")}
    nhan, mau = {}, {c: {} for c in cot_kq}

    for d in range(dong_dau, dong_cuoi + 1):
        if time.monotonic() > bt.het_gio:
            bt.het_ngan_sach = True
            pham_vi["cuoi"] = d - 1
            break
        # THAM_CHIEU ở mọi ô có thật của dòng
        for cot, v in o_that.get(d, []):
            if isinstance(v, str) and "#REF!" in v:
                them(MUC_CAO, "THAM_CHIEU", f"{cot}{d}", "Ô có #REF! — tham chiếu bị xóa/dời.", v)
            elif isinstance(v, str) and v.startswith("=") and ("[" in v or "http" in v.lower()):
                them(MUC_TB, "THAM_CHIEU", f"{cot}{d}", "Công thức lấy số từ FILE NGOÀI — mất liên kết là sai số.", v)
            if ws_gt is not None:
                g = ws_gt[f"{cot}{d}"].value
                if isinstance(g, str) and g in ("#REF!", "#VALUE!", "#DIV/0!", "#NAME?", "#N/A", "#NUM!", "#NULL!"):
                    them(MUC_CAO, "THAM_CHIEU", f"{cot}{d}", f"Ô đang ra lỗi {g}.", g)

        dg = ws_ct[f"{C('dien_giai')}{d}"].value if C("dien_giai") else None
        dg_u = giai_ma_vni(dg) if isinstance(dg, str) else ""
        dg_k = bo_dau(dg_u)
        sl = bt.lay(C("so_luong"), d) if C("so_luong") else None
        f_dong = {c: ct(c, d) for c in cot_kq}
        v_dong = {c: bt.lay(c, d) for c in cot_kq}

        # kết quả CUỐI của dòng: KL chung nếu nó dẫn KL riêng cùng dòng, không thì cột đầu tiên có số
        kr, kc = C("kl_rieng"), C("kl_chung")
        if kc and kr and f_dong.get(kc) and kr in {
                co for s, co, dd in _tham_chieu(f_dong[kc]) if s in (None, ws_ct.title) and dd == d}:
            cuoi = kc
        else:
            cuoi = next((c for c in cot_kq if _so(v_dong[c])), None)

        for c in cot_kq:
            f, v = f_dong[c], v_dong[c]
            if not f:
                if _so(v) and v != 0:
                    them(MUC_THAP, "HANG_SO", f"{c}{d}", "Số gõ tay trong cột khối lượng — ghi nguồn (bảng/bản vẽ) vào cột ghi chú.", v)
                continue
            mau[c][d] = _mau_cong_thuc(f, d)
            tc = _tham_chieu(f)
            ref = [(co, dd) for s, co, dd in tc if s in (None, ws_ct.title)]
            ngoai = [x for x in tc if x[0] not in (None, ws_ct.title)]
            ref_dong = {co for co, dd in ref if dd == d}
            # 1. Hệ số số lượng bỏ sót: chỉ miễn khi một công thức khác trên dòng là TÍCH có cả cột này và cột số lượng
            if (_so(sl) and sl not in (0, 1) and C("so_luong") not in ref_dong and ref_dong & cot_kt
                    and all(dd == d for _, dd in ref) and not ngoai):
                da_nhan = any(f_dong.get(c2) and _la_tich(f_dong[c2], d, {c, C("so_luong")}, ws_ct.title)
                              for c2 in cot_kq if c2 != c)
                if not da_nhan:
                    them(MUC_CAO, "HE_SO_BO_SOT", f"{c}{d}",
                         f"Cột số lượng {C('so_luong')}{d}={sl:g} nhưng không công thức nào trên dòng nhân nó. "
                         f"Diễn giải: {dg_u.strip()[:70]}", v, v * sl if _so(v) else None)
            # 7. Công thức toàn hằng số
            if not ref and not ngoai and re.search(r"\d", f) and len(f) > 4:
                le3 = any(len(x) >= 3 for x in re.findall(r"\d+\.(\d+)", f))
                them(MUC_THAP, "HANG_SO", f"{c}{d}", "Công thức chỉ gồm hằng số — ghi nguồn ở cột ghi chú."
                     + (" Có số lẻ ≥3 chữ số, dễ chép tay sai." if le3 else ""), f)
            # 6. SUM dừng trước dòng con còn số liệu
            m = re.fullmatch(r"=SUM\(\$?([A-Z]{1,3})\$?(\d+):\$?([A-Z]{1,3})\$?(\d+)\)", f.replace(" ", ""), re.I)
            if m and int(m.group(2)) == d + 1:
                if m.group(1) != m.group(3):
                    them(MUC_THAP, "SUM_BO_SOT", f"{c}{d}", f"SUM trải 2 cột {m.group(1)}:{m.group(3)} — kiểm có cố ý không.", f)
                n = int(m.group(4)) + 1
                la_dau = n in dau_muc or any(ws_ct[f"{k}{n}"].value not in (None, "") for k in cot_kq if k != m.group(1))
                if ws_ct[f"{m.group(1)}{n}"].value not in (None, "") and not la_dau:
                    them(MUC_TB, "SUM_BO_SOT", f"{c}{d}",
                         f"SUM dừng ở dòng {m.group(4)} nhưng dòng {n} ngay dưới vẫn có số và không phải đầu mục mới.", f)

        # 2. Khoản trừ: xét kết quả CUỐI của dòng
        if cuoi and re.match(r"^[\s+\-–]*tru\b", dg_k) and _so(v_dong[cuoi]) and v_dong[cuoi] > 0:
            them(MUC_CAO, "DAU_KHOAN_TRU", f"{cuoi}{d}",
                 f"Diễn giải là khoản TRỪ nhưng kết quả cuối của dòng dương. Diễn giải: {dg_u.strip()[:70]}",
                 v_dong[cuoi], -v_dong[cuoi])
        # 3. Nhãn a x b
        if C("dai") and C("rong"):
            kt = _KT.findall(dg_u.replace(",", "."))
            e, fr = ws_ct[f"{C('dai')}{d}"].value, ws_ct[f"{C('rong')}{d}"].value
            if len(kt) == 1 and _so(e) and _so(fr):
                a, b = float(kt[0][0]), float(kt[0][1])
                nhan[d] = (sorted((round(a, 4), round(b, 4))) == sorted((round(float(e), 4), round(float(fr), 4))),
                           f"{a:g}x{b:g}", f"{float(e):g}x{float(fr):g}")
        # 4. "(84 hố)"
        m = _DEM.search(dg_k)
        if m and _so(sl) and int(m.group(1)) != sl:
            them(MUC_TB, "SO_LUONG_LECH", f"{C('so_luong')}{d}",
                 f"Diễn giải ghi {m.group(1)} {m.group(2)} nhưng cột số lượng = {sl:g}.", sl, int(m.group(1)))

    # 3b. Nhãn lệch — khối cắt tại đầu mục, chỉ báo khi đa số dòng trong khối khớp nhãn
    for khoi in _khoi_lien(sorted(nhan), cat=dau_muc):
        if len(khoi) < 3:
            continue
        khop = [d for d in khoi if nhan[d][0]]
        if len(khop) * 2 >= len(khoi):
            for d in khoi:
                if not nhan[d][0]:
                    them(MUC_CAO, "NHAN_LECH_KT", f"{C('dai')}{d}",
                         f"Diễn giải ghi {nhan[d][1]} nhưng dài×rộng nhập {nhan[d][2]} "
                         f"({len(khop)}/{len(khoi)} dòng cùng khối khớp nhãn).", nhan[d][2], nhan[d][1])

    # 5. Công thức lệch đa số trong khối
    for c, mm in mau.items():
        for khoi in _khoi_lien(sorted(mm), cat=dau_muc):
            if len(khoi) < 3:
                continue
            chinh, sl_chinh = Counter(mm[d] for d in khoi).most_common(1)[0]
            if sl_chinh * 2 <= len(khoi) or sl_chinh == len(khoi):
                continue
            for d in khoi:
                if mm[d] == chinh:
                    continue
                ly_do = []
                if mm[d].startswith("=-") != chinh.startswith("=-"):
                    ly_do.append("đổi dấu")
                thieu_c = [co for co in _cot_cung_dong(chinh) - _cot_cung_dong(mm[d])
                           if _so(bt.lay(co, d)) and bt.lay(co, d) != 1]
                if thieu_c:
                    ly_do.append("không nhân cột " + ",".join(sorted(thieu_c)) + " dù ô có số")
                if (_cot_cung_dong(chinh) == _cot_cung_dong(mm[d])
                        and _phep_toan(chinh).lstrip("=-") != _phep_toan(mm[d]).lstrip("=-")):
                    ly_do.append("khác phép toán")
                if ly_do:
                    txt = " + ".join(ly_do)
                    them(MUC_TB, "CONG_THUC_LECH", f"{c}{d}",
                         f"{txt[:1].upper()}{txt[1:]} so với {sl_chinh}/{len(khoi)} dòng cùng khối ({chinh}).",
                         ws_ct[f"{c}{d}"].value)

    pham_vi["het_ngan_sach"] = bt.het_ngan_sach
    pham_vi["tu_tinh"] = bt.tu_tinh
    if thieu:
        them(MUC_TB, "CAU_TRUC", "(sheet)",
             f"Thiếu cột {thieu} — các kiểu lỗi cần cột đó KHÔNG được xét. Cột dò được: {cot_map}.")
    if bt.het_ngan_sach:
        them(MUC_CAO, "CAU_TRUC", "(sheet)",
             f"Hết ngân sách tính/thời gian — quét tới dòng {pham_vi['cuoi']}; ô không tính được bị bỏ qua.")
    return _loc_trung(loi), cot_map, pham_vi


def _khoi_lien(dong_sx, khe=1, cat=()):
    """Gom dòng liền nhau (cho phép khe 1 dòng); cắt khối tại dòng đầu mục hoặc khi khe chứa đầu mục."""
    khoi, cu = [], None
    for d in dong_sx:
        if cu is not None and d - cu <= khe + 1 and d not in cat and not any(cu < x < d for x in cat):
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


def quet_sheet_la(wb, max_o=500_000):
    """Tên sheet lạ (NGHI dấu vết macro XLM) + sheet không thấy tham chiếu TRỰC TIẾP.

    'Không thấy tham chiếu' chưa xét named range, tham chiếu 3D, INDIRECT, macro — không kết luận sheet thừa.
    """
    loi, duoc_goi, dem = [], set(), 0
    for ws in wb.worksheets:
        for _, o in getattr(ws, "_cells", {}).items():
            dem += 1
            if dem > max_o:
                break
            v = o.value
            if isinstance(v, str) and v.startswith("=") and "!" in v:
                for s, _, _ in _tham_chieu(v):
                    if s and s != ws.title:
                        duoc_goi.add(s)
    for t in wb.sheetnames:
        if _SHEET_LA.match(t):
            loi.append(dict(muc=MUC_CAO, loai="SHEET_LA", o=t, hien=None, de_xuat=None,
                            mo_ta="Tên sheet giống dấu vết virus macro XLM cũ — NGHI VẤN. Mở file khi tắt macro, "
                                  "quét bằng phần mềm diệt virus; chỉ xóa ở BẢN SAO sau khi xác nhận."))
    return loi, sorted(set(wb.sheetnames) - duoc_goi)


def dinh_dang_ket_qua(loi, max_ket_qua=150, pham_vi=()):
    """Bảng gọn 'mức|loại|ô|hiện tại|đề xuất|mô tả' + phạm vi đã quét."""
    dem = Counter(x["muc"] for x in loi)
    dong = [f"Tổng {len(loi)} nghi vấn: CAO {dem.get(MUC_CAO, 0)} · TB {dem.get(MUC_TB, 0)} · THẤP {dem.get(MUC_THAP, 0)}"
            " — là NGHI VẤN để ưu tiên đối chiếu bản vẽ; không cờ ≠ đúng."]
    for p in pham_vi:
        chua = "" if p["cuoi"] >= p["max_row"] else \
            f" · CHƯA QUÉT dòng {p['cuoi'] + 1}–{p['max_row']} (gọi lại với dong_bat_dau={p['cuoi'] + 1})"
        dong.append(f"Phạm vi {p['sheet']}: dòng {p['dau']}–{p['cuoi']}/{p['max_row']}{chua}"
                    + (f" · {p['tu_tinh']} ô tự tính (không có số Excel lưu sẵn)" if p.get("tu_tinh") else ""))
    dong.append("muc|loai|o|hien|de_xuat|mo_ta")

    def g(v):
        return "" if v is None else (f"{v:.6g}" if _so(v) else str(v))

    for x in loi[:max_ket_qua]:
        dong.append("|".join([x["muc"], x["loai"], x["o"], g(x["hien"]), g(x["de_xuat"]), x["mo_ta"].replace("|", "/")]))
    if len(loi) > max_ket_qua:
        dong.append(f"Đã trả {max_ket_qua}/{len(loi)} dòng (mức CAO xếp trước). Tăng max_ket_qua hoặc lọc theo sheet.")
    return "\n".join(dong)
