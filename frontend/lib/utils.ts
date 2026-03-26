import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return `${diffSecs}s ago`;
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

export function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

export function severityColor(severity: string): string {
  switch (severity.toUpperCase()) {
    case "P1":
      return "bg-red-500/20 text-red-400 border-red-500/30";
    case "P2":
      return "bg-orange-500/20 text-orange-400 border-orange-500/30";
    case "P3":
      return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
    case "P4":
      return "bg-blue-500/20 text-blue-400 border-blue-500/30";
    default:
      return "bg-gray-500/20 text-gray-400 border-gray-500/30";
  }
}

export function severityDot(severity: string): string {
  switch (severity.toUpperCase()) {
    case "P1":
      return "bg-red-500";
    case "P2":
      return "bg-orange-500";
    case "P3":
      return "bg-yellow-500";
    case "P4":
      return "bg-blue-500";
    default:
      return "bg-gray-500";
  }
}
