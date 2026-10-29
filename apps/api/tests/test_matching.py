from app.matching import best_pairs


def test_best_pairs_keeps_negative_benefit_over_leaving_empty() -> None:
    assert best_pairs({("L1", "V1"): -19_117_60}) == [("L1", "V1")]


def test_best_pairs_prefers_less_negative_and_positive_total() -> None:
    chosen = best_pairs(
        {
            ("L1", "V1"): -100,
            ("L1", "V2"): -50,
            ("L2", "V1"): 10,
            ("L2", "V2"): -200,
        }
    )
    assert set(chosen) == {("L1", "V2"), ("L2", "V1")}
