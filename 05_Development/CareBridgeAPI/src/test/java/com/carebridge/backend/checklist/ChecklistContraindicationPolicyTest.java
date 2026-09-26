package com.carebridge.backend.checklist;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.carebridge.backend.checklist.entity.ChecklistInstance;
import com.carebridge.backend.checklist.entity.ChecklistTaskInstance;
import com.carebridge.backend.checklist.model.ChecklistTaskStatus;
import com.carebridge.backend.checklist.policy.ChecklistContraindicationPolicy;
import com.carebridge.backend.content.entity.ChecklistItem;
import com.carebridge.backend.content.repository.ChecklistItemRepository;
import com.carebridge.backend.recommendation.service.RecommendationProfileTagResolver;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class ChecklistContraindicationPolicyTest {

    private final UUID mother = UUID.randomUUID();
    private final UUID instanceId = UUID.randomUUID();
    private final UUID walkingItemId = UUID.randomUUID();
    private final UUID kegelItemId = UUID.randomUUID();

    @Test
    void extractsSurveyTagsLikeTheMobileQuestionnaire() {
        Map<String, Object> profile = Map.of(
                "underlyingConditions", Map.of("state", "KNOWN", "codes", List.of("HYPERTENSION", "NONE_KNOWN")),
                "reproductiveHistory", Map.of("state", "KNOWN", "codes", List.of("PRIOR_PRETERM_BIRTH")),
                "nutrition", Map.of("state", "UNKNOWN", "codes", List.of("CALCIUM_INSUFFICIENT_OR_SUPPLEMENT")),
                "lifestyle", Map.of(
                        "smoking", Map.of("state", "KNOWN", "value", "CURRENT"),
                        "alcohol", Map.of("state", "KNOWN", "value", "NONE"),
                        "physicalActivity", Map.of("state", "KNOWN", "value", "LOW"),
                        "flags", List.of("STRESS")),
                "vaccination", Map.of("answers", List.of(
                        Map.of("code", "RUBELLA_IMMUNITY", "state", "KNOWN", "value", "NOT_RECEIVED"),
                        Map.of("code", "INFLUENZA", "state", "KNOWN", "value", "UP_TO_DATE"))));

        assertThat(RecommendationProfileTagResolver.extractTags(profile)).containsExactlyInAnyOrder(
                "HYPERTENSION", "PRIOR_PRETERM_BIRTH", "SMOKING", "LOW_ACTIVITY", "STRESS",
                "RUBELLA_NONIMMUNE");
    }

    @Test
    void emptyOrMissingProfileHasNoTags() {
        assertThat(RecommendationProfileTagResolver.extractTags(null)).isEmpty();
        assertThat(RecommendationProfileTagResolver.extractTags(Map.of(
                "underlyingConditions", Map.of("state", "KNOWN", "codes", List.of("NONE_KNOWN"))))).isEmpty();
    }

    @Test
    void hidesOnlyTasksWhoseItemMatchesTheMothersCurrentTags() {
        var fixture = fixture(Set.of("HYPERTENSION"));

        Set<UUID> hidden = fixture.policy().hiddenTaskIds(List.of(fixture.instance()), fixture.tasks());

        assertThat(hidden).containsExactly(fixture.tasks().get(0).getId());
    }

    @Test
    void updatedSurveyWithoutTheConditionShowsTheTaskAgain() {
        var fixture = fixture(Set.of("DIABETES"));

        assertThat(fixture.policy().hiddenTaskIds(List.of(fixture.instance()), fixture.tasks())).isEmpty();
    }

    @Test
    void noProfileTagsSkipsItemLookup() {
        var fixture = fixture(Set.of());

        assertThat(fixture.policy().hiddenTaskIds(List.of(fixture.instance()), fixture.tasks())).isEmpty();
        verify(fixture.items(), never()).findAllById(any());
    }

    @Test
    void hiddenRequiredTasksDoNotBlockCompletion() {
        var fixture = fixture(Set.of("HYPERTENSION"));
        ChecklistTaskInstance walking = fixture.tasks().get(0);
        ChecklistTaskInstance kegel = fixture.tasks().get(1);
        kegel.setStatus(ChecklistTaskStatus.COMPLETED);

        assertThat(ChecklistContraindicationPolicy.allVisibleRequiredCompleted(
                fixture.tasks(), Set.of())).isFalse();
        assertThat(ChecklistContraindicationPolicy.allVisibleRequiredCompleted(
                fixture.tasks(), Set.of(walking.getId()))).isTrue();
        assertThat(ChecklistContraindicationPolicy.allVisibleRequiredCompleted(
                List.of(), Set.of())).isFalse();
    }

    @Test
    void parsesContraindicationsFromItemConfiguration() {
        assertThat(ChecklistContraindicationPolicy.parse(
                "{\"sourceUrl\":\"https://x\",\"contraindications\":[\"ANEMIA\",\"LUPUS\"]}"))
                .containsExactly("ANEMIA", "LUPUS");
        assertThat(ChecklistContraindicationPolicy.parse("{}")).isEmpty();
        assertThat(ChecklistContraindicationPolicy.parse("not json")).isEmpty();
    }

    private Fixture fixture(Set<String> motherTags) {
        ChecklistItemRepository items = mock(ChecklistItemRepository.class);
        RecommendationProfileTagResolver resolver = mock(RecommendationProfileTagResolver.class);
        when(resolver.activeTags(mother)).thenReturn(motherTags);
        when(items.findAllById(any())).thenReturn(List.of(
                ChecklistItem.builder().id(walkingItemId)
                        .configurationJson("{\"contraindications\":[\"CARDIOVASCULAR_DISEASE\",\"HYPERTENSION\"]}")
                        .build(),
                ChecklistItem.builder().id(kegelItemId).configurationJson("{}").build()));
        ChecklistInstance instance = ChecklistInstance.builder()
                .id(instanceId).contextOwnerUserId(mother).recipientUserId(mother).build();
        List<ChecklistTaskInstance> tasks = List.of(
                task(walkingItemId), task(kegelItemId));
        return new Fixture(new ChecklistContraindicationPolicy(items, resolver), items, instance, tasks);
    }

    private ChecklistTaskInstance task(UUID itemId) {
        return ChecklistTaskInstance.builder()
                .id(UUID.randomUUID())
                .checklistInstanceId(instanceId)
                .templateItemVersionId(itemId)
                .required(true)
                .status(ChecklistTaskStatus.PENDING)
                .build();
    }

    private record Fixture(
            ChecklistContraindicationPolicy policy,
            ChecklistItemRepository items,
            ChecklistInstance instance,
            List<ChecklistTaskInstance> tasks) {
    }
}
