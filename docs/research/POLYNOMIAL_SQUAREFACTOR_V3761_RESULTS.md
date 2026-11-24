# V3.7.61 — finite-field square-factor filter acceptance record

Date: 2026-11-24. Scope: static filter independence and cross-platform reproducibility. INTERNAL/AI_AUTHORED.

## Frozen hypothesis and result

The nonzero polynomial with a repeated irreducible factor over F3, using five decimal digits in ascending coefficient order, must split at least one equivalence class of the existing 69 frozen binary filter rules to qualify as a new static descriptor. The rule is fixed independently of historical records.

The Euclidean algorithm and independent enumeration of squares of monic irreducible factors (degree 1 or 2) agree on all 243 residue vectors and all 100,000 decimal combinations.

| Metric | Exact result |
|---|---:|
| Accepted residue vectors | 78/243 |
| Standalone retained K | 34,488 |
| Standalone compression | 65.512% |
| Prior static equivalence classes | 93,568 |
| Refined classes | 94,966 |
| Split prior classes | 1,398 |
| Previously indistinguishable unordered pairs | 33,791 |
| Newly distinguished pairs | 13,600 |
| Remaining indistinguishable pairs | 20,191 |
| Reduction of indistinguishable pairs | 40.2474% |
| Small-class diagnostic union, 11 mathematical rules | 9,230 |
| Small-class diagnostic union, 12 mathematical rules | 16,244 |

Witness: 01150 and 03350 have identical outputs on all 69 prior masks but differ under the new rule. Since any Boolean combination of the prior masks is constant on each old equivalence class, this is an exact non-redundancy certificate relative to the frozen manifest, not a claim of global mathematical originality.

The small-class union increases by 7,014 candidates, but is not itself a candidate set satisfying K<=100. No historical backtracking coverage or historical false-exclusion measurement was performed. Static novelty does not establish utility for a specific selection policy, and no production adoption is justified by this experiment alone.

## Evidence and test commands

- Tested commit: `a62426678e4bf502094cf8fabb4a703f5fdc9ffe`; source commit: `e303cf46243dca77053e734d66b237b727f90373`.
- Reproduce: `python docs/research/experiments/polynomial_squarefactor_v3761.py`.
- [Targeted CI #45349927574](https://github.com/meilin2026dh/pl5/actions/runs/45349927574): Ubuntu and Windows both passed three tests. The complete JSON strings are byte-identical, including frozen mask digests.
- [Application CI #45349927504](https://github.com/meilin2026dh/pl5/actions/runs/45349927504): success on the tested commit. Earlier application timeout remains part of failure history, not erased.
- main verified at `c0e38040ec5f389d6444e64b90e7adc42adfca62`; PR #11 at `b5687f5e848d1fab567fcd15d8b1eb51d9e3b651` has 5/5 successful workflows; PR #13 at `53425be6a80533c219f097e023209776b3330f24` has 10/10 successful workflows. Issue #12 remains open. No source or historical data changes in this evidence commit; no merge.

Decision: accept V3.7.61 as an experimental static filter with demonstrated independent partition refinement, not as a validated historical coverage improvement. Preserve the full machine record below.

## Exact cross-platform machine record

```json
{
  "accepted_residue_vectors": 78,
  "baseline_manifest": [
    {
      "name": "legacy.adjacent_consecutive",
      "sha256": "4f35ad6c0596e096706bcbbe44391c42f02afdc271050e4cbdb100a716449b6f"
    },
    {
      "name": "legacy.adjacent_down",
      "sha256": "5cd9224bdaf6460a227401df720a60431b5a9cfcb939ca41e44461ac45dfb96d"
    },
    {
      "name": "legacy.adjacent_equal",
      "sha256": "0f931f78f8fdf43528477bc15dfdd9a41c91413c0bffa5fa2fd32ce38ddbac7c"
    },
    {
      "name": "legacy.adjacent_up",
      "sha256": "839099397c9008ffe99ef619624d1f6e70ba768e848b0dd677965b1630df64d9"
    },
    {
      "name": "legacy.digit_1",
      "sha256": "52161eccf4893b680ecdc59a678f2189f9a0d3a6aa3459bf1a2a56c56395b87c"
    },
    {
      "name": "legacy.digit_2",
      "sha256": "b3f4bffd0eb2eb23b756f4ef77f6dee97600a420ce4fdcd2f7471760717d365c"
    },
    {
      "name": "legacy.digit_3",
      "sha256": "911d25f8ac70dcdfebb9e162bc7d5fa8f3311e6f0d3b7314f085afbcd427de75"
    },
    {
      "name": "legacy.digit_4",
      "sha256": "89acafddba9b95b3bcf344c0d4407d661d2cd056b41bd7986f313a0e865574a4"
    },
    {
      "name": "legacy.digit_5",
      "sha256": "7c1b19a6298ab5abd639475983b1d3f7d9ef7e054cdeb56030040233ddebc4d0"
    },
    {
      "name": "legacy.even_position_sum",
      "sha256": "d8db33cd5fc45f9d6a36e43f26c1eec8ff8e10e25517e4c4302967ee1e48314a"
    },
    {
      "name": "legacy.first_last_gap",
      "sha256": "3d9f07ce7c2332fa89a85705f29fb299795b54fd584dc7415c1c3962514affbc"
    },
    {
      "name": "legacy.head_sum",
      "sha256": "d8defe7e495466d5923dc617ae7c0a56544244edc7f90d2aa0ffb822a4fea7bf"
    },
    {
      "name": "legacy.high_count",
      "sha256": "1bac36542da361fbe2208bc2d3afb630021119021ffd8c6664c322fcef69f096"
    },
    {
      "name": "legacy.inner_span",
      "sha256": "de5a7404a6c1b48507991bf2ea05a5252335c97eff12f64c6748d45bfc4b055c"
    },
    {
      "name": "legacy.max_frequency",
      "sha256": "d1695dd2fcf558fa0992183fe72fc724b32169960a1cf81f1450045361a85af6"
    },
    {
      "name": "legacy.middle_sum",
      "sha256": "c6380be1d77a78d3a01e34c8db8f84fe2c0a25ac9c778328daf7b809736c9398"
    },
    {
      "name": "legacy.mirror_pairs",
      "sha256": "4089698ecf2446db0b769c9ac9a0e9d022b8b1c4b55bcc9886530c2ec9a60cff"
    },
    {
      "name": "legacy.odd_count",
      "sha256": "cb8bc80d199937a556766eb432414406a37fd118e6018c286facc735f5654b87"
    },
    {
      "name": "legacy.odd_position_sum",
      "sha256": "9885a6533429bccf5f31feefba04f47a2358c5af63747ded40eb438262e6febb"
    },
    {
      "name": "legacy.pick23_6__consecutive_pairs",
      "sha256": "b1915fbb12697239b9e28b4c6518b5676ec857402429005a97fb6585be101092"
    },
    {
      "name": "legacy.pick23_6__first",
      "sha256": "c79300a4efb4e74d9586c7983eea9c54e6a5b10c5463975aa880b8c309bebce9"
    },
    {
      "name": "legacy.pick23_6__last",
      "sha256": "fe49c5ac230de78a14702e112646fccba27c6f571913d0e3d12281f00c6db272"
    },
    {
      "name": "legacy.pick23_6__lower_half_count",
      "sha256": "359de82063a01258627a74aaf3bc917f0decc367f32edd070b362811ca23f85b"
    },
    {
      "name": "legacy.pick23_6__max_gap",
      "sha256": "23b83e109a38069291bbef317562bd6cde1be6f2e635bf850f7ca61d7b9b5627"
    },
    {
      "name": "legacy.pick23_6__min_gap",
      "sha256": "bc8343880447df5c64d526aafac109e2cbdd2ea44d429aee3732732543f2b7b6"
    },
    {
      "name": "legacy.pick23_6__odd_count",
      "sha256": "02b59a1848f2da2427a94bfaaa2884dbc906156a02cc7708c447339fa96bc94f"
    },
    {
      "name": "legacy.pick23_6__span",
      "sha256": "5ab14ed64a146e3b823823fb6e4553dcb19f3da701d2beb98dc0132077952f10"
    },
    {
      "name": "legacy.pick23_6__sum",
      "sha256": "e9c623c2c35b5d79169b3cb79619c9bcabd4af7a5c6d4c4cb236b29c7833ee0c"
    },
    {
      "name": "legacy.pick41_4__consecutive_pairs",
      "sha256": "6cd712932519cb2427309d57412febb8347ff211a791d7cab1287170c1723a70"
    },
    {
      "name": "legacy.pick41_4__first",
      "sha256": "59701b1e7a90ec8a2df4b5ce1098a2c4fae56c9afee09e8326f8e0a559478161"
    },
    {
      "name": "legacy.pick41_4__last",
      "sha256": "f9951a7ac44028e276c7ff792e67a9b54d0de16e5fc363e27ba2f94ca839f7ef"
    },
    {
      "name": "legacy.pick41_4__lower_half_count",
      "sha256": "f0abe4d2e6916132be972ae105f3c640c562a9088823d2044d62c697ea6e146f"
    },
    {
      "name": "legacy.pick41_4__max_gap",
      "sha256": "8c010faf06508d797872d837dbc511aad33e0b69bc5c30c23427e3b1d4e901ec"
    },
    {
      "name": "legacy.pick41_4__min_gap",
      "sha256": "dd5c2684fbe59b5083b591257dd4488c2ade0426e3e2a66a4ee441025d44828f"
    },
    {
      "name": "legacy.pick41_4__odd_count",
      "sha256": "892abd8868bc014b4ce80ba5adc32d81765f4a59dc5a9303afa142d71f1d62d0"
    },
    {
      "name": "legacy.pick41_4__span",
      "sha256": "2c1484206d9860a1c8f02fd5a13f844953421fd0b9626f720dad3bc35a5953e8"
    },
    {
      "name": "legacy.pick41_4__sum",
      "sha256": "d9ba1b85569a2eb3dda9456b6bea1d6403aa8808048df60753e0421b9b6f269c"
    },
    {
      "name": "legacy.span",
      "sha256": "3c26cb43940e6271053c8528ec567b48fd1379143b8b8caf1ccc0d570353ab57"
    },
    {
      "name": "legacy.sum",
      "sha256": "6beeba693ff3aa8af75583b88ff7d4c1c069479250fc9231463f32f38f18205d"
    },
    {
      "name": "legacy.tail_sum",
      "sha256": "f7a0fbd362876422b7920a4c65b3eb94dcfe3867b249c2d2d5b55efa081ec3bf"
    },
    {
      "name": "legacy.ternary11__first_last_same",
      "sha256": "aa9221b5b1a848b0667085e7d9971669e46bed41b5aa14c8280657662178f2f8"
    },
    {
      "name": "legacy.ternary11__longest_run",
      "sha256": "a20a8fb99b33affdeeabe08d963e56cef30ea184f4b45ea7bd228c94a1fd54c8"
    },
    {
      "name": "legacy.ternary11__one_count",
      "sha256": "6c3fd65ad6411ee8998826225a951605d7d2722eead5f75e952880802dac28c5"
    },
    {
      "name": "legacy.ternary11__same_adjacent",
      "sha256": "2aa3bad6a447ce5f933df1c9796a3f23f09a387b56f08303bdb207cfd855cb44"
    },
    {
      "name": "legacy.ternary11__switch_count",
      "sha256": "2aa3bad6a447ce5f933df1c9796a3f23f09a387b56f08303bdb207cfd855cb44"
    },
    {
      "name": "legacy.ternary11__three_count",
      "sha256": "c9c04b3efdfc7dacc87293f9927ea2ed51be7024f5f0fcc10cb00c5bf07a77b2"
    },
    {
      "name": "legacy.ternary11__three_first_half",
      "sha256": "7e3dc6428259ce347bc707c0135f060e325e61a30b02c98fdf45a837531db1df"
    },
    {
      "name": "legacy.ternary11__weighted_sum",
      "sha256": "beaeace2cbf120dd060d023bf5b03fc1a3c41cb56932041d01a232ed2e8942c5"
    },
    {
      "name": "legacy.ternary11__zero_count",
      "sha256": "189ba21c57dc43ec22cae83c8e51d53536a5b06b2981c8ac1c1f0c46948fca5c"
    },
    {
      "name": "legacy.unique_count",
      "sha256": "c250021080ea7e9ce054e2b43ac3709f89a45b78c1b4f9f26789f83c20299524"
    },
    {
      "name": "dsc.exclude_mod10_arithmetic",
      "sha256": "7e25974f52b16f7dc5d777c29c9551f19b90d71834f1da25787252b19df1d9d3"
    },
    {
      "name": "dsc.exclude_exact_period2",
      "sha256": "e64d8f8ddd0dde5c00934affff99a9eec4376c678dac00c9171f52baed1c1946"
    },
    {
      "name": "dsc.exclude_low_delta_diversity",
      "sha256": "18e5c9880f0429c1914f6406b53084298e9973e5888d570966139692c7ece0ab"
    },
    {
      "name": "dsc.exclude_near_period2",
      "sha256": "457b4e68cfef0799b274a4664353a5aace8ab0fbf9638e2a018470cd840acb2d"
    },
    {
      "name": "dsc.exclude_mod10_arithmetic_duplicate",
      "sha256": "7e25974f52b16f7dc5d777c29c9551f19b90d71834f1da25787252b19df1d9d3"
    },
    {
      "name": "modular_recurrence.recurrence_d2_eq_d0_plus_d1_mod10",
      "sha256": "c6777d34f4536a1beafabff6e4b28deadfaf7722f4b9229bc8c0e1bc619b1963"
    },
    {
      "name": "modular_recurrence.recurrence_d3_eq_d1_plus_d2_mod10",
      "sha256": "f13489744bef0add18194efde5ab53d5b5971308f683366c2a84607fe524e799"
    },
    {
      "name": "modular_recurrence.recurrence_d4_eq_d2_plus_d3_mod10",
      "sha256": "911b87af0c97517c89c24616faf9faa2982e00960aa6c41487405e1fc911019a"
    },
    {
      "name": "mod2_zero",
      "sha256": "08a36d3e68efc65f25518ceb7e5d6257da1f65b90234a3af6667f04f478de880"
    },
    {
      "name": "mod3_zero",
      "sha256": "fdc130107904e8963650d35fcfcb37da457b154908afc038186e9bb14049b4eb"
    },
    {
      "name": "mod5_zero",
      "sha256": "a84402c183cef24981f911f3809d7624ddb34311b5aafaac9a17b272649aea48"
    },
    {
      "name": "mod7_zero",
      "sha256": "e69ff3ea78c61c5f028e1dc8cab9ddb9b7b062acbbaf72bf6eee633c5a00de53"
    },
    {
      "name": "mod11_zero",
      "sha256": "1d2db7b4757e9cd502ad7552a6db181dcafe5dadd78bb7ba16219cb18bd8af61"
    },
    {
      "name": "mod13_zero",
      "sha256": "182efc79462e0ee4f30e5dcc9b62880a33ccfe58f9a067d3fe7d19716f629fd3"
    },
    {
      "name": "omega_ge3",
      "sha256": "81f9a06309cc767642ce3537e88e287fc35f15365bc84ff28f57efaa675458ec"
    },
    {
      "name": "bigomega_ge3",
      "sha256": "c5100fc20864148c5dcf5c1a267f2c97c284819d3637ebecc0496a466f1ab075"
    },
    {
      "name": "squarefree_one",
      "sha256": "95e91457b62a786ef8fc85f78b153ab88b4c56f59789525fa9f3d5ac415c8214"
    },
    {
      "name": "spectral_C1_gt_C2",
      "sha256": "104a690fdb96ebfd10778f5a47c3f5c2be8930ab25b2cd1e67d637a5b409ee6d"
    },
    {
      "name": "det_H_gt_0",
      "sha256": "37df0bd077a846f9295b9ca70fc6301d5b5bd4c4e91a200ee7f50a2aa50cc300"
    }
  ],
  "baseline_rule_count": 69,
  "coefficient_order": "ascending degree from leftmost decimal digit",
  "domain": 100000,
  "eleven_rule_small_atom_union_k": 9230,
  "historical_coverage_measured": false,
  "modulus": 3,
  "new_classes": 94966,
  "old_classes": 93568,
  "practical_filter_value_proven": false,
  "remaining_indistinguishable_pairs": 20191,
  "residue_vectors": 243,
  "rule": "nonzero polynomial has repeated irreducible factor",
  "schema": "pl5-squarefactor-v3761-1",
  "small_atom_union_is_not_one_capped_filter": true,
  "source": "INTERNAL/AI_AUTHORED",
  "standalone_k": 34488,
  "standalone_sha256": "add6821f47298fa40d5be931593426c2eceabb87f7959619c002daf64c03b724",
  "static_independence": {
    "boolean_novelty_proven": true,
    "newly_distinguished_pairs": 13600,
    "old_indistinguishable_pairs": 33791,
    "split_old_classes": 1398,
    "witness_ids": [
      1150,
      3350
    ]
  },
  "twelve_rule_small_atom_union_k": 16244
}
```
