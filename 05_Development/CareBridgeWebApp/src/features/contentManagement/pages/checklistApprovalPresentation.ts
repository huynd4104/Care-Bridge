import { getApiErrorMessage } from '../../../shared/api/apiErrorMessage';
import type {
  ChecklistRangeUnit,
  ChecklistRecipientRole,
  ChecklistSubstage,
  ContentStage,
} from '../models/content';

export const CHECKLIST_APPROVAL_REASON_MESSAGES: Readonly<Record<string, string>> = {
  CHECKLIST_ACTIVE_LEGACY_CONFLICT:
    'Không thể xuất bản bộ chuỗi khi checklist legacy đang hoạt động. Hãy lưu trữ hoặc tắt checklist legacy trước.',
  CHECKLIST_ACTIVE_SEQUENCE_CONFLICT:
    'Không thể xuất bản checklist legacy khi chuỗi checklist đang hoạt động. Hãy lưu trữ hoặc tắt chuỗi trước.',
  CHECKLIST_REQUIRED_ITEM_MISSING:
    'Checklist trong chuỗi phải có ít nhất một mục bắt buộc.',
  CHECKLIST_DUPLICATE_SEQUENCE_POSITION:
    'Vị trí bộ checklist trong chuỗi Chuẩn bị mang thai đã có checklist khác đang hoạt động. Content Admin cần đổi "Vị trí bộ checklist" sang số chưa dùng (ví dụ bộ tiếp theo ở cuối chuỗi), hoặc tạo phiên bản mới từ chính checklist đang giữ vị trí đó nếu muốn thay thế.',
  CHECKLIST_SEQUENCE_POSITION_GAP:
    'Các bộ checklist phải liên tục từ bộ 1. Hãy xuất bản các bộ còn thiếu trước.',
  CHECKLIST_SEQUENCE_POSITION_IMMUTABLE:
    'Không thể đổi vị trí sau khi dòng checklist đã bắt đầu.',
};

export function checklistSequenceLabel(
  displayOrder: number | null | undefined,
  stage?: ContentStage | null,
): string {
  if (stage !== undefined && stage !== 'PRE_PREGNANCY') return 'Không áp dụng chuỗi Chuẩn bị mang thai';
  return displayOrder == null || displayOrder <= 0
    ? 'Legacy · ngoài chuỗi'
    : `Bộ chuỗi ${displayOrder}`;
}

export function checklistRecipientLabel(roles: ChecklistRecipientRole[] | null | undefined): string {
  if (!roles || roles.length === 0) return 'Chưa xác định người nhận';
  const labels: Record<ChecklistRecipientRole, string> = { MOTHER: 'Mẹ', FAMILY: 'Gia đình' };
  return roles.map((role) => labels[role]).join(' · ');
}

/** Chuẩn hóa nhãn hiển thị cửa sổ vòng đời (lifecycle window) của checklist sang tiếng Việt. */
export function checklistWindowLabel(
  checklist: {
    stage?: ContentStage | null;
    substage?: ChecklistSubstage | null;
    eligibilityStartInclusive?: number | null;
    eligibilityEndInclusive?: number | null;
  },
): string {
  if (checklist.stage === 'PRE_PREGNANCY') {
    return 'Toàn bộ giai đoạn';
  }

  const substage = checklist.substage;
  if (substage) {
    const code = substage.code ?? '';

    if (
      code.startsWith('PRE_PREGNANCY') ||
      code === 'LEGACY_PRE_PREGNANCY' ||
      code.startsWith('LEGACY_') ||
      substage.anchor === 'NONE'
    ) {
      return 'Toàn bộ giai đoạn';
    }

    let unit = substage.unit;
    let startInclusive = substage.startInclusive;
    let endInclusive = substage.endInclusive;

    if (!unit || startInclusive == null || endInclusive == null) {
      const match = code.match(/(?:^|_)(WEEK|DAY|MONTH)_(\d+)_(\d+)$/);
      if (match) {
        unit = match[1] as ChecklistRangeUnit;
        startInclusive = Number(match[2]);
        endInclusive = Number(match[3]);
      }
    }

    if (unit && startInclusive != null && endInclusive != null) {
      const isOpenEnded = endInclusive >= 2_000_000_000;
      if (unit === 'WEEK') {
        const start = startInclusive + 1;
        if (isOpenEnded) return `Tuần ${start}+`;
        const end = endInclusive + 1;
        return start === end ? `Tuần ${start}` : `Tuần ${start}–${end}`;
      }
      if (unit === 'DAY') {
        const start = startInclusive;
        if (isOpenEnded) return `Ngày ${start}+`;
        const end = endInclusive;
        return start === end ? `Ngày ${start}` : `Ngày ${start}–${end}`;
      }
      if (unit === 'MONTH') {
        const start = startInclusive;
        if (isOpenEnded) return `Tháng ${start}+`;
        const end = endInclusive;
        return start === end ? `Tháng ${start}` : `Tháng ${start}–${end}`;
      }
    }

    if (code) return code;
  }

  const start = checklist.eligibilityStartInclusive;
  const end = checklist.eligibilityEndInclusive;
  if (start != null && end != null) {
    if (end >= 2_000_000_000) return `Tuần ${start + 1}+`;
    if (start === end) return `Tuần ${start + 1}`;
    return `Tuần ${start + 1}–${end + 1}`;
  }

  return 'Không có cửa sổ';
}

export function checklistCadenceLabel(scheduleType?: string | null, materializationPolicy?: string | null): string {
  if (materializationPolicy === 'EACH_WEEK') return 'Theo tuần';
  if (materializationPolicy === 'EACH_DAY') return 'Theo ngày';
  if (materializationPolicy === 'ONCE_PER_WINDOW') return 'Theo bộ';
  if (scheduleType === 'SET') return 'Theo bộ';
  if (scheduleType === 'WEEKLY') return 'Theo tuần';
  if (scheduleType === 'DAILY') return 'Theo ngày';
  return 'Chưa cấu hình nhịp';
}

export function checklistCoexistenceGuidance(
  displayOrder: number | null | undefined,
  stage?: ContentStage | null,
): string {
  if (stage !== undefined && stage !== 'PRE_PREGNANCY') {
    return 'Chuỗi Chuẩn bị mang thai không áp dụng cho checklist ở giai đoạn này.';
  }
  return displayOrder == null || displayOrder <= 0
    ? 'Đây là checklist legacy (ngoài chuỗi). Không thể duyệt cùng lúc với một chuỗi Chuẩn bị mang thai đang hoạt động.'
    : 'Đây là bộ trong chuỗi Chuẩn bị mang thai. Checklist legacy bộ 0 phải được lưu trữ hoặc tắt trước khi xuất bản.';
}

function responseReasonCode(error: unknown): string | null {
  if (!error || typeof error !== 'object') return null;
  const response = (error as { response?: { data?: unknown } }).response;
  const data = response?.data;
  if (!data || typeof data !== 'object') return null;
  const metadata = (data as { metadata?: unknown }).metadata;
  if (!metadata || typeof metadata !== 'object') return null;
  const reasonCode = (metadata as { reasonCode?: unknown; reason?: unknown }).reasonCode
    ?? (metadata as { reason?: unknown }).reason;
  return typeof reasonCode === 'string' ? reasonCode : null;
}

export function checklistApprovalErrorMessage(
  error: unknown,
  decision: 'APPROVE' | 'REJECT' = 'APPROVE',
): string {
  const reasonCode = responseReasonCode(error);
  if (reasonCode && CHECKLIST_APPROVAL_REASON_MESSAGES[reasonCode]) {
    return CHECKLIST_APPROVAL_REASON_MESSAGES[reasonCode];
  }
  return getApiErrorMessage(error, decision === 'APPROVE'
    ? 'Không thể xuất bản mục này. Vui lòng thử lại.'
    : 'Không thể trả mục này về nháp. Vui lòng thử lại.');
}
