# UI Test Plan — Manual

Kịch bản test thủ công cho chatbot trên UI. Mỗi scenario phủ 1 hoặc 2 nhãn trong 6 nhãn spec:
`MISSING_FIELD`, `INVALID_INPUT`, `CONFIRMATION`, `SUCCESS_SAVE`, `ERROR_DB`, `UPDATE_PREVIOUS_FIELD`.

## Chuẩn bị

- Bật full stack: `docker compose up -d`
- Mở UI: http://localhost:5173
- Thay `{TAG}` trong tên event bằng 1 chuỗi ngắn duy nhất cho lần test (vd: `t01`, hoặc giờ phút hiện tại). Mục đích: tránh `ERROR_DB` ngoài ý muốn ở các scenario không kiểm tra duplicate.
- **Reset session giữa các scenario**: refresh trang (`Cmd+R`) hoặc xoá `localStorage` để bắt đầu hội thoại mới.
- Bot chỉ nhận tiếng Anh. Nhập tiếng Việt → bị xem là malformed.

---

## Scenario A — Happy path

**Mục tiêu:** Nhập đủ 17 field → bot tóm tắt → confirm → lưu thành công.
**Tag được verify:** `MISSING_FIELD` (lặp lại) → `CONFIRMATION` → `SUCCESS_SAVE`.

Refresh UI trước khi bắt đầu.

| # | Nhập | Bot phải |
|---|------|----------|
| 1 | `I want to create an event` | Hỏi tên event |
| 2 | `Kyoto Jazz {TAG}` | Echo tên, hỏi date (YYYY-MM-DD) |
| 3 | `2027-06-15` | Echo date, hỏi time (HH:MM) |
| 4 | `19:00` | Echo time, hỏi description |
| 5 | `A live jazz performance in Kyoto.` | Echo description, hỏi venue name |
| 6 | `Kyoto Concert Hall` | Echo venue name, hỏi venue address |
| 7 | `123 Sakyo-ku, Kyoto` | Echo address, hỏi capacity |
| 8 | `1000` | Echo capacity, hỏi organizer name |
| 9 | `Fenix Entertainment` | Echo organizer name, hỏi email |
| 10 | `info@fenix.co.jp` | Echo **đầy đủ** `info@fenix.co.jp` (không cắt `.jp`), hỏi ticket limit |
| 11 | `4` | Echo ticket limit, hỏi purchase_start |
| 12 | `2027-01-01` | Echo purchase_start, hỏi purchase_end |
| 13 | `2027-06-10` | Echo purchase_end, hỏi `recurring (yes/no)` |
| 14 | `no` | Echo recurring=False, hỏi category |
| 15 | `Concert` | Echo category, hỏi language |
| 16 | `Japanese` | Echo language, hỏi `online (yes/no)` |
| 17 | `no` | Echo online=False, hỏi seat_types |
| 18 | `VIP: 10000, Regular: 5000` | **Hiện summary đầy đủ 17 field + "Shall I save this event? (yes/no)"**. Tên event = `Kyoto Jazz {TAG}` (không bị overwrite). |
| 19 | `yes` | **"Event 'Kyoto Jazz {TAG}' saved successfully! (Event ID: N)"** |

**Pass khi:** turn 18 hiện summary chính xác, turn 19 báo saved + event ID. Ghi nhớ `{TAG}` để dùng cho scenario D.

---

## Scenario B — Invalid email + correction

**Mục tiêu:** Nhập email sai format → bot báo lỗi → nhập đúng → tiếp tục flow.
**Tag được verify:** `INVALID_INPUT` → `MISSING_FIELD`.

Refresh UI trước khi bắt đầu.

| # | Nhập | Bot phải |
|---|------|----------|
| 1 | `I want to create an event` | Hỏi tên event |
| 2 | `Workshop {TAG}` | Echo, hỏi date |
| 3 | `2027-08-20` | Echo, hỏi time |
| 4 | `14:00` | Echo, hỏi description |
| 5 | `An intro workshop.` | Echo, hỏi venue name |
| 6 | `Town Hall` | Echo, hỏi address |
| 7 | `456 Main St` | Echo, hỏi capacity |
| 8 | `200` | Echo, hỏi organizer name |
| 9 | `Acme Org` | Echo, hỏi email |
| 10 | `hello@not` | **"Thanks for the input. The organizer email you provided isn't valid: ... What's the organizer's email address?"** (KHÔNG được im lặng tiếp tục hoặc lưu email sai) |
| 11 | `hello@acme.io` | Echo email đúng, hỏi ticket limit |

**Pass khi:** turn 10 bot rõ ràng báo email không hợp lệ và hỏi lại; turn 11 chấp nhận email mới.

---

## Scenario C — Edit a previously-set field

**Mục tiêu:** User đổi giá trị field đã nhập → bot cập nhật, không lặp giá trị cũ.
**Tag được verify:** `UPDATE_PREVIOUS_FIELD`.

Refresh UI trước khi bắt đầu.

| # | Nhập | Bot phải |
|---|------|----------|
| 1 | `I want to create an event` | Hỏi tên |
| 2 | `Tech Summit {TAG}` | Echo, hỏi date |
| 3 | `2027-09-10` | Echo `2027-09-10`, hỏi time |
| 4 | `Actually, change the event date to 2027-09-12.` | **"Got it. Updated the event date to '2027-09-12'. Now, ..."** (date phải đổi sang `2027-09-12`, KHÔNG được giữ `2027-09-10`) |

**Pass khi:** turn 4 bot xác nhận `Updated the event date to '2027-09-12'`. Nếu bot vẫn nói "I have the event date as '2027-09-10'" → **fail**.

---

## Scenario D — Duplicate event

**Mục tiêu:** Lưu trùng (`name`, `date`) → bot báo lỗi duplicate.
**Tag được verify:** `MISSING_FIELD` × N → `CONFIRMATION` → `ERROR_DB`.

**Yêu cầu:** Phải đã chạy xong **Scenario A** với cùng `{TAG}` (event `Kyoto Jazz {TAG}` ngày `2027-06-15` phải có trong DB).

Refresh UI trước khi bắt đầu.

| # | Nhập | Bot phải |
|---|------|----------|
| 1 | `I want to create an event` | Hỏi tên |
| 2 | `Kyoto Jazz {TAG}` (cùng tên scenario A) | Echo, hỏi date |
| 3 | `2027-06-15` (cùng date scenario A) | Echo, hỏi time |
| 4–17 | Nhập **bất kỳ** giá trị khác Scenario A cho 14 field còn lại (vd: time `20:00`, venue `Other Hall`, email `other@example.com`, ...) | Tuần tự hỏi từng field |
| 18 | `General: 5000` (hoặc bất kỳ seat_types hợp lệ) | Hiện summary |
| 19 | `yes` | **"An event with the same name and date already exists. Event 'Kyoto Jazz {TAG}' on 2027-06-15 already exists. Please change the name or date to continue."** |

**Pass khi:** turn 19 bot rõ ràng báo duplicate, không lưu thành công.

---

## Scenario E — Multi-field bulk paste

**Mục tiêu:** Nhập 1 message dài chứa nhiều field cùng lúc → bot extract được tối đa có thể, hỏi tiếp field còn thiếu.
**Tag được verify:** `MISSING_FIELD` (cho field còn thiếu) → `CONFIRMATION` → `SUCCESS_SAVE` khi đủ.

Refresh UI trước khi bắt đầu.

| # | Nhập | Bot phải |
|---|------|----------|
| 1 | `I want to create an event called "Bulk Event {TAG}" on 2027-11-20 at 19:00, capacity 800, max 4 tickets, organizer email org@example.com, not recurring, offline.` | Bot hỏi field còn thiếu (bất kỳ trong: description / venue_name / venue_address / organizer_name / purchase_start / purchase_end / category / language / seat_types). **KHÔNG được hỏi lại name, date, time, capacity, ticket_limit, organizer_email, is_recurring, is_online** (vì đã có). Đặc biệt phải nhận `is_recurring=False` từ "not recurring" — không hỏi lại. |
| 2+ | Trả lời từng field bot hỏi tới khi đủ 17 field | Cuối cùng bot hiện summary + "Shall I save this event? (yes/no)" |
| cuối | `yes` | "Event 'Bulk Event {TAG}' saved successfully! (Event ID: N)" |

**Pass khi:**
- Sau turn 1, bot KHÔNG hỏi lại các field đã có trong message.
- Đặc biệt: `recurring` phải là `False` trong summary cuối (kiểm tra fix bug "not recurring").

**Lưu ý:** Free-form text như "in Tokyo Hall at 1 Tokyo Street" có thể không tách được rạch ròi venue_name vs venue_address bởi LLM — bot sẽ hỏi rõ từng cái. Đây là behavior chấp nhận được. Test chỉ kiểm tra **không hỏi lại** các field đã extract được.

---

## Scenario F — Unparseable input không kéo ack cũ

**Mục tiêu:** Khi user gõ thứ không parse được cho field đang được hỏi (vd: chỉ "5" cho time), bot KHÔNG được ack lại field cũ như thể user vừa cung cấp.
**Tag được verify:** `MISSING_FIELD`.

Refresh UI trước khi bắt đầu.

| # | Nhập | Bot phải |
|---|------|----------|
| 1 | `I want to create an event` | Hỏi tên |
| 2 | `Junk Test {TAG}` | Echo, hỏi date |
| 3 | `2027-10-05` | Echo, hỏi time |
| 4 | `5` | **Chỉ hỏi lại time** ("What time does it start? (Please use 24-hour HH:MM format)"). KHÔNG được nói "Got it. I have the event date as '2027-10-05'..." — vì user không cung cấp date mới ở turn này. |

**Pass khi:** turn 4 bot không xuất hiện cụm "Got it. I have the event date as" hoặc "Got it. I have the event name as".

---

## Tổng kết coverage

| Scenario | MISSING | INVALID | UPDATE | CONFIRM | SUCCESS | ERROR_DB |
|---|---|---|---|---|---|---|
| A | ✓ | | | ✓ | ✓ | |
| B | ✓ | ✓ | | | | |
| C | ✓ | | ✓ | | | |
| D | ✓ | | | ✓ | | ✓ |
| E | ✓ | | | ✓ | ✓ | |
| F | ✓ | | | | | |

Đủ 6/6 nhãn spec. E test multi-field extraction; F test UX không ack sai.

---

## Cleanup (optional)

Xoá các event test khỏi DB:

```bash
docker compose exec db psql -U chatbot -d event_chatbot -c \
  "DELETE FROM events WHERE name LIKE '%{TAG}%';"
```

Hoặc reset hoàn toàn:

```bash
docker compose down -v && docker compose up -d
docker compose exec app alembic upgrade head
```
