# Crypto Predictions Debug - 22 Jan 2026

## Problem
User saw BTC prediction in Telegram at 22:40 but PWA shows 0 crypto predictions.

## Investigation

### What I Found

1. **Telegram notification WAS sent** at 22:40:43:
   ```
   🔮 Crypto prediction sent: 1 events for L3_crypto_crypto_crypto_crypto_crypto_crypto_quantum_rng_space_weather
   ```

2. **Anomaly log shows predictions WERE generated** at 22:40:49:
   - Level 3 cluster (crypto + quantum_rng + space_weather)
   - Probabilities:
     - `btc_volatility_medium`: 21% probability (category: crypto)
     - `earthquake_strong`: 100% probability (category: earthquake)

3. **Current predictions file has 0 crypto predictions**:
   - Total: 50 predictions
   - Crypto: 0
   - All predictions are earthquakes

4. **140 crypto patterns exist** in patterns.json with ≥5 observations

5. **Test confirmed PWA CAN display crypto predictions** when manually added to file

### Root Cause Analysis

The code flow in `_handle_anomaly` (main.py line ~615):
```python
probabilities = self.pattern_tracker.get_probabilities(condition, category_filter=None)

# Save predictions to file for PWA
if probabilities:
    self._save_predictions_to_file(condition, probabilities)  # ← Should save ALL predictions

# Send to Telegram (filters to crypto ≥40%)
if probabilities:
    await self._send_prediction_notification(condition, probabilities)  # ← Filters to crypto ≥40%
```

**The bug**: `_save_predictions_to_file` should save ALL predictions (including crypto with 21% probability), but somehow crypto predictions are not being saved to the file.

### Possible Causes

1. **`_save_predictions_to_file` not being called** - but Telegram notification was sent, so probabilities dict was not empty
2. **Exception in `_save_predictions_to_file`** - would show error log (none found)
3. **Filtering logic removing crypto predictions** - checked code, no such filter
4. **Race condition with `_refresh_predictions_file`** - tested, refresh task preserves crypto predictions

### Changes Made

Added detailed INFO-level logging to `_save_predictions_to_file`:
- Log when function is called with number of events
- Log number of existing predictions loaded
- Log merge results
- Log filtering results
- Log category breakdown (crypto vs earthquake)

### Next Steps

**Waiting for next Level 3 cluster** to see detailed logs and identify where crypto predictions are being lost.

System is running with enhanced logging. When next Level 3 cluster occurs, logs will show:
```
💾 Saving predictions: X events for L3_...
💾 Loaded Y existing predictions
💾 Merged: Y existing + X new = Z total
💾 After filtering: Z active predictions
💾 Categories: N crypto, M earthquake
```

This will reveal exactly where crypto predictions disappear.

## Temporary Workaround

Added test crypto prediction to file - PWA displays it correctly. This confirms:
- PWA API works
- File reading works
- Display logic works

**The issue is in the prediction saving logic, not the display logic.**
