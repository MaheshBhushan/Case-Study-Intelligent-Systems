| scenario | policy | lead_time_h | on_time_rate | kwh_per_1000_good | oee | escaped_ppm | maintenance_h | mttr_h |
|---|---|---|---|---|---|---|---|---|
| low | FCFS | 185 ± 1.9 | 0.965 ± 0.0031 | 15 ± 0.22 | 0.82 ± 0.00086 | 465 ± 2.4 | 492 ± 12 | 5.11 ± 0.048 |
| base | FCFS | 201 ± 3.3 | 0.952 ± 0.0041 | 13.7 ± 0.19 | 0.82 ± 0.00072 | 463 ± 2.1 | 572 ± 11 | 5.15 ± 0.046 |
| high | FCFS | 246 ± 7.7 | 0.911 ± 0.0091 | 13 ± 0.15 | 0.82 ± 0.00069 | 465 ± 1.9 | 643 ± 11 | 5.18 ± 0.049 |
| harsh | FCFS | 206 ± 3.7 | 0.949 ± 0.0044 | 13.8 ± 0.19 | 0.809 ± 0.00078 | 497 ± 1.8 | 745 ± 14 | 5.21 ± 0.046 |
| low | SPT | 182 ± 1.5 | 0.964 ± 0.0033 | 15 ± 0.22 | 0.819 ± 0.00084 | 465 ± 2.3 | 492 ± 11 | 5.11 ± 0.049 |
| base | SPT | 196 ± 2.6 | 0.95 ± 0.0041 | 13.7 ± 0.19 | 0.819 ± 0.00073 | 463 ± 2 | 571 ± 11 | 5.14 ± 0.051 |
| high | SPT | 227 ± 5.3 | 0.914 ± 0.0064 | 12.9 ± 0.15 | 0.818 ± 0.00076 | 465 ± 1.9 | 640 ± 11 | 5.16 ± 0.044 |
| harsh | SPT | 199 ± 2.8 | 0.947 ± 0.0044 | 13.8 ± 0.19 | 0.808 ± 0.0008 | 498 ± 2 | 736 ± 14 | 5.18 ± 0.043 |
| low | SETUP | 185 ± 1.9 | 0.963 ± 0.0032 | 15 ± 0.22 | 0.821 ± 0.00089 | 468 ± 2.4 | 490 ± 11 | 5.11 ± 0.049 |
| base | SETUP | 203 ± 3.7 | 0.947 ± 0.0051 | 13.7 ± 0.19 | 0.824 ± 0.0009 | 464 ± 2.2 | 575 ± 11 | 5.18 ± 0.051 |
| high | SETUP | 245 ± 7.3 | 0.9 ± 0.011 | 13 ± 0.15 | 0.829 ± 0.00092 | 465 ± 1.8 | 634 ± 11 | 5.2 ± 0.047 |
| harsh | SETUP | 207 ± 4 | 0.943 ± 0.0053 | 13.7 ± 0.19 | 0.814 ± 0.0009 | 498 ± 2.1 | 737 ± 12 | 5.22 ± 0.043 |
| low | SETUP+PM | 183 ± 1.9 | 0.965 ± 0.0032 | 14.9 ± 0.23 | 0.835 ± 0.00086 | 406 ± 1.7 | 311 ± 8.9 | 4.17 ± 0.073 |
| base | SETUP+PM | 200 ± 3.4 | 0.951 ± 0.0047 | 13.6 ± 0.19 | 0.838 ± 0.00089 | 404 ± 1.5 | 364 ± 9.5 | 4.25 ± 0.067 |
| high | SETUP+PM | 239 ± 7.1 | 0.908 ± 0.01 | 12.9 ± 0.15 | 0.843 ± 0.00099 | 403 ± 1.5 | 400 ± 10 | 4.2 ± 0.069 |
| harsh | SETUP+PM | 201 ± 3.4 | 0.95 ± 0.005 | 13.7 ± 0.19 | 0.832 ± 0.00089 | 431 ± 1.5 | 446 ± 9.6 | 4.04 ± 0.054 |
| low | PRED-MO | 182 ± 1.6 | 0.971 ± 0.0027 | 14.1 ± 0.2 | 0.826 ± 0.00093 | 394 ± 2.5 | 304 ± 9.2 | 4.93 ± 0.098 |
| base | PRED-MO | 195 ± 2.7 | 0.965 ± 0.0033 | 13.2 ± 0.18 | 0.831 ± 0.00095 | 393 ± 2.2 | 350 ± 9.9 | 4.92 ± 0.092 |
| high | PRED-MO | 227 ± 5.6 | 0.942 ± 0.0067 | 12.7 ± 0.15 | 0.836 ± 0.00092 | 397 ± 2.3 | 392 ± 9.2 | 4.9 ± 0.085 |
| harsh | PRED-MO | 197 ± 2.8 | 0.963 ± 0.0036 | 13.3 ± 0.18 | 0.825 ± 0.00091 | 422 ± 2.2 | 448 ± 10 | 4.86 ± 0.081 |

| scenario   | kpi               | baseline   | policy   |   mean_diff |      ci |   rel_change_% |   p_value |
|:-----------|:------------------|:-----------|:---------|------------:|--------:|---------------:|----------:|
| low        | lead_time_h       | FCFS       | PRED-MO  |     -2.8595 |  0.5936 |        -1.5497 |    0      |
| base       | lead_time_h       | FCFS       | PRED-MO  |     -6.5701 |  0.948  |        -3.2608 |    0      |
| high       | lead_time_h       | FCFS       | PRED-MO  |    -19.2615 |  2.6924 |        -7.8351 |    0      |
| harsh      | lead_time_h       | FCFS       | PRED-MO  |     -8.9412 |  1.1759 |        -4.3478 |    0      |
| low        | on_time_rate      | FCFS       | PRED-MO  |      0.0056 |  0.0018 |         0.579  |    0      |
| base       | on_time_rate      | FCFS       | PRED-MO  |      0.0136 |  0.0028 |         1.4304 |    0      |
| high       | on_time_rate      | FCFS       | PRED-MO  |      0.0308 |  0.0047 |         3.3759 |    0      |
| harsh      | on_time_rate      | FCFS       | PRED-MO  |      0.0142 |  0.003  |         1.4929 |    0      |
| low        | kwh_per_1000_good | FCFS       | PRED-MO  |     -0.9077 |  0.0669 |        -6.0584 |    0      |
| base       | kwh_per_1000_good | FCFS       | PRED-MO  |     -0.5052 |  0.0528 |        -3.6809 |    0      |
| high       | kwh_per_1000_good | FCFS       | PRED-MO  |     -0.3011 |  0.048  |        -2.3204 |    0      |
| harsh      | kwh_per_1000_good | FCFS       | PRED-MO  |     -0.5009 |  0.0507 |        -3.6397 |    0      |
| low        | maintenance_h     | FCFS       | PRED-MO  |   -188.704  |  9.9328 |       -38.3182 |    0      |
| base       | maintenance_h     | FCFS       | PRED-MO  |   -221.751  |  8.9077 |       -38.7742 |    0      |
| high       | maintenance_h     | FCFS       | PRED-MO  |   -250.7    | 11.8367 |       -39.0107 |    0      |
| harsh      | maintenance_h     | FCFS       | PRED-MO  |   -296.397  | 11.6546 |       -39.8082 |    0      |
| low        | escaped_ppm       | FCFS       | PRED-MO  |    -70.4728 |  3.1412 |       -15.166  |    0      |
| base       | escaped_ppm       | FCFS       | PRED-MO  |    -70.3829 |  3.0533 |       -15.1901 |    0      |
| high       | escaped_ppm       | FCFS       | PRED-MO  |    -68.5652 |  2.5298 |       -14.7384 |    0      |
| harsh      | escaped_ppm       | FCFS       | PRED-MO  |    -75.2789 |  2.6458 |       -15.1499 |    0      |
| low        | lead_time_h       | SETUP      | PRED-MO  |     -3.5154 |  0.7437 |        -1.8984 |    0      |
| base       | lead_time_h       | SETUP      | PRED-MO  |     -7.8429 |  1.4985 |        -3.868  |    0      |
| high       | lead_time_h       | SETUP      | PRED-MO  |    -18.1744 |  2.7548 |        -7.4257 |    0      |
| harsh      | lead_time_h       | SETUP      | PRED-MO  |    -10.2735 |  1.6756 |        -4.9635 |    0      |
| low        | on_time_rate      | SETUP      | PRED-MO  |      0.0072 |  0.002  |         0.7433 |    0      |
| base       | on_time_rate      | SETUP      | PRED-MO  |      0.0177 |  0.0034 |         1.8735 |    0      |
| high       | on_time_rate      | SETUP      | PRED-MO  |      0.0421 |  0.007  |         4.6777 |    0      |
| harsh      | on_time_rate      | SETUP      | PRED-MO  |      0.02   |  0.0034 |         2.1149 |    0      |
| low        | kwh_per_1000_good | SETUP      | PRED-MO  |     -0.9094 |  0.0673 |        -6.0689 |    0      |
| base       | kwh_per_1000_good | SETUP      | PRED-MO  |     -0.5145 |  0.0526 |        -3.7467 |    0      |
| high       | kwh_per_1000_good | SETUP      | PRED-MO  |     -0.2859 |  0.0669 |        -2.206  |    0      |
| harsh      | kwh_per_1000_good | SETUP      | PRED-MO  |     -0.4761 |  0.0637 |        -3.4658 |    0      |
| low        | maintenance_h     | SETUP      | PRED-MO  |   -186.718  |  9.8939 |       -38.0684 |    0      |
| base       | maintenance_h     | SETUP      | PRED-MO  |   -224.871  | 10.1963 |       -39.1065 |    0      |
| high       | maintenance_h     | SETUP      | PRED-MO  |   -241.895  | 11.947  |       -38.1635 |    0      |
| harsh      | maintenance_h     | SETUP      | PRED-MO  |   -288.62   | 10.0983 |       -39.1729 |    0      |
| low        | escaped_ppm       | SETUP      | PRED-MO  |    -73.4776 |  3.4673 |       -15.7111 |    0      |
| base       | escaped_ppm       | SETUP      | PRED-MO  |    -71.5049 |  3.0319 |       -15.3949 |    0      |
| high       | escaped_ppm       | SETUP      | PRED-MO  |    -68.5845 |  2.4945 |       -14.7419 |    0      |
| harsh      | escaped_ppm       | SETUP      | PRED-MO  |    -75.8941 |  2.8673 |       -15.2548 |    0      |
| low        | lead_time_h       | SETUP+PM   | PRED-MO  |     -1.0888 |  0.692  |        -0.5958 |    0.0024 |
| base       | lead_time_h       | SETUP+PM   | PRED-MO  |     -5.0187 |  1.3878 |        -2.5102 |    0      |
| high       | lead_time_h       | SETUP+PM   | PRED-MO  |    -12.1081 |  2.8923 |        -5.0729 |    0      |
| harsh      | lead_time_h       | SETUP+PM   | PRED-MO  |     -4.0231 |  1.1837 |        -2.0042 |    0      |
| low        | on_time_rate      | SETUP+PM   | PRED-MO  |      0.0056 |  0.0019 |         0.5773 |    0      |
| base       | on_time_rate      | SETUP+PM   | PRED-MO  |      0.0143 |  0.003  |         1.5033 |    0      |
| high       | on_time_rate      | SETUP+PM   | PRED-MO  |      0.034  |  0.0061 |         3.7399 |    0      |
| harsh      | on_time_rate      | SETUP+PM   | PRED-MO  |      0.0132 |  0.003  |         1.3868 |    0      |
| low        | kwh_per_1000_good | SETUP+PM   | PRED-MO  |     -0.8597 |  0.067  |        -5.7565 |    0      |
| base       | kwh_per_1000_good | SETUP+PM   | PRED-MO  |     -0.4071 |  0.0567 |        -2.9876 |    0      |
| high       | kwh_per_1000_good | SETUP+PM   | PRED-MO  |     -0.1782 |  0.0646 |        -1.3864 |    0      |
| harsh      | kwh_per_1000_good | SETUP+PM   | PRED-MO  |     -0.4205 |  0.0525 |        -3.0734 |    0      |
| low        | maintenance_h     | SETUP+PM   | PRED-MO  |     -7.6276 | 10.2089 |        -2.4495 |    0.1414 |
| base       | maintenance_h     | SETUP+PM   | PRED-MO  |    -13.7634 | 10.7497 |        -3.782  |    0.0126 |
| high       | maintenance_h     | SETUP+PM   | PRED-MO  |     -8.1134 | 12.2769 |        -2.0281 |    0.1928 |
| harsh      | maintenance_h     | SETUP+PM   | PRED-MO  |      2.1548 | 10.0648 |         0.4831 |    0.6719 |
| low        | escaped_ppm       | SETUP+PM   | PRED-MO  |    -11.4042 |  3.1929 |        -2.8116 |    0      |
| base       | escaped_ppm       | SETUP+PM   | PRED-MO  |    -11.3523 |  2.6778 |        -2.8078 |    0      |
| high       | escaped_ppm       | SETUP+PM   | PRED-MO  |     -6.5462 |  2.695  |        -1.6236 |    0      |
| harsh      | escaped_ppm       | SETUP+PM   | PRED-MO  |     -8.8837 |  2.4929 |        -2.0636 |    0      |
