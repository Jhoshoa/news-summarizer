import { describe, expect, it } from "vitest";

import {
  buildNewsHref,
  getCategory,
  getCurrentPage,
  getDateValidationMessage,
  getDateValue,
  getNewsView,
  getSelectedDate,
  isValidDateValue,
} from "./newsRoute";

describe("getCategory", () => {
  it("returns undefined when there is no category param (the 'Todas' tab)", () => {
    expect(getCategory("?date=2026-08-25")).toBeUndefined();
  });

  it("returns 'general' as a real, filterable category", () => {
    // Regression test: this used to be treated as "no filter" because the
    // old "general" tab literally meant "show everything". Now that
    // "General" is a distinct tab sourced from the backend (the catch-all
    // bucket the classifier assigns), ?category=general must filter to it.
    expect(getCategory("?category=general")).toBe("general");
  });

  it("returns any other category value as-is", () => {
    expect(getCategory("?category=policiales")).toBe("policiales");
    expect(getCategory("?category=economia&page=2")).toBe("economia");
  });

  it("treats an empty category param the same as no param", () => {
    expect(getCategory("?category=")).toBeUndefined();
  });
});

describe("getCurrentPage", () => {
  it("defaults to 1 when missing", () => {
    expect(getCurrentPage("")).toBe(1);
  });

  it("parses a valid page number", () => {
    expect(getCurrentPage("?page=3")).toBe(3);
  });

  it("falls back to 1 for zero, negative, or non-numeric values", () => {
    expect(getCurrentPage("?page=0")).toBe(1);
    expect(getCurrentPage("?page=-2")).toBe(1);
    expect(getCurrentPage("?page=abc")).toBe(1);
  });
});

describe("getNewsView", () => {
  it("defaults to 'resumenes'", () => {
    expect(getNewsView("")).toBe("resumenes");
    expect(getNewsView("?view=algo-invalido")).toBe("resumenes");
  });

  it("recognizes 'recolectadas'", () => {
    expect(getNewsView("?view=recolectadas")).toBe("recolectadas");
  });
});

describe("isValidDateValue", () => {
  it("accepts a real calendar date in YYYY-MM-DD", () => {
    expect(isValidDateValue("2026-08-25")).toBe(true);
  });

  it("rejects malformed strings", () => {
    expect(isValidDateValue("25-08-2026")).toBe(false);
    expect(isValidDateValue("2026-8-25")).toBe(false);
    expect(isValidDateValue("not-a-date")).toBe(false);
  });

  it("rejects a calendar-invalid date like Feb 30", () => {
    expect(isValidDateValue("2026-02-30")).toBe(false);
  });
});

describe("getSelectedDate", () => {
  const today = "2026-08-26";

  it("returns today's date when there is no date param", () => {
    expect(getSelectedDate("", today)).toBe(today);
  });

  it("returns the requested date when valid and not in the future", () => {
    expect(getSelectedDate("?date=2026-08-20", today)).toBe("2026-08-20");
  });

  it("falls back to today for an invalid date", () => {
    expect(getSelectedDate("?date=not-a-date", today)).toBe(today);
  });

  it("falls back to today for a future date", () => {
    expect(getSelectedDate("?date=2026-08-27", today)).toBe(today);
  });
});

describe("getDateValidationMessage", () => {
  const today = "2026-08-26";

  it("is empty when there is no date param", () => {
    expect(getDateValidationMessage("", today, today)).toBe("");
  });

  it("is empty when the requested date is valid and matches the selected date", () => {
    expect(getDateValidationMessage("?date=2026-08-20", "2026-08-20", today)).toBe("");
  });

  it("warns about an invalid date format", () => {
    expect(getDateValidationMessage("?date=nope", "2026-08-26", today)).toContain("no es valida");
  });

  it("warns about a future date", () => {
    expect(getDateValidationMessage("?date=2026-08-27", "2026-08-26", today)).toContain(
      "no puede ser futura",
    );
  });
});

describe("buildNewsHref", () => {
  it("builds a URL with page, date and view but omits category when absent", () => {
    expect(buildNewsHref(1, "2026-08-25", undefined, "resumenes")).toBe(
      "/news?page=1&date=2026-08-25&view=resumenes",
    );
  });

  it("includes the category when given", () => {
    expect(buildNewsHref(2, "2026-08-25", "policiales", "recolectadas")).toBe(
      "/news?page=2&date=2026-08-25&view=recolectadas&category=policiales",
    );
  });

  it("includes 'general' as a real category value, not stripping it", () => {
    // Regression test companion to the getCategory fix above.
    expect(buildNewsHref(1, "2026-08-25", "general")).toBe(
      "/news?page=1&date=2026-08-25&view=resumenes&category=general",
    );
  });
});

describe("getDateValue", () => {
  it("formats a Date as YYYY-MM-DD with zero-padding", () => {
    expect(getDateValue(new Date(2026, 0, 5))).toBe("2026-01-05");
  });
});
