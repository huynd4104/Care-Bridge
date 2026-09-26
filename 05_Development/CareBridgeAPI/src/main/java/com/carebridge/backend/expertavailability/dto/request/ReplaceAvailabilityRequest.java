package com.carebridge.backend.expertavailability.dto.request;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import java.time.LocalDate;
import java.util.List;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ReplaceAvailabilityRequest {

    @NotEmpty
    private List<@NotNull LocalDate> targetDates;

    @NotNull
    private String timeZone;

    @NotNull(message = "Vui lòng chọn hình thức tư vấn")
    @Pattern(regexp = "ONLINE_CHAT|CHAT|VIDEO|VOICE|AUDIO|IN_PERSON",
            message = "Hình thức tư vấn không hợp lệ")
    private String channelType;

    @NotNull
    @Valid
    private List<HourlyAvailabilitySlotRequest> slots;
}
