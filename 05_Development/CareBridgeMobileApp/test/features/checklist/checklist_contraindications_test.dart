import 'package:flutter_test/flutter_test.dart';
import 'package:untitled/features/checklist/models/checklist_contraindications.dart';
import 'package:untitled/features/checklist/services/checklist_roadmap_service.dart';

void main() {
  group('ChecklistContraindications.profileTags', () {
    test('maps survey answers to the same tags as the backend', () {
      final tags = ChecklistContraindications.profileTags({
        'underlyingConditions': {
          'state': 'KNOWN',
          'codes': ['ANEMIA', 'NONE_KNOWN'],
        },
        'nutrition': {
          'state': 'UNKNOWN',
          'codes': ['CALCIUM_INSUFFICIENT_OR_SUPPLEMENT'],
        },
        'lifestyle': {
          'smoking': {'state': 'KNOWN', 'value': 'CURRENT'},
          'alcohol': {'state': 'KNOWN', 'value': 'NONE'},
          'flags': ['STRESS'],
        },
      });

      expect(tags, {'ANEMIA', 'SMOKING', 'STRESS'});
      expect(ChecklistContraindications.profileTags(null), isEmpty);
    });
  });

  group('ChecklistRoadmapService contraindication filtering', () {
    Future<List<String>> prePregnancyTitles(Set<String> tags) async {
      final service = ChecklistRoadmapService(profileTagsLoader: () async => tags);
      final roadmap = await service.loadRoadmap(stage: 'PRE_PREGNANCY', currentWeek: 1);
      return [for (final m in roadmap) for (final t in m.tasks) t.title];
    }

    test('hides a contraindicated item and shows it again after the survey changes', () async {
      const ironItem = 'Bổ sung Sắt và Axit Folic trước thai kỳ';

      final anemic = await prePregnancyTitles({'ANEMIA'});
      expect(anemic, isNot(contains(ironItem)));
      // Screening/review items stay visible for the same mother.
      expect(anemic, contains('Rà soát lịch sử tiêm chủng cá nhân'));

      final updated = await prePregnancyTitles({'DIABETES'});
      expect(updated, contains(ironItem));
    });
  });
}
