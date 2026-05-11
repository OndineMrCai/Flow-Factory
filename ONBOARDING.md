# Flow-Factory · VideoScore2 RL Baseline — Onboarding

End-to-end context for running the **Wan2.1-T2V-1.3B + VideoScore2 GRPO** baseline.
Config file: `examples/grpo/full/wan21_t2v_1.3b_videoscore2.yaml`

---

## 1. Install

### 1.1 Clone & core install

```bash
git clone <repo-url> Flow-Factory
cd Flow-Factory
pip install -e .
```

This installs everything in `pyproject.toml`'s `dependencies` — torch, diffusers, accelerate, transformers, **plus** `opencv-python-headless` and `qwen-vl-utils` (needed by the VideoScore2 reward).

### 1.2 Optional groups you also need

```bash
pip install -e ".[deepspeed]"   # ZeRO optimizer states
pip install -e ".[wandb]"       # experiment tracking
# Or do them all at once:
pip install -e ".[deepspeed,wandb]"
```

### 1.3 Flash-Attention 3 (required for 480x832 training)

The config sets `model.attn_backend: '_flash_3_hub'`. Install the kernels package — it fetches a prebuilt FA3 kernel from the HF kernels hub, no local compile:

```bash
pip install kernels
```

---

## 2. Set up wandb

### 2.1 Login

```bash
wandb login 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
```

> This key belongs to the project owner. Feel free to use it for now; switch to your own personal key if you prefer your runs attributed to you.

### 2.2 Confirm in config

The training YAML already has these set, no action needed:
```yaml
log:
  project: "Flow-Factory"
  logging_backend: "wandb"
```

Run names are auto-generated as `{model_type}_{finetune_type}_{trainer_type}_{timestamp}` — override with `log.run_name: "your-run-name"` if you want.

---

## 3. Dataset

Pre-baked at `dataset/videoscore2/` with:

```
dataset/videoscore2/
├── train.jsonl      # 2461 prompts + Wan official negative_prompt
└── test.jsonl       # 50 prompts + Wan official negative_prompt
```

Each line is:
```json
{"prompt": "...", "negative_prompt": "Bright tones, overexposed, static, ..."}
```

The data loader auto-detects `.jsonl` (preferred over `.txt`). No path changes needed in the config.

---

## 4. Launch — Single Node (smoke test first!)

Before going multi-node, run a 1-node smoke test to catch dependency / VRAM issues early:

```bash
# Override the multi-node fields via CLI
ff-train examples/grpo/full/wan21_t2v_1.3b_videoscore2.yaml \
  --num_machines 1 \
  --num_processes 8
```

This uses 8 GPUs on a single node. If it survives the first epoch (sampling + reward + 1 grad step), you're good to scale up.

---

## 5. Launch — Multi-Node (4 nodes × 8 GPUs = 32 ranks)

### 5.1 What's already configured in the YAML

```yaml
launcher: "accelerate"
config_file: multinode_examples/fsdp2_wan.yaml  # FSDP2 HYBRID_SHARD (shard within node, replicate across)
num_machines: 4
num_processes: 32
main_process_ip: "10.0.0.1"     # ← REPLACE with your real master IP
main_process_port: 29500
mixed_precision: "bf16"
```

**Update `main_process_ip`** to the internal IP of whichever node you designate as rank-0.

### 5.2 What you MUST set per-node (env var)

`MACHINE_RANK` is the only field that differs between nodes. On each node:

```bash
# Node 0 (master, the one whose IP you put in the YAML)
export MACHINE_RANK=0
ff-train examples/grpo/full/wan21_t2v_1.3b_videoscore2.yaml

# Node 1
export MACHINE_RANK=1
ff-train examples/grpo/full/wan21_t2v_1.3b_videoscore2.yaml

# Node 2
export MACHINE_RANK=2
ff-train examples/grpo/full/wan21_t2v_1.3b_videoscore2.yaml

# Node 3
export MACHINE_RANK=3
ff-train examples/grpo/full/wan21_t2v_1.3b_videoscore2.yaml
```

> **On managed clusters** (K8s / Slurm / PAI / Volcano): `MACHINE_RANK` / `NODE_RANK` / `INDEX` is auto-injected by the scheduler — you literally just run `ff-train examples/.../wan21_t2v_1.3b_videoscore2.yaml`.

### 5.3 Convenience wrapper (logs to a per-node file)

```bash
bash multinode_examples/launch_multinode.sh examples/grpo/full/wan21_t2v_1.3b_videoscore2.yaml
```

### 5.4 Shared filesystem prep (strongly recommended)

To avoid every node redundantly downloading 7B VideoScore2 + 1.3B Wan, point HF cache + Flow-Factory cache to a shared NFS path:

```bash
export HF_HOME=/shared/cache/huggingface
huggingface-cli download TIGER-Lab/VideoScore2     # warm up once
huggingface-cli download Wan-AI/Wan2.1-T2V-1.3B-Diffusers
```

Optionally edit the YAML:
```yaml
data:
  cache_dir: "/shared/.cache/flow_factory/datasets"
```

---

## 6. Key Config Parameters (cheat sheet)

Below are the knobs you'll most likely need to touch. Full file: `examples/grpo/full/wan21_t2v_1.3b_videoscore2.yaml`.

### 6.1 Geometry (sampling cost lives here)

| Section | Param | Value | Meaning |
|---|---|---|---|
| `train` | `resolution` | `[480, 832]` | Wan2.1 native, [H, W] |
| `train` | `num_frames` | `33` | `(F-1) % 4 == 0`; ~2s @16fps |
| `train` | `num_inference_steps` | `8` | Sampling steps (training); keep 8-10 |
| `train` | `guidance_scale` | `5.0` | Slightly below eval for exploration |
| `eval`  | `num_frames` | `81` | Canonical VBench length |
| `eval`  | `num_inference_steps` | `50` | Full denoising for eval quality |
| `eval`  | `guidance_scale` | `6.0` | Wan2.1 official VBench setting |

### 6.2 GRPO knobs

| Param | Value | Meaning |
|---|---|---|
| `trainer_type` | `grpo` | Vanilla Flow-GRPO |
| `per_device_batch_size` | `1` | One video per forward (memory-bound) |
| `group_size` | `8` | K-repeat: 8 samples per prompt for group-relative advantage |
| `unique_sample_num_per_epoch` | `32` | 32 unique prompts × 8 = 256 videos/epoch |
| `gradient_step_per_epoch` | `2` | Inner-epoch grad steps |
| `clip_range` | `1.0e-4` | PPO ratio clip |
| `adv_clip_range` | `5.0` | Advantage clip |
| `kl_beta` | `0` | KL disabled (memory). Set ~`1e-3` if training diverges |
| `learning_rate` | `1.0e-4` | AdamW |

> **Integer divisibility constraint**: `unique_sample_num_per_epoch × group_size` must be divisible by `num_processes × per_device_batch_size`. Currently `32×8=256`, `32×1=32`, `256/32=8` ✓.

### 6.3 Reward (VideoScore2)

| Param | Value | Meaning |
|---|---|---|
| `device` | `"cuda"` | Loads ~7B VLM on each rank's GPU |
| `visual_weight` | `1.0` | Visual quality dimension |
| `text_align_weight` | `1.0` | Text-video alignment |
| `physical_weight` | `1.0` | Physical / common-sense consistency |
| `infer_fps` | `2.0` | Frame rate Qwen2-VL samples at |
| `store_fps` | `15.0` | Wan native fps for temp mp4 |

**VLM frame coverage** ≈ `num_frames × (infer_fps / store_fps)`.
- Train (33 frames): ~4.4 frames seen by VLM
- Eval (81 frames): ~10.8 frames seen by VLM

### 6.4 Checkpointing

| Param | Value | Meaning |
|---|---|---|
| `save_dir` | `"saves/"` | Output directory |
| `save_freq` | `20` | Checkpoint every 20 epochs |
| `save_model_only` | `true` | Skip optimizer state (can't resume optimizer, saves disk) |

---

## 7. OOM Fallback Ladder

Each rank holds the 1.3B Wan policy + 7B VideoScore2 + EMA + activations. Tight on H20 96GB. If `nvidia-smi` shows OOM, try in order (each step roughly halves the most expensive memory pool):

1. **Drop group size**: `train.group_size: 8 → 4` (most effective)
2. **Move EMA to CPU**: `train.ema_device: "cuda" → "cpu"`
3. **Offload reference model**: `train.ref_param_device: "cuda" → "cpu"` (only matters if `kl_beta > 0`)
4. **Drop num_frames**: `train.num_frames: 33 → 17` (cuts sequence length ~2x)
5. **Remote reward server**: Move VideoScore2 to a separate GPU/node via HTTP. See `guidance/rewards.md` § "Remote Reward Server". This frees ~14 GB per training rank.

---

## 8. Expected per-Epoch Timing (32 ranks, 256 videos/epoch)

| Stage | Per-rank work | Estimated time |
|---|---|---|
| Sampling | 8 videos × 8 inference steps | ~2-3 min |
| VideoScore2 reward | 8 videos × ~30s | ~3-4 min |
| Optimization | 8 videos × 1 SDE-marked step | ~1-2 min |
| **Total** | | **~6-9 min/epoch** |

If too slow, the cheapest lever is `unique_sample_num_per_epoch: 32 → 16` (halves work per epoch, but each gradient step sees fewer unique prompts).

---

## 9. Algorithm Background

See `guidance/algorithms.md` for the full math. TL;DR for this config:

- **Flow-SDE dynamics** (`scheduler.dynamics_type: "Flow-SDE"`) injects Gaussian noise during sampling. `noise_level: 0.9` controls exploration magnitude.
- Only **1 SDE step** (`scheduler.num_sde_steps: 1`) out of 8 inference steps is marked for gradient — randomly picked from `sde_steps: [1, 2, 3]`. This is the MixGRPO / TempFlow-GRPO efficiency trick.
- **GRPO advantage** = `(reward − group_mean) / group_std`, computed across all 32 ranks for each prompt's group of 8 videos.

Workflow stages: `guidance/workflow.md` covers the 6-stage pipeline (preprocess → K-repeat → sample → reward → advantage → optimize).

---

## 10. Quick Sanity Checks

Before launching, verify:

```bash
# 1. CUDA available
python -c "import torch; print(torch.cuda.device_count(), 'GPUs visible')"

# 2. Flash-Attention 3 kernel installed
python -c "import kernels; print('kernels OK')"

# 3. wandb logged in
wandb status

# 4. Dataset readable
python -c "import json; [json.loads(l) for l in open('dataset/videoscore2/train.jsonl')]; print('jsonl OK')"

# 5. Master IP reachable from worker nodes (run on a worker)
nc -zv <master_ip> 29500
```

---

## Contact / Files

- Config: `examples/grpo/full/wan21_t2v_1.3b_videoscore2.yaml`
- Accelerate / FSDP2 config: `multinode_examples/fsdp2_wan.yaml`
- Multi-node launch wrapper: `multinode_examples/launch_multinode.sh`
- Reward implementation: `src/flow_factory/rewards/videoscore2.py`
- Workflow doc: `guidance/workflow.md`
- Algorithm doc: `guidance/algorithms.md`
- Reward doc: `guidance/rewards.md`
