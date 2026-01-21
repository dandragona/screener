# ML Stock Classification Proposal

## 1. Problem Definition
**Goal**: Classify the stock's movement over the **next 30 days** into 5 classes:
1.  **Large Positive** (e.g., > 7%)
2.  **Small Positive** (e.g., 2% to 7%)
3.  **Neutral** (e.g., -2% to 2%)
4.  **Small Negative** (e.g., -2% to -7%)
5.  **Large Negative** (e.g., < -7%)

**Input Data**: Daily data from YFinance, Tiingo, and Polygon.
**Horizon**: 1 Month (~21 trading days).

---

## 2. Feature Engineering
We will create a multi-modal input combining **Time-Series Data** (Price/Volume/Options) and **Static/Low-Frequency Data** (Fundamentals/Sentiment).

### A. Time-Series Features (Daily Sequence)
*Input Shape: [Lookback_Window=60 days, Features=~25]*

1.  **Price & Volume** (YFinance/Polygon):
    *   **Log Returns**: `ln(Close_t / Close_{t-1})`
    *   **Volume Change**: `(Vol_t - Vol_avg_20d) / Vol_avg_20d`
    *   **Volatility**: Rolling Standard Deviation of returns (14d, 30d).
    *   **Technical Indicators**: RSI (14), MACD, Bollinger Band Width, ATR (Normalized).
2.  **Options Dynamics** (Polygon):
    *   **Implied Volatility (IV30)**: 30-day constant maturity IV.
    *   **IV Rank**: `(IV_current - IV_low_1y) / (IV_high_1y - IV_low_1y)`
    *   **IV Term Structure**: `IV_Long (365d) / IV_Short (30d)` (Ratio > 1 implies Contango/Normal, < 1 implies Inverted/Fear).
    *   **Put-Call Ratio**: Volume or Open Interest ratio (if available continuously).
3.  **Sentiment** (Tiingo):
    *   **Daily Sentiment Score**: Rolling avg of last 3-7 days if daily data is sparse.

### B. Static / Low-Frequency Features (At time T)
*Input Shape: [Features=~10]*

1.  **Fundamentals** (YFinance):
    *   **Valuation**: P/E Ratio, PEG Ratio, Price/Book, Price/Sales.
    *   **Health**: Debt/Equity, Current Ratio.
    *   **Growth**: Revenue Growth, EPS Growth (latest quarter).
2.  **Categorical Embeddings**:
    *   **Sector / Industry**: One-hot encoded or learned embeddings (e.g., Tech vs. Energy).
3.  **Market Context**:
    *   **SPY (S&P 500) Trend**: Is the broad market above/below 200d MA? (Regime filter).

---

## 3. Model Architecture
Since we have a strong temporal component, a **Hybrid Time-Series Architecture** is recommended.

**Architecture: LSTM-CNN + Dense Head**

1.  **Time-Series Branch (Sequence Data)**:
    *   Input: `(Batch, 60, 25)`
    *   **Layer 1**: 1D Convolution (Kernel=3, Filters=32) -> ReLU -> MaxPool. *Captures short-term patterns (3-day trends).*
    *   **Layer 2**: LSTM or GRU (Units=64, Annualized). *Captures long-term dependencies up to 60 days.*
    *   **Output**: Vector of size 64.

2.  **Feature Branch (Static Data)**:
    *   Input: `(Batch, 10)`
    *   **Layer**: Dense (Units=16) -> ReLU.

3.  **Fusion & Output**:
    *   **Concatenate**: `[TimeSeries_Vector (64), Static_Vector (16)]` -> Total 80.
    *   **Dense Layers**: 64 -> Dropout(0.3) -> 32 -> ReLU.
    *   **Output Layer**: Dense(5, activation='softmax').

*Alternative (Simpler)*: **XGBoost**.
*   Flatten the time series: `Return_Mean_60d`, `Return_Std_60d`, `Slope_Linear_Reg_60d`, `RSI_Current`, `RSI_Slope`, etc.
*   Concatenate with static features.
*   *Pros*: Easier to train, often state-of-the-art for tabular data, handles missing values natively.
*   *Recommendation*: Start with XGBoost for the baseline. If performance plateaus, move to the LSTM/Transformer architecture.

---

## 4. Training & Validation Plan

### Phase 1: Data Collection (Backfill)
We need historical training data.
1.  **Stocks**: Use the S&P 1500 list currently in `symbol_loader.py`.
2.  **History**:
    *   Fetch **2 Years** of daily OHLCV + Option IV History.
    *   For **Sentiment**: Tiingo allows historical news. Fetch last 2 years of news for all tickers (Caution: Rate limits. Might need to throttle strictly).
3.  **Label Generation**:
    *   For every trading day `t` (from T-2years to t-35 days):
        *   Calculate `Return_30d = (Close_{t+21} - Close_t) / Close_t`.
        *   **Dynamic Binning**: Instead of fixed %, compute the **Z-Score** of the monthly return relative to the stock's *own* historical volatility.
            *   *Why?* A 5% move for a utility stock is "Large", for a bio-tech it is "Neutral".
            *   Class 0 (Large Neg): Z < -1.5
            *   Class 1 (Small Neg): -1.5 <= Z < -0.5
            *   Class 2 (Neutral): -0.5 <= Z <= 0.5
            *   Class 3 (Small Pos): 0.5 < Z <= 1.5
            *   Class 4 (Large Pos): Z > 1.5

### Phase 2: Walk-Forward Validation (Crucial)
Do **NOT** use random K-Fold split. It leaks future info.
Use **Rolling Time Window**:

*   **Fold 1**: Train [Jan 2024 - Jun 2024], Test [Jul 2024]
*   **Fold 2**: Train [Jan 2024 - Jul 2024], Test [Aug 2024]
*   **Fold 3**: Train [Jan 2024 - Aug 2024], Test [Sep 2024]
...

### Phase 3: Evaluation Metrics
*   **Accuracy**: Baseline is 20% (if classes balanced).
*   **Precision (Top Class)**: How often are we right when we predict "Large Positive"? This is the most money-making metric.
*   **F1-Score (Macro)**: To ensure we aren't just predicting "Neutral" all the time.

## 5. Implementation Steps
1.  **Script `ingest_backfill.py`**: Fetch 2y history for Price, IV, and News. Save to a separate ML-ready Dataset (CSV or Parquet, not just the current Relational DB).
2.  **Dataset Class**: Create `StockDataset` that yields `(X_seq, X_static, Y_label)`.
3.  **Baseline**: Train XGBoost on flattened features.
4.  **Deep Model**: Train the LSTM-CNN model using PyTorch/TensorFlow.
