package com.carebridge.backend.content.dto.response;

public record ExpertApprovalSummaryResponse(
    long all,
    long article,
    long faq,
    long checklist
) {}
