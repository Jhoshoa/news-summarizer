import { useEffect, useMemo, useRef, useState, type ReactElement } from "react";

import {
  useGetPreferenceOptionsQuery,
  usePreviewPreferencesMutation,
  useSubscribeToBriefMutation,
  useUnsubscribeFromBriefMutation,
} from "../services/api";
import type { PreferenceOption } from "../services/types";
import {
  buildSubscribePayload,
  getSubscribeApiErrorMessage,
  isValidEmail,
  isValidInternationalPhone,
  normalizePhone,
  sanitizePhoneInput,
  type SubscribeFormState,
  validateSubscribeForm,
} from "../utils/subscribe";

const defaultForm: SubscribeFormState = {
  channel: "email",
  email: "",
  phone: "",
  telegramId: "",
  categories: ["general"],
  frequency: "diario",
  preferredTime: "manana",
  consentAccepted: false,
};

const CHANNEL_ICONS: Record<string, ReactElement> = {
  email: (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <rect height="16" rx="2.5" stroke="currentColor" strokeWidth="1.8" width="20" x="2" y="4" />
      <path d="m3 6 9 6 9-6" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </svg>
  ),
  whatsapp: (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <path
        d="M12 3.5a8.5 8.5 0 0 0-7.34 12.77L3.5 20.5l4.36-1.14A8.5 8.5 0 1 0 12 3.5Z"
        stroke="currentColor"
        strokeLinejoin="round"
        strokeWidth="1.8"
      />
      <path
        d="M8.7 8.6c.2-.45.4-.46.6-.47h.4c.15 0 .35-.05.53.42.2.5.65 1.68.7 1.8.05.13.09.28 0 .45-.09.18-.14.28-.27.44-.14.16-.28.35-.4.47-.13.13-.27.27-.12.53.15.27.68 1.13 1.47 1.83.99.9 1.83 1.18 2.1 1.31.27.13.43.11.6-.07.16-.18.68-.8.86-1.07.18-.27.36-.23.6-.14.25.09 1.56.74 1.83.87.27.13.44.2.51.31.07.11.07.63-.15 1.24-.22.6-1.28 1.18-1.77 1.22-.45.05-1.02.07-1.66-.1-.38-.1-.87-.27-1.5-.53-2.65-1.14-4.38-3.8-4.51-3.98-.13-.18-1.08-1.44-1.08-2.75 0-1.3.68-1.94.93-2.2Z"
        fill="currentColor"
      />
    </svg>
  ),
  telegram: (
    <svg aria-hidden="true" fill="none" height="18" viewBox="0 0 24 24" width="18">
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="m7.2 12.1 9.1-3.5c.42-.16.82.19.69.63l-1.53 6.85c-.1.46-.63.66-1 .36l-2.32-1.85-1.24 1.15c-.24.22-.63.13-.75-.17l-.85-2.16-2.25-.7c-.5-.16-.5-.87.15-1.06Z"
        fill="currentColor"
      />
    </svg>
  ),
};

const optionLabel = (option: PreferenceOption) => (
  <>
    <span className="channel-label">
      {CHANNEL_ICONS[option.slug]}
      <strong>{option.label}</strong>
    </span>
    {option.note && <small>{option.note}</small>}
  </>
);

const CHANNEL_MOCK_COPY: Record<
  SubscribeFormState["channel"],
  { app: string; senderLine: (form: SubscribeFormState) => string; subLine: string }
> = {
  email: {
    app: "Bandeja de entrada",
    senderLine: (form) => `Para: ${form.email.trim() || "tu-correo@gmail.com"}`,
    subLine: "Asunto: Tu brief de EcoBrief",
  },
  whatsapp: {
    app: "WhatsApp",
    senderLine: (form) => (form.phone.trim() ? form.phone : "+591 700 00000"),
    subLine: "en linea",
  },
  telegram: {
    app: "Telegram",
    senderLine: (form) => (form.telegramId.trim() ? `@${form.telegramId.trim().replace(/^@/, "")}` : "Bot de EcoBrief"),
    subLine: "bot",
  },
};

export const SubscribePage = () => {
  const { data: options, isError: optionsError, isFetching: isLoadingOptions } = useGetPreferenceOptionsQuery();
  const [subscribe, subscribeState] = useSubscribeToBriefMutation();
  const [unsubscribe, unsubscribeState] = useUnsubscribeFromBriefMutation();
  const [previewPreferences, previewState] = usePreviewPreferencesMutation();
  const [form, setForm] = useState<SubscribeFormState>(defaultForm);
  const [unsubscribeIdentifier, setUnsubscribeIdentifier] = useState("");
  const [formErrors, setFormErrors] = useState<string[]>([]);
  const [unsubscribeMessage, setUnsubscribeMessage] = useState("");
  const [subscribeMessage, setSubscribeMessage] = useState("");
  const [isConfirmingSubscribe, setIsConfirmingSubscribe] = useState(false);
  const [isTermsOpen, setIsTermsOpen] = useState(false);
  const [toast, setToast] = useState<{ message: string; tone: "error" | "success" } | null>(null);
  const [touchedFields, setTouchedFields] = useState<Record<string, boolean>>({});

  const selectedChannel = options?.channels.find((channel) => channel.slug === form.channel);
  const selectedCategories = useMemo(
    () =>
      (options?.categories ?? []).filter((category) => form.categories.includes(category.slug)),
    [form.categories, options?.categories],
  );
  const categoryLabelBySlug = useMemo(
    () => new Map((options?.categories ?? []).map((category) => [category.slug, category.label])),
    [options?.categories],
  );

  useEffect(() => {
    if (!isConfirmingSubscribe && !isTermsOpen) {
      return undefined;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsConfirmingSubscribe(false);
        setIsTermsOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isConfirmingSubscribe, isTermsOpen]);

  const toggleCategory = (slug: string) => {
    setForm((current) => {
      const categories = current.categories.includes(slug)
        ? current.categories.filter((category) => category !== slug)
        : [...current.categories, slug];
      return {
        ...current,
        categories,
      };
    });
  };

  const markFieldTouched = (field: string) => {
    setTouchedFields((current) => ({
      ...current,
      [field]: true,
    }));
  };

  const emailInputError =
    form.channel === "email" && touchedFields.email && !isValidEmail(form.email)
      ? "Ingresa un correo electronico valido."
      : "";
  const phoneInputError =
    form.channel === "whatsapp" && touchedFields.phone && !isValidInternationalPhone(form.phone)
      ? "Ingresa un numero de WhatsApp en formato internacional."
      : "";
  const telegramInputError =
    form.channel === "telegram" && touchedFields.telegramId && !form.telegramId.trim()
      ? "Telegram requiere un identificador o usar el bot configurado."
      : "";

  const previewTriggerRef = useRef(previewPreferences);
  previewTriggerRef.current = previewPreferences;

  useEffect(() => {
    if (!form.categories.length) {
      return undefined;
    }

    const categories = form.categories;
    const frequency = form.frequency;
    const timeout = window.setTimeout(() => {
      previewTriggerRef.current({ categories, frequency });
    }, 450);

    return () => window.clearTimeout(timeout);
  }, [form.categories, form.frequency]);

  const handleSubmit = async () => {
    const errors = validateSubscribeForm(form, options);
    setFormErrors(errors);
    setSubscribeMessage("");
    setToast(null);

    if (errors.length) {
      return;
    }

    setIsConfirmingSubscribe(true);
  };

  const handleConfirmSubscribe = async () => {
    const payload = buildSubscribePayload(form, options);
    try {
      const response = await subscribe(payload).unwrap();
      setSubscribeMessage(response.message);
      setToast({ message: "Suscripcion guardada correctamente.", tone: "success" });
      setForm(defaultForm);
      setTouchedFields({});
      setFormErrors([]);
      setIsConfirmingSubscribe(false);
      previewState.reset();
    } catch (error) {
      const message = getSubscribeApiErrorMessage(error);
      setIsConfirmingSubscribe(false);
      setFormErrors([message]);
      setToast({
        message,
        tone: "error",
      });
    }
  };

  const handleUnsubscribe = async () => {
    const identifier =
      form.channel === "whatsapp"
        ? normalizePhone(unsubscribeIdentifier)
        : unsubscribeIdentifier.trim();
    setUnsubscribeMessage("");

    if (!identifier || identifier.length < 3) {
      setUnsubscribeMessage("Ingresa el numero o identificador usado en la suscripcion.");
      return;
    }

    try {
      const response = await unsubscribe({
        channel: form.channel,
        identifier,
      }).unwrap();
      setUnsubscribeMessage(response.message);
    } catch {
      setUnsubscribeMessage("No se pudo procesar la baja. Revisa el backend e intenta de nuevo.");
    }
  };

  return (
    <section className="subscribe-page">
      {toast && (
        <div className={`toast ${toast.tone}`} role="status" aria-live="polite">
          <span>{toast.message}</span>
          <button type="button" aria-label="Cerrar notificacion" onClick={() => setToast(null)}>
            x
          </button>
        </div>
      )}

      <header className="data-hero subscribe-hero">
        <div>
          <span className="eyebrow">Preferencias EcoBrief</span>
          <h1>Personaliza tu brief</h1>
          <p>
            Recibe solo las categorias que te importan, por el canal y frecuencia que elijas.
            Puedes cambiar preferencias o darte de baja cuando quieras.
          </p>
        </div>
      </header>

      {optionsError && (
        <p className="form-notice">No se pudieron cargar las opciones de preferencias.</p>
      )}

      <div className="subscribe-layout">
        <section className="data-panel subscribe-form-panel">
          <div className="panel-heading">
            <span className="panel-title">Suscripcion</span>
            <p>La validacion final se realiza tambien en backend.</p>
          </div>

          <div className="form-grid">
            <label className="form-field form-field--full">
              <span>Canal</span>
              <div className="segmented-options">
                {(options?.channels ?? []).map((channel) => (
                  <button
                    className={form.channel === channel.slug ? "active" : ""}
                    disabled={!channel.enabled && channel.slug !== "telegram"}
                    key={channel.slug}
                    type="button"
                    onClick={() =>
                      setForm((current) => ({
                        ...current,
                        channel: channel.slug as SubscribeFormState["channel"],
                      }))
                    }
                  >
                    {optionLabel(channel)}
                  </button>
                ))}
              </div>
              {selectedChannel?.note && <small>{selectedChannel.note}</small>}
            </label>

            {form.channel === "whatsapp" ? (
              <label className="form-field form-field--full">
                <span>Numero de WhatsApp</span>
                <input
                  aria-describedby={phoneInputError ? "phone-error" : undefined}
                  aria-invalid={Boolean(phoneInputError)}
                  className={phoneInputError ? "invalid" : ""}
                  inputMode="tel"
                  placeholder="+59170000000"
                  type="tel"
                  value={form.phone}
                  onBlur={() => markFieldTouched("phone")}
                  onChange={(event) => {
                    markFieldTouched("phone");
                    setForm((current) => ({
                      ...current,
                      phone: sanitizePhoneInput(event.target.value),
                    }));
                  }}
                />
                {phoneInputError && <small className="field-error" id="phone-error">{phoneInputError}</small>}
              </label>
            ) : form.channel === "email" ? (
              <label className="form-field form-field--full">
                <span>Correo electronico</span>
                <input
                  aria-describedby={emailInputError ? "email-error" : undefined}
                  aria-invalid={Boolean(emailInputError)}
                  autoComplete="email"
                  className={emailInputError ? "invalid" : ""}
                  inputMode="email"
                  placeholder="tu-correo@gmail.com"
                  type="email"
                  value={form.email}
                  onBlur={() => markFieldTouched("email")}
                  onChange={(event) => {
                    markFieldTouched("email");
                    setForm((current) => ({
                      ...current,
                      email: event.target.value,
                    }));
                  }}
                />
                {emailInputError && <small className="field-error" id="email-error">{emailInputError}</small>}
              </label>
            ) : (
              <label className="form-field form-field--full">
                <span>Telegram ID</span>
                <input
                  aria-describedby={telegramInputError ? "telegram-error" : undefined}
                  aria-invalid={Boolean(telegramInputError)}
                  className={telegramInputError ? "invalid" : ""}
                  placeholder="chat_id o identificador de demo"
                  type="text"
                  value={form.telegramId}
                  onBlur={() => markFieldTouched("telegramId")}
                  onChange={(event) => {
                    markFieldTouched("telegramId");
                    setForm((current) => ({
                      ...current,
                      telegramId: event.target.value,
                    }));
                  }}
                />
                {telegramInputError && <small className="field-error" id="telegram-error">{telegramInputError}</small>}
                <small>Para usuarios reales, lo ideal es conectar desde el bot con /preferencias.</small>
              </label>
            )}
          </div>

          <fieldset className="category-fieldset">
            <legend>Categorias</legend>
            <div className="category-choice-grid">
              {(options?.categories ?? []).map((category) => (
                <label className="check-card" key={category.slug}>
                  <input
                    checked={form.categories.includes(category.slug)}
                    type="checkbox"
                    onChange={() => toggleCategory(category.slug)}
                  />
                  <span>{category.label}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className="form-grid">
            <label className="form-field">
              <span>Frecuencia</span>
              <select
                value={form.frequency}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    frequency: event.target.value,
                  }))
                }
              >
                {(options?.frequencies ?? []).map((frequency) => (
                  <option key={frequency.slug} value={frequency.slug}>
                    {frequency.label}
                  </option>
                ))}
              </select>
            </label>

            <label className="form-field">
              <span>Ventana preferida</span>
              <select
                value={form.preferredTime}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    preferredTime: event.target.value,
                  }))
                }
              >
                {(options?.preferred_times ?? []).map((time) => (
                  <option key={time.slug} value={time.slug}>
                    {time.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label className="consent-row">
            <input
              checked={form.consentAccepted}
              type="checkbox"
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  consentAccepted: event.target.checked,
                }))
              }
            />
            <span>
              Acepto recibir briefs de EcoBrief segun mis preferencias y entiendo que puedo darme
              de baja cuando quiera. Acepto los{" "}
              <button
                className="inline-link"
                type="button"
                onClick={(event) => {
                  event.preventDefault();
                  setIsTermsOpen(true);
                }}
              >
                terminos y condiciones
              </button>
              .
            </span>
          </label>

          {formErrors.length > 0 && (
            <div className="form-notice">
              {formErrors.map((error) => (
                <p key={error}>{error}</p>
              ))}
            </div>
          )}

          {subscribeMessage && <p className="success-notice">{subscribeMessage}</p>}

          <div className="form-actions">
            <button className="button" disabled={subscribeState.isLoading || isLoadingOptions} type="button" onClick={handleSubmit}>
              {subscribeState.isLoading ? "Guardando" : "Guardar preferencias"}
            </button>
          </div>
        </section>

        <aside className="data-context-sidebar subscribe-side-panel">
          <section className="subscribe-preview-panel">
            <div className="panel-heading">
              <span className="panel-title">Asi se veria tu brief</span>
            </div>
            <div className="chips">
              {selectedCategories.map((category) => (
                <span key={category.slug}>{category.label}</span>
              ))}
            </div>

            <div className={`channel-mock channel-mock--${form.channel}`}>
              <div className="channel-mock-header">
                <span className="channel-mock-avatar">{CHANNEL_ICONS[form.channel]}</span>
                <div className="channel-mock-header-text">
                  <strong>{CHANNEL_MOCK_COPY[form.channel].app}</strong>
                  <small>{CHANNEL_MOCK_COPY[form.channel].senderLine(form)}</small>
                </div>
              </div>

              <div className="channel-mock-body">
                {previewState.isLoading ? (
                  <p className="impact-section-copy">Cargando briefs recientes...</p>
                ) : previewState.isError ? (
                  <p className="form-notice">
                    No se pudo cargar el preview. Revisa el backend e intenta de nuevo.
                  </p>
                ) : previewState.data?.items.length ? (
                  form.channel === "email" ? (
                    previewState.data.items.map((item) => (
                      <article className="mock-email-card" key={`${item.category}-${item.title}`}>
                        <span>{categoryLabelBySlug.get(item.category) ?? item.category}</span>
                        <h3>{item.title}</h3>
                        <p>{item.summary}</p>
                        {item.summary_date && <small>{item.summary_date}</small>}
                      </article>
                    ))
                  ) : (
                    <div className="mock-chat-bubble">
                      <strong>Tu brief de hoy</strong>
                      <ul>
                        {previewState.data.items.map((item) => (
                          <li key={`${item.category}-${item.title}`}>
                            <span>{categoryLabelBySlug.get(item.category) ?? item.category}</span>
                            {item.title}
                          </li>
                        ))}
                      </ul>
                      <span className="mock-chat-meta">
                        {new Date().toLocaleTimeString("es-BO", { hour: "2-digit", minute: "2-digit" })}
                        {form.channel === "whatsapp" && <span className="mock-chat-check">&#10003;&#10003;</span>}
                      </span>
                    </div>
                  )
                ) : previewState.data ? (
                  <p className="impact-section-copy">
                    No hay briefs recientes para las categorias seleccionadas.
                  </p>
                ) : (
                  <p className="impact-section-copy">Selecciona categorias para ver un ejemplo.</p>
                )}
              </div>
            </div>
            {previewState.data && !previewState.isLoading && <small>{previewState.data.message}</small>}
          </section>

          <section className="unsubscribe-panel">
            <div className="panel-heading">
              <span className="panel-title">Cancelar suscripcion</span>
              <p>Usa el mismo canal con el que te registraste.</p>
            </div>
            <div className="unsubscribe-row">
              <input
                placeholder={
                  form.channel === "whatsapp"
                    ? "+59170000000"
                    : form.channel === "email"
                      ? "tu-correo@gmail.com"
                      : "Telegram ID"
                }
                type="text"
                value={unsubscribeIdentifier}
                onChange={(event) =>
                  setUnsubscribeIdentifier(
                    form.channel === "whatsapp"
                      ? sanitizePhoneInput(event.target.value)
                      : event.target.value,
                  )
                }
              />
              <button
                className="secondary-button"
                disabled={unsubscribeState.isLoading}
                type="button"
                onClick={handleUnsubscribe}
              >
                {unsubscribeState.isLoading ? "Procesando" : "Cancelar"}
              </button>
            </div>
            {unsubscribeMessage && <p className="impact-section-copy">{unsubscribeMessage}</p>}
          </section>
        </aside>
      </div>

      {isConfirmingSubscribe && (
        <div className="modal-backdrop" role="presentation">
          <section
            aria-labelledby="subscribe-confirm-title"
            aria-modal="true"
            className="confirm-modal"
            role="dialog"
          >
            <div>
              <span className="panel-title" id="subscribe-confirm-title">
                Confirmar suscripcion
              </span>
              <p>
                Revisa tus preferencias antes de guardar. Podras cambiarlas o darte de baja cuando
                quieras.
              </p>
            </div>
            <dl className="confirm-summary">
              <div>
                <dt>Canal</dt>
                <dd>{selectedChannel?.label ?? form.channel}</dd>
              </div>
              <div>
                <dt>Categorias</dt>
                <dd>{selectedCategories.map((category) => category.label).join(", ")}</dd>
              </div>
              <div>
                <dt>Frecuencia</dt>
                <dd>
                  {options?.frequencies.find((frequency) => frequency.slug === form.frequency)?.label ??
                    form.frequency}
                </dd>
              </div>
              <div>
                <dt>Ventana</dt>
                <dd>
                  {options?.preferred_times.find((time) => time.slug === form.preferredTime)?.label ??
                    form.preferredTime}
                </dd>
              </div>
            </dl>
            <div className="form-actions">
              <button className="secondary-button" type="button" onClick={() => setIsConfirmingSubscribe(false)}>
                Cancelar
              </button>
              <button className="button" disabled={subscribeState.isLoading} type="button" onClick={handleConfirmSubscribe}>
                {subscribeState.isLoading ? "Guardando" : "Confirmar suscripcion"}
              </button>
            </div>
          </section>
        </div>
      )}

      {isTermsOpen && (
        <div className="modal-backdrop" role="presentation" onClick={() => setIsTermsOpen(false)}>
          <section
            aria-labelledby="terms-modal-title"
            aria-modal="true"
            className="confirm-modal terms-modal"
            role="dialog"
            onClick={(event) => event.stopPropagation()}
          >
            <div>
              <span className="panel-title" id="terms-modal-title">
                Terminos y condiciones
              </span>
              <p>Version resumida. Ultima actualizacion: agosto de 2026.</p>
            </div>

            <div className="terms-body">
              <section>
                <h3>1. Que es EcoBrief Bolivia</h3>
                <p>
                  Un servicio que resume noticias bolivianas de fuentes publicas con apoyo de
                  inteligencia artificial. No reemplaza al medio original: cada resumen cita su
                  fuente.
                </p>
              </section>

              <section>
                <h3>2. Tu suscripcion</h3>
                <p>
                  Al suscribirte aceptas recibir briefs por el canal, frecuencia y categorias que
                  elijas. Puedes cambiar tus preferencias o darte de baja en cualquier momento
                  desde esta misma pagina.
                </p>
              </section>

              <section>
                <h3>3. Tus datos</h3>
                <p>
                  Guardamos solo el contacto (correo, telefono o ID de Telegram) y las preferencias
                  que configuras, unicamente para enviarte el brief. No los compartimos con
                  terceros. Bolivia todavia no tiene una ley integral de proteccion de datos
                  personales (hay un anteproyecto en tramite ante AGETIC); mientras tanto aplicamos
                  los principios de la Ley N.º 164 sobre inviolabilidad de las comunicaciones y la
                  Ley N.º 1080 (Ciudadania Digital, Art. 12) sobre uso limitado de datos
                  personales.
                </p>
              </section>

              <section>
                <h3>4. Contenido generado con IA</h3>
                <p>
                  Los resumenes se generan automaticamente y pueden contener errores o
                  imprecisiones. Ante cualquier duda, verifica siempre la fuente original citada en
                  cada nota.
                </p>
              </section>

              <section>
                <h3>Marco legal de referencia</h3>
                <ul>
                  <li>
                    <a href="https://www.lexivox.org/norms/BO-L-19250119.xhtml" rel="noopener noreferrer" target="_blank">
                      Ley de Imprenta, 19 de enero de 1925
                    </a>
                    {" "}— Art. 1: libertad de publicar y difundir pensamientos sin censura previa.
                  </li>
                  <li>
                    <a href="https://www.oas.org/dil/esp/constitucion_bolivia.pdf" rel="noopener noreferrer" target="_blank">
                      Constitucion Politica del Estado
                    </a>
                    {" "}— Art. 21 y 106: derecho a la comunicacion, la informacion y la libertad de
                    expresion.
                  </li>
                  <li>
                    <a href="https://www.lexivox.org/norms/BO-L-N164.html" rel="noopener noreferrer" target="_blank">
                      Ley N.º 164, Ley General de Telecomunicaciones, TIC (2011)
                    </a>
                    {" "}— inviolabilidad de las comunicaciones y proteccion de datos de usuarios.
                  </li>
                  <li>
                    <a href="https://www.lexivox.org/norms/BO-L-N1080.html" rel="noopener noreferrer" target="_blank">
                      Ley N.º 1080, Ley de Ciudadania Digital (2018)
                    </a>
                    {" "}— Art. 12: proteccion de datos personales y seguridad informatica.
                  </li>
                </ul>
              </section>
            </div>

            <div className="form-actions">
              <button className="button" type="button" onClick={() => setIsTermsOpen(false)}>
                Cerrar
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
};
