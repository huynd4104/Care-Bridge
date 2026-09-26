# HƯỚNG DẪN TUÂN THỦ PHÁP LÝ & BẢO VỆ DỮ LIỆU DỰ ÁN CAREBRIDGE
**(CareBridge Legal & Regulatory Compliance Implementation Guide)**

- **Mục tiêu:** Cung cấp tài liệu tra cứu, căn cứ bảo vệ đồ án tốt nghiệp (SEP490), và hướng dẫn thực thi kỹ thuật nhằm đảm bảo hệ thống CareBridge vượt qua kiểm duyệt App Store, Google Play, và tuân thủ tuyệt đối Nghị định 13/2023/NĐ-CP.
- **Áp dụng cho:** Nhóm Backend (Spring Boot), Nhóm Web (React), Nhóm Mobile (Flutter), và Nhóm Kiểm thử (QA).

---

## 1. MA TRẬN ÁNH XẠ PHÁP LÝ VÀO TÍNH NĂNG HỆ THỐNG (LEGAL MAPPING)

| Văn bản Pháp luật | Điều khoản Trọng tâm | Tính năng CareBridge tương ứng | Giải pháp Kỹ thuật Triển khai |
| :--- | :--- | :--- | :--- |
| **Nghị định 13/2023/NĐ-CP** | **Điều 2, Khoản 4**<br>(Dữ liệu cá nhân nhạy cảm: sức khỏe, đời tư, vị trí) | • Hồ sơ thai kỳ, cử động thai<br>• Chỉ số sinh tồn, trầm cảm EPDS<br>• Nhật ký bé, biểu đồ WHO<br>• Vị trí GPS tính năng SOS | • Phân tách nhóm dữ liệu nhạy cảm.<br>• Yêu cầu Checkbox đồng ý minh bạch.<br>• Mã hóa cột dữ liệu (Field-level encryption) & mã hóa TLS 1.3. |
| **Nghị định 13/2023/NĐ-CP** | **Điều 11, 12**<br>(Sự đồng ý & Rút lại sự đồng ý) | • Màn hình Đăng ký tài khoản<br>• Màn hình Cài đặt Quyền riêng tư | • Lưu vết Consent Log trong database (User ID, Version, Timestamp, IP).<br>• Nút gạt bật/tắt chia sẻ dữ liệu sức khỏe. |
| **Nghị định 13/2023/NĐ-CP** | **Điều 16 & Google/Apple Policy**<br>(Quyền xóa dữ liệu / Account Deletion) | • Quản lý Tài khoản (Account Settings) | • Cung cấp tính năng "Xóa tài khoản vĩnh viễn" trực tiếp trên App.<br>• Cascade delete/ẩn danh hóa dữ liệu người dùng. |
| **Nghị định 13/2023/NĐ-CP** | **Điều 20**<br>(Dữ liệu cá nhân của trẻ em) | • Quản lý hồ sơ bé sơ sinh (Baby Profile)<br>• Bảng kiểm tiêm chủng | • Chỉ cho phép Cha/Mẹ/Người giám hộ hợp pháp tạo hồ sơ.<br>• Tuyệt đối cấm quảng cáo nhắm mục tiêu trẻ em. |
| **Luật Khám bệnh, chữa bệnh 2023** | **Điều 10, 45, 69**<br>(Bí mật y tế & Tư vấn khám chữa bệnh từ xa) | • Quản lý Chuyên gia y tế<br>• Tư vấn trực tuyến ZegoCloud<br>• Chat 1-on-1 với Bác sĩ | • Quy trình eKYC 2 cấp (CCCD + CCHN).<br>• Cấm kê đơn thuốc từ xa sai quy định.<br>• Mã hóa đầu cuối (E2EE/DTLS) luồng thoại/video. |
| **Apple App Store Review Guidelines** | **Guideline 1.4 & 5.1**<br>(Physical Harm & Health Apps Privacy) | • Trợ lý Ảo AI Nurse<br>• Cảnh báo ngã (Fall Detection)<br>• Checklists chăm sóc | • Hiển thị rõ **Medical Disclaimer** (Không thay thế bác sĩ/cấp cứu).<br>• Đường link Privacy Policy công khai trên Store & App. |
| **Google Play Policy** | **Health Apps & User Data Policy** | • Quyền Camera, Microphone, GPS | • Khai báo mục đích rõ ràng (Prominent Disclosure) trước khi xin Runtime Permission. |

---

## 2. CHECKLIST KIỂM ĐỊNH KỸ THUẬT (IMPLEMENTATION CHECKLIST)

### 2.1. Backend API (Spring Boot 3 + PostgreSQL)
- [x] **Bảng Audit Log & Consent Tracking:**
  - Cần bảo đảm bảng ghi nhận sự chấp thuận của người dùng (`user_consents` hoặc bảng hồ sơ) lưu các trường: `user_id`, `policy_version`, `accepted_at`, `ip_address`, `device_info`.
- [x] **API Xóa tài khoản (Account Deletion Endpoint):**
  - Cung cấp endpoint bảo mật: `DELETE /api/v1/users/me` hoặc `POST /api/v1/users/me/deactivate`.
  - Quy trình xử lý: Hủy phiên đăng nhập, thu hồi refresh token, xóa thông tin định danh và ngắt kết nối với các nhóm Family Care.
- [x] **Bảo mật luồng video/âm thanh ZegoCloud:**
  - Token gọi video/voice được tạo động từ phía backend (`ZegoTokenService`) với thời hạn hết hạn ngắn (TTL 3600s), không lưu trữ khóa bí mật (Secret Key) tại client.

### 2.2. Web Portal (React + TypeScript)
- [x] **Đường dẫn Pháp lý Công khai:**
  - `/terms-of-service` -> Kết nối tới [TermsOfServicePage.tsx](file:///d:/SEP490/CareBridge_SEP490_G79/05_Development/CareBridgeWebApp/src/features/legal/pages/TermsOfServicePage.tsx).
  - `/privacy-policy` -> Kết nối tới [PrivacyPolicyPage.tsx](file:///d:/SEP490/CareBridge_SEP490_G79/05_Development/CareBridgeWebApp/src/features/legal/pages/PrivacyPolicyPage.tsx).
- [x] **Footer & Màn hình Đăng ký:**
  - Các trang Landing Page, Chuyên gia đăng ký (Expert Registration) đều có liên kết nhúng đến 2 trang trên.

### 2.3. Mobile App (Flutter)
- [x] **Màn hình Đăng ký (Register Screen):**
  - Checkbox bắt buộc: *"Tôi đồng ý với Điều khoản và Chính sách quyền riêng tư"*.
  - Nhấp vào chữ "Điều khoản" mở nội dung Điều khoản dịch vụ.
  - Nhấp vào chữ "Chính sách quyền riêng tư" mở nội dung Chính sách bảo mật.
- [x] **Prominent Disclosure (Hộp thoại xin quyền trước khi gọi OS Permission):**
  - Quyền Vị trí (Location): Nêu rõ chỉ sử dụng khi người dùng kích hoạt SOS hoặc Cảnh báo ngã để gửi vị trí cho người thân.
  - Quyền Camera/Microphone: Nêu rõ chỉ dùng để gọi video tư vấn với chuyên gia và trích xuất điểm xương tư thế bài tập cục bộ.

---

## 3. ĐỀ CƯƠNG HỒ SƠ NỘP THẨM ĐỊNH BẢO VỆ ĐỒ ÁN (SEP490 DEFENSE READY)

Khi Hội đồng chấm đồ án tốt nghiệp hỏi về khía cạnh **Bảo mật, Quyền riêng tư & Tuân thủ Pháp lý (Security & Compliance)**:
1. **Câu hỏi:** *Hệ thống lưu trữ dữ liệu sức khỏe mẹ và bé, hệ thống đã tuân thủ quy định pháp luật nào của Việt Nam?*
   - **Trả lời:** Hệ thống xây dựng hoàn toàn theo chuẩn **Nghị định số 13/2023/NĐ-CP về Bảo vệ dữ liệu cá nhân** và **Luật Khám bệnh, chữa bệnh 2023**. Dữ liệu thai kỳ và trẻ em được phân loại là dữ liệu cá nhân nhạy cảm, có cơ chế xin chấp thuận độc lập, mã hóa cơ sở dữ liệu và lưu vết Audit log.
2. **Câu hỏi:** *Làm thế nào để tránh trách nhiệm y khoa khi AI hoặc bác sĩ tư vấn xảy ra sự cố?*
   - **Trả lời:** Hệ thống thiết lập điều khoản **Medical Disclaimer (Tuyên bố miễn trừ trách nhiệm y tế)** bắt buộc theo chuẩn Apple Guideline 1.4; khẳng định hệ thống chỉ có giá trị hỗ trợ và giáo dục sức khỏe, không thay thế cấp cứu 115 hay bệnh viện. Đồng thời bác sĩ tham gia tư vấn phải qua quy trình eKYC 2 cấp thẩm định chứng chỉ hành nghề theo Điều 45 Luật Khám bệnh, chữa bệnh.
3. **Câu hỏi:** *Ứng dụng sử dụng camera AI sửa tư thế yoga mẹ bầu có nguy cơ lộ lọt hình ảnh nhạy cảm không?*
   - **Trả lời:** Sidecar MediaPipe xử lý video stream cục bộ trong bộ nhớ tạm theo thời gian thực (real-time frame processing) để trích xuất 33 tọa độ mốc khung xương (x, y, z), **không ghi hình và không lưu trữ bất kỳ tệp video thô nào lên máy chủ/cloud**, đảm bảo quyền riêng tư tuyệt đối cho mẹ bầu.
