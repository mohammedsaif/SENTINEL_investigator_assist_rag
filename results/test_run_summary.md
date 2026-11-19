| transaction_id | label | risk | action | reason codes | cites | correct |
|---|---|---|---|---|---|---|
| TX_0000082299 | fraud | HIGH | HOLD_FOR_REVIEW | AMT_HIGH, AMT_ABS_HIGH, VELOCITY_1H, NIGHT_TXN, RECENT_FAILURES | 1 | yes |
| TX_0000082609 | fraud | MEDIUM | HOLD_FOR_REVIEW | NIGHT_TXN, RECENT_FAILURES | 2 | yes |
| TX_0000083035 | fraud | HIGH | HOLD_FOR_REVIEW | AMT_HIGH, VELOCITY_1H, NIGHT_TXN, RECENT_FAILURES, MCC_HIGH_RISK | 1 | yes |
| TX_0000083044 | fraud | HIGH | HOLD_FOR_REVIEW | AMT_ABS_HIGH, NIGHT_TXN, RECENT_FAILURES | 0 | yes |
| TX_0000083048 | fraud | HIGH | HOLD_FOR_REVIEW | AMT_HIGH, NIGHT_TXN, RECENT_FAILURES | 0 | yes |
| TX_0000082051 | genuine | LOW | APPROVE | NIGHT_TXN | 1 | yes |
| TX_0000082052 | genuine | MEDIUM | STEP_UP_AUTH | NEW_DEVICE, NIGHT_TXN | 1 | no |
| TX_0000082053 | genuine | LOW | APPROVE | NIGHT_TXN | 1 | yes |
| TX_0000082054 | genuine | LOW | STEP_UP_AUTH | NIGHT_TXN | 1 | no |
| TX_0000082055 | genuine | MEDIUM | STEP_UP_AUTH | NIGHT_TXN, RECENT_FAILURES | 2 | no |

Flag-vs-label agreement: **70%** (anything other than APPROVE counts as flagged)
