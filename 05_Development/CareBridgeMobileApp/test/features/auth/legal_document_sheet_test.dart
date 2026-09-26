import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:untitled/features/auth/screens/register_screen.dart';
import 'package:untitled/features/auth/widgets/legal_document_sheet.dart';

void main() {
  group('LegalDocumentSheet Widget Tests', () {
    testWidgets('renders terms of service by default and switches to privacy', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: LegalDocumentSheet(initialDoc: LegalDocType.terms),
          ),
        ),
      );

      // Verify terms content is displayed
      expect(find.text('Điều khoản dịch vụ'), findsNWidgets(2)); // header and tab
      expect(find.text('TUYÊN BỐ MIỄN TRỪ TRÁCH NHIỆM Y TẾ (QUAN TRỌNG)'), findsOneWidget);
      expect(find.textContaining('CareBridge và Trợ lý AI Nurse không cung cấp dịch vụ cấp cứu y tế'), findsOneWidget);

      // Tap on Privacy tab
      await tester.tap(find.text('Quyền riêng tư (NĐ 13)'));
      await tester.pumpAndSettle();

      // Verify privacy content is now displayed
      expect(find.text('TUÂN THỦ NGHỊ ĐỊNH 13/2023/NĐ-CP & LUẬT BẢO VỆ DỮ LIỆU CÁ NHÂN'), findsOneWidget);
      expect(find.textContaining('Dữ liệu sức khỏe thai kỳ và trẻ nhỏ thuộc nhóm DỮ LIỆU CÁ NHÂN NHẠY CẢM'), findsOneWidget);
    });

    testWidgets('close button dismisses sheet with false', (tester) async {
      bool? result;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () async {
                  result = await showLegalDocumentSheet(context);
                },
                child: const Text('Open'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();

      expect(find.byType(LegalDocumentSheet), findsOneWidget);

      await tester.tap(find.byTooltip('Đóng'));
      await tester.pumpAndSettle();

      expect(find.byType(LegalDocumentSheet), findsNothing);
      expect(result, isFalse);
    });

    testWidgets('agree button dismisses sheet with true', (tester) async {
      bool? result;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () async {
                  result = await showLegalDocumentSheet(context);
                },
                child: const Text('Open'),
              ),
            ),
          ),
        ),
      );

      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();

      expect(find.byType(LegalDocumentSheet), findsOneWidget);

      await tester.tap(find.text('Đã đọc & Đồng ý'));
      await tester.pumpAndSettle();

      expect(find.byType(LegalDocumentSheet), findsNothing);
      expect(result, isTrue);
    });
  });

  group('RegisterScreen Terms Tap Integration Tests', () {
    testWidgets('tapping Điều khoản opens terms bottom sheet and auto-checks on agreement', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: RegisterScreen(),
        ),
      );

      // Verify Checkbox is initially unchecked
      final checkboxFinder = find.byType(Checkbox);
      expect(checkboxFinder, findsOneWidget);
      expect(tester.widget<Checkbox>(checkboxFinder).value, isFalse);

      // Find the rich text containing "Điều khoản"
      final textRichFinder = find.byWidgetPredicate(
        (widget) => widget is RichText && widget.text.toPlainText().contains('Điều khoản'),
      );
      expect(textRichFinder, findsOneWidget);

      // Traverse InlineSpans to find "Điều khoản"
      final richText = tester.widget<RichText>(textRichFinder);
      TextSpan? termsSpan;
      richText.text.visitChildren((span) {
        if (span is TextSpan && span.text == 'Điều khoản') {
          termsSpan = span;
          return false;
        }
        return true;
      });

      expect(termsSpan, isNotNull);
      expect(termsSpan!.recognizer, isNotNull);
      (termsSpan!.recognizer as TapGestureRecognizer).onTap!();
      await tester.pumpAndSettle();

      // Verify bottom sheet is open with Terms content
      expect(find.byType(LegalDocumentSheet), findsOneWidget);
      expect(find.text('TUYÊN BỐ MIỄN TRỪ TRÁCH NHIỆM Y TẾ (QUAN TRỌNG)'), findsOneWidget);

      // Tap "Đã đọc & Đồng ý"
      await tester.tap(find.text('Đã đọc & Đồng ý'));
      await tester.pumpAndSettle();

      // Verify bottom sheet closed and checkbox is now checked
      expect(find.byType(LegalDocumentSheet), findsNothing);
      expect(tester.widget<Checkbox>(checkboxFinder).value, isTrue);
    });

    testWidgets('tapping Chính sách quyền riêng tư opens privacy bottom sheet', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: RegisterScreen(),
        ),
      );

      final textRichFinder = find.byWidgetPredicate(
        (widget) => widget is RichText && widget.text.toPlainText().contains('Chính sách quyền riêng tư'),
      );
      expect(textRichFinder, findsOneWidget);

      final richText = tester.widget<RichText>(textRichFinder);
      TextSpan? privacySpan;
      richText.text.visitChildren((span) {
        if (span is TextSpan && span.text == 'Chính sách quyền riêng tư') {
          privacySpan = span;
          return false;
        }
        return true;
      });

      expect(privacySpan, isNotNull);
      expect(privacySpan!.recognizer, isNotNull);
      (privacySpan!.recognizer as TapGestureRecognizer).onTap!();
      await tester.pumpAndSettle();

      // Verify bottom sheet is open with Privacy content
      expect(find.byType(LegalDocumentSheet), findsOneWidget);
      expect(find.text('TUÂN THỦ NGHỊ ĐỊNH 13/2023/NĐ-CP & LUẬT BẢO VỆ DỮ LIỆU CÁ NHÂN'), findsOneWidget);

      // Close sheet
      await tester.tap(find.byTooltip('Đóng'));
      await tester.pumpAndSettle();
      expect(find.byType(LegalDocumentSheet), findsNothing);
    });
  });
}
