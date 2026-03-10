import { formatNumber } from "@/lib/formatters";

interface ChartTooltipContentProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
  valueFormatter?: (value: number) => string;
}

export function ChartTooltipContent({
  active,
  payload,
  label,
  valueFormatter = formatNumber,
}: ChartTooltipContentProps) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="bg-base-100 rounded-md border px-3 py-2 shadow-md">
      <p className="text-muted-foreground mb-1 text-xs font-medium">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2 text-sm">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-mono font-medium">{valueFormatter(entry.value)}</span>
        </div>
      ))}
    </div>
  );
}
