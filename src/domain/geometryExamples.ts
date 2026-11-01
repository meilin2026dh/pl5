import {
  prepareGeometry,
  type GeometryConfig,
  type GeometryMethod,
} from "./geometry";
import type { HistoryRecord } from "./pick5";
/** Examples are display-only; every generated number is checked by the actual predicate. */
export function geometryExample(
  c: GeometryConfig,
  history?: HistoryRecord[],
): string | null {
  try {
    const prepared = prepareGeometry(c, history);
    const keypad = c.layout !== "trend";
    const preferred: Record<GeometryMethod, string> = {
      line: keypad ? "14741" : "13579",
      polyline: "11235",
      v:
        c.layout === "phone"
          ? "14863"
          : c.layout === "calculator"
            ? "74269"
            : "95159",
      invertedV:
        c.layout === "phone"
          ? "74269"
          : c.layout === "calculator"
            ? "14863"
            : "15951",
      arithmetic: "13579",
      geometric: "12489",
      fibonacci: "11235",
      triangle: keypad ? "13713" : "00100",
      trapezoid: keypad ? "13971" : "00110",
      mirror: keypad ? "13579" : "13531",
      central: "13579",
    };
    if (c.source === "history") {
      // Only this position affects a historical continuation: exhaust its ten possible digits.
      for (let d = 0; d < 10; d++) {
        const number = "00000".split("");
        number[c.position] = String(d);
        if (prepared.test(number.join(""))) return number.join("");
      }
      return null;
    }
    const fill = (path: string) =>
      "0".repeat(c.position) + path + "0".repeat(5 - c.position - c.length);
    const candidate = fill(preferred[c.method].slice(0, c.length));
    if (prepared.test(candidate)) return candidate;
    if (c.method === "trapezoid" && c.length < 4) return null;
    if (
      c.method === "geometric" &&
      c.sequence === "digits" &&
      c.length === 5 &&
      c.tolerance === 0
    )
      return null;
    for (let n = 0; n < 10 ** c.length; n++) {
      const number = fill(String(n).padStart(c.length, "0"));
      if (prepared.test(number)) return number;
    }
    return null;
  } catch {
    return null;
  }
}
