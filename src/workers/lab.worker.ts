/// <reference lib="webworker" />
import { analyzeLab } from "../domain/lab/engine";
self.onmessage = (e) => {
  const { id, input, config, task, previous } = e.data;
  try {
    self.postMessage({
      id,
      result: analyzeLab(input, config, task, previous, (stage) =>
        self.postMessage({ id, stage }),
      ),
    });
  } catch (error) {
    self.postMessage({ id, error: (error as Error).message });
  }
};
