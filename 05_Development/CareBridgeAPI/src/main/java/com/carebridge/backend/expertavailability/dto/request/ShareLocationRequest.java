package com.carebridge.backend.expertavailability.dto.request;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Future;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import lombok.*;
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.UUID;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class ShareLocationRequest {
    @NotNull
    @DecimalMin(value = "-90.0")
    @DecimalMax(value = "90.0")
    private BigDecimal latitude;

    @NotNull
    @DecimalMin(value = "-180.0")
    @DecimalMax(value = "180.0")
    private BigDecimal longitude;

    @PositiveOrZero(message = "Độ chính xác vị trí không được âm")
    @DecimalMax(value = "10000", message = "Độ chính xác vị trí tối đa 10.000 mét")
    private BigDecimal accuracyMeters;

    private String availabilityStatus;

    @NotNull
    @Future
    private LocalDateTime expiresAt;

    @NotNull
    private UUID consentReference;
}
