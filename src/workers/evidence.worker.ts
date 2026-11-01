/// <reference lib="webworker" />
import { analyzeEvidence } from "../domain/evidence/engine";
self.onmessage = (e) => {
  const { id, input, config } = e.data;
  try {
    self.postMessage({
      id,
      result: analyzeEvidence(input, config, (stage) =>
        self.postMessage({ id, stage }),
      ),
    });
  } catch (error) {
    self.postMessage({ id, error: (error as Error).message });
  }
};
