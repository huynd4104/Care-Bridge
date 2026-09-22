import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:untitled/features/community/models/community_model.dart';
import 'package:untitled/features/community/screens/create_question_screen.dart';
import 'package:untitled/features/community/services/community_service.dart';

class _FakeCommunityService extends CommunityService {
  final List<CommunityTopic> topics;
  Map<String, dynamic>? lastCreatedQuestion;

  _FakeCommunityService({required this.topics});

  @override
  Future<List<CommunityTopic>> getQuestionTopics() async => topics;

  @override
  Future<void> createQuestion({
    required String title,
    required String body,
    required String topicId,
    required String stage,
    required String urgency,
    required bool isAnonymous,
    List<String> imageUrls = const [],
    int? pregnancyWeek,
    int? babyAgeMonths,
  }) async {
    lastCreatedQuestion = {
      'title': title,
      'body': body,
      'topicId': topicId,
      'stage': stage,
      'urgency': urgency,
      'isAnonymous': isAnonymous,
      'imageUrls': imageUrls,
      'pregnancyWeek': pregnancyWeek,
      'babyAgeMonths': babyAgeMonths,
    };
  }
}

void main() {
  final List<CommunityTopic> testTopics = [
    CommunityTopic(
      id: 'topic-1',
      name: 'Dinh dưỡng thai kỳ',
      description: 'Chủ đề dinh dưỡng',
      icon: 'nutrition',
      type: 'TOPIC',
      isHidden: false,
      sortOrder: 1,
    ),
    CommunityTopic(
      id: 'topic-2',
      name: 'Chăm sóc sau sinh',
      description: 'Chủ đề sau sinh',
      icon: 'care',
      type: 'TOPIC',
      isHidden: false,
      sortOrder: 2,
    ),
  ];

  late _FakeCommunityService fakeService;

  setUp(() {
    fakeService = _FakeCommunityService(topics: testTopics);
    CommunityService.instance = fakeService;
  });

  testWidgets(
    'CreateQuestionScreen renders all synchronized sections and components',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1080, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        const MaterialApp(
          home: CreateQuestionScreen(initialTopicId: 'topic-1'),
        ),
      );
      await tester.pumpAndSettle();

      // Verify AppBar
      expect(find.text('Đặt câu hỏi'), findsOneWidget);
      expect(find.widgetWithText(TextButton, 'Đăng'), findsOneWidget);

      // Verify Section labels
      expect(find.text('Tiêu đề câu hỏi'), findsOneWidget);
      expect(find.text('Nội dung'), findsOneWidget);
      expect(find.text('Hình ảnh'), findsOneWidget);
      expect(find.text('Chủ đề'), findsOneWidget);
      expect(find.text('Giai đoạn liên quan'), findsOneWidget);
      expect(find.text('Mức độ ưu tiên'), findsOneWidget);

      // Verify Urgency radio options
      expect(find.text('Không gấp'), findsOneWidget);
      expect(find.text('Bình thường'), findsOneWidget);
      expect(find.text('Khẩn cấp'), findsOneWidget);

      // Verify Anonymous toggle container
      expect(find.text('Đăng ẩn danh'), findsOneWidget);
      expect(find.text('Tên của bạn sẽ bị ẩn'), findsOneWidget);
      expect(find.byIcon(Icons.person_off_outlined), findsOneWidget);
      expect(find.byType(Switch), findsOneWidget);

      // Verify Bottom button
      expect(find.widgetWithText(ElevatedButton, 'Đăng câu hỏi'), findsOneWidget);
    },
  );

  testWidgets('Allows selecting urgency and toggling anonymous', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      const MaterialApp(
        home: CreateQuestionScreen(initialTopicId: 'topic-1'),
      ),
    );
    await tester.pumpAndSettle();

    // Tap 'Khẩn cấp' urgency option
    await tester.tap(find.text('Khẩn cấp'));
    await tester.pumpAndSettle();

    // Toggle anonymous switch
    final switchFinder = find.byType(Switch);
    expect(tester.widget<Switch>(switchFinder).value, isFalse);

    await tester.tap(switchFinder);
    await tester.pumpAndSettle();

    expect(tester.widget<Switch>(switchFinder).value, isTrue);
  });

  testWidgets('Validates short title and body inputs', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      const MaterialApp(
        home: CreateQuestionScreen(initialTopicId: 'topic-1'),
      ),
    );
    await tester.pumpAndSettle();

    // Enter short title
    final titleFinder = find.widgetWithText(TextFormField, 'Nhập tiêu đề câu hỏi...');
    await tester.enterText(titleFinder, 'abc');

    // Enter short body
    final bodyFinder = find.widgetWithText(TextFormField, 'Mô tả chi tiết vấn đề của bạn...');
    await tester.enterText(bodyFinder, 'ngắn');

    // Tap submit button
    await tester.tap(find.widgetWithText(ElevatedButton, 'Đăng câu hỏi'));
    await tester.pumpAndSettle();

    expect(find.text('Tiêu đề cần ít nhất 5 ký tự'), findsOneWidget);
    expect(find.text('Nội dung cần ít nhất 10 ký tự'), findsOneWidget);
    expect(fakeService.lastCreatedQuestion, isNull);
  });

  testWidgets('Submits successfully with valid data via top action button', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: CreateQuestionScreen(initialTopicId: 'topic-1'),
      ),
    );
    await tester.pumpAndSettle();

    // Enter valid title
    final titleFinder = find.widgetWithText(TextFormField, 'Nhập tiêu đề câu hỏi...');
    await tester.enterText(titleFinder, 'Chế độ ăn cho mẹ bầu 3 tháng đầu');

    // Enter valid body
    final bodyFinder = find.widgetWithText(TextFormField, 'Mô tả chi tiết vấn đề của bạn...');
    await tester.enterText(
      bodyFinder,
      'Mình đang mang thai tuần thứ 8, xin hỏi các bác sĩ nên ăn những gì để bé phát triển tốt?',
    );

    // Tap top AppBar 'Đăng' button
    await tester.tap(find.widgetWithText(TextButton, 'Đăng'));
    await tester.pumpAndSettle();

    expect(fakeService.lastCreatedQuestion, isNotNull);
    expect(
      fakeService.lastCreatedQuestion!['title'],
      'Chế độ ăn cho mẹ bầu 3 tháng đầu',
    );
    expect(fakeService.lastCreatedQuestion!['topicId'], 'topic-1');
    expect(fakeService.lastCreatedQuestion!['stage'], 'PREGNANCY');
    expect(fakeService.lastCreatedQuestion!['urgency'], 'NORMAL');
    expect(fakeService.lastCreatedQuestion!['isAnonymous'], isFalse);
  });
}
