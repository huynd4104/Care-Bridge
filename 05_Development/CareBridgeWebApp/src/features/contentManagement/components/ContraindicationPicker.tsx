import { ShieldAlert } from 'lucide-react';
import { CHECKLIST_CONTRAINDICATION_GROUPS, CHECKLIST_CONTRAINDICATION_LABELS } from '../models/content';

interface ContraindicationPickerProps {
  itemLabel: string;
  value: string[];
  disabled?: boolean;
  onChange: (next: string[]) => void;
}

/**
 * Chọn các tag khảo sát (bệnh nền, tiền sử, lối sống...) mà mục checklist chống chỉ định.
 * Không bắt buộc: để trống nghĩa là mục phù hợp với mọi người mẹ.
 */
export default function ContraindicationPicker({ itemLabel, value, disabled, onChange }: ContraindicationPickerProps) {
  const selected = new Set(value);
  const toggle = (tag: string) => {
    const next = new Set(selected);
    if (next.has(tag)) next.delete(tag);
    else next.add(tag);
    onChange([...next].sort());
  };

  return (
    <details className="group rounded-xl border border-surface-container-highest bg-surface-container-low p-3 md:col-span-2">
      <summary className="flex cursor-pointer list-none flex-wrap items-center gap-2 text-sm font-semibold text-on-surface">
        <ShieldAlert size={16} className="text-error" />
        <span>Chống chỉ định <span className="font-normal text-on-surface-variant">(không bắt buộc)</span></span>
        {value.length === 0 ? (
          <span className="text-xs font-normal text-on-surface-variant">Phù hợp với mọi người mẹ</span>
        ) : (
          value.map((tag) => (
            <span key={tag} className="rounded-full bg-error-container/40 px-2.5 py-0.5 text-xs font-semibold text-error">
              {CHECKLIST_CONTRAINDICATION_LABELS[tag] ?? tag}
            </span>
          ))
        )}
      </summary>
      <p className="mt-3 text-xs text-on-surface-variant">
        Người mẹ có khảo sát cá nhân hóa trùng với bất kỳ tag nào dưới đây sẽ không thấy mục này
        (Trang chủ, Lộ trình, Chia sẻ cho chuyên gia). Không gắn cho mục sàng lọc, khám, theo dõi
        chỉ số hoặc dấu hiệu cảnh báo.
      </p>
      <div className="mt-3 grid gap-3">
        {CHECKLIST_CONTRAINDICATION_GROUPS.map((group) => (
          <fieldset key={group.label} className="grid gap-2">
            <legend className="mb-1 text-xs font-bold uppercase tracking-wide text-on-surface-variant">{group.label}</legend>
            <div className="flex flex-wrap gap-2">
              {group.options.map((option) => {
                const active = selected.has(option.value);
                return (
                  <button
                    key={option.value}
                    type="button"
                    aria-pressed={active}
                    aria-label={`Chống chỉ định ${option.label} cho ${itemLabel}`}
                    disabled={disabled}
                    onClick={() => toggle(option.value)}
                    className={`rounded-full border px-3 py-1 text-xs font-semibold transition-colors cursor-pointer disabled:cursor-not-allowed disabled:opacity-50 ${
                      active
                        ? 'border-error bg-error text-on-error'
                        : 'border-outline-variant bg-surface text-on-surface-variant hover:bg-surface-container'
                    }`}
                  >
                    {option.label}
                  </button>
                );
              })}
            </div>
          </fieldset>
        ))}
      </div>
    </details>
  );
}
