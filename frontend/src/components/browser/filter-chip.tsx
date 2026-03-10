"use client";

import { X } from "lucide-react";
import type { FilterCondition } from "@/lib/api/types";
import { FILTER_OPERATORS_BY_TYPE, NO_VALUE_OPERATORS } from "@/lib/constants";
import { cn } from "@/lib/utils";

function formatValue(condition: FilterCondition): string {
  const { operator, value, value2 } = condition;
  if (NO_VALUE_OPERATORS.includes(operator)) return "";
  if (operator === "between" && value !== undefined && value2 !== undefined) {
    return `${value} ~ ${value2}`;
  }
  if (value === undefined || value === null) return "";
  if (typeof value === "string") return value.length > 20 ? `${value.slice(0, 20)}...` : value;
  return String(value);
}

function getOperatorLabel(condition: FilterCondition): string {
  const ops = FILTER_OPERATORS_BY_TYPE[condition.binType];
  return ops?.find((o) => o.value === condition.operator)?.label ?? condition.operator;
}

interface FilterChipProps {
  condition: FilterCondition;
  onEdit: (id: string) => void;
  onRemove: (id: string) => void;
}

export function FilterChip({ condition, onEdit, onRemove }: FilterChipProps) {
  const opLabel = getOperatorLabel(condition);
  const val = formatValue(condition);

  return (
    <span
      className={cn(
        "border-base-300/60 bg-base-200/40 hover:border-base-300 inline-flex max-w-[280px] items-center gap-1 rounded-md border border-dashed px-2 py-1 text-xs transition-colors",
        "hover:bg-base-200/70 cursor-pointer",
      )}
      role="button"
      tabIndex={0}
      onClick={() => onEdit(condition.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onEdit(condition.id);
        }
      }}
    >
      <span className="text-base-content/70 font-mono font-medium">{condition.bin}</span>
      <span className="text-muted-foreground">{opLabel}</span>
      {val && <span className="text-base-content max-w-[120px] truncate font-medium">{val}</span>}
      <button
        type="button"
        className="text-muted-foreground hover:text-base-content -mr-0.5 ml-0.5 rounded-sm p-0.5 transition-colors"
        onClick={(e) => {
          e.stopPropagation();
          onRemove(condition.id);
        }}
        aria-label={`Remove ${condition.bin} filter`}
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}
