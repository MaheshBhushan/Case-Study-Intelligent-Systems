| scenario | policy | throughput_uph | lead_time_h | on_time_rate | kwh_per_1000_good | scrap_rate | maintenance_h | recovery_h |
|---|---|---|---|---|---|---|---|---|
| low | FCFS | 1.71e+03 ± 26 | 15.1 ± 0.72 | 0.955 ± 0.0067 | 79 ± 0.93 | 0.0571 ± 0.00036 | 22.4 ± 1.4 | 15.6 ± 0.95 |
| base | FCFS | 1.94e+03 ± 22 | 23.1 ± 1.7 | 0.889 ± 0.016 | 72.3 ± 0.64 | 0.0568 ± 0.00036 | 27.3 ± 1.4 | 25.3 ± 2.1 |
| high | FCFS | 2.03e+03 ± 16 | 41 ± 2.9 | 0.714 ± 0.033 | 70.4 ± 0.51 | 0.0567 ± 0.00033 | 28.6 ± 1.3 | 46.4 ± 3.4 |
| harsh | FCFS | 1.93e+03 ± 21 | 24.9 ± 1.9 | 0.873 ± 0.017 | 72.5 ± 0.63 | 0.0576 ± 0.00032 | 35.1 ± 1.3 | 25.8 ± 2 |
| low | SPT | 1.72e+03 ± 26 | 14 ± 0.44 | 0.966 ± 0.0042 | 78.8 ± 0.94 | 0.0572 ± 0.0004 | 21.9 ± 1.5 | 23.9 ± 3.6 |
| base | SPT | 1.96e+03 ± 25 | 19 ± 0.98 | 0.928 ± 0.0078 | 71.3 ± 0.71 | 0.057 ± 0.00033 | 26 ± 1.2 | 66.7 ± 8.8 |
| high | SPT | 2.1e+03 ± 19 | 29.5 ± 1.7 | 0.861 ± 0.011 | 67.2 ± 0.51 | 0.0571 ± 0.00038 | 27 ± 1.2 | 138 ± 9.9 |
| harsh | SPT | 1.95e+03 ± 24 | 20 ± 1.1 | 0.92 ± 0.0082 | 71.3 ± 0.7 | 0.0577 ± 0.00031 | 34.8 ± 1.3 | 77.9 ± 10 |
| low | SETUP | 1.73e+03 ± 29 | 13 ± 0.25 | 0.973 ± 0.0036 | 78.8 ± 0.98 | 0.0549 ± 0.00038 | 21.9 ± 1.5 | 13.9 ± 0.56 |
| base | SETUP | 2.03e+03 ± 34 | 15 ± 0.47 | 0.956 ± 0.0049 | 70.2 ± 0.84 | 0.0529 ± 0.00046 | 28.1 ± 1.3 | 16.4 ± 0.65 |
| high | SETUP | 2.3e+03 ± 32 | 19.4 ± 1 | 0.921 ± 0.009 | 64.4 ± 0.64 | 0.0504 ± 0.00046 | 31.4 ± 1.4 | 22.3 ± 1.3 |
| harsh | SETUP | 2.03e+03 ± 33 | 15.3 ± 0.47 | 0.954 ± 0.0053 | 70.2 ± 0.82 | 0.0539 ± 0.00037 | 37.9 ± 1.8 | 17.4 ± 0.67 |
| low | PRED-MO | 1.75e+03 ± 29 | 12.7 ± 0.19 | 0.986 ± 0.002 | 76.9 ± 0.87 | 0.0467 ± 0.00054 | 12.6 ± 1.3 | 13.1 ± 1.3 |
| base | PRED-MO | 2.04e+03 ± 34 | 14.3 ± 0.39 | 0.984 ± 0.0021 | 69.2 ± 0.77 | 0.0453 ± 0.00043 | 14.1 ± 1.1 | 17.3 ± 1.9 |
| high | PRED-MO | 2.32e+03 ± 33 | 17.8 ± 0.82 | 0.975 ± 0.0055 | 63.6 ± 0.62 | 0.0439 ± 0.00045 | 16.1 ± 1.1 | 28.3 ± 2.9 |
| harsh | PRED-MO | 2.05e+03 ± 34 | 14.4 ± 0.4 | 0.983 ± 0.0023 | 69.1 ± 0.77 | 0.0446 ± 0.00038 | 18.7 ± 1.4 | 17.1 ± 1.6 |

| scenario   | kpi               | baseline   | policy   |   mean_diff |     ci |   rel_change_% |   p_value |
|:-----------|:------------------|:-----------|:---------|------------:|-------:|---------------:|----------:|
| low        | lead_time_h       | FCFS       | PRED-MO  |     -2.4475 | 0.5605 |       -16.1804 |         0 |
| base       | lead_time_h       | FCFS       | PRED-MO  |     -8.8132 | 1.4285 |       -38.1281 |         0 |
| high       | lead_time_h       | FCFS       | PRED-MO  |    -23.2702 | 2.316  |       -56.6946 |         0 |
| harsh      | lead_time_h       | FCFS       | PRED-MO  |    -10.4948 | 1.5517 |       -42.2046 |         0 |
| low        | on_time_rate      | FCFS       | PRED-MO  |      0.0317 | 0.0061 |         3.3233 |         0 |
| base       | on_time_rate      | FCFS       | PRED-MO  |      0.095  | 0.0148 |        10.6901 |         0 |
| high       | on_time_rate      | FCFS       | PRED-MO  |      0.2616 | 0.0309 |        36.6571 |         0 |
| harsh      | on_time_rate      | FCFS       | PRED-MO  |      0.1103 | 0.0165 |        12.6397 |         0 |
| low        | kwh_per_1000_good | FCFS       | PRED-MO  |     -2.1702 | 0.3241 |        -2.7458 |         0 |
| base       | kwh_per_1000_good | FCFS       | PRED-MO  |     -3.085  | 0.5349 |        -4.2666 |         0 |
| high       | kwh_per_1000_good | FCFS       | PRED-MO  |     -6.7597 | 0.6957 |        -9.6073 |         0 |
| harsh      | kwh_per_1000_good | FCFS       | PRED-MO  |     -3.3193 | 0.5577 |        -4.5809 |         0 |
| low        | maintenance_h     | FCFS       | PRED-MO  |     -9.8504 | 1.5432 |       -43.96   |         0 |
| base       | maintenance_h     | FCFS       | PRED-MO  |    -13.2411 | 1.6423 |       -48.5111 |         0 |
| high       | maintenance_h     | FCFS       | PRED-MO  |    -12.4501 | 1.5336 |       -43.5589 |         0 |
| harsh      | maintenance_h     | FCFS       | PRED-MO  |    -16.3837 | 1.6215 |       -46.7328 |         0 |
| low        | lead_time_h       | SETUP      | PRED-MO  |     -0.286  | 0.0911 |        -2.2058 |         0 |
| base       | lead_time_h       | SETUP      | PRED-MO  |     -0.6675 | 0.1284 |        -4.4594 |         0 |
| high       | lead_time_h       | SETUP      | PRED-MO  |     -1.6532 | 0.2202 |        -8.5097 |         0 |
| harsh      | lead_time_h       | SETUP      | PRED-MO  |     -0.9127 | 0.1304 |        -5.9717 |         0 |
| low        | on_time_rate      | SETUP      | PRED-MO  |      0.0132 | 0.003  |         1.3604 |         0 |
| base       | on_time_rate      | SETUP      | PRED-MO  |      0.0275 | 0.0038 |         2.8752 |         0 |
| high       | on_time_rate      | SETUP      | PRED-MO  |      0.0543 | 0.0064 |         5.8992 |         0 |
| harsh      | on_time_rate      | SETUP      | PRED-MO  |      0.0292 | 0.0042 |         3.0655 |         0 |
| low        | kwh_per_1000_good | SETUP      | PRED-MO  |     -1.9546 | 0.2172 |        -2.4797 |         0 |
| base       | kwh_per_1000_good | SETUP      | PRED-MO  |     -0.9326 | 0.1703 |        -1.3294 |         0 |
| high       | kwh_per_1000_good | SETUP      | PRED-MO  |     -0.7642 | 0.1601 |        -1.1873 |         0 |
| harsh      | kwh_per_1000_good | SETUP      | PRED-MO  |     -1.0213 | 0.1403 |        -1.4556 |         0 |
| low        | maintenance_h     | SETUP      | PRED-MO  |     -9.3562 | 1.6079 |       -42.6963 |         0 |
| base       | maintenance_h     | SETUP      | PRED-MO  |    -14.0798 | 1.4565 |       -50.046  |         0 |
| high       | maintenance_h     | SETUP      | PRED-MO  |    -15.2617 | 1.5774 |       -48.6137 |         0 |
| harsh      | maintenance_h     | SETUP      | PRED-MO  |    -19.1945 | 2.0339 |       -50.6865 |         0 |
