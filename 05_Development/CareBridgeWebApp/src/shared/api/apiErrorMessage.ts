/**
 * Chuẩn hóa thông báo lỗi API sang tiếng Việt cho người dùng.
 *
 * Backend trả lỗi dạng { error: <mã>, message: <thông báo>, metadata }. Phần lớn `message` hiện
 * là tiếng Anh dành cho log/dev, còn axios tự đặt `error.message` kiểu
 * "Request failed with status code 400". Thứ tự ưu tiên:
 *   1. `message` của server nếu đã là tiếng Việt;
 *   2. câu tiếng Việt theo mã lỗi (`error`);
 *   3. fallback riêng của màn hình (nếu có);
 *   4. câu tiếng Việt theo HTTP status / lỗi mạng.
 */

const VIETNAMESE_CHARS = /[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i;

export function isVietnameseText(value: unknown): boolean {
  return typeof value === 'string' && VIETNAMESE_CHARS.test(value.normalize('NFC'));
}

/** Câu tiếng Việt cho các mã lỗi dùng chung của backend (GlobalExceptionHandler và mã phổ biến). */
export const API_ERROR_CODE_MESSAGES: Readonly<Record<string, string>> = {
  VALIDATION_ERROR: 'Dữ liệu gửi lên không hợp lệ. Vui lòng kiểm tra lại các trường đã nhập.',
  'CNT-001': 'Dữ liệu nội dung không hợp lệ. Vui lòng kiểm tra lại các trường đã nhập.',
  RESOURCE_NOT_FOUND: 'Không tìm thấy dữ liệu yêu cầu. Có thể dữ liệu đã bị xóa hoặc thay đổi.',
  METHOD_NOT_ALLOWED: 'Thao tác này không được hỗ trợ.',
  ACCESS_DENIED: 'Bạn không có quyền thực hiện thao tác này.',
  AUTHORIZATION_DENIED: 'Bạn không có quyền thực hiện thao tác này.',
  AUTHENTICATION_FAILED: 'Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.',
  SESSION_REVOKED: 'Phiên đăng nhập đã bị thu hồi. Vui lòng đăng nhập lại.',
  SESSION_NOT_FOUND: 'Phiên đăng nhập không còn tồn tại. Vui lòng đăng nhập lại.',
  INVALID_REFRESH_TOKEN: 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
  ACCOUNT_DISABLED: 'Tài khoản đã bị vô hiệu hóa.',
  ACCOUNT_ADMIN_LOCKED: 'Tài khoản đã bị quản trị viên khóa.',
  ACCOUNT_TEMPORARILY_LOCKED: 'Tài khoản đang bị tạm khóa. Vui lòng thử lại sau.',
  ACCOUNT_SUSPENDED: 'Tài khoản đang bị tạm đình chỉ.',
  CONSENT_DENIED: 'Chưa có sự đồng ý chia sẻ dữ liệu cần thiết cho thao tác này.',
  RATE_LIMIT_EXCEEDED: 'Bạn thao tác quá nhanh. Vui lòng đợi một lát rồi thử lại.',
  // An toàn: luôn giữ hướng dẫn gọi cấp cứu.
  RED_FLAG_DETECTED: 'Phát hiện dấu hiệu nguy hiểm. Nếu đây là tình huống khẩn cấp, hãy gọi 115 ngay.',
  INTERNAL_ERROR: 'Hệ thống đang gặp sự cố. Vui lòng thử lại sau.',
  SYSTEM_MAINTENANCE: 'Hệ thống đang bảo trì. Vui lòng quay lại sau.',
  IDEMPOTENCY_KEY_REUSE: 'Yêu cầu này đã được gửi trước đó với nội dung khác. Vui lòng tải lại trang và thử lại.',
  TASK_NOT_FOUND: 'Không tìm thấy việc cần làm. Có thể việc này đã được cập nhật.',
  CHECKLIST_NOT_FOUND: 'Không tìm thấy checklist.',
  APPOINTMENT_NOT_FOUND: 'Không tìm thấy lịch hẹn.',
  SYSTEM_TASK_IMMUTABLE: 'Việc do CareBridge gợi ý không thể chỉnh sửa hoặc xóa.',
  SEQUENCE_NOT_READY: 'Cần hoàn thành tất cả việc bắt buộc trước khi chuyển sang bộ checklist tiếp theo.',
  SEQUENCE_STALE_CURRENT: 'Bộ checklist hiện tại đã thay đổi. Vui lòng tải lại trang.',
  CONFIGURATION_BLOCKED: 'Bộ checklist tiếp theo chưa được cấu hình. Vui lòng thử lại sau.',
  'FAM-005': 'Không tìm thấy nhóm gia đình.',
  'FAM-008': 'Chỉ chủ nhóm mới có thể xóa nhóm này.',
  'EXPERT-004': 'Không tìm thấy hồ sơ chuyên gia.',
  'EXPERT-013': 'Những khung giờ đã chọn đều đã trôi qua. Vui lòng chọn giờ khác.',
  'EXPVER-004': 'Không tìm thấy chứng chỉ.',
  'FILE-001': 'Định dạng tệp không được hỗ trợ. Chỉ hỗ trợ ảnh JPEG, PNG, WebP, HEIC hoặc GIF.',
};

const STATUS_MESSAGES: Readonly<Record<number, string>> = {
  400: 'Yêu cầu không hợp lệ. Vui lòng kiểm tra lại thông tin.',
  401: 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
  403: 'Bạn không có quyền thực hiện thao tác này.',
  404: 'Không tìm thấy dữ liệu yêu cầu.',
  405: 'Thao tác này không được hỗ trợ.',
  408: 'Máy chủ phản hồi quá lâu. Vui lòng thử lại.',
  409: 'Dữ liệu đã thay đổi hoặc bị xung đột. Vui lòng tải lại trang và thử lại.',
  413: 'Tệp hoặc dữ liệu gửi lên quá lớn.',
  415: 'Định dạng tệp hoặc dữ liệu không được hỗ trợ.',
  422: 'Không thể xử lý yêu cầu với dữ liệu hiện tại.',
  429: 'Bạn thao tác quá nhanh. Vui lòng đợi một lát rồi thử lại.',
};

export const NETWORK_ERROR_MESSAGE = 'Không thể kết nối tới máy chủ. Vui lòng kiểm tra kết nối mạng và thử lại.';
export const TIMEOUT_ERROR_MESSAGE = 'Máy chủ phản hồi quá lâu. Vui lòng thử lại.';
export const GENERIC_ERROR_MESSAGE = 'Đã có lỗi xảy ra. Vui lòng thử lại.';

interface ApiErrorLike {
  code?: string;
  message?: string;
  response?: { status?: number; data?: unknown };
}

function responseData(error: unknown): Record<string, unknown> | null {
  const data = (error as ApiErrorLike | null)?.response?.data;
  return data && typeof data === 'object' ? data as Record<string, unknown> : null;
}

/** Thông báo tiếng Việt cụ thể nếu có: server message tiếng Việt hoặc theo mã lỗi. */
export function specificVietnameseMessage(error: unknown): string | null {
  const data = responseData(error);
  if (!data) return null;
  if (isVietnameseText(data.message)) return (data.message as string).trim();
  const code = typeof data.error === 'string' ? data.error : null;
  return code && API_ERROR_CODE_MESSAGES[code] ? API_ERROR_CODE_MESSAGES[code] : null;
}

/** Câu tiếng Việt theo HTTP status hoặc lỗi mạng/timeout. */
export function statusVietnameseMessage(error: unknown): string {
  const candidate = error as ApiErrorLike | null;
  if (candidate?.code === 'ECONNABORTED' || candidate?.code === 'ETIMEDOUT') return TIMEOUT_ERROR_MESSAGE;
  const status = candidate?.response?.status;
  if (status === undefined) {
    return candidate && typeof candidate === 'object' && 'isAxiosError' in candidate
      ? NETWORK_ERROR_MESSAGE
      : GENERIC_ERROR_MESSAGE;
  }
  if (STATUS_MESSAGES[status]) return STATUS_MESSAGES[status];
  if (status >= 500) return 'Hệ thống đang gặp sự cố. Vui lòng thử lại sau.';
  return GENERIC_ERROR_MESSAGE;
}

/**
 * Thông báo lỗi tiếng Việt để hiển thị cho người dùng.
 * `fallback` là câu riêng của màn hình, dùng khi server không có thông báo tiếng Việt cụ thể.
 */
export function getApiErrorMessage(error: unknown, fallback?: string): string {
  return specificVietnameseMessage(error) ?? fallback ?? statusVietnameseMessage(error);
}

const VALIDATION_PATTERNS: ReadonlyArray<[RegExp, (m: RegExpMatchArray) => string]> = [
  [/^must not be (blank|empty|null)$/i, () => 'Không được để trống.'],
  [/^size must be between (\d+) and (\d+)$/i, (m) => `Độ dài phải từ ${m[1]} đến ${m[2]} ký tự.`],
  [/^must be greater than or equal to (-?[\d.]+)$/i, (m) => `Giá trị phải lớn hơn hoặc bằng ${m[1]}.`],
  [/^must be less than or equal to (-?[\d.]+)$/i, (m) => `Giá trị phải nhỏ hơn hoặc bằng ${m[1]}.`],
  [/^must be greater than (-?[\d.]+)$/i, (m) => `Giá trị phải lớn hơn ${m[1]}.`],
  [/^must be less than (-?[\d.]+)$/i, (m) => `Giá trị phải nhỏ hơn ${m[1]}.`],
  [/^must be a well-formed email address$/i, () => 'Email không đúng định dạng.'],
  [/^must be a valid URL$/i, () => 'Đường dẫn không hợp lệ.'],
  [/^must be a future date$/i, () => 'Phải là ngày trong tương lai.'],
  [/^must be a past date$/i, () => 'Phải là ngày trong quá khứ.'],
  [/^must match ".*"$/i, () => 'Giá trị không đúng định dạng.'],
];

/** Dịch câu validation mặc định (Jakarta Bean Validation) của từng trường sang tiếng Việt. */
export function translateValidationMessage(message: string): string {
  const trimmed = message.trim();
  if (isVietnameseText(trimmed)) return trimmed;
  for (const [pattern, render] of VALIDATION_PATTERNS) {
    const match = trimmed.match(pattern);
    if (match) return render(match);
  }
  return 'Giá trị không hợp lệ.';
}

/**
 * Chuẩn hóa lỗi axios tại interceptor: `error.message` luôn là tiếng Việt; `data.message`
 * tiếng Anh được chuyển sang `data.rawMessage` và thay bằng câu theo mã lỗi (hoặc bỏ trống để
 * màn hình dùng fallback riêng). `metadata` giữ nguyên.
 */
export function normalizeApiError<T>(error: T): T {
  const data = responseData(error);
  if (data && typeof data.message === 'string' && !isVietnameseText(data.message)) {
    data.rawMessage = data.message;
    const code = typeof data.error === 'string' ? data.error : null;
    data.message = code && API_ERROR_CODE_MESSAGES[code] ? API_ERROR_CODE_MESSAGES[code] : undefined;
  }
  if (error && typeof error === 'object') {
    try {
      (error as { message?: string }).message = getApiErrorMessage(error);
    } catch {
      // Một số lỗi có message chỉ đọc; khi đó giữ nguyên.
    }
  }
  return error;
}
