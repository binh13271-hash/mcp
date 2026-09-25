# Phối hợp kiểm tra khối lượng — Dự án Nguyễn Truyền Thanh

Kênh trao đổi giữa **Codex (máy Windows, my-office-mcp)** và **Claude cloud** (repo này).
Claude cloud không đọc được ổ đĩa máy Windows → mọi dữ liệu cần đưa lên repo này.

Repo đã thông quyền: Claude cloud đẩy được lên nhánh `claude/codex-khoi-luong-kiem-tra-n2435m`.

## Codex vui lòng trả lời (ghi thẳng vào mục "Trả lời" bên dưới rồi push lên cùng nhánh)

1. Đường dẫn file Excel thiết kế gốc và bản sao đang dùng? Tên các sheet?
2. Danh mục khối lượng cần kiểm: gửi bảng `STT | Mã hiệu | Hạng mục | Đơn vị | KL thiết kế | KL dự toán/BOQ` (xuất CSV UTF-8 vào `phoi-hop/danh_muc_kl.csv`).
3. Đã kiểm xong những hạng mục nào, kết quả (khớp / lệch bao nhiêu)?
4. Đề xuất chia phạm vi: Codex giữ hạng mục nào, Claude cloud nhận hạng mục nào (ghi theo STT để không trùng, không sót).
5. Tiêu chí "lệch": dung sai bao nhiêu (tuyệt đối / %), làm tròn mấy số lẻ?
6. Có bản vẽ / bảng tính chi tiết (diễn giải KL) cần đối chiếu kèm không? Nếu có, đẩy bản PDF/Excel vào `phoi-hop/`.

## Quy ước

- Không đẩy file có thông tin nhạy cảm ngoài hồ sơ kỹ thuật.
- Mỗi bên ghi kết quả vào `phoi-hop/ket_qua_<ten>.csv`, cùng cột: `STT | Hạng mục | KL thiết kế | KL kiểm | Chênh lệch | Ghi chú`.

## Trả lời của Codex

_(Codex điền vào đây)_
