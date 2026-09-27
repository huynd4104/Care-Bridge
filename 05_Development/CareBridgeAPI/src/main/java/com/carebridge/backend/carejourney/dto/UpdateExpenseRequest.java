package com.carebridge.backend.carejourney.dto;

import com.carebridge.backend.carejourney.entity.ExpenseCategory;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.Digits;
import jakarta.validation.constraints.Positive;

import java.math.BigDecimal;
import java.time.LocalDate;

public record UpdateExpenseRequest(

        ExpenseCategory category,

        @Positive(message = "EXPENSE-002: amount must be positive")
        @DecimalMax(value = "1000000000", message = "EXPENSE-002: amount must not exceed 1,000,000,000")
        @Digits(integer = 10, fraction = 2, message = "EXPENSE-002: amount must have at most 2 decimal places")
        BigDecimal amount,

        LocalDate expenseDate,

        String note
) {}
