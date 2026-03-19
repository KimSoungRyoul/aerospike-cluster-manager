import { Badge } from "@/components/ui/badge";
import { BIN_TYPE_COLORS, type BinType } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface BinTypeBadgeProps {
  type: BinType;
  className?: string;
}

export function BinTypeBadge({ type, className }: BinTypeBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn("px-1.5 py-0 font-mono text-[10px]", BIN_TYPE_COLORS[type], className)}
    >
      {type}
    </Badge>
  );
}
