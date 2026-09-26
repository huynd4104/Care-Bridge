import type { AdminChecklistTemplateDetail } from '../models/content';

/**
 * Client-side mirror of the PRE_PREGNANCY sequence rules enforced at approval
 * (ChecklistTemplateApprovalServiceImpl#prepareSequenceApproval). The server
 * stays authoritative; this only lets authors pick a position that will pass.
 */
export interface SequenceHolder {
  id: string;
  name: string;
  versionNo: number;
  lineageId: string | null;
}

export interface SequenceOverview {
  /** Active (approved + distributed) sequence sets, keyed by position. */
  active: Map<number, SequenceHolder>;
  /** Other drafts already waiting for review at a position. */
  pending: Map<number, SequenceHolder[]>;
  /** Active out-of-sequence (position 0) mother checklists that block approval. */
  activeLegacy: SequenceHolder[];
}

export type PositionStatus =
  | { kind: 'free' }
  | { kind: 'replace-own'; holder: SequenceHolder }
  | { kind: 'occupied'; holder: SequenceHolder }
  | { kind: 'gap'; nextFree: number };

function toHolder(template: AdminChecklistTemplateDetail): SequenceHolder {
  return {
    id: template.id,
    name: template.name,
    versionNo: template.versionNo,
    lineageId: template.lineageId ?? null,
  };
}

function isActive(template: AdminChecklistTemplateDetail): boolean {
  return template.status === 'APPROVED' && template.distributionEnabled === true;
}

function isMandatoryPrePregnancy(template: AdminChecklistTemplateDetail): boolean {
  return template.stage === 'PRE_PREGNANCY' && (template.templateType ?? 'MANDATORY') === 'MANDATORY';
}

function isMotherOnly(template: AdminChecklistTemplateDetail): boolean {
  const roles = template.recipientRoles ?? [];
  return roles.length === 1 && roles[0] === 'MOTHER';
}

export function buildSequenceOverview(
  templates: readonly AdminChecklistTemplateDetail[],
  currentId: string | undefined,
): SequenceOverview {
  const active = new Map<number, SequenceHolder>();
  const pending = new Map<number, SequenceHolder[]>();
  const activeLegacy: SequenceHolder[] = [];
  for (const template of templates) {
    if (template.id === currentId || !isMandatoryPrePregnancy(template)) continue;
    const position = template.displayOrder ?? 0;
    if (position <= 0) {
      if (isActive(template) && (template.recipientRoles ?? []).includes('MOTHER')) {
        activeLegacy.push(toHolder(template));
      }
      continue;
    }
    if (!isMotherOnly(template)) continue;
    if (isActive(template)) {
      active.set(position, toHolder(template));
    } else if (template.status === 'PENDING_REVIEW') {
      pending.set(position, [...(pending.get(position) ?? []), toHolder(template)]);
    }
  }
  return { active, pending, activeLegacy };
}

/** Positions held by other lineages; the author's own lineage is replaced on approval. */
function otherLineagePositions(overview: SequenceOverview, lineageId: string | null): Set<number> {
  const positions = new Set<number>();
  overview.active.forEach((holder, position) => {
    if (!lineageId || holder.lineageId !== lineageId) positions.add(position);
  });
  return positions;
}

/** First position that keeps the chain contiguous from 1 (usually the end of the chain). */
export function nextFreePosition(overview: SequenceOverview, lineageId: string | null): number {
  const taken = otherLineagePositions(overview, lineageId);
  let position = 1;
  while (taken.has(position)) position += 1;
  return position;
}

export function evaluatePosition(
  position: number,
  overview: SequenceOverview,
  lineageId: string | null,
): PositionStatus {
  const holder = overview.active.get(position);
  if (holder) {
    return lineageId && holder.lineageId === lineageId
      ? { kind: 'replace-own', holder }
      : { kind: 'occupied', holder };
  }
  const nextFree = nextFreePosition(overview, lineageId);
  return position > nextFree ? { kind: 'gap', nextFree } : { kind: 'free' };
}

/** Options 1..(end of chain + 1), always including the currently selected value. */
export function positionOptions(
  overview: SequenceOverview,
  lineageId: string | null,
  selected: number,
): number[] {
  const highestActive = Math.max(0, ...overview.active.keys());
  const last = Math.max(highestActive + 1, nextFreePosition(overview, lineageId), selected);
  return Array.from({ length: last }, (_, index) => index + 1);
}

export function positionOptionLabel(
  position: number,
  overview: SequenceOverview,
  lineageId: string | null,
): string {
  const status = evaluatePosition(position, overview, lineageId);
  switch (status.kind) {
    case 'occupied':
      return `Bộ ${position} — Đã dùng: "${status.holder.name}" (v${status.holder.versionNo})`;
    case 'replace-own':
      return `Bộ ${position} — Thay thế phiên bản v${status.holder.versionNo} của chính checklist này`;
    case 'gap':
      return `Bộ ${position} — Chưa dùng được (phải dùng bộ ${status.nextFree} trước)`;
    default:
      return position === nextFreePosition(overview, lineageId)
        ? `Bộ ${position} — Còn trống (bộ tiếp theo)`
        : `Bộ ${position} — Còn trống`;
  }
}
