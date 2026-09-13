export type CategoryColor = { bg: string; fg: string };

const CATEGORY_COLOR: Record<string, CategoryColor> = {
  economia: { bg: "var(--brand-soft)", fg: "var(--brand-dark)" },
  politica: { bg: "var(--sky-soft)", fg: "var(--sky)" },
  deportes: { bg: "var(--amber-soft)", fg: "var(--amber-ink)" },
  tecnologia: { bg: "var(--sky-soft)", fg: "var(--sky)" },
  entretenimiento: { bg: "var(--amber-soft)", fg: "var(--amber-ink)" },
  policiales: { bg: "var(--danger-soft)", fg: "var(--danger)" },
  clima: { bg: "var(--sky-soft)", fg: "var(--sky)" },
  mundo: { bg: "var(--sky-soft)", fg: "var(--sky)" },
  salud: { bg: "var(--success-soft)", fg: "var(--success)" },
  sociedad: { bg: "var(--brand-soft)", fg: "var(--brand-dark)" },
  general: { bg: "var(--brand-soft)", fg: "var(--brand-dark)" },
};

const DEFAULT_COLOR: CategoryColor = { bg: "var(--brand-soft)", fg: "var(--brand-dark)" };

export const getCategoryColor = (category?: string | null): CategoryColor =>
  (category && CATEGORY_COLOR[category]) || DEFAULT_COLOR;
