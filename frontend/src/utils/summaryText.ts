const MIN_CONTEXT_CHARS = 110;
const MAX_CONTEXT_CHARS = 360;

export const cleanGeneratedText = (value?: string | null) =>
  String(value ?? "")
    .replace(/^\s*(?:\d+[.)]\s*)+/, "")
    .replace(/\s+/g, " ")
    .trim();

const limitText = (value: string, maxChars = MAX_CONTEXT_CHARS) => {
  if (value.length <= maxChars) {
    return value;
  }

  return value.slice(0, maxChars).replace(/\s+\S*$/, "").trim();
};

const splitSentences = (value: string) =>
  value
    .split(/(?<=[.!?])\s+/)
    .map((sentence) => sentence.replace(/\s+/g, " ").trim())
    .filter(Boolean);

const addsContext = (current: string, candidate: string) => {
  const normalizedCurrent = current.toLowerCase();
  const normalizedCandidate = candidate.toLowerCase();

  return Boolean(normalizedCandidate) && !normalizedCurrent.includes(normalizedCandidate);
};

export const buildContextualSummary = (
  summary?: string | null,
  fallbackContext?: string | null,
) => {
  const baseSummary = cleanGeneratedText(summary);
  if (baseSummary.length >= MIN_CONTEXT_CHARS || !fallbackContext) {
    return limitText(baseSummary);
  }

  let contextualSummary = baseSummary;
  for (const sentence of splitSentences(cleanGeneratedText(fallbackContext))) {
    if (!addsContext(contextualSummary, sentence)) {
      continue;
    }

    contextualSummary = contextualSummary ? `${contextualSummary}. ${sentence}` : sentence;
    if (contextualSummary.length >= MIN_CONTEXT_CHARS) {
      break;
    }
  }

  return limitText(contextualSummary);
};
