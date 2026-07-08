"""
DiMarket portfolio analytics engine.

Purpose
-------
Provide one source of truth for portfolio-level performance metrics.

Inputs
------
A sequence of trade returns, optionally with dates.

Outputs
-------
PortfolioMetrics with equity, drawdown, return, risk, and trade statistics.

Why it matters
--------------
DiMarket's mission is trust. Model accuracy alone is not enough. This module
helps answer whether a prediction strategy would have behaved responsibly as an
investment process.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Optional, Sequence

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PortfolioMetrics:
    initial_capital: float
    final_equity: float
    cumulative_return: float
    cagr: float
    annualized_return: float
    annualized_volatility: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    flat_trades: int
    win_rate: float
    loss_rate: float
    average_return: float
    average_win: float
    average_loss: float
    median_return: float
    best_trade: float
    worst_trade: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    expectancy: float
    calendar_years: float
    trades_per_year: float
    equity_curve: pd.Series
    drawdown_curve: pd.Series

    def to_dict(self, include_curves: bool = False) -> dict:
        result = asdict(self)

        if include_curves:
            result["equity_curve"] = _series_to_records(
                self.equity_curve,
                value_name="equity",
            )
            result["drawdown_curve"] = _series_to_records(
                self.drawdown_curve,
                value_name="drawdown",
            )
        else:
            result.pop("equity_curve", None)
            result.pop("drawdown_curve", None)

        return result


class PortfolioAnalytics:
    """
    Calculate portfolio performance metrics from trade returns.

    trade_returns are decimal returns:
    0.02 = +2%
    -0.01 = -1%

    If dates are supplied, annualization is based on actual calendar span.
    If dates are not supplied, annualization falls back to periods_per_year.
    """

    def __init__(
        self,
        trade_returns: Sequence[float] | pd.Series | np.ndarray,
        dates: Optional[Iterable] = None,
        initial_capital: float = 100_000.0,
        risk_free_rate: float = 0.02,
        periods_per_year: int = 252,
    ) -> None:
        self.trade_returns = _clean_returns(trade_returns)
        self.dates = _clean_dates(dates, len(self.trade_returns))
        self.initial_capital = float(initial_capital)
        self.risk_free_rate = float(risk_free_rate)
        self.periods_per_year = int(periods_per_year)
        self._validate()

    def _validate(self) -> None:
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be greater than zero.")

        if self.periods_per_year <= 0:
            raise ValueError("periods_per_year must be greater than zero.")

        if len(self.trade_returns) and not np.all(np.isfinite(self.trade_returns)):
            raise ValueError("trade_returns contains non-finite values.")

    def _calendar_years(self) -> float:
        if self.dates is None or len(self.dates) < 2:
            if len(self.trade_returns) == 0:
                return 0.0

            return len(self.trade_returns) / self.periods_per_year

        start_date = self.dates.iloc[0]
        end_date = self.dates.iloc[-1]
        days = max((end_date - start_date).days, 1)

        return days / 365.25

    def _trades_per_year(self) -> float:
        years = self._calendar_years()

        if years <= 0:
            return 0.0

        return len(self.trade_returns) / years

    def _build_index(self) -> pd.Index:
        if self.dates is None:
            return pd.RangeIndex(
                start=0,
                stop=len(self.trade_returns) + 1,
                step=1,
                name="trade",
            )

        first_date = self.dates.iloc[0]
        index_values = [first_date] + self.dates.tolist()

        return pd.DatetimeIndex(
            index_values,
            name="date",
        )

    def equity_curve(self) -> pd.Series:
        equity = np.empty(
            len(self.trade_returns) + 1,
            dtype=float,
        )

        equity[0] = self.initial_capital

        for i, trade_return in enumerate(self.trade_returns):
            equity[i + 1] = equity[i] * (1.0 + trade_return)

        return pd.Series(
            equity,
            index=self._build_index(),
            name="equity",
        )

    @staticmethod
    def drawdown_curve(equity_curve: pd.Series) -> pd.Series:
        running_peak = equity_curve.cummax()
        drawdown = (equity_curve / running_peak) - 1.0
        drawdown.name = "drawdown"
        return drawdown

    def _trade_stats(self) -> dict:
        returns = self.trade_returns
        total_trades = len(returns)

        if total_trades == 0:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "flat_trades": 0,
                "win_rate": 0.0,
                "loss_rate": 0.0,
                "average_return": 0.0,
                "average_win": 0.0,
                "average_loss": 0.0,
                "median_return": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "gross_profit": 0.0,
                "gross_loss": 0.0,
                "profit_factor": 0.0,
                "expectancy": 0.0,
            }

        wins = returns[returns > 0]
        losses = returns[returns < 0]
        flats = returns[returns == 0]

        gross_profit = float(wins.sum()) if len(wins) else 0.0
        gross_loss = float(abs(losses.sum())) if len(losses) else 0.0

        if gross_loss == 0.0:
            profit_factor = np.inf if gross_profit > 0.0 else 0.0
        else:
            profit_factor = gross_profit / gross_loss

        return {
            "total_trades": int(total_trades),
            "winning_trades": int(len(wins)),
            "losing_trades": int(len(losses)),
            "flat_trades": int(len(flats)),
            "win_rate": float(len(wins) / total_trades),
            "loss_rate": float(len(losses) / total_trades),
            "average_return": float(returns.mean()),
            "average_win": float(wins.mean()) if len(wins) else 0.0,
            "average_loss": float(losses.mean()) if len(losses) else 0.0,
            "median_return": float(np.median(returns)),
            "best_trade": float(returns.max()),
            "worst_trade": float(returns.min()),
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "profit_factor": float(profit_factor),
            "expectancy": float(returns.mean()),
        }

    def _annualized_return(
        self,
        cumulative_return: float,
        calendar_years: float,
    ) -> float:
        if calendar_years <= 0:
            return 0.0

        if cumulative_return <= -1.0:
            return -1.0

        return float(
            (1.0 + cumulative_return)
            ** (1.0 / calendar_years)
            - 1.0
        )

    def _annualized_volatility(self, trades_per_year: float) -> float:
        if len(self.trade_returns) < 2 or trades_per_year <= 0:
            return 0.0

        return float(
            self.trade_returns.std(ddof=1)
            * np.sqrt(trades_per_year)
        )

    def _sharpe_ratio(
        self,
        annualized_return: float,
        annualized_volatility: float,
    ) -> float:
        if annualized_volatility == 0.0:
            return 0.0

        return float(
            (annualized_return - self.risk_free_rate)
            / annualized_volatility
        )

    def _sortino_ratio(
        self,
        annualized_return: float,
        trades_per_year: float,
    ) -> float:
        downside = self.trade_returns[self.trade_returns < 0]

        if len(downside) < 2 or trades_per_year <= 0:
            return 0.0

        downside_deviation = float(
            downside.std(ddof=1)
            * np.sqrt(trades_per_year)
        )

        if downside_deviation == 0.0:
            return 0.0

        return float(
            (annualized_return - self.risk_free_rate)
            / downside_deviation
        )

    @staticmethod
    def _calmar_ratio(
        annualized_return: float,
        max_drawdown: float,
    ) -> float:
        if max_drawdown == 0.0:
            return 0.0

        return float(annualized_return / abs(max_drawdown))

    def calculate(self) -> PortfolioMetrics:
        equity = self.equity_curve()
        drawdown = self.drawdown_curve(equity)

        final_equity = float(equity.iloc[-1])

        cumulative_return = float(
            final_equity / self.initial_capital - 1.0
        )

        calendar_years = self._calendar_years()
        trades_per_year = self._trades_per_year()

        annualized_return = self._annualized_return(
            cumulative_return=cumulative_return,
            calendar_years=calendar_years,
        )

        cagr = annualized_return

        annualized_volatility = self._annualized_volatility(
            trades_per_year=trades_per_year,
        )

        max_drawdown = float(drawdown.min())

        sharpe_ratio = self._sharpe_ratio(
            annualized_return=annualized_return,
            annualized_volatility=annualized_volatility,
        )

        sortino_ratio = self._sortino_ratio(
            annualized_return=annualized_return,
            trades_per_year=trades_per_year,
        )

        calmar_ratio = self._calmar_ratio(
            annualized_return=annualized_return,
            max_drawdown=max_drawdown,
        )

        stats = self._trade_stats()

        return PortfolioMetrics(
            initial_capital=self.initial_capital,
            final_equity=final_equity,
            cumulative_return=cumulative_return,
            cagr=cagr,
            annualized_return=annualized_return,
            annualized_volatility=annualized_volatility,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            total_trades=stats["total_trades"],
            winning_trades=stats["winning_trades"],
            losing_trades=stats["losing_trades"],
            flat_trades=stats["flat_trades"],
            win_rate=stats["win_rate"],
            loss_rate=stats["loss_rate"],
            average_return=stats["average_return"],
            average_win=stats["average_win"],
            average_loss=stats["average_loss"],
            median_return=stats["median_return"],
            best_trade=stats["best_trade"],
            worst_trade=stats["worst_trade"],
            gross_profit=stats["gross_profit"],
            gross_loss=stats["gross_loss"],
            profit_factor=stats["profit_factor"],
            expectancy=stats["expectancy"],
            calendar_years=calendar_years,
            trades_per_year=trades_per_year,
            equity_curve=equity,
            drawdown_curve=drawdown,
        )


def _clean_returns(
    trade_returns: Sequence[float] | pd.Series | np.ndarray,
) -> np.ndarray:
    returns = np.asarray(
        trade_returns,
        dtype=float,
    )

    if returns.ndim != 1:
        raise ValueError("trade_returns must be one-dimensional.")

    return returns


def _clean_dates(
    dates: Optional[Iterable],
    expected_length: int,
) -> Optional[pd.Series]:
    if dates is None:
        return None

    series = pd.Series(
        pd.to_datetime(list(dates))
    )

    if len(series) != expected_length:
        raise ValueError(
            "dates must have the same length as trade_returns."
        )

    return series.reset_index(drop=True)


def _series_to_records(
    series: pd.Series,
    value_name: str,
) -> list[dict]:
    records = []

    for index_value, value in series.items():
        if isinstance(index_value, pd.Timestamp):
            x_value = index_value.isoformat()
        else:
            x_value = int(index_value)

        records.append(
            {
                "index": x_value,
                value_name: float(value),
            }
        )

    return records


def summarize_portfolio_metrics(metrics: PortfolioMetrics) -> str:
    return (
        "\n===================================\n"
        "PORTFOLIO ANALYTICS\n"
        "===================================\n"
        f"Initial Capital     : ${metrics.initial_capital:,.2f}\n"
        f"Final Equity        : ${metrics.final_equity:,.2f}\n"
        f"Cumulative Return   : {metrics.cumulative_return:.2%}\n"
        f"CAGR                : {metrics.cagr:.2%}\n"
        f"Annualized Return   : {metrics.annualized_return:.2%}\n"
        f"Annualized Vol      : {metrics.annualized_volatility:.2%}\n"
        f"Max Drawdown        : {metrics.max_drawdown:.2%}\n"
        f"Sharpe Ratio        : {metrics.sharpe_ratio:.4f}\n"
        f"Sortino Ratio       : {metrics.sortino_ratio:.4f}\n"
        f"Calmar Ratio        : {metrics.calmar_ratio:.4f}\n"
        f"Calendar Years      : {metrics.calendar_years:.2f}\n"
        f"Trades / Year       : {metrics.trades_per_year:.2f}\n"
        "\n"
        f"Total Trades        : {metrics.total_trades}\n"
        f"Winning Trades      : {metrics.winning_trades}\n"
        f"Losing Trades       : {metrics.losing_trades}\n"
        f"Win Rate            : {metrics.win_rate:.2%}\n"
        f"Average Return      : {metrics.average_return:.2%}\n"
        f"Average Win         : {metrics.average_win:.2%}\n"
        f"Average Loss        : {metrics.average_loss:.2%}\n"
        f"Best Trade          : {metrics.best_trade:.2%}\n"
        f"Worst Trade         : {metrics.worst_trade:.2%}\n"
        f"Profit Factor       : {metrics.profit_factor:.4f}\n"
        f"Expectancy          : {metrics.expectancy:.2%}\n"
    )
