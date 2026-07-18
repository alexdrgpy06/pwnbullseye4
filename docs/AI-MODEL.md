# PwnBullseye4 AI Model Guide

## Overview

PwnBullseye4 uses a modern AI architecture based on **ONNX Runtime** for fast, non-blocking inference on resource-constrained Raspberry Pi Zero devices. This replaces the old TensorFlow 1.x / stable-baselines approach which was slow and blocked the UI.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PwnBullseye4 Agent                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Bettercap  │───▶│  Observation │───▶│  AsyncONNX   │  │
│  │   Events     │    │   Builder    │    │    Agent     │  │
│  └──────────────┘    └──────────────┘    └──────┬───────┘  │
│                                                 │           │
│                    ┌──────────────┐             │           │
│                    │  Fallback    │◀────────────┘           │
│                    │  Heuristic   │                         │
│                    └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

1. **AsyncONNXAgent** - Main inference engine
   - Loads ONNX model in background thread
   - Non-blocking `predict()` calls
   - Automatic fallback to heuristic policy

2. **HeuristicPolicy** - Fallback when model not ready
   - Random exploration actions
   - Ensures pwnagotchi works immediately on boot

3. **ONNX Model** - Pre-trained A2C policy
   - Exported from stable-baselines3
   - Quantized to INT8 for Pi Zero performance
   - Opset 11 for broad compatibility

## Model Specifications

| Property | Value |
|----------|-------|
| Algorithm | A2C with MlpLstmPolicy |
| Framework | stable-baselines3 → ONNX |
| Input Shape | (1, 34) - observation vector |
| Output | (1, 14) - action logits |
| Precision | FP32 (INT8 quantized available) |
| Size | ~2-4 MB |
| Inference Time | ~5ms (Pi Zero 2 W), ~20ms (Pi Zero W) |

## Observation Space (34 features)

```
[0-13]   AP features per channel (RSSI, encryption, clients, etc.)
[14-27]  Peer/grid features (nearby pwnagotchis)
[28-31]  Self state (epoch, uptime, battery, channel)
[32-33]  Global stats (total APs, total handshakes)
```

## Action Space (14 actions)

```
0-10     Channel hop (1-11)
11       Deauth strongest client
12       Associate with best AP
13       Passive listen (no action)
```

## Training Pipeline

### 1. Environment Setup

```bash
cd /h/pwnbullseye4/ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Train Model

```bash
# Quick training (for testing)
python3 train.py --timesteps 50000 --output models/brain_test.zip

# Full training (recommended 1M+ steps)
python3 train.py --timesteps 1000000 --output models/brain.zip
```

### 3. Export to ONNX

```bash
python3 export_onnx.py models/brain.zip /root/brain.onnx
```

### 4. Quantize to INT8 (optional, for speed)

```bash
python3 quantize.py /root/brain.onnx /root/brain_int8.onnx
```

## Files in `/h/pwnbullseye4/ai/`

```
ai/
├── train.py              # Main training script
├── export_onnx.py        # ONNX export utility
├── quantize.py           # INT8 quantization
├── async_agent.py        # Async ONNX inference agent
├── models/               # Pre-trained models
│   ├── brain.onnx        # FP32 model (included in image)
│   └── brain_int8.onnx   # INT8 quantized (optional)
└── requirements.txt      # Python dependencies
```

## Configuration (in defaults.toml)

```toml
# AI Configuration
ai.enabled = true
ai.path = "/root/brain.onnx"
ai.inference_backend = "onnxruntime"
ai.async_inference = true
ai.fallback_policy = "heuristic"
ai.laziness = 0.1
ai.epochs_per_episode = 50
```

## Performance Targets

| Device | Model | Inference | Boot to Ready |
|--------|-------|-----------|---------------|
| Pi Zero W | FP32 | ~20ms | ~30s |
| Pi Zero W | INT8 | ~8ms | ~25s |
| Pi Zero 2 W | FP32 | ~5ms | ~15s |
| Pi Zero 2 W | INT8 | ~2ms | ~10s |

## Troubleshooting

### Model Not Loading

```bash
# Check file exists
ls -la /root/brain.onnx

# Check ONNX Runtime
pip3 list | grep onnx

# Check logs
sudo journalctl -u pwnagotchi -f | grep -i ai
```

### Slow Inference

```bash
# Verify quantization
python3 -c "
import onnxruntime as ort
sess = ort.InferenceSession('/root/brain.onnx')
print('Providers:', sess.get_providers())
print('Input:', sess.get_inputs()[0])
"
```

### Fallback Policy Active

If you see `fallback_rate` > 0.1 in AI stats:
- Model failed to load (check path/permissions)
- ONNX Runtime not installed correctly
- Model architecture mismatch

## Custom Training

### Modify Reward Function

Edit `train.py` reward configuration:

```python
reward_config = {
    'handshake': 10.0,      # Reward for capturing handshake
    'deauth': -0.1,         # Small penalty for deauth
    'associate': -0.05,     # Penalty for association
    'new_ap': 1.0,          # Reward for discovering new AP
    'new_client': 0.5,      # Reward for new client
    'peer_meet': 2.0,       # Bonus for meeting peer
    'epoch_penalty': -0.01  # Small time penalty
}
```

### Change Network Architecture

```python
policy_kwargs = dict(
    net_arch=[128, 128],    # Two hidden layers
    lstm_hidden_size=256,   # LSTM size
    activation_fn=nn.ReLU
)
```

### Different Algorithm

```python
# PPO instead of A2C
from stable_baselines3 import PPO
model = PPO("MlpLstmPolicy", env, policy_kwargs=policy_kwargs, **params)
```

## Model Versioning

Models are versioned with the image:
- `brain_v1.onnx` - Initial release
- `brain_v2.onnx` - Improved reward shaping
- `brain_v3.onnx` - INT8 optimized

Check version in logs:
```
[INFO] [ai] Loaded model: brain_v2.onnx (A2C, 14 actions, 34 obs)
```

## Deployment

The model is baked into the image at `/root/brain.onnx`. To update:

1. Build new model using training pipeline
2. Replace `/root/brain.onnx` on device:
   ```bash
   scp brain_new.onnx pi@pwnbullseye4.local:/tmp/
   ssh pi@pwnbullseye4.local "sudo mv /tmp/brain_new.onnx /root/brain.onnx && sudo systemctl restart pwnagotchi"
   ```

3. Or rebuild image with new model in `stage3/05-install-pwnagotchi/`

## Monitoring AI Performance

### Web UI
- `http://pwnbullseye4.local:8080/ai` - AI stats page
- Shows: inference time, fallback rate, current policy

### CLI
```bash
# Real-time AI stats
watch -n 5 'curl -s http://localhost:8080/api/ai/stats | jq'

# View epoch history
cat /var/tmp/pwnagotchi/sessions/latest.json | jq '.ai'
```

## Research & Experiments

For experimentation, see:
- `ai/experiments/` - Notebooks for hyperparameter tuning
- `ai/benchmarks/` - Inference benchmarks on Pi hardware
- `ai/analysis/` - Reward analysis and policy visualization

## References

- [stable-baselines3 A2C](https://stable-baselines3.readthedocs.io/en/master/modules/a2c.html)
- [ONNX Runtime](https://onnxruntime.ai/)
- [ONNX Quantization](https://onnxruntime.ai/docs/performance/quantization.html)
- Original pwnagotchi AI: https://github.com/evilsocket/pwnagotchi/blob/master/pwnagotchi/ai/