package com.carebridge.backend.expert.dto.request;

import static org.assertj.core.api.Assertions.assertThat;

import com.carebridge.backend.expert.entity.ExpertProfile;
import com.carebridge.backend.expert.mapper.ExpertProfileMapper;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import java.math.BigDecimal;
import java.util.Set;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class ExpertProfileRequestValidationTest {

    private static ValidatorFactory validatorFactory;
    private static Validator validator;

    @BeforeAll
    static void setUpValidator() {
        validatorFactory = Validation.buildDefaultValidatorFactory();
        validator = validatorFactory.getValidator();
    }

    @AfterAll
    static void closeValidator() {
        validatorFactory.close();
    }

    @Test
    void createAndUpdateAllowFeeAndExperienceBoundaryValues() {
        CreateExpertProfileRequest create = validCreate();
        create.setConsultationFeeVnd(0L);
        create.setExperienceYears(80);
        UpdateExpertProfileRequest update = UpdateExpertProfileRequest.builder()
                .consultationFeeVnd(0L)
                .experienceYears(0)
                .build();

        assertThat(validator.validate(create)).isEmpty();
        assertThat(validator.validate(update)).isEmpty();
    }

    @Test
    // hospitalId carries either a canonical care-facility UUID or a free-form facility identifier
    // coming from the map provider, so the column bound is 150 characters.
    void createAndUpdateAcceptCanonicalFacilityUuidAndRejectLongerIdentifiers() {
        String facilityId = java.util.UUID.randomUUID().toString();
        CreateExpertProfileRequest create = validCreate();
        create.setHospitalId(facilityId);
        UpdateExpertProfileRequest update = UpdateExpertProfileRequest.builder()
                .hospitalId(facilityId)
                .build();

        assertThat(validator.validate(create)).isEmpty();
        assertThat(validator.validate(update)).isEmpty();

        create.setHospitalId("x".repeat(150));
        update.setHospitalId("x".repeat(150));
        assertThat(validator.validate(create)).isEmpty();
        assertThat(validator.validate(update)).isEmpty();

        create.setHospitalId("x".repeat(151));
        update.setHospitalId("x".repeat(151));
        assertViolationOn(validator.validate(create), "hospitalId");
        assertViolationOn(validator.validate(update), "hospitalId");
    }

    @Test
    void createAndUpdateRejectNegativeConsultationFee() {
        CreateExpertProfileRequest create = validCreate();
        create.setConsultationFeeVnd(-1L);
        UpdateExpertProfileRequest update = UpdateExpertProfileRequest.builder()
                .consultationFeeVnd(-1L)
                .build();

        assertViolationOn(validator.validate(create), "consultationFeeVnd");
        assertViolationOn(validator.validate(update), "consultationFeeVnd");
    }

    @Test
    void createAndUpdateRejectExperienceOutsideZeroToEightyYears() {
        CreateExpertProfileRequest create = validCreate();
        create.setExperienceYears(81);
        UpdateExpertProfileRequest update = UpdateExpertProfileRequest.builder()
                .experienceYears(-1)
                .build();

        assertViolationOn(validator.validate(create), "experienceYears");
        assertViolationOn(validator.validate(update), "experienceYears");
    }

    @Test
    void mapperPreservesConsultationFeeInCanonicalProfileAndResponses() {
        CreateExpertProfileRequest request = validCreate();
        request.setConsultationFeeVnd(350_000L);
        ExpertProfileMapper mapper = new ExpertProfileMapper();

        ExpertProfile profile = mapper.toEntity(request, java.util.UUID.randomUUID());

        assertThat(profile.getConsultationFeeVnd()).isEqualTo(350_000L);
        assertThat(mapper.toResponse(profile, "Expert", null).getConsultationFeeVnd())
                .isEqualByComparingTo(BigDecimal.valueOf(350_000L));
        assertThat(mapper.toDetailResponse(profile, "Expert", null).getConsultationFeeVnd())
                .isEqualByComparingTo(BigDecimal.valueOf(350_000L));
    }

    @Test
    void createAndUpdateRejectConsultationFeeAboveTenMillionDong() {
        CreateExpertProfileRequest create = validCreate();
        create.setConsultationFeeVnd(10_000_000L);
        assertThat(validator.validate(create)).isEmpty();

        create.setConsultationFeeVnd(10_000_001L);
        UpdateExpertProfileRequest update = UpdateExpertProfileRequest.builder()
                .consultationFeeVnd(1_000_000_000_000L)
                .build();

        assertViolationOn(validator.validate(create), "consultationFeeVnd");
        assertViolationOn(validator.validate(update), "consultationFeeVnd");
    }

    @Test
    void createAndUpdateRejectTextFieldsThatAreOnlyWhitespace() {
        UpdateExpertProfileRequest update = UpdateExpertProfileRequest.builder()
                .professionalTitle("   ")
                .workplace("\t")
                .specialty(" ")
                .consultationScope("\n  \n")
                .build();

        Set<ConstraintViolation<UpdateExpertProfileRequest>> violations = validator.validate(update);

        assertViolationOn(violations, "professionalTitle");
        assertViolationOn(violations, "workplace");
        assertViolationOn(violations, "specialty");
        assertViolationOn(violations, "consultationScope");
    }

    @Test
    void multilineConsultationScopeWithRealTextIsAccepted() {
        UpdateExpertProfileRequest update = UpdateExpertProfileRequest.builder()
                .consultationScope("Thai kỳ nguy cơ cao\nTư vấn tiền sản")
                .professionalTitle("BS.CKII")
                .build();

        assertThat(validator.validate(update)).isEmpty();
    }

    @Test
    void createAndUpdateRejectWorkplaceCoordinatesOutsideTheGlobe() {
        CreateExpertProfileRequest create = validCreate();
        create.setTrackAsiaLat(999.0);
        UpdateExpertProfileRequest update = UpdateExpertProfileRequest.builder()
                .trackAsiaLng(-999.0)
                .build();

        assertViolationOn(validator.validate(create), "trackAsiaLat");
        assertViolationOn(validator.validate(update), "trackAsiaLng");
    }

    @Test
    void validationMessagesAreVietnameseSoTheUserSeesThem() {
        UpdateExpertProfileRequest update = UpdateExpertProfileRequest.builder()
                .consultationFeeVnd(20_000_000L)
                .build();

        assertThat(validator.validate(update))
                .extracting(ConstraintViolation::getMessage)
                .containsExactly("Phí tư vấn tối đa 10.000.000 đồng mỗi buổi");
    }

    @Test
    void ratingIsNotAcceptedFromTheExpertAndIsNeverCopiedFromTheRequest() {
        // Điểm đánh giá do người dùng chấm. Request không còn trường ratingAvg, nên JSON có gửi
        // "ratingAvg": 99 thì Jackson cũng bỏ qua và hồ sơ giữ nguyên điểm cũ.
        assertThat(java.util.Arrays.stream(UpdateExpertProfileRequest.class.getDeclaredFields())
                .map(java.lang.reflect.Field::getName))
                .doesNotContain("ratingAvg");
        assertThat(java.util.Arrays.stream(CreateExpertProfileRequest.class.getDeclaredFields())
                .map(java.lang.reflect.Field::getName))
                .doesNotContain("ratingAvg");

        ExpertProfileMapper mapper = new ExpertProfileMapper();
        ExpertProfile profile = mapper.toEntity(validCreate(), java.util.UUID.randomUUID());
        profile.setRatingAvg(new BigDecimal("4.50"));
        mapper.updateEntity(profile, UpdateExpertProfileRequest.builder().professionalTitle("BS").build());

        assertThat(profile.getRatingAvg()).isEqualByComparingTo("4.50");
    }

    @Test
    void mapperStoresTextWithoutSurroundingWhitespace() {
        ExpertProfileMapper mapper = new ExpertProfileMapper();
        ExpertProfile profile = mapper.toEntity(validCreate(), java.util.UUID.randomUUID());

        mapper.updateEntity(profile, UpdateExpertProfileRequest.builder()
                .professionalTitle("  BS.CKII  ")
                .workplace(" Bệnh viện Từ Dũ ")
                .build());

        assertThat(profile.getProfessionalTitle()).isEqualTo("BS.CKII");
        assertThat(profile.getWorkplace()).isEqualTo("Bệnh viện Từ Dũ");
    }

    private static CreateExpertProfileRequest validCreate() {
        return CreateExpertProfileRequest.builder()
                .specialtyId("OBGYN")
                .hospitalId("HCM-001")
                .build();
    }

    private static void assertViolationOn(
            Set<? extends ConstraintViolation<?>> violations, String property) {
        assertThat(violations)
                .anyMatch(violation -> property.equals(violation.getPropertyPath().toString()));
    }
}
