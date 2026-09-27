import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:untitled/core/network/api_client.dart';
import 'package:untitled/features/baby/models/baby_model.dart';
import 'package:untitled/features/baby/models/milestone_model.dart';
import 'package:untitled/features/baby/screens/record_milestone_screen.dart';
import 'package:untitled/features/baby/services/baby_log_service.dart';
import 'package:untitled/features/baby/services/baby_service.dart';

class MockBabyLogService extends BabyLogService {
  AddMilestoneRequest? lastRequest;
  String? lastBabyId;
  bool shouldThrow = false;
  Object? errorToThrow;

  @override
  Future<Milestone> addMilestone(
    String babyId,
    AddMilestoneRequest request,
  ) async {
    lastBabyId = babyId;
    lastRequest = request;
    if (shouldThrow) {
      throw errorToThrow ??
          ApiException(
            400,
            '{"errorCode":"BABY-065","message":"Achieved date cannot be before baby birth date"}',
          );
    }
    return Milestone(
      id: 'ms-123',
      babyId: babyId,
      milestoneType: request.milestoneType,
      achievedDate: request.achievedDate,
      note: request.note,
    );
  }
}

class MockBabyService extends BabyService {
  final DateTime birthDate;

  MockBabyService({required this.birthDate});

  @override
  Future<BabyProfile> getBabyProfile(String babyId) async {
    return BabyProfile(
      id: babyId,
      nickname: 'Bé Bắp',
      birthDate: birthDate,
      gender: BabyGender.male,
      isActive: true,
    );
  }
}

void main() {
  final testBirthDate = DateTime(2026, 6, 15);

  testWidgets('renders milestone choices and displays birth date hint when provided', (
    tester,
  ) async {
    final logService = MockBabyLogService();

    await tester.pumpWidget(
      MaterialApp(
        home: RecordMilestoneScreen(
          babyId: 'baby-1',
          birthDate: testBirthDate,
          logService: logService,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Mốc phát triển mới'), findsOneWidget);
    expect(find.text('Bé đã đạt được mốc gì?'), findsOneWidget);
    expect(find.text('Lẫy'), findsOneWidget);
    expect(find.text('Bò'), findsOneWidget);
    expect(find.text('Đi'), findsOneWidget);
    expect(find.text('Nói'), findsOneWidget);
    expect(find.text('Mọc răng'), findsOneWidget);
    expect(find.text('Ăn dặm'), findsOneWidget);
    expect(find.text('Mốc khác'), findsOneWidget);

    // Birth date hint is shown
    expect(find.text('Từ ngày sinh: 15/06/2026'), findsOneWidget);
  });

  testWidgets('loads baby birth date from babyService if not passed directly', (
    tester,
  ) async {
    final logService = MockBabyLogService();
    final babyService = MockBabyService(birthDate: testBirthDate);

    await tester.pumpWidget(
      MaterialApp(
        home: RecordMilestoneScreen(
          babyId: 'baby-1',
          logService: logService,
          babyService: babyService,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Từ ngày sinh: 15/06/2026'), findsOneWidget);
  });

  testWidgets('validates required milestone type selection before saving', (
    tester,
  ) async {
    final logService = MockBabyLogService();

    await tester.pumpWidget(
      MaterialApp(
        home: RecordMilestoneScreen(
          babyId: 'baby-1',
          birthDate: testBirthDate,
          logService: logService,
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Tap Save without selecting any milestone chip
    await tester.ensureVisible(find.text('Lưu mốc phát triển'));
    await tester.tap(find.text('Lưu mốc phát triển'));
    await tester.pump();

    expect(find.text('Vui lòng chọn loại mốc phát triển.'), findsOneWidget);
    expect(logService.lastRequest, isNull);
  });

  testWidgets('saves milestone successfully when valid type is selected', (
    tester,
  ) async {
    final logService = MockBabyLogService();

    await tester.pumpWidget(
      MaterialApp(
        home: RecordMilestoneScreen(
          babyId: 'baby-1',
          birthDate: testBirthDate,
          logService: logService,
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Select 'Lẫy'
    await tester.tap(find.text('Lẫy'));
    await tester.pumpAndSettle();

    // Save
    await tester.ensureVisible(find.text('Lưu mốc phát triển'));
    await tester.tap(find.text('Lưu mốc phát triển'));
    await tester.pump();

    expect(logService.lastRequest, isNotNull);
    expect(logService.lastRequest!.milestoneType, MilestoneType.roll);
    expect(logService.lastBabyId, 'baby-1');

    // Wait for success toast duration
    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();
  });

  testWidgets('shows Vietnamese error message when server rejects with BABY-065', (
    tester,
  ) async {
    final logService = MockBabyLogService()
      ..shouldThrow = true
      ..errorToThrow = ApiException(
        400,
        '{"error":"BABY-065","message":"Achieved date cannot be before baby birth date"}',
      );

    await tester.pumpWidget(
      MaterialApp(
        home: RecordMilestoneScreen(
          babyId: 'baby-1',
          birthDate: testBirthDate,
          logService: logService,
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Select 'Bò'
    await tester.tap(find.text('Bò'));
    await tester.pumpAndSettle();

    // Save
    await tester.ensureVisible(find.text('Lưu mốc phát triển'));
    await tester.tap(find.text('Lưu mốc phát triển'));
    await tester.pumpAndSettle();

    expect(find.text('Ngày đạt được không thể trước ngày sinh của bé.'), findsOneWidget);
  });

  testWidgets('date picker does not allow selecting dates before baby birth date', (
    tester,
  ) async {
    // Suppose baby birth date is today - 10 days
    final now = DateTime.now();
    final birth = DateTime(now.year, now.month, now.day).subtract(const Duration(days: 10));

    await tester.pumpWidget(
      MaterialApp(
        home: RecordMilestoneScreen(
          babyId: 'baby-1',
          birthDate: birth,
          logService: MockBabyLogService(),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Tap the date picker trigger
    await tester.tap(find.byIcon(Icons.calendar_today_rounded));
    await tester.pumpAndSettle();

    // The DatePickerDialog is displayed
    expect(find.byType(DatePickerDialog), findsOneWidget);

    final datePicker = tester.widget<DatePickerDialog>(find.byType(DatePickerDialog));
    // Verify firstDate equals baby's birthDate
    expect(
      DateUtils.dateOnly(datePicker.firstDate),
      equals(DateUtils.dateOnly(birth)),
    );
    // Verify lastDate is today
    expect(
      DateUtils.dateOnly(datePicker.lastDate),
      equals(DateUtils.dateOnly(now)),
    );
  });
}
