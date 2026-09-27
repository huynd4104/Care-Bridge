import { describe, expect, it } from 'vitest';
import type { AdminChecklistTemplateDetail } from '../models/content';
import {
  buildSequenceOverview,
  evaluatePosition,
  nextFreePosition,
  positionOptions,
} from './checklistSequencePositions';

function template(overrides: Partial<AdminChecklistTemplateDetail>): AdminChecklistTemplateDetail {
  return {
    id: 'template',
    name: 'Checklist',
    templateType: 'MANDATORY',
    stage: 'PRE_PREGNANCY',
    status: 'APPROVED',
    description: null,
    versionNo: 1,
    lineageId: 'lineage',
    versionId: 'version',
    recipientRoles: ['MOTHER'],
    substage: null,
    migrationReviewRequired: false,
    distributionEnabled: true,
    approvedAt: null,
    approvedBy: null,
    items: [],
    displayOrder: 1,
    ...overrides,
  } as AdminChecklistTemplateDetail;
}

describe('checklist sequence positions', () => {
  const templates = [
    template({ id: 'a', lineageId: 'la', displayOrder: 1 }),
    template({ id: 'b', lineageId: 'lb', displayOrder: 2 }),
    template({ id: 'draft', lineageId: 'ld', displayOrder: 3, status: 'PENDING_REVIEW', distributionEnabled: false }),
    template({ id: 'old', lineageId: 'lo', displayOrder: 4, status: 'ARCHIVED', distributionEnabled: false }),
    template({ id: 'optional', lineageId: 'lx', displayOrder: 5, templateType: 'OPTIONAL' }),
  ];

  it('only counts approved, distributed mother sequence sets as occupied', () => {
    const overview = buildSequenceOverview(templates, undefined);
    expect([...overview.active.keys()].sort()).toEqual([1, 2]);
    expect(overview.pending.get(3)?.map((holder) => holder.id)).toEqual(['draft']);
    expect(nextFreePosition(overview, null)).toBe(3);
    expect(positionOptions(overview, null, 3)).toEqual([1, 2, 3]);
  });

  it('classifies occupied, replacement, free and gap positions', () => {
    const overview = buildSequenceOverview(templates, undefined);
    expect(evaluatePosition(1, overview, null).kind).toBe('occupied');
    expect(evaluatePosition(1, overview, 'la').kind).toBe('replace-own');
    expect(evaluatePosition(3, overview, null).kind).toBe('free');
    expect(evaluatePosition(5, overview, null)).toEqual({ kind: 'gap', nextFree: 3 });
  });

  it('excludes the checklist being edited and reports active legacy blockers', () => {
    const overview = buildSequenceOverview([
      template({ id: 'self', displayOrder: 1 }),
      template({ id: 'legacy', name: 'Legacy', displayOrder: 0, recipientRoles: ['MOTHER', 'FAMILY'] }),
    ], 'self');
    expect(overview.active.size).toBe(0);
    expect(overview.activeLegacy.map((holder) => holder.name)).toEqual(['Legacy']);
  });
});
