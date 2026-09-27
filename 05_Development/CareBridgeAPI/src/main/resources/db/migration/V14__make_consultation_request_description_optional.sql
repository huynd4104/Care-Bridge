-- Consultation request description became optional in the API contract
-- (CreateConsultationRequestRequest no longer requires it), but the baseline
-- kept the column NOT NULL, so requests without a description failed with 500.
ALTER TABLE public."expert_consultation_requests"
    ALTER COLUMN description DROP NOT NULL;
