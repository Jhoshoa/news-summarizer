import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as analytics from "../../services/analytics";
import type { Story } from "../../services/types";
import { StoryTrustPanel } from "./StoryTrustPanel";

const baseStory: Story = {
  id: "story-1",
  canonical_title: "Historia de prueba",
  short_summary: null,
  detailed_summary: null,
  category: "economia",
  country: "bolivia",
  current_status: "developing",
  confidence: { level: "multi_source", label: "Confirmado por varias fuentes" },
  first_published_at: "2026-08-24T10:00:00",
  last_updated_at: "2026-08-24T12:00:00",
  last_update_note: null,
  article_count: 2,
  source_count: 2,
  sources: ["MedioA", "MedioB"],
  articles: [],
  claims: [
    {
      claim: "El pago inicia el 15 de marzo",
      confidence: "multi_source",
      claim_type: "fecha",
      article_id: 1,
      source_url: "https://medioa.com/nota",
      source_excerpt: "el pago inicia el 15 de marzo",
      published_at: null,
    },
  ],
  coverage: {
    source_count: 2,
    sources: ["MedioA", "MedioB"],
    confirmed_by_multiple_sources: [
      {
        claim: "El pago inicia el 15 de marzo",
        confidence: "multi_source",
        claim_type: "fecha",
        article_id: 1,
        source_url: "https://medioa.com/nota",
        source_excerpt: "el pago inicia el 15 de marzo",
        published_at: null,
      },
    ],
    based_on_official_statement: [],
    reported_by_single_source: [],
  },
  corrections: [],
};

describe("StoryTrustPanel", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing visible while loading", () => {
    render(<StoryTrustPanel story={undefined} isLoading isError={false} articleId={1} />);
    expect(screen.queryByText("Trazabilidad")).not.toBeInTheDocument();
  });

  it("renders nothing when the story failed to load, without throwing", () => {
    const { container } = render(<StoryTrustPanel story={undefined} isLoading={false} isError articleId={1} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when there is no story yet (e.g. article without story_cluster_id)", () => {
    const { container } = render(
      <StoryTrustPanel story={undefined} isLoading={false} isError={false} articleId={1} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the confidence badge, sources, and claims for a loaded story", () => {
    const { container } = render(
      <StoryTrustPanel story={baseStory} isLoading={false} isError={false} articleId={1} />,
    );

    expect(container.querySelector(".status-badge.confidence-multi")).toHaveTextContent(
      "Confirmado por varias fuentes",
    );
    expect(screen.getByText("MedioA")).toBeInTheDocument();
    expect(screen.getByText("MedioB")).toBeInTheDocument();
    expect(screen.getByText("El pago inicia el 15 de marzo")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver fuente" })).toHaveAttribute(
      "href",
      "https://medioa.com/nota",
    );
  });

  it("hides the sources list when the story has only one source", () => {
    const singleSourceStory: Story = { ...baseStory, sources: ["MedioA"], source_count: 1 };
    render(<StoryTrustPanel story={singleSourceStory} isLoading={false} isError={false} articleId={1} />);

    expect(screen.queryByText(/Fuentes que lo confirman/)).not.toBeInTheDocument();
  });

  it("shows the update note when present", () => {
    const updatedStory: Story = { ...baseStory, last_update_note: "Actualización: nuevos datos" };
    render(<StoryTrustPanel story={updatedStory} isLoading={false} isError={false} articleId={1} />);

    expect(screen.getByText("Actualización: nuevos datos")).toBeInTheDocument();
  });

  it("shows correction history when present", () => {
    const correctedStory: Story = {
      ...baseStory,
      confidence: { level: "corrected", label: "Corregido después de publicación" },
      corrections: [
        { reason: "El monto correcto es Bs 1.2 millones", corrected_by: "editor", corrected_at: "2026-08-24T13:00:00" },
      ],
    };
    render(<StoryTrustPanel story={correctedStory} isLoading={false} isError={false} articleId={1} />);

    expect(screen.getByText("El monto correcto es Bs 1.2 millones")).toBeInTheDocument();
  });

  it("tracks feedback_submitted and shows a confirmation when reporting an error", async () => {
    const trackEventSpy = vi.spyOn(analytics, "trackEvent").mockImplementation(() => {});
    const user = userEvent.setup();
    render(<StoryTrustPanel story={baseStory} isLoading={false} isError={false} articleId={42} />);

    await user.click(screen.getByRole("button", { name: "Reportar un error" }));

    expect(trackEventSpy).toHaveBeenCalledWith("feedback_submitted", {
      storyId: "story-1",
      metadata: { feedback_type: "error_report", article_id: 42 },
    });
    expect(screen.getByText("Gracias, registramos tu observación.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reportar un error" })).not.toBeInTheDocument();
  });
});
