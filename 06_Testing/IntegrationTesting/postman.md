# Hướng dẫn kiểm thử Postman — IT-AUTH-011 đến IT-AUTH-030

Tài liệu này được đối chiếu với backend hiện tại, không sao chép nguyên các placeholder trong cột Evidence của Excel. Những test case kiểm tra hành vi giao diện được đánh dấu rõ: Postman chỉ cung cấp evidence API hỗ trợ, không thay thế được ảnh UI.

## 1. Chuẩn bị chung

### 1.1 Environment

Tạo Postman Environment tên `CareBridge Local` với các biến:

| Variable | Initial/Current value |
| --- | --- |
| `mother_email` | email Mother thật đang hoạt động |
| `mother_password` | mật khẩu thật của Mother |
| `mother_access_token` | để trống, lấy khi đăng nhập |
| `mother_refresh_token` | để trống, lấy khi đăng nhập |
| `admin_email` | email SYSTEM_ADMIN thật |
| `admin_password` | mật khẩu thật của Admin |
| `expert_email` | email EXPERT thật |
| `expert_password` | mật khẩu thật của Expert |
| `family_email` | email FAMILY thật |
| `family_password` | mật khẩu thật của Family |
| `other_session_id` | để trống, lấy ở IT-AUTH-018 |
| `otp_test_email` | email mới, chưa đăng ký, có thể nhận thư |
| `used_otp` | để trống, lấy ở IT-AUTH-030 |

Không mặc định các tài khoản `*.dev` trong sheet chắc chắn tồn tại trên Supabase. Chỉ đánh dấu Passed khi request chạy với tài khoản thật và response đúng vai trò/trạng thái cần kiểm tra.

### 1.2 Đăng nhập Mother và tự lưu token

```http
POST http://localhost:8080/api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "{{mother_email}}",
  "password": "{{mother_password}}"
}
```

Trong tab **Scripts → Post-response**, thêm:

```javascript
const body = pm.response.json();
if (body?.data?.accessToken) {
  pm.environment.set("mother_access_token", body.data.accessToken);
  pm.environment.set("mother_refresh_token", body.data.refreshToken);
}
```

Kết quả hợp lệ là `200 OK`, `success: true`, có `data.accessToken`, `data.refreshToken` và `data.user.role: "MOTHER"`.

Với mọi request yêu cầu đăng nhập bên dưới, chọn **Authorization → Bearer Token** và nhập:

```text
{{mother_access_token}}
```

Không ghi token thật vào ảnh evidence.

---

## IT-AUTH-011 — Bật các quyền riêng tư (supporting API evidence)

Tên test case nói “add grant”, nhưng endpoint trong implementation hiện tại chỉ cập nhật privacy settings; nó không tạo consent grant. Request dưới đây chỉ chứng minh người dùng Mother có thể bật các lựa chọn riêng tư.

```http
PUT http://localhost:8080/api/v1/privacy-settings/me
Authorization: Bearer {{mother_access_token}}
Content-Type: application/json
```

```json
{
  "profileVisibility": "PUBLIC",
  "locationSharingEnabled": true,
  "analyticsConsent": true,
  "dataExportOptOut": false
}
```

Kỳ vọng: `200 OK`, `success: true`, `message: "Privacy settings updated successfully"`; `data` phản ánh các giá trị vừa gửi. Chụp Status và Response, che Authorization.

> Không dùng ảnh này để khẳng định consent grant đã được tạo. Nếu tiêu chí bắt buộc là grant thật, test case/specification cần sửa sang API `/api/v1/consent/grants`.

## IT-AUTH-012 — Kiểm tra trạng thái liên kết Google

```http
GET http://localhost:8080/api/v1/auth/identities/google
Authorization: Bearer {{mother_access_token}}
```

Kỳ vọng: `200 OK` với dữ liệu dạng:

```json
{
  "success": true,
  "data": {
    "provider": "GOOGLE",
    "linked": true,
    "email": "email-google-thật@gmail.com",
    "linkedAt": "..."
  },
  "timestamp": "..."
}
```

Postman chỉ chứng minh trạng thái liên kết. Yêu cầu “không hiển thị standalone handoff control” là kiểm thử UI; cần thêm ảnh màn hình **Linked Accounts** để kết luận Passed.

## IT-AUTH-013 — Bật push notification preference

Body đúng của backend sử dụng `notificationType`, `pushEnabled`, `emailEnabled`, `inAppEnabled`; không dùng `channel/category/enabled` như specification cũ.

```http
PUT http://localhost:8080/api/v1/users/me/notification-preferences
Authorization: Bearer {{mother_access_token}}
Content-Type: application/json
```

```json
{
  "preferences": [
    {
      "notificationType": "REMINDER",
      "pushEnabled": true,
      "emailEnabled": true,
      "inAppEnabled": true
    }
  ],
  "appointmentReminderDefaults": [15, 60]
}
```

Kỳ vọng: `200 OK`, `message: "Notification preferences updated successfully"`; trong `data.preferences`, mục `REMINDER` có `pushEnabled: true`.

Postman chỉ chứng minh preference phía server. Quyền thông báo của Chrome/Android là quyền thiết bị; cần ảnh permission dialog hoặc UI để chứng minh người dùng đã chọn Allow.

## IT-AUTH-014 — Tự vô hiệu hóa tài khoản

> Đây là thao tác phá hủy trạng thái tài khoản. Chỉ dùng tài khoản Mother dùng một lần hoặc tài khoản QA có thể khôi phục. Không dùng tài khoản chính đang cần cho IT-AUTH-015 đến IT-AUTH-020.

Đăng nhập tài khoản QA cần hủy và lưu access token riêng, ví dụ `deactivate_access_token`, sau đó gửi:

```http
DELETE http://localhost:8080/api/v1/auth/deactivate
Authorization: Bearer {{deactivate_access_token}}
Content-Type: application/json
```

```json
{
  "confirmPassword": "mật-khẩu-thật-của-tài-khoản-QA",
  "reason": "Integration test IT-AUTH-014"
}
```

Kỳ vọng: `200 OK`, `success: true`, `data: null`, `message: "Account deactivated successfully"`.

Xác minh bằng cách gọi lại `POST /api/v1/auth/login` với đúng email/password vừa dùng. Kỳ vọng `403 Forbidden`, `error: "ACCOUNT_DISABLED"` và không có access token.

## IT-AUTH-015 — Tắt các quyền riêng tư (supporting API evidence)

Tên test case nói “revoke grants”, nhưng endpoint hiện tại chỉ cập nhật privacy settings.

```http
PUT http://localhost:8080/api/v1/privacy-settings/me
Authorization: Bearer {{mother_access_token}}
Content-Type: application/json
```

```json
{
  "profileVisibility": "PRIVATE",
  "locationSharingEnabled": false,
  "analyticsConsent": false,
  "dataExportOptOut": true
}
```

Kỳ vọng: `200 OK`, `message: "Privacy settings updated successfully"`; `data` phản ánh trạng thái mới.

> Không dùng response này để khẳng định một consent grant đã bị revoke. Muốn test đúng grant phải có `consentId` thật và endpoint consent tương ứng.

## IT-AUTH-016 — Tắt push notification preference

```http
PUT http://localhost:8080/api/v1/users/me/notification-preferences
Authorization: Bearer {{mother_access_token}}
Content-Type: application/json
```

```json
{
  "preferences": [
    {
      "notificationType": "REMINDER",
      "pushEnabled": false,
      "emailEnabled": true,
      "inAppEnabled": true
    }
  ],
  "appointmentReminderDefaults": []
}
```

Kỳ vọng: `200 OK`; mục `REMINDER` trong response có `pushEnabled: false`. Đây là evidence preference phía backend; trạng thái permission của thiết bị cần kiểm tra trên UI/browser.

## IT-AUTH-017 — Thu hồi tất cả session khác

Phải tạo ít nhất hai session thật:

1. Gửi request đăng nhập Mother lần 1 và lưu token thành `mother_access_token_session_a`.
2. Gửi đăng nhập lần 2 và lưu token thành `mother_access_token_session_b`.
3. Dùng token session B gọi:

```http
GET http://localhost:8080/api/v1/sessions
Authorization: Bearer {{mother_access_token_session_b}}
```

Xác nhận có ít nhất một item `isCurrent: false`. Sau đó gọi:

```http
DELETE http://localhost:8080/api/v1/sessions
Authorization: Bearer {{mother_access_token_session_b}}
```

Không có Body. Kỳ vọng: `200 OK`, `success: true`, message có dạng `"Revoked 1 other session(s)"` (con số phụ thuộc dữ liệu thật).

Gọi lại `GET /api/v1/sessions` bằng token B: chỉ session hiện tại còn hoạt động. Không hardcode số session bị revoke.

## IT-AUTH-018 — Thu hồi một session cụ thể

Tạo hai session như IT-AUTH-017 nhưng chưa revoke. Dùng token session B gọi:

```http
GET http://localhost:8080/api/v1/sessions
Authorization: Bearer {{mother_access_token_session_b}}
```

Tìm item có `isCurrent: false`, copy `sessionId` vào biến `other_session_id`. Không lấy session có `isCurrent: true`.

```http
DELETE http://localhost:8080/api/v1/sessions/{{other_session_id}}
Authorization: Bearer {{mother_access_token_session_b}}
```

Kỳ vọng: `200 OK`, `success: true`, `data: null`. Gọi lại `GET /api/v1/sessions` để xác nhận ID đó không còn trong danh sách active.

Nếu chọn current session, backend sẽ từ chối và yêu cầu dùng Logout; đó không phải kết quả Passed của case này.

## IT-AUTH-019 — Retry Account Settings sau lỗi

Đây là kiểm thử hành vi nút Retry trên UI, Postman không thể chứng minh người dùng đã nhấn nút.

Request API hỗ trợ:

```http
GET http://localhost:8080/api/v1/auth/profile
Authorization: Bearer {{mother_access_token}}
```

Khi backend hoạt động, kỳ vọng `200 OK`, `success: true`, `data.accountStatus: "ACTIVE"` và `data.role: "MOTHER"`.

Evidence đúng nên gồm:

1. Ảnh UI ở trạng thái lỗi có nút Retry.
2. Ảnh UI sau khi nhấn Retry và nội dung tải lại thành công.
3. Có thể kèm response `GET /auth/profile` làm evidence API hỗ trợ.

Không nên cố tắt backend giữa chừng chỉ để chụp Postman nếu việc đó ảnh hưởng các thành viên khác.

## IT-AUTH-020 — Validation Account Settings

DTO `PUT /api/v1/auth/profile` hiện chỉ có hai trường `name` và `avatarUrl`; cả hai không được đánh dấu required. Vì vậy body cũ có `name: ""` và `phone: "invalid-phone"` không bảo đảm trả `400` (`phone` không thuộc DTO).

Để kiểm tra validation thật của backend, gửi `name` dài hơn 120 ký tự:

```http
PUT http://localhost:8080/api/v1/auth/profile
Authorization: Bearer {{mother_access_token}}
Content-Type: application/json
```

```json
{
  "name": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
}
```

Body trên có 121 ký tự `A`. Kỳ vọng: `400 Bad Request`, `error: "VALIDATION_ERROR"`, `message: "Invalid request"`, và `details` chứa field `name`.

Nếu tiêu chí bắt buộc là “required-field validation”, phải chụp validation phía UI hoặc sửa DTO/specification vì API hiện không khai báo `name` là bắt buộc.

## IT-AUTH-021 — Tài khoản bị khóa không thể đăng nhập

Chỉ dùng fixture locked thật hoặc tài khoản QA riêng. Không cố tình nhập sai nhiều lần trên tài khoản chính.

```http
POST http://localhost:8080/api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "email-tài-khoản-đang-bị-khóa",
  "password": "mật-khẩu-đúng-của-tài-khoản"
}
```

Kỳ vọng implementation hiện tại:

- `403 Forbidden`.
- Admin lock: `error: "ACCOUNT_ADMIN_LOCKED"`.
- Temporary lock: `error: "ACCOUNT_TEMPORARILY_LOCKED"`.
- Không có `data.accessToken`.

Nếu không có fixture locked trên Supabase, case chưa đủ precondition và không được dùng email giả rồi đánh dấu Passed.

## IT-AUTH-022 — Tài khoản chưa xác minh

Tạo một tài khoản đăng ký mới nhưng chưa nhập OTP, hoặc dùng fixture `PENDING_ACTIVATION` thật. Sau đó:

```http
POST http://localhost:8080/api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "email-pending-thật",
  "password": "mật-khẩu-đúng"
}
```

Theo backend hiện tại, tài khoản chưa kích hoạt có `enabled=false`, nên response thực tế thường là `403 Forbidden`, `error: "ACCOUNT_DISABLED"`, message `"Account is disabled"`; API login không tự trả OTP page.

Việc UI điều hướng sang màn hình OTP là evidence giao diện riêng. Nếu expected bắt buộc `"Account requires OTP verification"`, specification đang không khớp implementation hiện tại.

## IT-AUTH-023 — Identifier dài quá giới hạn

`LoginRequest.email` hiện có `@Email` nhưng không có `@Size(max=...)`. Một email dài nhưng đúng cú pháp có thể qua validation rồi trả `401` vì tài khoản không tồn tại, thay vì `400`.

```http
POST http://localhost:8080/api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@example.com",
  "password": "Test@1234"
}
```

Ghi nhận response thực tế. Không khẳng định `400` nếu server trả `401 Invalid credentials`. Nếu test case yêu cầu giới hạn chiều dài ở API, cần bổ sung `@Size` vào DTO; nếu giới hạn chỉ nằm ở UI, phải chụp UI validation.

## IT-AUTH-024 — Identifier quá ngắn/sai định dạng

```http
POST http://localhost:8080/api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "a",
  "password": "Test@1234"
}
```

Kỳ vọng: `400 Bad Request`, `error: "VALIDATION_ERROR"`, `message: "Invalid request"`; `details` có field `email` với lỗi định dạng email.

## IT-AUTH-025 — Credential có khoảng trắng đầu/cuối

```http
POST http://localhost:8080/api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "  {{mother_email}}  ",
  "password": "  {{mother_password}}  "
}
```

Backend hiện trim và lowercase email, nhưng không trim password. Vì password đã bị thêm khoảng trắng, kỳ vọng là request bị từ chối (`401 Unauthorized`, `Invalid credentials`) và không trả access token. Nếu chỉ thêm khoảng trắng quanh email nhưng giữ password chính xác, email sẽ được normalize và login có thể thành công; đó là hành vi có chủ ý của code hiện tại.

## IT-AUTH-026 — Đăng nhập Administrator

```http
POST http://localhost:8080/api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "{{admin_email}}",
  "password": "{{admin_password}}"
}
```

Kỳ vọng: `200 OK`, `message: "Login successful"`, có `data.accessToken`, `data.refreshToken`, và `data.user.role: "SYSTEM_ADMIN"`. Response hiện tại không có các field `tokenType` hoặc `expiresIn` như specification cũ.

## IT-AUTH-027 — Đăng nhập Expert

```http
POST http://localhost:8080/api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "{{expert_email}}",
  "password": "{{expert_password}}"
}
```

Kỳ vọng: `200 OK`, có access/refresh token và `data.user.role: "EXPERT"`. Chỉ dùng account Expert thật đang `ACTIVE`.

## IT-AUTH-028 — Đăng nhập Family

```http
POST http://localhost:8080/api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "{{family_email}}",
  "password": "{{family_password}}"
}
```

Kỳ vọng: `200 OK`, có access/refresh token và `data.user.role: "FAMILY"`.

## IT-AUTH-029 — Đăng nhập Mother

```http
POST http://localhost:8080/api/v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "{{mother_email}}",
  "password": "{{mother_password}}"
}
```

Kỳ vọng: `200 OK`, có access/refresh token, `data.user.role: "MOTHER"`, `data.user.accountStatus: "ACTIVE"`.

Với IT-AUTH-026 đến IT-AUTH-029, chụp phần Status và `data.user.role`; che toàn bộ `accessToken` và `refreshToken`.

## IT-AUTH-030 — OTP đã dùng bị từ chối

Phải dùng OTP thật rồi replay chính OTP đó. Không dùng `000000` vì nó chỉ chứng minh OTP sai, không chứng minh OTP đã từng được dùng.

### Bước 1: đăng ký tài khoản QA mới

Đặt `otp_test_email` thành một email thật chưa đăng ký và có thể nhận thư.

```http
POST http://localhost:8080/api/v1/auth/register
Content-Type: application/json
```

```json
{
  "name": "OTP Replay QA",
  "email": "{{otp_test_email}}",
  "password": "OtpReplay@123",
  "role": "MOTHER",
  "verificationMethod": "EMAIL"
}
```

Kỳ vọng: `201 Created`, `success: true`, message `"OTP sent"`. Lấy mã OTP 6 chữ số thật trong email và lưu vào biến `used_otp`. OTP có thời hạn ngắn; thực hiện ngay.

### Bước 2: dùng OTP lần đầu

```http
POST http://localhost:8080/api/v1/auth/verify-otp
Content-Type: application/json
```

```json
{
  "email": "{{otp_test_email}}",
  "otp": "{{used_otp}}"
}
```

Kỳ vọng lần đầu: `200 OK`, `success: true`, message `"OTP verified"`, có access/refresh token. Đây là bằng chứng OTP đã được sử dụng thành công.

### Bước 3: gửi lại đúng request lần thứ hai

Không đổi email và không đổi OTP. Nhấn **Send** lại.

Kỳ vọng lần hai: `400 Bad Request`, `success` không có hoặc false theo error envelope, `error: "VALIDATION_ERROR"`, message `"Invalid or expired OTP"`. Không có token mới.

Evidence tốt nhất gồm hai ảnh hoặc một ảnh ghép:

1. Lần đầu `200 OK` với `OTP verified` nhưng che access/refresh token.
2. Lần hai dùng cùng OTP trả `400 Bad Request`, `Invalid or expired OTP`; che mã OTP trong Body.

---

## 2. Quy tắc chụp evidence

- Hiển thị method, URL, HTTP status và response body.
- Thu gọn/che tab Authorization trước khi chụp.
- Che access token, refresh token, Firebase token, OTP và mật khẩu.
- Không dùng response `OPTIONS 200 OK` làm evidence; phải chọn request thật (`GET`, `POST`, `PUT` hoặc `DELETE`).
- Không đánh dấu Passed khi precondition không tồn tại, ví dụ không có locked account, không có second session hoặc email fixture không tồn tại trên Supabase.
- Các case UI (`IT-AUTH-012`, `013`, `016`, `019`, `020`, `022`, `023`) cần ảnh UI nếu expected result nói về control, dialog, redirect hoặc validation trên màn hình; Postman chỉ là evidence hỗ trợ.
