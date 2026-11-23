"""V3.7.40 complete source-module census for historical PL5 research.

An inventory is NOT a claim that every module is an interchangeable filter.
Classify every Python module on the current branch, preserve source digests,
and fail loudly if any module is not assigned a research role.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json

SCHEMA = "pl5-legacy-method-census-v3740-1"
# These sets describe intended execution roles, not efficacy rankings.
CATEGORIES = {
    "candidate_filters": """
        basic_filters basic_filter_catalog_v3716 pattern_rules multispace
        nine_spaces_v24 space_mapping digit_structure_v3737
        affine_recurrence_filters_v3739 nca_v36 sculpting
        probability_ranker engine
    """,
    "combination_optimizers": """
        ga_cs_optimizer_v3715 constraint_portfolio_v3731
        filter_equivalent_pruning_v3735 filter_irredundant_pruning_v3736
        filter_interactions_v3734 filter_search_oracle_v3732
        filter_search_suite_v3733 dsc_portfolio_audit_v3738
        prequential_portfolio_audit_v3730 high_throughput_v3714
        ablation_search_v373 ablation_benchmark_v373 ablation_statistics_v373
        codebook_v3713 covering_arrays_v3713 dynamic_budget_v3713
        conformal_audit_v3713
    """,
    "mathematical_operator_research": """
        adaptive_primitives_v379 adaptive_study_v379 autolift_v28
        bcse_v27 category_hypotheses_v32 coupled_primitives_v378
        coupled_study_v378 cross_task_v3711 generated_primitives_v3710
        generated_study_v3710 gate_induction_v3726
        grammar_discovery_v3724 highdim_v26 language_evolution_v3722
        latent_primitives_v377 math_discovery_v3720 math_language_v37
        meta_operator_v3721 open_grammar_v3725
        operator_evolution_v371 operator_metalearning_v33
        primitive_categories_v31 primitive_invention_v29
        primitive_study_v377 representation_v25 representation_registry_v25
        structure_ast_v372 structure_evidence_v372 structure_search_v372
        symbolic_operators_v30 transfer_evolution_v34 transfer_language_v3723
        transfer_study_v3711 template_study_v3712 template_transfer_v3712
        shift_windows_v3712
    """,
    "historical_evaluation_and_evidence": """
        backtest filter_validation_v35 forward_sculpt_v152
        official_dataset_v3719 prospective_validation_v3719
        research_validation_v3719 timestamp_evidence_v3719
        mapping_robustness research_agent autonomous_v374
        scientific_methods_v376 scientific_questions_v375
        scientific_runtime_v375 scientific_runtime_v376 evolution_v15
        discovery
    """,
    "infrastructure": """
        __init__ agents algorithm_registry_v14 ability_lab_v19
        capability_network data github_rule_parity hdse_registry_v26
        integration_bridge knowledge number_validation parameter_hub_v34
        sources value_center_v16 legacy_method_census_v3740 legacy_filter_matrix_v3740
    """,
}
CATALOG = {word: group for group, names in CATEGORIES.items()
           for word in names.split()}
DIRECTLY_MEASURABLE = {
    "basic_filters", "pattern_rules", "space_mapping", "digit_structure_v3737",
    "affine_recurrence_filters_v3739", "multispace", "engine"
}
REQUIRES_HISTORY = {"pattern_rules", "multispace", "engine", "probability_ranker",
                    "nca_v36", "backtest", "research_validation_v3719"}
REQUIRES_EXTERNAL = {"nca_v36", "official_dataset_v3719", "prospective_validation_v3719"}


def inventory(root: Path | None = None) -> dict:
    """Every source module has a unique category; unregistered files block."""
    root = Path(root) if root is not None else Path(__file__).resolve().parent
    modules = sorted(p for p in root.glob("*.py") if p.is_file())
    actual = {p.stem for p in modules}
    unknown = sorted(actual - set(CATALOG))
    stale = sorted(set(CATALOG) - actual)
    if unknown or stale or len(CATALOG) != sum(len(s.split()) for s in CATEGORIES.values()):
        raise ValueError(f"unclassified={unknown}; stale_or_duplicate={stale}")
    tests = root.parent / "tests"
    test_files = sorted(p for p in tests.glob("test_*.py") if p.is_file())
    rows = []
    for p in modules:
        name = p.stem
        rows.append({
            "name": name, "role": CATALOG[name],
            "source_path": f"pailie5/{p.name}",
            "source_sha256": sha256(p.read_bytes()).hexdigest(),
            "direct_mask_adapter_in_v3740": name in DIRECTLY_MEASURABLE,
            "history_context_required": name in REQUIRES_HISTORY,
            "external_data_or_custody_required": name in REQUIRES_EXTERNAL,
            "scope": ("FILTER_FAMILY_OR_ADAPTER" if name in DIRECTLY_MEASURABLE
                      else "RESEARCH_COMPONENT_NOT_DIRECT_COMPARABLE_MASK"),
        })
    return {
        "schema": SCHEMA, "tracked_package_modules": len(rows),
        "tracked_test_files": len(test_files),
        "source_rows": rows,
        "test_file_names": [p.name for p in test_files],
        "missing_registration": [],
        "historical_actual_records_checked": False,
        "meaning_of_test_file_count": "DISCOVERED_TEST_FILES_NOT_CLAIM_OF_PASS",
        "interpretation": [
            "A module may be an optimizer, audit tool, grammar, or infrastructure, not a stand-alone filter.",
            "Source digests bind one currently checked-out Git snapshot; they do not change source history.",
            "Direct filter effect is measured separately and never inferred from presence of a Python module.",
        ],
    }
