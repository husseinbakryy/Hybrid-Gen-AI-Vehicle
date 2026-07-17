import pandas as pd

# 1. Define the logic
def get_trip_output(df):
    # Business Logic for Trip Duration
    # Assumption: Avg speed 60km/h
    df['trip_duration_mins'] = (df['distance_km'] / 60) * 60
    
    # Business Logic for Range
    # Assumption: 0.16 kWh/km consumption
    df['remaining_range_km'] = (df['usable_battery_kwh'] * (df['battery_soc_start'] / 100)) / 0.16
    
    return df

# 2. TEST IT (Create a tiny dummy data to see the output)
data = {
    'distance_km': [50, 100, 20],
    'usable_battery_kwh': [60, 60, 60],
    'battery_soc_start': [80, 50, 10]
}
df_test = pd.DataFrame(data)

# 3. APPLY LOGIC
df_result = get_trip_output(df_test)

# 4. OUTPUT
print("--- CALCULATED BUSINESS LOGIC OUTPUT ---")
print(df_result[['trip_duration_mins', 'remaining_range_km']])