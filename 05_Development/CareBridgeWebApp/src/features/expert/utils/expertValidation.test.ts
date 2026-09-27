import { describe, expect, it } from 'vitest';
import {
  credentialDateErrors,
  experienceYearsError,
  localToday,
  textFieldError,
} from './expertValidation';

describe('experienceYearsError', () => {
  it('cho để trống vì không bắt buộc', () => {
    expect(experienceYearsError('')).toBeNull();
    expect(experienceYearsError('  ')).toBeNull();
  });

  it('nhận biên 0 và 80', () => {
    expect(experienceYearsError('0')).toBeNull();
    expect(experienceYearsError('80')).toBeNull();
  });

  it('chặn số âm, quá 80 năm và số lẻ', () => {
    expect(experienceYearsError('-1')).toBe('Số năm kinh nghiệm không được âm');
    expect(experienceYearsError('81')).toBe('Số năm kinh nghiệm tối đa 80 năm');
    expect(experienceYearsError('2.5')).toBe('Số năm kinh nghiệm phải là số nguyên');
    expect(experienceYearsError('abc')).toBe('Số năm kinh nghiệm phải là số nguyên');
  });
});

describe('textFieldError', () => {
  const title = { label: 'chức danh', max: 150 };

  it('chặn ô chỉ có khoảng trắng', () => {
    expect(textFieldError('   ', title)).toBe('Chức danh không được chỉ chứa khoảng trắng');
    expect(textFieldError('', title)).toBeNull();
  });

  it('ô bắt buộc báo thiếu', () => {
    expect(textFieldError('  ', { ...title, required: true })).toBe('Vui lòng nhập chức danh');
  });

  it('chặn quá độ dài', () => {
    expect(textFieldError('x'.repeat(151), title)).toBe('Chức danh tối đa 150 ký tự');
    expect(textFieldError('x'.repeat(150), title)).toBeNull();
  });
});

describe('credentialDateErrors', () => {
  const today = '2026-09-27';

  it('nhận chứng chỉ hợp lệ', () => {
    expect(credentialDateErrors('2020-01-01', '2030-01-01', { today })).toEqual({});
    expect(credentialDateErrors('2020-01-01', '', { today })).toEqual({});
  });

  it('ngày cấp không được ở tương lai hay quá xa', () => {
    expect(credentialDateErrors('2026-09-28', '', { today }).issuedDate).toBe('Ngày cấp không được ở tương lai');
    expect(credentialDateErrors('1900-01-01', '', { today }).issuedDate).toBe('Ngày cấp không hợp lệ');
    expect(credentialDateErrors(today, '', { today })).toEqual({});
  });

  it('ngày hết hạn phải sau ngày cấp và còn hiệu lực', () => {
    expect(credentialDateErrors('2020-01-01', '2019-01-01', { today }).expiryDate).toBe('Ngày hết hạn phải sau ngày cấp');
    expect(credentialDateErrors('2020-01-01', '2020-01-01', { today }).expiryDate).toBe('Ngày hết hạn phải sau ngày cấp');
    expect(credentialDateErrors('2020-01-01', '2026-09-26', { today }).expiryDate).toBe(
      'Chứng chỉ đã hết hạn, vui lòng nộp chứng chỉ còn hiệu lực',
    );
  });

  it('báo thiếu ngày hết hạn khi loại chứng chỉ bắt buộc', () => {
    expect(credentialDateErrors('2020-01-01', '', { today, expiryRequired: true }).expiryDate).toBe(
      'Loại chứng chỉ này yêu cầu ngày hết hạn',
    );
  });
});

describe('localToday', () => {
  it('lấy ngày theo giờ địa phương chứ không theo UTC', () => {
    // 01:15 sáng 27/9 giờ máy: toISOString() sẽ ra ngày 26 nếu máy ở UTC+7.
    expect(localToday(new Date(2026, 8, 27, 1, 15))).toBe('2026-09-27');
  });
});
