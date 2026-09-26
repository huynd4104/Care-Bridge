package com.carebridge.backend.common.validation;

import jakarta.validation.Constraint;
import jakarta.validation.Payload;
import jakarta.validation.ReportAsSingleViolation;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Pattern;
import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * Email that can actually receive mail: {@link Email} accepts "user@host" (no dot in the
 * domain), which is valid per RFC but undeliverable on the public internet, so OTP and
 * invitation mail sent there would never arrive. This additionally requires a dotted domain
 * ending in a TLD of at least two letters. Null is valid; combine with {@code @NotBlank}.
 */
@Documented
@Email
@Pattern(regexp = "^[^@\\s]+@[^@\\s.]+(\\.[^@\\s.]+)*\\.[A-Za-z]{2,}$")
@ReportAsSingleViolation
@Constraint(validatedBy = {})
@Target({ElementType.FIELD, ElementType.PARAMETER})
@Retention(RetentionPolicy.RUNTIME)
public @interface DeliverableEmail {

    String message() default "Invalid email address";

    Class<?>[] groups() default {};

    Class<? extends Payload>[] payload() default {};
}
