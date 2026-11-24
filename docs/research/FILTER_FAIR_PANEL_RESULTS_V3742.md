# PL5 V3.7.42 actual two-stage fair-filter panel result

## Source, scope and technical gates

The implemented experiment reuses three **existing PL5 methods** with an
identical **K=100** candidate budget. It is an entirely internal
proof-of-mechanism using the repository's explicitly synthetic
`data/synthetic_demo.csv` fixture, not an authenticated historical
study or a public third-party timestamp.

Latest tested implementation commit:
`a4947bb06023b8d3e5d9cd5f30aac7f5e37980c0`.

[GitHub Actions workflow #45221543040](https://github.com/meilin2026dh/pl5/actions/runs/45221543040):

| Independent job | Actual conclusion |
|---|---|
| Ubuntu / Python 3.12 contract tests | **12 passed** |
| Windows / Python 3.12 contract tests | **12 passed** |
| `freeze-first`: snapshot and upload frozen panel | **success** |
| `evaluate-later`: download frozen bytes and verify one row | **success** |

The `evaluate-later` job was dependent on completion of the first job
and both OS test jobs; the observed synthetic record was never an
argument to the `freeze` CLI. This proves an inspectable **two-stage
software execution path** under GitHub Actions, not externally trusted
event chronology.

The workflow uploaded frozen panel plus evaluation JSON to artifact
`v3742-sealed-filter-evaluation-45221543040`. Downloaded and inspected
the archive independently:

- Frozen JSON exact SHA256:
  `8fecb07059f22717382d35da4e09eb397b8d187ced1589147ff0e02e99233150`
- Canonical frozen *payload* SHA256:
  `54695121d4f2f63fbf6b97ba84908dddae68409c64c1afc471e9e3da109b04c1`
- Evaluation JSON exact SHA256:
  `5a4344f2c9b16c87618dc1def176aa2e1482ce00bc46fef212d7fee9640bbd44`
- Last training issue: `000041`
- Reserved synthetic evaluation issue: `000042`
- Full candidate lists, source-code-byte hashes and configuration hashes
  were preserved inside the frozen JSON.

## Same-budget experiment outcomes

| Frozen filtering method | Candidate identities kept | Synthetic record contained |
|---|---:|---|
| Original position-statistics adapter | 100 | No |
| Existing V3.7.39 modular-recurrence structure | 100 | No |
| Uniform seeded baseline | 100 | No |

All three retained exactly **100/100000** candidate identities
(0.1% of the full space) using different fixed sets. For a single
synthetic record, three negative membership results do **not** rank
the methods. The test objective was governance: demonstrate identical
K, separation of phases, complete membership preservation, and
consistent reproducible verification.

The record explicitly reports:

- `source_classification=INTERNAL_SYNTHETIC`
- `source_identity_authenticated_by_this_module=false`
- `external_timestamp_attested=false`
- `full_candidate_memberships_verified=true`
- `statistical_significance_evaluated=false`

## Known limitations

The SHA256 digest protects file content against undetected edits
without recomputing hashes. It does not prevent a privileged actor
from replacing both the content and its hash, and does not prove when
a record was first published. GitHub Actions schedules are not
strong timing guarantees. The original upstream application has a
reusable staged workflow idea but is not copied into this repo.

**A real operating fair-comparison platform requires** independently
authenticated data, an independent publication-timing attestation, a
durable append-only chain under controlled identity/custody, and
sufficiently large multi-window comparisons including all earlier
compatible filtering methods. This PR is an accepted *software
mechanism* once CI completes, not a scientific claim from one held-out
synthetic row.

No private data or old source hashes were changed; `main` was not
modified. The separate full clean-machine Python workflow remains
an independent merge gate.
