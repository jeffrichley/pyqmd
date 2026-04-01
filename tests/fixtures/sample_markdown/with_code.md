# Python Examples

## Reading Data

Use pandas to read CSV files:

```python
import pandas as pd

df = pd.read_csv("data.csv")
print(df.head())
```

## Plotting

Create a simple plot:

```python
import matplotlib.pyplot as plt

plt.plot(df["x"], df["y"])
plt.title("My Plot")
plt.show()
```
