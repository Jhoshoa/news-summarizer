const SESSION_STORAGE_KEY = "ecobrief_session_id";
const MAX_BATCH_SIZE = 20;
const FLUSH_DELAY_MS = 2000;

export type AnalyticsEventName =
  | "user_registered"
  | "onboarding_completed"
  | "brief_opened"
  | "story_opened"
  | "source_clicked"
  | "category_followed"
  | "entity_followed"
  | "story_saved"
  | "story_shared"
  | "alert_created"
  | "feedback_submitted"
  | "report_generated";

export type AnalyticsEventProps = {
  category?: string;
  storyId?: string;
  sourceId?: string;
  department?: string;
  country?: string;
  metadata?: Record<string, unknown>;
};

type QueuedEvent = {
  event_name: AnalyticsEventName;
  session_id: string;
  category?: string;
  story_id?: string;
  source_id?: string;
  department?: string;
  country?: string;
  device: string;
  metadata?: Record<string, unknown>;
};

let queue: QueuedEvent[] = [];
let flushTimer: ReturnType<typeof setTimeout> | null = null;
let cachedSessionId: string | null = null;

const generateId = (): string => {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `sess-${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const getSessionId = (): string => {
  if (cachedSessionId) {
    return cachedSessionId;
  }
  try {
    const existing = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (existing) {
      cachedSessionId = existing;
      return existing;
    }
    const created = generateId();
    window.sessionStorage.setItem(SESSION_STORAGE_KEY, created);
    cachedSessionId = created;
    return created;
  } catch {
    // sessionStorage puede fallar en modo privado; degradamos a un id por evento.
    return generateId();
  }
};

const getDevice = (): string => {
  if (typeof navigator === "undefined") {
    return "unknown";
  }
  return /Mobi|Android/i.test(navigator.userAgent) ? "mobile" : "desktop";
};

const getEndpoint = (): string => {
  const base = import.meta.env.VITE_API_BASE_URL || "";
  return `${base}/api/analytics/events`;
};

const sendBatch = (events: QueuedEvent[], useBeacon: boolean): void => {
  if (events.length === 0) {
    return;
  }
  const body = JSON.stringify({ events });

  if (useBeacon && typeof navigator !== "undefined" && "sendBeacon" in navigator) {
    const blob = new Blob([body], { type: "application/json" });
    const sent = navigator.sendBeacon(getEndpoint(), blob);
    if (sent) {
      return;
    }
  }

  // Fire-and-forget: la telemetria nunca debe romper la experiencia del usuario.
  fetch(getEndpoint(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => {
    // Perder eventos de analitica es aceptable; reintentar agregaria complejidad
    // sin beneficio real para telemetria de producto.
  });
};

const scheduleFlush = (): void => {
  if (flushTimer !== null) {
    return;
  }
  flushTimer = setTimeout(() => {
    flushTimer = null;
    flush();
  }, FLUSH_DELAY_MS);
};

export const flush = (useBeacon = false): void => {
  if (flushTimer !== null) {
    clearTimeout(flushTimer);
    flushTimer = null;
  }
  const batch = queue;
  queue = [];
  sendBatch(batch, useBeacon);
};

export const trackEvent = (eventName: AnalyticsEventName, props: AnalyticsEventProps = {}): void => {
  queue.push({
    event_name: eventName,
    session_id: getSessionId(),
    category: props.category,
    story_id: props.storyId,
    source_id: props.sourceId,
    department: props.department,
    country: props.country,
    device: getDevice(),
    metadata: props.metadata,
  });

  if (queue.length >= MAX_BATCH_SIZE) {
    flush();
    return;
  }
  scheduleFlush();
};

if (typeof document !== "undefined") {
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      flush(true);
    }
  });
}

/** Solo para tests: limpia el estado interno del modulo entre casos. */
export const __resetAnalyticsForTests = (): void => {
  if (flushTimer !== null) {
    clearTimeout(flushTimer);
    flushTimer = null;
  }
  queue = [];
  cachedSessionId = null;
};
