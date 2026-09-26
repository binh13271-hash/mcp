"""Giải mã chữ gõ bằng font VNI-Windows (vd 'Tröø caùc hoá ga') sang Unicode ('Trừ các hố ga').

Hồ sơ khối lượng đời cũ hay gõ diễn giải bằng font VNI: đọc ra Python là chuỗi Latin-1 lạ,
nên mọi phép dò từ khóa ('trừ', 'hố', 'cái') đều trượt. Hàm ở đây chỉ giải mã khi chuỗi
TRÔNG NHƯ VNI; chuỗi Unicode thật được trả nguyên.
"""
import re
import unicodedata

# Dấu kết hợp Unicode
_SAC, _HUYEN, _HOI, _NGA, _NANG = "́", "̀", "̉", "̃", "̣"
_MU, _TRANG = "̂", "̆"  # â ê ô  /  ă

# Ký tự "dấu" của VNI đứng SAU nguyên âm gốc (a, e, o, u, y và chữ hoa)
_DAU_SAU = {
    "ù": _SAC, "ø": _HUYEN, "û": _HOI, "õ": _NGA, "ï": _NANG,
    "â": _MU, "á": _MU + _SAC, "à": _MU + _HUYEN, "å": _MU + _HOI, "ã": _MU + _NGA, "ä": _MU + _NANG,
}
_DAU_SAU.update({k.upper(): v for k, v in list(_DAU_SAU.items())})
# Dấu trăng (ă) chỉ đi sau a/A
_DAU_TRANG = {
    "ê": _TRANG, "é": _TRANG + _SAC, "è": _TRANG + _HUYEN, "ú": _TRANG + _HOI,
    "ü": _TRANG + _NGA, "ë": _TRANG + _NANG,
}
_DAU_TRANG.update({k.upper(): v for k, v in list(_DAU_TRANG.items())})
# Chữ đứng riêng
_CHU_RIENG = {
    "ô": "ơ", "Ô": "Ơ", "ö": "ư", "Ö": "Ư", "ñ": "đ", "Ñ": "Đ",
    "í": "í", "ì": "ì", "æ": "ỉ", "ó": "ĩ", "ò": "ị",
    "Í": "Í", "Ì": "Ì", "Æ": "Ỉ", "Ó": "Ĩ", "Ò": "Ị",
}
_NGUYEN_AM = set("aeouyAEOUYơƠưƯ")
_DAU_HIEU_VNI = set("ñÑöÖøØûÛïÏæÆåÅäÄëËüÜ")  # không có trong chữ Việt Unicode
# Cặp chỉ gặp ở VNI: nguyên âm + â (oâ = ô), a + ê (aê = ă), nguyên âm + ù (aù = á)
_CAP_VNI = re.compile(r"[aeouyAEOUY][âÂ]|[aA][êÊéÉèÈ]|[aeouyAEOUY][ùÙ]")


def trong_nhu_vni(chuoi: str) -> bool:
    """True khi chuỗi có dấu hiệu gõ VNI và KHÔNG chứa chữ Việt Unicode dựng sẵn."""
    if not chuoi:
        return False
    for ch in chuoi:
        o = ord(ch)
        if 0x1EA0 <= o <= 0x1EF9 or ch in "ăĂđĐơƠưƯ":
            return False
    return any(ch in _DAU_HIEU_VNI for ch in chuoi) or bool(_CAP_VNI.search(chuoi))


def giai_ma_vni(chuoi):
    """Trả chuỗi Unicode dựng sẵn (NFC). Không phải VNI thì trả nguyên."""
    if not isinstance(chuoi, str) or not trong_nhu_vni(chuoi):
        return chuoi
    ra = []
    for ch in chuoi:
        truoc = ra[-1][-1:] if ra else ""
        goc_truoc = unicodedata.normalize("NFD", truoc)[:1] if truoc else ""
        if goc_truoc in ("a", "A") and ch in _DAU_TRANG:
            ra[-1] += _DAU_TRANG[ch]
        elif goc_truoc in _NGUYEN_AM and ch in _DAU_SAU:
            ra[-1] += _DAU_SAU[ch]
        elif ch in _CHU_RIENG:
            ra.append(_CHU_RIENG[ch])
        else:
            ra.append(ch)
    return unicodedata.normalize("NFC", "".join(ra))


def bo_dau(chuoi: str) -> str:
    """Bỏ dấu tiếng Việt + chữ thường, để dò từ khóa ('trừ' -> 'tru')."""
    s = unicodedata.normalize("NFD", giai_ma_vni(chuoi or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()
