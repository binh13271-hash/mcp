"""Giải mã chữ gõ bằng font VNI-Windows (vd 'Tröø caùc hoá ga') sang Unicode ('Trừ các hố ga').

Hồ sơ khối lượng đời cũ hay gõ diễn giải bằng font VNI: đọc ra Python là chuỗi Latin-1 lạ,
nên mọi phép dò từ khóa ('trừ', 'hố', 'cái') đều trượt.

Xét TỪNG TỪ, không xét cả ô (ô có thể lẫn VNI và Unicode: 'Tröø hố ga'):
  - từ có chữ Việt Unicode dựng sẵn (ố, ư, đ...)          -> giữ nguyên
  - từ có dấu hiệu CHẮC CHẮN là VNI (ñ, ö, ø, û, ï, aâ...)  -> giải mã
  - từ MƠ HỒ (vd 'hoá': Unicode 'hoá' hay VNI 'hố'?)       -> chỉ giải mã khi cùng ô có từ chắc
    chắn VNI và KHÔNG có từ chắc chắn Unicode; không thì giữ nguyên (không đoán)
  - từ còn lại ('bê', 'tông', 'Müller')                      -> giữ nguyên
che_do='vni' / 'unicode' để ép khi đã biết font của cột (bằng chứng mạnh hơn mọi phép đoán).
"""
import re
import unicodedata

_SAC, _HUYEN, _HOI, _NGA, _NANG = "́", "̀", "̉", "̃", "̣"
_MU, _TRANG = "̂", "̆"  # â ê ô  /  ă

# Ký tự "dấu" VNI đứng SAU nguyên âm gốc
_DAU_SAU = {
    "ù": _SAC, "ø": _HUYEN, "û": _HOI, "õ": _NGA, "ï": _NANG,
    "â": _MU, "á": _MU + _SAC, "à": _MU + _HUYEN, "å": _MU + _HOI, "ã": _MU + _NGA, "ä": _MU + _NANG,
}
_DAU_SAU.update({k.upper(): v for k, v in list(_DAU_SAU.items())})
_DAU_TRANG = {  # ă: chỉ đi sau a/A
    "ê": _TRANG, "é": _TRANG + _SAC, "è": _TRANG + _HUYEN, "ú": _TRANG + _HOI,
    "ü": _TRANG + _NGA, "ë": _TRANG + _NANG,
}
_DAU_TRANG.update({k.upper(): v for k, v in list(_DAU_TRANG.items())})
_CHU_RIENG = {
    "ô": "ơ", "Ô": "Ơ", "ö": "ư", "Ö": "Ư", "ñ": "đ", "Ñ": "Đ",
    "í": "í", "ì": "ì", "æ": "ỉ", "ó": "ĩ", "ò": "ị",
    "Í": "Í", "Ì": "Ì", "Æ": "Ỉ", "Ó": "Ĩ", "Ò": "Ị",
}
_NGUYEN_AM = set("aeouyAEOUYơƠưƯ")
_NA = "aeouyAEOUY"
# Chắc chắn VNI: ký tự không có trong chữ Việt Unicode, hoặc cặp chỉ VNI mới có
_CHAC_VNI = re.compile(r"[ñÑöÖøØûÛïÏæÆåÅäÄëËüÜ]|[" + _NA + r"][âÂùÙ]|[aA][êÊéÉèÈ]")
# Mơ hồ: nguyên âm + ký tự vừa là chữ Unicode vừa là dấu VNI (oá = hoá/hố, oà...)
_MO_HO = re.compile(r"[" + _NA + r"][áÁàÀãÃõÕúÚ]")


def _co_unicode_viet(tu):
    return any(0x1EA0 <= ord(ch) <= 0x1EF9 or ch in "ăĂđĐơƠưƯ" for ch in tu)


def trong_nhu_vni(chuoi: str) -> bool:
    """True khi chuỗi có ít nhất một từ chắc chắn gõ VNI."""
    return bool(chuoi) and any(not _co_unicode_viet(t) and _CHAC_VNI.search(t) for t in chuoi.split())


def _giai_tu(tu):
    ra = []
    for ch in tu:
        truoc = ra[-1][-1:] if ra else ""
        goc = unicodedata.normalize("NFD", truoc)[:1] if truoc else ""
        if goc in ("a", "A") and ch in _DAU_TRANG:
            ra[-1] += _DAU_TRANG[ch]
        elif goc in _NGUYEN_AM and ch in _DAU_SAU:
            ra[-1] += _DAU_SAU[ch]
        elif ch in _CHU_RIENG:
            ra.append(_CHU_RIENG[ch])
        else:
            ra.append(ch)
    return unicodedata.normalize("NFC", "".join(ra))


def giai_ma_vni(chuoi, che_do="tu_dong"):
    """Trả chuỗi Unicode (NFC). che_do: 'tu_dong' | 'vni' | 'unicode'."""
    if not isinstance(chuoi, str) or not chuoi or che_do == "unicode":
        return chuoi
    phan = re.split(r"(\s+)", chuoi)
    tu = [p for p in phan if p and not p.isspace()]
    if che_do == "vni":
        giai = {t for t in tu if not _co_unicode_viet(t)}
    else:
        chac_vni = {t for t in tu if not _co_unicode_viet(t) and _CHAC_VNI.search(t)}
        co_unicode = any(_co_unicode_viet(t) for t in tu)
        giai = set(chac_vni)
        if chac_vni and not co_unicode:
            giai |= {t for t in tu if not _co_unicode_viet(t) and _MO_HO.search(t)}
    if not giai:
        return chuoi
    return "".join(_giai_tu(p) if p in giai else p for p in phan)


def bo_dau(chuoi: str, che_do="tu_dong") -> str:
    """Bỏ dấu tiếng Việt + chữ thường, để dò từ khóa ('trừ' -> 'tru')."""
    s = unicodedata.normalize("NFD", giai_ma_vni(chuoi or "", che_do))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D").lower()
