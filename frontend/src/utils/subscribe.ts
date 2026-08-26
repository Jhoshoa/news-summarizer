import type { PreferenceOptionsResponse, SubscribeRequest } from "../services/types";

export type SubscribeFormState = {
  channel: "whatsapp" | "telegram" | "email";
  email: string;
  phone: string;
  telegramId: string;
  categories: string[];
  frequency: string;
  preferredHour: number;
  consentAccepted: boolean;
};

export const normalizePhone = (value: string) => {
  let normalized = value.trim().replace(/[\s().-]+/g, "");
  if (normalized.startsWith("00")) {
    normalized = `+${normalized.slice(2)}`;
  }
  if (normalized && !normalized.startsWith("+")) {
    normalized = `+${normalized}`;
  }
  return normalized;
};

export const sanitizePhoneInput = (value: string) => {
  const compact = value.replace(/[^\d+]/g, "");
  const withoutExtraPlus = compact
    .split("")
    .filter((char, index) => char !== "+" || index === 0)
    .join("");
  return withoutExtraPlus.slice(0, 16);
};

export const isValidInternationalPhone = (value: string) => /^\+\d{8,15}$/.test(normalizePhone(value));

export const normalizeEmail = (value: string) => value.trim().toLowerCase();

export const isValidEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(normalizeEmail(value));

export const getSubscribeApiErrorMessage = (error: unknown) => {
  if (!error || typeof error !== "object") {
    return "No se pudo guardar la suscripcion. Revisa los datos e intenta de nuevo.";
  }

  const maybeError = error as {
    data?: { detail?: unknown };
    status?: number | string;
  };
  const detail = maybeError.data?.detail;

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: unknown }).msg);
        }
        return "";
      })
      .filter(Boolean);
    if (messages.length) {
      return messages.join(" ");
    }
  }

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (maybeError.status === 500) {
    return "No se pudo guardar en la base de datos. Revisa que la migracion de email este aplicada.";
  }

  return "No se pudo guardar la suscripcion. Revisa los datos e intenta de nuevo.";
};

export const validateSubscribeForm = (
  form: SubscribeFormState,
  options?: PreferenceOptionsResponse,
) => {
  const errors: string[] = [];
  const validCategories = new Set((options?.categories ?? []).map((item) => item.slug));
  const validFrequencies = new Set((options?.frequencies ?? []).map((item) => item.slug));
  const validPreferredHours = new Set((options?.preferred_hours ?? []).map((item) => item.slug));
  const selectedCategories = form.categories.filter((category) => !validCategories.size || validCategories.has(category));

  if (form.channel === "whatsapp" && !isValidInternationalPhone(form.phone)) {
    errors.push("Ingresa un numero de WhatsApp en formato internacional.");
  }

  if (form.channel === "telegram" && !form.telegramId.trim()) {
    errors.push("Telegram requiere un identificador o usar el bot configurado.");
  }

  if (form.channel === "email" && !isValidEmail(form.email)) {
    errors.push("Ingresa un correo electronico valido.");
  }

  if (!selectedCategories.length) {
    errors.push("Selecciona al menos una categoria.");
  }

  if (validFrequencies.size && !validFrequencies.has(form.frequency)) {
    errors.push("Selecciona una frecuencia valida.");
  }

  if (validPreferredHours.size && !validPreferredHours.has(String(form.preferredHour))) {
    errors.push("Selecciona una hora valida.");
  }

  if (!form.consentAccepted) {
    errors.push("Debes aceptar recibir briefs segun tus preferencias.");
  }

  return errors;
};

export const buildSubscribePayload = (
  form: SubscribeFormState,
  options?: PreferenceOptionsResponse,
): SubscribeRequest => {
  const validCategories = new Set((options?.categories ?? []).map((item) => item.slug));
  const categories = form.categories.filter((category) => !validCategories.size || validCategories.has(category));

  return {
    channel: form.channel,
    phone: form.channel === "whatsapp" ? normalizePhone(form.phone) : null,
    telegram_id: form.channel === "telegram" ? form.telegramId.trim() : null,
    email: form.channel === "email" ? normalizeEmail(form.email) : null,
    categories,
    frequency: form.frequency,
    preferred_hour: form.preferredHour,
    timezone: "America/La_Paz",
    consent_accepted: form.consentAccepted,
  };
};
