import { filter, type FilterInput } from "../domain/pick5";
self.onmessage = (
  event: MessageEvent<{ requestId: number; input: FilterInput }>,
) => {
  const { requestId, input } = event.data;
  try {
    self.postMessage({ requestId, result: filter(input) });
  } catch (e) {
    self.postMessage({
      requestId,
      error: e instanceof Error ? e.message : "计算失败，请重试",
    });
  }
};
