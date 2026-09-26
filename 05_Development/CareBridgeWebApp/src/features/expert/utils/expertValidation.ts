/**
 * Luật nhập liệu cho hồ sơ và chứng chỉ chuyên gia, dùng chung cho mọi form chuyên gia.
 *
 * Các giới hạn phải khớp với backend (CreateExpertProfileRequest, UpdateExpertProfileRequest,
 * SubmitCredentialRequest, ExpertCredentialServiceImpl). Backend vẫn là nơi chặn cuối cùng;
 * ở đây chỉ để báo lỗi ngay khi đang gõ, thay vì chờ bấm Lưu rồi mới biết.
 */

export const MAX_EXPERIENCE_YEARS = 80;
export const MAX_PROFESSIONAL_TITLE = 150;
export const MAX_WORKPLACE = 200;
export const MAX_CONSULTATION_SCOPE = 5000;
export const MAX_CREDENTIAL_NUMBER = 100;
export const MAX_ISSUER = 200;
/** Ngày cấp sớm nhất còn hợp lý; backend chặn cùng mốc này. */
export const EARLIEST_ISSUED_DATE = '1950-01-01';

/**
 * Ngày hôm nay theo lịch của người dùng, dạng YYYY-MM-DD.
 *
 * Không dùng `new Date().toISOString()`: hàm đó trả ngày UTC, nên từ 0h đến 7h sáng ở Việt Nam
 * "hôm nay" thành "hôm qua" và người dùng không chọn được ngày hôm nay.
 */
export function localToday(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${month}-${day}`;
}

/** Số năm kinh nghiệm: không bắt buộc, nếu nhập thì là số nguyên từ 0 đến 80. */
export function experienceYearsError(value: string): string | null {
  const text = value.trim();
  if (!text) return null;
  if (!/^-?\d+$/.test(text)) return 'Số năm kinh nghiệm phải là số nguyên';
  const years = Number(text);
  if (years < 0) return 'Số năm kinh nghiệm không được âm';
  if (years > MAX_EXPERIENCE_YEARS) return `Số năm kinh nghiệm tối đa ${MAX_EXPERIENCE_YEARS} năm`;
  return null;
}

interface TextRule {
  /** Tên ô, viết như trong câu: "chức danh", "nơi công tác"... */
  label: string;
  max: number;
  required?: boolean;
}

/**
 * Ô văn bản: bắt buộc thì không được trống; không bắt buộc thì hoặc để trống hẳn, hoặc có chữ
 * thật. "   " từng được lưu thành chức danh trống trơn trên hồ sơ công khai.
 */
export function textFieldError(value: string, rule: TextRule): string | null {
  const label = rule.label.charAt(0).toUpperCase() + rule.label.slice(1);
  if (!value.trim()) {
    if (rule.required) return `Vui lòng nhập ${rule.label}`;
    return value.length > 0 ? `${label} không được chỉ chứa khoảng trắng` : null;
  }
  if (value.length > rule.max) return `${label} tối đa ${rule.max} ký tự`;
  return null;
}

export interface CredentialDateErrors {
  issuedDate?: string;
  expiryDate?: string;
}

/**
 * Ngày cấp / ngày hết hạn chứng chỉ. Ngày ở dạng YYYY-MM-DD nên so sánh chuỗi là đủ và không
 * dính múi giờ (`new Date('2026-09-27')` là nửa đêm UTC, tức 7h sáng ở Việt Nam).
 */
export function credentialDateErrors(
  issuedDate: string,
  expiryDate: string,
  options: { expiryRequired?: boolean; today?: string } = {},
): CredentialDateErrors {
  const today = options.today ?? localToday();
  const errors: CredentialDateErrors = {};
  if (!issuedDate) {
    errors.issuedDate = 'Vui lòng chọn ngày cấp';
  } else if (issuedDate > today) {
    errors.issuedDate = 'Ngày cấp không được ở tương lai';
  } else if (issuedDate < EARLIEST_ISSUED_DATE) {
    errors.issuedDate = 'Ngày cấp không hợp lệ';
  }
  if (!expiryDate) {
    if (options.expiryRequired) errors.expiryDate = 'Loại chứng chỉ này yêu cầu ngày hết hạn';
  } else if (issuedDate && expiryDate <= issuedDate) {
    errors.expiryDate = 'Ngày hết hạn phải sau ngày cấp';
  } else if (expiryDate <= today) {
    errors.expiryDate = 'Chứng chỉ đã hết hạn, vui lòng nộp chứng chỉ còn hiệu lực';
  }
  return errors;
}
