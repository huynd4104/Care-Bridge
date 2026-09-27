import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../models/expert_onboarding_model.dart';
import '../services/expert_onboarding_service.dart';
import '../services/expert_onboarding_store.dart';

class VerificationStatusScreen extends StatefulWidget {
  const VerificationStatusScreen({super.key, this.service});

  final ExpertOnboardingService? service;

  @override
  State<VerificationStatusScreen> createState() =>
      _VerificationStatusScreenState();
}

class _VerificationStatusScreenState extends State<VerificationStatusScreen> {
  ExpertOnboardingState? _state;
  bool _loading = true;
  String? _error;
  bool _resubmitting = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final state = await (widget.service ?? ExpertOnboardingService.instance)
          .loadState();
      ExpertOnboardingStore.instance.update(state);
      if (mounted) setState(() => _state = state);
    } catch (_) {
      if (mounted) {
        setState(() => _error = 'Không thể cập nhật trạng thái xét duyệt.');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF7F1ED),
      appBar: AppBar(
        title: const Text('Trạng thái xác minh'),
        backgroundColor: Colors.transparent,
        foregroundColor: const Color(0xFF2C221E),
        surfaceTintColor: Colors.transparent,
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(20),
          children: [
            if (_loading)
              const Padding(
                padding: EdgeInsets.only(top: 180),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              _messageCard(
                Icons.cloud_off_rounded,
                'Chưa tải được trạng thái',
                _error!,
                const Color(0xFF93000A),
              )
            else ...[
              _statusHero(_state!),
              const SizedBox(height: 18),
              _progressCard(_state!),
              // Chỉ hiện khi còn thứ phải sửa. Model lấy cả lý do cũ của lần định danh
              // trước, nên hồ sơ đã gửi lại xong không được hiện khung đỏ nữa.
              if (_state!.rejectionReason?.isNotEmpty == true &&
                  (_state!.canResubmit ||
                      _state!.identityStatus == 'REJECTED' ||
                      _state!.identityStatus == 'MANUAL_REVIEW_REQUIRED')) ...[
                const SizedBox(height: 16),
                // MANUAL_REVIEW_REQUIRED nghĩa là chờ người duyệt tay, không phải bị
                // từ chối. Gọi nó là "lý do từ chối" và tô đỏ là nói sai với chuyên
                // gia, trong khi ba ô trạng thái ngay trên vẫn đang vàng "chờ duyệt".
                if (_state!.canResubmit || _state!.identityStatus == 'REJECTED')
                  _messageCard(
                    Icons.info_outline_rounded,
                    'Lý do quản trị viên từ chối',
                    _state!.rejectionReason!,
                    const Color(0xFF93000A),
                  )
                else
                  _messageCard(
                    Icons.hourglass_top_rounded,
                    'Tình trạng đối chiếu hồ sơ',
                    _state!.rejectionReason!,
                    const Color(0xFF8A6100),
                  ),
              ],
              const SizedBox(height: 22),
              if (_state!.approved)
                FilledButton.icon(
                  onPressed: () => context.go('/expert-home'),
                  icon: const Icon(Icons.dashboard_rounded),
                  label: const Text('Vào trang chuyên gia'),
                )
              else if (_state!.nextStep != ExpertOnboardingStep.review)
                FilledButton.icon(
                  onPressed: () => context.go(_resumePath(_state!.nextStep)),
                  icon: const Icon(Icons.arrow_forward_rounded),
                  label: const Text('Tiếp tục hoàn thiện hồ sơ'),
                )
              else ...[
                OutlinedButton.icon(
                  onPressed: _load,
                  icon: const Icon(Icons.refresh_rounded),
                  label: const Text('Cập nhật trạng thái'),
                ),
                // Máy chủ là nơi biết khâu nào bị chấm sai, nên app mở đúng bước đó
                // thay vì suy đoán từ trạng thái tài liệu.
                if (_state!.rejectedStep != null) ...[
                  const SizedBox(height: 10),
                  FilledButton.tonalIcon(
                    onPressed: () =>
                        context.go(_resumePath(_state!.rejectedStep!)),
                    icon: const Icon(Icons.edit_outlined),
                    label: Text(
                      'Sửa lại bước ${_stepLabel(_state!.rejectedStep!)}',
                    ),
                  ),
                ],
                // Kiểm tra thủ công không phải là từ chối nên máy chủ không đánh dấu
                // bước sai, nhưng chuyên gia vẫn cần chụp lại ảnh cho rõ.
                if (_state!.identityStatus == 'MANUAL_REVIEW_REQUIRED') ...[
                  const SizedBox(height: 10),
                  FilledButton.tonalIcon(
                    onPressed: () => context.go('/expert/identity'),
                    icon: const Icon(Icons.badge_outlined),
                    label: const Text('Làm lại định danh'),
                  ),
                ],
                // Sửa xong vẫn phải có động tác gửi lại: từ chối toàn hồ sơ không gắn
                // với tài liệu nào để tự kích hoạt xét duyệt.
                if (_state!.canResubmit) ...[
                  const SizedBox(height: 10),
                  FilledButton.icon(
                    onPressed: _resubmitting ? null : _resubmit,
                    icon: const Icon(Icons.send_rounded),
                    label: Text(
                      _resubmitting
                          ? 'Đang gửi lại...'
                          : 'Gửi lại hồ sơ để duyệt',
                    ),
                  ),
                ],
              ],
            ],
          ],
        ),
      ),
    );
  }

  Widget _statusHero(ExpertOnboardingState state) {
    final approved = state.approved;
    final rejected = state.rejected;
    // Hồ sơ đã nộp đủ (kể cả vừa gửi lại) là việc của chuyên gia đã xong, nên
    // dùng màu xanh lá như trạng thái thành công, không dùng màu cảnh báo.
    final submitted = !approved && !rejected &&
        state.nextStep == ExpertOnboardingStep.review;
    final color = approved || submitted
        ? const Color(0xFF287D55)
        : rejected
        ? const Color(0xFFB3261E)
        : const Color(0xFFC06F5A);
    final title = approved
        ? 'Đã xác minh chuyên gia'
        : rejected
        ? 'Hồ sơ cần chỉnh sửa'
        : submitted
        ? 'Đã hoàn thiện hồ sơ'
        : 'Hồ sơ chưa hoàn tất';
    final detail = approved
        ? 'Bạn đã có thể sử dụng các chức năng dành cho chuyên gia.'
        : rejected
        ? 'Sửa đúng bước được chỉ ra bên dưới rồi gửi lại hồ sơ.'
        : submitted
        ? 'Vui lòng đợi quản trị viên xác thực. Kết quả sẽ được gửi về email bạn đã đăng ký.'
        : 'Hoàn thành các bước còn lại để gửi hồ sơ cho quản trị viên.';
    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: color.withValues(alpha: .1),
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        children: [
          Icon(
            approved
                ? Icons.verified_rounded
                : rejected
                ? Icons.assignment_late_rounded
                : submitted
                ? Icons.task_alt_rounded
                : Icons.hourglass_top_rounded,
            size: 62,
            color: color,
          ),
          const SizedBox(height: 14),
          Text(
            title,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w800,
              color: color,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            detail,
            textAlign: TextAlign.center,
            style: const TextStyle(height: 1.5),
          ),
        ],
      ),
    );
  }

  Widget _progressCard(ExpertOnboardingState state) => Container(
    padding: const EdgeInsets.all(18),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(20),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Tiến độ hồ sơ',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800),
        ),
        const SizedBox(height: 14),
        _row('Hồ sơ chuyên môn', state.profileComplete, 'Đã khai báo'),
        _row(
          'Danh tính & CCCD',
          state.identityComplete,
          _statusLabel(state.identityStatus),
        ),
        _row(
          'Giấy tờ chuyên môn',
          state.credentialComplete,
          _statusLabel(state.credentialStatus),
        ),
        _row(
          'Duyệt hồ sơ',
          state.approved,
          _statusLabel(state.verificationStatus),
        ),
      ],
    ),
  );

  Widget _row(String title, bool done, String subtitle) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: Row(
      children: [
        Icon(
          done ? Icons.check_circle : Icons.radio_button_unchecked,
          color: done ? const Color(0xFF287D55) : const Color(0xFF9C857C),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
              Text(
                subtitle,
                style: const TextStyle(fontSize: 12, color: Color(0xFF75635C)),
              ),
            ],
          ),
        ),
      ],
    ),
  );

  Widget _messageCard(
    IconData icon,
    String title,
    String message,
    Color color,
  ) => Container(
    padding: const EdgeInsets.all(18),
    decoration: BoxDecoration(
      color: Colors.white,
      borderRadius: BorderRadius.circular(20),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, color: color),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(fontWeight: FontWeight.w800, color: color),
              ),
              const SizedBox(height: 5),
              Text(message, style: const TextStyle(height: 1.4)),
            ],
          ),
        ),
      ],
    ),
  );

  String _statusLabel(String status) {
    switch (status.toUpperCase()) {
      case 'APPROVED':
        return 'Đã duyệt';
      case 'REJECTED':
        return 'Bị từ chối — cần gửi lại';
      case 'MANUAL_REVIEW_REQUIRED':
        return 'Cần quản trị viên kiểm tra thủ công';
      case 'PENDING':
      case 'PENDING_REVIEW':
      case 'SUBMITTED':
      case 'UNDER_REVIEW':
        return 'Đang chờ xét duyệt';
      case 'EXPIRED':
        return 'Hết hạn — cần gửi lại';
      case 'SUSPENDED':
        return 'Tạm ngưng';
      case 'RETRYABLE':
      case 'RETRYABLE_ERROR':
        return 'Tạm thời chưa xử lý được — vui lòng thử lại';
      case 'MISSING':
      case 'NOT_SUBMITTED':
      case 'REQUIRED':
        return 'Chưa gửi';
      default:
        return status.isEmpty ? 'Chưa có trạng thái' : 'Đang xử lý';
    }
  }

  Future<void> _resubmit() async {
    setState(() => _resubmitting = true);
    try {
      await (widget.service ?? ExpertOnboardingService.instance)
          .renewVerification();
      await _load();
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Không gửi lại được hồ sơ. Vui lòng thử lại.'),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _resubmitting = false);
    }
  }

  /// Tên bước, dùng đúng chữ trên thẻ tiến độ để chuyên gia khỏi phải đoán.
  String _stepLabel(ExpertOnboardingStep step) {
    switch (step) {
      case ExpertOnboardingStep.profile:
        return 'thông tin hồ sơ';
      case ExpertOnboardingStep.expertType:
        return 'hình thức hợp tác';
      case ExpertOnboardingStep.identity:
        return 'định danh';
      case ExpertOnboardingStep.credential:
        return 'chứng chỉ';
      case ExpertOnboardingStep.contract:
        return 'ký thoả thuận';
      case ExpertOnboardingStep.availability:
        return 'lịch làm việc';
      case ExpertOnboardingStep.review:
      case ExpertOnboardingStep.complete:
        return 'hồ sơ';
    }
  }

  String _resumePath(ExpertOnboardingStep step) {
    switch (step) {
      case ExpertOnboardingStep.profile:
        return '/expert-profile-setup';
      case ExpertOnboardingStep.expertType:
        return '/expert/type';
      case ExpertOnboardingStep.contract:
        return '/expert/contract';
      case ExpertOnboardingStep.availability:
        return '/expert-calendar';
      case ExpertOnboardingStep.identity:
        return '/expert/identity';
      case ExpertOnboardingStep.credential:
        return '/expert/credentials';
      case ExpertOnboardingStep.review:
      case ExpertOnboardingStep.complete:
        return '/expert-verification-status';
    }
  }
}
