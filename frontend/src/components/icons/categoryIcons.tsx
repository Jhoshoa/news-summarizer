import type { ReactElement } from "react";

import {
  IconCoins,
  IconCloudRain,
  IconCpu,
  IconGlobe,
  IconGrid,
  IconHeartPulse,
  IconLandmark,
  IconShieldAlert,
  IconTicket,
  IconTrophy,
  IconUsers,
} from "./Icons";

type IconProps = { size?: number };

const CATEGORY_ICON: Record<string, (props: IconProps) => ReactElement> = {
  economia: IconCoins,
  politica: IconLandmark,
  deportes: IconTrophy,
  tecnologia: IconCpu,
  entretenimiento: IconTicket,
  policiales: IconShieldAlert,
  clima: IconCloudRain,
  mundo: IconGlobe,
  salud: IconHeartPulse,
  sociedad: IconUsers,
  general: IconGrid,
};

export const CategoryIcon = ({ category, size = 16 }: { category?: string | null; size?: number }) => {
  const Icon = (category && CATEGORY_ICON[category]) || IconGrid;
  return <Icon size={size} />;
};
