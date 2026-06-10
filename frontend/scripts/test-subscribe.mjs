import assert from "node:assert/strict";
import { join } from "node:path";
import { loadTsModule } from "./load-ts-module.mjs";

const {
  buildSubscribePayload,
  getSubscribeApiErrorMessage,
  isValidEmail,
  isValidInternationalPhone,
  normalizeEmail,
  normalizePhone,
  sanitizePhoneInput,
  validateSubscribeForm,
} = loadTsModule(join(process.cwd(), "src", "utils", "subscribe.ts"));

const options = {
  categories: [
    { slug: "general", label: "General", enabled: true },
    { slug: "economia", label: "Economia", enabled: true },
  ],
  channels: [
    { slug: "email", label: "Email", enabled: true },
    { slug: "whatsapp", label: "WhatsApp", enabled: true },
  ],
  frequencies: [{ slug: "diario", label: "Diario", enabled: true }],
  preferred_times: [{ slug: "manana", label: "Manana", enabled: true }],
};

const form = {
  channel: "whatsapp",
  email: "",
  phone: "591 700-00000",
  telegramId: "",
  categories: ["economia"],
  frequency: "diario",
  preferredTime: "manana",
  consentAccepted: true,
};

assert.equal(normalizePhone("591 700-00000"), "+59170000000");
assert.equal(normalizePhone("0059170000000"), "+59170000000");
assert.equal(sanitizePhoneInput("abc+591 700-00000 ext"), "+59170000000");
assert.equal(sanitizePhoneInput("++591@@700xx00000"), "+59170000000");
assert.equal(sanitizePhoneInput("591-700-00000"), "59170000000");
assert.equal(isValidInternationalPhone("591 700-00000"), true);
assert.equal(isValidInternationalPhone("abc"), false);
assert.equal(normalizeEmail(" Persona@Example.COM "), "persona@example.com");
assert.equal(isValidEmail("persona@example.com"), true);
assert.equal(isValidEmail("bad"), false);
assert.deepEqual(JSON.parse(JSON.stringify(validateSubscribeForm(form, options))), []);

assert.deepEqual(JSON.parse(JSON.stringify(buildSubscribePayload(form, options))), {
  channel: "whatsapp",
  phone: "+59170000000",
  telegram_id: null,
  email: null,
  categories: ["economia"],
  frequency: "diario",
  preferred_time: "manana",
  timezone: "America/La_Paz",
  consent_accepted: true,
});

assert.match(
  validateSubscribeForm({ ...form, consentAccepted: false }, options).join(" "),
  /aceptar/,
);
assert.match(
  validateSubscribeForm({ ...form, categories: [] }, options).join(" "),
  /categoria/,
);
assert.match(
  validateSubscribeForm({ ...form, phone: "bad" }, options).join(" "),
  /WhatsApp/,
);

const emailForm = {
  ...form,
  channel: "email",
  email: " Persona@Example.COM ",
  phone: "",
};

assert.deepEqual(JSON.parse(JSON.stringify(validateSubscribeForm(emailForm, options))), []);
assert.deepEqual(JSON.parse(JSON.stringify(buildSubscribePayload(emailForm, options))), {
  channel: "email",
  phone: null,
  telegram_id: null,
  email: "persona@example.com",
  categories: ["economia"],
  frequency: "diario",
  preferred_time: "manana",
  timezone: "America/La_Paz",
  consent_accepted: true,
});
assert.match(
  validateSubscribeForm({ ...emailForm, email: "bad" }, options).join(" "),
  /correo/,
);

assert.equal(
  getSubscribeApiErrorMessage({ data: { detail: "DB no disponible" }, status: 503 }),
  "DB no disponible",
);
assert.equal(
  getSubscribeApiErrorMessage({ status: 500 }),
  "No se pudo guardar en la base de datos. Revisa que la migracion de email este aplicada.",
);
assert.equal(
  getSubscribeApiErrorMessage({
    data: { detail: [{ msg: "Value error, Email invalido" }] },
    status: 422,
  }),
  "Value error, Email invalido",
);

console.log("subscribe tests passed");
