---
name: kiem-tra-khoi-luong
description: "Vai CHUYÊN VIÊN KIỂM KHỐI LƯỢNG — rà soát bảng khối lượng thiết kế/dự toán (KLCT, THKL, KLDD, bảng diễn giải) đối chiếu bản vẽ PDF và CAD, sửa trên BẢN SAO có ghi chú diễn giải. LUÔN dùng khi: 'kiểm tra khối lượng', 'soát KLCT', 'đối chiếu khối lượng với bản vẽ', 'tính lại khối lượng hố ga/bồn cây/bó vỉa/vỉa hè', 'file khối lượng có sai không', 'bóc lại khối lượng từ CAD', hoặc nhận hồ sơ thiết kế (XLS + PDF + DWG) cần rà trước khi trình/thanh toán."
---

# Kiểm tra khối lượng — quy trình nhanh, ít token

Rút từ đợt kiểm thật 25/09/2026 (đường đô thị, 154 trang PDF scan, 6 DWG, KLCT 1.400 dòng):
kiểm thủ công mất ~4 giờ; AI mất ~2 giờ, trong đó **45 phút chết vì chuyển tiếp giữa 2 AI** và
~30 phút viết công cụ tại chỗ. Skill này gói lại để lần sau còn **30–60 phút**.

## 0. Phiếu giao việc — hỏi MỘT lần duy nhất ở đầu, sau đó không hỏi kỹ thuật nữa

Sếp không đọc bản vẽ. Hỏi điểm kỹ thuật giữa chừng = treo việc. Đầu phiên lấy đủ 5 dòng
(thiếu dòng nào thì dùng mặc định in đậm, ghi rõ là đã dùng mặc định):

```
1. Thư mục hồ sơ:        <đường dẫn>  (XLS khối lượng · PDF bản vẽ · DWG/DXF)
2. Phạm vi:              **toàn bộ sheet có cột khối lượng**
3. Quyền:                **toàn quyền soát + sửa trên BẢN SAO trong _sandbox, ghi chú cột Ghi chú,
                          KHÔNG động file gốc, KHÔNG vá server/skill khi chưa duyệt**
4. Tiêu chí lệch:        **giữ số chưa làm tròn; lệch theo độ chính xác nguồn, không tự đặt ngưỡng**
5. Đầu ra:               **bản sao _DA-SUA_<ngày>.xls + nhật ký ô cũ→mới + báo cáo 1 trang**
```

Trong phạm vi quyền đó: **tự quyết theo bản vẽ**. Chỉ dừng hỏi khi cần căn cứ NGOÀI bản vẽ
(phụ lục hợp đồng, biên bản hiện trường, chỉ đạo CĐT) — gom hết vào mục "còn treo" cuối báo cáo.

## 1. Quy trình 6 bước (theo thứ tự, đừng nhảy)

| Bước | Việc | Tool | Ra gì |
|---|---|---|---|
| 1 | Sao bản sao vào `_sandbox\<ma-du-an>\`, so SHA256 với nguồn | tool chép file + băm | nhật ký nguồn |
| 2 | **Máy quét công thức trước** | `excel_quet_loi_khoi_luong` | danh sách nghi vấn CAO/TB/THẤP |
| 3 | Đọc bản vẽ **chỉ cho dòng bị gắn cờ** + trang mặt cắt điển hình | đọc PDF / ảnh trang | kích thước, số lượng, ghi chú |
| 4 | Đếm & đo trên CAD | `cad_dem_doi_tuong`, `cad_hatch_giao_doi_tuong` | số lượng theo hình học, danh sách trừ/không trừ |
| 5 | Sửa BẢN SAO: tô vàng ô sửa, cột Ghi chú = lý do + căn cứ (tờ/trang) + giá trị cũ; nhật ký `SUA_KL_<ngày>.txt`; tính lại, soát THKL = KLCT, 0 ô #REF! | tool ghi COM (`excel_ghi_nhieu_o`) | bản sao đã sửa |
| 6 | Báo cáo 1 trang: bảng số chính cũ→mới, còn treo, việc sếp làm | — | báo cáo |

Bước 2 là cái rẻ nhất và bắt nhiều nhất: đợt 25/09 nó bắt **10/10 lỗi công thức đã chốt** chỉ
trong vài giây. Đừng đọc tràn 154 trang PDF trước khi có danh sách cờ.

## 2. Mười bẫy đã gặp thật — soát đủ

| # | Bẫy | Dấu hiệu | Cách bắt |
|---|---|---|---|
| 1 | **Quên nhân số lượng** | cột G/NHAU = 84 mà công thức `=-E*F` | quét HE_SO_BO_SOT |
| 2 | **Khoản trừ ra dương** | "Trừ bồn cây" = +468 | quét DAU_KHOAN_TRU |
| 3 | **Nhãn lệch kích thước** | ghi "1.2x3.5", nhập 1.5/2.4 (chép dòng trên) | quét NHAN_LECH_KT; đối chiếu chu vi/cốt thép cùng loại hố ở các dòng khác |
| 4 | **Nhãn loại đối tượng sai** | "hố 1.2x2.6" thực tế là 1.2x1.6 (bản vẽ điển hình) → kéo sai đục hố, BT, ván khuôn | đọc bản vẽ điển hình từng loại hố; sửa CẢ chuỗi dòng dùng kích thước đó |
| 5 | **Sót đối tượng ngoài tuyến chính** | 6 hố đường nhánh không vào bảng | `cad_dem_doi_tuong` so số lượng với bảng; lập danh mục theo MÃ (HG90–95) |
| 6 | **Trừ lặp với hatch** | vùng lát đã khoét bồn cây, bảng trừ thêm đủ số bồn | `cad_hatch_giao_doi_tuong`: chỉ trừ TRONG_VUNG, bỏ DA_KHOET/NGOAI_VUNG |
| 7 | **Trừ đối tượng nằm ngoài vùng lát** | trừ 84 hố ga nhưng chỉ 31 hố nằm trong vùng lát | như #6 |
| 8 | **Gõ nhầm số trong bảng thống kê** | Slg7 = 689, nhãn bản vẽ = 698 | so từng nhãn Slg với diện tích hatch cùng vùng (lệch >1 m² thì xem) |
| 9 | **Số nhập tay không nguồn / liên kết file ngoài / #REF!** | `=180.434+23.56`, `'[file cũ.xls]'!K67` | quét HANG_SO, THAM_CHIEU; THKL #REF! thì lập lại THKL theo KLCT |
| 10 | **Sheet rác / virus macro** | sheet `xxxxxxxx`, `HelpMe`, sheet chép từ dự án khác (tên đường khác) | quét SHEET_LA; mở file khi TẮT macro; xóa ở bản sao trước khi trình |

Hai nghi vấn đợt 25/09 bị **bản vẽ bác bỏ** (đai Ø6 đúng nhưng nhãn ghi Þ8; suất bó vỉa đúng BV
dù khác sheet BOVIA cũ): **nghi vấn từ công thức chưa phải lỗi** — không sửa khi chưa có căn cứ.

## 3. Luật trung thực (vi phạm đợt 25/09, không được lặp)

- **Không bao giờ ghi "sếp đã chốt/duyệt"** nếu sếp không trực tiếp nói trong phiên. Quyết định
  theo quyền giao ghi: *"chốt theo bản vẽ <tờ/trang> – <tên AI>, <ngày>"*.
- Kết luận nào sai ở lượt trước thì đính chính công khai trong báo cáo ("B4 sai, lượt 3 sửa").
- Chưa chạy thật thì không nói "đã xong". Bị chặn quyền ghi thì báo bị chặn, **không mở phiên
  khác để ghi thay**.
- Không đưa hồ sơ thật (XLS/PDF/DWG, số liệu dự án) lên GitHub hay bất kỳ chỗ công khai nào.

## 4. Hai AI phối hợp (khi có Codex) — vai rõ, không chat qua lại liên tục

Chuyển tiếp thời gian thực giữa 2 AI (gõ qua trình duyệt, dán 60 KB văn bản) là chỗ chậm nhất.
Cách đúng:

| Vai | Làm gì | Khi nào |
|---|---|---|
| **Claude Code chạy trên máy** (chính) | Bước 1–6 trọn vẹn, file trong tầm tay | luôn |
| **Codex** (phản biện độc lập) | Đọc `KET_QUA_*.md` + nhật ký sửa, soát chéo 3–5 điểm rủi ro nhất trên bản vẽ; không sửa file | sau Bước 5, trước khi sếp duyệt |
| Claude cloud | Chỉ khi không có máy: viết/sửa công cụ, test dữ liệu tự dựng | không làm nghiệp vụ hồ sơ |

Bàn giao bằng FILE (`BAN_GIAO.md` trong `_sandbox\<ma-du-an>\`), không bằng tin nhắn. Bên nào hết
token thì bên kia đọc file làm tiếp.

## 5. Ca kiểm chứng (hồi quy) cho tool

Bản sao đợt 25/09 trong `_sandbox\kiem-kl-ntt\`: `excel_quet_loi_khoi_luong` trên file GỐC phải
gắn cờ CAO đủ: J76, J77, J80, J81, J82 (hệ số), J84 (dấu), E70, E83 (nhãn), J251, J252 (cừ tràm).
Thiếu ô nào là tool thụt lùi.
