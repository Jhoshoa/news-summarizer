import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as analytics from "../../services/analytics";
import { StoryFeedback } from "./StoryFeedback";

describe("StoryFeedback", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the three reaction buttons and the follow button initially", () => {
    render(<StoryFeedback articleId={1} storyId="story-1" />);

    expect(screen.getByRole("button", { name: "Relevante" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "No me interesa" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ya lo sabia" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Seguir esta historia" })).toBeInTheDocument();
  });

  it("tracks feedback_submitted with the right feedback_type and replaces the buttons with a confirmation", async () => {
    const trackEventSpy = vi.spyOn(analytics, "trackEvent").mockImplementation(() => {});
    const user = userEvent.setup();
    render(<StoryFeedback articleId={42} storyId="story-1" />);

    await user.click(screen.getByRole("button", { name: "No me interesa" }));

    expect(trackEventSpy).toHaveBeenCalledWith("feedback_submitted", {
      storyId: "story-1",
      metadata: { feedback_type: "not_interested", article_id: 42 },
    });
    expect(screen.getByText("Gracias por tu feedback.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Relevante" })).not.toBeInTheDocument();
  });

  it("tracks story_saved when following a story, independently of the reaction", async () => {
    const trackEventSpy = vi.spyOn(analytics, "trackEvent").mockImplementation(() => {});
    const user = userEvent.setup();
    render(<StoryFeedback articleId={7} storyId="story-9" />);

    await user.click(screen.getByRole("button", { name: "Seguir esta historia" }));

    expect(trackEventSpy).toHaveBeenCalledWith("story_saved", {
      storyId: "story-9",
      metadata: { article_id: 7 },
    });
    expect(screen.getByRole("button", { name: "Siguiendo esta historia" })).toBeDisabled();
    // La reaccion sigue disponible: seguir no es excluyente con reaccionar.
    expect(screen.getByRole("button", { name: "Relevante" })).toBeInTheDocument();
  });

  it("works without a storyId (article without story_cluster_id yet)", async () => {
    const trackEventSpy = vi.spyOn(analytics, "trackEvent").mockImplementation(() => {});
    const user = userEvent.setup();
    render(<StoryFeedback articleId={3} />);

    await user.click(screen.getByRole("button", { name: "Relevante" }));

    expect(trackEventSpy).toHaveBeenCalledWith("feedback_submitted", {
      storyId: undefined,
      metadata: { feedback_type: "relevant", article_id: 3 },
    });
  });
});
