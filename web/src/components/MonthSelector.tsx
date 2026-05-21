import { Label } from '@/components/ui/label';
import { Select } from '@/components/ui/select';
import { formatMonthLabel } from '@/lib/format';

interface Props {
  label: string;
  value: string;
  onChange: (v: string) => void;
  months: string[];
  disabled?: boolean;
  id?: string;
}

export function MonthSelector({ label, value, onChange, months, disabled, id }: Props) {
  const inputId = id ?? `month-${label.toLowerCase().replace(/\s+/g, '-')}`;
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={inputId}>{label}</Label>
      <Select
        id={inputId}
        ariaLabel={label}
        value={value}
        onChange={onChange}
        disabled={disabled}
        options={months.map((m) => ({ value: m, label: formatMonthLabel(m) }))}
      />
    </div>
  );
}
