import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ExpertSharedRecordsPage from './ExpertSharedRecordsPage';
import {
  fetchBabyGrowthChart,
  fetchExpertSharedRecords,
  type SharedRecordEntry,
} from '../services/expertSharedRecordsService';

vi.mock('../services/expertSharedRecordsService', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/expertSharedRecordsService')>();
  return { ...actual, fetchExpertSharedRecords: vi.fn(), fetchBabyGrowthChart: vi.fn() };
});

const makeRecord = (overrides: Partial<SharedRecordEntry>): SharedRecordEntry => ({
  id: 'rec-1',
  conversationId: 'conv-1',
  motherUserId: 'mother-1',
  motherName: 'Mẹ M1',
  createdAt: '2026-09-14T08:00:00Z',
  type: 'BABY_GROWTH',
  alertLevel: 'NORMAL',
  status: 'PENDING_REVIEW',
  ...overrides,
});

describe('ExpertSharedRecordsPage (SBG-TC-018)', () => {
  afterEach(() => {
    cleanup();
  });

  it('filters mother cards by the baby growth tab', async () => {
    vi.mocked(fetchExpertSharedRecords).mockResolvedValue([
      makeRecord({
        babyGrowthData: {
          title: 'Phát triển của bé',
          babyId: '11111111-1111-1111-1111-111111111111',
          babyNickname: 'Bé Test',
          birthDate: '2025-01-10',
          measurementCount: 1,
          latest: null,
          isLiveSync: true,
        },
      }),
      makeRecord({
        id: 'rec-2',
        conversationId: 'conv-2',
        motherUserId: 'mother-2',
        motherName: 'Mẹ M2',
        type: 'CHECKLIST',
        checklistData: {
          title: 'Checklist',
          completedCount: 0,
          totalCount: 1,
          progressPercent: 0,
          currentItems: [{ text: 'Khám thai', completed: false }],
        },
      }),
    ]);
    vi.mocked(fetchBabyGrowthChart).mockResolvedValue([
      { measuredDate: '2025-01-10', weightKg: 3.2, heightCm: 50.0, headCircumferenceCm: 34.0 },
    ]);

    render(
      <MemoryRouter>
        <ExpertSharedRecordsPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText('Mẹ M2')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /^Tăng trưởng bé \(/ }));

    expect(screen.getByText('Mẹ M1')).toBeTruthy();
    expect(screen.queryByText('Mẹ M2')).toBeNull();
    expect(await screen.findByText('Xu hướng cân nặng')).toBeTruthy();
  });

  it('does not allow editing or deleting completed checklist items', async () => {
    vi.mocked(fetchExpertSharedRecords).mockResolvedValue([
      makeRecord({
        id: 'rec-checklist',
        conversationId: 'conv-checklist',
        motherUserId: 'mother-checklist',
        motherName: 'Mẹ Bầu Lan',
        type: 'CHECKLIST',
        checklistData: {
          title: 'Lộ trình chăm sóc mẹ',
          completedCount: 1,
          totalCount: 2,
          progressPercent: 50,
          currentItems: [
            { text: 'Uống vitamin buổi sáng', completed: true },
            { text: 'Đi bộ 15 phút', completed: false },
          ],
        },
      }),
    ]);

    render(
      <MemoryRouter>
        <ExpertSharedRecordsPage />
      </MemoryRouter>,
    );

    // Switch to Checklist tab if needed or find mother card
    expect(await screen.findByText('Mẹ Bầu Lan')).toBeTruthy();

    // Check items rendered
    expect(screen.getByText('Uống vitamin buổi sáng')).toBeTruthy();
    expect(screen.getByText('Đi bộ 15 phút')).toBeTruthy();

    // Only the uncompleted item should have Edit and Delete buttons
    const editButtons = screen.getAllByTitle('Chỉnh sửa việc cần làm');
    expect(editButtons.length).toBe(1);

    const deleteButtons = screen.getAllByTitle('Xóa việc cần làm');
    expect(deleteButtons.length).toBe(1);

    // Clicking completed task shows toast and prevents status toggle
    const completedItemText = screen.getByText('Uống vitamin buổi sáng');
    fireEvent.click(completedItemText);

    expect(await screen.findByText('Việc cần làm đã hoàn thành không thể chỉnh sửa.')).toBeTruthy();
  });
});
