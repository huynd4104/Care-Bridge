package com.carebridge.backend.content.dto.response;

import com.carebridge.backend.checklist.model.ChecklistTargetSubject;
import com.carebridge.backend.checklist.model.ChecklistSupportFunction;
import java.util.List;
import java.util.UUID;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import com.fasterxml.jackson.annotation.JsonInclude;

@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ChecklistItemResponse {

    private UUID id;
    private String itemText;
    private String description;
    private Integer order;
    private Boolean isRequired;
    private ChecklistTargetSubject targetSubject;
    private ChecklistSupportFunction supportFunction;
    private Boolean repeatWeekly;
    private Boolean repeatDaily;
    private String sourceUrl;
    /** Tag khảo sát chống chỉ định của mục; rỗng nếu mục phù hợp với mọi người mẹ. */
    private List<String> contraindications;

    /** Compatibility constructor for the pre-contraindication response shape. */
    public ChecklistItemResponse(
            UUID id,
            String itemText,
            String description,
            Integer order,
            Boolean isRequired,
            ChecklistTargetSubject targetSubject,
            ChecklistSupportFunction supportFunction,
            Boolean repeatWeekly,
            Boolean repeatDaily,
            String sourceUrl) {
        this(id, itemText, description, order, isRequired, targetSubject, supportFunction,
                repeatWeekly, repeatDaily, sourceUrl, null);
    }

    /** Compatibility constructor for the pre-detail response shape. */
    public ChecklistItemResponse(
            UUID id,
            String itemText,
            Integer order,
            Boolean isRequired,
            ChecklistTargetSubject targetSubject) {
        this(id, itemText, null, order, isRequired, targetSubject, null, false, false, null);
    }

    /** Compatibility constructor for the pre-source-link response shape. */
    public ChecklistItemResponse(
            UUID id,
            String itemText,
            String description,
            Integer order,
            Boolean isRequired,
            ChecklistTargetSubject targetSubject,
            ChecklistSupportFunction supportFunction,
            Boolean repeatWeekly,
            Boolean repeatDaily) {
        this(id, itemText, description, order, isRequired, targetSubject, supportFunction,
                repeatWeekly, repeatDaily, null);
    }
}
