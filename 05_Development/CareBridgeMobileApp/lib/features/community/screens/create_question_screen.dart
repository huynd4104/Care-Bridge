import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../../../core/constants/content_stages.dart';
import '../models/community_model.dart';
import '../services/community_service.dart';
import '../widgets/community_image_attachments.dart';

class CreateQuestionScreen extends StatefulWidget {
  final String? initialTopicId;
  final String? initialStage;
  final int? initialPregnancyWeek;
  final int? initialBabyAgeMonths;

  const CreateQuestionScreen({
    super.key,
    this.initialTopicId,
    this.initialStage,
    this.initialPregnancyWeek,
    this.initialBabyAgeMonths,
  });

  @override
  State<CreateQuestionScreen> createState() => _CreateQuestionScreenState();
}

class _CreateQuestionScreenState extends State<CreateQuestionScreen> {
  static const _primary = Color(0xFF845143);
  static const _primaryContainer = Color(0xFFC98C7B);
  static const _canvas = Color(0xFFF6F1EC);
  static const _surface = Colors.white;
  static const _surfaceContainerHigh = Color(0xFFFFE2D9);
  static const _onSurface = Color(0xFF271812);
  static const _onSurfaceVariant = Color(0xFF524440);
  static const _outline = Color(0xFF84736F);
  static const _outlineVariant = Color(0xFFD6C2BD);
  static const _error = Color(0xFFBA1A1A);

  final _formKey = GlobalKey<FormState>();
  final _titleCtrl = TextEditingController();
  final _bodyCtrl = TextEditingController();
  final _imageService = CommunityImageService();
  final List<CommunityImageAttachment> _images = [];

  List<CommunityTopic> _topics = [];
  String? _selectedTopicId;
  late String _stage;
  String _urgency = 'NORMAL';
  bool _isAnonymous = false;
  bool _loadingTopics = false;
  bool _submitting = false;

  static const _urgencyOptions = [
    {'value': 'LOW', 'label': 'Không gấp'},
    {'value': 'NORMAL', 'label': 'Bình thường'},
    {'value': 'URGENT', 'label': 'Khẩn cấp'},
  ];

  @override
  void initState() {
    super.initState();
    _selectedTopicId = widget.initialTopicId;
    _stage = normalizeContentStage(widget.initialStage);
    _loadTopics();
  }

  @override
  void dispose() {
    _titleCtrl.dispose();
    _bodyCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadTopics() async {
    setState(() => _loadingTopics = true);
    try {
      final topics = await CommunityService.instance.getQuestionTopics();
      if (!mounted) return;
      setState(() {
        _topics = topics;
        final selectedStillExists = topics.any(
          (topic) => topic.id == _selectedTopicId,
        );
        if (!selectedStillExists && _selectedTopicId != null) {
          _selectedTopicId = null;
        }
      });
    } catch (error) {
      if (mounted) {
        setState(() {
          _topics = [];
          _selectedTopicId = null;
        });
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Không thể tải chủ đề: $error')));
      }
    } finally {
      if (mounted) setState(() => _loadingTopics = false);
    }
  }

  bool get _hasValidTopicSelection =>
      _selectedTopicId != null &&
      _topics.any((topic) => topic.id == _selectedTopicId);

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate() || !_hasValidTopicSelection) return;
    setState(() => _submitting = true);
    try {
      final imageUrls = await _imageService.uploadAll(
        _images,
        purpose: 'COMMUNITY_QUESTION_IMAGE',
      );
      await CommunityService.instance.createQuestion(
        title: _titleCtrl.text.trim(),
        body: _bodyCtrl.text.trim(),
        topicId: _selectedTopicId!,
        stage: _stage,
        urgency: _urgency,
        isAnonymous: _isAnonymous,
        imageUrls: imageUrls,
        pregnancyWeek: widget.initialPregnancyWeek,
        babyAgeMonths: widget.initialBabyAgeMonths,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Đăng câu hỏi thành công!'),
            backgroundColor: Color(0xFF4CAF50),
          ),
        );
        Navigator.of(context).pop(true);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Thất bại: $e'),
            backgroundColor: _error,
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _pickImage(ImageSource source) async {
    if (_images.length >= communityImageLimit) return;
    try {
      final image = await _imageService.pick(source);
      if (image != null && mounted) setState(() => _images.add(image));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Không thể thêm ảnh: $e')));
      }
    }
  }

  InputDecoration _inputDecoration(String hint) => InputDecoration(
    hintText: hint,
    hintStyle: const TextStyle(color: _outline, fontSize: 14),
    filled: true,
    fillColor: _surface,
    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: _outlineVariant),
    ),
    enabledBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: _outlineVariant),
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: _primaryContainer, width: 1.5),
    ),
    errorBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(12),
      borderSide: const BorderSide(color: _error),
    ),
    counterStyle: const TextStyle(color: _outline, fontSize: 11),
  );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _canvas,
      appBar: AppBar(
        backgroundColor: _canvas,
        elevation: 0,
        shadowColor: Colors.black12,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: _primary),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: const Text(
          'Đặt câu hỏi',
          style: TextStyle(
            color: _primary,
            fontWeight: FontWeight.bold,
            fontSize: 17,
          ),
        ),
        actions: [
          if (_submitting)
            const Center(
              child: Padding(
                padding: EdgeInsets.only(right: 16),
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: _primary,
                  ),
                ),
              ),
            )
          else
            TextButton(
              onPressed: (_loadingTopics || !_hasValidTopicSelection)
                  ? null
                  : _submit,
              child: const Text(
                'Đăng',
                style: TextStyle(
                  color: _primary,
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
            ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            // Title field
            const _SectionLabel('Tiêu đề câu hỏi'),
            const SizedBox(height: 8),
            TextFormField(
              controller: _titleCtrl,
              maxLength: 255,
              decoration: _inputDecoration('Nhập tiêu đề câu hỏi...'),
              style: const TextStyle(fontSize: 15, color: _onSurface),
              validator: (v) {
                if (v == null || v.trim().length < 5) {
                  return 'Tiêu đề cần ít nhất 5 ký tự';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),

            // Body field
            const _SectionLabel('Nội dung'),
            const SizedBox(height: 8),
            TextFormField(
              controller: _bodyCtrl,
              maxLength: 5000,
              maxLines: 8,
              decoration: _inputDecoration('Mô tả chi tiết vấn đề của bạn...'),
              style: const TextStyle(fontSize: 15, color: _onSurface),
              validator: (v) {
                if (v == null || v.trim().length < 10) {
                  return 'Nội dung cần ít nhất 10 ký tự';
                }
                return null;
              },
            ),
            const SizedBox(height: 16),

            // Image picker
            const _SectionLabel('Hình ảnh'),
            const SizedBox(height: 8),
            CommunityImagePickerField(
              images: _images,
              enabled: !_submitting,
              onCamera: () => _pickImage(ImageSource.camera),
              onGallery: () => _pickImage(ImageSource.gallery),
              onRemove: (index) => setState(() => _images.removeAt(index)),
            ),
            const SizedBox(height: 16),

            // Topic field
            const _SectionLabel('Chủ đề'),
            const SizedBox(height: 8),
            if (_loadingTopics)
              const Center(child: CircularProgressIndicator(color: _primary))
            else if (_topics.isEmpty)
              Container(
                padding: const EdgeInsets.symmetric(
                  vertical: 12,
                  horizontal: 16,
                ),
                decoration: BoxDecoration(
                  color: _surface,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.orange.shade200),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.info_outline,
                      color: Colors.orange.shade700,
                      size: 18,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Chưa có chủ đề nào. Quản trị viên cần tạo chủ đề trước khi bạn có thể đặt câu hỏi.',
                        style: TextStyle(
                          fontSize: 13,
                          color: Colors.orange.shade800,
                        ),
                      ),
                    ),
                  ],
                ),
              )
            else
              DropdownButtonFormField<String>(
                initialValue: _selectedTopicId,
                decoration: _inputDecoration('Chọn chủ đề'),
                items: _topics
                    .map(
                      (topic) => DropdownMenuItem<String>(
                        value: topic.id,
                        child: Text(topic.name),
                      ),
                    )
                    .toList(),
                validator: (value) => value == null || value.isEmpty
                    ? 'Vui lòng chọn chủ đề'
                    : null,
                onChanged: (value) => setState(() => _selectedTopicId = value),
              ),
            const SizedBox(height: 16),

            // Stage field
            const _SectionLabel('Giai đoạn liên quan'),
            const SizedBox(height: 4),
            const Text(
              'Chọn giai đoạn của mẹ hoặc em bé được nhắc đến.',
              style: TextStyle(color: _onSurfaceVariant, fontSize: 12),
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              initialValue: _stage,
              decoration: _inputDecoration('Chọn giai đoạn'),
              items: contentStageOptions
                  .map(
                    (stage) => DropdownMenuItem(
                      value: stage.value,
                      child: Text(stage.label),
                    ),
                  )
                  .toList(growable: false),
              onChanged: (value) {
                if (value != null) setState(() => _stage = value);
              },
            ),
            const SizedBox(height: 16),

            // Urgency picker
            const _SectionLabel('Mức độ ưu tiên'),
            const SizedBox(height: 8),
            Material(
              color: _surface,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
                side: const BorderSide(color: _outlineVariant),
              ),
              clipBehavior: Clip.antiAlias,
              child: RadioGroup<String>(
                groupValue: _urgency,
                onChanged: (value) {
                  if (value != null) {
                    setState(() => _urgency = value);
                  }
                },
                child: Column(
                  children: _urgencyOptions.map((opt) {
                    final selected = _urgency == opt['value'];
                    return RadioListTile<String>(
                      value: opt['value']!,
                      title: Text(
                        opt['label']!,
                        style: TextStyle(
                          fontSize: 14,
                          color: selected ? _primary : _onSurface,
                          fontWeight: selected
                              ? FontWeight.w600
                              : FontWeight.normal,
                        ),
                      ),
                      activeColor: _primary,
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 12,
                      ),
                      dense: true,
                    );
                  }).toList(),
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Anonymous toggle
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: _surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: _outlineVariant),
              ),
              child: Row(
                children: [
                  Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: _surfaceContainerHigh,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(
                      Icons.person_off_outlined,
                      color: _primary,
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Đăng ẩn danh',
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: _onSurface,
                          ),
                        ),
                        Text(
                          'Tên của bạn sẽ bị ẩn',
                          style: TextStyle(
                            fontSize: 12,
                            color: _onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Switch(
                    value: _isAnonymous,
                    onChanged: (v) => setState(() => _isAnonymous = v),
                    activeThumbColor: _primary,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Submit button
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: _primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: const StadiumBorder(),
                  textStyle: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                onPressed: (_submitting || !_hasValidTopicSelection)
                    ? null
                    : _submit,
                child: _submitting
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('Đăng câu hỏi'),
              ),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel(this.text);

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        color: Color(0xFF524440),
        letterSpacing: 0.2,
      ),
    );
  }
}
