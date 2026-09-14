import QRCode from "qrcode";
import { useEffect, useState } from "react";

import { useCreateTelegramLinkMutation } from "../../services/api";

type TelegramConnectProps = {
  categories: string[];
  frequency: string;
  preferredHour: number;
  timezone: string;
  consentAccepted: boolean;
};

type ActiveLink = {
  deepLink: string;
  expiresAt: number;
};

const formatCountdown = (secondsLeft: number) => {
  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
};

export const TelegramConnect = ({
  categories,
  frequency,
  preferredHour,
  timezone,
  consentAccepted,
}: TelegramConnectProps) => {
  const [createTelegramLink, telegramLinkState] = useCreateTelegramLinkMutation();
  const [link, setLink] = useState<ActiveLink | null>(null);
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [secondsLeft, setSecondsLeft] = useState(0);
  const [error, setError] = useState("");

  const canGenerate = categories.length > 0 && consentAccepted;
  const expired = link ? secondsLeft <= 0 : false;

  useEffect(() => {
    if (!link) {
      setQrDataUrl(null);
      return;
    }

    let cancelled = false;
    QRCode.toDataURL(link.deepLink, { margin: 1, width: 220 })
      .then((dataUrl) => {
        if (!cancelled) setQrDataUrl(dataUrl);
      })
      .catch(() => {
        if (!cancelled) setQrDataUrl(null);
      });

    return () => {
      cancelled = true;
    };
  }, [link]);

  useEffect(() => {
    if (!link) return undefined;

    const tick = () => setSecondsLeft(Math.max(0, Math.round((link.expiresAt - Date.now()) / 1000)));
    tick();
    const interval = window.setInterval(tick, 1000);
    return () => window.clearInterval(interval);
  }, [link]);

  const handleGenerate = async () => {
    setError("");
    try {
      const response = await createTelegramLink({
        categories,
        frequency,
        preferred_hour: preferredHour,
        timezone,
        consent_accepted: consentAccepted,
      }).unwrap();
      setLink({
        deepLink: response.deep_link,
        expiresAt: Date.now() + response.expires_in_seconds * 1000,
      });
    } catch {
      setError("No se pudo generar el codigo de Telegram. Revisa que el bot este configurado e intenta de nuevo.");
    }
  };

  const handleCopy = async () => {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link.deepLink);
    } catch {
      // El clipboard puede fallar (permiso denegado, contexto no seguro); el
      // link ya queda visible en el boton "Abrir en Telegram" para copiar a mano.
    }
  };

  return (
    <div className="telegram-connect">
      {!link || expired ? (
        <>
          <p className="telegram-connect-lede">
            Generá un código para conectarte con nuestro bot de Telegram. Va a guardar las
            categorías, frecuencia y hora que elegiste arriba, sin que tengas que repetirlas
            adentro de Telegram.
          </p>
          <button
            className="button"
            disabled={!canGenerate || telegramLinkState.isLoading}
            type="button"
            onClick={handleGenerate}
          >
            {telegramLinkState.isLoading
              ? "Generando"
              : expired
                ? "Generar un nuevo codigo"
                : "Generar codigo de Telegram"}
          </button>
          {!canGenerate && (
            <small>Elegi al menos una categoria y aceptá los terminos para generar el codigo.</small>
          )}
          {expired && <small className="field-error">El codigo anterior vencio.</small>}
        </>
      ) : (
        <div className="telegram-connect-result">
          {qrDataUrl && (
            <img alt="Codigo QR para conectar con el bot de Telegram de EcoBrief" src={qrDataUrl} />
          )}
          <div className="telegram-connect-actions">
            <a className="button" href={link.deepLink} rel="noopener noreferrer" target="_blank">
              Abrir en Telegram
            </a>
            <button className="secondary-button" type="button" onClick={handleCopy}>
              Copiar link
            </button>
          </div>
          <small>
            Escaneá el código con la cámara o abrí el link desde tu celular, y presioná Start.
            Vence en {formatCountdown(secondsLeft)}.
          </small>
        </div>
      )}
      {error && <p className="form-notice">{error}</p>}
    </div>
  );
};
