package com.carebridge.backend.expertavailability.dto.request;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import lombok.*;
import java.time.Instant;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CreateAvailabilityRequest {
    @NotNull(message = "Vui lòng chọn giờ bắt đầu")
    private Instant startAt;

    @NotNull(message = "Vui lòng chọn giờ kết thúc")
    private Instant endAt;

    @NotNull(message = "Vui lòng chọn hình thức tư vấn")
    @Pattern(regexp = "ONLINE_CHAT|CHAT|VIDEO|VOICE|AUDIO|IN_PERSON",
            message = "Hình thức tư vấn không hợp lệ")
    private String channelType;

    private String status;
}
