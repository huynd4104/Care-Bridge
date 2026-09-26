package com.carebridge.backend.security.dto.request;

import com.carebridge.backend.common.validation.VietnamesePhoneNumber;
import com.carebridge.backend.security.rbac.Role;
import com.carebridge.backend.common.validation.DeliverableEmail;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
public class RegisterRequest {

    @NotBlank
    @Size(min = 2, max = 120)
    // Họ và tên chỉ gồm chữ cái (kể cả tiếng Việt có dấu) và khoảng trắng.
    @Pattern(regexp = "^\\s*[\\p{L}\\p{M}]+(\\s+[\\p{L}\\p{M}]+)*\\s*$", message = "Name must contain letters and spaces only")
    private String name;

    @VietnamesePhoneNumber
    private String phone;

    @DeliverableEmail
    private String email;

    @NotBlank
    @Size(min = 8, max = 100)
    private String password;

    private Role role;

    /** The client must choose a verification channel before this endpoint is called. */
    @NotNull
    private VerificationMethod verificationMethod;
}
