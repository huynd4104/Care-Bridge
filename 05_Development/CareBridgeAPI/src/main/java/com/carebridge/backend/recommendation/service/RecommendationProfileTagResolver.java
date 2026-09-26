package com.carebridge.backend.recommendation.service;

import com.carebridge.backend.consent.entity.ConsentGrant;
import com.carebridge.backend.consent.repository.ConsentGrantRepository;
import com.carebridge.backend.journey.entity.MotherJourney;
import com.carebridge.backend.journey.repository.MotherJourneyRepository;
import com.carebridge.backend.recommendation.RecommendationConstants;
import com.carebridge.backend.recommendation.entity.RecommendationProfileStatus;
import java.time.Clock;
import java.time.Instant;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Component;

/**
 * Trích xuất tập "tag" khảo sát cá nhân hóa (bệnh nền, tiền sử sinh sản, lối sống,
 * dinh dưỡng, tiêm chủng, thuốc, sức khỏe tình dục) mà người mẹ đang có.
 *
 * <p>Tag dùng cùng mã với questionnaire trên mobile
 * ({@code recommendation_questionnaire.dart}); lựa chọn "Không thuộc các trường hợp trên"
 * không bao giờ là tag. Component này chỉ đọc: không làm mới/xóa hồ sơ khi consent
 * hết hạn (việc đó thuộc {@link RecommendationService}). Khi consent không còn hiệu lực
 * hoặc hồ sơ chưa hoàn tất, trả về tập rỗng.</p>
 */
@Slf4j
@Component
public class RecommendationProfileTagResolver {

    private static final Set<String> CODE_DOMAINS = Set.of(
            "reproductiveHistory", "underlyingConditions", "nutrition",
            "currentMedications", "sexualHealth");

    private static final Set<String> LIFESTYLE_EXTRA_FLAGS = Set.of(
            "SUBSTANCE_USE", "STRESS", "UNHEALTHY_DIET");

    private static final Set<String> NON_TAG_CODES = Set.of(
            "NONE", "NONE_KNOWN", "NO_LISTED_REPRODUCTIVE_HISTORY", "NO_CURRENT_CONCERN",
            "NONE_KNOWN_LIFESTYLE", "NONE_KNOWN_VACCINATION", "NONE_KNOWN_MEDICATION",
            "NO_CURRENT_INFORMATION_NEED", "NO_PRIOR_PREGNANCY");

    private final MotherJourneyRepository journeyRepository;
    private final ConsentGrantRepository consentGrantRepository;
    private final Clock clock;

    @Autowired
    public RecommendationProfileTagResolver(
            MotherJourneyRepository journeyRepository,
            ConsentGrantRepository consentGrantRepository) {
        this(journeyRepository, consentGrantRepository, Clock.systemUTC());
    }

    public RecommendationProfileTagResolver(
            MotherJourneyRepository journeyRepository,
            ConsentGrantRepository consentGrantRepository,
            Clock clock) {
        this.journeyRepository = journeyRepository;
        this.consentGrantRepository = consentGrantRepository;
        this.clock = clock;
    }

    /** Tag khảo sát đang hiệu lực của người mẹ; rỗng nếu không có hồ sơ/consent hợp lệ. */
    public Set<String> activeTags(UUID motherUserId) {
        if (motherUserId == null) {
            return Set.of();
        }
        try {
            MotherJourney journey = journeyRepository.findCanonical(motherUserId).orElse(null);
            if (journey == null
                    || (journey.getRecommendationProfileStatus() != RecommendationProfileStatus.ACTIVE
                    && journey.getRecommendationProfileStatus() != RecommendationProfileStatus.REVIEW_REQUIRED)
                    || !hasValidConsent(motherUserId)) {
                return Set.of();
            }
            Map<String, Object> envelope = journey.getRecommendationProfileJson();
            return extractTags(envelope == null ? null : envelope.get("profile"));
        } catch (RuntimeException ex) {
            log.warn("Recommendation profile tag resolution failed for owner={}", motherUserId);
            return Set.of();
        }
    }

    private boolean hasValidConsent(UUID ownerUserId) {
        List<ConsentGrant> rows = consentGrantRepository.findLatestRecommendationGrant(
                ownerUserId, RecommendationService.CONSENT_SCOPE, PageRequest.of(0, 1));
        ConsentGrant latest = rows.isEmpty() ? null : rows.get(0);
        Instant now = Instant.now(clock);
        return latest != null
                && latest.getRevokedAt() == null
                && RecommendationConstants.POLICY_VERSION.equals(latest.getPolicyVersion())
                && latest.getExpiryAt() != null
                && latest.getExpiryAt().isAfter(now)
                && "ACTIVE".equalsIgnoreCase(latest.getStatus());
    }

    /** Chuyển hồ sơ JSON (dạng đã validate) thành tập tag phẳng. */
    public static Set<String> extractTags(Object profile) {
        if (!(profile instanceof Map<?, ?> root)) {
            return Set.of();
        }
        Set<String> tags = new LinkedHashSet<>();
        for (String domain : CODE_DOMAINS) {
            if (root.get(domain) instanceof Map<?, ?> node && known(node)
                    && node.get("codes") instanceof Collection<?> codes) {
                for (Object code : codes) {
                    if (code instanceof String value && !NON_TAG_CODES.contains(value)) {
                        tags.add(value);
                    }
                }
            }
        }
        if (root.get("lifestyle") instanceof Map<?, ?> lifestyle) {
            if ("CURRENT".equals(lifestyleValue(lifestyle, "smoking"))) tags.add("SMOKING");
            String alcohol = lifestyleValue(lifestyle, "alcohol");
            if (alcohol != null && !"NONE".equals(alcohol)) tags.add("ALCOHOL_USE");
            if ("LOW".equals(lifestyleValue(lifestyle, "physicalActivity"))) tags.add("LOW_ACTIVITY");
            if ("CONCERN".equals(lifestyleValue(lifestyle, "sleep"))) tags.add("SLEEP_CONCERN");
            if (lifestyle.get("flags") instanceof Collection<?> flags) {
                for (Object flag : flags) {
                    if (flag instanceof String value && LIFESTYLE_EXTRA_FLAGS.contains(value)) {
                        tags.add(value);
                    }
                }
            }
        }
        if (root.get("vaccination") instanceof Map<?, ?> vaccination) {
            addVaccinationTags(vaccination, tags);
        }
        return Set.copyOf(tags);
    }

    /** Mirror {@code _selectedVaccinationFlags} of the mobile questionnaire. */
    private static void addVaccinationTags(Map<?, ?> vaccination, Set<String> tags) {
        if (vaccination.get("flags") instanceof Collection<?> flags && flags.contains("NOT_ASSESSED")) {
            tags.add("NOT_ASSESSED");
            return;
        }
        if (!(vaccination.get("answers") instanceof Collection<?> answers) || answers.isEmpty()) {
            return;
        }
        java.util.Map<String, Object> valueByCode = new java.util.HashMap<>();
        for (Object raw : answers) {
            if (!(raw instanceof Map<?, ?> answer) || !known(answer)) {
                return;
            }
            if (answer.get("code") instanceof String code) {
                valueByCode.put(code, answer.get("value"));
            }
        }
        if ("NOT_RECEIVED".equals(valueByCode.get("RUBELLA_IMMUNITY"))) tags.add("RUBELLA_NONIMMUNE");
        if (valueByCode.containsKey("HEPATITIS_B") && !"UP_TO_DATE".equals(valueByCode.get("HEPATITIS_B"))) {
            tags.add("HEPATITIS_B_INCOMPLETE");
        }
        if (valueByCode.containsKey("INFLUENZA") && !"UP_TO_DATE".equals(valueByCode.get("INFLUENZA"))) {
            tags.add("INFLUENZA_DUE");
        }
        if (valueByCode.containsKey("COVID_19") && !"UP_TO_DATE".equals(valueByCode.get("COVID_19"))) {
            tags.add("COVID_19_UPDATE");
        }
    }

    private static boolean known(Map<?, ?> node) {
        return "KNOWN".equals(node.get("state"));
    }

    private static String lifestyleValue(Map<?, ?> lifestyle, String key) {
        if (lifestyle.get(key) instanceof Map<?, ?> node && known(node)
                && node.get("value") instanceof String value) {
            return value;
        }
        return null;
    }
}
