"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import {
  Hash,
  Type,
  ToggleLeft,
  MapPin,
  List,
  Braces,
  Binary,
  Search,
  DatabaseZap,
} from "lucide-react";
import type { BinDataType } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const TYPE_ICONS: Record<BinDataType, React.ElementType> = {
  integer: Hash,
  float: Hash,
  string: Type,
  bool: ToggleLeft,
  geo: MapPin,
  list: List,
  map: Braces,
};

const TYPE_COLORS: Record<BinDataType, string> = {
  integer: "text-blue-500",
  float: "text-cyan-500",
  string: "text-emerald-500",
  bool: "text-amber-500",
  geo: "text-rose-500",
  list: "text-violet-500",
  map: "text-orange-500",
};

interface FilterColumnPickerProps {
  bins: Array<{ name: string; type: BinDataType }>;
  onSelect: (binName: string, binType: BinDataType) => void;
  onClose: () => void;
}

export function FilterColumnPicker({ bins, onSelect, onClose }: FilterColumnPickerProps) {
  const [search, setSearch] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const filtered = useMemo(() => {
    if (!search.trim()) return bins;
    const q = search.toLowerCase();
    return bins.filter((b) => b.name.toLowerCase().includes(q));
  }, [bins, search]);

  return (
    <div className="w-[220px]">
      {/* Search */}
      <div className="border-base-300/40 flex items-center gap-2 border-b px-3 py-2">
        <Search className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
        <input
          ref={inputRef}
          type="text"
          placeholder="Filter by..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="placeholder:text-muted-foreground/60 w-full bg-transparent text-xs outline-none"
        />
      </div>

      {/* Indexed bin label */}
      <div className="border-base-300/40 flex items-center gap-1.5 border-b px-3 py-1.5">
        <DatabaseZap className="h-3 w-3 text-amber-500" />
        <span className="text-muted-foreground text-[10px]">Secondary Index required</span>
      </div>

      {/* Bin list */}
      <div className="max-h-[240px] overflow-auto py-1">
        {bins.length === 0 ? (
          <div className="text-muted-foreground space-y-1 px-3 py-4 text-center text-xs">
            <p>No indexed bins found</p>
            <p className="text-muted-foreground/50 text-[10px]">
              Create a secondary index on the Indexes tab to enable filtering
            </p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-muted-foreground px-3 py-4 text-center text-xs">
            No matching bins
          </div>
        ) : (
          filtered.map((bin) => {
            const Icon = TYPE_ICONS[bin.type] ?? Binary;
            const color = TYPE_COLORS[bin.type] ?? "text-muted-foreground";
            return (
              <button
                key={bin.name}
                type="button"
                className={cn(
                  "hover:bg-base-200/60 flex w-full items-center gap-2.5 px-3 py-1.5 text-left text-xs transition-colors",
                )}
                onClick={() => {
                  onSelect(bin.name, bin.type);
                  onClose();
                }}
              >
                <Icon className={cn("h-3.5 w-3.5 shrink-0", color)} />
                <span className="truncate font-mono">{bin.name}</span>
                <span className="text-muted-foreground/50 ml-auto text-[10px]">{bin.type}</span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
