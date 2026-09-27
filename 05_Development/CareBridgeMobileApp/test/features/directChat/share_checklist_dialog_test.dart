import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:untitled/features/directChat/widgets/share_checklist_dialog.dart';
import 'package:untitled/features/directChat/widgets/checklist_message_card.dart';
import 'package:untitled/features/reminder/models/reminder_model.dart';
import 'package:untitled/features/reminder/models/today_task_model.dart';

void main() {
  group('ShareChecklistDialog Tests - Default Send All Without Selection', () {
    testWidgets('renders dialog and send button sends all items by default without checkboxes', (
      tester,
    ) async {
      ChecklistShareData? result;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () async {
                  result = await ShareChecklistDialog.show(context);
                },
                child: const Text('Open Dialog'),
              ),
            ),
          ),
        ),
      );

      // Open dialog
      await tester.tap(find.text('Open Dialog'));
      await tester.pumpAndSettle();

      // Verify title & default send all scope banner
      expect(find.text('Chia sẻ việc cần làm'), findsOneWidget);
      expect(find.textContaining('Mặc định gửi toàn bộ'), findsAtLeastNWidgets(1));

      // Verify no checkboxes exist for item selection
      expect(find.byType(Checkbox), findsNothing);
      expect(find.byType(CheckboxListTile), findsNothing);

      // Verify "Bỏ chọn hết" or "Chọn tất cả" action bar is removed
      expect(find.text('Bỏ chọn hết'), findsNothing);
      expect(find.text('Chọn tất cả'), findsNothing);

      // Verify TabBar exists and has 3 tabs
      expect(find.byType(TabBar), findsOneWidget);
      expect(find.byType(Tab), findsNWidgets(3));

      // Tap send button
      final sendBtn = find.byKey(const Key('share-all-checklist-btn'));
      expect(sendBtn, findsOneWidget);
      await tester.tap(sendBtn);
      await tester.pumpAndSettle();

      // Verify dialog popped
      expect(find.text('Chia sẻ việc cần làm'), findsNothing);
      expect(result, isNotNull);
      expect(result!.totalCount, greaterThan(0));
    });

    testWidgets('renders baby care checklists and sends baby checklist data when stage is BABY_CARE', (
      tester,
    ) async {
      tester.view.devicePixelRatio = 1.0;
      tester.view.physicalSize = const Size(800, 1200);
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      ChecklistShareData? result;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () async {
                  result = await ShareChecklistDialog.show(
                    context,
                    initialStage: 'BABY_CARE',
                    initialBabyName: 'Bé Bơ',
                  );
                },
                child: const Text('Open Baby Dialog'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Open Baby Dialog'));
      await tester.pumpAndSettle();

      // Verify stage label
      expect(find.textContaining('Chăm sóc bé'), findsAtLeastNWidgets(1));

      // Verify baby care items rendered with baby badge
      expect(find.textContaining('Dành cho bé'), findsWidgets);
      expect(find.text('Khám và theo dõi sơ sinh'), findsOneWidget);

      // Tap send
      final sendBtn = find.byKey(const Key('share-all-checklist-btn'));
      await tester.tap(sendBtn);
      await tester.pumpAndSettle();

      expect(result, isNotNull);
      expect(result!.stage, 'BABY_CARE');
      expect(result!.title, contains('bé'));
      expect(
        result!.currentItems.any((i) => i.text == 'Khám và theo dõi sơ sinh'),
        isTrue,
      );
    });

    testWidgets('renders mother and baby items with target filter chips for postpartum with baby', (
      tester,
    ) async {
      tester.view.devicePixelRatio = 1.0;
      tester.view.physicalSize = const Size(800, 1200);
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      ChecklistShareData? result;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () async {
                  result = await ShareChecklistDialog.show(
                    context,
                    initialStage: 'POSTPARTUM',
                    initialBabyName: 'Bé Bơ',
                  );
                },
                child: const Text('Open Postpartum Dialog'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Open Postpartum Dialog'));
      await tester.pumpAndSettle();

      // Verify both mother and baby items exist -> target chips shown
      expect(find.textContaining('Của mẹ'), findsAtLeastNWidgets(1));
      expect(find.textContaining('Dành cho bé'), findsAtLeastNWidgets(1));

      // Filter to only baby items
      final babyChip = find.textContaining('Dành cho bé').first;
      await tester.tap(babyChip);
      await tester.pumpAndSettle();

      // Baby item is shown
      expect(find.text('Khám và theo dõi sơ sinh'), findsOneWidget);

      // Filter to only mother items
      final motherChip = find.textContaining('Của mẹ').first;
      await tester.tap(motherChip);
      await tester.pumpAndSettle();

      // Baby item is filtered out
      expect(find.text('Khám và theo dõi sơ sinh'), findsNothing);

      // Switch back to all and send
      final allChip = find.textContaining('Tất cả').first;
      await tester.tap(allChip);
      await tester.pumpAndSettle();

      final sendBtn = find.byKey(const Key('share-all-checklist-btn'));
      await tester.tap(sendBtn);
      await tester.pumpAndSettle();

      expect(result, isNotNull);
      expect(result!.title, 'Danh sách việc cần làm (Mẹ & Bé)');
      expect(
        result!.currentItems.any((i) => i.text == 'Khám và theo dõi sơ sinh'),
        isTrue,
      );
    });

    testWidgets('sends only mother items when "Của mẹ" target is selected', (
      tester,
    ) async {
      tester.view.devicePixelRatio = 1.0;
      tester.view.physicalSize = const Size(800, 1200);
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      ChecklistShareData? result;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () async {
                  result = await ShareChecklistDialog.show(
                    context,
                    initialStage: 'POSTPARTUM',
                    initialBabyName: 'Bé Bơ',
                  );
                },
                child: const Text('Open Postpartum Dialog'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Open Postpartum Dialog'));
      await tester.pumpAndSettle();

      // Tap on "Của mẹ" target chip
      final motherChip = find.textContaining('Của mẹ').first;
      await tester.tap(motherChip);
      await tester.pumpAndSettle();

      // Verify send button text updated to Mother checklist
      expect(find.textContaining('Chia sẻ việc của mẹ'), findsOneWidget);

      // Tap send button
      final sendBtn = find.byKey(const Key('share-all-checklist-btn'));
      await tester.tap(sendBtn);
      await tester.pumpAndSettle();

      expect(result, isNotNull);
      expect(result!.title, 'Lộ trình chăm sóc sau sinh');
      // No baby item should be in currentItems
      expect(
        result!.currentItems.any((i) => i.text == 'Khám và theo dõi sơ sinh'),
        isFalse,
      );
      // Only mother items exist
      expect(
        result!.currentItems.every((i) => !(i.category?.contains('bé') ?? false)),
        isTrue,
      );
    });

    testWidgets('sends only baby items when "Dành cho bé" target is selected', (
      tester,
    ) async {
      tester.view.devicePixelRatio = 1.0;
      tester.view.physicalSize = const Size(800, 1200);
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      ChecklistShareData? result;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () async {
                  result = await ShareChecklistDialog.show(
                    context,
                    initialStage: 'POSTPARTUM',
                    initialBabyName: 'Bé Bơ',
                  );
                },
                child: const Text('Open Postpartum Dialog'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Open Postpartum Dialog'));
      await tester.pumpAndSettle();

      // Tap on "Dành cho bé" target chip
      final babyChip = find.textContaining('Dành cho bé').first;
      await tester.tap(babyChip);
      await tester.pumpAndSettle();

      // Verify send button text updated to Baby checklist
      expect(find.textContaining('Chia sẻ việc chăm sóc bé'), findsOneWidget);

      // Tap send button
      final sendBtn = find.byKey(const Key('share-all-checklist-btn'));
      await tester.tap(sendBtn);
      await tester.pumpAndSettle();

      expect(result, isNotNull);
      expect(result!.title, 'Danh sách việc chăm sóc bé');
      expect(result!.stage, 'BABY_CARE');
      expect(result!.stageLabel, 'Chăm sóc bé');
      // Baby item is present
      expect(
        result!.currentItems.any((i) => i.text == 'Khám và theo dõi sơ sinh'),
        isTrue,
      );
    });

    testWidgets('pregnant mother at week 13 with baby profile retains current pregnancy tasks under "Của mẹ"', (
      tester,
    ) async {
      tester.view.devicePixelRatio = 1.0;
      tester.view.physicalSize = const Size(800, 1200);
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      ChecklistShareData? result;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () async {
                  result = await ShareChecklistDialog.show(
                    context,
                    initialStage: 'PREGNANCY',
                    initialGestationalWeek: 13,
                    initialBabyName: 'Bé Miu',
                  );
                },
                child: const Text('Open Pregnancy Dialog'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Open Pregnancy Dialog'));
      await tester.pumpAndSettle();

      // Tap on "Của mẹ" target chip
      final motherChip = find.textContaining('Của mẹ').first;
      await tester.tap(motherChip);
      await tester.pumpAndSettle();

      // Verify "Hiện tại" tab has tasks (e.g. Hiện tại (8)), NOT Hiện tại (0)
      expect(find.text('Hiện tại (0)'), findsNothing);

      // Verify pregnancy task is displayed
      expect(find.text('Đi khám thai lần đầu'), findsOneWidget);

      // Tap send
      final sendBtn = find.byKey(const Key('share-all-checklist-btn'));
      await tester.tap(sendBtn);
      await tester.pumpAndSettle();

      expect(result, isNotNull);
      expect(result!.currentItems.isNotEmpty, isTrue);
      expect(
        result!.currentItems.any((i) => i.text == 'Đi khám thai lần đầu'),
        isTrue,
      );
      // All items in currentItems should be mother tasks, not baby tasks
      expect(
        result!.currentItems.every((i) => !(i.category?.contains('bé') ?? false)),
        isTrue,
      );
    });
  });

  group('ShareChecklistDialog - khớp với "Gợi ý CareBridge" của mẹ', () {
    TodayTask task(
      String id,
      String title, {
      TodayTaskKind kind = TodayTaskKind.checklist,
      TodayTaskOrigin origin = TodayTaskOrigin.systemTemplate,
      bool completed = false,
      TodayChecklistStage stage = TodayChecklistStage.pregnancy,
      String? careContextType,
      String? careContextLabel,
    }) => TodayTask(
      id: id,
      kind: kind,
      sourceType: kind == TodayTaskKind.checklist
          ? TodayTaskSourceType.checklist
          : TodayTaskSourceType.reminder,
      type: ReminderType.other,
      title: title,
      status: ReminderStatus.pending,
      taskStatus: completed ? TodayTaskStatus.completed : TodayTaskStatus.pending,
      priority: 1,
      target: TodayTaskTarget.unknown,
      origin: origin,
      bucket: TodayTimeBucket.today,
      stage: stage,
      careContextType: careContextType,
      careContextLabel: careContextLabel,
      allowedActions: const {TodayTaskAction.complete},
    );

    // 8 gợi ý CareBridge (3 đã xong, 1 việc của bé, 1 việc quá hạn), cộng việc cá nhân và
    // việc nhắc lịch — những thứ mẹ không thấy trong tab "Gợi ý CareBridge".
    final suggestionTitles = [
      'Đi khám thai lần đầu',
      'Uống axit folic mỗi ngày',
      'Ăn đủ bữa, chia nhỏ bữa',
      'Theo dõi cân nặng',
      'Uống đủ nước',
      'Ngủ đủ giấc',
      'Đi bộ nhẹ nhàng 15 phút',
      'Chuẩn bị đồ sơ sinh cho bé',
    ];
    TodayTasksSnapshot snapshot() => TodayTasksSnapshot(
      asOf: DateTime(2026, 9, 27),
      zoneId: 'Asia/Ho_Chi_Minh',
      horizonDays: 7,
      correlationId: 'test',
      sections: TodayTaskSections(
        overdue: [task('s1', suggestionTitles[0], completed: true)],
        today: [
          task('s2', suggestionTitles[1], completed: true),
          task('s3', suggestionTitles[2], completed: true),
          task('s4', suggestionTitles[3]),
          task('s5', suggestionTitles[4]),
          task('s6', suggestionTitles[5]),
          task('s7', suggestionTitles[6]),
          task(
            's8',
            suggestionTitles[7],
            stage: TodayChecklistStage.babyCare,
            careContextType: 'BABY',
            careContextLabel: 'Bé Na',
          ),
          task(
            'u1',
            'Việc cá nhân của mẹ',
            origin: TodayTaskOrigin.userCreated,
            completed: true,
          ),
          task(
            'r1',
            'Nhắc uống thuốc sắt',
            kind: TodayTaskKind.reminder,
            origin: TodayTaskOrigin.unknown,
            completed: true,
          ),
        ],
        upcoming: const [],
        unscheduled: const [],
      ),
    );

    Future<ChecklistShareData?> openAndSend(
      WidgetTester tester,
      Future<TodayTasksSnapshot> Function() loader,
    ) async {
      tester.view.devicePixelRatio = 1.0;
      tester.view.physicalSize = const Size(800, 1200);
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      ChecklistShareData? result;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () async {
                  result = await ShareChecklistDialog.show(
                    context,
                    initialStage: 'PREGNANCY',
                    initialGestationalWeek: 13,
                    todayTasksLoader: loader,
                  );
                },
                child: const Text('Open'),
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();

      expect(
        find.text('Chia sẻ việc cần làm tuần này (8 việc)'),
        findsOneWidget,
      );
      await tester.tap(find.byKey(const Key('share-all-checklist-btn')));
      await tester.pumpAndSettle();
      return result;
    }

    testWidgets('chia sẻ đúng 8 việc gợi ý, 3 việc đã xong như mẹ đang thấy', (
      tester,
    ) async {
      final result = await openAndSend(tester, () async => snapshot());

      expect(result, isNotNull);
      expect(result!.totalCount, 8);
      expect(result.completedCount, 3);
      expect(result.progressPercent, 38);
      expect(result.historyItems, isEmpty);
      expect(result.futureItems, isEmpty);
      expect(
        result.currentItems.map((i) => i.text).toSet(),
        suggestionTitles.toSet(),
      );
      expect(
        result.currentItems.where((i) => i.completed).map((i) => i.text),
        unorderedEquals(suggestionTitles.take(3)),
      );
    });

    testWidgets('payload sau khi serialize vẫn giữ 8 việc / 3 đã xong cho chuyên gia', (
      tester,
    ) async {
      final result = await openAndSend(tester, () async => snapshot());
      final parsed = ChecklistShareData.parse(result!.serialize());

      expect(parsed, isNotNull);
      expect(parsed!.allItems.length, 8);
      expect(parsed.totalCount, 8);
      expect(parsed.completedCount, 3);
      expect(parsed.allItems.where((i) => i.completed).length, 3);
    });

    testWidgets('snapshot hôm nay trống thì không gộp mẫu lộ trình vào "Hiện tại"', (
      tester,
    ) async {
      tester.view.devicePixelRatio = 1.0;
      tester.view.physicalSize = const Size(800, 1200);
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () => ShareChecklistDialog.show(
                  context,
                  initialStage: 'PREGNANCY',
                  initialGestationalWeek: 13,
                  todayTasksLoader: () async => TodayTasksSnapshot(
                    asOf: DateTime(2026, 9, 27),
                    zoneId: 'Asia/Ho_Chi_Minh',
                    horizonDays: 7,
                    correlationId: 'test',
                    sections: const TodayTaskSections(
                      overdue: [],
                      today: [],
                      upcoming: [],
                      unscheduled: [],
                    ),
                  ),
                ),
                child: const Text('Open'),
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();

      expect(find.text('Hiện tại (0)'), findsOneWidget);
      expect(find.text('Đi khám thai lần đầu'), findsNothing);
    });
  });

  group('ChecklistMessageCard Tests - Baby Badge Rendering', () {
    testWidgets('renders baby badge on baby items in message card', (
      tester,
    ) async {
      tester.view.devicePixelRatio = 1.0;
      tester.view.physicalSize = const Size(800, 1200);
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final data = ChecklistShareData(
        title: 'Danh sách việc cần làm (Mẹ & Bé)',
        stage: 'POSTPARTUM',
        stageLabel: 'Sau sinh & Chăm bé',
        completedCount: 1,
        totalCount: 2,
        progressPercent: 50,
        currentItems: const [
          ChecklistItemShareData(
            text: 'Đánh giá tâm trạng & sàng lọc trầm cảm sau sinh',
            completed: true,
            category: 'Chăm sóc sau sinh',
            timeLabel: 'Sau sinh',
          ),
          ChecklistItemShareData(
            text: 'Khám và theo dõi sơ sinh',
            completed: false,
            category: 'Chăm sóc bé',
            timeLabel: 'Bé · Sơ sinh',
          ),
        ],
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ChecklistMessageCard(
              data: data,
              isOwnMessage: true,
            ),
          ),
        ),
      );

      await tester.pumpAndSettle();

      // Verify card renders title
      expect(find.text('Danh sách việc cần làm (Mẹ & Bé)'), findsOneWidget);

      // Verify baby badge on message card preview
      expect(find.text('👶 Cho bé'), findsOneWidget);
      expect(find.text('Khám và theo dõi sơ sinh'), findsOneWidget);

      // Tap on 'Xem Lịch sử & Tương lai' to open full detail modal
      await tester.tap(find.text('Xem Lịch sử & Tương lai'));
      await tester.pumpAndSettle();

      // In detail modal, verify baby badge is displayed
      expect(find.text('Dành cho bé'), findsOneWidget);
      expect(find.text('Khám và theo dõi sơ sinh'), findsWidgets);
    });
  });
}
