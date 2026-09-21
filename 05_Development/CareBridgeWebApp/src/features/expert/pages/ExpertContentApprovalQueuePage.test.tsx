// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const harness = vi.hoisted(() => ({
  fetchExpertApprovalQueue: vi.fn(),
  fetchExpertApprovalSummary: vi.fn(),
  decideExpertContent: vi.fn(),
  decideExpertChecklist: vi.fn(),
  navigate: vi.fn(),
}));

vi.mock('../../contentManagement/services/contentApi', () => ({
  fetchExpertApprovalQueue: harness.fetchExpertApprovalQueue,
  fetchExpertApprovalSummary: harness.fetchExpertApprovalSummary,
  decideExpertContent: harness.decideExpertContent,
  decideExpertChecklist: harness.decideExpertChecklist,
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => harness.navigate };
});

import ExpertContentApprovalQueuePage from './ExpertContentApprovalQueuePage';

const mockItems = [
  {
    id: 'art-1',
    kind: 'CONTENT' as const,
    title: 'Dinh dưỡng 3 tháng đầu',
    type: 'ARTICLE' as const,
    stage: 'PREGNANCY' as const,
    versionNo: 1,
    summary: 'Tóm tắt bài viết dinh dưỡng',
    assignedAt: '2026-09-20T10:00:00Z',
    updatedAt: '2026-09-20T10:00:00Z',
  },
  {
    id: 'faq-1',
    kind: 'CONTENT' as const,
    title: 'Bé bị sốt phải làm sao?',
    type: 'FAQ' as const,
    stage: 'BABY_CARE' as const,
    versionNo: 1,
    summary: 'Giải đáp câu hỏi sốt ở trẻ',
    assignedAt: '2026-09-20T11:00:00Z',
    updatedAt: '2026-09-20T11:00:00Z',
  },
  {
    id: 'chk-1',
    kind: 'CHECKLIST' as const,
    title: 'Checklist chuẩn bị sinh',
    type: 'CHECKLIST' as const,
    stage: 'PREGNANCY' as const,
    versionNo: 2,
    itemCount: 8,
    assignedAt: '2026-09-20T12:00:00Z',
    updatedAt: '2026-09-20T12:00:00Z',
  },
];

describe('ExpertContentApprovalQueuePage', () => {
  beforeEach(() => {
    harness.fetchExpertApprovalQueue.mockReset();
    harness.fetchExpertApprovalSummary.mockReset();
    harness.decideExpertContent.mockReset();
    harness.decideExpertChecklist.mockReset();
    harness.navigate.mockReset();

    harness.fetchExpertApprovalSummary.mockResolvedValue({
      all: 3,
      article: 1,
      faq: 1,
      checklist: 1,
    });

    harness.fetchExpertApprovalQueue.mockImplementation(async (params) => {
      const filtered = params?.type
        ? mockItems.filter((i) => i.type === params.type)
        : mockItems;
      return {
        content: filtered,
        page: params?.page ?? 0,
        size: params?.size ?? 20,
        totalElements: filtered.length,
        totalPages: 1,
      };
    });
  });

  afterEach(cleanup);

  it('renders queue items and summary statistics correctly', async () => {
    render(<ExpertContentApprovalQueuePage />);

    expect(await screen.findByText('Dinh dưỡng 3 tháng đầu')).toBeTruthy();
    expect(screen.getByText('Bé bị sốt phải làm sao?')).toBeTruthy();
    expect(screen.getByText('Checklist chuẩn bị sinh')).toBeTruthy();
    expect(screen.getByText('Phiên bản v2')).toBeTruthy();
    expect(screen.getByText('· 8 mục checklist')).toBeTruthy();
  });

  it('opens batch approval dropdown with options and item counts', async () => {
    render(<ExpertContentApprovalQueuePage />);

    const batchButton = await screen.findByRole('button', { name: /Phê duyệt tất cả/i });
    fireEvent.click(batchButton);

    expect(screen.getByText('Phê duyệt tất cả bài viết')).toBeTruthy();
    expect(screen.getByText('Phê duyệt tất cả FAQ')).toBeTruthy();
    expect(screen.getByText('Phê duyệt tất cả Checklist')).toBeTruthy();
  });

  it('opens batch confirmation modal when selecting an option and executes batch approval for all items', async () => {
    harness.decideExpertContent.mockResolvedValue({ id: 'art-1', previousStatus: 'PENDING_REVIEW', newStatus: 'APPROVED' });
    harness.decideExpertChecklist.mockResolvedValue({ id: 'chk-1', previousStatus: 'PENDING_REVIEW', newStatus: 'APPROVED' });

    render(<ExpertContentApprovalQueuePage />);

    const batchButton = await screen.findByRole('button', { name: /Phê duyệt tất cả/i });
    fireEvent.click(batchButton);

    const allOption = screen.getAllByText('Phê duyệt tất cả')[1]; // Second instance is in dropdown
    fireEvent.click(allOption);

    // Modal title should appear
    expect(await screen.findByText('Phê duyệt tất cả nội dung đang chờ')).toBeTruthy();
    expect(await screen.findByText(/Đã chọn/)).toBeTruthy();

    // Confirm batch approval
    const confirmBtn = await screen.findByRole('button', { name: /Xác nhận phê duyệt \(3 mục\)/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(harness.decideExpertContent).toHaveBeenCalledTimes(2); // art-1 and faq-1
      expect(harness.decideExpertChecklist).toHaveBeenCalledTimes(1); // chk-1
    });

    expect(harness.decideExpertContent).toHaveBeenCalledWith('art-1', 'APPROVE');
    expect(harness.decideExpertContent).toHaveBeenCalledWith('faq-1', 'APPROVE');
    expect(harness.decideExpertChecklist).toHaveBeenCalledWith('chk-1', 'APPROVE');

    // Success message should appear
    expect(await screen.findByText(/Đã phê duyệt và xuất bản thành công tất cả 3 mục/i)).toBeTruthy();
  });

  it('allows filtering by target in batch approval modal (e.g. only ARTICLE)', async () => {
    harness.decideExpertContent.mockResolvedValue({ id: 'art-1', previousStatus: 'PENDING_REVIEW', newStatus: 'APPROVED' });

    render(<ExpertContentApprovalQueuePage />);

    const batchButton = await screen.findByRole('button', { name: /Phê duyệt tất cả/i });
    fireEvent.click(batchButton);

    const articleOption = screen.getByText('Phê duyệt tất cả bài viết');
    fireEvent.click(articleOption);

    expect(await screen.findByText('Phê duyệt tất cả bài viết y tế')).toBeTruthy();
    const confirmBtn = await screen.findByRole('button', { name: /Xác nhận phê duyệt \(1 mục\)/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(harness.decideExpertContent).toHaveBeenCalledTimes(1);
      expect(harness.decideExpertContent).toHaveBeenCalledWith('art-1', 'APPROVE');
      expect(harness.decideExpertChecklist).not.toHaveBeenCalled();
    });
  });

  it('allows toggling items selection in batch modal', async () => {
    harness.decideExpertContent.mockResolvedValue({ id: 'art-1', previousStatus: 'PENDING_REVIEW', newStatus: 'APPROVED' });

    render(<ExpertContentApprovalQueuePage />);

    const batchButton = await screen.findByRole('button', { name: /Phê duyệt tất cả/i });
    fireEvent.click(batchButton);

    const allOption = screen.getAllByText('Phê duyệt tất cả')[1];
    fireEvent.click(allOption);

    // Click "Bỏ chọn tất cả"
    const toggleAllBtn = await screen.findByRole('button', { name: /Bỏ chọn tất cả/i });
    fireEvent.click(toggleAllBtn);

    expect(screen.getByText((_, el) => el?.tagName === 'SPAN' && (el?.textContent?.includes('Đã chọn 0 / 3 mục') ?? false))).toBeTruthy();

    // Select single item: "Dinh dưỡng 3 tháng đầu" in modal
    const articleRow = screen.getAllByText('Dinh dưỡng 3 tháng đầu')[1];
    fireEvent.click(articleRow);

    expect(screen.getByText((_, el) => el?.tagName === 'SPAN' && (el?.textContent?.includes('Đã chọn 1 / 3 mục') ?? false))).toBeTruthy();

    const confirmBtn = await screen.findByRole('button', { name: /Xác nhận phê duyệt \(1 mục\)/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(harness.decideExpertContent).toHaveBeenCalledTimes(1);
      expect(harness.decideExpertContent).toHaveBeenCalledWith('art-1', 'APPROVE');
      expect(harness.decideExpertChecklist).not.toHaveBeenCalled();
    });
  });

  it('handles single item approval from the table', async () => {
    harness.decideExpertChecklist.mockResolvedValue({ id: 'chk-1', previousStatus: 'PENDING_REVIEW', newStatus: 'APPROVED' });

    render(<ExpertContentApprovalQueuePage />);

    const approveButtons = await screen.findAllByTitle('Phê duyệt và xuất bản');
    fireEvent.click(approveButtons[0]);

    expect(screen.getByText('Xác nhận phê duyệt nội dung')).toBeTruthy();

    const submitBtn = screen.getByRole('button', { name: /Xác nhận xuất bản/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(harness.decideExpertChecklist).toHaveBeenCalledWith('chk-1', 'APPROVE', undefined);
    });

    expect(await screen.findByText(/Đã phê duyệt và xuất bản: "Checklist chuẩn bị sinh"/i)).toBeTruthy();
  });
});
