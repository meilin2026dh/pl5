import { backtest } from "../domain/backtest";
import { filter, type FilterInput } from "../domain/pick5";
self.onmessage = (
  event: MessageEvent<{
    requestId: number;
    input: FilterInput;
    operation?: "backtest";
    count?: number;
  }>,
) => {
  const { requestId, input } = event.data;
  try {
    if (event.data.operation === "backtest")
      self.postMessage({
        requestId,
        rows: backtest(input, event.data.count ?? 30),
      });
    else self.postMessage({ requestId, result: filter(input) });
  } catch (e) {
    self.postMessage({
      requestId,
      error: e instanceof Error ? e.message : "计算失败，请重试",
    });
  }
};
