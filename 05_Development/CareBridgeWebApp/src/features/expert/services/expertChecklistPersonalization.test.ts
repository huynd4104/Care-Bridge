import { describe, expect, it, vi } from 'vitest';
import {
  CHECKLIST_SHARE_TAG,
  editChecklistItemInSharedRecord,
  parseChecklistShare,
  savePersonalizedChecklist,
  type ChecklistShareData,
} from './expertSharedRecordsService';
import { sendMessage } from '../../directChat/services/directChatApi';

vi.mock('../../directChat/services/directChatApi', () => ({
  sendMessage: vi.fn().mockResolvedValue({ messageId: 'm-1' }),
}));

describe('Expert Checklist Editing & Reverting (CareBridge suggestion preservation)', () => {
  it('allows renaming a CareBridge item and then reverting it back to the original text as EXPERT', async () => {
    const initialChecklist: ChecklistShareData = {
      title: 'Lộ trình thai kỳ',
      currentItems: [
        {
          text: 'Đo huyết áp hàng tuần',
          completed: false,
          category: 'Khám thai & Y tế',
          origin: 'SYSTEM',
        },
      ],
      historyItems: [],
      futureItems: [],
      removedItems: [],
    };

    // Step 1: Doctor edits "Đo huyết áp hàng tuần" to "Đo huyết áp hàng ngày"
    const step1 = await editChecklistItemInSharedRecord(
      'conv-1',
      initialChecklist,
      'CURRENT',
      0,
      {
        text: 'Đo huyết áp hàng ngày',
        completed: false,
        category: 'Khám thai & Y tế',
      },
      'Bác sĩ yêu cầu đo hàng ngày'
    );

    expect(step1.currentItems).toHaveLength(1);
    expect(step1.currentItems![0].text).toBe('Đo huyết áp hàng ngày');
    expect(step1.currentItems![0].isExpertCustom).toBe(true);
    expect(step1.currentItems![0].origin).toBe('EXPERT');
    expect(step1.currentItems![0].replacesText).toBe('Đo huyết áp hàng tuần');
    expect(step1.removedItems).toContain('Đo huyết áp hàng tuần');

    // Step 2: Doctor edits "Đo huyết áp hàng ngày" back to original "Đo huyết áp hàng tuần"
    const step2 = await editChecklistItemInSharedRecord(
      'conv-1',
      step1,
      'CURRENT',
      0,
      {
        text: 'Đo huyết áp hàng tuần',
        completed: false,
        category: 'Khám thai & Y tế',
      },
      'Chỉnh về theo dõi hàng tuần'
    );

    expect(step2.currentItems).toHaveLength(1);
    expect(step2.currentItems![0].text).toBe('Đo huyết áp hàng tuần');
    expect(step2.currentItems![0].isExpertCustom).toBe(true);
    expect(step2.currentItems![0].origin).toBe('EXPERT');
    // It should NOT be in removedItems!
    expect(step2.removedItems).not.toContain('Đo huyết áp hàng tuần');
  });

  it('parseChecklistShare does not filter out expert items if removedItems contains their title', () => {
    const rawPayload: ChecklistShareData = {
      title: 'Lộ trình thai kỳ',
      currentItems: [
        {
          text: 'Đo huyết áp hàng tuần',
          completed: false,
          category: 'Khám thai & Y tế',
          origin: 'EXPERT',
          isExpertCustom: true,
        },
      ],
      removedItems: ['Đo huyết áp hàng tuần'],
    };

    const parsed = parseChecklistShare(`${CHECKLIST_SHARE_TAG}\n${JSON.stringify(rawPayload)}`);
    expect(parsed).not.toBeNull();
    expect(parsed?.currentItems).toHaveLength(1);
    expect(parsed?.currentItems![0].text).toBe('Đo huyết áp hàng tuần');
    expect(parsed?.currentItems![0].isExpertCustom).toBe(true);
    expect(parsed?.removedItems).not.toContain('Đo huyết áp hàng tuần');
  });

  it('savePersonalizedChecklist cleans active items from removedItems', async () => {
    const rawPayload: ChecklistShareData = {
      title: 'Lộ trình thai kỳ',
      currentItems: [
        {
          text: 'Đo huyết áp hàng tuần',
          completed: false,
          category: 'Khám thai & Y tế',
          origin: 'EXPERT',
          isExpertCustom: true,
        },
      ],
      removedItems: ['Đo huyết áp hàng tuần', 'Item Khác Bị Xóa'],
    };

    const saved = await savePersonalizedChecklist('conv-1', rawPayload);
    expect(saved.currentItems).toHaveLength(1);
    expect(saved.currentItems![0].text).toBe('Đo huyết áp hàng tuần');
    expect(saved.removedItems).toEqual(['Item Khác Bị Xóa']);
  });
});
