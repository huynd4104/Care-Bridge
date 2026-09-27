import 'package:untitled/features/reminder/services/plan_disclaimer_storage.dart';
import 'package:untitled/features/reminder/widgets/plan_disclaimer_banner.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class _MemoryDisclaimerStorage implements PlanDisclaimerStorage {
  _MemoryDisclaimerStorage({this.acknowledged = false});

  bool acknowledged;

  @override
  Future<bool> isAcknowledged() async => acknowledged;

  @override
  Future<void> markAcknowledged() async => acknowledged = true;
}

Future<void> _pump(WidgetTester tester, PlanDisclaimerStorage storage) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(body: PlanDisclaimerBanner(storage: storage)),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('shows disclaimer until acknowledged', (tester) async {
    await _pump(tester, _MemoryDisclaimerStorage());

    expect(find.byKey(const Key('plan-disclaimer-banner')), findsOneWidget);
    expect(find.text(planDisclaimerMessage), findsOneWidget);
    expect(find.text('Đã hiểu'), findsOneWidget);
  });

  testWidgets('cancel in confirm dialog keeps disclaimer visible', (
    tester,
  ) async {
    final storage = _MemoryDisclaimerStorage();
    await _pump(tester, storage);

    await tester.tap(find.byKey(const Key('plan-disclaimer-ack-button')));
    await tester.pumpAndSettle();
    expect(
      find.byKey(const Key('plan-disclaimer-confirm-dialog')),
      findsOneWidget,
    );

    await tester.tap(find.byKey(const Key('plan-disclaimer-cancel')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('plan-disclaimer-banner')), findsOneWidget);
    expect(storage.acknowledged, isFalse);
  });

  testWidgets('confirm hides disclaimer and persists acknowledgement', (
    tester,
  ) async {
    final storage = _MemoryDisclaimerStorage();
    await _pump(tester, storage);

    await tester.tap(find.byKey(const Key('plan-disclaimer-ack-button')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('plan-disclaimer-confirm')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('plan-disclaimer-banner')), findsNothing);
    expect(storage.acknowledged, isTrue);
  });

  testWidgets('stays hidden when previously acknowledged', (tester) async {
    await _pump(tester, _MemoryDisclaimerStorage(acknowledged: true));

    expect(find.byKey(const Key('plan-disclaimer-banner')), findsNothing);
  });
}
