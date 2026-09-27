package com.carebridge.backend.family.dto;

import com.carebridge.backend.family.entity.GroupMemberRole;
import com.carebridge.backend.common.validation.DeliverableEmail;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class InviteCareGroupMemberRequest {

    @NotBlank
    @DeliverableEmail
    private String email;

    /** Defaults to MEMBER when omitted. */
    private GroupMemberRole memberRole;
}
