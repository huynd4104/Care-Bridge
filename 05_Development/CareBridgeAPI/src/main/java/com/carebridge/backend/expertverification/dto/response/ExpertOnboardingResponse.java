package com.carebridge.backend.expertverification.dto.response;

import com.carebridge.backend.expert.verificationstatus.VerificationStatus;
import lombok.*;

@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ExpertOnboardingResponse {
    private boolean profileExists;
    private String identityStatus;
    private String credentialStatus;
    private VerificationStatus verificationStatus;
    /** COMMUNITY | PENDING_CONTRACT | CONTRACTED | null (chưa chọn hình thức). */
    private String expertType;
    private String rejectionReason;
    /**
     * Bước mà quản trị viên chấm là sai, để giao diện mở đúng chỗ đó cho chuyên gia
     * sửa thay vì bắt họ dò lại cả luồng. null khi hồ sơ không bị từ chối.
     */
    private String rejectedStep;
    /** Hồ sơ đang ở trạng thái được phép nộp lại cho quản trị viên xét lần nữa. */
    private boolean canResubmit;
    private String nextStep;
    private IdentityVerificationResponse latestIdentityAttempt;
}
