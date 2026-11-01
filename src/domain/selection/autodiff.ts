export type Vector = { v: number[]; g: Float64Array; back: () => void };
export class Tape {
  nodes: Vector[] = [];
  parameters: { offset: number; node: Vector }[] = [];
  node(v: number[], back?: (n: Vector) => void) {
    const n: Vector = {
      v,
      g: new Float64Array(v.length),
      back: () => back?.(n),
    };
    this.nodes.push(n);
    return n;
  }
  constant(v: number[]) {
    return this.node(v);
  }
  param(w: Float64Array, offset: number, n: number) {
    const existing = this.parameters.find((p) => p.offset === offset);
    if (existing) return existing.node;
    const node = this.node(Array.from(w.slice(offset, offset + n)));
    this.parameters.push({ offset, node });
    return node;
  }
  add(a: Vector, b: Vector) {
    return this.node(
      a.v.map((x, i) => x + b.v[i]),
      (n) =>
        n.g.forEach((g, i) => {
          a.g[i] += g;
          b.g[i] += g;
        }),
    );
  }
  mul(a: Vector, b: Vector) {
    return this.node(
      a.v.map((x, i) => x * b.v[i]),
      (n) =>
        n.g.forEach((g, i) => {
          a.g[i] += g * b.v[i];
          b.g[i] += g * a.v[i];
        }),
    );
  }
  activate(a: Vector, kind: "tanh" | "sigmoid") {
    const v = a.v.map((x) =>
      kind === "tanh" ? Math.tanh(x) : 1 / (1 + Math.exp(-x)),
    );
    return this.node(v, (n) =>
      n.g.forEach(
        (g, i) =>
          (a.g[i] +=
            g * (kind === "tanh" ? 1 - v[i] * v[i] : v[i] * (1 - v[i]))),
      ),
    );
  }
  slice(a: Vector, start: number, n: number) {
    return this.node(a.v.slice(start, start + n), (r) =>
      r.g.forEach((g, i) => (a.g[start + i] += g)),
    );
  }
  concat(a: Vector, b: Vector) {
    return this.node(a.v.concat(b.v), (n) => {
      a.g.forEach((_, i) => (a.g[i] += n.g[i]));
      b.g.forEach((_, i) => (b.g[i] += n.g[i + a.v.length]));
    });
  }
  embedding(e: Vector, d: number) {
    return this.slice(e, d * 4, 4);
  }
  affine(x: Vector, w: Vector, b: Vector) {
    const input = x.v.length,
      out = w.v.length / input,
      v = Array.from({ length: out }, (_, o) =>
        x.v.reduce((s, a, i) => s + a * w.v[o * input + i], b.v[o] ?? 0),
      );
    return this.node(v, (n) =>
      n.g.forEach((g, o) => {
        if (o < b.g.length) b.g[o] += g;
        x.g.forEach((_, i) => {
          x.g[i] += g * w.v[o * input + i];
          w.g[o * input + i] += g * x.v[i];
        });
      }),
    );
  }
  softmax(x: Vector) {
    const m = Math.max(...x.v),
      e = x.v.map((v) => Math.exp(v - m)),
      s = e.reduce((a, b) => a + b, 0),
      v = e.map((a) => a / s);
    return this.node(v, (n) => {
      const dot = v.reduce((s, p, i) => s + p * n.g[i], 0);
      x.g.forEach((_, i) => (x.g[i] += v[i] * (n.g[i] - dot)));
    });
  }
  norm(x: Vector, gain: Vector, bias: Vector) {
    const N = x.v.length,
      mean = x.v.reduce((a, b) => a + b, 0) / N,
      sd = Math.sqrt(x.v.reduce((s, a) => s + (a - mean) ** 2, 0) / N + 1e-5),
      hat = x.v.map((a) => (a - mean) / sd);
    return this.node(
      hat.map((h, i) => h * gain.v[i] + bias.v[i]),
      (n) => {
        const gh = hat.map((_, i) => n.g[i] * gain.v[i]),
          sum = gh.reduce((a, b) => a + b, 0),
          dot = gh.reduce((s, a, i) => s + a * hat[i], 0);
        x.g.forEach((_, i) => {
          x.g[i] += (N * gh[i] - sum - hat[i] * dot) / (N * sd);
          gain.g[i] += n.g[i] * hat[i];
          bias.g[i] += n.g[i];
        });
      },
    );
  }
  attention(q: Vector, keys: Vector[], values: Vector[]) {
    const scores = this.node(
        keys.map((k) => k.v.reduce((s, a, i) => s + a * q.v[i], 0) / 2),
        (n) =>
          n.g.forEach((g, j) => {
            q.g.forEach((_, i) => {
              q.g[i] += (g * keys[j].v[i]) / 2;
              keys[j].g[i] += (g * q.v[i]) / 2;
            });
          }),
      ),
      weights = this.softmax(scores),
      out = this.node(
        q.v.map((_, i) =>
          values.reduce((s, v, j) => s + weights.v[j] * v.v[i], 0),
        ),
        (n) =>
          values.forEach((v, j) => {
            weights.g[j] += n.g.reduce((s, g, i) => s + g * v.v[i], 0);
            v.g.forEach((_, i) => (v.g[i] += n.g[i] * weights.v[j]));
          }),
      );
    return { out, weights };
  }
  backward(output: Vector, target: number, size: number) {
    const probs = this.softmax(output),
      loss = -Math.log(Math.max(1e-300, probs.v[target]));
    output.g.set(probs.v.map((p, i) => p - Number(i === target)));
    for (let i = this.nodes.indexOf(output); i >= 0; i--) this.nodes[i].back();
    const gradient = new Float64Array(size);
    for (const p of this.parameters)
      p.node.g.forEach((g, i) => (gradient[p.offset + i] += g));
    return { loss, gradient, probabilities: probs.v };
  }
}
