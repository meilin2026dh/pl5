# V3.7.52 — conditional complementarity and exact subset certificate

## Single frozen research question
Do the nine V3.7.51 binary filtering rules provide information that is mutually nonredundant **after conditioning on all 58 frozen V3.7.40 static masks**? Individual independence relative to the old library does not imply mutual independence. This experiment measures exact structural pair separation, not candidate-set compression or historical coverage.

## Mathematical certificate
Group the 100000 candidate IDs by the complete old 58-bit decision vector. Within each group, encode the nine new rule outputs in a 9-bit signature. For every unordered pair in that group, form the XOR difference pattern D. Let h(D) count pairs with that pattern. Then for any subset S of the nine new rules,

    v(S) = sum_{D : D & S != 0} h(D).

The identity follows because at least one chosen rule distinguishes the pair exactly when the difference pattern intersects S. A subset zeta transform computes all 512 values exactly. An independent direct regrouping calculation checks every one. Since v is monotone and measures a set union, equal value to the full set certifies an identical refinement of the old equivalence partition. Exhaustive enumeration certifies the smallest equivalent subset and best subsets at every fixed number of new rules.

The exact leave-one-out contribution of rule i is h(1<<i). A nonzero count has a concrete witness pair independently rechecked using the original 58 masks and trial division. Shapley contribution is sum h(D)/popcount(D) over patterns containing i: each pair is credited equally among its distinguishing rules. Rational arithmetic preserves exact total credit. This is conditional pair-separation Shapley, not exclusion-set Shapley or measured execution cost.

## Frozen inputs and controls
- Parent: V3.7.51 documentation and tested implementation at bac3d7adf5028ddac8efe06f31f0e95e7a4dc466.
- Recompile existing registered static masks and fail closed unless manifest SHA256 matches V3.7.51.
- Reuse the same six divisibility predicates and three prime-factor predicates, without new thresholds or fitting.
- Verify all nine singleton values against the preceding experiment, conservation of pair counts, exact Shapley total, independent direct regrouping for all subsets, and explicit duplicate/zero-rule controls.
- All data are INTERNAL/AI_AUTHORED finite-domain structural inputs. Dynamic rules are excluded, no historical records used, no new production rules selected.

## Reproduce
From repository root:

    python docs/research/experiments/conditional_complementarity_v3752.py

The program runs three unittest cases then emits V3752_COMPLEMENTARITY_JSON including all 512 subset values, XOR histogram, exact rational credits, conditional exclusive witnesses, and cardinality frontier. Windows and Ubuntu Python 3.12 focused CI. Cross-platform acceptance requires successful CI on the code commit. No changes to main, source data or historical hashes, and no automatic merge.
