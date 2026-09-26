/// Luật nhập liệu cho hồ sơ và chứng chỉ chuyên gia, dùng chung cho các màn chuyên gia.
///
/// Giới hạn và câu thông báo khớp với backend (CreateExpertProfileRequest,
/// UpdateExpertProfileRequest, SubmitCredentialRequest, ExpertCredentialServiceImpl) và
/// với web (`features/expert/utils/expertValidation.ts`). Backend vẫn là nơi chặn cuối
/// cùng; ở đây để báo lỗi ngay khi đang nhập thay vì chờ bấm Lưu.
library;

const int maxExperienceYears = 80;
const int maxSpecialty = 100;
const int maxProfessionalTitle = 150;
const int maxWorkplace = 200;
const int maxConsultationScope = 5000;
const int maxCredentialNumber = 100;
const int maxIssuer = 200;

/// Ngày cấp sớm nhất còn hợp lý; backend chặn cùng mốc này.
final DateTime earliestIssuedDate = DateTime(1950, 1, 1);

/// Ngày hôm nay theo lịch của máy (bỏ phần giờ).
DateTime localToday([DateTime? now]) {
  final value = now ?? DateTime.now();
  return DateTime(value.year, value.month, value.day);
}

/// Số năm kinh nghiệm: không bắt buộc, nếu nhập thì là số nguyên từ 0 đến 80.
String? experienceYearsError(String value) {
  final text = value.trim();
  if (text.isEmpty) return null;
  final years = int.tryParse(text);
  if (years == null) return 'Số năm kinh nghiệm phải là số nguyên';
  if (years < 0) return 'Số năm kinh nghiệm không được âm';
  if (years > maxExperienceYears) {
    return 'Số năm kinh nghiệm tối đa $maxExperienceYears năm';
  }
  return null;
}

/// Ô văn bản: bắt buộc thì không được trống; không bắt buộc thì hoặc để trống hẳn, hoặc
/// có chữ thật. `label` viết như trong câu: "chức danh", "nơi công tác"...
String? textFieldError(
  String value, {
  required String label,
  required int max,
  bool required = false,
}) {
  final capitalized = label[0].toUpperCase() + label.substring(1);
  if (value.trim().isEmpty) {
    if (required) return 'Vui lòng nhập $label';
    return value.isNotEmpty ? '$capitalized không được chỉ chứa khoảng trắng' : null;
  }
  if (value.length > max) return '$capitalized tối đa $max ký tự';
  return null;
}

/// Lỗi của ngày cấp và ngày hết hạn chứng chỉ.
class CredentialDateErrors {
  const CredentialDateErrors({this.issuedDate, this.expiryDate});

  final String? issuedDate;
  final String? expiryDate;

  String? get first => issuedDate ?? expiryDate;
}

/// Ngày cấp không ở tương lai, không trước 1950; ngày hết hạn phải sau ngày cấp và còn
/// hiệu lực. So theo ngày (không có giờ) nên không dính múi giờ.
CredentialDateErrors credentialDateErrors(
  DateTime? issuedDate,
  DateTime? expiryDate, {
  bool expiryRequired = false,
  DateTime? today,
}) {
  final day = localToday(today);
  String? issuedError;
  String? expiryError;
  if (issuedDate == null) {
    issuedError = 'Vui lòng chọn ngày cấp';
  } else if (issuedDate.isAfter(day)) {
    issuedError = 'Ngày cấp không được ở tương lai';
  } else if (issuedDate.isBefore(earliestIssuedDate)) {
    issuedError = 'Ngày cấp không hợp lệ';
  }
  if (expiryDate == null) {
    if (expiryRequired) expiryError = 'Loại chứng chỉ này yêu cầu ngày hết hạn';
  } else if (issuedDate != null && !expiryDate.isAfter(issuedDate)) {
    expiryError = 'Ngày hết hạn phải sau ngày cấp';
  } else if (!expiryDate.isAfter(day)) {
    expiryError = 'Chứng chỉ đã hết hạn, vui lòng nộp chứng chỉ còn hiệu lực';
  }
  return CredentialDateErrors(issuedDate: issuedError, expiryDate: expiryError);
}
