# Quantitative Metrics for 8-24 Month Investment Horizons

**Author:** Quantitative Research Desk
**Date:** January 16, 2026
**Horizon:** Medium Term (8-24 Months)

## 1. Executive Summary

The 8-24 month investment horizon represents a distinct "sweet spot" in quantitative finance. It is sufficiently long to allow fundamental value realization (mean reversion) but short enough to benefit from intermediate-term momentum (trend persistence). Institutional research suggests that **multi-factor models** combining **Quality**, **Value**, and **Momentum** (QVM) offer the highest information ratios for this specific duration.

While high-frequency trading relies on microstructure and long-term investing (5y+) on macro/secular trends, the 1-2 year hold is dominated by:
1.  **Earnings Surprises & Revisions**: The market adjusting to new fundamental realities.
2.  **Valuation Re-rating**: Multiples expanding as sentiment shifts.
3.  **Factor Persistence**: The tendency of "winners" to keep winning (Momentum) and "cheap quality" to outperform.

---

## 2. Core Factor Categories

### A. Value (The "Safety Margin")
*For a 1-2 year hold, we prioritize metrics that signal near-term re-pricing potential rather than deep distressed value.*

*   **Free Cash Flow (FCF) Yield**
    *   **Formula:** $\frac{Free Cash Flow}{Market Cap}$ or $\frac{FCF}{Enterprise Value}$
    *   **Rationale:** FCF is harder to manipulate than EPS. High FCF yield provides a buffer (buybacks, dividends) and often precedes a re-rating.
    *   **Quant Note:** Top decile FCF yield stocks have historically outperformed the S&P 500 by ~3-4% annualized.

*   **EV / EBITDA**
    *   **Formula:** $\frac{Enterprise Value}{Earnings Before Interest, Taxes, Depreciation, Amortization}$
    *   **Rationale:** Capital structure neutral. Better for comparing companies with different debt loads. Look for values < 8x-10x in non-hyper-growth sectors.
    *   **Academic Support:** EBITDA/EV is widely cited in academic literature (e.g., Gray & Carlisle) as superior to P/E for predictive returns.

*   **Shareholder Yield**
    *   **Formula:** $\frac{Dividends + Net Buybacks + Debt Paydown}{Market Cap}$
    *   **Rationale:** Measures total cash returned to shareholders. Companies aggressively buying back stock often support price floors over 12-24 months.

### B. Quality (The "Compounder" Filter)
*Quality metrics protect against downside risk and ensure the company survives long enough for the thesis to play out.*

*   **ROIC (Return on Invested Capital)**
    *   **Formula:** $\frac{NOPAT}{Invested Capital}$
    *   **Rationale:** The truest measure of management efficiency. Companies with high and stable ROIC (>15%) tend to compound intrinsic value regardless of market cycles.
    *   **Strategy:** "The Magic Formula" (Greenblatt) combines High ROIC + High Earnings Yield.

*   **Gross Margin Stability**
    *   **Metric:** Coefficient of Variation of Gross Margins (5Y).
    *   **Rationale:** Stable gross margins indicate pricing power and a competitive moat. Volatile margins suggest commodity-like business models.

*   **Piotroski F-Score**
    *   **Metric:** 0-9 scale based on Profitability, Leverage, Liquidity, and Operating Efficiency.
    *   **Target:** Score $\ge$ 7.
    *   **Rationale:** Filters out "value traps." Statistically significant alpha generator when applied to a universe of value stocks.

### C. Momentum (The "Timing" Element)
*Momentum prevents catching falling knives. For 8-24 months, we look for intermediate trend strength.*

*   **Price Momentum (6m - 1m)**
    *   **Formula:** Total return over last 6 months, excluding the most recent month (to avoid short-term reversals).
    *   **Rationale:** The "Jegadeesh & Titman" effect. Winners over the last 6-12 months tend to continue winning for the next year due to investor under-reaction to positive news.

*   **Earnings Momentum (Standardized Unexpected Earnings - SUE)**
    *   **Formula:** $\frac{Actual EPS - Expected EPS}{Standard Deviation of Estimates}$
    *   **Rationale:** Post-Earnings Announcement Drift (PEAD). Companies that beat estimates tend to drift upwards for months.

### D. Risk & Financial Health (The "Blow-up" Avoidance)

*   **Altman Z-Score**
    *   **Rationale:** Probability of bankruptcy within 2 years. Essential filter for holding periods > 1 year.
    *   **Target:** Safe Zone > 3.0.

*   **Beneish M-Score**
    *   **Rationale:** Probabilistic model to detect earnings manipulation. Avoid companies with high M-Scores (> -1.78) to reduce tail risk of fraud.

---

## 3. Recommended Composite Strategies

For a quantitative-focused portfolio over this horizon, single metrics are noisy. We recommend composite rankings:

### Strategy 1: "Quality at a Reasonable Price" (QARP)
*   **Rank Universe by:**
    1.  **ROIC** (High is good)
    2.  **FCF Yield** (High is good)
*   **Filter:** Debt/EBITDA < 3.0
*   **Holding Period:** 12 Months + rebalance.

### Strategy 2: "Trending Value" (O'Shaughnessy)
*   **Filter:** Top 10% of universe by **Value** (Composite of P/E, P/S, P/B, P/FCF, EV/EBITDA).
*   **Select:** Top 25 stocks from that list with the highest **6-Month Price Momentum**.
*   **Rationale:** Buys cheap stocks that the market has just started to recognize.

### Strategy 3: The "Double Sort" (Fama-French Inspired)
*   **Primary Sort:** **Book-to-Market** (High B/M = Value).
*   **Secondary Sort:** **Operating Profitability** (High Profitability).
*   **Rationale:** Exposure to the Value and Profitability premiums, two of the most robust factors in academic history.

---

## 4. Implementation Checklist for Quant Screening

When building your screener, ensure data normalization:
1.  **Sector Relative:** Compare P/E against Sector Median, not just market aggregate (e.g., Tech vs. Energy).
2.  **Look-Ahead Bias:** Ensure backtests use only data available at the time of trade (Point-in-Time data).
3.  **Liquidity Filter:** Exclude nano-caps unless specifically targeting illiquidity premium. Minimum Avg Daily Volume > $1M.

**Suggested Final Quant Score Formula:**
$$ Score = 0.4(Z_{Value}) + 0.3(Z_{Quality}) + 0.3(Z_{Momentum}) $$
*(Where Z represents the Z-score of the composite metric for that factor)*
