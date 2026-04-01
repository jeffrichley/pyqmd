# Machine Learning for Trading

## Part 1: Data Access

### Reading Stock Data

Stock data can be accessed through various APIs. The most common approach
is to use pandas DataReader or a custom data utility function.

When working with stock data, you need to handle missing values carefully.
Trading days don't include weekends or holidays, so there will be gaps
in the calendar dates.

### Adjusting for Splits and Dividends

Historical stock prices need to be adjusted for corporate actions like
stock splits and dividend payments. Most data providers offer adjusted
close prices that account for these events.

The adjustment factor is calculated by comparing the close price before
and after the corporate action. This ensures that returns calculated
from the adjusted prices accurately reflect the actual returns an
investor would have experienced.

## Part 2: Technical Indicators

### Simple Moving Average

The Simple Moving Average (SMA) is calculated by taking the arithmetic
mean of a given set of values over a specified period. For example, a
20-day SMA adds up the closing prices for the last 20 days and divides
by 20.

SMA is a lagging indicator because it is based on past prices. The
longer the period, the more the indicator lags behind the current price.

### Bollinger Bands

Bollinger Bands consist of three lines: the middle band (SMA), an upper
band (SMA + 2 standard deviations), and a lower band (SMA - 2 standard
deviations).

When the price touches the upper band, the asset may be overbought. When
it touches the lower band, it may be oversold. The width of the bands
indicates volatility.

### Relative Strength Index

The RSI measures the speed and magnitude of recent price changes. It
oscillates between 0 and 100. Traditional interpretation says that an
RSI above 70 indicates overbought conditions, while below 30 indicates
oversold conditions.

## Part 3: Strategy Development

### Manual Rule-Based Strategy

A manual strategy uses predefined rules based on technical indicators.
For example, buy when the price crosses below the lower Bollinger Band
and the RSI is below 30.

### Machine Learning Strategy

A machine learning strategy learns the relationship between technical
indicators and future returns from historical data. Common approaches
include decision trees, random forests, and neural networks.

The training data consists of features (indicator values) and labels
(future N-day returns, discretized into BUY, SELL, HOLD).
