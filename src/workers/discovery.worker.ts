/// <reference lib="webworker" />
import { analyzeDiscovery, walkDiscovery } from "../domain/discovery/engine";
self.onmessage = (e) => {
  const { id, input, config, rolling } = e.data;
  try {
    const progress = (stage: string) => self.postMessage({ id, stage });
    self.postMessage({
      id,
      result: rolling
        ? walkDiscovery(input, config, progress)
        : analyzeDiscovery(input, config, progress),
    });
  } catch (error) {
    self.postMessage({ id, error: (error as Error).message });
  }
};
