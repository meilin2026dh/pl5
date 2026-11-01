import type { HistoryRecord } from "../pick5";
import {
  fitModel,
  kinds,
  priors,
  probability,
  updateModel,
  softmax,
  type JointModel,
} from "./models";
export type OnlinePoint = {
  issue: string;
  weights: number[];
  probabilities: number[];
  loss: number;
  mixtureLoss: number;
  expertLoss: number[];
  regret: number;
  bound: number;
};
export type OnlineState = {
  version: "probability-online-v1";
  source: string;
  strength: number;
  training: HistoryRecord[];
  consumed: HistoryRecord[];
  models: JointModel[];
  logs: number[];
  trace: OnlinePoint[];
  mixtureLoss: number;
  expertLoss: number[];
};
export function onlineReplay(
  training: HistoryRecord[],
  later: HistoryRecord[],
  strength: number,
  source: string,
  previous?: OnlineState,
) {
  // Cache identity uses complete records. Canonical replay avoids trusting stored/imported weights.
  const same =
    previous?.version === "probability-online-v1" &&
    previous.source === source &&
    previous.strength === strength &&
    JSON.stringify(previous.training) === JSON.stringify(training) &&
    previous.consumed.length <= later.length &&
    JSON.stringify(previous.consumed) ===
      JSON.stringify(later.slice(0, previous.consumed.length));
  const rebuilt = !!previous && !same;
  const models = kinds.map((k) => fitModel(k, training, strength)),
    logs = priors.map(Math.log),
    trace: OnlinePoint[] = [],
    expertLoss = kinds.map(() => 0);
  let mixtureLoss = 0;
  for (const row of later) {
    const weights = softmax(logs),
      ps = models.map((m) => probability(m, row.number)),
      q = ps.reduce((a, p, i) => a + p * weights[i], 0),
      loss = -Math.log(q);
    mixtureLoss += loss;
    ps.forEach((p, i) => {
      const l = -Math.log(p);
      expertLoss[i] += l;
      logs[i] -= l;
      updateModel(models[i], row.number);
    });
    const best = expertLoss.indexOf(Math.min(...expertLoss));
    trace.push({
      issue: row.issue,
      weights,
      probabilities: ps,
      loss,
      mixtureLoss,
      expertLoss: [...expertLoss],
      regret: mixtureLoss - expertLoss[best],
      bound: -Math.log(priors[best]),
    });
  }
  const last = trace.at(-1),
    state: OnlineState = {
      version: "probability-online-v1",
      source,
      strength,
      training,
      consumed: later,
      models,
      logs,
      trace,
      mixtureLoss,
      expertLoss,
    };
  return {
    trace,
    regret: last?.regret ?? 0,
    bound: last?.bound ?? Math.log(6),
    weights: softmax(logs),
    rebuilt,
    verifiedPrefix: same ? previous!.consumed.length : 0,
    state,
  };
}
