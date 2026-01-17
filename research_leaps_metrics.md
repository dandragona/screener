# Advanced Metrics & Signals for LEAPs Screening

This document outlines additional metrics, signals, and advanced concepts to enhance the LEAPs screening process, going beyond basic fundamental and technical filters.

## 1. Options Market Structure & Volatility Signals

The pricing and structure of the options market itself can provide powerful "smart money" signals.

### A. Implied Volatility (IV) Skew
*   **Concept:** Variation in IV across different strike prices for the same expiration.
*   **Call Skew (Bullish):** When OTM (Out-of-the-Money) Calls have higher IV than ITM (In-the-Money) Calls or ATM Puts. This "forward skew" is rare in equities but indicates the market is aggressively pricing in upside potential.
*   **Put/Call Skew (Sentiment):** The ratio of IV for OTM Puts to OTM Calls.
    *   *High Skew (Smirk):* High demand for crash protection (bearish/cautious).
    *   *Flattening Skew:* Decreasing fear; potentially bullish if combined with technical breakouts.
*   **Actionable Metric:** **25-Delta Risk Reversal** (IV of 25-Delta Call - IV of 25-Delta Put). Positive values generally indicate bullish sentiment.

### B. IV Term Structure (Time)
*   **Concept:** Variation in IV across different expiration dates.
*   **Contango (Normal):** Long-term IV > Short-term IV.
    *   *Signal:* A "flatter" than normal term structure (where LEAPs IV is unusually close to Short-term IV) can make LEAPs relatively cheaper to buy.
*   **Backwardation:** Short-term IV > Long-term IV.
    *   *Signal:* Often occurs during panic or pre-earnings. While high short-term IV is bad for buying short-term options, it might seemingly make LEAPs look "cheap" by comparison, BUT beware that volatility often mean-reverts. The collapse of short-term IV can drag down the whole curve.
*   **Actionable Metric:** **IV Term Slope** (IV[365d] / IV[30d]). Low ratio suggests long-term options are relatively cheap.

### C. Liquidity & Health
*   **Open Interest (OI) Growth:** Rising OI on LEAPs strikes suggests long-term positioning.
*   **Bid-Ask Spread %:** LEAPs are notoriously illiquid.
    *   *Metric:* `(Ask - Bid) / Midpoint`. Target < 2-5%. Wide spreads drastically raise the breakeven price.

## 2. "Smart Money" Flow (Quality & Conviction)

LEAPs require a 1-2 year horizon. Aligning with long-term holders is crucial.

### A. Institutional Sponsorship
*   **Concept:** Institutions (Pensions, Mutual Funds) hold for the long term.
*   **Trend:** Rising Institutional Ownership % quarter-over-quarter.
*   **Breadth:** Increase in the *number* of funds holding the stock, not just the share count (avoids concentration risk).
*   **Signal:** "High Quality" verification. Institutions rarely buy "garbage" to hold for years.

### B. Insider Activity
*   **Concept:** Executives know their business best.
*   **Cluster Buying:** Multiple insiders (CEO, CFO, Directors) buying on the open market within a short window.
*   **Signal:** Strongest bullish signal for value/turnaround plays. Insiders buying *deep* into a decline suggest the bottom is near.
*   **Note:** Ignore sales (often for tax/diversification). Focus purely on *un-mandated open market purchases*.

## 3. Advanced Fundamental & Quantitative Factors

Refining the "Thrive" criteria from `leaps.md`.

### A. Capital Allocation Efficiency
*   **Shareholder Yield:** (Dividends + Net Buybacks) / Market Cap.
    *   *Relevance:* Buybacks support stock price floors, reducing downside risk for LEAPs.
*   **CROIC (Cash Return on Invested Capital):** FCF / Invested Capital. Harder to manipulate than ROIC.

### B. Earnings Quality
*   **Accruals Ratio:** Low accruals suggest "real" cash earnings vs. accounting tricks.
*   **Beneish M-Score:** Probability of earnings manipulation. (Screen out high risk scores).

### C. Bankruptcy/Distress Risk (Crucial for 2-year holds)
*   **Altman Z-Score:** Predicts bankruptcy risk. LEAPs can go to zero if equity is wiped out. Target "Safe Zone" > 3.0.
*   **Distance to Default:** Market-based measure of default risk using volatility and asset value.

## 4. Derived Composite Scores

Combine these into new composite signals:

1.  **The "Cheap Vol" Entry:** Low IV Rank (<20) + Flat Term Structure + Support at 200 SMA.
2.  **The "Insider Value" Play:** High FCF Yield + Cluster Insider Buying + Low Price/Sales.
3.  **The "Compounder" Lock:** High ROIC + Rising Institutional Ownership + Low IV Skew.

## Summary of New Metrics to Implement

| Category | Metric Name | Purpose |
| :--- | :--- | :--- |
| **Options** | **IV Term Slope** | Identify when LEAPs are cheap relative to near-term. |
| **Options** | **Call/Put Skew** | Gauge long-term market sentiment/positioning. |
| **Flow** | **Inst. Ownership Trend** | Confirm "smart money" accumulation. |
| **Flow** | **Net Insider Buying** | High conviction bullish signal. |
| **Quant** | **Shareholder Yield** | Downside protection via buybacks. |
| **Quant** | **Altman Z-Score** | "Don't go into bankruptcy" safety check. |
