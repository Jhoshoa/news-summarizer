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

export const IconCoins = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <circle cx="9.5" cy="9.5" r="6" />
    <path d="M13.2 8a6 6 0 1 1-4.3 8.9" />
  </svg>
);

export const IconLandmark = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M4 10l8-5.5L20 10" />
    <path d="M5 10v8M9 10v8M15 10v8M19 10v8M3.5 20.5h17" />
  </svg>
);

export const IconTrophy = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M7 4h10v5a5 5 0 0 1-10 0V4z" />
    <path d="M7 5.5H4a3 3 0 0 0 3 4.3M17 5.5h3a3 3 0 0 1-3 4.3" />
    <path d="M12 14v3M9 20.5h6M9.5 17.3h5" />
  </svg>
);

export const IconCpu = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <rect x="6.5" y="6.5" width="11" height="11" rx="1.5" />
    <rect x="9.5" y="9.5" width="5" height="5" rx="1" />
    <path d="M9 3v2.3M15 3v2.3M9 18.7V21M15 18.7V21M3 9h2.3M3 15h2.3M18.7 9H21M18.7 15H21" />
  </svg>
);

export const IconTicket = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M4 9a2 2 0 0 0 0 6M20 9a2 2 0 0 1 0 6" />
    <rect x="4" y="6" width="16" height="12" rx="2" />
    <path d="M12 6.5v11" strokeDasharray="1.5 2.5" />
  </svg>
);

export const IconShieldAlert = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M12 3.3l6.5 2.6v5.2c0 4.6-3 7.7-6.5 8.6-3.5-.9-6.5-4-6.5-8.6V5.9L12 3.3z" />
    <path d="M12 8.5v4M12 15.3h.01" />
  </svg>
);

export const IconCloudRain = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M6.8 15.3a3.8 3.8 0 0 1-.4-7.5 5 5 0 0 1 9.6-1.5 4.2 4.2 0 0 1-.7 9H6.8z" />
    <path d="M8.5 18.5l-1.2 2M12 18.5l-1.2 2M15.5 18.5l-1.2 2" />
  </svg>
);

export const IconGlobe = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <circle cx="12" cy="12" r="8.5" />
    <ellipse cx="12" cy="12" rx="3.6" ry="8.5" />
    <path d="M3.5 12h17" />
  </svg>
);

export const IconHeartPulse = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M12 20s-7-4.4-9-9.3C1.6 6.8 4 4 7.2 4c1.9 0 3.4 1 4.8 2.7C13.4 5 14.9 4 16.8 4 20 4 22.4 6.8 21 10.7 19 15.6 12 20 12 20z" />
    <path d="M6 11h2.5l1.5-3 2 6 1.5-3H18" />
  </svg>
);

export const IconGrid = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <rect x="4" y="4" width="7" height="7" rx="1.3" />
    <rect x="13" y="4" width="7" height="7" rx="1.3" />
    <rect x="4" y="13" width="7" height="7" rx="1.3" />
    <rect x="13" y="13" width="7" height="7" rx="1.3" />
  </svg>
);

export const IconTrendingUp = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M3.5 16.5l5.5-6 4 4 6.5-8" />
    <path d="M15.5 6.2h4v4" />
  </svg>
);

export const IconCloudSun = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M5 4.5v1.8M2.4 8h1.8M9.6 4.3L8.4 5.7M12 8l-1.4 1.4" />
    <path d="M8.5 19a3.6 3.6 0 0 1-.4-7.2 4.8 4.8 0 0 1 9.2-1.4A4 4 0 0 1 17.7 19H8.5z" />
  </svg>
);

export const IconSparkles = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M12 3l1.4 4.2 4.1 1.3-4.1 1.4L12 14l-1.4-4.1-4.1-1.4 4.1-1.3L12 3z" />
    <path d="M18.5 14l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z" />
  </svg>
);

export const IconSun = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2.5v2.5M12 19v2.5M4.5 12H2M22 12h-2.5M5.5 5.5l1.7 1.7M16.8 16.8l1.7 1.7M18.5 5.5l-1.7 1.7M7.2 16.8l-1.7 1.7" />
  </svg>
);

export const IconDroplet = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M12 3.3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z" />
  </svg>
);

export const IconWind = ({ size = 18, ...props }: IconProps) => (
  <svg {...base(size)} {...props}>
    <path d="M3 8h11.5a2.7 2.7 0 1 0-2.6-3.4" />
    <path d="M3 12.2h15.5a3 3 0 1 1-2.9 3.7" />
    <path d="M3 16.4h8.5" />
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
