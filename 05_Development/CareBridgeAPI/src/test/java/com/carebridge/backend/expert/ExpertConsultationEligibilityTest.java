package com.carebridge.backend.expert;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.carebridge.backend.expert.entity.ExpertProfile;
import com.carebridge.backend.audit.entity.AuditAction;
import com.carebridge.backend.expert.exception.ExpertException;
import com.carebridge.backend.expert.mapper.ExpertProfileMapper;
import com.carebridge.backend.expert.repository.ExpertProfileRepository;
import com.carebridge.backend.expert.repository.ProfessionalSpecialtyRepository;
import com.carebridge.backend.expert.service.impl.ExpertProfileServiceImpl;
import com.carebridge.backend.expert.truststatus.TrustStatus;
import com.carebridge.backend.expert.verificationstatus.VerificationStatus;
import com.carebridge.backend.security.repository.UserRepository;
import com.carebridge.backend.audit.service.AuditService;
import com.carebridge.backend.expertverification.entity.ExpertCredential;
import com.carebridge.backend.expertverification.entity.ExpertIdentityVerification;
import com.carebridge.backend.expertverification.enums.IdentityReviewStatus;
import com.carebridge.backend.expertverification.repository.ExpertCredentialRepository;
import com.carebridge.backend.expertverification.repository.ExpertIdentityVerificationRepository;
import com.carebridge.backend.expertverification.reviewstatus.ReviewStatus;
import com.carebridge.backend.masterdata.repository.SpecialtyRepository;
import com.carebridge.backend.map.repository.CareFacilityRepository;
import com.carebridge.backend.security.entity.User;
import com.carebridge.backend.security.service.EmailService;
import com.carebridge.backend.security.service.impl.GmailEmailService;
import jakarta.mail.Multipart;
import jakarta.mail.Part;
import jakarta.mail.Session;
import jakarta.mail.internet.MimeMessage;
import java.util.Properties;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import com.carebridge.backend.expertavailability.repository.ExpertAvailabilityRepository;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@ExtendWith(MockitoExtension.class)
class ExpertConsultationEligibilityTest {

    @Mock private ExpertProfileRepository repository;
    @Mock private UserRepository userRepository;
    @Mock private SpecialtyRepository specialtyRepository;
    @Mock private CareFacilityRepository careFacilityRepository;
    @Mock private ProfessionalSpecialtyRepository professionalSpecialtyRepository;
    @Mock private ExpertAvailabilityRepository expertAvailabilityRepository;
    @Mock private ExpertIdentityVerificationRepository identityRepository;
    @Mock private ExpertCredentialRepository credentialRepository;
    @Mock private AuditService auditService;
    @Mock private EmailService emailService;

    private final ExpertProfileMapper mapper = new ExpertProfileMapper();

    @Test
    void mapperExposesOnlyTheDerivedEligibilityBooleanOnBothPublicDtos() {
        ExpertProfile eligible = profile(VerificationStatus.APPROVED, TrustStatus.ACTIVE);
        eligible.setConsultationScope("Postpartum nutrition");
        ExpertProfile suspended = profile(VerificationStatus.APPROVED, TrustStatus.SUSPENDED);

        assertThat(mapper.toResponse(eligible, "Expert", null).isConsultationEligible())
                .isTrue();
        assertThat(mapper.toDetailResponse(eligible, "Expert", null)
                .isConsultationEligible()).isTrue();
        assertThat(mapper.toDetailResponse(eligible, "Expert", null)
                .getConsultationScope()).isEqualTo("Postpartum nutrition");
        assertThat(mapper.toResponse(suspended, "Expert", null).isConsultationEligible())
                .isFalse();
        assertThat(mapper.toDetailResponse(suspended, "Expert", null)
                .isConsultationEligible()).isFalse();
    }

    @Test
    void publicProfileIsHiddenWhenTrustIsNotActive() {
        ExpertProfile suspended = profile(VerificationStatus.APPROVED, TrustStatus.SUSPENDED);
        when(repository.findById(suspended.getExpertProfileId()))
                .thenReturn(Optional.of(suspended));
        ExpertProfileServiceImpl service =
                new ExpertProfileServiceImpl(repository, userRepository, mapper,
                        identityRepository, credentialRepository, auditService,
                        specialtyRepository, careFacilityRepository, professionalSpecialtyRepository, expertAvailabilityRepository, emailService);

        assertThatThrownBy(() -> service.getPublicProfile(suspended.getExpertProfileId()))
                .isInstanceOfSatisfying(ExpertException.class,
                        error -> assertThat(error.getCode()).isEqualTo("EXPERT-004"));
    }

    @Test
    void everyEligibilityMutationUsesTheSameExpertRowLock() {
        UUID profileId = UUID.randomUUID();
        UUID adminId = UUID.randomUUID();
        ExpertProfile approve = profile(VerificationStatus.PENDING, TrustStatus.ACTIVE);
        approve.setExpertProfileId(profileId);
        ExpertProfile reject = profile(VerificationStatus.UNDER_REVIEW, TrustStatus.ACTIVE);
        reject.setExpertProfileId(profileId);
        ExpertProfile trust = profile(VerificationStatus.APPROVED, TrustStatus.ACTIVE);
        trust.setExpertProfileId(profileId);
        when(repository.findByIdForUpdate(profileId))
                .thenReturn(Optional.of(approve), Optional.of(reject), Optional.of(trust));
        when(repository.save(any())).thenAnswer(invocation -> invocation.getArgument(0));
        when(identityRepository.findFirstByExpertProfileIdOrderByCreatedAtDesc(profileId))
                .thenReturn(Optional.of(ExpertIdentityVerification.builder()
                        .reviewStatus(IdentityReviewStatus.APPROVED).build()));
        when(credentialRepository.findByExpertProfileIdAndReviewStatus(profileId, ReviewStatus.APPROVED))
                .thenReturn(java.util.List.of(ExpertCredential.builder()
                        .credentialType("MEDICAL_LICENSE")
                        .reviewStatus(ReviewStatus.APPROVED)
                        .build()));
        ExpertProfileServiceImpl service =
                new ExpertProfileServiceImpl(repository, userRepository, mapper,
                        identityRepository, credentialRepository, auditService,
                        specialtyRepository, careFacilityRepository, professionalSpecialtyRepository, expertAvailabilityRepository, emailService);

        service.approveExpert(profileId, adminId);
        service.rejectExpert(profileId, adminId, "reason");
        service.setTrustStatus(profileId, TrustStatus.REVOKED, adminId);

        verify(repository, times(3)).findByIdForUpdate(profileId);
        verify(repository, never()).findById(profileId);
        verify(repository, times(3)).save(any());
    }

    @Test
    void rejectionNotifiesTheExpertByEmail() {
        UUID userId = UUID.randomUUID();
        UUID profileId = userId;
        UUID adminId = UUID.randomUUID();
        ExpertProfile profile = profile(VerificationStatus.UNDER_REVIEW, TrustStatus.ACTIVE);
        profile.setExpertProfileId(profileId);
        when(repository.findByIdForUpdate(profileId)).thenReturn(Optional.of(profile));
        when(repository.save(profile)).thenReturn(profile);
        when(userRepository.findById(userId)).thenReturn(Optional.of(User.builder()
                .id(userId)
                .name("Bác sĩ An")
                .email("expert@example.com")
                .build()));

        service().rejectExpert(profileId, adminId, "  Thiếu giấy phép hành nghề  ");

        assertThat(profile.getVerificationStatus()).isEqualTo(VerificationStatus.REJECTED);
        verify(emailService).sendExpertRejectionEmail(
                "expert@example.com", "Bác sĩ An", "Thiếu giấy phép hành nghề");
    }

    @Test
    void rejectionSkipsEmailWhenTheAccountHasNoEmailAddress() {
        UUID userId = UUID.randomUUID();
        UUID profileId = userId;
        ExpertProfile profile = profile(VerificationStatus.PENDING, TrustStatus.ACTIVE);
        profile.setExpertProfileId(profileId);
        when(repository.findByIdForUpdate(profileId)).thenReturn(Optional.of(profile));
        when(repository.save(profile)).thenReturn(profile);
        when(userRepository.findById(userId)).thenReturn(Optional.of(User.builder()
                .id(userId)
                .name("Bác sĩ An")
                .email(" ")
                .build()));

        service().rejectExpert(profileId, UUID.randomUUID(), "Thiếu giấy phép hành nghề");

        assertThat(profile.getVerificationStatus()).isEqualTo(VerificationStatus.REJECTED);
        verifyNoInteractions(emailService);
    }

    @Test
    void rejectionStillSucceedsWhenEmailDeliveryFails() {
        UUID userId = UUID.randomUUID();
        UUID profileId = userId;
        UUID adminId = UUID.randomUUID();
        ExpertProfile profile = profile(VerificationStatus.PENDING, TrustStatus.ACTIVE);
        profile.setExpertProfileId(profileId);
        when(repository.findByIdForUpdate(profileId)).thenReturn(Optional.of(profile));
        when(repository.save(profile)).thenReturn(profile);
        when(userRepository.findById(userId)).thenReturn(Optional.of(User.builder()
                .id(userId)
                .name("Bác sĩ An")
                .email("expert@example.com")
                .build()));
        doThrow(new IllegalStateException("SMTP unavailable"))
                .when(emailService)
                .sendExpertRejectionEmail(any(), any(), any());

        assertThatCode(() -> service().rejectExpert(
                profileId, adminId, "Thiếu giấy phép hành nghề"))
                .doesNotThrowAnyException();
        assertThat(profile.getVerificationStatus()).isEqualTo(VerificationStatus.REJECTED);
        verify(repository).save(profile);
        verify(auditService).log(
                eq(AuditAction.EXPERT_VERIFICATION), eq(adminId), eq("ExpertProfile"),
                eq(profileId.toString()), any());
    }

    @Test
    void rejectionDefersEmailUntilTheTransactionCommits() {
        UUID userId = UUID.randomUUID();
        UUID profileId = userId;
        ExpertProfile profile = profile(VerificationStatus.PENDING, TrustStatus.ACTIVE);
        profile.setExpertProfileId(profileId);
        when(repository.findByIdForUpdate(profileId)).thenReturn(Optional.of(profile));
        when(repository.save(profile)).thenReturn(profile);
        when(userRepository.findById(userId)).thenReturn(Optional.of(User.builder()
                .id(userId)
                .name("Bác sĩ An")
                .email("expert@example.com")
                .build()));

        TransactionSynchronizationManager.initSynchronization();
        try {
            service().rejectExpert(profileId, UUID.randomUUID(), "Thiếu giấy phép hành nghề");
            verifyNoInteractions(emailService);

            TransactionSynchronizationManager.getSynchronizations()
                    .forEach(synchronization -> synchronization.afterCommit());

            verify(emailService).sendExpertRejectionEmail(
                    "expert@example.com", "Bác sĩ An", "Thiếu giấy phép hành nghề");
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
        }
    }

    @Test
    void rejectionEmailEscapesUntrustedHtmlContent() throws Exception {
        JavaMailSender mailSender = mock(JavaMailSender.class);
        MimeMessage message = new MimeMessage(Session.getInstance(new Properties()));
        when(mailSender.createMimeMessage()).thenReturn(message);
        doAnswer(invocation -> {
            ((MimeMessage) invocation.getArgument(0)).saveChanges();
            return null;
        }).when(mailSender).send(any(MimeMessage.class));
        GmailEmailService gmailEmailService = new GmailEmailService(mailSender);
        ReflectionTestUtils.setField(gmailEmailService, "fromAddress", "noreply@carebridge.test");
        ReflectionTestUtils.setField(gmailEmailService, "fromName", "CareBridge");

        gmailEmailService.sendExpertRejectionEmail(
                "expert@example.com", "<b>Doctor An</b>", "<script>alert('x')</script>");

        String html = findHtmlContent(message);
        assertThat(html)
                .contains("&lt;b&gt;Doctor An&lt;/b&gt;")
                .contains("&lt;script&gt;alert(&#39;x&#39;)&lt;/script&gt;")
                .doesNotContain("<script>");
    }

    private static String findHtmlContent(Part part) throws Exception {
        if (part.isMimeType("text/html")) {
            return part.getContent().toString();
        }
        if (part.isMimeType("multipart/*")) {
            Multipart multipart = (Multipart) part.getContent();
            for (int index = 0; index < multipart.getCount(); index++) {
                String html = findHtmlContent(multipart.getBodyPart(index));
                if (!html.isEmpty()) {
                    return html;
                }
            }
        }
        return "";
    }

    private ExpertProfileServiceImpl service() {
        return new ExpertProfileServiceImpl(repository, userRepository, mapper,
                identityRepository, credentialRepository, auditService,
                specialtyRepository, careFacilityRepository,
                professionalSpecialtyRepository, expertAvailabilityRepository, emailService);
    }

    private static ExpertProfile profile(
            VerificationStatus verificationStatus, TrustStatus trustStatus) {
        return ExpertProfile.builder()
                .expertProfileId(UUID.randomUUID())
                .userId(UUID.randomUUID())
                .verificationStatus(verificationStatus)
                .trustStatus(trustStatus)
                .build();
    }
}
