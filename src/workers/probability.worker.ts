/// <reference lib="webworker" />
import { analyzeProbability } from "../domain/probability/engine";
self.onmessage = (e) => {
  const { id, input, config, previous } = e.data;
  try {
    self.postMessage({
      id,
      result: analyzeProbability(
        input,
        config,
        (stage) => self.postMessage({ id, stage }),
        previous,
      ),
    });
  } catch (error) {
    self.postMessage({ id, error: (error as Error).message });
  }
};
