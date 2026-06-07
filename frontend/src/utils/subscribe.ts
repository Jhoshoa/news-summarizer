import type { PreferenceOptionsResponse, SubscribeRequest } from "../services/types";

export type SubscribeFormState = {
  channel: "whatsapp" | "telegram";
  phone: string;
  telegramId: string;
  categories: string[];
  frequency: string;
  preferredTime: string;
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

export const validateSubscribeForm = (
  form: SubscribeFormState,
  options?: PreferenceOptionsResponse,
) => {
  const errors: string[] = [];
  const validCategories = new Set((options?.categories ?? []).map((item) => item.slug));
  const validFrequencies = new Set((options?.frequencies ?? []).map((item) => item.slug));
  const validPreferredTimes = new Set((options?.preferred_times ?? []).map((item) => item.slug));
  const selectedCategories = form.categories.filter((category) => !validCategories.size || validCategories.has(category));

  if (form.channel === "whatsapp" && !isValidInternationalPhone(form.phone)) {
    errors.push("Ingresa un numero de WhatsApp en formato internacional.");
  }

  if (form.channel === "telegram" && !form.telegramId.trim()) {
    errors.push("Telegram requiere un identificador o usar el bot configurado.");
  }

  if (!selectedCategories.length) {
    errors.push("Selecciona al menos una categoria.");
  }

  if (validFrequencies.size && !validFrequencies.has(form.frequency)) {
    errors.push("Selecciona una frecuencia valida.");
  }

  if (validPreferredTimes.size && !validPreferredTimes.has(form.preferredTime)) {
    errors.push("Selecciona una ventana valida.");
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
    categories,
    frequency: form.frequency,
    preferred_time: form.preferredTime,
    timezone: "America/La_Paz",
    consent_accepted: form.consentAccepted,
  };
};
