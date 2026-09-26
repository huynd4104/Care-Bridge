import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Remembers whether the user acknowledged the care-plan medical disclaimer.
class PlanDisclaimerStorage {
  static const _acknowledgedKey = 'cb_plan_disclaimer_acknowledged';

  final FlutterSecureStorage _storage;

  PlanDisclaimerStorage({FlutterSecureStorage? storage})
    : _storage =
          storage ??
          const FlutterSecureStorage(
            aOptions: AndroidOptions(encryptedSharedPreferences: true),
          );

  /// Fails open: any storage error means the disclaimer is shown again.
  Future<bool> isAcknowledged() async {
    try {
      return await _storage.read(key: _acknowledgedKey) == 'true';
    } catch (_) {
      return false;
    }
  }

  Future<void> markAcknowledged() async {
    try {
      await _storage.write(key: _acknowledgedKey, value: 'true');
    } catch (_) {
      // Hidden for this session only; it reappears on next launch.
    }
  }
}
