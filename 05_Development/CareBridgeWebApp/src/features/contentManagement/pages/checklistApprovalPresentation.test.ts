import { describe, expect, it } from 'vitest';
import {
  checklistApprovalErrorMessage,
  checklistCadenceLabel,
  checklistCoexistenceGuidance,
  checklistRecipientLabel,
  checklistSequenceLabel,
  checklistWindowLabel,
} from './checklistApprovalPresentation';

describe('checklist approval presentation', () => {
  it('labels legacy and positive sequence positions distinctly', () => {
    expect(checklistSequenceLabel(0)).toContain('Legacy');
    expect(checklistSequenceLabel(null)).toContain('Legacy');
    expect(checklistSequenceLabel(3)).toContain('3');
    expect(checklistSequenceLabel(0, 'PREGNANCY')).toContain('Không áp dụng');
    expect(checklistSequenceLabel(0, null)).toContain('Không áp dụng');
  });

  it('describes recipients and cohort coexistence', () => {
    expect(checklistRecipientLabel(['MOTHER', 'FAMILY'])).toContain('·');
    expect(checklistCoexistenceGuidance(0)).toContain('legacy');
    expect(checklistCoexistenceGuidance(2)).toContain('Chuẩn bị mang thai');
    expect(checklistCoexistenceGuidance(0, 'POSTPARTUM')).toContain('không áp dụng');
  });

  it('maps allowlisted backend reasons without exposing arbitrary server text', () => {
    const known = checklistApprovalErrorMessage({
      response: { data: { metadata: { reasonCode: 'CHECKLIST_ACTIVE_LEGACY_CONFLICT' } } },
    });
    expect(known).toContain('legacy');

    const unknown = checklistApprovalErrorMessage({
      response: { data: { metadata: { reasonCode: 'UNKNOWN', message: 'internal SQL details' } } },
    });
    expect(unknown).not.toContain('internal SQL details');
    expect(unknown).toContain('Vui');
  });

  it('explains a duplicate preconception sequence position with how to fix it', () => {
    const message = checklistApprovalErrorMessage({
      response: { status: 400, data: { metadata: { reasonCode: 'CHECKLIST_DUPLICATE_SEQUENCE_POSITION' } } },
    });
    expect(message).toContain('Vị trí bộ checklist');
    expect(message).toContain('số chưa dùng');
    expect(message).not.toContain('status code 400');
  });

  it('renders inline pregnancy windows and cadence for V2 roots', () => {
    expect(checklistWindowLabel({ substage: null, eligibilityStartInclusive: 20, eligibilityEndInclusive: 24 })).toBe('Tuần 21–25');
    expect(checklistWindowLabel({ substage: null, eligibilityStartInclusive: 39, eligibilityEndInclusive: 2147483647 })).toBe('Tuần 40+');
    expect(checklistCadenceLabel('WEEKLY', 'EACH_WEEK')).toBe('Theo tuần');
    expect(checklistCadenceLabel('SET', 'ONCE_PER_WINDOW')).toBe('Theo bộ');
  });

  it('normalizes pre-pregnancy, week, day, and month substages to Vietnamese', () => {
    // Pre-pregnancy raw codes and stage
    expect(checklistWindowLabel({
      substage: {
        code: 'PRE_PREGNANCY_NONE_DAY_0_0',
        anchor: 'NONE',
        startInclusive: 0,
        endInclusive: 0,
        unit: 'DAY',
      },
    })).toBe('Toàn bộ giai đoạn');
    expect(checklistWindowLabel({ stage: 'PRE_PREGNANCY', substage: null })).toBe('Toàn bộ giai đoạn');
    expect(checklistWindowLabel({ substage: { code: 'PRE_PREGNANCY_ALL', anchor: 'NONE', startInclusive: 0, endInclusive: 0, unit: 'DAY' } })).toBe('Toàn bộ giai đoạn');
    expect(checklistWindowLabel({ substage: { code: 'LEGACY_PRE_PREGNANCY', anchor: 'NONE', startInclusive: 0, endInclusive: 2147483647, unit: 'DAY' } })).toBe('Toàn bộ giai đoạn');

    // Week window from substage
    expect(checklistWindowLabel({
      substage: {
        code: 'PREGNANCY_LMP_WEEK_0_12',
        anchor: 'LMP',
        startInclusive: 0,
        endInclusive: 12,
        unit: 'WEEK',
      },
    })).toBe('Tuần 1–13');

    // Month window from substage
    expect(checklistWindowLabel({
      substage: {
        code: 'BABY_CARE_MONTH_0_3',
        anchor: 'BIRTH_DATE',
        startInclusive: 0,
        endInclusive: 3,
        unit: 'MONTH',
      },
    })).toBe('Tháng 0–3');

    // Day window from substage
    expect(checklistWindowLabel({
      substage: {
        code: 'POSTPARTUM_DAY_0_7',
        anchor: 'DELIVERY_DATE',
        startInclusive: 0,
        endInclusive: 7,
        unit: 'DAY',
      },
    })).toBe('Ngày 0–7');

    // Fallback parsing from code string when attributes are absent
    expect(checklistWindowLabel({ substage: { code: 'PREGNANCY_LMP_WEEK_0_19' } as any })).toBe('Tuần 1–20');
    expect(checklistWindowLabel({ substage: null, eligibilityStartInclusive: null, eligibilityEndInclusive: null })).toBe('Không có cửa sổ');
  });
});
