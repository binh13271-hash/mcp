# kiem_kl — công cụ kiểm khối lượng (chỉ đọc)

| Module | Hàm | Việc |
|---|---|---|
| `quet_loi.py` | `quet_loi_sheet`, `quet_sheet_la`, `dinh_dang_ket_qua` | Quét 9 kiểu lỗi công thức bảng khối lượng Excel |
| `cad.py` | `dem_doi_tuong`, `hatch_giao_doi_tuong` | Đếm đối tượng DXF; đo đối tượng nằm trong vùng hatch (chống trừ lặp) |
| `vni.py` | `giai_ma_vni`, `bo_dau` | Đọc diễn giải gõ font VNI-Windows |

Ghép vào my-office-mcp: xem `tich_hop/them_vao_server.py`. Quy trình nghiệp vụ: `skills/kiem-tra-khoi-luong/SKILL.md`.

```bash
pip install openpyxl ezdxf shapely pytest
python -m pytest tests -q
```
