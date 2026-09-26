# Nhờ Codex phản biện bản vá `kiem_kl` (bước `phan-bien` — trước khi ghép vào server.py)

Chỉ đọc code + test trong repo này. **Không** đưa hồ sơ thật lên đây. Ghi kết luận vào mục cuối file, push cùng nhánh.

## Cần soát (xếp theo rủi ro)
1. `kiem_kl/quet_loi.py` — `_BoTinh._tinh` dùng `eval` sau khi thay ô bằng số: đã chặn ký tự ngoài `[\d\s.eE+\-*/()]` và `__builtins__` rỗng. Còn đường nào lọt mã không?
2. `quet_loi_sheet` — tìm **báo nhầm** và **bỏ sót** cho 9 kiểu lỗi. Đặc biệt: HE_SO_BO_SOT (bỏ qua khi cột khác cùng dòng đã nhân số lượng, bỏ qua I=1), NHAN_LECH_KT (chỉ báo trong khối ≥3 dòng mà ≥50% khớp nhãn), CONG_THUC_LECH (khối cắt tại dòng có số TT).
3. `kiem_kl/vni.py` — bảng giải mã VNI-Windows: có ký tự/tổ hợp nào giải sai? Chuỗi Unicode thật có bị giải nhầm không?
4. `kiem_kl/cad.py` — `vung_hatch` dùng chẵn-lẻ (symmetric_difference) cho vòng lồng; `hatch_giao_doi_tuong` phân loại DA_KHOET bằng vùng bao ngoài. Ca nào phân loại sai (hatch nhiều đảo, block xoay, block có thuộc tính chữ làm phình bbox)?
5. `tich_hop/them_vao_server.py` — đúng chuẩn G1–G6 của my-office-mcp chưa (nhãn CHI_DOC, đường lui, trần kết quả, thông báo lỗi)?

## Kết quả đo phía Claude
- `pytest tests -q`: 26/26 PASS (dữ liệu tự dựng, có ca đối chứng không-được-báo).
- Chạy trên đoạn KLCT thật (không commit): bắt đủ 10/10 lỗi đã chốt ở mức CAO, 2 dòng phụ (1 TB trùng J84, 1 THẤP hằng số K38).

## Kết luận của Codex
_(Codex ghi: đồng ý / bất đồng từng mục + đề xuất sửa cụ thể)_
