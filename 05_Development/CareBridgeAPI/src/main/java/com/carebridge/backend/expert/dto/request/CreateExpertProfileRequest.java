package com.carebridge.backend.expert.dto.request;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;
import lombok.*;
import java.util.List;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class CreateExpertProfileRequest {

    /**
     * Ô văn bản không bắt buộc vẫn không được chỉ toàn khoảng trắng: "   " lọt qua @Size và
     * được lưu thành chức danh/nơi công tác trống trơn trên hồ sơ công khai.
     */
    static final String HAS_TEXT = "(?s).*\\S.*";

    @NotBlank(message = "Vui lòng chọn chuyên khoa")
    @Size(max = 80, message = "Mã chuyên khoa không hợp lệ")
    private String specialtyId;

    @Size(max = 20, message = "Chỉ được chọn tối đa 20 chuyên khoa")
    private List<@NotBlank(message = "Mã chuyên khoa không được để trống")
            @Size(max = 80, message = "Mã chuyên khoa không hợp lệ") String> specialtyIds;

    @NotBlank(message = "Vui lòng chọn nơi công tác")
    @Size(max = 150, message = "Mã nơi công tác không hợp lệ")
    private String hospitalId;

    @Size(max = 255, message = "Tên nơi công tác tối đa 255 ký tự")
    @Pattern(regexp = HAS_TEXT, message = "Tên nơi công tác không được chỉ chứa khoảng trắng")
    private String trackAsiaName;

    @Size(max = 500, message = "Địa chỉ nơi công tác tối đa 500 ký tự")
    @Pattern(regexp = HAS_TEXT, message = "Địa chỉ nơi công tác không được chỉ chứa khoảng trắng")
    private String trackAsiaAddress;

    @DecimalMin(value = "-90.0", message = "Vĩ độ nơi công tác phải trong khoảng -90 đến 90")
    @DecimalMax(value = "90.0", message = "Vĩ độ nơi công tác phải trong khoảng -90 đến 90")
    private Double trackAsiaLat;

    @DecimalMin(value = "-180.0", message = "Kinh độ nơi công tác phải trong khoảng -180 đến 180")
    @DecimalMax(value = "180.0", message = "Kinh độ nơi công tác phải trong khoảng -180 đến 180")
    private Double trackAsiaLng;

    @Size(max = 100, message = "Chuyên khoa tối đa 100 ký tự")
    @Pattern(regexp = HAS_TEXT, message = "Chuyên khoa không được chỉ chứa khoảng trắng")
    private String specialty;

    @Size(max = 150, message = "Chức danh tối đa 150 ký tự")
    @Pattern(regexp = HAS_TEXT, message = "Chức danh không được chỉ chứa khoảng trắng")
    private String professionalTitle;

    @Min(value = 0, message = "Số năm kinh nghiệm không được âm")
    @Max(value = 80, message = "Số năm kinh nghiệm tối đa 80 năm")
    private Integer experienceYears;

    @Size(max = 200, message = "Nơi công tác tối đa 200 ký tự")
    @Pattern(regexp = HAS_TEXT, message = "Nơi công tác không được chỉ chứa khoảng trắng")
    private String workplace;

    /** province_id from /api/v1/master-data/provinces; scopes the hospital lookup. */
    @Size(max = 16, message = "Mã tỉnh/thành không hợp lệ")
    private String workplaceProvinceId;

    @Size(max = 5000, message = "Phạm vi tư vấn tối đa 5000 ký tự")
    @Pattern(regexp = HAS_TEXT, message = "Phạm vi tư vấn không được chỉ chứa khoảng trắng")
    private String consultationScope;

    // Không có ratingAvg: điểm đánh giá do người dùng chấm, chuyên gia không được tự khai.
    // Trường này từng nằm ở đây và được ghi thẳng vào hồ sơ, nên ai cũng tự đặt được 5 sao
    // (hoặc 99) và nhảy lên đầu danh bạ, vốn xếp theo điểm này.

    @PositiveOrZero(message = "Phí tư vấn không được âm")
    @Max(value = 10_000_000, message = "Phí tư vấn tối đa 10.000.000 đồng mỗi buổi")
    private Long consultationFeeVnd;
}
