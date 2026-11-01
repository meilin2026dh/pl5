import { it, expect, vi, afterEach } from "vitest";
import { defaultPositions } from "../src/domain/pick5";
afterEach(() => {
  vi.unstubAllGlobals();
  vi.resetModules();
});
it("routes replay and filter messages through real algorithms and returns identifiable errors", async () => {
  const transport = {
    postMessage: vi.fn(),
    onmessage: null as null | ((event: any) => void),
  };
  vi.stubGlobal("self", transport);
  await import("../src/workers/filter.worker");
  transport.onmessage!({
    data: {
      requestId: 7,
      operation: "backtest",
      count: 1,
      input: {
        positions: defaultPositions(),
        rules: [],
        history: [{ issue: "1", date: "2026-01-01", number: "00000" }],
      },
    },
  });
  expect(transport.postMessage.mock.calls[0][0]).toMatchObject({
    requestId: 7,
    rows: [{ number: "00000", status: "retained" }],
  });
  transport.onmessage!({
    data: {
      requestId: 8,
      input: {
        positions: defaultPositions(),
        rules: [],
        candidates: ["00127"],
      },
    },
  });
  expect(transport.postMessage.mock.calls[1][0]).toMatchObject({
    requestId: 8,
    result: { numbers: ["00127"] },
  });
  transport.onmessage!({
    data: {
      requestId: 9,
      operation: "backtest",
      count: 0,
      input: { positions: defaultPositions(), rules: [] },
    },
  });
  expect(transport.postMessage.mock.calls[2][0]).toMatchObject({
    requestId: 9,
    error: expect.stringContaining("回放范围"),
  });
});
