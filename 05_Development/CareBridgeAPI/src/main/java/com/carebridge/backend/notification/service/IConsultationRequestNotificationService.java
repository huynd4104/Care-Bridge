package com.carebridge.backend.notification.service;

import java.util.UUID;

public interface IConsultationRequestNotificationService {
    void notifyCreated(UUID expertUserId, UUID requesterUserId, UUID requestId);

    void notifyAccepted(UUID requesterUserId, UUID expertUserId, UUID requestId);

    void notifyRejected(UUID requesterUserId, UUID expertUserId, UUID requestId);

    default void notifyRejected(UUID requesterUserId, UUID expertUserId, UUID requestId, String reason) {
        notifyRejected(requesterUserId, expertUserId, requestId);
    }

    void notifyCancelled(UUID expertUserId, UUID requesterUserId, UUID requestId);

    void notifyExpired(UUID requesterUserId, UUID expertUserId, UUID requestId);

    void retryPendingNotifications();
}
