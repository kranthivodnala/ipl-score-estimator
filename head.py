import pandas as pd
df = pd.read_csv('ipl.csv')
print(df.shape)
print(df.columns.tolist())
print(df.head(2))
