import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:untitled/core/auth/auth_state.dart';
import 'package:untitled/features/directChat/models/direct_conversation.dart';
import 'package:untitled/features/directChat/models/expert_directory_item.dart';
import 'package:untitled/features/directChat/services/direct_chat_service.dart';
import 'package:untitled/features/home/screens/expert_home_shell.dart';
import 'package:untitled/features/home/screens/family_home_shell.dart';
import 'package:untitled/features/home/screens/home_shell.dart';
import 'package:untitled/features/privacy/services/location_consent_coordinator.dart';

class _FakeDirectChatService extends DirectChatService {
  @override
  Future<List<DirectConversationSummary>> listMyConversations() async =>
      const [];

  @override
  Future<UnreadSummary> getUnreadSummary() async =>
      const UnreadSummary(
        unreadConversationCount: 0,
        totalUnreadMessageCount: 0,
      );

  @override
  Future<ExpertDirectoryPage> getExpertDirectory({
    String? q,
    String? specialty,
    int page = 0,
    int size = 20,
  }) async => const ExpertDirectoryPage(
    experts: [],
    currentPage: 0,
    pageSize: 20,
    totalElements: 0,
    totalPages: 0,
  );
}

void main() {
  setUp(() async {
    FlutterSecureStorage.setMockInitialValues({});
    await AuthState.instance.init();
    await AuthState.instance.clear();
    DirectChatService.instance = _FakeDirectChatService();
    LocationConsentCoordinator.instance.resetSession();
  });

  tearDown(() async {
    LocationConsentCoordinator.instance = LocationConsentCoordinator();
    await AuthState.instance.clear();
  });

  group('LocationConsentCoordinator unit tests', () {
    test('hasLocationConsent returns true when active safety grant exists', () async {
      final coordinator = LocationConsentCoordinator(
        consentProbe: () async => true,
      );
      expect(await coordinator.hasLocationConsent(), isTrue);
    });

    test('hasLocationConsent returns false when probe returns false or throws', () async {
      final coordinator = LocationConsentCoordinator(
        consentProbe: () async => false,
      );
      expect(await coordinator.hasLocationConsent(), isFalse);

      final failingCoordinator = LocationConsentCoordinator(
        consentProbe: () async => throw Exception('network error'),
      );
      expect(await failingCoordinator.hasLocationConsent(), isFalse);
    });

    test('grantLocationConsent invokes consentGrant and osPermissionRequest', () async {
      var grantCalled = false;
      var osRequested = false;

      final coordinator = LocationConsentCoordinator(
        consentGrant: ({
          required String dataType,
          required String purpose,
          required String recipient,
          required String scope,
        }) async {
          expect(dataType, 'LOCATION');
          expect(purpose, 'SHARE');
          expect(recipient, 'CAREBRIDGE_SAFETY');
          expect(scope, 'SAFETY_EMERGENCY_ALERT');
          grantCalled = true;
        },
        osPermissionRequest: () async {
          osRequested = true;
          return true;
        },
      );

      await coordinator.grantLocationConsent();
      expect(grantCalled, isTrue);
      expect(osRequested, isTrue);
    });

    testWidgets('showLocationConsentDialog renders standard disclosure and handles actions', (tester) async {
      final coordinator = LocationConsentCoordinator();

      bool? result;
      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () async {
                result = await coordinator.showLocationConsentDialog(context);
              },
              child: const Text('Show Dialog'),
            ),
          ),
        ),
      );

      // Open dialog
      await tester.tap(find.text('Show Dialog'));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('location-consent-dialog')), findsOneWidget);
      expect(find.byKey(const Key('location-consent-disclosure')), findsOneWidget);
      expect(find.byKey(const Key('location-consent-cancel')), findsOneWidget);
      expect(find.byKey(const Key('location-consent-confirm')), findsOneWidget);

      // Tap cancel
      await tester.tap(find.byKey(const Key('location-consent-cancel')));
      await tester.pumpAndSettle();
      expect(result, isFalse);

      // Open again and confirm
      await tester.tap(find.text('Show Dialog'));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('location-consent-confirm')));
      await tester.pumpAndSettle();
      expect(result, isTrue);
    });

    testWidgets('checkAndPromptLocationConsent returns false when unauthenticated', (tester) async {
      await AuthState.instance.clear();
      final coordinator = LocationConsentCoordinator(
        consentProbe: () async => false,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (context) {
              WidgetsBinding.instance.addPostFrameCallback((_) {
                coordinator.checkAndPromptLocationConsent(context);
              });
              return const SizedBox();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('location-consent-dialog')), findsNothing);
    });

    testWidgets('checkAndPromptLocationConsent returns false when already granted', (tester) async {
      await AuthState.instance.setTokens(
        accessToken: 'valid-token',
        refreshToken: 'valid-refresh',
        userId: 'user-already-granted',
        role: 'MOTHER',
      );

      final coordinator = LocationConsentCoordinator(
        consentProbe: () async => true,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (context) {
              WidgetsBinding.instance.addPostFrameCallback((_) {
                coordinator.checkAndPromptLocationConsent(context);
              });
              return const SizedBox();
            },
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('location-consent-dialog')), findsNothing);
    });

    testWidgets('checkAndPromptLocationConsent prompts and grants on confirm', (tester) async {
      await AuthState.instance.setTokens(
        accessToken: 'valid-token',
        refreshToken: 'valid-refresh',
        userId: 'user-new',
        role: 'MOTHER',
      );

      var grantCalled = false;
      var osRequested = false;

      final coordinator = LocationConsentCoordinator(
        consentProbe: () async => false,
        consentGrant: ({
          required String dataType,
          required String purpose,
          required String recipient,
          required String scope,
        }) async {
          grantCalled = true;
        },
        osPermissionRequest: () async {
          osRequested = true;
          return true;
        },
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (context) {
              WidgetsBinding.instance.addPostFrameCallback((_) {
                coordinator.checkAndPromptLocationConsent(context);
              });
              return const Scaffold(body: Text('Home Screen'));
            },
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('location-consent-dialog')), findsOneWidget);
      await tester.tap(find.byKey(const Key('location-consent-confirm')));
      await tester.pumpAndSettle();

      expect(grantCalled, isTrue);
      expect(osRequested, isTrue);
    });

    testWidgets('checkAndPromptLocationConsent suppresses re-prompting in same session after cancel', (tester) async {
      await AuthState.instance.setTokens(
        accessToken: 'valid-token',
        refreshToken: 'valid-refresh',
        userId: 'user-cancels',
        role: 'MOTHER',
      );

      final coordinator = LocationConsentCoordinator(
        consentProbe: () async => false,
      );

      late BuildContext savedContext;
      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (context) {
              savedContext = context;
              WidgetsBinding.instance.addPostFrameCallback((_) {
                coordinator.checkAndPromptLocationConsent(context);
              });
              return const Scaffold(body: Text('Home Screen'));
            },
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Dismiss by Cancel
      expect(find.byKey(const Key('location-consent-dialog')), findsOneWidget);
      await tester.tap(find.byKey(const Key('location-consent-cancel')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('location-consent-dialog')), findsNothing);

      // Calling checkAndPromptLocationConsent again for the same account should not prompt
      final promptedAgain = await coordinator.checkAndPromptLocationConsent(savedContext);
      await tester.pumpAndSettle();
      expect(promptedAgain, isFalse);
      expect(find.byKey(const Key('location-consent-dialog')), findsNothing);
    });
  });

  group('Location Consent Integration in Home Shells', () {
    testWidgets('Mother HomeShell checks and prompts location consent for new user', (tester) async {
      await AuthState.instance.setTokens(
        accessToken: 'mother-token',
        refreshToken: 'mother-refresh',
        userId: 'mother-new-acc',
        role: 'MOTHER',
      );

      var grantCalled = false;
      LocationConsentCoordinator.instance = LocationConsentCoordinator(
        consentProbe: () async => false,
        consentGrant: ({
          required String dataType,
          required String purpose,
          required String recipient,
          required String scope,
        }) async {
          grantCalled = true;
        },
        osPermissionRequest: () async => true,
      );

      await tester.pumpWidget(const MaterialApp(home: HomeShell()));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('location-consent-dialog')), findsOneWidget);
      await tester.tap(find.byKey(const Key('location-consent-confirm')));
      await tester.pumpAndSettle();

      expect(grantCalled, isTrue);
    });

    testWidgets('Family FamilyHomeShell checks and prompts location consent for new user', (tester) async {
      await AuthState.instance.setTokens(
        accessToken: 'family-token',
        refreshToken: 'family-refresh',
        userId: 'family-new-acc',
        role: 'FAMILY',
      );

      var grantCalled = false;
      LocationConsentCoordinator.instance = LocationConsentCoordinator(
        consentProbe: () async => false,
        consentGrant: ({
          required String dataType,
          required String purpose,
          required String recipient,
          required String scope,
        }) async {
          grantCalled = true;
        },
        osPermissionRequest: () async => true,
      );

      await tester.pumpWidget(const MaterialApp(home: FamilyHomeShell()));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('location-consent-dialog')), findsOneWidget);
      await tester.tap(find.byKey(const Key('location-consent-confirm')));
      await tester.pumpAndSettle();

      expect(grantCalled, isTrue);
    });

    testWidgets('Expert ExpertHomeShell checks and prompts location consent for new user', (tester) async {
      await AuthState.instance.setTokens(
        accessToken: 'expert-token',
        refreshToken: 'expert-refresh',
        userId: 'expert-new-acc',
        role: 'EXPERT',
      );

      var grantCalled = false;
      LocationConsentCoordinator.instance = LocationConsentCoordinator(
        consentProbe: () async => false,
        consentGrant: ({
          required String dataType,
          required String purpose,
          required String recipient,
          required String scope,
        }) async {
          grantCalled = true;
        },
        osPermissionRequest: () async => true,
      );

      await tester.pumpWidget(const MaterialApp(home: ExpertHomeShell()));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('location-consent-dialog')), findsOneWidget);
      await tester.tap(find.byKey(const Key('location-consent-confirm')));
      await tester.pumpAndSettle();

      expect(grantCalled, isTrue);
    });
  });
}
