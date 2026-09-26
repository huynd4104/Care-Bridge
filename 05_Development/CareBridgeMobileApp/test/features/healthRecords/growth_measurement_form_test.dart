import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:untitled/core/network/api_client.dart';
import 'package:untitled/features/baby/models/baby_model.dart';
import 'package:untitled/features/baby/services/baby_service.dart';
import 'package:untitled/features/healthRecords/models/growth_measurement_model.dart';
import 'package:untitled/features/healthRecords/screens/growth_measurement_form_screen.dart';
import 'package:untitled/features/healthRecords/services/growth_measurement_service.dart';

class _FakeGrowthMeasurementService extends GrowthMeasurementService {
  Map<String, dynamic>? addedPayload;
  Map<String, dynamic>? updatedPayload;
  String? updatedId;
  bool fail = false;

  @override
  Future<void> addGrowthMeasurement(
    String babyId,
    Map<String, dynamic> payload,
  ) async {
    if (fail) throw StateError('offline');
    addedPayload = {'babyId': babyId, ...payload};
  }

  @override
  Future<void> updateGrowthMeasurement(
    String babyId,
    String measurementId,
    Map<String, dynamic> payload,
  ) async {
    if (fail) throw StateError('offline');
    updatedId = measurementId;
    updatedPayload = {'babyId': babyId, ...payload};
  }
}

class _FakeBabyService extends BabyService {
  final BabyProfile? profile;
  bool throwError = false;

  _FakeBabyService({this.profile});

  @override
  Future<BabyProfile> getBabyProfile(String babyId) async {
    if (throwError) throw StateError('offline');
    return profile ??
        BabyProfile(
          id: babyId,
          nickname: 'Bé Bi',
          birthDate: DateTime(2026, 1, 1),
          gender: BabyGender.male,
          isActive: true,
        );
  }
}

GrowthMeasurement _measurement() => GrowthMeasurement(
  id: 'growth-1',
  measuredAt: DateTime(2026, 7, 14),
  weightKg: 6.1,
  heightCm: 61.5,
  recordedBy: 'mother-1',
  sourceType: 'CLINIC',
  note: 'Before edit',
);

GrowthMeasurement _measurementWithoutNote() => GrowthMeasurement(
  id: 'growth-2',
  measuredAt: DateTime(2026, 7, 14),
  weightKg: 6.1,
  recordedBy: 'mother-1',
  sourceType: 'CLINIC',
);

Future<void> _pumpForm(
  WidgetTester tester, {
  GrowthMeasurementService? service,
  BabyService? babyService,
  DateTime? birthDate,
  Future<void> Function(String babyId, Map<String, dynamic> payload)? onAdd,
  Future<void> Function(
    String babyId,
    String measurementId,
    Map<String, dynamic> payload,
  )?
  onUpdate,
  GrowthMeasurement? measurement,
}) async {
  // The form is taller than the 800x600 default test surface, which pushes the save button
  // outside the render tree and makes every tap() miss. Use a phone-sized viewport instead.
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: GrowthMeasurementFormScreen(
        babyId: 'baby-1',
        measurement: measurement,
        service: service,
        babyService: babyService,
        birthDate: birthDate,
        onAdd: onAdd,
        onUpdate: onUpdate,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('valid add submits the selected baby and measurement fields', (
    tester,
  ) async {
    String? babyId;
    Map<String, dynamic>? payload;
    await _pumpForm(
      tester,
      onAdd: (id, body) async {
        babyId = id;
        payload = body;
      },
    );

    await tester.enterText(find.byKey(const Key('growth-form-weight')), '6.2');
    await tester.tap(find.byKey(const Key('growth-form-save')));
    await tester.pumpAndSettle();

    expect(babyId, 'baby-1');
    expect(payload?['weightKg'], 6.2);
    expect(payload?['sourceType'], 'HOME_SCALE');
    expect(payload?['measuredDate'], matches(RegExp(r'^\d{4}-\d{2}-\d{2}$')));
  });

  testWidgets('edit submits a PATCH payload for the existing measurement', (
    tester,
  ) async {
    String? babyId;
    String? measurementId;
    Map<String, dynamic>? payload;
    await _pumpForm(
      tester,
      measurement: _measurement(),
      onUpdate: (id, recordId, body) async {
        babyId = id;
        measurementId = recordId;
        payload = body;
      },
    );

    await tester.enterText(find.byKey(const Key('growth-form-weight')), '6.3');
    await tester.tap(find.byKey(const Key('growth-form-save')));
    await tester.pumpAndSettle();

    expect(measurementId, 'growth-1');
    expect(babyId, 'baby-1');
    expect(payload?['weightKg'], 6.3);
    expect(payload?['heightCm'], 61.5);
    expect(payload?['sourceType'], 'CLINIC');
  });

  testWidgets('empty metrics are rejected without a request', (tester) async {
    final service = _FakeGrowthMeasurementService();
    await _pumpForm(tester, service: service);

    await tester.tap(find.byKey(const Key('growth-form-save')));
    await tester.pump();

    expect(find.byKey(const Key('growth-form-error')), findsOneWidget);
    expect(service.addedPayload, isNull);
  });

  testWidgets(
    'negative and non-finite metrics are rejected without a request',
    (tester) async {
      final service = _FakeGrowthMeasurementService();
      await _pumpForm(tester, service: service);

      await tester.enterText(find.byKey(const Key('growth-form-weight')), '-1');
      await tester.tap(find.byKey(const Key('growth-form-save')));
      await tester.pump();
      expect(find.byKey(const Key('growth-form-error')), findsOneWidget);
      expect(service.addedPayload, isNull);

      await tester.enterText(
        find.byKey(const Key('growth-form-weight')),
        'NaN',
      );
      await tester.tap(find.byKey(const Key('growth-form-save')));
      await tester.pump();
      expect(find.byKey(const Key('growth-form-error')), findsOneWidget);
      expect(service.addedPayload, isNull);
    },
  );

  testWidgets(
    'zero metrics are rejected without a request with clear message',
    (tester) async {
      final service = _FakeGrowthMeasurementService();
      await _pumpForm(tester, service: service);

      await tester.enterText(find.byKey(const Key('growth-form-weight')), '0');
      await tester.tap(find.byKey(const Key('growth-form-save')));
      await tester.pump();
      expect(find.byKey(const Key('growth-form-error')), findsOneWidget);
      expect(find.text('Số đo phải lớn hơn 0.'), findsOneWidget);
      expect(service.addedPayload, isNull);

      await tester.enterText(
        find.byKey(const Key('growth-form-height')),
        '0.0',
      );
      await tester.enterText(
        find.byKey(const Key('growth-form-head')),
        '0',
      );
      await tester.tap(find.byKey(const Key('growth-form-save')));
      await tester.pump();
      expect(find.byKey(const Key('growth-form-error')), findsOneWidget);
      expect(find.text('Số đo phải lớn hơn 0.'), findsOneWidget);
      expect(service.addedPayload, isNull);
    },
  );

  testWidgets(
    'new record does not show source field and supplies default sourceType',
    (tester) async {
      final service = _FakeGrowthMeasurementService();
      await _pumpForm(tester, service: service);

      expect(find.byKey(const Key('growth-form-source')), findsNothing);
      await tester.enterText(
        find.byKey(const Key('growth-form-weight')),
        '6.2',
      );
      await tester.tap(find.byKey(const Key('growth-form-save')));
      await tester.pumpAndSettle();

      expect(service.addedPayload, isNotNull);
      expect(service.addedPayload?['sourceType'], isNotEmpty);
    },
  );

  testWidgets('editing cannot silently clear an existing metric', (
    tester,
  ) async {
    final service = _FakeGrowthMeasurementService();
    await _pumpForm(tester, service: service, measurement: _measurement());

    await tester.enterText(find.byKey(const Key('growth-form-weight')), '');
    await tester.tap(find.byKey(const Key('growth-form-save')));
    await tester.pump();

    expect(find.byKey(const Key('growth-form-error')), findsOneWidget);
    expect(service.updatedPayload, isNull);
  });

  testWidgets('edit preserves a null note when it is unchanged', (
    tester,
  ) async {
    final service = _FakeGrowthMeasurementService();
    await _pumpForm(
      tester,
      service: service,
      measurement: _measurementWithoutNote(),
    );

    await tester.tap(find.byKey(const Key('growth-form-save')));
    await tester.pumpAndSettle();

    expect(service.updatedPayload, isNotNull);
    expect(service.updatedPayload!.containsKey('note'), isFalse);
  });

  // The counterpart of the case above: skipping an untouched empty note must not also swallow a
  // deliberate clear, otherwise the note could never be removed once written.
  testWidgets('edit sends an empty note when the user clears an existing one', (
    tester,
  ) async {
    final service = _FakeGrowthMeasurementService();
    await _pumpForm(tester, service: service, measurement: _measurement());

    await tester.enterText(find.byKey(const Key('growth-form-note')), '');
    await tester.tap(find.byKey(const Key('growth-form-save')));
    await tester.pumpAndSettle();

    expect(service.updatedPayload, isNotNull);
    expect(service.updatedPayload!['note'], '');
  });

  testWidgets('edit keeps an unchanged non-empty note out of the payload', (
    tester,
  ) async {
    final service = _FakeGrowthMeasurementService();
    await _pumpForm(tester, service: service, measurement: _measurement());

    await tester.tap(find.byKey(const Key('growth-form-save')));
    await tester.pumpAndSettle();

    expect(service.updatedPayload, isNotNull);
    expect(service.updatedPayload!.containsKey('note'), isFalse);
  });

  testWidgets('failed save keeps the form open and preserves entered values', (
    tester,
  ) async {
    final service = _FakeGrowthMeasurementService()..fail = true;
    await _pumpForm(tester, service: service);

    await tester.enterText(find.byKey(const Key('growth-form-weight')), '6.2');
    await tester.tap(find.byKey(const Key('growth-form-save')));
    await tester.pumpAndSettle();

    expect(
      find.byKey(const Key('growth-measurement-form-screen')),
      findsOneWidget,
    );
    expect(find.byKey(const Key('growth-form-error')), findsOneWidget);
    expect(find.text('6.2'), findsOneWidget);
  });

  testWidgets('specific server error message is displayed on save failure', (
    tester,
  ) async {
    final service = _FakeGrowthMeasurementService();
    await _pumpForm(
      tester,
      service: service,
      onAdd: (id, body) async {
        throw ApiException(
          400,
          '{"code":"BABY-072","message":"At least one measurement value is required"}',
        );
      },
    );

    await tester.enterText(find.byKey(const Key('growth-form-weight')), '6.2');
    await tester.tap(find.byKey(const Key('growth-form-save')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('growth-form-error')), findsOneWidget);
    expect(find.text('Vui lòng nhập ít nhất một chỉ số đo.'), findsOneWidget);
  });

  testWidgets(
    'back button closes the form without submitting and no cancel button is shown',
    (tester) async {
      final service = _FakeGrowthMeasurementService();
      await _pumpForm(tester, service: service);

      expect(find.byKey(const Key('growth-form-cancel')), findsNothing);
      expect(find.text('Hủy bỏ'), findsNothing);

      await tester.tap(find.byKey(const Key('growth-form-back')));
      await tester.pumpAndSettle();

      expect(
        find.byKey(const Key('growth-measurement-form-screen')),
        findsNothing,
      );
      expect(service.addedPayload, isNull);
    },
  );

  testWidgets(
    'displays birthDate hint and restricts date picker when birthDate is provided',
    (tester) async {
      final birth = DateTime(2026, 5, 10);
      await _pumpForm(tester, birthDate: birth);

      expect(find.text('Từ ngày sinh: 10/05/2026'), findsOneWidget);

      await tester.tap(find.byKey(const Key('growth-form-date')));
      await tester.pumpAndSettle();

      expect(find.byType(DatePickerDialog), findsOneWidget);
      final datePicker =
          tester.widget<DatePickerDialog>(find.byType(DatePickerDialog));
      expect(
        DateUtils.dateOnly(datePicker.firstDate),
        equals(DateUtils.dateOnly(birth)),
      );
      expect(
        DateUtils.dateOnly(datePicker.lastDate),
        equals(DateUtils.dateOnly(DateTime.now())),
      );
      await tester.tap(find.text('Hủy'));
      await tester.pumpAndSettle();
    },
  );

  testWidgets(
    'loads birthDate from BabyService when birthDate parameter is omitted',
    (tester) async {
      final babyService = _FakeBabyService(
        profile: BabyProfile(
          id: 'baby-1',
          nickname: 'Bé Test',
          birthDate: DateTime(2026, 3, 15),
          gender: BabyGender.female,
          isActive: true,
        ),
      );
      await _pumpForm(tester, babyService: babyService);

      expect(find.text('Từ ngày sinh: 15/03/2026'), findsOneWidget);
    },
  );

  testWidgets(
    'rejects save when measuredDate is before birthDate with clear message',
    (tester) async {
      final service = _FakeGrowthMeasurementService();
      await _pumpForm(
        tester,
        service: service,
        measurement: _measurement(),
        birthDate: DateTime(2026, 8, 1),
      );

      await tester.tap(find.byKey(const Key('growth-form-save')));
      await tester.pump();

      expect(find.byKey(const Key('growth-form-error')), findsOneWidget);
      expect(
        find.text('Ngày đo không thể trước ngày sinh của bé.'),
        findsOneWidget,
      );
      expect(service.updatedPayload, isNull);
    },
  );

  testWidgets('displays BABY-075 translated message on save failure', (
    tester,
  ) async {
    final service = _FakeGrowthMeasurementService();
    await _pumpForm(
      tester,
      service: service,
      onAdd: (id, body) async {
        throw ApiException(
          400,
          '{"code":"BABY-075","message":"Measured date cannot be before baby birth date"}',
        );
      },
    );

    await tester.enterText(find.byKey(const Key('growth-form-weight')), '6.2');
    await tester.tap(find.byKey(const Key('growth-form-save')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('growth-form-error')), findsOneWidget);
    expect(
      find.text('Ngày đo không thể trước ngày sinh của bé.'),
      findsOneWidget,
    );
  });
}
