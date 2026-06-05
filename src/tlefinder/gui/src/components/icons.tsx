import type { ReactNode, SVGProps } from "react";

/** Inline SVG icons (kept simple — geometric shapes only). */

type IconProps = { size?: number };

const stroke: SVGProps<SVGSVGElement> = {
  fill: "none",
  stroke: "currentColor",
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

export const I = {
  Plus: ({ size = 14 }: IconProps) => (
    <svg viewBox="0 0 16 16" width={size} height={size} {...stroke} strokeWidth={1.6}>
      <path d="M8 3v10M3 8h10" />
    </svg>
  ),
  Search: ({ size = 14 }: IconProps) => (
    <svg viewBox="0 0 16 16" width={size} height={size} {...stroke} strokeWidth={1.6}>
      <circle cx="7" cy="7" r="4.2" />
      <path d="M10.2 10.2L13.5 13.5" />
    </svg>
  ),
  Pencil: ({ size = 13 }: IconProps) => (
    <svg viewBox="0 0 16 16" width={size} height={size} {...stroke} strokeWidth={1.5}>
      <path d="M2.5 13.5L3 11l7-7 2.5 2.5-7 7-2.5.5z" />
      <path d="M10 4l2.5 2.5" />
    </svg>
  ),
  Trash: ({ size = 13 }: IconProps) => (
    <svg viewBox="0 0 16 16" width={size} height={size} {...stroke} strokeWidth={1.5}>
      <path d="M3 4.5h10M6 4.5V3.5a1 1 0 011-1h2a1 1 0 011 1v1M4.5 4.5L5 13a1 1 0 001 1h4a1 1 0 001-1l.5-8.5" />
    </svg>
  ),
  Close: ({ size = 14 }: IconProps) => (
    <svg viewBox="0 0 16 16" width={size} height={size} {...stroke} strokeWidth={1.6}>
      <path d="M4 4l8 8M12 4l-8 8" />
    </svg>
  ),
  Chevron: ({ size = 12 }: IconProps) => (
    <svg viewBox="0 0 16 16" width={size} height={size} {...stroke} strokeWidth={1.6}>
      <path d="M4 6l4 4 4-4" />
    </svg>
  ),
  Pin: ({ size = 14 }: IconProps) => (
    <svg viewBox="0 0 16 16" width={size} height={size} {...stroke} strokeWidth={1.5}>
      <circle cx="8" cy="6.5" r="2.5" />
      <path d="M8 9.5V14" />
      <path d="M3.5 6.5C3.5 4 5.5 1.5 8 1.5s4.5 2.5 4.5 5c0 3-4.5 7.5-4.5 7.5S3.5 9.5 3.5 6.5z" />
    </svg>
  ),
  Clock: ({ size = 14 }: IconProps) => (
    <svg viewBox="0 0 16 16" width={size} height={size} {...stroke} strokeWidth={1.5}>
      <circle cx="8" cy="8" r="6" />
      <path d="M8 4.5V8l2.5 1.5" />
    </svg>
  ),
  Sliders: ({ size = 14 }: IconProps) => (
    <svg viewBox="0 0 16 16" width={size} height={size} {...stroke} strokeWidth={1.5}>
      <path d="M3 5h10M3 11h10" />
      <circle cx="6" cy="5" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="10" cy="11" r="1.6" fill="currentColor" stroke="none" />
    </svg>
  ),
  Copy: ({ size = 12 }: IconProps) => (
    <svg viewBox="0 0 16 16" width={size} height={size} {...stroke} strokeWidth={1.4}>
      <rect x="5" y="5" width="8" height="8" rx="1.5" />
      <path d="M3 11V4.5A1.5 1.5 0 014.5 3H11" />
    </svg>
  ),
  Check: ({ size = 14 }: IconProps) => (
    <svg viewBox="0 0 16 16" width={size} height={size} {...stroke} strokeWidth={1.8}>
      <path d="M3 8.5L6.5 12 13 5" />
    </svg>
  ),
  Empty: () => (
    <svg viewBox="0 0 24 24" width={22} height={22} {...stroke} strokeWidth={1.5}>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12h8" />
    </svg>
  ),
  Sat: () => (
    <svg viewBox="0 0 24 24" width={22} height={22} {...stroke} strokeWidth={1.5}>
      <circle cx="12" cy="12" r="3" />
      <path d="M5 5l4 4M19 19l-4-4M15 9l4-4M9 15l-4 4" />
    </svg>
  ),
  Warn: () => (
    <svg viewBox="0 0 24 24" width={22} height={22} {...stroke} strokeWidth={1.5}>
      <path d="M12 4l9 16H3z" />
      <path d="M12 10v5M12 17.5v.5" />
    </svg>
  ),
} satisfies Record<string, (props: IconProps) => ReactNode>;
