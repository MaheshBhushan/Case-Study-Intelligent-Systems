PRED-MO minus SETUP+PM (relative %, paired over common seeds; * = p < 0.05).

| parameter | level | value | lead_time_h | on_time_rate | kwh_per_1000_good | maintenance_h | escaped_ppm | oee |
|---|---|---|---|---|---|---|---|---|
| baseline | base |  | -2.6* | +1.4* | -3.1* | -2.7 | -2.4* | -0.9* |
| demand | low | 540 | -0.5 | +0.9* | -5.6* | -2.4 | -2.0* | -1.0* |
| demand | high | 430 | -4.2* | +2.8* | -2.4* | -3.7 | -2.1* | -0.8* |
| wear_rate | low | 0.004 | -2.4* | +1.1* | -4.1* | -1.5 | -12.7* | -0.7* |
| wear_rate | high | 0.012 | -2.1* | +0.8* | -3.1* | -3.1 | +2.2* | -1.0* |
| repair_time | low | 0.5 | -2.6* | +1.3* | -3.8* | +8.9* | -2.5* | -1.1* |
| repair_time | high | 1.5 | -2.7* | +1.6* | -3.4* | -6.2* | -1.9* | -0.7* |
| technicians | low | 1 | -2.7* | +1.4* | -3.9* | -3.9 | -2.5* | -0.9* |
| technicians | high | 3 | -2.6* | +1.4* | -3.0* | -3.0 | -2.3* | -0.9* |
| setters | low | 2 | -2.6* | +1.5* | -3.0* | -3.8 | -2.5* | -0.8* |
| setters | high | 4 | -2.6* | +1.4* | -3.1* | -3.5 | -2.4* | -0.9* |
| mould_change | low | 90 | -2.3* | +1.3* | -3.5* | +2.1 | -2.3* | -1.0* |
| mould_change | high | 180 | -2.8* | +1.5* | -3.7* | -2.5 | -2.5* | -0.9* |
| pm_duration | low | 60 | -2.4* | +1.3* | -3.3* | -12.7* | -2.5* | -0.7* |
| pm_duration | high | 240 | -2.7* | +1.6* | -3.6* | +8.6* | -2.5* | -1.1* |
| qa_hold | low | 1440 | -2.9* | +1.6* | -3.1* | -2.7 | -2.1* | -0.9* |
| qa_hold | high | 4320 | -2.3* | +1.7* | -3.6* | -2.7 | -2.6* | -0.9* |
| hvac | low | 60 | -2.6* | +1.4* | -3.7* | -2.7 | -2.4* | -0.9* |
| hvac | high | 180 | -2.6* | +1.4* | -2.6* | -2.7 | -2.4* | -0.9* |
| camera | low | 0.95 | -2.6* | +1.4* | -3.1* | -2.7 | -2.6* | -0.9* |
| camera | high | 0.995 | -2.6* | +1.4* | -3.1* | -2.7 | -3.1* | -0.9* |

Parameters:

- `demand`: mean order interarrival [min] (base 480)
- `wear_rate`: screw wear per running min (base 0.008)
- `repair_time`: repair time multiplier (base 1.0)
- `technicians`: maintenance technicians (base 2)
- `setters`: day-shift setters (base 3)
- `mould_change`: mould change [min] (base 120)
- `pm_duration`: planned maintenance [min] (base 120)
- `qa_hold`: QA release hold mean [min] (base 2880)
- `hvac`: clean-room HVAC load [kW] (base 120)
- `camera`: camera defect detection (base 0.98)
