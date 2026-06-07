import { useMemo, useState } from "react";

import {
  useGetPreferenceOptionsQuery,
  usePreviewPreferencesMutation,
  useSubscribeToBriefMutation,
  useUnsubscribeFromBriefMutation,
} from "../services/api";
import type { PreferenceOption } from "../services/types";
import {
  buildSubscribePayload,
  normalizePhone,
  sanitizePhoneInput,
  type SubscribeFormState,
  validateSubscribeForm,
} from "../utils/subscribe";

const defaultForm: SubscribeFormState = {
  channel: "whatsapp",
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

  const selectedChannel = options?.channels.find((channel) => channel.slug === form.channel);
  const selectedCategories = useMemo(
    () =>
      (options?.categories ?? []).filter((category) => form.categories.includes(category.slug)),
    [form.categories, options?.categories],
  );

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

    if (errors.length) {
      return;
    }

    const payload = buildSubscribePayload(form, options);
    try {
      const response = await subscribe(payload).unwrap();
      setSubscribeMessage(response.message);
    } catch {
      setFormErrors(["No se pudo guardar la suscripcion. Revisa el backend e intenta de nuevo."]);
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
          <strong>WhatsApp</strong>
          <small>Telegram se activa cuando el bot este configurado.</small>
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
                  inputMode="tel"
                  placeholder="+59170000000"
                  type="tel"
                  value={form.phone}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      phone: sanitizePhoneInput(event.target.value),
                    }))
                  }
                />
              </label>
            ) : (
              <label className="form-field">
                <span>Telegram ID</span>
                <input
                  placeholder="chat_id o identificador de demo"
                  type="text"
                  value={form.telegramId}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      telegramId: event.target.value,
                    }))
                  }
                />
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
            placeholder={form.channel === "whatsapp" ? "+59170000000" : "Telegram ID"}
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
    </section>
  );
};
