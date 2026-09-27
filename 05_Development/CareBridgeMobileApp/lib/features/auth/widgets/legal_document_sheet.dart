import 'package:flutter/material.dart';
import 'auth_ui.dart';

/// Enum phân loại tài liệu pháp lý cần hiển thị.
enum LegalDocType {
  terms,
  privacy,
}

/// Mở Modal BottomSheet hiển thị văn bản Điều khoản hoặc Chính sách quyền riêng tư.
/// Trả về `true` nếu người dùng nhấn nút "Đồng ý", hoặc `false`/`null` nếu đóng.
Future<bool?> showLegalDocumentSheet(
  BuildContext context, {
  LegalDocType initialDoc = LegalDocType.terms,
}) {
  return showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    backgroundColor: Colors.transparent,
    barrierColor: Colors.black54,
    builder: (_) => LegalDocumentSheet(initialDoc: initialDoc),
  );
}

class LegalDocumentSheet extends StatefulWidget {
  const LegalDocumentSheet({
    super.key,
    this.initialDoc = LegalDocType.terms,
  });

  final LegalDocType initialDoc;

  @override
  State<LegalDocumentSheet> createState() => _LegalDocumentSheetState();
}

class _LegalDocumentSheetState extends State<LegalDocumentSheet> {
  late LegalDocType _currentDoc;

  @override
  void initState() {
    super.initState();
    _currentDoc = widget.initialDoc;
  }

  @override
  Widget build(BuildContext context) {
    final mediaQuery = MediaQuery.of(context);
    final maxHeight = mediaQuery.size.height * 0.88;

    return Container(
      constraints: BoxConstraints(maxHeight: maxHeight),
      decoration: const BoxDecoration(
        color: AuthPalette.surface,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          children: [
            _buildDragHandle(),
            _buildHeader(context),
            const Divider(height: 1, color: AuthPalette.line),
            _buildSegmentedTab(),
            Expanded(
              child: SingleChildScrollView(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                child: _currentDoc == LegalDocType.terms
                    ? _buildTermsContent()
                    : _buildPrivacyContent(),
              ),
            ),
            const Divider(height: 1, color: AuthPalette.line),
            _buildStickyFooter(context),
          ],
        ),
      ),
    );
  }

  Widget _buildDragHandle() {
    return Center(
      child: Container(
        margin: const EdgeInsets.only(top: 12, bottom: 8),
        width: 44,
        height: 4,
        decoration: BoxDecoration(
          color: AuthPalette.line,
          borderRadius: BorderRadius.circular(2),
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 4, 12, 12),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AuthPalette.surfaceSoft,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              _currentDoc == LegalDocType.terms
                  ? Icons.gavel_rounded
                  : Icons.privacy_tip_rounded,
              size: 20,
              color: AuthPalette.accentDeep,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _currentDoc == LegalDocType.terms
                      ? 'Điều khoản dịch vụ'
                      : 'Chính sách quyền riêng tư',
                  style: const TextStyle(
                    fontFamily: 'Lexend',
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    color: AuthPalette.ink,
                  ),
                ),
                const SizedBox(height: 2),
                const Text(
                  'Nền tảng Y tế Mẹ & Bé CareBridge (v1.0)',
                  style: TextStyle(
                    fontFamily: 'Lexend',
                    fontSize: 12,
                    color: AuthPalette.muted,
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close_rounded, color: AuthPalette.mutedStrong),
            tooltip: 'Đóng',
            onPressed: () => Navigator.of(context).pop(false),
          ),
        ],
      ),
    );
  }

  Widget _buildSegmentedTab() {
    return Container(
      margin: const EdgeInsets.fromLTRB(20, 10, 20, 4),
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: AuthPalette.surfaceSoft,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Expanded(
            child: _buildTabItem(
              title: 'Điều khoản dịch vụ',
              selected: _currentDoc == LegalDocType.terms,
              onTap: () => setState(() => _currentDoc = LegalDocType.terms),
            ),
          ),
          Expanded(
            child: _buildTabItem(
              title: 'Quyền riêng tư (NĐ 13)',
              selected: _currentDoc == LegalDocType.privacy,
              onTap: () => setState(() => _currentDoc = LegalDocType.privacy),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTabItem({
    required String title,
    required bool selected,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          color: selected ? AuthPalette.surface : Colors.transparent,
          borderRadius: BorderRadius.circular(9),
          boxShadow: selected
              ? [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.05),
                    blurRadius: 4,
                    offset: const Offset(0, 1),
                  ),
                ]
              : null,
        ),
        child: Text(
          title,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontFamily: 'Lexend',
            fontSize: 12,
            fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
            color: selected ? AuthPalette.accentDeep : AuthPalette.muted,
          ),
        ),
      ),
    );
  }

  Widget _buildTermsContent() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildNoticeCard(
          icon: Icons.warning_amber_rounded,
          color: const Color(0xFFD97706),
          bgColor: const Color(0xFFFFFBEB),
          title: 'TUYÊN BỐ MIỄN TRỪ TRÁCH NHIỆM Y TẾ (QUAN TRỌNG)',
          content:
              'CareBridge và Trợ lý AI Nurse không cung cấp dịch vụ cấp cứu y tế. '
              'Mọi gợi ý, checklist, phân tích chỉ mang tính chất tham khảo giáo dục sức khỏe, '
              'không thay thế cho chẩn đoán của bác sĩ. Trong trường hợp nguy cấp, '
              'hãy gọi ngay 115 hoặc đến cơ sở y tế gần nhất.',
        ),
        const SizedBox(height: 16),
        _buildSectionTitle('1. Chấp thuận Thỏa thuận Điện tử'),
        _buildParagraph(
          'Bằng việc đăng ký tài khoản hoặc sử dụng ứng dụng CareBridge, bạn xác nhận '
          'đã đủ 18 tuổi (hoặc có người giám hộ) và đồng ý chịu ràng buộc pháp lý theo '
          'Luật Giao dịch điện tử số 20/2023/QH15 và Luật Bảo vệ quyền lợi người tiêu dùng số 19/2023/QH15.',
        ),
        const SizedBox(height: 14),
        _buildSectionTitle('2. Quy chuẩn dành cho Chuyên gia Y tế (eKYC 2 cấp)'),
        _buildParagraph(
          'Bác sĩ tham gia tư vấn phải trải qua thẩm định eKYC sinh trắc học và đối soát '
          'Giấy phép hành nghề y khoa còn hiệu lực theo Luật Khám bệnh, chữa bệnh số 15/2023/QH15. '
          'Chuyên gia cam kết giữ bí mật thông tin người bệnh và không kê đơn thuốc trái quy định.',
        ),
        const SizedBox(height: 14),
        _buildSectionTitle('3. Dịch vụ Tư vấn từ xa & Cuộc gọi Video (ZegoCloud)'),
        _buildParagraph(
          'CareBridge kết nối người dùng với chuyên gia qua tin nhắn và cuộc gọi thoại/video bảo mật. '
          'Cả hai bên có nghĩa vụ ứng xử văn minh, giữ gìn đạo đức y khoa và không phát tán nội dung riêng tư.',
        ),
        const SizedBox(height: 14),
        _buildSectionTitle('4. Trợ lý AI Nurse & Video Chỉnh tư thế (MediaPipe ML)'),
        _buildParagraph(
          '• Trợ lý AI Nurse hỗ trợ tra cứu lịch tiêm chủng, mốc thai kỳ dựa trên tri thức y khoa chuẩn hóa.\n'
          '• Tính năng hướng dẫn tập luyện nhận diện 33 điểm mốc khung xương theo thời gian thực tại bộ nhớ tạm, '
          'cam kết KHÔNG lưu trữ và KHÔNG thu thập video camera thô của người dùng.',
        ),
        const SizedBox(height: 14),
        _buildSectionTitle('5. Nhóm Gia đình, Nút SOS & Phát hiện Ngã'),
        _buildParagraph(
          'Người mẹ có toàn quyền quản trị quyền xem/chỉnh sửa trong Nhóm Chăm sóc Gia đình. '
          'Tính năng cảnh báo SOS và phát hiện té ngã gửi thông báo và tọa độ vị trí GPS đến người thân, '
          'hoạt động phụ thuộc vào kết nối mạng của thiết bị.',
        ),
        const SizedBox(height: 14),
        _buildSectionTitle('6. Luật áp dụng & Giải quyết Tranh chấp'),
        _buildParagraph(
          'Điều khoản được điều chỉnh bởi pháp luật Việt Nam. Mọi tranh chấp trước hết '
          'được hòa giải thương lượng thiện chí, hoặc giải quyết tại Tòa án nhân dân có thẩm quyền.',
        ),
        const SizedBox(height: 20),
      ],
    );
  }

  Widget _buildPrivacyContent() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildNoticeCard(
          icon: Icons.verified_user_rounded,
          color: const Color(0xFF0D9488),
          bgColor: const Color(0xFFF0FDFA),
          title: 'TUÂN THỦ NGHỊ ĐỊNH 13/2023/NĐ-CP & LUẬT BẢO VỆ DỮ LIỆU CÁ NHÂN',
          content:
              'Dữ liệu sức khỏe thai kỳ và trẻ nhỏ thuộc nhóm DỮ LIỆU CÁ NHÂN NHẠY CẢM. '
              'CareBridge chỉ xử lý khi có sự đồng ý minh bạch của bạn và cam kết TUYỆT ĐỐI '
              'không mua bán dữ liệu cho bất kỳ bên thứ ba nào vì mục đích quảng cáo.',
        ),
        const SizedBox(height: 16),
        _buildSectionTitle('1. Danh mục Dữ liệu được Thu thập'),
        _buildParagraph(
          '• Dữ liệu cơ bản: Họ tên, email, số điện thoại, ngày sinh, mối quan hệ gia đình.\n'
          '• Dữ liệu nhạy cảm: Tuần thai, nhật ký cử động thai, chỉ số sinh tồn (vitals), '
          'kết quả sàng lọc trầm cảm sau sinh (EPDS), biểu đồ tăng trưởng chuẩn WHO của bé, '
          'tọa độ GPS khi kích hoạt SOS, và dữ liệu eKYC chuyên gia.',
        ),
        const SizedBox(height: 14),
        _buildSectionTitle('2. Bảo vệ Dữ liệu Cá nhân Trẻ em (Luật Trẻ em 2016)'),
        _buildParagraph(
          'Hồ sơ của trẻ nhỏ (dưới 16 tuổi) chỉ được tạo lập, quản lý và chia sẻ '
          'bởi cha mẹ hoặc người giám hộ hợp pháp. Bạn có quyền xem, chỉnh sửa hoặc xóa '
          'bất kỳ lúc nào.',
        ),
        const SizedBox(height: 14),
        _buildSectionTitle('3. An toàn Dữ liệu Trí tuệ Nhân tạo & Video Stream'),
        _buildParagraph(
          'Dữ liệu trao đổi với AI Nurse được ẩn danh hóa và không dùng để đào tạo các '
          'mô hình AI công cộng. Luồng video phân tích tư thế tập luyện chỉ xử lý tọa độ '
          'cục bộ và tự động giải phóng khỏi RAM ngay khi kết thúc bài tập.',
        ),
        const SizedBox(height: 14),
        _buildSectionTitle('4. Biện pháp Bảo mật Kỹ thuật Đa tầng'),
        _buildParagraph(
          '• Mã hóa đường truyền bằng TLS 1.3 / HTTPS và DTLS cho cuộc gọi ZegoCloud.\n'
          '• Mật khẩu băm một chiều bằng BCrypt, mã hóa cấp trường cho dữ liệu nhạy cảm.\n'
          '• Xác thực hai bước bằng mã OTP và ghi vết nhật ký kiểm toán (audit logs).',
        ),
        const SizedBox(height: 14),
        _buildSectionTitle('5. Mười một (11) Quyền của Chủ thể Dữ liệu'),
        _buildParagraph(
          'Theo Điều 9 NĐ 13/2023/NĐ-CP, bạn có quyền: Được biết, Đồng ý, Truy cập, '
          'Rút lại sự đồng ý, Xóa dữ liệu (Right to be Forgotten), Hạn chế xử lý, Phản đối, '
          'Yêu cầu bồi thường và Khiếu nại.\n\n'
          'Tính năng Xóa tài khoản vĩnh viễn (Delete Account) có sẵn trực tiếp trong ứng dụng '
          'theo chuẩn Apple/Google. Mọi yêu cầu gửi tới privacy@carebridgevn.site sẽ được giải quyết trong vòng 72 giờ.',
        ),
        const SizedBox(height: 20),
      ],
    );
  }

  Widget _buildNoticeCard({
    required IconData icon,
    required Color color,
    required Color bgColor,
    required String title,
    required String content,
  }) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontFamily: 'Lexend',
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: color,
                    letterSpacing: 0.3,
                  ),
                ),
                const SizedBox(height: 5),
                Text(
                  content,
                  style: const TextStyle(
                    fontFamily: 'Lexend',
                    fontSize: 12,
                    height: 1.45,
                    color: AuthPalette.ink,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionTitle(String title) {
    return Text(
      title,
      style: const TextStyle(
        fontFamily: 'Lexend',
        fontSize: 13,
        fontWeight: FontWeight.w700,
        color: AuthPalette.accentDeep,
      ),
    );
  }

  Widget _buildParagraph(String text) {
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Text(
        text,
        style: const TextStyle(
          fontFamily: 'Lexend',
          fontSize: 12.5,
          height: 1.5,
          color: AuthPalette.mutedStrong,
        ),
      ),
    );
  }

  Widget _buildStickyFooter(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
      child: Row(
        children: [
          Expanded(
            child: OutlinedButton(
              style: OutlinedButton.styleFrom(
                foregroundColor: AuthPalette.mutedStrong,
                side: const BorderSide(color: AuthPalette.line),
                padding: const EdgeInsets.symmetric(vertical: 13),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text(
                'Đóng',
                style: TextStyle(
                  fontFamily: 'Lexend',
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 2,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: AuthPalette.accentDeep,
                foregroundColor: Colors.white,
                elevation: 0,
                padding: const EdgeInsets.symmetric(vertical: 13),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onPressed: () => Navigator.of(context).pop(true),
              icon: const Icon(Icons.check_circle_outline_rounded, size: 18),
              label: const Text(
                'Đã đọc & Đồng ý',
                style: TextStyle(
                  fontFamily: 'Lexend',
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
