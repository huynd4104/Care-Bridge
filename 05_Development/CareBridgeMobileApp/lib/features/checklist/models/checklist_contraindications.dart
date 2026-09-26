/// Chống chỉ định của mục checklist theo khảo sát cá nhân hóa của mẹ.
///
/// Backend ẩn các mục chống chỉ định trong Trang chủ / lịch sử / chia sẻ. Hàm ở đây
/// dùng cho lộ trình dựng từ danh mục dự phòng trên client, và phải khớp với
/// `RecommendationProfileTagResolver.extractTags` ở backend.
class ChecklistContraindications {
  const ChecklistContraindications._();

  static const _codeDomains = [
    'reproductiveHistory',
    'underlyingConditions',
    'nutrition',
    'currentMedications',
    'sexualHealth',
  ];

  static const _lifestyleExtraFlags = {'SUBSTANCE_USE', 'STRESS', 'UNHEALTHY_DIET'};

  static const _nonTagCodes = {
    'NONE',
    'NONE_KNOWN',
    'NO_LISTED_REPRODUCTIVE_HISTORY',
    'NO_CURRENT_CONCERN',
    'NONE_KNOWN_LIFESTYLE',
    'NONE_KNOWN_VACCINATION',
    'NONE_KNOWN_MEDICATION',
    'NO_CURRENT_INFORMATION_NEED',
    'NO_PRIOR_PREGNANCY',
  };

  /// Tập tag khảo sát đang có của mẹ (rỗng nếu chưa làm khảo sát).
  static Set<String> profileTags(Map<String, dynamic>? profile) {
    if (profile == null) return const {};
    final tags = <String>{};
    for (final domain in _codeDomains) {
      final node = profile[domain];
      if (node is Map && node['state'] == 'KNOWN' && node['codes'] is List) {
        for (final code in (node['codes'] as List).whereType<String>()) {
          if (!_nonTagCodes.contains(code)) tags.add(code);
        }
      }
    }
    final lifestyle = profile['lifestyle'];
    if (lifestyle is Map) {
      String? value(String key) {
        final node = lifestyle[key];
        return node is Map && node['state'] == 'KNOWN' && node['value'] is String
            ? node['value'] as String
            : null;
      }

      if (value('smoking') == 'CURRENT') tags.add('SMOKING');
      final alcohol = value('alcohol');
      if (alcohol != null && alcohol != 'NONE') tags.add('ALCOHOL_USE');
      if (value('physicalActivity') == 'LOW') tags.add('LOW_ACTIVITY');
      if (value('sleep') == 'CONCERN') tags.add('SLEEP_CONCERN');
      final flags = lifestyle['flags'];
      if (flags is List) {
        tags.addAll(flags.whereType<String>().where(_lifestyleExtraFlags.contains));
      }
    }
    final vaccination = profile['vaccination'];
    if (vaccination is Map) _addVaccinationTags(vaccination, tags);
    return tags;
  }

  static void _addVaccinationTags(Map vaccination, Set<String> tags) {
    final flags = vaccination['flags'];
    if (flags is List && flags.contains('NOT_ASSESSED')) {
      tags.add('NOT_ASSESSED');
      return;
    }
    final answers = vaccination['answers'];
    if (answers is! List || answers.isEmpty) return;
    final valueByCode = <String, dynamic>{};
    for (final raw in answers) {
      if (raw is! Map || raw['state'] != 'KNOWN') return;
      final code = raw['code'];
      if (code is String) valueByCode[code] = raw['value'];
    }
    if (valueByCode['RUBELLA_IMMUNITY'] == 'NOT_RECEIVED') {
      tags.add('RUBELLA_NONIMMUNE');
    }
    if (valueByCode.containsKey('HEPATITIS_B') &&
        valueByCode['HEPATITIS_B'] != 'UP_TO_DATE') {
      tags.add('HEPATITIS_B_INCOMPLETE');
    }
    if (valueByCode.containsKey('INFLUENZA') &&
        valueByCode['INFLUENZA'] != 'UP_TO_DATE') {
      tags.add('INFLUENZA_DUE');
    }
    if (valueByCode.containsKey('COVID_19') &&
        valueByCode['COVID_19'] != 'UP_TO_DATE') {
      tags.add('COVID_19_UPDATE');
    }
  }

  static bool isContraindicated(
    Iterable<String> itemContraindications,
    Set<String> profileTags,
  ) =>
      profileTags.isNotEmpty && itemContraindications.any(profileTags.contains);
}
