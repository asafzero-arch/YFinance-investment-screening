def calc_value_score(info: dict, weights: dict) -> float:
    """
    バリュースコアを100点満点で計算する
    PER・PBR・配当利回り・ROE・売上成長率の5指標で評価
    """
    score = 0.0

    # PERスコア（低いほど高得点、上限50倍）
    per = info.get("trailingPE")
    if per and 0 < per < 50:
        score += weights["per_weight"] * max(0, (50 - per) / 50)

    # PBRスコア（低いほど高得点、上限5倍）
    pbr = info.get("priceToBook")
    if pbr and 0 < pbr < 5:
        score += weights["pbr_weight"] * max(0, (5 - pbr) / 5)

    # 配当利回りスコア（高いほど高得点、上限5%で正規化）
    div = info.get("dividendYield", 0) or 0
    if div > 1:  # yfinanceがパーセント値で返す場合の正規化
        div /= 100
    score += weights["dividend_weight"] * min(div / 0.05, 1.0)

    # ROEスコア（高いほど高得点、上限20%で正規化）
    roe = info.get("returnOnEquity", 0) or 0
    score += weights["roe_weight"] * min(max(roe, 0) / 0.20, 1.0)

    # 売上成長率スコア（高いほど高得点、上限20%で正規化）
    growth = info.get("revenueGrowth", 0) or 0
    score += weights["revenue_growth_weight"] * min(max(growth, 0) / 0.20, 1.0)

    return round(score, 2)