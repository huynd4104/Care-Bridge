import 'package:flutter/material.dart';

import '../services/plan_disclaimer_storage.dart';

const planDisclaimerMessage =
    'Các kế hoạch được gợi ý dựa trên dữ liệu chung và không thay thế cho việc '
    'chẩn đoán, điều trị hoặc lời khuyên của bác sĩ chuyên khoa. Người dùng cần '
    'tham khảo ý kiến bác sĩ trước khi thay đổi chế độ vận động hoặc dinh dưỡng.';

/// Medical disclaimer that stays visible until the user taps "Đã hiểu" and
/// confirms in a dialog.
class PlanDisclaimerBanner extends StatefulWidget {
  const PlanDisclaimerBanner({super.key, this.storage});

  final PlanDisclaimerStorage? storage;

  @override
  State<PlanDisclaimerBanner> createState() => _PlanDisclaimerBannerState();
}

class _PlanDisclaimerBannerState extends State<PlanDisclaimerBanner> {
  static const _text = Color(0xFF5A463F);
  static const _body = Color(0xFF735E56);
  static const _accent = Color(0xFF845143);

  late final PlanDisclaimerStorage _storage =
      widget.storage ?? PlanDisclaimerStorage();
  bool _loaded = false;
  bool _acknowledged = false;

  @override
  void initState() {
    super.initState();
    _loadAcknowledgement();
  }

  Future<void> _loadAcknowledgement() async {
    final acknowledged = await _storage.isAcknowledged();
    if (!mounted) return;
    setState(() {
      _acknowledged = acknowledged;
      _loaded = true;
    });
  }

  Future<void> _confirmDismiss() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        key: const Key('plan-disclaimer-confirm-dialog'),
        title: const Text(
          'Xác nhận đã hiểu',
          style: TextStyle(
            fontFamily: 'Quicksand',
            fontWeight: FontWeight.w800,
            color: _text,
          ),
        ),
        content: const Text(
          'Bạn xác nhận đã đọc và hiểu rằng các kế hoạch gợi ý không thay thế '
          'cho việc chẩn đoán, điều trị hoặc lời khuyên của bác sĩ chuyên khoa?',
          style: TextStyle(fontFamily: 'Quicksand', color: _body),
        ),
        actions: [
          TextButton(
            key: const Key('plan-disclaimer-cancel'),
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            key: const Key('plan-disclaimer-confirm'),
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Xác nhận'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _acknowledged = true);
    await _storage.markAcknowledged();
  }

  @override
  Widget build(BuildContext context) {
    if (!_loaded || _acknowledged) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Semantics(
        key: const Key('plan-disclaimer-banner'),
        container: true,
        label: planDisclaimerMessage,
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
          decoration: BoxDecoration(
            color: const Color(0xFFFFF7F1),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: const Color(0xFFE8CFC2)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(Icons.info_outline_rounded, color: Color(0xFFC98C7B)),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      planDisclaimerMessage,
                      style: TextStyle(
                        fontFamily: 'Quicksand',
                        fontSize: 13,
                        height: 1.4,
                        color: _body,
                      ),
                    ),
                  ),
                ],
              ),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  key: const Key('plan-disclaimer-ack-button'),
                  onPressed: _confirmDismiss,
                  style: TextButton.styleFrom(foregroundColor: _accent),
                  child: const Text(
                    'Đã hiểu',
                    style: TextStyle(
                      fontFamily: 'Quicksand',
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
