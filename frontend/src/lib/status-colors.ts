export const STATUS_COLORS = {
  success: "bg-success/10 text-success border-success/20",
  warning: "bg-warning/10 text-warning border-warning/20",
  error: "bg-error/10 text-error border-error/20",
  info: "bg-info/10 text-info border-info/20",
  neutral: "bg-base-200 text-muted-foreground border-base-300",
} as const;

export type StatusColorKey = keyof typeof STATUS_COLORS;
