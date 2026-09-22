import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  decideExpertChecklist,
  decideExpertContent,
  fetchExpertApprovalQueue,
  fetchExpertApprovalSummary,
} from '../../contentManagement/services/contentApi';
import type { ContentStage, ContentType, ExpertApprovalQueueItem } from '../../contentManagement/models/content';
import { STAGE_LABELS, STAGE_OPTIONS, TYPE_LABELS } from '../../contentManagement/models/content';
import { SortableTableHeader, type SortDirection } from '../../contentManagement/components/SortableTableHeader';
import { nextSortDirection, sortRows } from '../../contentManagement/utils/tableSorting';

type TypeFilter = 'ALL' | ContentType;
type BatchTarget = 'ALL' | 'ARTICLE' | 'FAQ' | 'CHECKLIST';
type QueueSortKey = 'title' | 'type' | 'stage' | 'assignedAt';

type PendingDecision = {
  item: ExpertApprovalQueueItem;
  decision: 'APPROVE' | 'REJECT';
};

const PAGE_SIZE_OPTIONS = [10, 20, 50] as const;

const CONTENT_TABS: { label: string; value: TypeFilter; icon: string }[] = [
  { label: 'Tất cả nội dung', value: 'ALL', icon: 'view_list' },
  { label: 'Bài viết y tế', value: 'ARTICLE', icon: 'article' },
  { label: 'Câu hỏi FAQ', value: 'FAQ', icon: 'quiz' },
  { label: 'Checklist hành trình', value: 'CHECKLIST', icon: 'checklist' },
];

function formatDateTime(iso?: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' });
}

export default function ExpertContentApprovalQueuePage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<ExpertApprovalQueueItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Filters
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('ALL');
  const [stageFilter, setStageFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Tab & Batch counts (accurate across all content, not just current page)
  const [tabCounts, setTabCounts] = useState<{
    ALL: number;
    ARTICLE: number;
    FAQ: number;
    CHECKLIST: number;
  }>({
    ALL: 0,
    ARTICLE: 0,
    FAQ: 0,
    CHECKLIST: 0,
  });

  // Sorting
  const [sortKey, setSortKey] = useState<QueueSortKey>('assignedAt');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // Pagination
  const [page, setPage] = useState<number>(0);
  const [pageSize, setPageSize] = useState<(typeof PAGE_SIZE_OPTIONS)[number]>(20);
  const [totalElements, setTotalElements] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);

  // Decision Modal
  const [pendingDecision, setPendingDecision] = useState<PendingDecision | null>(null);
  const [rejectReason, setRejectReason] = useState<string>('');
  const [rejectReasonError, setRejectReasonError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Batch Approval State
  const [isBatchMenuOpen, setIsBatchMenuOpen] = useState<boolean>(false);
  const [batchTarget, setBatchTarget] = useState<BatchTarget | null>(null);
  const [batchModalItems, setBatchModalItems] = useState<ExpertApprovalQueueItem[]>([]);
  const [batchModalLoading, setBatchModalLoading] = useState<boolean>(false);
  const [isBatchApproving, setIsBatchApproving] = useState<boolean>(false);
  const [batchError, setBatchError] = useState<string | null>(null);
  const [selectedBatchItemIds, setSelectedBatchItemIds] = useState<Set<string>>(new Set());
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsBatchMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const getDetailPath = (item: ExpertApprovalQueueItem) => {
    return item.kind === 'CHECKLIST'
      ? `/expert/content-review/checklists/${item.id}`
      : `/expert/content-review/${item.id}`;
  };

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchExpertApprovalQueue({
        type: typeFilter === 'ALL' ? undefined : typeFilter,
        stage: stageFilter === 'ALL' ? undefined : (stageFilter as ContentStage),
        keyword: searchQuery.trim() || undefined,
        page,
        size: pageSize,
      });
      setItems(res.content || []);
      setTotalElements(res.totalElements || 0);
      setTotalPages(res.totalPages || 1);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Không thể tải danh sách thẩm định';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [typeFilter, stageFilter, searchQuery, page, pageSize]);

  const loadSummaryCounts = useCallback(async () => {
    const stage = stageFilter === 'ALL' ? undefined : (stageFilter as ContentStage);
    const keyword = searchQuery.trim() || undefined;

    try {
      const summary = await fetchExpertApprovalSummary({ stage, keyword });
      setTabCounts({
        ALL: summary.all,
        ARTICLE: summary.article,
        FAQ: summary.faq,
        CHECKLIST: summary.checklist,
      });
    } catch {
      // Fallback: fetch counts via Promise.all across each type with size: 1
      try {
        const [allRes, artRes, faqRes, chkRes] = await Promise.all([
          fetchExpertApprovalQueue({ stage, keyword, page: 0, size: 1 }),
          fetchExpertApprovalQueue({ type: 'ARTICLE', stage, keyword, page: 0, size: 1 }),
          fetchExpertApprovalQueue({ type: 'FAQ', stage, keyword, page: 0, size: 1 }),
          fetchExpertApprovalQueue({ type: 'CHECKLIST', stage, keyword, page: 0, size: 1 }),
        ]);
        setTabCounts({
          ALL: allRes.totalElements || 0,
          ARTICLE: artRes.totalElements || 0,
          FAQ: faqRes.totalElements || 0,
          CHECKLIST: chkRes.totalElements || 0,
        });
      } catch (err) {
        console.error('Failed to load queue summary counts', err);
      }
    }
  }, [stageFilter, searchQuery]);

  useEffect(() => {
    void loadQueue();
  }, [loadQueue]);

  useEffect(() => {
    void loadSummaryCounts();
  }, [loadSummaryCounts]);

  const openBatchConfirmation = async (target: BatchTarget) => {
    setIsBatchMenuOpen(false);
    setBatchError(null);
    setBatchTarget(target);
    setBatchModalLoading(true);

    try {
      const res = await fetchExpertApprovalQueue({
        type: target === 'ALL' ? undefined : target,
        stage: stageFilter === 'ALL' ? undefined : (stageFilter as ContentStage),
        keyword: searchQuery.trim() || undefined,
        page: 0,
        size: 500,
      });
      const fetchedItems = res.content || [];
      setBatchModalItems(fetchedItems);
      setSelectedBatchItemIds(new Set(fetchedItems.map((item) => `${item.kind}-${item.id}`)));
    } catch {
      const fallbackItems = items.filter((item) => {
        if (target === 'ALL') return true;
        return item.type === target;
      });
      setBatchModalItems(fallbackItems);
      setSelectedBatchItemIds(new Set(fallbackItems.map((item) => `${item.kind}-${item.id}`)));
    } finally {
      setBatchModalLoading(false);
    }
  };

  const toggleSelectBatchItem = (key: string) => {
    setSelectedBatchItemIds((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const toggleSelectAllBatch = () => {
    if (selectedBatchItemIds.size === batchModalItems.length) {
      setSelectedBatchItemIds(new Set());
    } else {
      setSelectedBatchItemIds(new Set(batchModalItems.map((item) => `${item.kind}-${item.id}`)));
    }
  };

  const confirmBatchApproval = async () => {
    if (!batchTarget) return;

    const targetItems = batchModalItems.filter((item) =>
      selectedBatchItemIds.has(`${item.kind}-${item.id}`)
    );

    if (targetItems.length === 0) {
      setBatchTarget(null);
      return;
    }

    setIsBatchApproving(true);
    setBatchError(null);

    try {
      const results = await Promise.allSettled(
        targetItems.map((item) =>
          item.kind === 'CHECKLIST'
            ? decideExpertChecklist(item.id, 'APPROVE')
            : decideExpertContent(item.id, 'APPROVE')
        )
      );

      const failedCount = results.filter((r) => r.status === 'rejected').length;
      if (failedCount > 0) {
        const successCount = results.length - failedCount;
        setBatchError(`Đã phê duyệt ${successCount}/${results.length} mục. ${failedCount} mục bị lỗi, vui lòng thử lại.`);
        await Promise.all([loadQueue(), loadSummaryCounts()]);
      } else {
        setSuccessMessage(`Đã phê duyệt và xuất bản thành công tất cả ${results.length} mục.`);
        setBatchTarget(null);
        await Promise.all([loadQueue(), loadSummaryCounts()]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Không thể phê duyệt các mục đã chọn. Vui lòng thử lại.';
      setBatchError(msg);
    } finally {
      setIsBatchApproving(false);
    }
  };

  const handleOpenDecision = (item: ExpertApprovalQueueItem, decision: 'APPROVE' | 'REJECT') => {
    setPendingDecision({ item, decision });
    setRejectReason('');
    setRejectReasonError(null);
  };

  const handleCloseDecision = () => {
    if (submitting) return;
    setPendingDecision(null);
    setRejectReason('');
    setRejectReasonError(null);
  };

  const handleSubmitDecision = async () => {
    if (!pendingDecision) return;

    if (pendingDecision.decision === 'REJECT' && !rejectReason.trim()) {
      setRejectReasonError('Vui lòng nhập lý do từ chối / góp ý chỉnh sửa cho tác giả.');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const { item, decision } = pendingDecision;
      if (item.kind === 'CHECKLIST') {
        await decideExpertChecklist(item.id, decision, decision === 'REJECT' ? rejectReason.trim() : undefined);
      } else {
        await decideExpertContent(item.id, decision, decision === 'REJECT' ? rejectReason.trim() : undefined);
      }

      setSuccessMessage(
        decision === 'APPROVE'
          ? `Đã phê duyệt và xuất bản: "${item.title}"`
          : `Đã trả về yêu cầu chỉnh sửa: "${item.title}"`
      );
      handleCloseDecision();
      await Promise.all([loadQueue(), loadSummaryCounts()]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Thao tác thất bại';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const sortedItems = useMemo(() => sortRows(items, sortDirection, (item) => {
    switch (sortKey) {
      case 'title': return item.title;
      case 'type': return TYPE_LABELS[item.type] || item.type;
      case 'stage': return item.stage ? STAGE_LABELS[item.stage] : '';
      case 'assignedAt': {
        const iso = item.assignedAt || item.updatedAt;
        return iso ? new Date(iso).getTime() : null;
      }
    }
  }), [items, sortDirection, sortKey]);

  const changeSort = (key: QueueSortKey) => {
    setSortDirection(nextSortDirection(sortKey, key, sortDirection));
    setSortKey(key);
  };

  const resetFilters = () => {
    setSearchQuery('');
    setTypeFilter('ALL');
    setStageFilter('ALL');
    setPage(0);
  };

  const pageStart = items.length === 0 ? 0 : page * pageSize + 1;
  const pageEnd = Math.min((page + 1) * pageSize, totalElements);

  return (
    <div className="portal-page">
      <main className="font-sans">
        <div className="p-8">
          {/* Header */}
          <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-[26px] font-bold text-on-surface m-0">Thẩm định & Phê duyệt nội dung</h1>
              <p className="text-on-surface-variant text-sm mt-1">
                Các bài viết y khoa, giải đáp FAQ và checklist sức khỏe được hệ thống tự động phân chia cho bạn thẩm định
              </p>
            </div>
            <div className="flex items-center gap-3 self-start md:self-auto">
              {/* Batch Approve Dropdown */}
              <div className="relative inline-block text-left" ref={dropdownRef}>
                <button
                  type="button"
                  onClick={() => setIsBatchMenuOpen((prev) => !prev)}
                  disabled={loading || isBatchApproving || items.length === 0}
                  className="inline-flex items-center gap-2 py-2.5 px-5 rounded-full bg-emerald-600 text-white text-sm font-semibold cursor-pointer hover:bg-emerald-700 disabled:opacity-50 shadow-sm transition-colors"
                  title="Phê duyệt hàng loạt các nội dung đang chờ"
                >
                  <span className="material-symbols-outlined text-lg">done_all</span>
                  Phê duyệt tất cả
                  <span className="material-symbols-outlined text-lg">arrow_drop_down</span>
                </button>

                {isBatchMenuOpen && (
                  <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-surface border border-surface-container-highest shadow-xl py-2 z-30">
                    <button
                      type="button"
                      onClick={() => void openBatchConfirmation('ALL')}
                      className="w-full text-left px-4 py-2.5 text-sm font-semibold text-on-surface hover:bg-surface-container-low flex items-center justify-between cursor-pointer transition-colors"
                    >
                      <span className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-emerald-600 text-lg">select_all</span>
                        Phê duyệt tất cả
                      </span>
                      <span className="py-0.5 px-2.5 rounded-full bg-surface-container-high text-xs font-bold text-outline">
                        {tabCounts.ALL}
                      </span>
                    </button>

                    <button
                      type="button"
                      onClick={() => void openBatchConfirmation('ARTICLE')}
                      className="w-full text-left px-4 py-2.5 text-sm font-semibold text-on-surface hover:bg-surface-container-low flex items-center justify-between cursor-pointer transition-colors"
                    >
                      <span className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-blue-600 text-lg">article</span>
                        Phê duyệt tất cả bài viết
                      </span>
                      <span className="py-0.5 px-2.5 rounded-full bg-surface-container-high text-xs font-bold text-outline">
                        {tabCounts.ARTICLE}
                      </span>
                    </button>

                    <button
                      type="button"
                      onClick={() => void openBatchConfirmation('FAQ')}
                      className="w-full text-left px-4 py-2.5 text-sm font-semibold text-on-surface hover:bg-surface-container-low flex items-center justify-between cursor-pointer transition-colors"
                    >
                      <span className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-amber-600 text-lg">quiz</span>
                        Phê duyệt tất cả FAQ
                      </span>
                      <span className="py-0.5 px-2.5 rounded-full bg-surface-container-high text-xs font-bold text-outline">
                        {tabCounts.FAQ}
                      </span>
                    </button>

                    <button
                      type="button"
                      onClick={() => void openBatchConfirmation('CHECKLIST')}
                      className="w-full text-left px-4 py-2.5 text-sm font-semibold text-on-surface hover:bg-surface-container-low flex items-center justify-between cursor-pointer transition-colors"
                    >
                      <span className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-purple-600 text-lg">checklist</span>
                        Phê duyệt tất cả Checklist
                      </span>
                      <span className="py-0.5 px-2.5 rounded-full bg-surface-container-high text-xs font-bold text-outline">
                        {tabCounts.CHECKLIST}
                      </span>
                    </button>
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={() => {
                  void loadQueue();
                  void loadSummaryCounts();
                }}
                disabled={loading || isBatchApproving}
                className="inline-flex items-center gap-2 py-2.5 px-5 rounded-full bg-surface border border-outline-variant text-on-surface-variant text-sm font-semibold cursor-pointer hover:bg-surface-container-low disabled:opacity-50 transition-colors"
              >
                <span className={`material-symbols-outlined text-lg ${loading ? 'animate-spin' : ''}`}>
                  refresh
                </span>
                Làm mới
              </button>
            </div>
          </div>

          {/* Notifications */}
          {successMessage && (
            <div className="mb-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm text-emerald-700 dark:text-emerald-300 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-emerald-600 text-[20px]">check_circle</span>
                <span>{successMessage}</span>
              </div>
              <button
                type="button"
                onClick={() => setSuccessMessage(null)}
                className="text-emerald-700 hover:text-emerald-900 dark:text-emerald-300 cursor-pointer"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>
          )}

          {error && (
            <div className="mb-4 rounded-2xl border border-error-container bg-error-container/60 p-4 text-sm text-error flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[20px]">error</span>
                <span>{error}</span>
              </div>
              <button
                type="button"
                onClick={() => setError(null)}
                className="text-rose-700 hover:text-rose-900 dark:text-rose-300 cursor-pointer"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </div>
          )}

          {/* Action & Filter Bar */}
          <div className="bg-surface rounded-2xl p-4 shadow-sm border border-surface-container-highest mb-6 space-y-4">
            {/* Tabs */}
            <div className="flex flex-wrap gap-2 border-b border-surface-container-highest pb-3">
              {CONTENT_TABS.map((tabItem) => (
                <button
                  key={tabItem.value}
                  type="button"
                  onClick={() => {
                    setTypeFilter(tabItem.value);
                    setPage(0);
                  }}
                  className={`inline-flex items-center gap-2 py-2 px-4 rounded-full text-xs font-semibold cursor-pointer transition-colors ${
                    typeFilter === tabItem.value
                      ? 'bg-primary text-on-primary shadow-sm'
                      : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container-highest'
                  }`}
                >
                  <span className="material-symbols-outlined text-base">{tabItem.icon}</span>
                  {tabItem.label}
                  <span
                    className={`py-0.5 px-2 rounded-full text-[11px] font-bold ${
                      typeFilter === tabItem.value
                        ? 'bg-white/20 text-white'
                        : 'bg-surface-container-high text-outline'
                    }`}
                  >
                    {tabCounts[tabItem.value]}
                  </span>
                </button>
              ))}
            </div>

            {/* Filter controls */}
            <div className="flex flex-col xl:flex-row items-center gap-3">
              <div className="flex-1 w-full relative">
                <span className="material-symbols-outlined text-outline absolute left-[14px] top-1/2 -translate-y-1/2 text-xl">
                  search
                </span>
                <input
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setPage(0);
                  }}
                  placeholder="Tìm theo tiêu đề, mô tả, nội dung..."
                  className="w-full py-2.5 pr-[14px] pl-[42px] rounded-2xl border border-outline-variant bg-surface text-sm text-on-surface outline-none font-sans"
                />
              </div>

              <div className="flex flex-wrap md:flex-nowrap items-center gap-2 w-full xl:w-auto">
                <select
                  value={stageFilter}
                  onChange={(e) => {
                    setStageFilter(e.target.value);
                    setPage(0);
                  }}
                  className="py-2.5 px-4 rounded-2xl border border-outline-variant bg-surface text-sm text-on-surface-variant cursor-pointer font-sans"
                >
                  <option value="ALL">Tất cả giai đoạn</option>
                  {STAGE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>

                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value) as typeof pageSize);
                    setPage(0);
                  }}
                  className="py-2.5 px-4 rounded-2xl border border-outline-variant bg-surface text-sm text-on-surface-variant cursor-pointer font-sans"
                >
                  {PAGE_SIZE_OPTIONS.map((size) => (
                    <option key={size} value={size}>
                      {size} / trang
                    </option>
                  ))}
                </select>

                {(searchQuery || stageFilter !== 'ALL' || typeFilter !== 'ALL') && (
                  <button
                    type="button"
                    onClick={resetFilters}
                    className="py-2.5 px-4 rounded-full border border-outline-variant bg-surface text-xs font-semibold text-on-surface-variant cursor-pointer hover:bg-surface-container-low flex items-center gap-1 whitespace-nowrap"
                  >
                    <span className="material-symbols-outlined text-base">filter_alt_off</span>
                    Xóa lọc
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Data Table */}
          <div className="bg-surface rounded-2xl p-6 shadow-md border border-surface-container-highest">
            {loading ? (
              <div className="py-12 text-center text-outline">Đang tải danh sách thẩm định...</div>
            ) : items.length === 0 ? (
              <div className="py-12 text-center text-outline">Không có nội dung nào chờ thẩm định.</div>
            ) : (
              <>
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="border-b-2 border-surface-container-highest text-left">
                        {([
                          ['title', 'NỘI DUNG'],
                          ['type', 'PHÂN LOẠI'],
                          ['stage', 'GIAI ĐOẠN'],
                          ['assignedAt', 'THỜI ĐIỂM GÁN'],
                        ] as const).map(([key, label]) => (
                          <SortableTableHeader
                            key={key}
                            label={label}
                            active={sortKey === key}
                            direction={sortDirection}
                            onClick={() => changeSort(key)}
                          />
                        ))}
                        <th
                          scope="col"
                          className="py-3 px-2 text-[11px] font-semibold text-outline uppercase tracking-[0.05em] text-right"
                        >
                          THAO TÁC
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedItems.map((item) => (
                        <tr
                          key={`${item.kind}-${item.id}`}
                          className="border-b border-surface-container-highest hover:bg-surface-bright transition-colors"
                        >
                          {/* Content Title & Summary */}
                          <td
                            className="py-3.5 px-2 max-w-[380px] cursor-pointer"
                            onClick={() => navigate(getDetailPath(item))}
                          >
                            <div className="font-semibold text-sm text-on-surface hover:text-primary transition-colors">
                              {item.title}
                            </div>
                            {item.summary && (
                              <div className="text-xs text-on-surface-variant line-clamp-2 mt-0.5">
                                {item.summary}
                              </div>
                            )}
                            <div className="mt-1 flex items-center gap-2 text-[11px] text-outline">
                              <span>Phiên bản v{item.versionNo ?? 1}</span>
                              {item.itemCount !== undefined && <span>· {item.itemCount} mục checklist</span>}
                              {item.sourceLabel && <span>· Nguồn: {item.sourceLabel}</span>}
                            </div>
                          </td>

                          {/* Type Badge */}
                          <td className="py-3.5 px-2 whitespace-nowrap">
                            <span className="inline-flex items-center gap-1 py-1 px-3 rounded-full bg-surface-container-low text-primary text-xs font-semibold">
                              <span className="material-symbols-outlined text-[15px]">
                                {item.type === 'ARTICLE' ? 'article' : item.type === 'FAQ' ? 'quiz' : 'checklist'}
                              </span>
                              {TYPE_LABELS[item.type] || item.type}
                            </span>
                          </td>

                          {/* Stage Badge */}
                          <td className="py-3.5 px-2 text-[13px] text-on-surface-variant whitespace-nowrap">
                            {item.stage ? STAGE_LABELS[item.stage] : 'Chung'}
                          </td>

                          {/* Assigned At */}
                          <td className="py-3.5 px-2 whitespace-nowrap text-[13px] text-outline">
                            {formatDateTime(item.assignedAt || item.updatedAt)}
                          </td>

                          {/* Actions */}
                          <td className="py-3.5 px-2">
                            <div className="flex items-center gap-1.5 justify-end">
                              <button
                                type="button"
                                onClick={() => navigate(getDetailPath(item))}
                                className="h-8 py-1 px-3 rounded-lg border border-outline-variant bg-transparent cursor-pointer text-xs font-semibold text-primary flex items-center gap-1 hover:bg-surface-container-low transition-colors"
                                title="Xem chi tiết nội dung và thẩm định"
                              >
                                <span className="material-symbols-outlined text-base">visibility</span>
                                Xem
                              </button>

                              <button
                                type="button"
                                onClick={() => handleOpenDecision(item, 'APPROVE')}
                                className="h-8 py-1 px-4 rounded-full bg-emerald-600 text-white border-0 text-xs font-semibold cursor-pointer flex items-center gap-1 hover:bg-emerald-700 shadow-sm transition-colors"
                                title="Phê duyệt và xuất bản"
                              >
                                <span className="material-symbols-outlined text-base">check</span>
                                Duyệt
                              </button>

                              <button
                                type="button"
                                onClick={() => handleOpenDecision(item, 'REJECT')}
                                className="h-8 py-1 px-3 rounded-lg border border-outline-variant bg-surface text-on-surface-variant text-xs font-semibold cursor-pointer flex items-center gap-1 hover:bg-surface-container-low transition-colors"
                                title="Từ chối / Yêu cầu sửa"
                              >
                                <span className="material-symbols-outlined text-base">close</span>
                                Trả về
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                <div className="flex justify-between items-center mt-5 pt-4 border-t border-surface-container-highest">
                  <span className="text-[13px] text-outline">
                    Hiển thị {items.length === 0 ? 0 : pageStart}-{pageEnd} trong {totalElements} kết quả
                  </span>
                  <div className="flex gap-1">
                    <button
                      type="button"
                      disabled={page === 0 || loading}
                      onClick={() => setPage((p) => Math.max(0, p - 1))}
                      className={`w-9 h-9 rounded-full border border-outline-variant bg-surface flex items-center justify-center ${
                        page === 0 || loading ? 'opacity-40 cursor-default' : 'cursor-pointer hover:bg-surface-container-low'
                      }`}
                    >
                      <span className="material-symbols-outlined text-primary text-lg">chevron_left</span>
                    </button>
                    {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                      const startPage = Math.max(0, Math.min(page - 2, totalPages - 5));
                      const p = startPage + i;
                      if (p >= totalPages) return null;
                      return (
                        <button
                          key={p}
                          type="button"
                          onClick={() => setPage(p)}
                          className={`w-9 h-9 rounded-full text-sm font-semibold cursor-pointer flex items-center justify-center ${
                            page === p
                              ? 'border-0 bg-primary text-on-primary'
                              : 'border border-outline-variant bg-surface text-on-surface-variant hover:bg-surface-container-low'
                          }`}
                        >
                          {p + 1}
                        </button>
                      );
                    })}
                    <button
                      type="button"
                      disabled={page >= totalPages - 1 || loading}
                      onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                      className={`w-9 h-9 rounded-full border border-outline-variant bg-surface flex items-center justify-center ${
                        page >= totalPages - 1 || loading ? 'opacity-40 cursor-default' : 'cursor-pointer hover:bg-surface-container-low'
                      }`}
                    >
                      <span className="material-symbols-outlined text-primary text-lg">chevron_right</span>
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </main>

      {/* Single Item Decision Dialog */}
      {pendingDecision && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-lg rounded-2xl border border-surface-container-highest bg-surface p-6 shadow-xl">
            <div className="flex items-center justify-between border-b border-surface-container-highest pb-3 mb-4">
              <h3 className="text-base font-bold text-on-surface flex items-center gap-2">
                <span
                  className={`material-symbols-outlined ${
                    pendingDecision.decision === 'APPROVE' ? 'text-emerald-600' : 'text-rose-600'
                  }`}
                >
                  {pendingDecision.decision === 'APPROVE' ? 'verified' : 'assignment_late'}
                </span>
                {pendingDecision.decision === 'APPROVE' ? 'Xác nhận phê duyệt nội dung' : 'Yêu cầu chỉnh sửa / Trả về'}
              </h3>
              <button
                type="button"
                onClick={handleCloseDecision}
                disabled={submitting}
                className="text-outline hover:text-on-surface cursor-pointer"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="space-y-4 text-xs text-on-surface">
              <div className="rounded-xl bg-surface-container-low p-3.5 border border-surface-container-highest">
                <p className="font-semibold text-sm text-on-surface">{pendingDecision.item.title}</p>
                <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-outline">
                  <span>Loại: {TYPE_LABELS[pendingDecision.item.type]}</span>
                  <span>· Giai đoạn: {pendingDecision.item.stage ? STAGE_LABELS[pendingDecision.item.stage] : 'Chung'}</span>
                  <span>· Phiên bản: v{pendingDecision.item.versionNo ?? 1}</span>
                </div>
              </div>

              {pendingDecision.decision === 'APPROVE' ? (
                <p className="text-on-surface-variant text-xs leading-relaxed">
                  Khi bạn phê duyệt, nội dung này sẽ chính thức được kích hoạt và xuất bản trên Thư viện chăm sóc cho các bà mẹ và gia đình. Bạn có chắc chắn muốn xuất bản không?
                </p>
              ) : (
                <div>
                  <label className="block font-semibold text-on-surface-variant mb-1">
                    Lý do từ chối & Hướng dẫn chỉnh sửa cho tác giả <span className="text-rose-500">*</span>
                  </label>
                  <textarea
                    rows={4}
                    value={rejectReason}
                    onChange={(e) => {
                      setRejectReason(e.target.value);
                      if (rejectReasonError) setRejectReasonError(null);
                    }}
                    placeholder="Ghi rõ các điểm chưa chính xác về chuyên môn y khoa hoặc cần bổ sung tài liệu..."
                    className="w-full rounded-xl border border-outline-variant bg-surface p-2.5 text-xs text-on-surface focus:border-primary focus:outline-none"
                  />
                  {rejectReasonError && (
                    <p className="mt-1 text-xs text-rose-500">{rejectReasonError}</p>
                  )}
                </div>
              )}
            </div>

            <div className="mt-6 flex items-center justify-end gap-3 border-t border-surface-container-highest pt-4">
              <button
                type="button"
                onClick={handleCloseDecision}
                disabled={submitting}
                className="rounded-full border border-outline-variant bg-surface px-5 py-2 text-xs font-semibold text-on-surface hover:bg-surface-container-low disabled:opacity-50 cursor-pointer"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={handleSubmitDecision}
                disabled={submitting}
                className={`inline-flex items-center gap-1.5 rounded-full px-5 py-2 text-xs font-semibold text-white transition-colors disabled:opacity-50 cursor-pointer shadow-sm ${
                  pendingDecision.decision === 'APPROVE'
                    ? 'bg-emerald-600 hover:bg-emerald-700'
                    : 'bg-rose-600 hover:bg-rose-700'
                }`}
              >
                {submitting ? (
                  <>
                    <span className="material-symbols-outlined animate-spin text-[16px]">progress_activity</span>
                    Đang xử lý...
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[16px]">
                      {pendingDecision.decision === 'APPROVE' ? 'check' : 'send'}
                    </span>
                    {pendingDecision.decision === 'APPROVE' ? 'Xác nhận xuất bản' : 'Gửi yêu cầu sửa'}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Batch Approval Confirmation Modal */}
      {batchTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-2xl rounded-2xl border border-surface-container-highest bg-surface p-6 shadow-xl">
            <div className="flex items-center justify-between border-b border-surface-container-highest pb-3 mb-4">
              <h3 className="text-base font-bold text-on-surface flex items-center gap-2">
                <span className="material-symbols-outlined text-emerald-600">done_all</span>
                {batchTarget === 'ALL'
                  ? 'Phê duyệt tất cả nội dung đang chờ'
                  : batchTarget === 'ARTICLE'
                  ? 'Phê duyệt tất cả bài viết y tế'
                  : batchTarget === 'FAQ'
                  ? 'Phê duyệt tất cả câu hỏi FAQ'
                  : 'Phê duyệt tất cả mẫu checklist'}
              </h3>
              <button
                type="button"
                onClick={() => !isBatchApproving && setBatchTarget(null)}
                disabled={isBatchApproving}
                className="text-outline hover:text-on-surface cursor-pointer"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            {batchError && (
              <div className="mb-4 rounded-xl bg-rose-500/10 border border-rose-500/30 p-3 text-xs text-rose-600 dark:text-rose-400 flex items-center gap-2">
                <span className="material-symbols-outlined text-[18px]">error</span>
                <span>{batchError}</span>
              </div>
            )}

            <p className="text-xs text-on-surface-variant leading-relaxed mb-4">
              Các nội dung được chọn bên dưới sẽ được phê duyệt và chính thức xuất bản trên hệ thống. Bạn có thể chọn lọc từng mục hoặc phê duyệt toàn bộ.
            </p>

            {/* List Selection Header */}
            <div className="mb-2 flex items-center justify-between text-xs text-outline">
              <button
                type="button"
                onClick={toggleSelectAllBatch}
                disabled={batchModalLoading || batchModalItems.length === 0}
                className="inline-flex items-center gap-1.5 font-semibold text-primary hover:underline cursor-pointer border-0 bg-transparent p-0 disabled:opacity-50"
              >
                <span className="material-symbols-outlined text-[18px]">
                  {batchModalItems.length > 0 && selectedBatchItemIds.size === batchModalItems.length
                    ? 'check_box'
                    : 'check_box_outline_blank'}
                </span>
                {batchModalItems.length > 0 && selectedBatchItemIds.size === batchModalItems.length
                  ? 'Bỏ chọn tất cả'
                  : 'Chọn tất cả'}
              </button>
              <span>
                Đã chọn <strong className="text-on-surface">{selectedBatchItemIds.size}</strong> / {batchModalItems.length} mục
              </span>
            </div>

            {/* Items List */}
            {batchModalLoading ? (
              <div className="py-12 flex flex-col items-center justify-center gap-3 text-outline">
                <span className="material-symbols-outlined animate-spin text-3xl text-primary">progress_activity</span>
                <span className="text-xs">Đang tải danh sách nội dung ({tabCounts[batchTarget]} mục)...</span>
              </div>
            ) : batchModalItems.length === 0 ? (
              <div className="py-8 text-center text-xs text-outline">
                Không có nội dung nào phù hợp để phê duyệt.
              </div>
            ) : (
              <div className="max-h-72 overflow-y-auto rounded-xl border border-surface-container-highest divide-y divide-surface-container-highest bg-surface-container-low/40 p-1">
                {batchModalItems.map((item) => {
                  const itemKey = `${item.kind}-${item.id}`;
                  const isSelected = selectedBatchItemIds.has(itemKey);
                  return (
                    <div
                      key={itemKey}
                      onClick={() => toggleSelectBatchItem(itemKey)}
                      className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-surface-container transition-colors cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => {}} // Handled by div click
                        className="h-4 w-4 rounded border-outline-variant text-primary focus:ring-primary cursor-pointer"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-semibold text-on-surface truncate">{item.title}</div>
                        <div className="flex items-center gap-2 text-[10px] text-outline mt-0.5">
                          <span>{TYPE_LABELS[item.type]}</span>
                          <span>· {item.stage ? STAGE_LABELS[item.stage] : 'Chung'}</span>
                          <span>· v{item.versionNo ?? 1}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Modal Actions */}
            <div className="mt-6 flex items-center justify-end gap-3 border-t border-surface-container-highest pt-4">
              <button
                type="button"
                onClick={() => setBatchTarget(null)}
                disabled={isBatchApproving}
                className="rounded-full border border-outline-variant bg-surface px-5 py-2 text-xs font-semibold text-on-surface hover:bg-surface-container-low disabled:opacity-50 cursor-pointer"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={confirmBatchApproval}
                disabled={isBatchApproving || batchModalLoading || selectedBatchItemIds.size === 0}
                className="inline-flex items-center gap-1.5 rounded-full bg-emerald-600 px-5 py-2 text-xs font-semibold text-white shadow-sm hover:bg-emerald-700 disabled:opacity-50 cursor-pointer transition-colors"
              >
                {isBatchApproving ? (
                  <>
                    <span className="material-symbols-outlined animate-spin text-[16px]">progress_activity</span>
                    Đang phê duyệt {selectedBatchItemIds.size} mục...
                  </>
                ) : (
                  <>
                    <span className="material-symbols-outlined text-[16px]">check</span>
                    Xác nhận phê duyệt ({selectedBatchItemIds.size} mục)
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
