import 'package:untitled/features/expert/utils/expert_validation.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('experienceYearsError', () {
    test('cho để trống vì không bắt buộc', () {
      expect(experienceYearsError(''), isNull);
      expect(experienceYearsError('  '), isNull);
    });

    test('nhận biên 0 và 80', () {
      expect(experienceYearsError('0'), isNull);
      expect(experienceYearsError('80'), isNull);
    });

    test('chặn số âm, quá 80 năm và chữ', () {
      expect(experienceYearsError('-1'), 'Số năm kinh nghiệm không được âm');
      expect(experienceYearsError('81'), 'Số năm kinh nghiệm tối đa 80 năm');
      expect(experienceYearsError('2.5'), 'Số năm kinh nghiệm phải là số nguyên');
      expect(experienceYearsError('abc'), 'Số năm kinh nghiệm phải là số nguyên');
    });
  });

  group('textFieldError', () {
    test('chặn ô chỉ có khoảng trắng', () {
      expect(
        textFieldError('   ', label: 'chức danh', max: 150),
        'Chức danh không được chỉ chứa khoảng trắng',
      );
      expect(textFieldError('', label: 'chức danh', max: 150), isNull);
    });

    test('ô bắt buộc báo thiếu', () {
      expect(
        textFieldError(' ', label: 'chuyên khoa', max: 100, required: true),
        'Vui lòng nhập chuyên khoa',
      );
    });

    test('chặn quá độ dài', () {
      expect(
        textFieldError('x' * 151, label: 'chức danh', max: 150),
        'Chức danh tối đa 150 ký tự',
      );
      expect(textFieldError('x' * 150, label: 'chức danh', max: 150), isNull);
    });
  });

  group('credentialDateErrors', () {
    final today = DateTime(2026, 9, 27);

    test('nhận chứng chỉ hợp lệ, kể cả cấp hôm nay', () {
      expect(
        credentialDateErrors(DateTime(2020), DateTime(2030), today: today).first,
        isNull,
      );
      expect(credentialDateErrors(today, null, today: today).first, isNull);
    });

    test('ngày cấp không ở tương lai, không quá xa', () {
      expect(
        credentialDateErrors(DateTime(2026, 9, 28), null, today: today).issuedDate,
        'Ngày cấp không được ở tương lai',
      );
      expect(
        credentialDateErrors(DateTime(1900), null, today: today).issuedDate,
        'Ngày cấp không hợp lệ',
      );
    });

    test('ngày hết hạn phải sau ngày cấp và còn hiệu lực', () {
      expect(
        credentialDateErrors(DateTime(2020), DateTime(2019), today: today).expiryDate,
        'Ngày hết hạn phải sau ngày cấp',
      );
      expect(
        credentialDateErrors(DateTime(2020), DateTime(2026, 9, 26), today: today)
            .expiryDate,
        'Chứng chỉ đã hết hạn, vui lòng nộp chứng chỉ còn hiệu lực',
      );
    });
  });
}
