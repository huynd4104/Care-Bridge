package com.carebridge.backend.checklist.policy;

import com.carebridge.backend.checklist.entity.ChecklistInstance;
import com.carebridge.backend.checklist.entity.ChecklistTaskInstance;
import com.carebridge.backend.content.entity.ChecklistItem;
import com.carebridge.backend.content.repository.ChecklistItemRepository;
import com.carebridge.backend.recommendation.service.RecommendationProfileTagResolver;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Component;

/**
 * Chống chỉ định của mục checklist theo tag khảo sát cá nhân hóa của người mẹ.
 *
 * <p>Mỗi mục checklist (care_item_templates.CHECKLIST_ENTRY) có thể khai báo
 * {@code configuration_jsonb.contraindications = ["KIDNEY_DISEASE", ...]}. Khi hồ sơ khảo sát
 * đang hiệu lực của người mẹ (chủ ngữ cảnh chăm sóc) chứa bất kỳ tag nào trong đó, mục bị ẩn
 * khỏi mọi màn hình đọc và không được tính là mục bắt buộc khi xét hoàn thành checklist.
 * Việc lọc thực hiện lúc đọc, nên khi mẹ cập nhật lại khảo sát, mục sẽ tự hiển thị lại.</p>
 */
@Component
public class ChecklistContraindicationPolicy {

    public static final String CONFIG_KEY = "contraindications";

    /** Tag được phép gắn — trùng mã questionnaire trên mobile, trừ các lựa chọn "không có". */
    public static final Set<String> ALLOWED_TAGS = Set.of(
            // Tiền sử sinh sản
            "PRIOR_PREGNANCY_LOSS", "PRIOR_RECURRENT_PREGNANCY_LOSS", "PRIOR_STILLBIRTH",
            "PRIOR_PRETERM_BIRTH", "PRIOR_MULTIPLE_PREGNANCY", "PRIOR_ECTOPIC_PREGNANCY",
            "PRIOR_PREECLAMPSIA", "PRIOR_GESTATIONAL_DIABETES",
            // Bệnh nền
            "DIABETES", "HYPERTENSION", "CARDIOVASCULAR_DISEASE", "KIDNEY_DISEASE",
            "THYROID_DISORDER", "ASTHMA", "EPILEPSY", "LUPUS", "AUTOIMMUNE_DISEASE", "ANEMIA",
            "PCOS", "ENDOMETRIOSIS", "INFERTILITY", "MENTAL_HEALTH_CONDITION",
            // Lối sống
            "SMOKING", "ALCOHOL_USE", "SUBSTANCE_USE", "SLEEP_CONCERN", "STRESS",
            "LOW_ACTIVITY", "UNHEALTHY_DIET",
            // Dinh dưỡng
            "FOLIC_ACID_NOT_STARTED", "IODINE_UNASSESSED_OR_INSUFFICIENT",
            "VITAMIN_D_INSUFFICIENT_OR_SUPPLEMENT", "IRON_INSUFFICIENT_OR_SUPPLEMENT",
            "CALCIUM_INSUFFICIENT_OR_SUPPLEMENT",
            // Tiêm chủng
            "NOT_ASSESSED", "RUBELLA_NONIMMUNE", "HEPATITIS_B_INCOMPLETE", "INFLUENZA_DUE",
            "COVID_19_UPDATE",
            // Thuốc đang dùng
            "HIGH_RISK_OR_CONTRAINDICATED", "NEEDS_ADJUSTMENT",
            // Sức khỏe tình dục
            "SAFE_SEX_COUNSELING_NEEDED", "STI_RISK", "REPRODUCTIVE_TRACT_INFECTION",
            "STI_SUSPECTED_OR_KNOWN", "NO_PREGNANCY_PLAN");

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private final ChecklistItemRepository itemRepository;
    private final RecommendationProfileTagResolver tagResolver;

    public ChecklistContraindicationPolicy(
            ChecklistItemRepository itemRepository,
            RecommendationProfileTagResolver tagResolver) {
        this.itemRepository = itemRepository;
        this.tagResolver = tagResolver;
    }

    /** Đọc danh sách tag chống chỉ định từ configuration_jsonb của mục checklist. */
    public static List<String> parse(String configurationJson) {
        if (configurationJson == null || configurationJson.isBlank()) {
            return List.of();
        }
        try {
            JsonNode node = OBJECT_MAPPER.readTree(configurationJson);
            JsonNode tags = node == null ? null : node.get(CONFIG_KEY);
            if (tags == null || !tags.isArray()) {
                return List.of();
            }
            Set<String> result = new LinkedHashSet<>();
            tags.forEach(tag -> {
                if (tag.isTextual() && !tag.asText().isBlank()) {
                    result.add(tag.asText().trim());
                }
            });
            return List.copyOf(result);
        } catch (Exception ignored) {
            return List.of();
        }
    }

    public static boolean isContraindicated(ChecklistItem item, Set<String> profileTags) {
        if (item == null || profileTags == null || profileTags.isEmpty()) {
            return false;
        }
        return parse(item.getConfigurationJson()).stream().anyMatch(profileTags::contains);
    }

    /** Tag khảo sát đang hiệu lực của người mẹ. */
    public Set<String> profileTags(UUID motherUserId) {
        return tagResolver.activeTags(motherUserId);
    }

    /** ID mục checklist (template item) bị chống chỉ định với tập tag đã cho. */
    public Set<UUID> hiddenItemIds(Set<String> profileTags, Collection<ChecklistItem> items) {
        if (profileTags == null || profileTags.isEmpty() || items == null) {
            return Set.of();
        }
        Set<UUID> hidden = new HashSet<>();
        for (ChecklistItem item : items) {
            if (isContraindicated(item, profileTags)) {
                hidden.add(item.getId());
            }
        }
        return hidden;
    }

    /**
     * ID task instance bị ẩn. Tag được lấy theo chủ ngữ cảnh chăm sóc (người mẹ) của từng
     * checklist instance, không theo người đang xem (người nhà/chuyên gia).
     */
    public Set<UUID> hiddenTaskIds(
            Collection<ChecklistInstance> instances,
            Collection<ChecklistTaskInstance> tasks) {
        if (instances == null || instances.isEmpty() || tasks == null || tasks.isEmpty()) {
            return Set.of();
        }
        Map<UUID, UUID> ownerByInstance = new HashMap<>();
        for (ChecklistInstance instance : instances) {
            ownerByInstance.put(instance.getId(), instance.getContextOwnerUserId());
        }
        Map<UUID, Set<String>> tagsByOwner = new HashMap<>();
        for (UUID owner : new HashSet<>(ownerByInstance.values())) {
            if (owner != null) {
                tagsByOwner.put(owner, profileTags(owner));
            }
        }
        if (tagsByOwner.values().stream().allMatch(Set::isEmpty)) {
            return Set.of();
        }
        List<UUID> itemIds = tasks.stream()
                .map(ChecklistTaskInstance::getTemplateItemVersionId)
                .filter(Objects::nonNull)
                .distinct()
                .toList();
        if (itemIds.isEmpty()) {
            return Set.of();
        }
        Map<UUID, List<String>> contraindicationsByItem = new HashMap<>();
        for (ChecklistItem item : itemRepository.findAllById(itemIds)) {
            List<String> tags = parse(item.getConfigurationJson());
            if (!tags.isEmpty()) {
                contraindicationsByItem.put(item.getId(), tags);
            }
        }
        if (contraindicationsByItem.isEmpty()) {
            return Set.of();
        }
        Set<UUID> hidden = new HashSet<>();
        for (ChecklistTaskInstance task : tasks) {
            List<String> tags = contraindicationsByItem.get(task.getTemplateItemVersionId());
            if (tags == null) {
                continue;
            }
            Set<String> ownerTags = tagsByOwner.getOrDefault(
                    ownerByInstance.get(task.getChecklistInstanceId()), Set.of());
            if (tags.stream().anyMatch(ownerTags::contains)) {
                hidden.add(task.getId());
            }
        }
        return hidden;
    }

    /**
     * Quy tắc hoàn thành dùng chung cho sequence (resolver + advance): checklist phải có mục
     * bắt buộc, và mọi mục bắt buộc còn hiển thị (không bị chống chỉ định) đã hoàn thành.
     */
    public static boolean allVisibleRequiredCompleted(
            Collection<ChecklistTaskInstance> tasks, Set<UUID> hiddenTaskIds) {
        Set<UUID> hidden = hiddenTaskIds == null ? Set.of() : hiddenTaskIds;
        boolean hasRequired = false;
        for (ChecklistTaskInstance task : tasks) {
            if (!Boolean.TRUE.equals(task.getRequired())) {
                continue;
            }
            hasRequired = true;
            if (!hidden.contains(task.getId())
                    && task.getStatus() != com.carebridge.backend.checklist.model.ChecklistTaskStatus.COMPLETED) {
                return false;
            }
        }
        return hasRequired;
    }

    /** Tiện ích cho các nơi chỉ xét một checklist instance. */
    public Set<UUID> hiddenTaskIds(ChecklistInstance instance, Collection<ChecklistTaskInstance> tasks) {
        return instance == null ? Set.of() : hiddenTaskIds(List.of(instance), tasks);
    }
}
