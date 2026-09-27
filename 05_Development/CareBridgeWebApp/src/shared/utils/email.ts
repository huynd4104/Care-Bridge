/**
 * Email có thể nhận thư thật: tên miền phải có dấu chấm và đuôi (TLD) từ 2 chữ cái.
 *
 * `<input type="email">` của trình duyệt coi "e@e" là hợp lệ (đúng chuẩn HTML) nhưng
 * địa chỉ đó không bao giờ nhận được OTP/thư mời. Phản chiếu `@DeliverableEmail`
 * phía backend để màn hình báo lỗi trước khi gửi.
 */
const DELIVERABLE_EMAIL = /^[^@\s]+@[^@\s.]+(\.[^@\s.]+)*\.[A-Za-z]{2,}$/;

export const INVALID_EMAIL_ERROR = 'Email không đúng định dạng (ví dụ: ten@example.com).';

export function isDeliverableEmail(value: string): boolean {
  return DELIVERABLE_EMAIL.test(value.trim());
}
