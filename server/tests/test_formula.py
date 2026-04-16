from server.app.services.risk_engine import Decision, RiskEngine, RiskInput


def test_dynamic_formula_weights_default() -> None:
    engine = RiskEngine()
    result = engine.apply_dynamic_formula(s_static=0.2, s_dev=0.8, c_match=0.0)
    assert abs(result - 0.38) < 1e-6


def test_dynamic_formula_tracks_c_match() -> None:
    engine = RiskEngine()
    low = engine.apply_dynamic_formula(s_static=0.1, s_dev=0.2, c_match=0.0)
    high = engine.apply_dynamic_formula(s_static=0.1, s_dev=0.9, c_match=1.0)
    assert high > low
    assert abs(high - 0.9) < 1e-6


def test_calculate_final_risk_uses_formula() -> None:
    engine = RiskEngine()
    final = engine._calculate_final_risk(
        flag_s=0.3,
        g_behavior=0.0,
        g_dynamic=0.7,
        hard_block=False,
        c_match=0.5,
    )
    expected = engine.apply_dynamic_formula(s_static=0.3, s_dev=0.7, c_match=0.5)
    assert abs(final - expected) < 1e-6


def test_hard_block_still_overrides_formula() -> None:
    engine = RiskEngine()
    result = engine._calculate_final_risk(
        flag_s=0.0,
        g_behavior=0.0,
        g_dynamic=0.0,
        hard_block=True,
        c_match=1.0,
    )
    assert result == 1.0


def test_mvp_thresholds_for_decision_routing() -> None:
    engine = RiskEngine()
    assert engine._resolve_decision(0.29) == Decision.PASS
    assert engine._resolve_decision(0.30) == Decision.INTERROGATE
    assert engine._resolve_decision(0.80) == Decision.INTERROGATE
    assert engine._resolve_decision(0.81) == Decision.BLOCK


def test_c_match_influences_assess_final_risk() -> None:
    engine = RiskEngine()
    base_input = RiskInput(
        payee_name="测试收款人",
        amount=6000,
        current_city="北京",
        is_known_payee=False,
        common_cities=["上海"],
        recent_transfer_count=0,
        recent_page="home",
        last_action="tap_transfer",
        semantic_summary="普通转账说明",
        classification_risk_level="medium",
        classification_category="异地大额异常转账",
        classification_block_hint=False,
        classification_keywords=["异地", "大额"],
        classification_scenarios=["remote_large_transfer"],
        c_match=0.2,
    )
    low_match_assessment = engine.assess(base_input)
    high_match_assessment = engine.assess(
        RiskInput(**{**base_input.__dict__, "c_match": 0.9})
    )

    # c_match 越高，f_final 越接近 s_dev；当 s_static > s_dev 时，风险分会下降。
    target_s_dev = high_match_assessment.g_dynamic
    high_gap = abs(high_match_assessment.final_risk - target_s_dev)
    low_gap = abs(low_match_assessment.final_risk - target_s_dev)

    assert high_gap < low_gap
