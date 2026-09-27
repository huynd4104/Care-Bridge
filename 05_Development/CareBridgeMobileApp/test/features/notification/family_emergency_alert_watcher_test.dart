import 'package:flutter_test/flutter_test.dart';
import 'package:untitled/core/notifications/fcm_service.dart';
import 'package:untitled/features/notification/models/notification_model.dart';
import 'package:untitled/features/notification/services/family_emergency_alert_watcher.dart';

const _sessionA = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const _sessionB = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
final _now = DateTime.utc(2026, 9, 26, 10);

NotificationRecord _emergency(
  String id, {
  String sessionId = _sessionA,
  bool isRead = false,
  Duration age = const Duration(seconds: 5),
  String type = 'EMERGENCY',
  String referenceType = 'EMERGENCY_SESSION',
}) => NotificationRecord(
  id: id,
  userId: 'family',
  type: type,
  title: 'Cảnh báo khẩn cấp',
  body: 'Hệ thống phát hiện dấu hiệu khẩn cấp.',
  referenceId: sessionId,
  referenceType: referenceType,
  status: 'SENT',
  isRead: isRead,
  createdAt: _now.subtract(age),
);

void main() {
  late List<NotificationRecord> inbox;
  late List<String> opened;
  late List<String> markedRead;

  FamilyEmergencyAlertWatcher build({
    FcmService? fcm,
    bool Function(String route)? openRoute,
  }) => FamilyEmergencyAlertWatcher(
    fetchNotifications: () async => inbox,
    openRoute:
        openRoute ??
        (route) {
          opened.add(route);
          return true;
        },
    isRouteRecentlyOpened: fcm == null
        ? null
        : (route) => fcm.isEmergencyRouteRecent(route, now: _now),
    recordOpenedRoute: fcm == null
        ? null
        : (route) => fcm.recordEmergencyRoute(route, now: _now),
    markAsRead: (n) async => markedRead.add(n.id),
    now: () => _now,
  );

  setUp(() {
    inbox = [];
    opened = [];
    markedRead = [];
  });

  test('auto-opens a new unread emergency alert and marks it read', () async {
    inbox = [_emergency('n1')];
    await build().poll();
    expect(opened, ['/emergency/alert/$_sessionA']);
    expect(markedRead, ['n1']);
  });

  test('does not reopen the same notification on later polls', () async {
    final watcher = build();
    inbox = [_emergency('n1')];
    await watcher.poll();
    await watcher.poll();
    expect(opened, hasLength(1));
  });

  test('opens a re-alert (new notification) for the same session', () async {
    final watcher = build();
    inbox = [_emergency('n1')];
    await watcher.poll();
    inbox = [_emergency('n2'), _emergency('n1', isRead: true)];
    await watcher.poll();
    expect(opened, [
      '/emergency/alert/$_sessionA',
      '/emergency/alert/$_sessionA',
    ]);
  });

  test('opens only the newest when several alerts are pending', () async {
    inbox = [
      _emergency('old', age: const Duration(minutes: 3)),
      _emergency('new', sessionId: _sessionB),
    ];
    await build().poll();
    expect(opened, ['/emergency/alert/$_sessionB']);
  });

  test('ignores read, stale, and non-emergency notifications', () async {
    inbox = [
      _emergency('read', isRead: true),
      _emergency('stale', age: const Duration(hours: 2)),
      _emergency('other', type: 'REMINDER', referenceType: 'REMINDER_SCHEDULE'),
    ];
    await build().poll();
    expect(opened, isEmpty);
    expect(markedRead, isEmpty);
  });

  test('skips when the FCM push already opened the alert route', () async {
    final fcm = FcmService();
    expect(
      fcm.claimEmergencyRoute('/emergency/alert/$_sessionA', now: _now),
      isTrue,
    );
    inbox = [_emergency('n1')];
    await build(fcm: fcm).poll();
    expect(opened, isEmpty);
    expect(markedRead, isEmpty);
  });

  test('records the opened route so a late FCM push is suppressed', () async {
    final fcm = FcmService();
    inbox = [_emergency('n1')];
    await build(fcm: fcm).poll();
    expect(opened, hasLength(1));
    expect(
      fcm.claimEmergencyRoute('/emergency/alert/$_sessionA', now: _now),
      isFalse,
    );
  });

  test('retries on the next poll when the route could not be opened', () async {
    var canOpen = false;
    final watcher = build(
      fcm: FcmService(),
      openRoute: (route) {
        if (!canOpen) return false;
        opened.add(route);
        return true;
      },
    );
    inbox = [_emergency('n1')];
    await watcher.poll();
    expect(opened, isEmpty);
    canOpen = true;
    await watcher.poll();
    expect(opened, ['/emergency/alert/$_sessionA']);
  });

  test('reports every poll result for the bell badge', () async {
    List<NotificationRecord>? seen;
    inbox = [_emergency('n1', isRead: true)];
    await FamilyEmergencyAlertWatcher(
      fetchNotifications: () async => inbox,
      openRoute: (_) => true,
      onNotifications: (n) => seen = n,
      now: () => _now,
    ).poll();
    expect(seen, same(inbox));
  });

  test('swallows fetch failures so the next tick can retry', () async {
    final watcher = FamilyEmergencyAlertWatcher(
      fetchNotifications: () async => throw Exception('offline'),
      openRoute: (_) => true,
      now: () => _now,
    );
    await expectLater(watcher.poll(), completes);
  });

  group('FcmService.claimEmergencyRoute', () {
    test('dedupes the same route inside the window and frees it after', () {
      final service = FcmService();
      const route = '/emergency/alert/$_sessionA';
      expect(service.claimEmergencyRoute(route, now: _now), isTrue);
      expect(
        service.claimEmergencyRoute(
          route,
          now: _now.add(const Duration(seconds: 30)),
        ),
        isFalse,
      );
      expect(
        service.claimEmergencyRoute(
          route,
          now: _now.add(
            FcmService.emergencyDedupeWindow + const Duration(seconds: 1),
          ),
        ),
        isTrue,
      );
    });
  });
}
