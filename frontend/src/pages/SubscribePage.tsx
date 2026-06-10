import { useEffect, useMemo, useState } from "react";

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

const optionLabel = (option: PreferenceOption) => (
  <>
    <strong>{option.label}</strong>
    {option.note && <small>{option.note}</small>}
  </>
);

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
  const [toast, setToast] = useState<{ message: string; tone: "error" | "success" } | null>(null);
  const [touchedFields, setTouchedFields] = useState<Record<string, boolean>>({});

  const selectedChannel = options?.channels.find((channel) => channel.slug === form.channel);
  const selectedCategories = useMemo(
    () =>
      (options?.categories ?? []).filter((category) => form.categories.includes(category.slug)),
    [form.categories, options?.categories],
  );

  useEffect(() => {
    if (!isConfirmingSubscribe) {
      return undefined;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsConfirmingSubscribe(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isConfirmingSubscribe]);

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

  const handlePreview = async () => {
    const errors = validateSubscribeForm({ ...form, consentAccepted: true }, options);
    const categoryErrors = errors.filter((error) => error.includes("categoria"));
    if (categoryErrors.length) {
      setFormErrors(categoryErrors);
      return;
    }

    setFormErrors([]);
    await previewPreferences({
      categories: form.categories,
      frequency: form.frequency,
    });
  };

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
        <div className="data-status-card">
          <span>Canal recomendado</span>
          <strong>Email</strong>
          <small>WhatsApp queda disponible para demo y Telegram cuando el bot este configurado.</small>
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
            <label className="form-field">
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
              <label className="form-field">
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
              <label className="form-field">
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
              <label className="form-field">
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
              de baja cuando quiera.
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
            <button className="secondary-button" disabled={previewState.isLoading} type="button" onClick={handlePreview}>
              {previewState.isLoading ? "Cargando preview" : "Ver preview"}
            </button>
          </div>
        </section>

        <aside className="data-panel subscribe-preview-panel">
          <span className="panel-title">Asi se veria tu brief</span>
          <div className="chips">
            {selectedCategories.map((category) => (
              <span key={category.slug}>{category.label}</span>
            ))}
          </div>
          <div className="preview-list">
            {previewState.data?.items.length ? (
              previewState.data.items.map((item) => (
                <article className="preview-item" key={`${item.category}-${item.title}`}>
                  <span>{item.category}</span>
                  <h3>{item.title}</h3>
                  <p>{item.summary}</p>
                </article>
              ))
            ) : (
              <p className="impact-section-copy">
                Usa "Ver preview" para cargar briefs recientes segun tus categorias. No se llama a
                IA para esta vista previa.
              </p>
            )}
          </div>
          {previewState.data && <small>{previewState.data.message}</small>}
        </aside>
      </div>

      <section className="data-panel unsubscribe-panel">
        <div className="panel-heading">
          <span className="panel-title">Cancelar suscripcion</span>
          <p>Tambien puedes darte de baja desde WhatsApp o Telegram enviando cancelar.</p>
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
    </section>
  );
};
