import { selectPortfolio, replaySelection } from "../domain/selection/engine";
import type { FilterInput } from "../domain/pick5";
import type { SelectionConfig } from "../domain/selection/config";
self.onmessage = (
  event: MessageEvent<{
    id: number;
    input: FilterInput;
    config: SelectionConfig;
    task?: "select" | "replay";
  }>,
) => {
  const { id, input, config, task } = event.data;
  try {
    if (task === "replay") {
      const replay = replaySelection(input, config, (stage) =>
        self.postMessage({ id, stage }),
      );
      self.postMessage({ id, replay });
      return;
    }
    const result = selectPortfolio(input, config, (stage) =>
      self.postMessage({ id, stage }),
    );
    self.postMessage({ id, result });
  } catch (e) {
    self.postMessage({
      id,
      error: e instanceof Error ? e.message : "精选计算失败",
    });
  }
};
