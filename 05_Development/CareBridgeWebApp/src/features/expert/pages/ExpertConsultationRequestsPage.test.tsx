// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const harness = vi.hoisted(() => ({
  get: vi.fn(),
  patch: vi.fn(),
  post: vi.fn(),
  navigate: vi.fn(),
}));

vi.mock('../../../shared/api/apiClient', () => ({
  default: {
    get: harness.get,
    patch: harness.patch,
    post: harness.post,
  },
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return { ...actual, useNavigate: () => harness.navigate };
});

import ExpertConsultationRequestsPage from './ExpertConsultationRequestsPage';

const mockRequests = [
  {
    id: 'req-1',
    counterpartDisplayName: 'Huy Nguyễn',
    topic: 'Tư vấn dinh dưỡng sơ sinh',
    status: 'PENDING',
    createdAt: new Date().toISOString(),
    directConversationId: null,
  },
  {
    id: 'req-2',
    counterpartDisplayName: 'Mẹ Lan',
    topic: 'Bé bị phát ban nhẹ',
    status: 'ACCEPTED',
    createdAt: new Date().toISOString(),
    directConversationId: 'conv-123',
  },
];

describe('ExpertConsultationRequestsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    harness.get.mockResolvedValue({
      data: {
        data: {
          content: mockRequests,
          totalElements: 2,
        },
      },
    });
  });

  afterEach(() => {
    cleanup();
  });

  it('renders requests and displays sender and topic', async () => {
    render(<ExpertConsultationRequestsPage />);

    expect(await screen.findByText('Huy Nguyễn')).toBeInTheDocument();
    expect(screen.getByText('Tư vấn dinh dưỡng sơ sinh')).toBeInTheDocument();
    expect(screen.getByText('Mẹ Lan')).toBeInTheDocument();
    expect(screen.getByText('Bé bị phát ban nhẹ')).toBeInTheDocument();
  });

  it('accepts request with PATCH call and navigates when conversation id exists', async () => {
    harness.patch.mockResolvedValueOnce({
      data: {
        data: {
          directConversationId: 'conv-999',
        },
      },
    });

    render(<ExpertConsultationRequestsPage />);
    expect(await screen.findByText('Huy Nguyễn')).toBeInTheDocument();

    const acceptBtn = screen.getByRole('button', { name: 'Chấp nhận' });
    fireEvent.click(acceptBtn);

    await waitFor(() => {
      expect(harness.patch).toHaveBeenCalledWith('/api/v1/consultation-requests/req-1/accept');
      expect(harness.navigate).toHaveBeenCalledWith('/expert/direct-chats/conv-999');
    });
  });

  it('opens rejection modal when clicking "Từ chối" and sends PATCH with reason', async () => {
    harness.patch.mockResolvedValueOnce({ data: { success: true } });

    render(<ExpertConsultationRequestsPage />);
    expect(await screen.findByText('Huy Nguyễn')).toBeInTheDocument();

    const rejectBtn = screen.getByRole('button', { name: 'Từ chối' });
    fireEvent.click(rejectBtn);

    // Modal opens
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Từ chối yêu cầu tư vấn')).toBeInTheDocument();
    const reasonInput = screen.getByLabelText(/Lý do từ chối/i);
    expect(reasonInput).toHaveValue('Chuyên gia bận lịch công tác');

    // Change reason
    fireEvent.change(reasonInput, { target: { value: 'Bác sĩ đang trong ca trực cấp cứu' } });

    // Confirm rejection
    const confirmBtn = screen.getByRole('button', { name: 'Xác nhận từ chối' });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(harness.patch).toHaveBeenCalledWith(
        '/api/v1/consultation-requests/req-1/reject',
        { reason: 'Bác sĩ đang trong ca trực cấp cứu' }
      );
    });

    // Modal closes
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
  });

  it('displays API error inside modal when rejection fails', async () => {
    harness.patch.mockRejectedValueOnce({
      response: {
        data: {
          message: 'Yêu cầu không còn ở trạng thái chờ phản hồi',
        },
      },
    });

    render(<ExpertConsultationRequestsPage />);
    expect(await screen.findByText('Huy Nguyễn')).toBeInTheDocument();

    const rejectBtn = screen.getByRole('button', { name: 'Từ chối' });
    fireEvent.click(rejectBtn);

    const confirmBtn = await screen.findByRole('button', { name: 'Xác nhận từ chối' });
    fireEvent.click(confirmBtn);

    expect(await screen.findByText('Yêu cầu không còn ở trạng thái chờ phản hồi')).toBeInTheDocument();
  });
});
