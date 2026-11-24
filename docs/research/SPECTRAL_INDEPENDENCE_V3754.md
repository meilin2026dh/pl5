# V3.7.54 — Five-digit discrete-spectrum filtering and independent contribution

## Frozen falsifiable hypothesis
A five-point discrete Fourier transform (DFT) of each five-digit tuple may produce a **binary spectral KEEP rule** not expressible by (a) the existing **58 frozen V3.7.40 static Boolean rules**, nor (b) those 58 plus the nine **predeclared V3.7.51 modular and prime-factor binary rules**. An absence of distinguishing pairs is a valid negative result and must be kept.

The single rule is frozen **before** any outcome evaluation:

> KEEP a five-digit tuple if the squared DFT magnitude at frequency 1 exceeds that at frequency 2.

No thresholds are searched and no training/history is read.

## Exact integer spectral derivation

Write `d_0,...,d_4` for the decimal digits (including leading zero), `F_k = sum_{j=0}^4 d_j exp(-2πikj/5)`, and cyclic autocorrelations `C_l = sum_j d_j d_(j+l mod 5)` for `l = 0,1,2`.

Then the two nontrivial squared spectral magnitudes are, exactly,

`|F_1|² = (2 C_0 - C_1 - C_2 + sqrt(5)(C_1 - C_2))/2`,

`|F_2|² = (2 C_0 - C_1 - C_2 - sqrt(5)(C_1 - C_2))/2`.

Consequently **`|F_1|² > |F_2|²` if and only if `C_1 > C_2`**. The implementation evaluates the integer expression only; it neither rounds spectral magnitudes nor relies on platform floating-point comparisons. Independent numerical complex-DFT oracles validate both identities on a predeclared grid of examples.

## Exact independent-contribution method
Read the 58 original static masks from the **same V3.7.40 registered adapter functions** as the prior audit. Refuse a changed manifest SHA256. Group every one of 100000 IDs by the original 58-bit signature; then separately group by 58 plus the nine existing binary number-theoretic predicates (mod 2,3,5,7,11,13 residue 0; distinct factor count ≥3, total factor count ≥3, squarefree=1).

Within every old equivalence class, count pairs split by (i) the full exact algebraic spectral feature `(2C0-C1-C2, C1-C2)` and (ii) the **single predeclared binary KEEP rule**. A positive split-pair count plus an independently checked same-signature/opposite-spectral-keep witness proves the binary rule is not a Boolean expression over that frozen old catalog. Zero proves an exact negative result.

Also report standalone retained identities, the existing V3.7.39 100-member recurrence baseline intersection, and the 58-rule full-intersection marginal. Empty intersections are never a valid successful nonempty compression.

## Reproduce

```sh
python docs/research/experiments/spectral_independence_v3754.py
```

The executable runs three checks: independent numerical DFT reference, exact full-domain old-rule signature refinement with witness oracle, and a hand-enumerated small equivalence-class oracle. It prints a JSON evidence record `V3754_SPECTRAL_JSON` only after tests pass.

## Verification limits
- This is one bounded **INTERNAL/AI_AUTHORED** fixed-rule experiment. Prior tests are development, not external independent acceptance.
- Structural Boolean novelty does not prove improved historical coverage, historical deletion rate, execution speed, or useful candidate set compression.
- 58 static masks and nine frozen number-theoretic binary rules are checked; dynamic and time-dependent engines are outside this proof.
- Subset comparisons are exact finite-domain arithmetic; there is no time-forward history or equal-budget outcome benchmark here.
- New GitHub Actions matrix must pass on **Windows and Ubuntu for the exact tested source SHA**. Application checks and complete regression remain separate gates.
- Production rule inventory, `main`, preexisting historical data, hashes, and private inputs are unchanged. Draft only; no merge.
