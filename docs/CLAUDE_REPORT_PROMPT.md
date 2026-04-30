# 🤖 Copy-Paste this Prompt to Claude

**Prompt:**
"I need you to generate a professional, academic LaTeX report template for my Cloud Computing project. The report is for a course called CISC 886 at Queen's University. 

**Project Title:** E-commerce Business Intelligence Chatbot (Group 25fltp)
**Objective:** Building an automated Big Data pipeline and a domain-specific LLM to provide executive-level SWOT analysis, competitor benchmarking, and market trend insights.

Please structure the LaTeX code with the following sections and include detailed placeholders/technical descriptions based on these facts:

1. **Abstract:** Summarize the use of AWS EMR for processing 1.8M reviews, QLoRA fine-tuning on TinyLlama-1.1B, and deployment via EC2/Ollama with a RAG layer.

2. **Introduction:**
   - Problem: E-commerce data is too vast for manual analysis.
   - Solution: A conversational AI assistant for CEOs/Owners.
   - Scope: SWOT Analysis, Competitor Comparison, and Trend Identification.

3. **Data Engineering (AWS EMR & PySpark):**
   - Dataset: McAuley-Lab Amazon Reviews 2023 (9 major categories).
   - Infrastructure: 3-node EMR 7.1.0 cluster using m5.xlarge instances.
   - Pipeline: Direct streaming from HuggingFace to S3, Spark cleaning (deduplication, length clipping), and feature engineering (extracting topic tags for 'Price', 'Quality', and 'Logistics').

4. **Model Fine-Tuning (QLoRA):**
   - Base Model: TinyLlama-1.1B-Chat.
   - Method: QLoRA (4-bit NF4 quantization) using the Unsloth library.
   - Stats: 2 epochs, learning rate 2e-4, rank 16.
   - Export: GGUF format (Q4_K_M) for CPU-efficient inference.

5. **System Deployment & RAG:**
   - Hosting: AWS EC2 (t3.large) with Ubuntu 22.04.
   - Stack: Ollama for model runtime and OpenWebUI for the interface.
   - RAG: Implementation using FAISS and sentence-transformers (all-MiniLM-L6-v2) to provide ground-truth business context.

6. **Infrastructure as Code (IaC):**
   - Terraform: Modular setup for VPC, EMR, EC2, and S3.

7. **Figures & Results:**
   - Create figure environments for: Architecture Diagram, EMR Console Success, S3 Processed Data, Training Loss Graph, Ollama List Terminal, and OpenWebUI Chat Interface.
   - Add captions describing each figure's role in the pipeline.

8. **Conclusion:**
   - Mention successful generation of structured SWOT reports.
   - Future work: Scaling to larger parameter models like Llama 3.

**Formatting Requirements:**
- Use the `article` class with 12pt font.
- Include packages for `graphicx`, `hyperref`, `booktabs` (for tables), and `listings` (for code snippets).
- Add a professional title page and a Table of Contents.
- Use `\section` and `\subsection` tags properly."
