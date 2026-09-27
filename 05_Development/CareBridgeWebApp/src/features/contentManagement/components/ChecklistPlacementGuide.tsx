import type { AdminChecklistTemplateDetail } from '../models/content';
import {
  evaluatePosition,
  nextFreePosition,
  positionOptionLabel,
  positionOptions,
  type SequenceOverview,
} from '../pages/checklistSequencePositions';

export type StageChecklistsState =
  | { status: 'idle' | 'loading' | 'error' }
  | { status: 'ready'; templates: AdminChecklistTemplateDetail[] };

const FIELD = 'w-full py-2.5 px-4 rounded-2xl border border-outline-variant bg-surface text-sm text-on-surface outline-none font-sans focus:border-primary focus:ring-2 focus:ring-primary/20 disabled:bg-surface-container-low disabled:text-outline';
const HINT = 'text-xs font-normal text-on-surface-variant';

interface SequencePositionFieldProps {
  value: number;
  onChange: (value: number) => void;
  disabled: boolean;
  lineageId: string | null;
  stageChecklists: StageChecklistsState;
  overview: SequenceOverview | null;
  onOpenChecklist: (id: string) => void;
}

export function SequencePositionField({
  value,
  onChange,
  disabled,
  lineageId,
  stageChecklists,
  overview,
  onOpenChecklist,
}: SequencePositionFieldProps) {
  if (stageChecklists.status !== 'ready' || !overview) {
    return (
      <label className="mt-4 grid gap-2 text-sm font-semibold text-on-surface">
        Vị trí bộ checklist
        <input
          aria-label="Checklist sequence position"
          type="number"
          min={1}
          max={1000}
          step={1}
          disabled={disabled}
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
          className={FIELD}
        />
        <span className={HINT}>
          {stageChecklists.status === 'loading'
            ? 'Đang tải các vị trí đã dùng trong chuỗi...'
            : stageChecklists.status === 'error'
              ? 'Không tải được danh sách vị trí đã dùng. Nhập 1, 2, 3... theo thứ tự; vị trí sẽ được kiểm tra lại khi phê duyệt.'
              : 'Nhập 1, 2, 3... theo thứ tự các bộ. Vị trí được kiểm tra lại khi phê duyệt.'}
        </span>
      </label>
    );
  }

  const status = evaluatePosition(value, overview, lineageId);
  const pendingHere = overview.pending.get(value) ?? [];
  const chain = [...overview.active.entries()].sort(([left], [right]) => left - right);
  const nextFree = nextFreePosition(overview, lineageId);

  return (
    <div className="mt-4 grid gap-3">
      <label className="grid gap-2 text-sm font-semibold text-on-surface">
        Vị trí bộ checklist
        <select
          aria-label="Checklist sequence position"
          disabled={disabled}
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
          className={FIELD}
        >
          {positionOptions(overview, lineageId, value).map((position) => {
            const kind = evaluatePosition(position, overview, lineageId).kind;
            return (
              <option key={position} value={position} disabled={kind === 'occupied' || kind === 'gap'}>
                {positionOptionLabel(position, overview, lineageId)}
              </option>
            );
          })}
        </select>
        <span className={HINT}>
          Các bộ phải liên tục từ 1 và mỗi vị trí chỉ có một checklist đang hoạt động. Muốn thay nội dung một bộ đã có,
          hãy tạo phiên bản mới từ chính checklist đó thay vì tạo checklist mới.
        </span>
      </label>

      {status.kind === 'occupied' && (
        <div role="alert" className="rounded-xl border border-error-container bg-error-container/60 p-3 text-xs text-error">
          Bộ {value} đang được dùng bởi “{status.holder.name}” (v{status.holder.versionNo}). Hãy chọn bộ {nextFree} (bộ tiếp
          theo còn trống), hoặc{' '}
          <button type="button" onClick={() => onOpenChecklist(status.holder.id)} className="font-semibold underline cursor-pointer">
            mở checklist đó
          </button>{' '}
          để tạo phiên bản mới nếu muốn thay thế.
        </div>
      )}
      {status.kind === 'gap' && (
        <div role="alert" className="rounded-xl border border-error-container bg-error-container/60 p-3 text-xs text-error">
          Chuỗi phải liên tục từ bộ 1. Hiện chưa có bộ {status.nextFree}, nên hãy chọn bộ {status.nextFree}.
        </div>
      )}
      {status.kind === 'replace-own' && (
        <div role="status" className="rounded-xl border border-surface-container-highest bg-surface-container-low p-3 text-xs text-on-surface-variant">
          Khi được duyệt, phiên bản này sẽ thay thế v{status.holder.versionNo} đang hoạt động ở bộ {value}.
        </div>
      )}
      {pendingHere.length > 0 && (
        <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          Bộ {value} cũng đang được chọn bởi checklist chờ duyệt: {pendingHere.map((holder) => `“${holder.name}”`).join(', ')}.
          Chỉ checklist được duyệt trước giữ vị trí này; checklist còn lại sẽ phải đổi vị trí.
        </div>
      )}
      {overview.activeLegacy.length > 0 && (
        <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          Đang có checklist Chuẩn bị mang thai ngoài chuỗi (vị trí 0) hoạt động:{' '}
          {overview.activeLegacy.map((holder) => `“${holder.name}”`).join(', ')}. Cần lưu trữ hoặc tắt các checklist này
          trước khi duyệt bộ trong chuỗi.
        </div>
      )}

      <div className="rounded-xl border border-surface-container-highest bg-surface-bright p-3">
        <p className="mb-2 text-xs font-semibold text-on-surface">Chuỗi Chuẩn bị mang thai hiện tại</p>
        {chain.length === 0 ? (
          <p className={HINT}>Chưa có bộ nào đang hoạt động. Checklist này sẽ là bộ 1.</p>
        ) : (
          <ol aria-label="Current sequence positions" className="m-0 grid list-none gap-1.5 p-0">
            {chain.map(([position, holder]) => (
              <li key={position} className="flex flex-wrap items-center gap-2 text-xs text-on-surface-variant">
                <span className="inline-flex min-w-14 justify-center rounded-full bg-surface-container-low px-2 py-0.5 font-semibold text-primary">
                  Bộ {position}
                </span>
                <span className="text-on-surface">{holder.name}</span>
                <span>· v{holder.versionNo}</span>
                {lineageId && holder.lineageId === lineageId && <span className="font-semibold">· checklist này</span>}
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
