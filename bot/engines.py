from typing import Dict, Optional, Any
from .utils import clamp

def detect_regime(inputs: Dict[str, Any]) -> Dict[str, str]:
    cluster = inputs.get("cluster")
    if not cluster:
        return {"regime": "CHOP", "reason": "missing_cluster"}

    regime_val = cluster.get("regime", 0)

    if regime_val == 1:
        return {"regime": "TREND_UP", "reason": f"ST_Cluster_Bullish_{cluster.get('strength', 0):.2f}"}
    elif regime_val == -1:
        return {"regime": "TREND_DOWN", "reason": f"ST_Cluster_Bearish_{cluster.get('strength', 0):.2f}"}
    else:
        return {"regime": "CHOP", "reason": "ST_Cluster_Neutral"}

def score_direction(inputs: Dict[str, Any]) -> Dict[str, float]:
    price = inputs.get("price")
    cluster = inputs.get("cluster")
    rsi = inputs.get("rsi")
    cvd_data = inputs.get("cvd_data") # {divergence: BULLISH|BEARISH|NONE, cvd_delta: float}
    mc_data = inputs.get("mc_data") # {prob_up: float, bias: str}

    macd_1m = inputs.get("macd")
    ha_1m_color = inputs.get("heikenColor")
    ha_1m_count = inputs.get("heikenCount")

    macd_5m = inputs.get("macd_5m")
    macd_5m_hist_color = macd_5m.get("histColor") if macd_5m else None
    macd_5m_hist_count = macd_5m.get("histCount") if macd_5m else 0

    ha_5m_color = inputs.get("heiken_5m_color")
    ha_5m_count = inputs.get("heiken_5m_count") or 0

    up = 1.0
    down = 1.0

    # Trend detection (SuperTrend Cluster on 5m)
    cluster_regime = cluster.get("regime", 0) if cluster else 0
    cluster_strength = cluster.get("strength", 0) if cluster else 0
    uptrend = True if cluster_regime == 1 else False if cluster_regime == -1 else None

    # Handle missing essential inputs
    if price is None or cluster is None:
        return {"upScore": None, "downScore": None, "rawUp": None, "uptrend": uptrend}

    # 1. SuperTrend Strength (Trend Following)
    # 1. SuperTrend Strength (Trend Following) - Increased weight for CORE
    if cluster_regime == 1:
        up += 30 * cluster_strength
    elif cluster_regime == -1:
        down += 30 * cluster_strength

    # 2. Monte Carlo conviction (Predictive)
    # 2. Monte Carlo conviction (Predictive) + GOLD SYNERGY
    if mc_data:
        p_up = mc_data.get("prob_up", 0.5)
        p_down = mc_data.get("prob_down", 0.5)
        up += p_up * 40
        down += p_down * 40

        # "GOLD SYNERGY": Boost if Trend and Prediction align
        if cluster_regime == 1 and p_up > 0.55:
            up += 20
        elif cluster_regime == -1 and p_down > 0.55:
            down += 20

    # 3. 5m MACD Momentum
    # Early momentum (1-5 bars) - CRITICAL entry point
    # Exhaustion (6+) is handled by the Veto layer at the end
    if not macd_5m_exhausted:
        if macd_5m_hist_color == "up": up += 25
        elif macd_5m_hist_color == "down": down += 25

    # 4. Heiken Ashi Alignment (1m & 5m)
    # Alignment: 5m trend requires 1m confirmation for scoring
    # Note: Exhaustion is handled by the Veto layer at the end
    ha_5m_exhausted = ha_5m_count >= 6
    ha_1m_exhausted = ha_1m_count >= 6

    # UP Conviction (5m Green)
    if ha_5m_color == "green":
        if not (ha_5m_exhausted or ha_1m_exhausted):
            if ha_1m_color == "green":
                up += 30 # Double confirmation
            else:
                up = 0.0 # 5m Green but 1m Red: "It does not go"

    # DOWN Conviction (5m Red)
    if ha_5m_color == "red":
        if not (ha_5m_exhausted or ha_1m_exhausted):
            if ha_1m_color == "red":
                down += 30 # Double confirmation
            else:
                down = 0.0 # 5m Red but 1m Green: "It does not go"

    # 5. CVD Aggression and Divergence - Final Filter
    if cvd_data:
        div = cvd_data.get("divergence", "NONE")
        if div == "BULLISH": up += 35
        elif div == "BEARISH": down += 35

    # 6. RSI Safeguards: Avoid Overbought/Oversold territories
    if rsi is not None:
        if rsi > 70:
            down += 25 # High conviction reversal
            # AVOID REGIONS: Stop trend-following into OB
            if up > down:
                up *= 0.1
        elif rsi < 30:
            up += 25 # High conviction reversal
            # AVOID REGIONS: Stop trend-following into OS
            if down > up:
                down *= 0.1



    # FINAL TREND FILTER (Enforced Rule: NEVER BUY AGAINST THE TREND)
    # If a clear regime is detected by ST Cluster, strictly block the opposite side
    if cluster_regime == 1:
        down = 0.0 # Strict Bullish only
    elif cluster_regime == -1:
        up = 0.0 # Strict Bearish only

    # MOMENTUM EXHAUSTION VETO (Rule: Never buy into an exhausted trend)
    # This acts after all other logic to ensure we don't chase 6+ bar streaks
    if (ha_5m_exhausted or ha_1m_exhausted):
        if ha_5m_color == "green" or ha_1m_color == "green":
            up = 0.0 # Veto the Buy
        if ha_5m_color == "red" or ha_1m_color == "red":
            down = 0.0 # Veto the Sell

    # MACD Exhaustion Veto
    macd_5m_exhausted = macd_5m_hist_count >= 6
    if macd_5m_exhausted:
        if macd_5m_hist_color == "up":
            up = 0.0
        elif macd_5m_hist_color == "down":
            down = 0.0

    import math
    def is_invalid(v):
        return v is None or (isinstance(v, float) and math.isnan(v))

    if is_invalid(up) or is_invalid(down):
        return {"upScore": None, "downScore": None, "rawUp": None, "uptrend": uptrend}

    raw_up = up / (up + down) if (up + down) > 0 else None

    return {"upScore": up, "downScore": down, "rawUp": raw_up, "uptrend": uptrend}

def apply_time_awareness(raw_up: Optional[float], remaining_minutes: float, window_minutes: float) -> Dict[str, Optional[float]]:
    time_decay = clamp(remaining_minutes / window_minutes, 0, 1)

    if raw_up is None or time_decay is None:
        return {"timeDecay": time_decay, "adjustedUp": None, "adjustedDown": None}

    adj = 0.5 + (raw_up - 0.5) * time_decay
    adjusted_up = clamp(adj, 0, 1)

    return {
        "timeDecay": time_decay,
        "adjustedUp": adjusted_up,
        "adjustedDown": (1 - adjusted_up) if adjusted_up is not None else None
    }

def compute_edge(inputs: Dict[str, Any]) -> Dict[str, Optional[float]]:
    model_up = inputs.get("modelUp")
    model_down = inputs.get("modelDown")
    market_yes = inputs.get("marketYes")
    market_no = inputs.get("marketNo")

    if market_yes is None or market_no is None:
        return {"marketUp": None, "marketDown": None, "edgeUp": None, "edgeDown": None}

    total_market = market_yes + market_no
    market_up = market_yes / total_market if total_market > 0 else None
    market_down = market_no / total_market if total_market > 0 else None

    edge_up = model_up - market_up if (model_up is not None and market_up is not None) else None
    edge_down = model_down - market_down if (model_down is not None and market_down is not None) else None

    return {
        "marketUp": clamp(market_up, 0, 1) if market_up is not None else None,
        "marketDown": clamp(market_down, 0, 1) if market_down is not None else None,
        "edgeUp": edge_up,
        "edgeDown": edge_down
    }

def decide(inputs: Dict[str, Any]) -> Dict[str, Any]:
    remaining_minutes = inputs.get("remainingMinutes")
    edge_up = inputs.get("edgeUp")
    edge_down = inputs.get("edgeDown")
    model_up = inputs.get("modelUp")
    model_down = inputs.get("modelDown")

    # Time remaining strictness: ignore everything after 7 mins remaining
    if remaining_minutes is not None and remaining_minutes < 7.0:
        return {"action": "NO_TRADE", "side": None, "phase": "LATE", "reason": "beyond_7min_window"}

    phase = "EARLY" if remaining_minutes > 10 else "MID" if remaining_minutes > 5 else "LATE"

    # Requirement for High Conviction (Predictive options style)
    # We prioritize model probability over market edge
    min_prob = 0.70 # Require 70% conviction for any trade

    if model_up is None or model_down is None:
        return {"action": "NO_TRADE", "side": None, "phase": phase, "reason": "missing_model_data"}

    best_side = "UP" if model_up > model_down else "DOWN"
    best_prob = model_up if best_side == "UP" else model_down

    if best_prob < min_prob:
        return {"action": "NO_TRADE", "side": None, "phase": phase, "reason": f"conviction_{best_prob:.2f}_below_{min_prob}"}

    # Optional: still check edge if market data is available, but don't block
    edge = edge_up if best_side == "UP" else edge_down
    if edge is not None and edge < 0:
        # If model says UP but market is already priced HIGHER than model, skip
        return {"action": "NO_TRADE", "side": None, "phase": phase, "reason": "negative_edge"}

    strength = "HIGH_CONVICTION" if best_prob >= 0.8 else "STRONG"
    return {"action": "ENTER", "side": best_side, "phase": phase, "strength": strength, "prob": best_prob}
