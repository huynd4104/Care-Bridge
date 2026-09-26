package com.carebridge.backend.expertverification;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.carebridge.backend.audit.service.AuditService;
import com.carebridge.backend.expert.entity.ExpertProfile;
import com.carebridge.backend.expert.exception.ExpertException;
import com.carebridge.backend.expert.repository.ExpertProfileRepository;
import com.carebridge.backend.expertverification.dto.request.SubmitCredentialRequest;
import com.carebridge.backend.expertverification.mapper.ExpertCredentialMapper;
import com.carebridge.backend.expertverification.repository.ExpertCredentialRepository;
import com.carebridge.backend.expertverification.service.impl.ExpertCredentialServiceImpl;
import com.carebridge.backend.file.service.IFileService;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockMultipartFile;

/**
 * Ngày cấp và ngày hết hạn chứng chỉ phải được chặn ở backend. Web chỉ kiểm tra ở bước
 * onboarding, còn trang "Chứng chỉ & Giấy tờ" và app thì không, nên trước đây nộp được
 * chứng chỉ cấp ở tương lai hoặc hết hạn trước cả ngày cấp.
 */
@ExtendWith(MockitoExtension.class)
class ExpertCredentialDateValidationTest {

    private static final LocalDate TODAY = LocalDate.now(ZoneId.of("Asia/Ho_Chi_Minh"));

    @Mock private ExpertCredentialRepository credentialRepository;
    @Mock private ExpertProfileRepository expertProfileRepository;
    @Mock private ExpertCredentialMapper credentialMapper;
    @Mock private IFileService fileService;
    @Mock private AuditService auditService;

    @InjectMocks private ExpertCredentialServiceImpl service;

    private final UUID userId = UUID.randomUUID();
    private final MockMultipartFile file =
            new MockMultipartFile("file", "license.pdf", "application/pdf", new byte[] {1, 2, 3});

    @BeforeEach
    void profileExists() {
        when(expertProfileRepository.findByUserId(userId))
                .thenReturn(Optional.of(ExpertProfile.builder().expertProfileId(userId).build()));
    }

    @Test
    void rejectsIssueDateInTheFuture() {
        assertRejected(request(TODAY.plusDays(1), null), "Ngày cấp không được ở tương lai");
    }

    @Test
    void rejectsExpiryDateOnOrBeforeIssueDate() {
        assertRejected(request(TODAY.minusYears(1), TODAY.minusYears(2)), "Ngày hết hạn phải sau ngày cấp");
        assertRejected(request(TODAY.minusYears(1), TODAY.minusYears(1)), "Ngày hết hạn phải sau ngày cấp");
    }

    @Test
    void rejectsCredentialThatHasAlreadyExpired() {
        assertRejected(request(TODAY.minusYears(5), TODAY.minusDays(1)),
                "Chứng chỉ đã hết hạn, vui lòng nộp chứng chỉ còn hiệu lực");
    }

    @Test
    void rejectsImplausiblyOldIssueDate() {
        assertRejected(request(LocalDate.of(1900, 1, 1), null), "Ngày cấp không hợp lệ");
    }

    private void assertRejected(SubmitCredentialRequest request, String message) {
        assertThatThrownBy(() -> service.submitCredential(userId, request, file))
                .isInstanceOf(ExpertException.class)
                .hasMessage(message);
        // Chặn trước khi tải tệp lên, để không để lại tệp mồ côi trong kho lưu trữ.
        verify(fileService, never()).uploadPrivateFile(any(), any());
    }

    private static SubmitCredentialRequest request(LocalDate issued, LocalDate expiry) {
        SubmitCredentialRequest request = new SubmitCredentialRequest();
        request.setCredentialType("MEDICAL_LICENSE");
        request.setCredentialNumber("0123/HCM-CCHN");
        request.setIssuer("Sở Y tế TP.HCM");
        request.setIssuedDate(issued.toString());
        request.setExpiryDate(expiry == null ? null : expiry.toString());
        return request;
    }
}
