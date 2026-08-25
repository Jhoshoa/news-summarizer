import { useState } from "react";

import { trackEvent } from "../../services/analytics";

type ReactionValue = "relevant" | "not_interested" | "already_knew";

const REACTIONS: { value: ReactionValue; label: string }[] = [
  { value: "relevant", label: "Relevante" },
  { value: "not_interested", label: "No me interesa" },
  { value: "already_knew", label: "Ya lo sabia" },
];

type StoryFeedbackProps = {
  articleId: number;
  storyId?: string | null;
};

export const StoryFeedback = ({ articleId, storyId }: StoryFeedbackProps) => {
  const [reaction, setReaction] = useState<ReactionValue | null>(null);
  const [following, setFollowing] = useState(false);

  const sendFeedback = (feedbackType: ReactionValue) => {
    trackEvent("feedback_submitted", {
      storyId: storyId ?? undefined,
      metadata: { feedback_type: feedbackType, article_id: articleId },
    });
    setReaction(feedbackType);
  };

  const toggleFollow = () => {
    trackEvent("story_saved", {
      storyId: storyId ?? undefined,
      metadata: { article_id: articleId },
    });
    setFollowing(true);
  };

  return (
    <section className="story-feedback" aria-label="Feedback sobre esta noticia">
      <div className="story-feedback-reactions">
        {reaction ? (
          <span className="story-feedback-confirmation">Gracias por tu feedback.</span>
        ) : (
          REACTIONS.map((option) => (
            <button
              className="story-feedback-button"
              key={option.value}
              type="button"
              onClick={() => sendFeedback(option.value)}
            >
              {option.label}
            </button>
          ))
        )}
      </div>

      <button
        className="story-feedback-button story-feedback-follow"
        disabled={following}
        type="button"
        onClick={toggleFollow}
      >
        {following ? "Siguiendo esta historia" : "Seguir esta historia"}
      </button>
    </section>
  );
};
