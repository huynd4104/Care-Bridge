import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:universal_io/io.dart';

import 'api_client.dart';

/// Chuẩn hóa thông báo lỗi sang tiếng Việt để hiển thị cho người dùng.
///
/// Backend trả `{error: <mã>, message: <thông báo>}` với phần lớn `message` là tiếng Anh
/// dành cho log. Thứ tự ưu tiên (giống web `shared/api/apiErrorMessage.ts`):
///   1. `message` của server nếu đã là tiếng Việt;
///   2. câu tiếng Việt theo mã lỗi;
///   3. `fallback` riêng của màn hình;
///   4. câu tiếng Việt theo HTTP status / lỗi mạng.
/// Không bao giờ trả về chuỗi thô kiểu `ApiException(400): {...}`.
class ApiErrorMessages {
  const ApiErrorMessages._();

  static final _vietnameseChars = RegExp(
    r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]',
    caseSensitive: false,
  );

  static const networkError =
      'Không thể kết nối tới máy chủ. Vui lòng kiểm tra kết nối mạng và thử lại.';
  static const timeoutError = 'Máy chủ phản hồi quá lâu. Vui lòng thử lại.';
  static const genericError = 'Đã có lỗi xảy ra. Vui lòng thử lại.';

  static const codeMessages = <String, String>{
    'VALIDATION_ERROR':
        'Dữ liệu gửi lên không hợp lệ. Vui lòng kiểm tra lại thông tin đã nhập.',
    'RESOURCE_NOT_FOUND':
        'Không tìm thấy dữ liệu yêu cầu. Có thể dữ liệu đã bị xóa hoặc thay đổi.',
    'METHOD_NOT_ALLOWED': 'Thao tác này không được hỗ trợ.',
    'ACCESS_DENIED': 'Bạn không có quyền thực hiện thao tác này.',
    'AUTHORIZATION_DENIED': 'Bạn không có quyền thực hiện thao tác này.',
    'AUTHENTICATION_FAILED':
        'Phiên đăng nhập không hợp lệ. Vui lòng đăng nhập lại.',
    'SESSION_REVOKED': 'Phiên đăng nhập đã bị thu hồi. Vui lòng đăng nhập lại.',
    'SESSION_NOT_FOUND':
        'Phiên đăng nhập không còn tồn tại. Vui lòng đăng nhập lại.',
    'INVALID_REFRESH_TOKEN':
        'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
    'ACCOUNT_DISABLED': 'Tài khoản đã bị vô hiệu hóa.',
    'ACCOUNT_ADMIN_LOCKED': 'Tài khoản đã bị quản trị viên khóa.',
    'ACCOUNT_TEMPORARILY_LOCKED':
        'Tài khoản đang bị tạm khóa. Vui lòng thử lại sau.',
    'ACCOUNT_SUSPENDED': 'Tài khoản đang bị tạm đình chỉ.',
    'CONSENT_DENIED':
        'Chưa có sự đồng ý chia sẻ dữ liệu cần thiết cho thao tác này.',
    'RATE_LIMIT_EXCEEDED':
        'Bạn thao tác quá nhanh. Vui lòng đợi một lát rồi thử lại.',
    // An toàn: luôn giữ hướng dẫn gọi cấp cứu.
    'RED_FLAG_DETECTED':
        'Phát hiện dấu hiệu nguy hiểm. Nếu đây là tình huống khẩn cấp, hãy gọi 115 ngay.',
    'INTERNAL_ERROR': 'Hệ thống đang gặp sự cố. Vui lòng thử lại sau.',
    'SYSTEM_MAINTENANCE': 'Hệ thống đang bảo trì. Vui lòng quay lại sau.',
    'IDEMPOTENCY_KEY_REUSE':
        'Yêu cầu này đã được gửi trước đó với nội dung khác. Vui lòng tải lại và thử lại.',
    'TASK_NOT_FOUND':
        'Không tìm thấy việc cần làm. Có thể việc này đã được cập nhật.',
    'CHECKLIST_NOT_FOUND': 'Không tìm thấy checklist.',
    'APPOINTMENT_NOT_FOUND': 'Không tìm thấy lịch hẹn.',
    'SYSTEM_TASK_IMMUTABLE':
        'Việc do CareBridge gợi ý không thể chỉnh sửa hoặc xóa.',
    'SEQUENCE_NOT_READY':
        'Cần hoàn thành tất cả việc bắt buộc trước khi chuyển sang bộ checklist tiếp theo.',
    'SEQUENCE_STALE_CURRENT':
        'Bộ checklist hiện tại đã thay đổi. Vui lòng tải lại.',
    'CONFIGURATION_BLOCKED':
        'Bộ checklist tiếp theo chưa được cấu hình. Vui lòng thử lại sau.',
    'RECOMMENDATION_JOURNEY_REQUIRED':
        'Cần có hành trình thai kỳ đang hoạt động để dùng tính năng này.',
    'BASELINE_REQUIRED':
        'Vui lòng hoàn tất thông tin ban đầu trước khi bắt đầu hành trình.',
    'FAM-005': 'Không tìm thấy nhóm gia đình.',
    'FAM-008': 'Chỉ chủ nhóm mới có thể xóa nhóm này.',
    'EXPERT-004': 'Không tìm thấy hồ sơ chuyên gia.',
    'EXPERT-013':
        'Những khung giờ đã chọn đều đã trôi qua. Vui lòng chọn giờ khác.',
    'BABY-060': 'Không tìm thấy hồ sơ của bé.',
    'BABY-061': 'Bạn không có quyền cập nhật mốc phát triển cho bé này.',
    'BABY-062': 'Hồ sơ của bé đã lưu trữ, không thể thêm mốc phát triển.',
    'BABY-063': 'Loại mốc phát triển không hợp lệ.',
    'BABY-064': 'Ngày đạt được không được ở tương lai.',
    'BABY-065': 'Ngày đạt được không thể trước ngày sinh của bé.',
    'BABY-070': 'Không tìm thấy hồ sơ của bé.',
    'BABY-071':
        'Bạn không có quyền thực hiện thao tác này trên hồ sơ của bé.',
    'BABY-072': 'Vui lòng nhập ít nhất một chỉ số đo.',
    'BABY-073':
        'Hồ sơ của bé đã được lưu trữ, không thể cập nhật thêm số đo.',
    'BABY-074': 'Chỉ số đo phải là số dương lớn hơn 0.',
    'BABY-075': 'Ngày đo không thể trước ngày sinh của bé.',
    'BABY-076': 'Vui lòng nhập ít nhất một trường thông tin cần cập nhật.',
    'BABY-077': 'Vui lòng nhập ít nhất một chỉ số đo.',
    'BABY-078': 'Chỉ số đo phải là số dương lớn hơn 0.',
    'BABY-079': 'Không tìm thấy số đo tăng trưởng.',
    'BABY-GROWTH-400': 'Ngày đo hoặc nguồn đo không hợp lệ.',
    'MILESTONE-001': 'Không tìm thấy mốc phát triển.',
    'MILESTONE-002': 'Bạn không có quyền chỉnh sửa mốc phát triển này.',
    'MILESTONE-003': 'Thông tin cập nhật mốc phát triển không hợp lệ.',
    'METRIC-004': 'Thời điểm đo không được ở tương lai quá 5 phút.',
    'METRIC-032': 'Huyết áp tâm thu phải lớn hơn huyết áp tâm trương.',
    'METRIC-033': 'Đơn vị đo không hợp lệ. Vui lòng thử lại.',
    'METRIC-038': 'Giá trị chỉ số phải lớn hơn 0.',
    'METRIC-039': 'Giá trị chỉ số nằm ngoài giới hạn sinh lý hợp lệ.',
  };

  static const _statusMessages = <int, String>{
    400: 'Yêu cầu không hợp lệ. Vui lòng kiểm tra lại thông tin.',
    401: 'Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.',
    403: 'Bạn không có quyền thực hiện thao tác này.',
    404: 'Không tìm thấy dữ liệu yêu cầu.',
    405: 'Thao tác này không được hỗ trợ.',
    408: 'Máy chủ phản hồi quá lâu. Vui lòng thử lại.',
    409: 'Dữ liệu đã thay đổi hoặc bị xung đột. Vui lòng tải lại và thử lại.',
    413: 'Tệp hoặc dữ liệu gửi lên quá lớn.',
    415: 'Định dạng tệp hoặc dữ liệu không được hỗ trợ.',
    422: 'Không thể xử lý yêu cầu với dữ liệu hiện tại.',
    429: 'Bạn thao tác quá nhanh. Vui lòng đợi một lát rồi thử lại.',
  };

  static bool isVietnamese(String? value) =>
      value != null && _vietnameseChars.hasMatch(value);

  /// Body JSON của ApiException → `{error, message}`; null nếu không phải JSON.
  static Map<String, dynamic>? decodeBody(String body) {
    try {
      final decoded = jsonDecode(body);
      return decoded is Map<String, dynamic> ? decoded : null;
    } catch (_) {
      return null;
    }
  }

  /// Câu tiếng Việt cụ thể: server message tiếng Việt hoặc theo mã lỗi; null nếu không có.
  static String? specific(ApiException error) {
    final decoded = decodeBody(error.message);
    final serverMessage = decoded?['message']?.toString().trim();
    if (isVietnamese(serverMessage)) return serverMessage;
    if (decoded == null && isVietnamese(error.message)) return error.message.trim();
    final code = error.errorCode;
    return code == null ? null : codeMessages[code];
  }

  static String forStatus(int statusCode) {
    final known = _statusMessages[statusCode];
    if (known != null) return known;
    if (statusCode >= 500) return 'Hệ thống đang gặp sự cố. Vui lòng thử lại sau.';
    return genericError;
  }
}

/// Thông báo lỗi tiếng Việt cho mọi loại lỗi (ApiException, mất mạng, timeout...).
String userErrorMessage(Object? error, {String? fallback}) {
  if (error is ApiException) {
    return ApiErrorMessages.specific(error) ??
        fallback ??
        ApiErrorMessages.forStatus(error.statusCode);
  }
  if (error is TimeoutException) return ApiErrorMessages.timeoutError;
  if (error is SocketException || error is http.ClientException) {
    return ApiErrorMessages.networkError;
  }
  if (error is String && ApiErrorMessages.isVietnamese(error)) return error;
  if (error is StateError && ApiErrorMessages.isVietnamese(error.message)) {
    return error.message;
  }
  if (error is FormatException && ApiErrorMessages.isVietnamese(error.message)) {
    return error.message;
  }
  // Service thường ném Exception('câu tiếng Việt'): bỏ tiền tố "Exception: ".
  final text = error?.toString() ?? '';
  final stripped = text.replaceFirst(RegExp(r'^[A-Za-z_]*(Exception|Error): '), '').trim();
  if (ApiErrorMessages.isVietnamese(stripped)) return stripped;
  return fallback ?? ApiErrorMessages.genericError;
}
