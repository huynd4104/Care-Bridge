package com.carebridge.backend.security.dto.request;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import java.util.Set;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class UpdateProfileRequestValidationTest {

    private static Validator validator;

    @BeforeAll
    static void setUpValidator() {
        validator = Validation.buildDefaultValidatorFactory().getValidator();
    }

    @Test
    void rejectsPhoneThatIsTooLong() {
        UpdateProfileRequest request = new UpdateProfileRequest();
        request.setPhone("098123123111111");

        assertTrue(hasPhoneViolation(validator.validate(request)));
    }

    @Test
    void rejectsPhoneWithoutVietnamesePrefix() {
        UpdateProfileRequest request = new UpdateProfileRequest();
        request.setPhone("901236472");

        assertTrue(hasPhoneViolation(validator.validate(request)));
    }

    @Test
    void acceptsValidLocalAndE164Phones() {
        UpdateProfileRequest local = new UpdateProfileRequest();
        local.setPhone("0981234567");
        UpdateProfileRequest e164 = new UpdateProfileRequest();
        e164.setPhone("+84981234567");

        assertFalse(hasPhoneViolation(validator.validate(local)));
        assertFalse(hasPhoneViolation(validator.validate(e164)));
    }

    private static boolean hasPhoneViolation(Set<ConstraintViolation<UpdateProfileRequest>> violations) {
        return violations.stream().anyMatch(v -> "phone".equals(v.getPropertyPath().toString()));
    }
}
