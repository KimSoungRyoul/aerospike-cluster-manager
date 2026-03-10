"use client";

import { useState, useEffect, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { FilterCondition, FilterOperator, BinValue } from "@/lib/api/types";
import {
  FILTER_OPERATORS_BY_TYPE,
  NO_VALUE_OPERATORS,
  DUAL_VALUE_OPERATORS,
} from "@/lib/constants";

interface FilterConditionEditorProps {
  condition: FilterCondition;
  onChange: (updates: Partial<Omit<FilterCondition, "id">>) => void;
  onApply: () => void;
  onCancel: () => void;
}

function parseInputValue(raw: string, binType: string): BinValue {
  if (binType === "integer") {
    const n = parseInt(raw, 10);
    return isNaN(n) ? raw : n;
  }
  if (binType === "float") {
    const n = parseFloat(raw);
    return isNaN(n) ? raw : n;
  }
  return raw;
}

export function FilterConditionEditor({
  condition,
  onChange,
  onApply,
  onCancel,
}: FilterConditionEditorProps) {
  const operators = FILTER_OPERATORS_BY_TYPE[condition.binType] ?? [];
  const needsValue = !NO_VALUE_OPERATORS.includes(condition.operator);
  const needsValue2 = DUAL_VALUE_OPERATORS.includes(condition.operator);
  const isGeo = condition.operator === "geo_within" || condition.operator === "geo_contains";

  const [val, setVal] = useState(condition.value !== undefined ? String(condition.value) : "");
  const [val2, setVal2] = useState(condition.value2 !== undefined ? String(condition.value2) : "");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (needsValue) {
      inputRef.current?.focus();
    }
  }, [needsValue]);

  const handleApply = () => {
    const updates: Partial<Omit<FilterCondition, "id">> = {};
    if (needsValue) {
      updates.value = isGeo ? val : parseInputValue(val, condition.binType);
    }
    if (needsValue2) {
      updates.value2 = parseInputValue(val2, condition.binType);
    }
    onChange(updates);
    onApply();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleApply();
    }
    if (e.key === "Escape") {
      e.preventDefault();
      onCancel();
    }
  };

  const currentOpLabel = operators.find((o) => o.value === condition.operator)?.label ?? "=";

  return (
    <div className="w-[260px] space-y-2.5 p-3">
      {/* Bin name header */}
      <div className="text-base-content/70 font-mono text-xs font-medium">{condition.bin}</div>

      {/* Operator selector */}
      <Select
        value={condition.operator}
        onChange={(e) => onChange({ operator: e.target.value as FilterOperator })}
        className="h-8 text-xs"
      >
        {operators.map((op) => (
          <option key={op.value} value={op.value}>
            {op.label}
          </option>
        ))}
      </Select>

      {/* Value input(s) */}
      {needsValue && !isGeo && (
        <Input
          ref={inputRef}
          type={
            condition.binType === "integer" || condition.binType === "float" ? "number" : "text"
          }
          placeholder={condition.operator === "regex" ? "Pattern..." : "Value..."}
          value={val}
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={handleKeyDown}
          className={`h-8 text-xs ${condition.operator === "regex" ? "font-mono" : ""}`}
        />
      )}

      {needsValue2 && (
        <Input
          type={
            condition.binType === "integer" || condition.binType === "float" ? "number" : "text"
          }
          placeholder="Upper bound..."
          value={val2}
          onChange={(e) => setVal2(e.target.value)}
          onKeyDown={handleKeyDown}
          className="h-8 text-xs"
        />
      )}

      {isGeo && (
        <Textarea
          placeholder='{"type":"AeroCircle","coordinates":[[lng,lat],radius]}'
          value={val}
          onChange={(e) => setVal(e.target.value)}
          className="min-h-[80px] font-mono text-xs"
        />
      )}

      {/* Apply / Cancel */}
      <div className="flex items-center justify-end gap-2 pt-1">
        <Button variant="ghost" size="sm" onClick={onCancel} className="h-7 text-xs">
          Cancel
        </Button>
        <Button size="sm" onClick={handleApply} className="h-7 text-xs">
          Apply
        </Button>
      </div>
    </div>
  );
}
