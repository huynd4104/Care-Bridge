package com.carebridge.backend.security.dto.request;

import com.carebridge.backend.common.validation.VietnamesePhoneNumber;
import com.carebridge.backend.security.rbac.Role;
import com.carebridge.backend.common.validation.DeliverableEmail;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record PhoneRegisterRequest(
        @NotBlank @Size(max = 8192) String idToken,
        @NotBlank @Size(min = 2, max = 120)
        @Pattern(regexp = "^\\s*[\\p{L}\\p{M}]+(\\s+[\\p{L}\\p{M}]+)*\\s*$", message = "Name must contain letters and spaces only") String name,
        @NotBlank @DeliverableEmail @Size(max = 255) String email,
        @NotBlank @VietnamesePhoneNumber String phone,
        @NotBlank @Size(min = 8, max = 100) String password,
        Role role,
        @Size(max = 500) String deviceInfo) {
}
