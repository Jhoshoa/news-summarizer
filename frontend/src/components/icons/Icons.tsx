import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

const base = (size: number): SVGProps<SVGSVGElement> => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
});

export const IconHome = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M3 11.5 12 4l9 7.5" />
    <path d="M5.5 10v9a1 1 0 0 0 1 1H9v-6h6v6h2.5a1 1 0 0 0 1-1v-9" />
  </svg>
);

export const IconNews = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <rect x="3.5" y="4.5" width="17" height="15" rx="1.5" />
    <path d="M7 8.5h6M7 11.5h10M7 14.5h10M7 17h6" />
  </svg>
);

export const IconChart = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M4 20V9M10 20V4M16 20v6M22 20H2" />
  </svg>
);

export const IconTarget = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <circle cx="12" cy="12" r="8.2" />
    <circle cx="12" cy="12" r="4.4" />
    <circle cx="12" cy="12" r="0.6" fill="currentColor" />
  </svg>
);

export const IconRss = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M5 4.5a14.5 14.5 0 0 1 14.5 14.5" />
    <path d="M5 10a9 9 0 0 1 9 9" />
    <circle cx="6.3" cy="17.7" r="1.6" fill="currentColor" stroke="none" />
  </svg>
);

export const IconBell = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M6 10.5a6 6 0 0 1 12 0c0 4 1.5 5.2 1.5 5.5H4.5c0-.3 1.5-1.5 1.5-5.5Z" />
    <path d="M10 19a2 2 0 0 0 4 0" />
  </svg>
);

export const IconArrowLeft = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M19 12H5M11 6l-6 6 6 6" />
  </svg>
);

export const IconArrowRight = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </svg>
);

export const IconChevronRight = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M9 6l6 6-6 6" />
  </svg>
);

export const IconCheckCircle = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <circle cx="12" cy="12" r="8.3" />
    <path d="M8.3 12.3l2.4 2.4 5-5.4" />
  </svg>
);

export const IconUsers = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <circle cx="9" cy="9" r="3" />
    <path d="M3.5 19c0-3 2.5-5 5.5-5s5.5 2 5.5 5" />
    <circle cx="17" cy="9.5" r="2.4" />
    <path d="M15.5 14.3c2.4.3 4 2 4 4.7" />
  </svg>
);

export const IconShield = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M12 3.5 19 6v6c0 5-3 8-7 9-4-1-7-4-7-9V6l7-2.5Z" />
    <path d="M9 12l2 2 4-4.5" />
  </svg>
);

export const IconClock = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <circle cx="12" cy="12" r="8.3" />
    <path d="M12 7.5V12l3 2" />
  </svg>
);

export const IconMenu = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M4 6h16M4 12h16M4 18h16" />
  </svg>
);

export const IconX = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M6 6l12 12M18 6L6 18" />
  </svg>
);

export const IconExternal = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M9 6H5.5A1.5 1.5 0 0 0 4 7.5v11A1.5 1.5 0 0 0 5.5 20h11a1.5 1.5 0 0 0 1.5-1.5V15" />
    <path d="M14 4h6v6M20 4l-9.5 9.5" />
  </svg>
);
