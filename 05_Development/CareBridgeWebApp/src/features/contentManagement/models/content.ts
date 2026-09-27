export type ContentType = 'ARTICLE' | 'FAQ' | 'CHECKLIST';
export type ContentStage = 'PRE_PREGNANCY' | 'PREGNANCY' | 'POSTPARTUM' | 'BABY_CARE';
export type ContentStatus = 'DRAFT' | 'PENDING_REVIEW' | 'APPROVED' | 'ARCHIVED';
export type ChecklistTemplateStatus = 'DRAFT' | 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED' | 'ARCHIVED';
export type ChecklistTemplateType = 'MANDATORY' | 'OPTIONAL';
export type ContentDecision = 'APPROVE' | 'REJECT';
export type ChecklistRecipientRole = 'MOTHER' | 'FAMILY';
export type ChecklistTargetSubject = 'MOTHER' | 'BABY';
export type ChecklistSupportFunction =
  | 'HEALTH_RECORDS'
  | 'MATERNAL_HEALTH_METRICS'
  | 'MATERNAL_EXERCISES'
  | 'APPOINTMENTS'
  | 'REMINDERS'
  | 'JOURNEY'
  | 'BABY_CARE'
  | 'EXPERT_CONSULTATION'
  | 'CONTENT_LIBRARY'
  | 'AI_TRIAGE';
export type ChecklistAnchorType = 'NONE' | 'LMP' | 'EDD' | 'DELIVERY_DATE' | 'BIRTH_DATE';
export type ChecklistRangeUnit = 'DAY' | 'WEEK' | 'MONTH';
export type ChecklistScheduleType = 'LEGACY' | 'SET' | 'WEEKLY' | 'DAILY';
export type ChecklistMaterializationPolicy =
  | 'LEGACY_WINDOW'
  | 'SEQUENCE_STEP'
  | 'ONCE_PER_WINDOW'
  | 'EACH_WEEK'
  | 'EACH_DAY';
export type ChecklistCareContextType = 'JOURNEY' | 'BABY';
export type ChecklistScheduleEndMode = 'NONE' | 'FIXED_OFFSET' | 'STAGE_EXIT';
export type ChecklistWeekBoundaryRule = 'NONE' | 'ANCHOR_RELATIVE_7D';

export const CHECKLIST_SUPPORT_FUNCTION_OPTIONS: ReadonlyArray<{
  value: ChecklistSupportFunction;
  label: string;
}> = [
  { value: 'MATERNAL_HEALTH_METRICS', label: 'Đo chỉ số sức khỏe của mẹ' },
  { value: 'MATERNAL_EXERCISES', label: 'Bài tập cho mẹ' },
  { value: 'HEALTH_RECORDS', label: 'Hồ sơ sức khỏe' },
  { value: 'APPOINTMENTS', label: 'Lịch hẹn' },
  { value: 'REMINDERS', label: 'Nhắc nhở' },
  { value: 'JOURNEY', label: 'Hành trình' },
  { value: 'BABY_CARE', label: 'Chăm sóc em bé' },
  { value: 'EXPERT_CONSULTATION', label: 'Tư vấn chuyên gia' },
  { value: 'CONTENT_LIBRARY', label: 'Thư viện nội dung' },
  { value: 'AI_TRIAGE', label: 'Sàng lọc AI' },
];

/**
 * Tag khảo sát cá nhân hóa của mẹ (trùng mã với questionnaire trên mobile) dùng để khai báo
 * chống chỉ định cho từng mục checklist. Mẹ có tag trùng sẽ không thấy mục đó.
 * Phải khớp với ChecklistContraindicationPolicy.ALLOWED_TAGS ở backend.
 */
export const CHECKLIST_CONTRAINDICATION_GROUPS: ReadonlyArray<{
  label: string;
  options: ReadonlyArray<{ value: string; label: string }>;
}> = [
  {
    label: 'Bệnh nền',
    options: [
      { value: 'DIABETES', label: 'Đái tháo đường' },
      { value: 'HYPERTENSION', label: 'Tăng huyết áp' },
      { value: 'CARDIOVASCULAR_DISEASE', label: 'Bệnh tim' },
      { value: 'KIDNEY_DISEASE', label: 'Bệnh thận' },
      { value: 'THYROID_DISORDER', label: 'Bệnh tuyến giáp' },
      { value: 'ASTHMA', label: 'Hen' },
      { value: 'EPILEPSY', label: 'Động kinh' },
      { value: 'LUPUS', label: 'Lupus' },
      { value: 'AUTOIMMUNE_DISEASE', label: 'Bệnh tự miễn' },
      { value: 'ANEMIA', label: 'Thiếu máu' },
      { value: 'PCOS', label: 'PCOS' },
      { value: 'ENDOMETRIOSIS', label: 'Lạc nội mạc tử cung' },
      { value: 'INFERTILITY', label: 'Hiếm muộn' },
      { value: 'MENTAL_HEALTH_CONDITION', label: 'Tình trạng sức khỏe tâm thần' },
    ],
  },
  {
    label: 'Tiền sử sinh sản',
    options: [
      { value: 'PRIOR_PREGNANCY_LOSS', label: 'Từng sảy thai' },
      { value: 'PRIOR_RECURRENT_PREGNANCY_LOSS', label: 'Từng sảy thai nhiều lần' },
      { value: 'PRIOR_STILLBIRTH', label: 'Từng thai lưu' },
      { value: 'PRIOR_PRETERM_BIRTH', label: 'Từng sinh non' },
      { value: 'PRIOR_MULTIPLE_PREGNANCY', label: 'Từng mang đa thai' },
      { value: 'PRIOR_ECTOPIC_PREGNANCY', label: 'Từng mang thai ngoài tử cung' },
      { value: 'PRIOR_PREECLAMPSIA', label: 'Từng bị tiền sản giật' },
      { value: 'PRIOR_GESTATIONAL_DIABETES', label: 'Từng mắc đái tháo đường thai kỳ' },
    ],
  },
  {
    label: 'Lối sống',
    options: [
      { value: 'SMOKING', label: 'Hút thuốc' },
      { value: 'ALCOHOL_USE', label: 'Uống rượu bia' },
      { value: 'SUBSTANCE_USE', label: 'Sử dụng ma túy hoặc chất kích thích' },
      { value: 'SLEEP_CONCERN', label: 'Thiếu ngủ' },
      { value: 'STRESS', label: 'Stress' },
      { value: 'LOW_ACTIVITY', label: 'Ít vận động' },
      { value: 'UNHEALTHY_DIET', label: 'Chế độ ăn không lành mạnh' },
    ],
  },
  {
    label: 'Dinh dưỡng',
    options: [
      { value: 'FOLIC_ACID_NOT_STARTED', label: 'Chưa sử dụng acid folic' },
      { value: 'IODINE_UNASSESSED_OR_INSUFFICIENT', label: 'Chưa đánh giá / có thể thiếu iod' },
      { value: 'VITAMIN_D_INSUFFICIENT_OR_SUPPLEMENT', label: 'Có thể thiếu vitamin D' },
      { value: 'IRON_INSUFFICIENT_OR_SUPPLEMENT', label: 'Có thể thiếu sắt' },
      { value: 'CALCIUM_INSUFFICIENT_OR_SUPPLEMENT', label: 'Có thể thiếu canxi' },
    ],
  },
  {
    label: 'Tiêm chủng',
    options: [
      { value: 'NOT_ASSESSED', label: 'Chưa được đánh giá tiêm chủng' },
      { value: 'RUBELLA_NONIMMUNE', label: 'Chưa có miễn dịch Rubella/MMR' },
      { value: 'HEPATITIS_B_INCOMPLETE', label: 'Chưa được bảo vệ đủ với viêm gan B' },
      { value: 'INFLUENZA_DUE', label: 'Cần tiêm cúm mùa' },
      { value: 'COVID_19_UPDATE', label: 'Cần cập nhật vắc xin COVID-19' },
    ],
  },
  {
    label: 'Thuốc đang dùng',
    options: [
      { value: 'HIGH_RISK_OR_CONTRAINDICATED', label: 'Thuốc chống chỉ định / nguy cơ cao khi mang thai' },
      { value: 'NEEDS_ADJUSTMENT', label: 'Thuốc cần điều chỉnh' },
    ],
  },
  {
    label: 'Sức khỏe tình dục',
    options: [
      { value: 'SAFE_SEX_COUNSELING_NEEDED', label: 'Chưa được tư vấn tình dục an toàn' },
      { value: 'STI_RISK', label: 'Có nguy cơ mắc STIs' },
      { value: 'REPRODUCTIVE_TRACT_INFECTION', label: 'Nghi ngờ/mắc nhiễm khuẩn đường sinh sản' },
      { value: 'STI_SUSPECTED_OR_KNOWN', label: 'Nghi ngờ/mắc bệnh lây truyền qua đường tình dục' },
      { value: 'NO_PREGNANCY_PLAN', label: 'Chưa có kế hoạch mang thai' },
    ],
  },
];

export const CHECKLIST_CONTRAINDICATION_LABELS: Readonly<Record<string, string>> = Object.fromEntries(
  CHECKLIST_CONTRAINDICATION_GROUPS.flatMap((group) => group.options.map((option) => [option.value, option.label])),
);

export interface ChecklistSubstage {
  code: string;
  anchor: ChecklistAnchorType;
  startInclusive: number;
  endInclusive: number;
  unit: ChecklistRangeUnit;
}

export interface ReviewFeedback {
  reason: string;
  requestedAt: string | null;
  requestedBy: string | null;
  versionNo: number | null;
}

export interface ContentListItem {
  id: string;
  type: ContentType;
  title: string;
  stage: ContentStage;
  topicId: string;
  publishedAt: string | null;
}

export interface ContentDetail {
  id: string;
  type: ContentType;
  title: string;
  body: string;
  summary?: string | null;
  stage: ContentStage;
  topicId: string;
  tagIds?: string[];
  eligibleFromWeek?: number | null;
  eligibleToWeek?: number | null;
  recommendationPriority?: number;
  version: number;
  publishedAt: string | null;
  status: ContentStatus;
  createdAt: string;
  updatedAt?: string | null;
  sourceLabel?: string | null;
  sources?: ContentSource[];
  assignedExpertId?: string | null;
  assignedAt?: string | null;
  approvedBy?: string | null;
  approvedAt?: string | null;
  latestReviewFeedback?: ReviewFeedback | null;
}

export interface ExpertApprovalQueueItem {
  id: string;
  kind: 'CONTENT' | 'CHECKLIST';
  type: ContentType;
  title: string;
  stage: ContentStage;
  status: string;
  versionNo?: number;
  itemCount?: number;
  summary?: string;
  /** Toàn văn bài viết. Checklist không có — nó được duyệt theo danh sách mục. */
  body?: string;
  sourceLabel?: string;
  assignedAt?: string | null;
  updatedAt?: string | null;
  createdAt?: string | null;
}

export interface RecommendationTag {
  id: string;
  slug: string;
  domain: string;
  label: string;
}

export interface RecommendationTagCatalog {
  catalogVersion: string;
  items: RecommendationTag[];
}

export interface ContentSource { title: string; url?: string; publisher?: string; }

export interface ContentSearchItem {
  id: string;
  type: ContentType;
  title: string;
  stage: ContentStage;
  topicName: string;
  publishedAt: string | null;
}

export interface ChecklistTemplate {
  id: string;
  name: string;
  stage: ContentStage | null;
  status: ChecklistTemplateStatus;
  description: string;
  templateType: ChecklistTemplateType;
  /** 1 = legacy target-bearing; 2 = recommendation-only targetless. */
  checklistContractVersion?: number | null;
  planNumber?: number | null;
  section?: 'COMMON' | 'WEEKLY' | null;
  scheduleType?: ChecklistScheduleType | null;
  materializationPolicy?: ChecklistMaterializationPolicy | null;
  scheduleGroupKey?: string | null;
  scheduleContextType?: ChecklistCareContextType | null;
  scheduleEndMode?: ChecklistScheduleEndMode | null;
  weekBoundaryRule?: ChecklistWeekBoundaryRule | null;
  eligibilityStartInclusive?: number | null;
  eligibilityEndInclusive?: number | null;
  displayOrder?: number | null;
  items: ChecklistItem[];
  latestReviewFeedback?: ReviewFeedback | null;
  archiveReason?: string | null;
  archivedAt?: string | null;
  archivedBy?: string | null;
}

export interface ContentVersionSnapshot {
  versionNo: number;
  title: string;
  stage: string | null;
  status: string;
  sourceSummary: string | null;
  tagIds?: string[];
  eligibleFromWeek?: number | null;
  eligibleToWeek?: number | null;
  recommendationPriority?: number | null;
  changedBy: string | null;
  createdAt: string;
}

export interface ChecklistTemplateVersionSnapshot {
  versionNo: number;
  name: string;
  stage: string | null;
  status: string;
  itemCount: number;
  changedBy: string | null;
  createdAt: string;
}

export interface AdminChecklistTemplateDetail extends ChecklistTemplate {
  versionNo: number;
  lineageId: string;
  versionId: string;
  recipientRoles: ChecklistRecipientRole[];
  substage: ChecklistSubstage | null;
  migrationReviewRequired: boolean;
  distributionEnabled: boolean;
  approvedAt: string | null;
  approvedBy: string | null;
  migrationReviewedAt?: string | null;
  migrationReviewedBy?: string | null;
  checklistQuarantineReasonCode?: string | null;
  provenance?: ChecklistProvenance | null;
}

export interface ChecklistProvenance {
  schema?: string | null;
  sourceArtifactPath?: string | null;
  sourceArtifactSha256?: string | null;
  importBatchId?: string | null;
  importCorrelationId?: string | null;
  normalizerId?: string | null;
  copyReviewPolicy?: string | null;
  provenanceStatus?: string | null;
  cadenceReviewStatus?: string | null;
  cadenceReviewerUserId?: string | null;
  cadenceReviewedAt?: string | null;
  reviewAuthorityId?: string | null;
  copyReviewerUserId?: string | null;
  qualificationEvidenceRef?: string | null;
  credentialVerifiedAt?: string | null;
  contentOwnerUserId?: string | null;
  contentOwnerApprovedAt?: string | null;
  copyReviewedAt?: string | null;
  sourceTitle?: string | null;
  sourceRelationship?: string | null;
  sourceOrganization?: string | null;
  sourceVersionOrPublicationDate?: string | null;
  sourceUrl?: string | null;
  sourceLanguage?: string | null;
  renderedLanguage?: string | null;
  translationProvenance?: string | null;
  priorityNarrative?: string | null;
  priorityNarrativeMode?: string | null;
  sourceLocator?: string | null;
  renderedManifestSchema?: string | null;
  renderedManifestCanonicalization?: string | null;
  renderedManifestHash?: string | null;
  validityMode?: string | null;
  validUntil?: string | null;
  revokedAt?: string | null;
}

export interface ChecklistItem {
  id: string;
  itemText: string;
  order: number;
  isRequired: boolean | null;
  targetSubject: ChecklistTargetSubject | null;
  description?: string | null;
  sourceUrl?: string | null;
  supportFunction?: ChecklistSupportFunction | null;
  /** Authoring metadata for recurrence labels shown on the checklist item. */
  repeatWeekly?: boolean | null;
  repeatDaily?: boolean | null;
  /** Tag khảo sát mà mục này chống chỉ định (không bắt buộc). */
  contraindications?: string[] | null;
}

export interface ChecklistItemInput {
  id?: string;
  itemText: string;
  order: number;
  isRequired?: boolean | null;
  targetSubject?: ChecklistTargetSubject | null;
  description?: string | null;
  sourceUrl?: string | null;
  supportFunction?: ChecklistSupportFunction | null;
  repeatWeekly?: boolean | null;
  repeatDaily?: boolean | null;
  /** Tag khảo sát mà mục này chống chỉ định (không bắt buộc). */
  contraindications?: string[] | null;
}

export interface CreateChecklistTemplatePayload {
  name: string;
  description?: string;
  templateType: ChecklistTemplateType;
  checklistContractVersion?: number | null;
  recipientRoles: ChecklistRecipientRole[];
  stage: ContentStage | null;
  substage: ChecklistSubstage | null;
  displayOrder?: number;
  scheduleType?: ChecklistScheduleType | null;
  materializationPolicy?: ChecklistMaterializationPolicy | null;
  scheduleGroupKey?: string | null;
  scheduleContextType?: ChecklistCareContextType | null;
  scheduleEndMode?: ChecklistScheduleEndMode | null;
  weekBoundaryRule?: ChecklistWeekBoundaryRule | null;
  items: ChecklistItemInput[];
}

export interface UpdateChecklistTemplatePayload {
  name: string;
  description?: string;
  templateType: ChecklistTemplateType;
  checklistContractVersion?: number | null;
  recipientRoles: ChecklistRecipientRole[];
  stage: ContentStage | null;
  substage: ChecklistSubstage | null;
  status: ChecklistTemplateStatus;
  displayOrder?: number;
  scheduleType?: ChecklistScheduleType | null;
  materializationPolicy?: ChecklistMaterializationPolicy | null;
  scheduleGroupKey?: string | null;
  scheduleContextType?: ChecklistCareContextType | null;
  scheduleEndMode?: ChecklistScheduleEndMode | null;
  weekBoundaryRule?: ChecklistWeekBoundaryRule | null;
  // null/undefined = keep existing items unchanged; [] = clear all; non-empty = full replace
  items?: ChecklistItemInput[] | null;
}

export type CommunityTopicType = 'TOPIC' | 'CATEGORY' | 'TAG';

interface CommunityTopicMutationFields {
  name: string;
  description?: string;
  icon?: string;
  sortOrder?: number;
}

export type CreateCommunityTopicPayload = CommunityTopicMutationFields & (
  | { type: 'TOPIC'; parentId: string }
  | { type: 'CATEGORY' | 'TAG'; parentId: null }
);

// Type is intentionally absent: ADR-COM-025 makes it immutable after creation.
export interface UpdateCommunityTopicPayload extends Partial<CommunityTopicMutationFields> {
  parentId?: string | null;
  isHidden?: boolean;
}

export interface AdminChecklistTemplate {
  id: string;
  name: string;
  lineageId?: string;
  versionId?: string;
  recipientRoles?: ChecklistRecipientRole[];
  /** 0/null is the legacy, unsequenced cohort; positive values are sequence positions. */
  displayOrder?: number | null;
  stage: ContentStage | null;
  substage?: ChecklistSubstage | null;
  status: ChecklistTemplateStatus;
  description: string;
  templateType?: ChecklistTemplateType;
  checklistContractVersion?: number | null;
  planNumber?: number | null;
  section?: 'COMMON' | 'WEEKLY' | null;
  scheduleType?: ChecklistScheduleType | null;
  materializationPolicy?: ChecklistMaterializationPolicy | null;
  scheduleGroupKey?: string | null;
  scheduleContextType?: ChecklistCareContextType | null;
  scheduleEndMode?: ChecklistScheduleEndMode | null;
  weekBoundaryRule?: ChecklistWeekBoundaryRule | null;
  eligibilityStartInclusive?: number | null;
  eligibilityEndInclusive?: number | null;
  checklistQuarantineReasonCode?: string | null;
  versionNo: number;
  updatedAt: string | null;
  itemCount: number;
  migrationReviewRequired?: boolean;
  distributionEnabled?: boolean;
  assignedExpertId?: string | null;
  assignedAt?: string | null;
  /** Admin list projection only; consumers must never use this to distribute content. */
  provenanceStatus?: string | null;
  latestReviewFeedback?: ReviewFeedback | null;
}

export interface CommunityTopic {
  id: string;
  name: string;
  description: string;
  icon: string;
  type: CommunityTopicType;
  slug: string;
  parentId: string | null;
  questionCount: number;
  isHidden: boolean;
  sortOrder: number;
  createdAt: string;
  updatedAt: string;
}

export interface PaginatedResponse<T> {
  content: T[];
  totalElements: number;
  totalPages: number;
  size: number;
  number: number;
}

export const STAGE_LABELS: Record<ContentStage, string> = {
  PRE_PREGNANCY: 'Chuẩn bị mang thai',
  PREGNANCY: 'Thai kỳ',
  POSTPARTUM: 'Hậu sản',
  BABY_CARE: 'Chăm bé',
};

export const STAGE_OPTIONS: ReadonlyArray<{ value: ContentStage; label: string }> = [
  { value: 'PRE_PREGNANCY', label: STAGE_LABELS.PRE_PREGNANCY },
  { value: 'PREGNANCY', label: STAGE_LABELS.PREGNANCY },
  { value: 'POSTPARTUM', label: STAGE_LABELS.POSTPARTUM },
  { value: 'BABY_CARE', label: STAGE_LABELS.BABY_CARE },
];

export const TYPE_LABELS: Record<ContentType, string> = {
  ARTICLE: 'Bài viết',
  FAQ: 'FAQ',
  CHECKLIST: 'Checklist',
};

export const STATUS_LABELS: Record<ContentStatus, string> = {
  DRAFT: 'Bản nháp',
  PENDING_REVIEW: 'Chờ phê duyệt',
  APPROVED: 'Đã xuất bản',
  ARCHIVED: 'Đã lưu trữ',
};

export const CHECKLIST_STATUS_LABELS: Record<ChecklistTemplateStatus, string> = {
  DRAFT: 'Bản nháp',
  PENDING_REVIEW: 'Chờ duyệt',
  APPROVED: 'Đã duyệt',
  REJECTED: 'Đã từ chối',
  ARCHIVED: 'Đã lưu trữ',
};
