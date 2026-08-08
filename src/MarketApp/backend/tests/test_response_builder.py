from schemas.response import (
    ForecastCollection,
    ForecastPresentation,
    ForecastTrajectoryPoint,
    PredictionResponse,
)
from services.response_builder import ResponseBuilder


def _trajectory() -> list[ForecastTrajectoryPoint]:
    return [
        ForecastTrajectoryPoint(
            day=0,
            date="2026-07-30",
            price=100.0,
            expected_move_pct=0.0,
            confidence=50,
            confidence_level="CURRENT",
            recommendation="CURRENT",
            source="current",
        ),
        ForecastTrajectoryPoint(
            day=1,
            date="2026-07-31",
            price=102.0,
            expected_move_pct=2.0,
            confidence=70,
            confidence_level="MEDIUM",
            recommendation="BUY",
            source="model",
        ),
        ForecastTrajectoryPoint(
            day=2,
            date="2026-08-03",
            price=101.0,
            expected_move_pct=1.0,
            confidence=65,
            confidence_level="MEDIUM",
            recommendation="HOLD",
            source="model",
        ),
    ]


def test_build_forecast_collection_uses_calibrated_bounds() -> None:
    collection = ResponseBuilder.build_forecast_collection(
        expected_price=105.0,
        lower_price=101.0,
        upper_price=109.0,
        calibration={
            "method": "out_of_sample_return_residual_quantiles",
            "model_task": "return_forecast_h5",
            "model_version": "001",
            "horizon": 5,
            "lower_quantile": 0.10,
            "upper_quantile": 0.90,
            "intended_coverage": 0.80,
            "sample_count": 200,
            "calibration_start": "2024-01-01",
            "calibration_end": "2025-12-31",
            "generated_at": "2026-08-05T00:00:00+00:00",
        },
    )

    assert collection is not None
    assert collection.lowest_expected_price == 101.0
    assert collection.expected_price == 105.0
    assert collection.highest_expected_price == 109.0
    assert collection.calibration is not None
    assert collection.calibration.sample_count == 200


def test_build_forecast_collection_fails_closed_without_bounds() -> None:
    assert (
        ResponseBuilder.build_forecast_collection(
            expected_price=105.0,
        )
        is None
    )


def test_build_forecast_collection_rejects_invalid_ordering() -> None:
    assert (
        ResponseBuilder.build_forecast_collection(
            expected_price=105.0,
            lower_price=106.0,
            upper_price=109.0,
        )
        is None
    )


def test_build_forecast_collection_handles_missing_expected_price() -> None:
    assert (
        ResponseBuilder.build_forecast_collection(
            expected_price=None,
            lower_price=101.0,
            upper_price=109.0,
        )
        is None
    )


def test_build_prediction_response_preserves_existing_schema() -> None:
    trajectory = _trajectory()[:1]
    collection = ForecastCollection(
        lowest_expected_price=103.0,
        expected_price=105.0,
        highest_expected_price=107.0,
    )

    response = ResponseBuilder.build_prediction_response(
        ticker="AAPL",
        current_price=100.0,
        forecast_price=105.0,
        expected_move_pct=5.0,
        confidence=80,
        confidence_level="HIGH",
        horizon=5,
        recommendation="BUY",
        model="EnsembleDecisionEngine_h5",
        details_available=True,
        reasons=["Positive signal"],
        warnings=["Market risk"],
        explanation={"summary": "Test"},
        historical_confidence={"sample_size": 10},
        trajectory=trajectory,
        forecast_collection=collection,
    )

    assert isinstance(response, PredictionResponse)
    assert response.model_dump() == {
        "ticker": "AAPL",
        "current_price": 100.0,
        "forecast_price": 105.0,
        "expected_move_pct": 5.0,
        "confidence": 80,
        "confidence_level": "HIGH",
        "horizon": 5,
        "recommendation": "BUY",
        "model": "EnsembleDecisionEngine_h5",
        "details_available": True,
        "reasons": ["Positive signal"],
        "warnings": ["Market risk"],
        "explanation": {"summary": "Test"},
        "historical_confidence": {"sample_size": 10},
        "trajectory": [trajectory[0].model_dump()],
        "forecast_collection": collection.model_dump(),
        "forecast_presentation": None,
    }


def test_build_prediction_response_uses_independent_empty_lists() -> None:
    first = ResponseBuilder.build_prediction_response(
        ticker="AAPL",
        current_price=100.0,
        forecast_price=None,
        expected_move_pct=0.0,
        confidence=50,
        confidence_level="LOW",
        horizon=1,
        recommendation="HOLD",
        model="test",
        details_available=False,
    )
    second = ResponseBuilder.build_prediction_response(
        ticker="MSFT",
        current_price=200.0,
        forecast_price=None,
        expected_move_pct=0.0,
        confidence=50,
        confidence_level="LOW",
        horizon=1,
        recommendation="HOLD",
        model="test",
        details_available=False,
    )

    first.reasons.append("only-first")

    assert second.reasons == []
    assert second.warnings == []
    assert second.trajectory == []
    assert second.forecast_collection is None


def _full_forecast_collection() -> ForecastCollection:
    return ForecastCollection(
        lowest_expected_price=101.0,
        expected_price=105.0,
        highest_expected_price=108.0,
    )


def _build_authorized_response(
    authorization_context: dict[str, bool],
) -> PredictionResponse:
    return ResponseBuilder.build_prediction_response(
        ticker="AAPL",
        current_price=100.0,
        forecast_price=105.0,
        expected_move_pct=5.0,
        confidence=80,
        confidence_level="HIGH",
        horizon=5,
        recommendation="BUY",
        model="EnsembleDecisionEngine_h5",
        details_available=True,
        trajectory=_trajectory(),
        forecast_collection=_full_forecast_collection(),
        authorization_context=authorization_context,
    )


def test_explorer_receives_average_forecast_without_range() -> None:
    response = _build_authorized_response(
        {
            "lowest_forecast": False,
            "highest_forecast": False,
        }
    )

    assert response.forecast_price == 105.0
    assert response.forecast_collection is None


def test_standard_receives_authorized_forecast_collection() -> None:
    response = _build_authorized_response(
        {
            "lowest_forecast": True,
            "highest_forecast": True,
        }
    )

    assert response.forecast_collection == _full_forecast_collection()


def test_premium_receives_authorized_forecast_collection() -> None:
    response = _build_authorized_response(
        {
            "lowest_forecast": True,
            "highest_forecast": True,
        }
    )

    assert response.forecast_collection == _full_forecast_collection()


def test_gold_receives_authorized_forecast_collection() -> None:
    response = _build_authorized_response(
        {
            "lowest_forecast": True,
            "highest_forecast": True,
        }
    )

    assert response.forecast_collection == _full_forecast_collection()


def test_administrator_receives_authorized_forecast_collection() -> None:
    response = _build_authorized_response(
        {
            "lowest_forecast": True,
            "highest_forecast": True,
        }
    )

    assert response.forecast_collection == _full_forecast_collection()


def test_partial_range_authorization_does_not_expose_partial_collection() -> None:
    response = _build_authorized_response(
        {
            "lowest_forecast": True,
            "highest_forecast": False,
        }
    )

    assert response.forecast_collection is None


def test_missing_authorization_context_preserves_backward_compatibility() -> None:
    response = ResponseBuilder.build_prediction_response(
        ticker="AAPL",
        current_price=100.0,
        forecast_price=105.0,
        expected_move_pct=5.0,
        confidence=80,
        confidence_level="HIGH",
        horizon=5,
        recommendation="BUY",
        model="EnsembleDecisionEngine_h5",
        details_available=True,
        trajectory=_trajectory(),
        forecast_collection=_full_forecast_collection(),
    )

    assert response.forecast_collection == _full_forecast_collection()


def test_filtering_does_not_mutate_generated_response() -> None:
    original = ResponseBuilder.build_prediction_response(
        ticker="AAPL",
        current_price=100.0,
        forecast_price=105.0,
        expected_move_pct=5.0,
        confidence=80,
        confidence_level="HIGH",
        horizon=5,
        recommendation="BUY",
        model="EnsembleDecisionEngine_h5",
        details_available=True,
        trajectory=_trajectory(),
        forecast_collection=_full_forecast_collection(),
    )

    filtered = ResponseBuilder.filter_prediction_response(
        response=original,
        authorization_context={
            "lowest_forecast": False,
            "highest_forecast": False,
        },
    )

    assert filtered.forecast_collection is None
    assert original.forecast_collection == _full_forecast_collection()
    assert filtered.forecast_price == original.forecast_price
    assert filtered.trajectory == original.trajectory


def test_legacy_presentation_preserves_forecast_price() -> None:
    presentation = ResponseBuilder.build_forecast_presentation(
        forecast_price=105.0,
        forecast_collection=_full_forecast_collection(),
    )

    assert presentation == ForecastPresentation(
        mode="legacy",
        display_price=105.0,
    )


def test_premium_locked_selection_resolves_selected_price() -> None:
    presentation = ResponseBuilder.build_forecast_presentation(
        forecast_price=105.0,
        forecast_collection=_full_forecast_collection(),
        daily_selection_state={
            "mode": "locked_selection",
            "selection": "highest",
            "market_day": "2026-07-31",
            "locked": True,
        },
    )

    assert presentation == ForecastPresentation(
        mode="locked_selection",
        selection="highest",
        display_price=108.0,
        market_day="2026-07-31",
        locked=True,
    )


def test_missing_premium_selection_uses_expected_fallback() -> None:
    presentation = ResponseBuilder.build_forecast_presentation(
        forecast_price=105.0,
        forecast_collection=_full_forecast_collection(),
        daily_selection_state={
            "mode": "locked_selection",
            "selection": None,
            "market_day": "2026-07-31",
            "locked": False,
        },
    )

    assert presentation.mode == "locked_selection"
    assert presentation.selection is None
    assert presentation.display_price == 105.0
    assert presentation.locked is False


def test_gold_simultaneous_presentation_keeps_collection() -> None:
    state = {
        "mode": "simultaneous",
        "selection": None,
        "market_day": "2026-07-31",
        "locked": False,
    }
    presentation = ResponseBuilder.build_forecast_presentation(
        forecast_price=105.0,
        forecast_collection=_full_forecast_collection(),
        daily_selection_state=state,
    )
    response = ResponseBuilder.build_prediction_response(
        ticker="AAPL",
        current_price=100.0,
        forecast_price=105.0,
        expected_move_pct=5.0,
        confidence=80,
        confidence_level="HIGH",
        horizon=5,
        recommendation="BUY",
        model="test",
        details_available=True,
        forecast_collection=_full_forecast_collection(),
        forecast_presentation=presentation,
        authorization_context=(
            ResponseBuilder.authorization_context_for_presentation(state)
        ),
    )

    assert presentation.mode == "simultaneous"
    assert presentation.display_price == 105.0
    assert response.forecast_collection == _full_forecast_collection()


def test_premium_response_hides_raw_collection_but_keeps_resolved_price() -> None:
    state = {
        "mode": "locked_selection",
        "selection": "lowest",
        "market_day": "2026-07-31",
        "locked": True,
    }
    presentation = ResponseBuilder.build_forecast_presentation(
        forecast_price=105.0,
        forecast_collection=_full_forecast_collection(),
        daily_selection_state=state,
    )
    response = ResponseBuilder.build_prediction_response(
        ticker="AAPL",
        current_price=100.0,
        forecast_price=105.0,
        expected_move_pct=5.0,
        confidence=80,
        confidence_level="HIGH",
        horizon=5,
        recommendation="BUY",
        model="test",
        details_available=True,
        forecast_collection=_full_forecast_collection(),
        forecast_presentation=presentation,
        authorization_context=(
            ResponseBuilder.authorization_context_for_presentation(state)
        ),
    )

    assert response.forecast_price == 105.0
    assert response.forecast_collection is None
    assert response.forecast_presentation is not None
    assert response.forecast_presentation.display_price == 101.0
