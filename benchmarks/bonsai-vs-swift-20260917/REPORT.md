# Bonsai versus Swift on R9700

Every timed entry uses the same native Lucebox build. Bonsai includes its packed HIP kernels and signed Hadamard transforms. Prism is used only for prior numerical qualification.

**Method:** one run per task, thinking enabled with xhigh requested, temperature 0, seed 42, identical frozen template and 16 prompts. Six quality tasks have unchanged strict format/answer checks. Ten article speed tasks check completion only; their code correctness is not established. Results are preliminary, without confidence intervals.

## All 16 tasks

| Configuration | Completed | Quality passed | Wall s | Prefill s | Decode s | Output tokens | Thinking tokens | Decode tok/s | Wall speedup vs Swift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Swift IQ4_XS | 16/16 | 6/6 measured | 210.57 | 3.06 | 207.37 | 7042 | 5317 | 33.96 | 1.00× |
| Bonsai PQ2_0 | 16/16 | 6/6 measured | 206.36 | 3.15 | 202.83 | 8335 | 6703 | 41.09 | 1.02× |
| Bonsai PTQ1_0 | 16/16 | 6/6 measured | 348.63 | 8.81 | 339.66 | 10853 | 9235 | 31.95 | 0.60× |
| Bonsai Q2_0 | 16/16 | 6/6 measured | 207.45 | 3.14 | 204.15 | 8335 | 6703 | 40.83 | 1.02× |
| Swift IQ4_XS + DFlash2 | 16/16 | 6/6 measured | 85.01 | 3.15 | 81.72 | 7322 | 5698 | 89.60 | 2.48× |

## Six quality tasks

| Configuration | Completed | Quality passed | Wall s | Prefill s | Decode s | Output tokens | Thinking tokens | Decode tok/s | Wall speedup vs Swift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Swift IQ4_XS | 6/6 | 6/6 measured | 50.47 | 1.14 | 49.29 | 1680 | 1559 | 34.09 | 1.00× |
| Bonsai PQ2_0 | 6/6 | 6/6 measured | 55.56 | 1.18 | 54.19 | 2222 | 2101 | 41.00 | 0.91× |
| Bonsai PTQ1_0 | 6/6 | 6/6 measured | 70.26 | 3.03 | 67.17 | 2151 | 2030 | 32.02 | 0.72× |
| Bonsai Q2_0 | 6/6 | 6/6 measured | 55.81 | 1.18 | 54.57 | 2222 | 2101 | 40.72 | 0.90× |
| Swift IQ4_XS + DFlash2 | 6/6 | 6/6 measured | 20.85 | 1.17 | 19.63 | 1717 | 1596 | 87.45 | 2.42× |

## Ten article speed tasks

| Configuration | Completed | Quality passed | Wall s | Prefill s | Decode s | Output tokens | Thinking tokens | Decode tok/s | Wall speedup vs Swift |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Swift IQ4_XS | 10/10 | Not scored | 160.10 | 1.92 | 158.09 | 5362 | 3758 | 33.92 | 1.00× |
| Bonsai PQ2_0 | 10/10 | Not scored | 150.80 | 1.97 | 148.64 | 6113 | 4602 | 41.13 | 1.06× |
| Bonsai PTQ1_0 | 10/10 | Not scored | 278.37 | 5.78 | 272.49 | 8702 | 7205 | 31.94 | 0.58× |
| Bonsai Q2_0 | 10/10 | Not scored | 151.64 | 1.96 | 149.58 | 6113 | 4602 | 40.87 | 1.06× |
| Swift IQ4_XS + DFlash2 | 10/10 | Not scored | 64.16 | 1.99 | 62.09 | 5605 | 4102 | 90.27 | 2.50× |

Decode rate is total generated tokens divided by total measured decode time, including thinking. Wall time excludes model loading and warmup. Partial totals must not be compared with complete suites. Shorter reasoning can improve task time without faster kernels.

## Per-task results

| Configuration | Task | Wall s | Prefill ms | Decode ms | Output tokens | Thinking tokens | Result |
|---|---|---:|---:|---:|---:|---:|---|
| Swift IQ4_XS | arithmetic | 15.75 | 197.2 | 15547.1 | 528 | 518 | pass |
| Swift IQ4_XS | constraints | 4.75 | 134.0 | 4608.1 | 158 | 145 | pass |
| Swift IQ4_XS | code_aliasing | 8.31 | 135.3 | 8165.5 | 279 | 258 | pass |
| Swift IQ4_XS | code_intervals | 15.71 | 132.3 | 15572.6 | 530 | 503 | pass |
| Swift IQ4_XS | extraction | 3.62 | 171.8 | 3443.5 | 118 | 109 | pass |
| Swift IQ4_XS | tool_call | 2.33 | 366.8 | 1950.4 | 67 | 26 | pass |
| Swift IQ4_XS | has_close_elements | 22.45 | 199.2 | 22238.1 | 755 | 581 | completed; correctness unscored |
| Swift IQ4_XS | separate_paren_groups | 27.80 | 202.2 | 27588.5 | 935 | 707 | completed; correctness unscored |
| Swift IQ4_XS | truncate_number | 13.43 | 167.7 | 13250.2 | 450 | 352 | completed; correctness unscored |
| Swift IQ4_XS | below_zero | 10.39 | 194.0 | 10182.8 | 346 | 188 | completed; correctness unscored |
| Swift IQ4_XS | mean_absolute_deviation | 13.89 | 193.0 | 13692.3 | 465 | 296 | completed; correctness unscored |
| Swift IQ4_XS | intersperse | 15.47 | 189.9 | 15271.1 | 518 | 379 | completed; correctness unscored |
| Swift IQ4_XS | parse_nested_parens | 27.48 | 198.4 | 27271.3 | 922 | 707 | completed; correctness unscored |
| Swift IQ4_XS | filter_by_substring | 6.10 | 188.0 | 5906.5 | 201 | 88 | completed; correctness unscored |
| Swift IQ4_XS | sum_product | 11.22 | 196.3 | 11018.1 | 374 | 216 | completed; correctness unscored |
| Swift IQ4_XS | rolling_max | 11.87 | 193.9 | 11668.8 | 396 | 244 | completed; correctness unscored |
| Bonsai PQ2_0 | arithmetic | 25.62 | 205.4 | 25371.0 | 1007 | 997 | pass |
| Bonsai PQ2_0 | constraints | 4.08 | 142.3 | 3908.3 | 166 | 153 | pass |
| Bonsai PQ2_0 | code_aliasing | 9.16 | 142.1 | 8994.4 | 380 | 359 | pass |
| Bonsai PQ2_0 | code_intervals | 11.66 | 137.9 | 11506.0 | 487 | 460 | pass |
| Bonsai PQ2_0 | extraction | 3.05 | 178.4 | 2851.0 | 121 | 112 | pass |
| Bonsai PQ2_0 | tool_call | 2.00 | 374.5 | 1562.7 | 61 | 20 | pass |
| Bonsai PQ2_0 | has_close_elements | 27.76 | 211.4 | 27532.1 | 1121 | 943 | completed; correctness unscored |
| Bonsai PQ2_0 | separate_paren_groups | 23.96 | 207.2 | 23723.9 | 982 | 754 | completed; correctness unscored |
| Bonsai PQ2_0 | truncate_number | 14.95 | 175.9 | 14747.2 | 605 | 507 | completed; correctness unscored |
| Bonsai PQ2_0 | below_zero | 8.74 | 205.5 | 8511.9 | 354 | 196 | completed; correctness unscored |
| Bonsai PQ2_0 | mean_absolute_deviation | 23.85 | 200.1 | 23630.4 | 962 | 797 | completed; correctness unscored |
| Bonsai PQ2_0 | intersperse | 10.62 | 180.3 | 10424.2 | 439 | 296 | completed; correctness unscored |
| Bonsai PQ2_0 | parse_nested_parens | 17.51 | 207.7 | 17279.2 | 707 | 493 | completed; correctness unscored |
| Bonsai PQ2_0 | filter_by_substring | 3.72 | 179.1 | 3527.5 | 139 | 120 | completed; correctness unscored |
| Bonsai PQ2_0 | sum_product | 9.92 | 204.2 | 9699.4 | 406 | 250 | completed; correctness unscored |
| Bonsai PQ2_0 | rolling_max | 9.78 | 200.0 | 9563.6 | 398 | 246 | completed; correctness unscored |
| Bonsai PTQ1_0 | arithmetic | 28.06 | 566.8 | 27484.0 | 880 | 870 | pass |
| Bonsai PTQ1_0 | constraints | 7.15 | 366.4 | 6772.1 | 213 | 200 | pass |
| Bonsai PTQ1_0 | code_aliasing | 12.63 | 357.1 | 12264.9 | 389 | 368 | pass |
| Bonsai PTQ1_0 | code_intervals | 15.43 | 349.4 | 15074.6 | 487 | 460 | pass |
| Bonsai PTQ1_0 | extraction | 4.29 | 564.5 | 3719.0 | 121 | 112 | pass |
| Bonsai PTQ1_0 | tool_call | 2.69 | 824.1 | 1860.0 | 61 | 20 | pass |
| Bonsai PTQ1_0 | has_close_elements | 41.84 | 588.3 | 41244.1 | 1316 | 1138 | completed; correctness unscored |
| Bonsai PTQ1_0 | separate_paren_groups | 63.52 | 584.1 | 62927.1 | 2012 | 1784 | completed; correctness unscored |
| Bonsai PTQ1_0 | truncate_number | 30.35 | 561.5 | 29774.1 | 956 | 858 | completed; correctness unscored |
| Bonsai PTQ1_0 | below_zero | 10.61 | 580.9 | 10024.1 | 322 | 165 | completed; correctness unscored |
| Bonsai PTQ1_0 | mean_absolute_deviation | 63.63 | 578.6 | 63041.1 | 2007 | 1855 | completed; correctness unscored |
| Bonsai PTQ1_0 | intersperse | 14.25 | 566.7 | 13674.6 | 439 | 296 | completed; correctness unscored |
| Bonsai PTQ1_0 | parse_nested_parens | 22.53 | 587.1 | 21937.1 | 707 | 493 | completed; correctness unscored |
| Bonsai PTQ1_0 | filter_by_substring | 4.90 | 564.6 | 4323.5 | 139 | 120 | completed; correctness unscored |
| Bonsai PTQ1_0 | sum_product | 13.57 | 581.2 | 12981.3 | 406 | 250 | completed; correctness unscored |
| Bonsai PTQ1_0 | rolling_max | 13.16 | 584.3 | 12563.1 | 398 | 246 | completed; correctness unscored |
| Bonsai Q2_0 | arithmetic | 24.85 | 205.7 | 24637.0 | 1007 | 997 | pass |
| Bonsai Q2_0 | constraints | 4.31 | 150.2 | 4147.6 | 166 | 153 | pass |
| Bonsai Q2_0 | code_aliasing | 9.47 | 141.4 | 9317.8 | 380 | 359 | pass |
| Bonsai Q2_0 | code_intervals | 12.11 | 140.2 | 11962.2 | 487 | 460 | pass |
| Bonsai Q2_0 | extraction | 3.24 | 183.0 | 3048.4 | 121 | 112 | pass |
| Bonsai Q2_0 | tool_call | 1.83 | 356.4 | 1460.6 | 61 | 20 | pass |
| Bonsai Q2_0 | has_close_elements | 27.48 | 211.0 | 27253.8 | 1121 | 943 | completed; correctness unscored |
| Bonsai Q2_0 | separate_paren_groups | 24.47 | 213.7 | 24239.0 | 982 | 754 | completed; correctness unscored |
| Bonsai Q2_0 | truncate_number | 14.88 | 172.8 | 14694.7 | 605 | 507 | completed; correctness unscored |
| Bonsai Q2_0 | below_zero | 8.79 | 201.0 | 8577.4 | 354 | 196 | completed; correctness unscored |
| Bonsai Q2_0 | mean_absolute_deviation | 24.09 | 199.8 | 23878.6 | 962 | 797 | completed; correctness unscored |
| Bonsai Q2_0 | intersperse | 10.96 | 180.6 | 10766.4 | 439 | 296 | completed; correctness unscored |
| Bonsai Q2_0 | parse_nested_parens | 17.48 | 207.9 | 17260.5 | 707 | 493 | completed; correctness unscored |
| Bonsai Q2_0 | filter_by_substring | 3.52 | 175.4 | 3338.0 | 139 | 120 | completed; correctness unscored |
| Bonsai Q2_0 | sum_product | 10.02 | 200.3 | 9812.7 | 406 | 250 | completed; correctness unscored |
| Bonsai Q2_0 | rolling_max | 9.97 | 198.9 | 9758.0 | 398 | 246 | completed; correctness unscored |
| Swift IQ4_XS + DFlash2 | arithmetic | 6.56 | 203.6 | 6349.4 | 534 | 524 | pass |
| Swift IQ4_XS + DFlash2 | constraints | 1.78 | 139.1 | 1635.6 | 130 | 117 | pass |
| Swift IQ4_XS + DFlash2 | code_aliasing | 3.36 | 142.0 | 3210.7 | 287 | 266 | pass |
| Swift IQ4_XS + DFlash2 | code_intervals | 6.32 | 138.0 | 6168.9 | 573 | 546 | pass |
| Swift IQ4_XS + DFlash2 | extraction | 1.56 | 178.8 | 1369.0 | 118 | 109 | pass |
| Swift IQ4_XS + DFlash2 | tool_call | 1.28 | 366.2 | 899.5 | 75 | 34 | pass |
| Swift IQ4_XS + DFlash2 | has_close_elements | 8.96 | 208.8 | 8737.4 | 770 | 596 | completed; correctness unscored |
| Swift IQ4_XS + DFlash2 | separate_paren_groups | 16.43 | 204.1 | 16214.2 | 1233 | 1012 | completed; correctness unscored |
| Swift IQ4_XS + DFlash2 | truncate_number | 6.93 | 174.0 | 6746.0 | 506 | 493 | completed; correctness unscored |
| Swift IQ4_XS + DFlash2 | below_zero | 3.37 | 201.9 | 3158.7 | 308 | 150 | completed; correctness unscored |
| Swift IQ4_XS + DFlash2 | mean_absolute_deviation | 9.85 | 200.6 | 9643.0 | 725 | 560 | completed; correctness unscored |
| Swift IQ4_XS + DFlash2 | intersperse | 2.74 | 195.9 | 2539.0 | 347 | 208 | completed; correctness unscored |
| Swift IQ4_XS + DFlash2 | parse_nested_parens | 7.51 | 205.3 | 7295.6 | 744 | 532 | completed; correctness unscored |
| Swift IQ4_XS + DFlash2 | filter_by_substring | 1.92 | 193.3 | 1714.0 | 201 | 88 | completed; correctness unscored |
| Swift IQ4_XS + DFlash2 | sum_product | 2.89 | 202.1 | 2677.9 | 375 | 219 | completed; correctness unscored |
| Swift IQ4_XS + DFlash2 | rolling_max | 3.57 | 199.8 | 3363.2 | 396 | 244 | completed; correctness unscored |

## DFlash2 verification

| Configuration | Speculation actually ran | Median request acceptance |
|---|---:|---:|
| Swift IQ4_XS + DFlash2 | 16/16 | 38.03% |

Acceptance is the median of native per-request rates, not a pooled token-weighted acceptance estimate.

## Quality failures

No failed quality checks among measured requests; see coverage above.

## Limits and reproducibility

- All reasoning counts come from native usage accounting. Other output tokens include any protocol/control tokens counted by the runtime; they are not necessarily just visible answer text.
- The same xhigh setting does not imply equal reasoning length. Maximum output is 64,000 within a 65,536 context; reaching the length ceiling is not normal completion.
- Post-request VRAM observations are not peak memory measurements. No synthetic throughput microbenchmark or thermal/order randomization is included in this first pass.
- Target-only results and the separately selected Bonsai DFlash2 follow-up are labelled explicitly. Shared ancestry alone is not treated as evidence of drafter compatibility.
- The private build uses the same Q8 K/V kernels for every entry with FA_ALL_QUANTS=OFF. This is not a production deployment.
- Numerical qualification compares fixed-token final logits with Prism and batched versus incremental processing. It does not establish bit-identical long generations or broader model quality.
- Prompt counts match Swift for all available matched cases.

Evidence: [raw requests and responses](results.json), [CSV measurements](measurements.csv), [launch arguments](launch.json), [provenance](provenance.json), [numerical qualification](qualification/numerical-results.json).
