import { describe, expect, it } from 'vitest';
import {
  NETWORK_ERROR_MESSAGE,
  TIMEOUT_ERROR_MESSAGE,
  getApiErrorMessage,
  normalizeApiError,
  translateValidationMessage,
} from './apiErrorMessage';

function axiosError(status: number | undefined, data?: Record<string, unknown>, code?: string) {
  return {
    isAxiosError: true,
    code,
    message: status ? `Request failed with status code ${status}` : 'Network Error',
    response: status === undefined ? undefined : { status, data },
  };
}

describe('apiErrorMessage', () => {
  it('replaces the axios "Request failed with status code" text with Vietnamese', () => {
    const error = normalizeApiError(axiosError(400, { error: 'SOME_UNMAPPED', message: 'Something went wrong' }));

    expect(error.message).toBe('Yêu cầu không hợp lệ. Vui lòng kiểm tra lại thông tin.');
    expect(error.message).not.toContain('status code');
    expect(error.response?.data).toMatchObject({ message: undefined, rawMessage: 'Something went wrong' });
  });

  it('keeps a Vietnamese server message as-is', () => {
    const error = normalizeApiError(axiosError(409, { error: 'X', message: 'Buổi tư vấn đã kết thúc.' }));

    expect(error.message).toBe('Buổi tư vấn đã kết thúc.');
    expect(error.response?.data).toMatchObject({ message: 'Buổi tư vấn đã kết thúc.' });
    expect(error.response?.data).not.toHaveProperty('rawMessage');
  });

  it('maps known backend codes and keeps metadata untouched', () => {
    const metadata = { reasonCode: 'CHECKLIST_DUPLICATE_SEQUENCE_POSITION' };
    const error = normalizeApiError(axiosError(400, {
      error: 'VALIDATION_ERROR', message: 'Invalid request body', metadata,
    }));

    expect(error.message).toContain('Dữ liệu gửi lên không hợp lệ');
    expect(error.response?.data).toMatchObject({ message: error.message, metadata });
  });

  it('never drops the emergency instruction for red-flag errors', () => {
    const message = getApiErrorMessage(axiosError(400, {
      error: 'RED_FLAG_DETECTED', message: 'Severe bleeding. If this is an emergency, call 115 immediately.',
    }));

    expect(message).toContain('115');
  });

  it('prefers the screen fallback over a generic status message', () => {
    const error = normalizeApiError(axiosError(404, { error: 'UNMAPPED', message: 'Not here' }));

    expect(getApiErrorMessage(error, 'Không tìm thấy lịch hẹn này.')).toBe('Không tìm thấy lịch hẹn này.');
  });

  it('explains network failures and timeouts in Vietnamese', () => {
    expect(normalizeApiError(axiosError(undefined)).message).toBe(NETWORK_ERROR_MESSAGE);
    expect(normalizeApiError(axiosError(undefined, undefined, 'ECONNABORTED')).message).toBe(TIMEOUT_ERROR_MESSAGE);
    expect(normalizeApiError(axiosError(503, { error: 'X', message: 'Service Unavailable' })).message)
      .toContain('Hệ thống đang gặp sự cố');
  });

  it('translates default field validation messages', () => {
    expect(translateValidationMessage('must not be blank')).toBe('Không được để trống.');
    expect(translateValidationMessage('size must be between 1 and 500')).toBe('Độ dài phải từ 1 đến 500 ký tự.');
    expect(translateValidationMessage('Tên không hợp lệ')).toBe('Tên không hợp lệ');
    expect(translateValidationMessage('some unknown english text')).toBe('Giá trị không hợp lệ.');
  });
});
