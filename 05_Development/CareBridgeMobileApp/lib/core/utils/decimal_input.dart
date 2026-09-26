import 'package:flutter/services.dart';

/// Ô nhập số thập phân không âm.
///
/// Bàn phím tiếng Việt dùng `,` làm dấu thập phân, nên `,` được đổi thành `.`
/// thay vì bị lọc bỏ (lọc bỏ khiến "1,5" thành "15"). Chỉ cho phép một dấu
/// thập phân và giới hạn số chữ số phần nguyên/phần thập phân, để không thể
/// nhập chữ, số âm hay số quá lớn.
class DecimalTextInputFormatter extends TextInputFormatter {
  DecimalTextInputFormatter({
    this.maxIntegerDigits = 6,
    this.maxFractionDigits = 2,
  }) : _pattern = RegExp(
         maxFractionDigits > 0
             ? '^\\d{0,$maxIntegerDigits}(\\.\\d{0,$maxFractionDigits})?\$'
             : '^\\d{0,$maxIntegerDigits}\$',
       );

  final int maxIntegerDigits;
  final int maxFractionDigits;
  final RegExp _pattern;

  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final text = newValue.text.replaceAll(',', '.');
    if (text.isEmpty) return newValue;
    // Luôn cho xóa bớt ký tự, kể cả khi giá trị điền sẵn vượt định dạng
    // (vd. "5.5555"), để ô không bị khóa.
    final isDeletion = text.length < oldValue.text.length &&
        RegExp(r'^[0-9.]*$').hasMatch(text);
    if (!isDeletion && !_pattern.hasMatch(text)) return oldValue;
    return newValue.copyWith(text: text);
  }
}

/// Đọc số từ ô nhập, chấp nhận cả `,` và `.`; trả về null nếu rỗng/không hợp lệ.
double? parseDecimalInput(String? raw) {
  final text = (raw ?? '').trim().replaceAll(',', '.');
  if (text.isEmpty) return null;
  final value = double.tryParse(text);
  return value != null && value.isFinite ? value : null;
}

/// Hiển thị giới hạn gọn gàng: 10.0 → "10", 0.5 → "0.5".
String formatDecimalBound(num value) {
  return value == value.roundToDouble()
      ? value.toInt().toString()
      : value.toString();
}
