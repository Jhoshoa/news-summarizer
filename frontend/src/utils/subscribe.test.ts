import { describe, expect, it } from "vitest";

import type { PreferenceOptionsResponse } from "../services/types";
import {
  buildSubscribePayload,
  isValidEmail,
  isValidInternationalPhone,
  type SubscribeFormState,
  validateSubscribeForm,
} from "./subscribe";

const options: PreferenceOptionsResponse = {
  categories: [
    { slug: "economia", label: "Economia", enabled: true },
    { slug: "general", label: "General", enabled: true },
  ],
  channels: [
    { slug: "email", label: "Email", enabled: true },
    { slug: "whatsapp", label: "WhatsApp", enabled: true },
    { slug: "telegram", label: "Telegram", enabled: true },
  ],
  frequencies: [
    { slug: "diario", label: "Diario", enabled: true },
    { slug: "semanal", label: "Semanal", enabled: true },
  ],
  preferred_hours: Array.from({ length: 15 }, (_, i) => ({
    slug: String(i + 9),
    label: `${String(i + 9).padStart(2, "0")}:00`,
    enabled: true,
  })),
};

const baseForm: SubscribeFormState = {
  channel: "email",
  email: "persona@example.com",
  phone: "",
  telegramId: "",
  categories: ["economia"],
  frequency: "diario",
  preferredHour: 9,
  consentAccepted: true,
};

describe("validateSubscribeForm - preferred hour", () => {
  it("accepts an hour within the valid range", () => {
    const errors = validateSubscribeForm(baseForm, options);
    expect(errors).not.toContain("Selecciona una hora valida.");
  });

  it("rejects an hour outside the valid range (e.g. picked before the form loaded real options)", () => {
    const errors = validateSubscribeForm({ ...baseForm, preferredHour: 3 }, options);
    expect(errors).toContain("Selecciona una hora valida.");
  });

  it("skips hour validation when options haven't loaded yet", () => {
    const errors = validateSubscribeForm({ ...baseForm, preferredHour: 3 }, undefined);
    expect(errors).not.toContain("Selecciona una hora valida.");
  });
});

describe("buildSubscribePayload", () => {
  it("sends preferred_hour as a number, matching the backend's SubscribeRequest", () => {
    const payload = buildSubscribePayload({ ...baseForm, preferredHour: 16 }, options);

    expect(payload.preferred_hour).toBe(16);
    expect(typeof payload.preferred_hour).toBe("number");
  });
});

describe("phone and email helpers (sanity check, unrelated to this session's changes)", () => {
  it("validates an international phone number", () => {
    expect(isValidInternationalPhone("+59170000000")).toBe(true);
    expect(isValidInternationalPhone("123")).toBe(false);
  });

  it("validates an email address", () => {
    expect(isValidEmail("persona@example.com")).toBe(true);
    expect(isValidEmail("no-arroba")).toBe(false);
  });
});
