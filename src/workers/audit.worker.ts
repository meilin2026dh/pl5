import { analyzeConditions } from "../domain/audit/engine";
import type { FilterInput } from "../domain/pick5";
import type { AuditConfig } from "../domain/audit/config";
self.onmessage = (
  event: MessageEvent<{
    id: number;
    input: FilterInput;
    config: AuditConfig;
    walk: boolean;
  }>,
) => {
  const { id, input, config, walk } = event.data;
  try {
    const result = analyzeConditions(input, config, walk, (stage) =>
      self.postMessage({ id, stage }),
    );
    self.postMessage({ id, result });
  } catch (e) {
    self.postMessage({ id, error: (e as Error).message });
  }
};
