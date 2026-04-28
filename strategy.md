# "Gold" Synergy Strategy: Polymarket BTC 15m

This document outlines the high-conviction, options-style trading strategy used by the bot. The strategy is designed to prioritize trend alignment and early momentum while strictly avoiding late-cycle volatility.

## 1. The "Gold" Hierarchy

The engine follows a strict priority list to determine trade conviction.

### A. Core Trend Filter (SUPER TREND CLUSTER)
- **Rule**: NEVER BUY AGAINST THE TREND.
- **Bullish Regime**: Downtrend conviction is hard-blocked (set to 0.0). Only `UP` trades are permitted.
- **Bearish Regime**: Uptrend conviction is hard-blocked (set to 0.0). Only `DOWN` trades are permitted.
- **Neutral**: The engine waits for a trend to establish.

### B. Gold Synergy Bonus
- When the **Trend Cluster** and the **Monte Carlo Prediction** (>55%) both point in the same direction, a **+20 point synergy bonus** is applied. This signals extreme conviction.

### C. Momentum & Exhaustion (Heiken Ashi)
- **Multi-Timeframe Alignment**: 5m Heiken Ashi signals are only followed if confirmed by the 1m Heiken Ashi color. (e.g., 5m Green + 1m Red = NO TRADE).
- **Strict Exhaustion Block**: If a momentum streak reaches **6+ bars** on EITHER the 1m or 5m timeframe, that side is blocked. We do not chase over-extended trends on any timeframe.
- **Slope-Based MACD**: Evaluates the histogram slope on the 5m timeframe to detect early momentum shifts before zero-crosses.

### D. Safety Filters
- **RSI Safeguard**: If RSI > 70 or < 30, the bot attempts to detect reversals. If the bot tries to trend-follow into an overbought/oversold region, the conviction score is slashed by **90%** to prevent exit-liquidity entries.
- **CVD Divergence**: A high-weight (+35 point) confirmation layer that identifies aggressive buying/selling pressure moving against price.

## 2. Decision Windows (Options Timing)

Timing is critical for 15-minute binary options.

| Phase | Time Remaining | Action |
|-------|----------------|--------|
| **GOLD ZONE** | 15m - 10m | Maximum conviction allowed. Best entries. |
| **MID ZONE** | 10m - 7m | Reduced conviction due to time decay. |
| **DEAD ZONE** | < 7m | **NO TRADE**. All entries are strictly ignored. |

## 3. Entry Requirements

1.  **Strict Time Window**: No entries after 7 minutes remaining.
2.  **Minimum Conviction**: Adjusted model probability must exceed **70%**.
3.  **Positive Edge**: The model prediction must be higher than the current Polymarket odds (model must see value).
4.  **Trend Alignment**: Must be in a clear, non-exhausted trend.

## 4. Resolution

Trades are simulated or executed against the **Polymarket/Chainlink Strike Price**. The bot tracks the specific 15-minute open price and uses the remaining duration as its simulation horizon for Monte Carlo paths.
