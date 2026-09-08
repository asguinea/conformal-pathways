from conformal_pathways.demo_oracle import demo_cases, evaluate_oracle_case


def test_demo_counts_and_oracle_safety() -> None:
    for workflow, sample_meta in demo_cases():
        result = evaluate_oracle_case(workflow, sample_meta)

        assert result.pathway_count == 18
        assert result.oracle_is_safe is True
