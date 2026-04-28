#!/usr/bin/env python3
"""
Person 1: Amazon Reviews 2023 — PySpark Preprocessing Pipeline
================================================================
Purpose  : Transform raw Amazon Reviews 2023 (HuggingFace) into
           instruction-tuning JSONL for fine-tuning TinyLlama.

Input    : HuggingFace dataset "McAuley-Lab/Amazon-Reviews-2023"
           Categories: Electronics, Home_and_Kitchen,
           Clothing_Shoes_and_Jewelry, Beauty_and_Personal_Care,
           Grocery_and_Gourmet_Food

Output   : data/processed/train.jsonl  (80%)
           data/processed/val.jsonl    (10%)
           data/processed/test.jsonl   (10%)

Run on   : AWS EMR 6.x (Spark 3.x) or local PySpark

Usage    : spark-submit spark/spark_preprocess.py
           --master yarn --deploy-mode cluster \
           --conf spark.yarn.stagingDir=s3://<bucket>/staging/ \
           --conf spark.yarn.dist.files=s3://<bucket>/config/ \
           --total-executor-cores 64 --executor-cores 4 \
           --executor-memory 16G --num-executors 16
"""

from __future__ import print_function, absolute_import
import sys
import json
import argparse
import warnings
from functools import reduce
from operator import add

# ── PySpark imports ──────────────────────────────────────────────────────────
try:
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F
    from pyspark.sql.types import StringType, IntegerType, StructType, StructField
    from pyspark import SparkConf, SparkContext
    from pyspark.sql.window import Window
except ImportError:
    raise ImportError("PySpark is required. Install with: pip install pyspark")

# ── Constants ────────────────────────────────────────────────────────────────
DATASET_NAME = "McAuley-Lab/Amazon-Reviews-2023"
CATEGORIES = [
    "Electronics",
    "Home_and_Kitchen",
    "Clothing_Shoes_and_Jewelry",
    "Beauty_and_Personal_Care",
    "Grocery_and_Gourmet_Food",
]

# Task templates for instruction-tuning
SYSTEM_PROMPT = (
    "You are an expert e-commerce business intelligence analyst. "
    "Answer based on the provided review data and market knowledge. "
    "Use structured formats: SWOT tables, bullet lists, comparison grids."
)

TASK_TEMPLATES = [
    # ── Template 1: Review Intelligence ───────────────────────────────────
    {
        "task_type": "review_intelligence",
        "instruction": (
            "Summarize the key product strengths and weaknesses "
            "based on the customer reviews below. "
            "List top 5 strengths and top 5 weaknesses with supporting quote counts."
        ),
        "output_template": (
            "## Key Strengths\n"
            "1. [Strength] — [N] positive mentions\n"
            "   Evidence: [representative quote excerpt]\n\n"
            "## Key Weaknesses\n"
            "1. [Weakness] — [N] negative mentions\n"
            "   Evidence: [representative quote excerpt]"
        ),
    },
    # ── Template 2: SWOT Analysis ──────────────────────────────────────────
    {
        "task_type": "swot_analysis",
        "instruction": (
            "Perform a SWOT analysis for the e-commerce platform "
            "based on the customer reviews below. Include strategic takeaways."
        ),
        "output_template": (
            "## Strengths\n"
            "- [Strength 1]\n"
            "- [Strength 2]\n\n"
            "## Weaknesses\n"
            "- [Weakness 1]\n"
            "- [Weakness 2]\n\n"
            "## Opportunities\n"
            "- [Opportunity 1]\n"
            "- [Opportunity 2]\n\n"
            "## Threats\n"
            "- [Threat 1]\n"
            "- [Threat 2]\n\n"
            "## Strategic Takeaway\n"
            "[2-sentence strategic recommendation]"
        ),
    },
    # ── Template 3: Competitor Comparison ──────────────────────────────────
    {
        "task_type": "competitor_comparison",
        "instruction": (
            "Compare Amazon, Walmart, and Alibaba based on the customer reviews below. "
            "Use a structured comparison table with dimensions: "
            "Pricing, Logistics & Delivery, Product Assortment, Customer Experience."
        ),
        "output_template": (
            "| Dimension | Amazon | Walmart | Alibaba |\n"
            "|---|---|---|---|\n"
            "| Pricing | [summary] | [summary] | [summary] |\n"
            "| Logistics & Delivery | [summary] | [summary] | [summary] |\n"
            "| Product Assortment | [summary] | [summary] | [summary] |\n"
            "| Customer Experience | [summary] | [summary] | [summary] |\n\n"
            "## Summary\n"
            "[2-sentence overall comparison]"
        ),
    },
    # ── Template 4: Market Trends ──────────────────────────────────────────
    {
        "task_type": "market_trends",
        "instruction": (
            "Identify and explain the top 3 e-commerce market trends "
            "based on customer review themes. Include business implications for each."
        ),
        "output_template": (
            "## Trend 1: [Trend Name]\n"
            "**Description**: [2-sentence explanation]\n"
            "**Business Implication**: [actionable recommendation]\n\n"
            "## Trend 2: [Trend Name]\n"
            "**Description**: [2-sentence explanation]\n"
            "**Business Implication**: [actionable recommendation]\n\n"
            "## Trend 3: [Trend Name]\n"
            "**Description**: [2-sentence explanation]\n"
            "**Business Implication**: [actionable recommendation]"
        ),
    },
    # ── Template 5: Pricing & Delivery Analysis ────────────────────────────
    {
        "task_type": "pricing_delivery",
        "instruction": (
            "Analyze customer sentiment around pricing and delivery "
            "based on the reviews below. Identify key pain points and satisfaction drivers."
        ),
        "output_template": (
            "## Pricing Sentiment\n"
            "- **Overall**: [Positive/Negative/Neutral] — [percentage]%\n"
            "- **Key Driver**: [Main positive factor]\n"
            "- **Main Pain Point**: [Main negative factor]\n\n"
            "## Delivery Sentiment\n"
            "- **Overall**: [Positive/Negative/Neutral] — [percentage]%\n"
            "- **Satisfaction Factors**: [list]\n"
            "- **Complaint Categories**: [list]"
        ),
    },
]

# ── CLI Arguments ────────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="Preprocess Amazon Reviews 2023 for e-commerce chatbot fine-tuning"
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        default=CATEGORIES,
        help="Dataset categories to process",
    )
    parser.add_argument(
        "--max-per-category",
        type=int,
        default=200_000,
        help="Max records per category (for prototype; remove for full run)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/processed",
        help="Output directory for JSONL files",
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.8,
        help="Training split ratio",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.1,
        help="Validation split ratio",
    )
    parser.add_argument(
        "--s3-bucket",
        default=None,
        help="S3 bucket for output (e.g., s3://my-bucket/ecom-chatbot/data/processed). "
             "If omitted, writes locally.",
    )
    return parser.parse_args()


# ── Spark Session ─────────────────────────────────────────────────────────────
def create_spark_session(app_name="AmazonReviewsPreprocess"):
    """Create a Spark session with optimal settings for EMR."""
    # Prevent duplicate logs
    spark = SparkSession.builder \
        .appName(app_name) \
        .config("spark.sql.shuffle.partitions", "200") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer") \
        .config("spark.kryoserializer.buffer.max", "512m") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")
    return spark


# ── Data Loading ──────────────────────────────────────────────────────────────
def load_category_reviews(spark, category: str, max_records: int = None):
    """
    Load a single category from HuggingFace Amazon Reviews 2023 dataset.
    Uses Spark's read format for HuggingFace datasets.

    Falls back to pandas + pandasAPI.spark() if spark reader unavailable.
    """
    subset_name = f"raw_review_{category}"

    try:
        # Try direct Spark reader (HuggingFace Spark integration)
        df = spark.read \
            .format("huggingface") \
            .option("dataset", DATASET_NAME) \
            .option("subset", subset_name) \
            .load()

        print(f"[OK] Loaded '{subset_name}' with {df.count()} rows")
        return df

    except Exception as e:
        print(f"[WARN] HuggingFace Spark reader not available: {e}")
        print(f"[INFO] Falling back to pandas + pandas_to_spark conversion")

        # Fallback: pandas + pandas_spark_type converter
        try:
            from datasets import load_dataset
            import pandas as pd
            from pyspark.sql.types import StructType, StructField, StringType, IntegerType

            print(f"[INFO] Downloading '{subset_name}' via HuggingFace datasets...")
            hf_ds = load_dataset(
                DATASET_NAME,
                subset_name,
                split="full",
                trust_remote_code=True,
                streaming=True,
            )

            # Convert streaming dataset to pandas DataFrame
            records = []
            count = 0
            limit = max_records or float("inf")
            for row in hf_ds:
                records.append(row)
                count += 1
                if count >= limit:
                    break

            pdf = pd.DataFrame(records)
            print(f"[OK] Downloaded {len(pdf)} rows for '{subset_name}'")

            # Define schema matching Amazon Reviews 2023 fields
            schema = StructType([
                StructField("rating", StringType(), True),
                StructField("title", StringType(), True),
                StructField("text", StringType(), True),
                StructField("asin", StringType(), True),
                StructField("parent_asin", StringType(), True),
                StructField("user_id", StringType(), True),
                StructField("timestamp", StringType(), True),
                StructField("verified_purchase", StringType(), True),
                StructField("helpful_vote", StringType(), True),
                StructField("category", StringType(), True),
            ])

            # Filter to columns that exist
            available_cols = [c for c in schema.fieldNames() if c in pdf.columns]
            pdf = pdf[available_cols]
            for col in schema.fieldNames():
                if col not in pdf.columns:
                    pdf[col] = None

            # Reorder columns
            pdf = pdf[schema.fieldNames()]

            # Convert to Spark
            df = spark.createDataFrame(pdf, schema=schema)
            print(f"[OK] Converted to Spark DataFrame: {df.count()} rows")
            return df

        except ImportError as ie:
            raise ImportError(
                "Neither HuggingFace Spark reader nor 'datasets' library available. "
                "Install: pip install datasets pyspark"
            ) from ie


# ── Preprocessing Steps ───────────────────────────────────────────────────────
def preprocess(df, category_name: str):
    """
    Full preprocessing pipeline for one category DataFrame.

    Steps:
    1. Column selection
    2. Deduplication
    3. Null / short-text filtering
    4. Whitespace normalization
    5. Length filter (30–1500 chars)
    6. Rating to sentiment hint
    7. Topic tagging (shipping / quality / pricing / service)
    8. Review grouping per product (parent_asin)
    """

    print(f"\n[PREPROCESS] Category: {category_name}")
    initial = df.count()
    print(f"  [1] Initial rows: {initial:,}")

    # ── Step 1: Column selection ──────────────────────────────────────────
    keep_cols = ["rating", "title", "text", "asin", "parent_asin",
                 "user_id", "timestamp", "verified_purchase", "helpful_vote"]
    existing_cols = [c for c in keep_cols if c in df.columns]
    df = df.select(*existing_cols)
    print(f"  [2] Selected columns: {existing_cols}")

    # ── Step 2: Deduplication ─────────────────────────────────────────────
    # Drop exact duplicates on (asin, user_id, timestamp)
    if {"asin", "user_id", "timestamp"}.issubset(set(df.columns)):
        df = df.dropDuplicates(["asin", "user_id", "timestamp"])
    else:
        df = df.dropDuplicates()
    print(f"  [3] After deduplication: {df.count():,}")

    # ── Step 3: Null filtering ───────────────────────────────────────────
    # Keep rows where text is non-null and not empty
    df = df.filter(F.col("text").isNotNull())
    df = df.filter(F.trim(F.col("text")) != "")
    print(f"  [4] After null filtering: {df.count():,}")

    # ── Step 4: Short-text removal (< 30 chars) ───────────────────────────
    df = df.filter(F.length(F.col("text")) >= 30)
    print(f"  [5] After short-text removal: {df.count():,}")

    # ── Step 5: Whitespace normalization ───────────────────────────────────
    df = df.withColumn("text", F.trim(F.regexp_replace(F.col("text"), r"\s+", " ")))
    df = df.withColumn("title", F.trim(F.regexp_replace(F.col("title"), r"\s+", " ")))
    print(f"  [6] Whitespace normalized")

    # ── Step 6: Length filter (30–1500 chars) ─────────────────────────────
    df = df.filter(F.length(F.col("text")) <= 1500)
    print(f"  [7] After length filter: {df.count():,}")

    # ── Step 7: Rating → sentiment_hint ───────────────────────────────────
    df = df.withColumn(
        "rating_num",
        F.col("rating").cast("double")
    )
    df = df.withColumn(
        "sentiment_hint",
        F.when(F.col("rating_num") >= 4.0, "positive")
         .when(F.col("rating_num") <= 2.0, "negative")
         .otherwise("neutral")
    )
    print(f"  [8] Sentiment derived")

    # ── Step 8: Topic tagging ─────────────────────────────────────────────
    text_lower = F.lower(F.col("text"))
    df = df.withColumn(
        "topic_tag",
        F.concat_ws(",",
            F.when(text_lower.contains("shipping") | text_lower.contains("delivery") |
                   text_lower.contains("arrived") | text_lower.contains("package"),
                   F.lit("shipping")),
            F.when(text_lower.contains("price") | text_lower.contains("expensive") |
                   text_lower.contains("cheap") | text_lower.contains("value"),
                   F.lit("pricing")),
            F.when(text_lower.contains("quality") | text_lower.contains("broken") |
                   text_lower.contains("defective") | text_lower.contains("durab"),
                   F.lit("quality")),
            F.when(text_lower.contains("customer service") | text_lower.contains("return") |
                   text_lower.contains("refund") | text_lower.contains("support"),
                   F.lit("service")),
            F.when(text_lower.contains("easy to use") | text_lower.contains("intuit") |
                   text_lower.contains("convenient") | text_lower.contains("design"),
                   F.lit("usability")),
        )
    )
    df = df.withColumn("topic_tag", F.regexp_replace(F.col("topic_tag"), "^,|,$", ""))
    df = df.withColumn("topic_tag", F.when(F.col("topic_tag") == "", None).otherwise(F.col("topic_tag")))
    print(f"  [9] Topic tags added")

    # ── Step 9: Verified purchase flag ───────────────────────────────────
    df = df.withColumn(
        "verified_purchase_bool",
        F.when(F.col("verified_purchase") == "true", True).otherwise(False)
    )

    # ── Step 10: Add category ──────────────────────────────────────────────
    df = df.withColumn("category", F.lit(category_name))

    final = df.count()
    print(f"  [10] Final rows: {final:,} (removed {initial - final:,}, "
          f"{100*(initial-final)/max(initial,1):.1f}%)")

    return df


# ── Instruction Generation ───────────────────────────────────────────────────
def generate_instruction(record, template):
    """Generate a single instruction-tuning example from a review record."""
    import random

    text = record.get("text", "") or ""
    title = record.get("title", "") or ""
    rating = record.get("rating", "0")
    asin = record.get("asin", "unknown")
    sentiment = record.get("sentiment_hint", "neutral")
    topics = record.get("topic_tag", "") or "general e-commerce"

    # Truncate context to avoid exceeding model context window
    # We use ~600 chars of review text as context
    context_snippet = text[:600].strip()

    instruction = template["instruction"]
    output_template = template["output_template"]

    # Build output with placeholder values (model learns format from template)
    # For real use, these would be populated from aggregations
    rating_int = int(float(rating)) if rating else 3

    # Simulate realistic output values based on the review content
    if "price" in topics or "expens" in text.lower():
        pricing_note = "Customers frequently mention pricing as a key factor."
    else:
        pricing_note = "Pricing is mentioned as reasonable for the product quality."

    if "shipping" in topics or "delivery" in text.lower() or "arrived" in text.lower():
        delivery_note = "Delivery speed and reliability are frequently praised."
    else:
        delivery_note = "Delivery experience is generally satisfactory."

    if rating_int >= 4:
        quality_note = "High product quality and reliability reported."
    elif rating_int <= 2:
        quality_note = "Quality concerns raised; durability issues noted."
    else:
        quality_note = "Mixed quality feedback; varies by product."

    # Format output based on template type
    if template["task_type"] == "review_intelligence":
        output = output_template.replace("[N]", str(random.randint(50, 500)))
        output = output.replace("[Strength]", f"{topics.title()} Related Quality")
        output = output.replace("[Weakness]", "Product Consistency")
        output = output.replace(
            "[representative quote excerpt]",
            f'"{context_snippet[:100]}..."'
        )
    elif template["task_type"] == "swot_analysis":
        output = (
            "## Strengths\n"
            f"- Strong {topics.replace(',', ' and ')} focus\n"
            "- Established customer base\n\n"
            "## Weaknesses\n"
            "- Price sensitivity in competitive market\n"
            "- Delivery variability by region\n\n"
            "## Opportunities\n"
            "- Growing e-commerce adoption\n"
            "- AI-driven personalization\n\n"
            "## Threats\n"
            "- Intense competition (Walmart, Alibaba)\n"
            "- Supply chain disruptions\n\n"
            "## Strategic Takeaway\n"
            "Focus on strengthening logistics networks while investing in "
            "AI-powered product recommendations to drive customer loyalty."
        )
    elif template["task_type"] == "competitor_comparison":
        output = (
            "| Dimension | Amazon | Walmart | Alibaba |\n"
            "|---|---|---|---|\n"
            f"| Pricing | Competitive | Good value | Lowest prices | "
            f"| Logistics & Delivery | Prime fast shipping | Same-day options | Variable | "
            f"| Product Assortment | Massive selection | Broad range | Huge marketplace | "
            f"| Customer Experience | Highly rated | Good | Mixed |\n\n"
            "## Summary\n"
            "Amazon leads in logistics and CX; Walmart excels in physical-digital integration; "
            "Alibaba dominates in price-sensitive global markets."
        )
    elif template["task_type"] == "market_trends":
        output = (
            "## Trend 1: Same-Day Delivery Standardization\n"
            "**Description**: Consumers increasingly expect same-day delivery as baseline. "
            "This shifts competitive advantage from product selection to logistics speed.\n"
            "**Business Implication**: Invest in micro-fulfillment centers and last-mile optimization.\n\n"
            "## Trend 2: AI-Powered Product Recommendations\n"
            "**Description**: Advanced ML models now drive 35%+ of e-commerce conversions "
            "through personalized recommendations and dynamic pricing.\n"
            "**Business Implication**: Deploy transformer-based recommendation engines to "
            "increase average order value and retention.\n\n"
            "## Trend 3: Social Commerce Integration\n"
            "**Description**: Shoppable content on TikTok, Instagram, and YouTube Shorts "
            "now accounts for 25%+ of discovery for younger demographics.\n"
            "**Business Implication**: Build creator marketplace and shoppable video "
            "integration to capture impulse purchases."
        )
    elif template["task_type"] == "pricing_delivery":
        output = (
            "## Pricing Sentiment\n"
            f"- **Overall**: {sentiment.capitalize()}\n"
            f"- **Key Driver**: {pricing_note}\n"
            "- **Main Pain Point**: Price fluctuations and hidden fees\n\n"
            "## Delivery Sentiment\n"
            f"- **Overall**: {sentiment.capitalize()}\n"
            "- **Satisfaction Factors**: Fast shipping, package condition, tracking accuracy\n"
            "- **Complaint Categories**: Delays, incorrect addresses, packaging damage"
        )
    else:
        output = output_template

    # Build full instruction example
    example = {
        "system": SYSTEM_PROMPT,
        "input": instruction,
        "context": context_snippet,
        "output": output,
    }

    return example


# ── Main Pipeline ─────────────────────────────────────────────────────────────
def main():
    args = parse_args()

    print("=" * 60)
    print("Amazon Reviews 2023 — Preprocessing Pipeline")
    print("=" * 60)
    print(f"Categories   : {args.categories}")
    print(f"Max/category: {args.max_per_category:,}")
    print(f"Output dir  : {args.output_dir}")
    print(f"S3 bucket   : {args.s3_bucket or 'local'}")
    print("=" * 60)

    spark = create_spark_session()
    sc = spark.sparkContext

    # ── Step 1: Load and preprocess each category ─────────────────────────
    category_dfs = []
    for cat in args.categories:
        print(f"\n{'='*50}")
        print(f"Processing category: {cat}")
        print(f"{'='*50}")

        try:
            df_cat = load_category_reviews(spark, cat, max_records=args.max_per_category)
            df_clean = preprocess(df_cat, cat)
            category_dfs.append(df_clean)
        except Exception as e:
            print(f"[ERROR] Failed to process category '{cat}': {e}")
            continue

    if not category_dfs:
        print("[ERROR] No categories processed successfully. Exiting.")
        sys.exit(1)

    # ── Step 2: Union all categories ──────────────────────────────────────
    print(f"\n{'='*50}")
    print("Unioning all categories...")
    df_all = reduce(lambda a, b: a.unionByName(b, allowMissingColumns=True), category_dfs)
    total = df_all.count()
    print(f"Total combined rows: {total:,}")

    # ── Step 3: Split by parent_asin (prevent data leakage) ───────────────
    print("\nSplitting into train/val/test by parent_asin...")
    unique_parents = df_all.select("parent_asin").distinct().withColumnRenamed("parent_asin", "pa")
    total_parents = unique_parents.count()

    # Assign each parent_asin to a split
    window = Window.orderBy(F.rand(seed=42))
    unique_parents = unique_parents.withColumn("rn", F.row_number().over(window))
    unique_parents = unique_parents.withColumn("total", F.lit(total_parents))
    unique_parents = unique_parents.withColumn(
        "split_assign",
        F.when(F.col("rn") <= F.col("total") * args.train_ratio, "train")
         .when(F.col("rn") <= F.col("total") * (args.train_ratio + args.val_ratio), "val")
         .otherwise("test")
    )

    # Join split assignment back
    df_all = df_all.join(
        unique_parents.select("pa", "split_assign"),
        df_all.parent_asin == unique_parents.pa,
        "left"
    )

    train_count = df_all.filter(F.col("split_assign") == "train").count()
    val_count = df_all.filter(F.col("split_assign") == "val").count()
    test_count = df_all.filter(F.col("split_assign") == "test").count()

    print(f"  Train: {train_count:,} ({100*train_count/total:.1f}%)")
    print(f"  Val  : {val_count:,} ({100*val_count/total:.1f}%)")
    print(f"  Test : {test_count:,} ({100*test_count/total:.1f}%)")

    # ── Step 4: Generate instruction-tuning examples ───────────────────────
    print("\nGenerating instruction-tuning examples...")

    import random
    random.seed(42)

    def generate_examples(partition_iter):
        """MapPartition: generate instruction examples for each partition."""
        for record in partition_iter:
            # Pick a random template for variety
            template = random.choice(TASK_TEMPLATES)
            try:
                record_dict = record.asDict() if hasattr(record, "asDict") else dict(record)
                example = generate_instruction(record_dict, template)
                yield json.dumps(example, ensure_ascii=False)
            except Exception:
                continue

    # ── Step 5: Write output JSONL ───────────────────────────────────────
    output_base = args.output_dir
    if args.s3_bucket:
        output_base = args.s3_bucket.rstrip("/")

    splits = {
        "train": df_all.filter(F.col("split_assign") == "train"),
        "val": df_all.filter(F.col("split_assign") == "val"),
        "test": df_all.filter(F.col("split_assign") == "test"),
    }

    for split_name, split_df in splits.items():
        output_path = f"{output_base}/{split_name}.jsonl"
        print(f"\nWriting {split_name}.jsonl to {output_path}...")

        split_df.rdd.mapPartitions(generate_examples) \
            .coalesce(1) \
            .saveAsTextFile(output_path)

        # Rename part-* to split_name.jsonl (Spark writes as directory)
        # This is handled by EMR step with a copy command (see run_commands.md)

    print("\n" + "=" * 60)
    print("PREPROCESSING COMPLETE")
    print("=" * 60)
    print(f"Output files:")
    print(f"  {output_base}/train.jsonl")
    print(f"  {output_base}/val.jsonl")
    print(f"  {output_base}/test.jsonl")
    print("=" * 60)

    spark.stop()


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    main()
