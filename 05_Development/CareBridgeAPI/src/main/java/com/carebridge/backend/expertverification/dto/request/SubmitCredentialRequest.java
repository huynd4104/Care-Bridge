package com.carebridge.backend.expertverification.dto.request;

import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;
import org.springframework.web.multipart.MultipartFile;

@Data
public class SubmitCredentialRequest {

 /** Chặn giá trị chỉ toàn khoảng trắng ở các ô không bắt buộc. */
 static final String HAS_TEXT = "(?s).*\\S.*";

 @NotBlank(message = "Vui lòng chọn loại chứng chỉ")
 @Pattern(regexp = "MEDICAL_LICENSE|DEGREE|CERTIFICATE|IDENTITY_DOCUMENT|PROFESSIONAL_LICENSE",
          message = "Loại chứng chỉ không hợp lệ")
 @Size(max = 50, message = "Loại chứng chỉ không hợp lệ")
 private String credentialType;

 @Size(max = 100, message = "Số chứng chỉ tối đa 100 ký tự")
 @Pattern(regexp = HAS_TEXT, message = "Số chứng chỉ không được chỉ chứa khoảng trắng")
 private String credentialNumber;

 @Size(max = 200, message = "Đơn vị cấp tối đa 200 ký tự")
 @Pattern(regexp = HAS_TEXT, message = "Đơn vị cấp không được chỉ chứa khoảng trắng")
 private String issuer;

 // Định dạng yyyy-MM-dd; ngày cấp và ngày hết hạn được kiểm tra ở ExpertCredentialServiceImpl.
 private String issuedDate;

 private String expiryDate;

 @Size(max = 2000, message = "Ghi chú tối đa 2000 ký tự")
 private String reviewNote;

 private MultipartFile file;
}
