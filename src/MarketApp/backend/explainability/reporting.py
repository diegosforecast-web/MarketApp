"""
Explainability reporting utilities.

Purpose
-------
Format prediction explanations for CLI output.

Why it matters
--------------
The same structured explanation object can later power API responses and
frontend cards.
"""

from __future__ import annotations

from explainability.models import PredictionExplanation


def format_explanation_report(
    explanation: PredictionExplanation,
) -> str:
    lines = [
        "",
        "===================================",
        "MODEL EXPLANATION",
        "===================================",
        f"Prediction : {explanation.prediction}",
        f"Confidence : {explanation.confidence:.2%}",
        "",
        "Top Positive Drivers",
        "-----------------------------------",
    ]

    if explanation.top_positive_features:
        for item in explanation.top_positive_features:
            lines.append(
                f"+ {item.display_name:<28} {item.impact:>9.4f}"
            )
    else:
        lines.append("No positive drivers identified.")

    lines.extend(
        [
            "",
            "Top Negative Drivers",
            "-----------------------------------",
        ]
    )

    if explanation.top_negative_features:
        for item in explanation.top_negative_features:
            lines.append(
                f"- {item.display_name:<28} {item.impact:>9.4f}"
            )
    else:
        lines.append("No negative drivers identified.")

    lines.extend(
        [
            "",
            "Summary",
            "-----------------------------------",
            explanation.summary,
            "",
        ]
    )

    return "\n".join(lines)
