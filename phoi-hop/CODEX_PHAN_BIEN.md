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

## PHẢN HỒI — Codex — 2026-09-26 07:20 (+07:00)

**Kết luận: CAN_BO_SUNG — chưa đồng ý ghép bản này vào `server.py`.** Hướng làm bộ dò nghi vấn chỉ đọc là phù hợp, nhưng còn lỗi tính số, bỏ sót/báo nhầm và lỗi tích hợp có thể làm kết quả kiểm khối lượng sai âm thầm.

Đầu vào: nhánh `claude/codex-khoi-luong-kiem-tra-n2435m`, commit `0cdd820`, repo `binh13271-hash/mcp`; code, test và skill trong repo. Đối chiếu riêng chữ ký/hạ tầng với `server.py` v7.2.1 và `NGUYEN_TAC.md` trên máy; không chép các file đó vào repo này.

Đầu ra: chỉ nối phản biện vào file này; không sửa code/test/skill, không ghép vào MCP đang chạy. Tiêu chí hoàn tất phản biện: kiểm 5 mục được giao, chạy test hiện hữu và ca phản ví dụ tự dựng, nêu điều kiện sửa–kiểm rõ ràng.

### 1. Bằng chứng và giới hạn

- Chạy lại `python -m pytest tests -q` trên Python 3.14.6: **26 passed in 0.93s**.
- Chạy thêm các ca nhỏ bằng Python trên workbook trong bộ nhớ và DXF trong thư mục tạm; kết quả thực đo ghi bên dưới. Không thêm chúng vào bộ test của tác giả trong lượt phản biện này.
- Không chạy hồ sơ thật; kết quả **10/10 lỗi thật** phía Claude chưa được Codex xác minh độc lập. 26 test xanh chưa chứng minh đủ các biến thể Excel/CAD.
- Các dòng mã dẫn dưới đây thuộc commit `0cdd820`. P1 = chặn ghép, có thể tính sai hoặc làm server không nạp; P2 = phải bổ sung độ phủ/chẩn đoán trước nghiệm thu.

### 2. Đồng ý / bất đồng theo 5 mục được giao

| Mục | Kết luận | Căn cứ |
|---|---|---|
| 1. `eval` | Chưa thấy đường thực thi mã tùy ý qua whitelist hiện tại; **không đồng ý coi là đã an toàn** | Còn `**`, `//`, tính số sai và không có ngân sách tính toán/range; xem R1–R2 |
| 2. 9 kiểu nghi vấn | Đồng ý là gợi ý kiểm tra; **chưa đạt độ tin cậy để hướng dẫn sửa** | Bỏ sót hệ số, báo nhầm dấu/nhãn, lỗi ngoài cột kết quả không được quét, phạm vi cắt im lặng; R3–R4, R9 |
| 3. VNI | Một số chuỗi VNI đồng nhất giải đúng (test hiện hữu); **không giữ nguyên mọi Unicode thật** | Chuỗi hỗn hợp bị bỏ qua hoặc làm hỏng chữ Unicode; R5 |
| 4. Hatch/hình học | Chẵn–lẻ phù hợp cho vòng lồng hợp lệ theo kiểu normal; **chưa đồng ý phân loại/diện tích tổng quát** | Sai đơn vị, mất vỏ đảo nhỏ, bbox block xoay, lỗ khoét một phần; R6–R8 |
| 5. Ghép server | **Chưa đạt G1–G6** | `CHI_DOC` không tồn tại trong server đích; còn dò cột song song, thiếu hydration CAD/ngân sách/đóng workbook; R9–R10 |

### 3. Phát hiện và yêu cầu sửa

**R1 — P1 — Bộ tính trả số sai thay vì trạng thái chưa tính được.**

Vị trí: `kiem_kl/quet_loi.py:130–168`, nhất là thay ô tại dòng 159–163 và cộng SUM tại 147–157.

| Ca tự dựng | Thực tế | Kết quả đúng / yêu cầu |
|---|---|---|
| Sheet trống, `_BoTinh(ws)._tinh('=1E3+2', 0)` | `12` | `1002`; regex nhận nhầm `E3` trong số khoa học thành địa chỉ ô rồi thay bằng 0 |
| A1=`=ROUND(2.4,0)`, A2=`=A1+5`, không có cache | A1=`None`, A2=`5` | A2 đúng là 7; nếu không hỗ trợ ROUND thì phải trả chưa tính được, không biến A1 thành ô trống |
| Thêm A3=`=SUM(A1:A2)` | `5.0` | Đúng là 9; không được bỏ qua công thức chưa tính được như bỏ qua chữ/ô trống |

Sửa: dùng token công thức để phân biệt NUMBER/RANGE; tách ô trống, lỗi Excel, vòng tham chiếu và công thức chưa hỗ trợ thành trạng thái khác nhau. Lan truyền trạng thái không xác định, không sinh đề xuất số khi nguồn chưa xác định. Cache Excel chỉ là giá trị lưu sẵn, cần ghi xuất xứ/giới hạn độ mới, không coi là bằng chứng vừa tính lại.

**R2 — P1 — Whitelist ký tự chưa giới hạn phép toán và chi phí.**

Vị trí: `quet_loi.py:147–167`. Thực đo `=9**9` trả `387420489`; `=5//2` trả `2`. Đây không phải cú pháp số học Excel đã cam kết. Có thể tăng số mũ/độ dài biểu thức gây tiêu tốn CPU/RAM. `SUM(A1:XFD1048576)` còn bị bung ô trước khi tới whitelist; `max_dong` của vòng quét không chặn việc này. Không chạy payload lớn để tránh treo máy.

Sửa: parser/AST có whitelist node/toán tử, chỉ cho cú pháp đã hỗ trợ; chặn số không hữu hạn, giới hạn độ dài/độ sâu/độ lớn toán hạng, tổng số ô tham chiếu và thời gian. Chặn ngay trước khi duyệt range. `__builtins__={}` hữu ích nhưng không giải quyết cạn tài nguyên; không khẳng định có lỗ RCE khi chưa có bằng chứng.

**R3 — P1 — Chỉ thấy tham chiếu số lượng đã miễn cảnh báo, chưa chứng minh có nhân đúng.**

Vị trí: `quet_loi.py:216–224`. E10=2, F10=3, I10=10, J10=`=E10*F10`; lần lượt K10=`=I10+J10` hoặc `=I10*100`: cả hai ca trả **không nghi vấn**. Cột K chỉ nhắc I đã che mất lỗi hệ số của J, dù không nhân J với I. Ca đối chứng K=`I*J` là hợp lệ, nhưng không đủ để chứng minh điều kiện hiện tại đúng.

Sửa: chỉ miễn khi chứng minh quan hệ phụ thuộc và phép nhân số lượng đúng trong đường tính kết quả; nếu không phân tích được thì ghi nghi vấn/chưa xác định. Phải phân biệt khối lượng một đối tượng và khối lượng tổng, không yêu cầu mọi ô đều nhân I.

**R4 — P2 — Báo nhầm dấu/nhãn và bỏ sót biến thể công thức.**

| Vị trí | Ca tự dựng / kết quả | Sửa cụ thể |
|---|---|---|
| `quet_loi.py:225–229` | C10=`Trừ hố`, E=2, F=3, I=2, J=`=E10*F10*I10`, K=`=-J10`: báo CAO ở J và đề xuất -12, dù kết quả K đã âm đúng | Theo đường phụ thuộc tới kết quả cuối; giữ J dương khi K chịu trách nhiệm đổi dấu |
| `quet_loi.py:264` | Đầu mục B10=1/B13=2; dòng 11,12 nhãn 1x2 khớp; dòng 14 nhãn 1x2 nhưng kích thước 3x2: vẫn báo E14 dựa vào 2 dòng thuộc đầu mục trước | Cắt khối NHAN_LECH_KT theo ranh giới đầu mục; `_khoi_lien` hiện cho qua một dòng trống/đầu mục |
| `quet_loi.py:284–303` | J11,J12=`E*F*I`, J13=`E*F/I`, các E/F/I=2/3/4: không báo CONG_THUC_LECH | Bổ sung khác toán tử, không chỉ khác dấu đầu hoặc thiếu tên cột; vẫn trả nghi vấn cần kiểm |
| `quet_loi.py:107–121` | `=E11*$I$1` và `=E12*$I$1` thành `=E[0]*I[-10]` và `=E[0]*I[-11]` | Giữ nguyên tính tuyệt đối `$I$1` khi chuẩn hóa; nếu không, công thức sao chép đúng mất dạng đa số |

Độ phủ 9 kiểu: HE_SO_BO_SOT/DAU_KHOAN_TRU/NHAN_LECH_KT/CONG_THUC_LECH có vấn đề trên. SO_LUONG_LECH mới hỗ trợ mẫu đếm đóng trong ngoặc và danh sách đơn vị hữu hạn. SUM_BO_SOT mới xét tổng ở trước chi tiết, bắt đầu đúng dòng kế tiếp và chỉ nhìn một dòng sau phạm vi. THAM_CHIEU chỉ kiểm các cột KL riêng/chung; #REF! ở cột kích thước có thể không được báo tại ô nguồn. HANG_SO không bắt số nhập tay thuần vì `if not f: continue`. SHEET_LA chỉ là heuristic theo tên, không chứng minh có virus; danh sách không được tham chiếu cũng không chứng minh sheet thừa (chưa xét đầy đủ named range, 3D reference, INDIRECT, macro). Cần mô tả rõ phạm vi hỗ trợ và đánh dấu chưa kiểm, tránh hiểu “không cờ” thành “đúng”.

**R5 — P1 — Nhận diện VNI ở cấp cả chuỗi gây bỏ sót và hỏng Unicode.**

Vị trí: `kiem_kl/vni.py:38–65`. Thực đo:

- `Tröø hố ga` → giữ nguyên, không nhận ra “trừ” vì `ố` khiến cả chuỗi bị coi là Unicode.
- `Ñoå bê tông` → `Đổ bê tơng`: phần Unicode đúng bị đổi sai.
- `Müller bê tông` → `Müller bê tơng`: chuỗi Unicode thật có tên nước ngoài cũng bị đổi sai.
- `boàn` → giữ nguyên, dù VNI có thể biểu diễn “bồn”; `hoá` → giữ nguyên, vừa có thể là Unicode “hoá” vừa có thể là VNI “hố”. Đây là mơ hồ thực sự, không được khắc phục bằng cách luôn giải mã.

Sửa: có chế độ mã hóa rõ ràng, ưu tiên bằng chứng font/run/ô nguồn; hỗ trợ đoạn hỗn hợp khi có căn cứ. Chế độ tự động phải giữ nguyên hoặc báo mơ hồ nếu không phân biệt chắc, không âm thầm sửa Unicode. Bổ sung các ca trên và bảng kiểm ký tự hoa/thường/dấu; chưa tuyên bố bảng mã đã đủ chỉ từ 7 câu mẫu.

**R6 — P1 — DXF dùng mm nhưng trả m² không chuyển đổi.**

Vị trí: `kiem_kl/cad.py:216`, cùng các giá trị diện tích/chiều dài xuất ra. DXF `$INSUNITS=4`, hatch 1000×1000: trả `1000000.00 m²`, đúng phải là **1 m²**. Tỉ lệ giao vẫn không đổi nhưng diện tích báo sai một triệu lần.

Sửa: quy đổi chiều dài theo hệ số đơn vị, diện tích theo bình phương hệ số; hoặc ghi rõ đơn vị bản vẽ và không gắn m². `$INSUNITS=0`/nguồn đơn vị không chắc phải báo chưa xác định, cho người dùng cung cấp đơn vị. Thêm ca mét, mm và unitless.

**R7 — P1 — Phân loại DA_KHOET không chứng minh đối tượng đã bị trừ đủ.**

Vị trí: `cad.py:189, 195–213`.

- Hatch ngoài 10×10; lỗ (1,1)–(1.6,2); đối tượng (1,1)–(2,2), diện tích 1: trả **DA_KHOET, 40% vẫn trong vùng lát**. Hướng dẫn “KHÔNG trừ nữa” bỏ sót phần 0.4 chưa khoét.
- Cùng một hatch có hai vỏ rời: (0,0)–(10,10), (20,0)–(24,4), lỗ (21,1)–(22,2). Đối tượng trùng lỗ đảo nhỏ bị trả **NGOAI_VUNG**, vì `max(vo)` chỉ giữ vỏ lớn nhất.

Sửa: dựng cây vòng/vỏ cho mọi thành phần; trả riêng diện tích giao phần tô, phần lỗ và phần ngoài. Chỉ kết luận đã khoét hoàn toàn khi phần tô còn lại nằm trong dung sai hình học có giải thích; ca giao một phần phải giữ nhãn riêng, không dựa ngưỡng 50% để ra quyết định trừ toàn bộ hoặc không trừ. Đoạn skill “chỉ trừ TRONG_VUNG” phải sửa tương ứng.

**R8 — P1 — Bbox block và đường lui thiếu Shapely cho diện tích sai.**

Vị trí: `cad.py:147–166`, `_chu_nhat` tại 58–71.

- Block chữ nhật 2×1 xoay 45°: `_hinh_doi_tuong` trả diện tích **4.5**, hình thật **2**. Bỏ TEXT/ATTRIB ở cấp trực tiếp là đúng hướng, nhưng bbox trục tọa độ vẫn không phải đường bao đối tượng; block lồng còn cần lọc chữ đệ quy.
- Hatch hai vỏ 100 và 16, lỗ 1 ở ca R7: có Shapely ra **115**, ép nhánh không Shapely ra **83** (`100-16-1`). Nhánh “xấp xỉ” vẫn xuất dưới tiêu đề “đã trừ lỗ khoét”, không cảnh báo sai phạm vi hỗ trợ.
- Đọc mã: polyline đối tượng lấy thẳng đỉnh, bỏ bulge; `_chu_nhat` cũng bỏ bulge. Cần ca cung cong/OCS, block lồng và MINSERT; chưa coi các biến thể này đã được nghiệm thu.

Sửa: đo theo hình học thực đã biến đổi; nếu chỉ có bbox thì gắn “ước lượng/chưa xác định”, không kết luận cần trừ. Thiếu Shapely vẫn có thể trả block/chiều dài nhưng phải báo không tính được diện tích hatch, hoặc triển khai thuật toán vòng đúng có test. Không nuốt ngoại lệ thành số 0/âm hoặc bỏ đối tượng mà không nêu handle và lý do.

**R9 — P1 — Phạm vi quét cắt im lặng, chi phí không bị chặn.**

Vị trí: `quet_loi.py:54–69, 181, 330–340`; vòng duyệt CAD tại `cad.py:85, 183, 194`; wrapper Excel tại `them_vao_server.py:49–62`.

- `max_dong=1`, `dong_bat_dau=10` vẫn quét cả dòng 10 và 11 (đã tái hiện). Mặc định thực tế 5001 dòng; phần sau không có cờ “CHƯA QUÉT HẾT”.
- Bảng chỉ có A1=`Diễn giải`, B1=`Khối lượng`, B2=`=#REF!`: trả `([], {'dien_giai':'A'})`; wrapper tự động bỏ qua sheet. Khi ép tên sheet, không có chẩn đoán đủ mạnh về thiếu cột kết quả.
- `quet_sheet_la` duyệt hình chữ nhật mọi cột tới max_column × 5000 dòng, vi phạm yêu cầu `_o_co_that()`; sheet định dạng lan tới XFD gây tốn bộ nhớ/thời gian. Không có ngân sách thời gian/tổng ô/tổng entity. Trần dòng kết quả không giới hạn công việc đã thực hiện.

Sửa: đúng `start + limit - 1`, xác thực giới hạn dương; trả vùng đã kiểm, vùng chưa kiểm, số lượng bỏ qua và cách tiếp tục. Duyệt ô có thật, ngân sách chung cho bộ tính và vòng quét, chặn kích thước/range trước khi bung. Bổ sung chẩn đoán map cột/ứng viên bị loại, không trả “0 nghi vấn” như một lần quét đầy đủ khi không đủ cấu trúc.

**R10 — P1 — Đoạn ghép chưa tương thích server thật.**

Vị trí: `tich_hop/them_vao_server.py:24, 69, 88` và thân ba wrapper.

- **G1:** server đích định nghĩa `_DECO_DOC` tại dòng 949, không có `CHI_DOC`. Dán nguyên trạng sẽ `NameError: name 'CHI_DOC' is not defined` lúc đăng ký tool; đã tái hiện với đối tượng `mcp` giả. Dùng decorator có sẵn `@_DECO_DOC`.
- **G6:** đã kiểm chữ ký `_nap_workbook(duong_dan, **kw)` ở server dòng 1496: hai lời gọi lấy công thức/giá trị **phù hợp**, `.xls` có đường chuyển qua `_nguon_doc`. Không cần tạo loader khác. Tuy nhiên cần `try/finally` đóng cả hai workbook, kể cả lỗi JSON/không có sheet/lỗi nạp workbook thứ hai.
- **G6/F2:** vẫn có `do_cot` + từ khóa nhúng; truyền `cot_map` tay không loại bỏ bộ dò vì `quet_loi_sheet` luôn gọi `do_cot`. Phải thiết kế adapter cho các cột kích thước/số lượng/KL riêng–chung, vì map chung hiện có không tự nhiên cung cấp đủ các vai trò đó; giữ tương thích tool cũ.
- **G6:** hai wrapper CAD thiếu `ensure_file_hydrated` trước đọc DXF. **G4:** mới bắt `RuntimeError`; regex sai, DXF hỏng, JSON hợp lệ nhưng không phải object, map cột không hợp lệ chưa trả chẩn đoán 3 ý. **G2/G3:** thêm giới hạn thực theo R2/R9; xác thực `nguong` trong miền được định nghĩa, không cho giá trị 0/âm/>1 làm phân loại vô nghĩa.
- **G3b/H0:** chưa có bằng chứng tổng docstring sau ghép dưới 50.000 ký tự; cần đo trên server đích. Bổ sung dependency/module vào cả hai file dựng máy, bảng phiên bản/alias và skill trước nghiệm thu. Đây là điều kiện ghép, không phải yêu cầu sửa server trong lượt phản biện này.

### 4. Yêu cầu cho lượt sửa–kiểm kế tiếp

1. Sửa R1–R3, R5–R10 trước khi ghép; bổ sung ca âm/dương cho R4. Giữ nguyên mục đích 26 test cũ; thêm ca hồi quy tái hiện đúng từng lỗi đã nêu, không chỉ sửa kỳ vọng cho xanh.
2. Test tích hợp trên server đích: đăng ký đủ 3 tool, nhãn đúng, loader/đóng workbook/hydration, input lỗi, timeout và cảnh báo phạm vi; chạy kiểm cấu trúc + trần docstring. Chỉ có 26 test module hiện tại chưa kiểm phần này.
3. Cập nhật skill: máy quét chỉ dùng để ưu tiên, không được giới hạn đối chiếu bản vẽ vào duy nhất dòng có cờ khi nhiệm vụ là kiểm toàn bộ. Không suy từ tên sheet thành virus để xóa; không dùng nhãn DA_KHOET hiện tại để bỏ trừ. Giải quyết mâu thuẫn “không tự đặt ngưỡng” với ví dụ lệch >1 m², thay bằng độ chính xác nguồn/dung sai có căn cứ.
4. Sau khi sửa, Claude chạy hồi quy hồ sơ thật tại máy: toàn bộ vùng đã giao và cả ca không-được-báo, CAD nhiều đảo/block xoay/đơn vị mm, số liệu và liên kết KLCT→THKL. Mọi thử ghi chỉ trên bản sao theo E1. Chỉ đưa bằng chứng đã loại dữ liệu hồ sơ khỏi nội dung lên repo.
5. Nối phản hồi vào cùng file, nêu commit sửa, ca đã xử và giới hạn còn lại để Codex kiểm vòng sau. Lượt này hoàn tất **phản biện**, chưa nghiệm thu công cụ hay số liệu công trình.
