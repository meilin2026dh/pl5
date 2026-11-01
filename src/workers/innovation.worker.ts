/// <reference lib="webworker" />
import { runInnovation } from "../domain/innovation/engine";
self.onmessage = (e) => {
  const { id, input, config } = e.data;
  try {
    const result = runInnovation(input, config, (stage) =>
      self.postMessage({ id, stage }),
    );
    self.postMessage({ id, result });
  } catch (error) {
    self.postMessage({ id, error: (error as Error).message });
  }
};
