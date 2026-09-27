import 'dart:async';

import '../models/notification_model.dart';
import '../routing/consultation_notification_routing.dart';

/// In-app fallback for UC-65 family emergency alerts.
///
/// The backend always persists an EMERGENCY / EMERGENCY_SESSION notification
/// record, but an FCM push may never reach this device (no registered token,
/// provider failure, web permission denied). Without a push nothing opened the
/// alert while the family home was on screen — only the bell badge changed.
/// This watcher polls the notification inbox and opens every new, recent,
/// unread emergency alert automatically so urgent-care escalation stays visible.
class FamilyEmergencyAlertWatcher {
  FamilyEmergencyAlertWatcher({
    required this.fetchNotifications,
    required this.openRoute,
    this.isRouteRecentlyOpened,
    this.recordOpenedRoute,
    this.markAsRead,
    this.onNotifications,
    DateTime Function()? now,
    this.interval = const Duration(seconds: 10),
    this.freshness = const Duration(minutes: 15),
  }) : _now = now ?? DateTime.now;

  final Future<List<NotificationRecord>> Function() fetchNotifications;

  /// Opens the alert route. Returns false when the route could not be opened
  /// (e.g. screen unmounted, account switched) so it is retried next poll.
  final bool Function(String route) openRoute;

  /// Shared de-duplication with the FCM foreground path: checked before
  /// opening, and recorded only after the route actually opened, so a failed
  /// open never blocks the retry on the next poll.
  final bool Function(String route)? isRouteRecentlyOpened;
  final void Function(String route)? recordOpenedRoute;
  final Future<void> Function(NotificationRecord notification)? markAsRead;

  /// Receives every successful poll result (used to keep the bell badge live).
  final void Function(List<NotificationRecord> notifications)? onNotifications;
  final Duration interval;

  /// Unread alerts older than this are left in the inbox instead of
  /// auto-opening every time the home screen mounts.
  final Duration freshness;
  final DateTime Function() _now;

  final Set<String> _handledNotificationIds = <String>{};
  Timer? _timer;
  bool _polling = false;

  bool get isRunning => _timer != null;

  void start() {
    if (_timer != null) return;
    _timer = Timer.periodic(interval, (_) => unawaited(poll()));
    unawaited(poll());
  }

  void stop() {
    _timer?.cancel();
    _timer = null;
  }

  Future<void> poll() async {
    if (_polling) return;
    _polling = true;
    try {
      final notifications = await fetchNotifications();
      onNotifications?.call(notifications);
      final pending = notifications.where(_shouldAutoOpen).toList()
        ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
      if (pending.isEmpty) return;
      // Open only the newest alert; older ones stay unread in the inbox.
      final newest = pending.first;
      final route = resolveNotificationRoute(newest)!;
      if (isRouteRecentlyOpened?.call(route) ?? false) {
        // The FCM push already opened this alert.
        _handledNotificationIds.addAll(pending.map((n) => n.id));
        return;
      }
      if (!openRoute(route)) return;
      _handledNotificationIds.addAll(pending.map((n) => n.id));
      recordOpenedRoute?.call(route);
      final markRead = markAsRead;
      if (markRead != null) {
        try {
          await markRead(newest);
        } catch (_) {}
      }
    } catch (_) {
      // Transient network failures are retried on the next tick.
    } finally {
      _polling = false;
    }
  }

  bool _shouldAutoOpen(NotificationRecord n) {
    if (!n.isUnread || _handledNotificationIds.contains(n.id)) return false;
    if (n.type.trim().toUpperCase() != 'EMERGENCY') return false;
    final route = resolveNotificationRoute(n);
    if (route == null || !route.startsWith('/emergency/alert/')) return false;
    final age = _now().difference(n.sentAt ?? n.createdAt);
    return age <= freshness;
  }
}
