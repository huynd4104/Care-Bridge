import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:universal_io/io.dart';
import 'package:untitled/core/network/api_client.dart';

void main() {
  group('userErrorMessage', () {
    test('never shows the raw ApiException dump for an English server message', () {
      final error = ApiException(
        400,
        '{"success":false,"error":"SOME_UNMAPPED","message":"Something went wrong"}',
      );

      final message = userErrorMessage(error);

      expect(message, 'Yêu cầu không hợp lệ. Vui lòng kiểm tra lại thông tin.');
      expect(message, isNot(contains('ApiException')));
      expect(message, isNot(contains('{')));
      expect(error.displayMessage, isEmpty);
      expect(error.rawServerMessage, 'Something went wrong');
      // Logic cũ dựa trên toString()/body vẫn giữ nguyên.
      expect(error.toString(), contains('SOME_UNMAPPED'));
    });

    test('keeps a Vietnamese server message and maps known codes', () {
      final vietnamese = ApiException(409, '{"error":"X","message":"Buổi tư vấn đã kết thúc."}');
      final mapped = ApiException(403, '{"error":"ACCESS_DENIED","message":"Insufficient permissions"}');

      expect(userErrorMessage(vietnamese), 'Buổi tư vấn đã kết thúc.');
      expect(vietnamese.displayMessage, 'Buổi tư vấn đã kết thúc.');
      expect(userErrorMessage(mapped), 'Bạn không có quyền thực hiện thao tác này.');
    });

    test('keeps the emergency instruction for red-flag errors', () {
      final error = ApiException(
        400,
        '{"error":"RED_FLAG_DETECTED","message":"If this is an emergency, call 115 immediately."}',
      );

      expect(userErrorMessage(error), contains('115'));
    });

    test('uses the screen fallback before the generic status message', () {
      final error = ApiException(404, '{"error":"UNMAPPED","message":"Not here"}');

      expect(userErrorMessage(error, fallback: 'Không tìm thấy nhật ký.'), 'Không tìm thấy nhật ký.');
    });

    test('explains network, timeout and generic failures in Vietnamese', () {
      expect(userErrorMessage(const SocketException('Failed host lookup')), ApiErrorMessages.networkError);
      expect(userErrorMessage(TimeoutException('slow')), ApiErrorMessages.timeoutError);
      expect(userErrorMessage(Exception('Không thể tải dữ liệu')), 'Không thể tải dữ liệu');
      expect(userErrorMessage(StateError('bad state')), ApiErrorMessages.genericError);
    });
  });
}
