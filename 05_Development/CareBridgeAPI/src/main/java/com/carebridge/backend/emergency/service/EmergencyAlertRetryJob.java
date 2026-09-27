package com.carebridge.backend.emergency.service;

import com.carebridge.backend.emergency.event.EmergencySessionOpened;
import com.carebridge.backend.emergency.repository.IEmergencySessionRepository;
import java.time.Duration;
import java.time.Instant;
import java.util.UUID;
import lombok.RequiredArgsConstructor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
public class EmergencyAlertRetryJob {
    private static final Logger log = LoggerFactory.getLogger(EmergencyAlertRetryJob.class);
    private static final Duration RETRY_DELAY = Duration.ofMinutes(1);
    // Sessions left ACTIVE longer than this stop re-sending, so a stale alert cannot
    // surface unexpectedly later (e.g. once a family member is linked) mid-countdown of a new fall.
    private static final Duration MAX_RETRY_AGE = Duration.ofMinutes(15);

    private final IEmergencySessionRepository emergencySessionRepository;
    private final IFamilyAlertService familyAlertService;

    @Scheduled(fixedDelayString = "${carebridge.emergency.alert-retry-delay-ms:60000}")
    public void retryPendingAlerts() {
        Instant now = Instant.now();
        for (UUID sessionId : emergencySessionRepository
                .findAlertRetryCandidates(now.minus(RETRY_DELAY), now.minus(MAX_RETRY_AGE))) {
            emergencySessionRepository.findById(sessionId).ifPresent(session -> {
                try {
                    familyAlertService.sendAlert(new EmergencySessionOpened(
                            UUID.randomUUID(), session.getId(), session.getUserId(),
                            session.getTriggerSource(), session.getUserLatitude(),
                            session.getUserLongitude(), session.getCreatedAt()));
                } catch (RuntimeException exception) {
                    log.warn("Emergency alert retry failed session={} reason={}",
                            sessionId, exception.getClass().getSimpleName());
                }
            });
        }
    }
}
