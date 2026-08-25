import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Sin esto, el DOM de un test no se desmonta antes del siguiente: elementos
// de renders previos se acumulan y rompen queries como getByRole que esperan
// un unico match (vitest no expone `afterEach` global como Jest).
afterEach(() => {
  cleanup();
});
