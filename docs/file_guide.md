# Complete File Guide — E-commerce BI Chatbot
## Person 2: Model Fine-Tuning Lead

---

## File Overview

Your project has **two main deliverables**:

| Deliverable | File | Location | Description |
|---|---|---|---|
| Fine-tuned model | GGUF file (~700 MB) | Download from Colab → S3 | Deployed by Person 3 on EC2 |
| LoRA adapters | `.safetensors` (~50 MB) | `outputs/ecom_chatbot_adapter/` | Saved for future merging |

Both are produced by running `training/finetune.ipynb` on Google Colab.

---

## File-by-File Explanation

### Core Training Files (Your Main Deliverable)

| File | What It Does | Who Uses It | How |
|---|---|---|---|
| `training/finetune.ipynb` | **Complete Colab notebook** — loads real Amazon reviews from HuggingFace, fine-tunes TinyLlama-1.1B with QLoRA, exports to GGUF | **You (Person 2)** — run on Colab T4 GPU | Upload to Colab, Runtime → T4 GPU, run all blocks sequentially |
| `training/hyperparameters.md` | Documents all training hyperparameters (lr=2e-4, batch=4, r=16, alpha=32, dropout=0.05) with justifications | Include in final report | Copy-paste into Sections 3 & 5 |
| `training/eval_prompts.md` | 5 evaluation prompts comparing base vs fine-tuned model with expected outputs | Include in final report | Add real outputs after running BLOCK 15 |

### Spark Preprocessing (Person 1's Work — Provided for Context)

| File | What It Does | Who Uses It | How |
|---|---|---|---|
| `spark/spark_preprocess.py` | Full PySpark pipeline: loads Amazon Reviews 2023 from HuggingFace, deduplicates, filters, generates instruction-tuning JSONL with 80/10/10 train/val/test split | Person 1 runs on AWS EMR, or you can run locally | `python spark/spark_preprocess.py --output-dir ./data/processed --categories Electronics ...` |
| `spark/run_commands.md` | AWS EMR cluster creation and job submission commands | Person 1 or team member for AWS setup | Configure AWS CLI, then run commands |

### Deployment Files (For Person 3)

| File | What It Does | Who Uses It | How |
|---|---|---|---|
| `deployment/backend_rag.py` | RAG layer: loads FAISS index + Ollama, retrieves context, augments prompts. Has CLI chat interface | Person 3 copies to EC2 | `python backend_rag.py --cli` on EC2 after Ollama is running |
| `deployment/model_load_instructions.md` | Step-by-step: download GGUF from S3 → create Modelfile → `ollama create` → test | Person 3 reads this | Share with Person 3 via email or Slack |
| `deployment/deploy_commands.md` | All EC2 setup commands: Ollama install, systemd service, OpenWebUI, firewall | Person 3 runs these on EC2 | Share with Person 3 |
| `deployment/knowledge/*.md` | RAG knowledge base: Amazon, Alibaba, Walmart profiles + market trends | Loaded by `backend_rag.py` at runtime | Copy to EC2 at `deployment/knowledge/` |

### Documentation Files

| File | What It Does | Who Uses It | How |
|---|---|---|---|
| `docs/submission_guide.md` | Complete submission instructions with file-by-file descriptions, step-by-step Colab commands, troubleshooting | **Your main reference** | Read this when submitting |
| `docs/Person2_Report_Sections.md` | **Sections 3 & 5** of the final report — ready to copy-paste into LaTeX | Include in final PDF | Copy Sections 3 & 5 into your LaTeX document |
| `docs/file_guide.md` | **This file** — explains every file, its purpose, and how to use it | You (Person 2) | Reference when explaining files to teammates |

### Project Root Files

| File | What It Does | Who Uses It | How |
|---|---|---|---|
| `README.md` | Complete end-to-end replication guide with architecture diagram | Everyone on the team | Read for full project context |
| `requirements.txt` | Python dependencies (unsloth, datasets, trl, peft, faiss-cpu, sentence-transformers, requests) | Person 3 installs on EC2 | `pip install -r requirements.txt` on EC2 |
| `github_upload.sh` | Bash script that pushes all files to GitHub | You run once to share work | Run: `bash github_upload.sh` |
| `.gitignore` | Git ignore rules | Git | No action needed |

---

## How to Run the Notebook (Step-by-Step)

### 1. Download All Files
Download the entire `ecom-chatbot` folder from GitHub or this workspace to your computer.

### 2. Open Google Colab
Go to https://colab.research.google.com → File → Upload notebook → select `training/finetune.ipynb`

### 3. Set GPU Runtime
Runtime → Change runtime type → Select **T4 GPU** → Save

### 4. Run Blocks in Order

| Block | What Happens | Expected Output | Time |
|---|---|---|---|
| BLOCK 1 | Install Unsloth + dependencies | "Unsloth version: 2026.4.x" | 2 min |
| BLOCK 2 | Load 10,000 real Amazon reviews from HuggingFace | "Loaded 10,000 reviews" | 30 sec |
| BLOCK 3 | Clean: remove short reviews, duplicates | "After cleaning: ~8,000 reviews" | 5 sec |
| BLOCK 4 | Generate instruction-tuning examples (5 task types) | "Generated ~8,000 examples" | 10 sec |
| BLOCK 5 | Save to `train.jsonl` | "Saved 8000 examples to train.jsonl" | 5 sec |
| BLOCK 6 | Load TinyLlama-1.1B with Unsloth (4-bit) | "Model loaded successfully!" | 2 min |
| BLOCK 7 | Attach QLoRA adapters | "trainable params: X M / total params: Y M" | 5 sec |
| BLOCK 8 | Load JSONL for SFTTrainer | "Dataset loaded: 8000 examples" | 5 sec |
| BLOCK 9 | Format with chat template | "Formatted dataset: 8000 examples" | 5 sec |
| BLOCK 10 | Set training arguments | Shows all hyperparameters | 2 sec |
| BLOCK 11 | **Fine-tune** (QLoRA training) | "Training complete in ~35 min" | **30-40 min** |
| BLOCK 12 | Save LoRA adapters to `outputs/ecom_chatbot_adapter/` | "Adapters saved (~50 MB)" | 10 sec |
| BLOCK 13 | Export to GGUF format (q4_k_m) | "GGUF file: tinyllama-chat.Q4_K_M.gguf" | 3-5 min |
| BLOCK 14 | Download GGUF and upload to S3 | Click download button | 2 min |
| BLOCK 15 | Inference test with SWOT prompt | SWOT analysis output | 30 sec |
| BLOCK 16 | Summary | Shows all output files | 2 sec |

### 5. Download the GGUF File
In BLOCK 14, click the **download button** that appears in Colab. The file `tinyllama-chat.Q4_K_M.gguf` (~700 MB) saves to your Downloads folder.

### 6. Upload to S3
```bash
aws configure  # Enter your Access Key ID and Secret Access Key
aws s3 mb s3://<NETID>-ecom-chatbot
aws s3 cp ~/Downloads/tinyllama-chat.Q4_K_M.gguf s3://<NETID>-ecom-chatbot/model/
```

### 7. Share with Person 3
Send Person 3 the S3 path: `s3://<NETID>-ecom-chatbot/model/tinyllama-chat.Q4_K_M.gguf`

---

## Overfitting Diagnosis and Fixes

### Is Your Model Overfitting?

Based on your training run:
- **Loss curve**: 2.36 (step 10) → 0.55 (step 900) — smooth, stable descent ✅
- **Gap between train and val**: You ran only train split (no val) — **cannot confirm overfitting with current code**
- **Output quality**: SWOT analysis was **structurally correct and business-relevant** ✅

**Signs of overfitting** to watch for:
- Loss keeps dropping but validation loss flattens or rises
- Model outputs become repetitive or start copying input verbatim
- Output quality degrades after many epochs
- Model becomes "stuck" on one format

**Signs your model is healthy**:
- Loss converges to a stable value (not NaN)
- Output follows instruction format (SWOT, comparison table, etc.)
- No repetition in generated text
- Loss plateau around 0.5-0.8 for 7,000+ examples is normal

### How to Check for Overfitting

**Current issue**: Your notebook does **not** have a validation split. To detect overfitting:

1. Add this to BLOCK 5:
```python
from sklearn.model_selection import train_test_split

train_examples, val_examples = train_test_split(
    examples, test_size=0.1, random_state=42
)
# Save val.jsonl for validation
with open('val.jsonl', 'w') as f:
    for ex in val_examples:
        f.write(json.dumps(ex) + '\n')
```

2. In BLOCK 10, add evaluation:
```python
evaluation_strategy="steps",
eval_steps=100,
eval_dataset=val_dataset,  # Load from val.jsonl
```

3. Compare eval loss vs train loss. If eval loss plateaus while train loss keeps dropping → **overfitting**.

### Fixes for Overfitting

| Fix | How | Effect |
|---|---|---|
| **Add validation split** | 80/10/10 train/val/test split in BLOCK 5 | Detects overfitting early |
| **Increase dropout** | Change `LORA_DROPOUT` from 0.05 to 0.1 in BLOCK 7 | Prevents over-reliance on specific weights |
| **Reduce LoRA rank** | Change `LORA_R` from 16 to 8 in BLOCK 7 | Fewer trainable parameters = less overfitting |
| **Early stopping** | Add `load_best_model_at_end=True` in BLOCK 10 | Stops training when val loss stops improving |
| **More data** | Increase `MAX_SAMPLES` from 10,000 to 20,000 in BLOCK 2 | More examples = better generalization |
| **Reduce epochs** | Change `EPOCHS` from 2 to 1 in BLOCK 10 | Less overfitting, faster training |
| **Increase weight decay** | Change `WEIGHT_DECAY` from 0.01 to 0.05 in BLOCK 10 | Stronger regularization |

### Fixes for Underfitting

| Fix | How | Effect |
|---|---|---|
| **More epochs** | Change `EPOCHS` from 2 to 3 in BLOCK 10 | Model has more time to learn patterns |
| **Increase rank** | Change `LORA_R` from 16 to 32 in BLOCK 7 | More trainable capacity |
| **Increase alpha** | Change `LORA_ALPHA` from 32 to 64 in BLOCK 7 | Stronger LoRA scaling |
| **Higher learning rate** | Change `LEARNING_RATE` from 2e-4 to 3e-4 in BLOCK 10 | Faster initial learning |
| **More data** | Increase `MAX_SAMPLES` from 10,000 to 20,000 | More patterns learned |
| **Remove gradient checkpointing** | In BLOCK 7, remove `use_gradient_checkpointing='unsloth'` | More memory = better training |

### Balanced Enhancement Strategy

If you want the best model without overfitting or underfitting:

1. **Best single change**: Add a **validation split** (10% of data) and monitor eval loss
2. **Second best**: Increase data from 10,000 to 20,000 samples
3. **Third best**: Run for 3 epochs instead of 2, but watch val loss

---

## Submitting to Person 3

After running the notebook successfully, you need to deliver to Person 3:

### What to Send

1. **GGUF model location**: `s3://<NETID>-ecom-chatbot/model/tinyllama-chat.Q4_K_M.gguf`
2. **This file**: `deployment/model_load_instructions.md`
3. **This file**: `deployment/deploy_commands.md`
4. **RAG backend**: `deployment/backend_rag.py`
5. **Knowledge base**: `deployment/knowledge/` (4 markdown files)
6. **Report sections**: `docs/Person2_Report_Sections.md`

### Message Template for Person 3

> "Here's the complete model package for EC2 deployment:
> - GGUF model: `s3://<NETID>-ecom-chatbot/model/tinyllama-chat.Q4_K_M.gguf` (~700 MB, q4_k_m)
> - See `deployment/model_load_instructions.md` for step-by-step Ollama setup
> - See `deployment/deploy_commands.md` for all EC2 commands
> - RAG backend: `deployment/backend_rag.py` + `deployment/knowledge/`
> - Report sections: `docs/Person2_Report_Sections.md` (Sections 3 & 5)
>
> The model is fine-tuned on 7,256 real Amazon Electronics reviews using QLoRA.
> Expected output: SWOT analysis, competitor comparison tables, market trend reports."

---

## Troubleshooting

### GGUF Export Failed
If BLOCK 13 shows "No GGUF file found":
1. Check if `os.makedirs` failed due to permissions
2. Try: `!mkdir -p ./outputs/ecom_chatbot_gguf_gguf` before running BLOCK 13
3. If still failing, check if Colab ran out of disk space (model needs ~3 GB free)

### Training Loss is NaN
1. Reduce learning rate: change `2e-4` to `1e-4` in BLOCK 10
2. Ensure `fp16=True` is set in BLOCK 10
3. Reduce batch size: change `BATCH_SIZE` from 4 to 2 in BLOCK 10

### CUDA Out of Memory
1. Reduce `MAX_SAMPLES` from 10,000 to 5,000 in BLOCK 2
2. Reduce `BATCH_SIZE` from 4 to 2 in BLOCK 10
3. Reduce `MAX_SEQ_LENGTH` from 2048 to 1024 in BLOCK 6

### Download Button Not Appearing in BLOCK 14
If no download button appears, manually download from Colab file browser:
1. Click the folder icon on the left sidebar
2. Navigate to `./outputs/ecom_chatbot_gguf_gguf/`
3. Right-click `tinyllama-chat.Q4_K_M.gguf` → Download

---

*Last updated: 2026-04-23*
*Author: MiniMax Agent (for Person 2)*
