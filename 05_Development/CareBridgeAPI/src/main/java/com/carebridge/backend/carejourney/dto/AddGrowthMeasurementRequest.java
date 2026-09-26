package com.carebridge.backend.carejourney.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDate;

@Data
public class AddGrowthMeasurementRequest {
    @NotNull
    private LocalDate measuredDate;

    // Trẻ 0–24 tháng: WHO +3SD lúc 24 tháng ≈ 17–18 kg; cận dưới chừa cho trẻ sinh non.
    @DecimalMin(value = "0.5", message = "weightKg must be between 0.5 and 20 kg")
    @DecimalMax(value = "20.0", message = "weightKg must be between 0.5 and 20 kg")
    private BigDecimal weightKg;

    // WHO +3SD chiều dài lúc 24 tháng ≈ 97 cm.
    @DecimalMin(value = "20.0", message = "heightCm must be between 20 and 100 cm")
    @DecimalMax(value = "100.0", message = "heightCm must be between 20 and 100 cm")
    private BigDecimal heightCm;

    // WHO +3SD vòng đầu lúc 24 tháng ≈ 52 cm; chừa biên cho não úng thủy/đầu to bệnh lý.
    @DecimalMin(value = "20.0", message = "headCircumferenceCm must be between 20 and 60 cm")
    @DecimalMax(value = "60.0", message = "headCircumferenceCm must be between 20 and 60 cm")
    private BigDecimal headCircumferenceCm;

    @NotBlank
    @Size(max = 30)
    private String sourceType;

    private String note;
}
