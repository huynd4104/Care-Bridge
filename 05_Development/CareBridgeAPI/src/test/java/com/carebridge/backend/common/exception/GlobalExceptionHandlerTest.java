package com.carebridge.backend.common.exception;

import static org.assertj.core.api.Assertions.assertThat;

import com.carebridge.backend.common.response.ErrorResponse;
import com.carebridge.backend.content.exception.ContentException;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.servlet.resource.NoResourceFoundException;
import org.springframework.web.HttpRequestMethodNotSupportedException;

class GlobalExceptionHandlerTest {

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler();

    @Test
    void handleValidation_preservesDomainErrorCode() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRequestURI("/api/v1/auth/change-password");

        ResponseEntity<ErrorResponse> response = handler.handleValidation(
                new ValidationException("AUTH-071", "Current password is incorrect"),
                request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().getError()).isEqualTo("AUTH-071");
        assertThat(response.getBody().getMessage()).isEqualTo("Current password is incorrect");
    }

    @Test
    void handleMethodArgumentNotValid_surfacesVietnameseFieldMessageSoTheUserSeesIt() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRequestURI("/api/v1/expert/profiles/me");
        org.springframework.validation.BeanPropertyBindingResult result =
                new org.springframework.validation.BeanPropertyBindingResult(new Object(), "request");
        result.addError(new org.springframework.validation.FieldError(
                "request", "experienceYears", 90, false, null, null, "must be less than or equal to 80"));
        result.addError(new org.springframework.validation.FieldError(
                "request", "consultationFeeVnd", 20_000_000L, false, null, null,
                "Phí tư vấn tối đa 10.000.000 đồng mỗi buổi"));
        org.springframework.core.MethodParameter parameter = new org.springframework.core.MethodParameter(
                Object.class.getMethod("equals", Object.class), 0);

        ResponseEntity<ErrorResponse> response = handler.handleMethodArgumentNotValid(
                new org.springframework.web.bind.MethodArgumentNotValidException(parameter, result), request);

        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().getError()).isEqualTo("VALIDATION_ERROR");
        // Câu tiếng Anh đứng trước bị bỏ qua: web và app chỉ hiện message khi nó là tiếng Việt.
        assertThat(response.getBody().getMessage()).isEqualTo("Phí tư vấn tối đa 10.000.000 đồng mỗi buổi");
        assertThat(response.getBody().getDetails()).hasSize(2);
    }

    @Test
    void handleMethodArgumentNotValid_keepsGenericMessageWhenNoFieldMessageIsVietnamese() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest();
        org.springframework.validation.BeanPropertyBindingResult result =
                new org.springframework.validation.BeanPropertyBindingResult(new Object(), "request");
        result.addError(new org.springframework.validation.FieldError(
                "request", "title", "", false, null, null, "must not be blank"));
        org.springframework.core.MethodParameter parameter = new org.springframework.core.MethodParameter(
                Object.class.getMethod("equals", Object.class), 0);

        ResponseEntity<ErrorResponse> response = handler.handleMethodArgumentNotValid(
                new org.springframework.web.bind.MethodArgumentNotValidException(parameter, result), request);

        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().getMessage()).isEqualTo("Invalid request");
    }

    @Test
    void handleContent_preservesChecklistReasonMetadata() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRequestURI("/api/v1/admin/checklist-templates/1/decision");

        ResponseEntity<ErrorResponse> response = handler.handleContent(
                new ContentException("CNT-001", "Validation failed", HttpStatus.BAD_REQUEST,
                        Map.of("reasonCode", "CHECKLIST_ACTIVE_LEGACY_CONFLICT")),
                request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_REQUEST);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().getMetadata())
                .containsEntry("reasonCode", "CHECKLIST_ACTIVE_LEGACY_CONFLICT");
    }

    @Test
    void handleNoResourceFound_returnsNeutral404WithoutFrameworkResourceMetadata() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRequestURI("/api/v1/unmatched-story-69-route");
        NoResourceFoundException exception = new NoResourceFoundException(
                HttpMethod.GET,
                "api/v1/unmatched-story-69-route",
                "PRIVATE-FRAMEWORK-RESOURCE-SENTINEL");

        ResponseEntity<ErrorResponse> response = handler.handleNoResourceFound(exception, request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().getStatus()).isEqualTo(404);
        assertThat(response.getBody().getError()).isEqualTo("RESOURCE_NOT_FOUND");
        assertThat(response.getBody().getMessage()).isEqualTo("Resource not found");
        assertThat(response.getBody().getMessage())
                .doesNotContain(exception.getResourcePath(), "PRIVATE-FRAMEWORK-RESOURCE-SENTINEL");
        assertThat(response.getBody().getDetails()).isNull();
    }

    @Test
    void handleMethodNotSupported_returnsNeutral405WithoutAllowedMethodMetadata() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRequestURI("/api/v1/user-checklist-items/unmapped-route");
        HttpRequestMethodNotSupportedException exception =
                new HttpRequestMethodNotSupportedException(
                        "GET", java.util.List.of("PUT", "PATCH", "DELETE"));

        ResponseEntity<ErrorResponse> response =
                handler.handleMethodNotSupported(exception, request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.METHOD_NOT_ALLOWED);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().getStatus()).isEqualTo(405);
        assertThat(response.getBody().getError()).isEqualTo("METHOD_NOT_ALLOWED");
        assertThat(response.getBody().getMessage()).isEqualTo("Request method not supported");
        assertThat(response.getBody().getMessage())
                .doesNotContain("GET", "PUT", "PATCH", "DELETE");
        assertThat(response.getBody().getDetails()).isNull();
    }

    @Test
    void handleMap_preservesHttpStatusAndErrorCode() {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.setRequestURI("/api/v1/map/nearby-facilities");

        com.carebridge.backend.map.exception.MapException exception =
                new com.carebridge.backend.map.exception.MapException(
                        HttpStatus.BAD_GATEWAY, "MAP-008", "TrackAsia is temporarily unavailable");

        ResponseEntity<ErrorResponse> response = handler.handleMap(exception, request);

        assertThat(response.getStatusCode()).isEqualTo(HttpStatus.BAD_GATEWAY);
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().getStatus()).isEqualTo(502);
        assertThat(response.getBody().getError()).isEqualTo("MAP-008");
        assertThat(response.getBody().getMessage()).isEqualTo("TrackAsia is temporarily unavailable");
    }
}
