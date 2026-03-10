"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

function extractText(node: React.ReactNode): string {
  if (typeof node === "string") return node;
  if (typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(extractText).join("");
  if (React.isValidElement(node)) {
    const props = node.props as Record<string, unknown>;
    if (props.children) return extractText(props.children as React.ReactNode);
  }
  return "";
}

interface TooltipTriggerProps {
  children: React.ReactNode;
  asChild?: boolean;
}

const TooltipTrigger: React.FC<TooltipTriggerProps> = ({ children }) => <>{children}</>;
TooltipTrigger.displayName = "TooltipTrigger";

interface TooltipContentProps extends React.HTMLAttributes<HTMLDivElement> {
  side?: "top" | "bottom" | "left" | "right";
  sideOffset?: number;
}

const TooltipContent: React.FC<TooltipContentProps> = () => null;
TooltipContent.displayName = "TooltipContent";

const sideClassMap: Record<string, string> = {
  top: "tooltip-top",
  bottom: "tooltip-bottom",
  left: "tooltip-left",
  right: "tooltip-right",
};

const Tooltip = ({ children }: { children: React.ReactNode }) => {
  let triggerContent: React.ReactNode = null;
  let tipText = "";
  let side = "top";

  React.Children.forEach(children, (child) => {
    if (!React.isValidElement(child)) return;

    if (child.type === TooltipTrigger) {
      const p = child.props as TooltipTriggerProps;
      triggerContent = p.children;
    } else if (child.type === TooltipContent) {
      const p = child.props as TooltipContentProps & { children?: React.ReactNode };
      tipText = extractText(p.children);
      side = p.side || "top";
    }
  });

  return (
    <div className={cn("tooltip", sideClassMap[side] || "tooltip-top")} data-tip={tipText}>
      {triggerContent}
    </div>
  );
};

export { Tooltip, TooltipTrigger, TooltipContent };
