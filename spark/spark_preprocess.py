import argparse
import random
import sys
import json
from functools import reduce
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, trim, regexp_replace, when, lit, count, avg, length, struct, udf
from pyspark.sql.types import StringType

# ── STEP 1: PERSONA CONFIGURATION ──────────────────────────────────────────
# This system prompt defines the "Owner BI" personality.
# It ensures the model treats the Amazon reviews as internal proprietary data.
SYSTEM_PROMPT = """You are the Amazon Internal Executive BI Assistant. 
Your role is to provide the CEO and Company Owners with strategic insights based on OUR internal customer data.
Always refer to categories and products as 'OURS'. Focus on market share, competitor threats, and product health."""

INSTRUCTION_TEMPLATES = [
    {"task_type": "full_swot", "instruction": "EXECUTIVE BRIEF: Provide a complete SWOT analysis for our [Category] department based on this data: [Context]"},
    {"task_type": "swot_threats", "instruction": "RISK ASSESSMENT: What are the specific THREATS to our [Category] business in this feedback? Data: [Context]"},
    {"task_type": "swot_strengths", "instruction": "ASSET AUDIT: What are our core STRENGTHS in [Category] according to this report? Data: [Context]"},
    {"task_type": "competitor_compare", "instruction": "COMPETITOR GAP: How does our [Category] product compare to 'Competitor X' based on these customer pain points? Data: [Context]"},
    {"task_type": "trend_prediction", "instruction": "MARKET FORECAST: Based on these internal insights, what is the #1 trend we must lead in [Category]? Data: [Context]"}
]

def generate_instruction(row, templates):
    """
    Step 2: Advanced Executive Logic
    """
    text = row["review_body"]
    rating = row.get("rating") or row.get("overall")
    topics = row["detected_topics"]
    category = row["category"]
    context_snippet = text[:400]
    rating_int = int(float(rating)) if rating is not None else 3
    
    template = random.choice(templates)
    instruction = template["instruction"].replace("[Context]", context_snippet).replace("[Category]", category)
    
    # ── ADVANCED RESPONSE LOGIC ──
    if template["task_type"] == "full_swot":
        output = f"## Executive SWOT: {category}\n- **S**: High Quality focus.\n- **W**: Delivery delays in {topics}.\n- **O**: Expand premium line.\n- **T**: Competitor pricing pressure."
        
    elif template["task_type"] == "swot_threats":
        level = "HIGH" if rating_int < 3 else "MODERATE"
        output = f"## Risk Report: {category}\n- **Primary Threat**: Customer dissatisfaction with {topics}.\n- **Risk Level**: {level}\n- **Mitigation**: Immediate quality audit required."

    elif template["task_type"] == "trend_prediction":
        trend_label = "Premium Premiumization" if rating_int >= 4 else "Budget Consolidation"
        output = f"## Market Forecast: {category}\n- **Emerging Trend**: {trend_label}\n- **Consumer Behavior**: High interest in {topics}.\n- **CEO Recommendation**: Shift marketing budget to highlight {topics} next quarter."
        
    else: # Generic Strategic Insight
        output = f"## Strategic Brief: Our {category}\n- **Observation**: {topics} remains our key differentiator.\n- **Action Plan**: Increase R&D budget for {category} by 15% to maintain our lead."

    return f"### System:\n{SYSTEM_PROMPT}\n\n### Instruction:\n{instruction}\n\n### Response:\n{output}"

def perform_eda(df, split_name):
    """
    Step 3: Exploratory Data Analysis (Requirement for Section 4)
    This function calculates the statistics needed for the 3 required report figures.
    """
    print(f"\n📊 --- EDA REPORT FOR {split_name.upper()} ---")
    
    # Metric 1: Sample Count
    sample_count = df.count()
    print(f"Total Sample Count: {sample_count}")
    
    # Metric 2: Sentiment Balance (Class Balance)
    sentiment_counts = df.groupBy("sentiment_spark").count().collect()
    print("Class Balance (Sentiment):")
    for row in sentiment_counts:
        print(f"  - {row['sentiment_spark']}: {row['count']}")
        
    # Metric 3: Token Length Distribution
    token_stats = df.select(avg(length(col("review_body"))).alias("avg_len")).collect()[0]
    print(f"Average Character Length: {token_stats['avg_len']:.2f}")
    
    return sample_count

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--s3-bucket", default="25fltp-ecom-chatbot")
    parser.add_argument("--categories", nargs="+", default=["Electronics", "Home_Improvement"])
    parser.add_argument("--output-path", default="s3://25fltp-ecom-chatbot/processed")
    parser.add_argument("--max-per-category", type=int, default=10000)
    args = parser.parse_args()

    # Initialize Spark Session (EMR Cluster Entry Point)
    spark = SparkSession.builder.appName("AmazonOwnerBI-ETL").getOrCreate()

    # ── STEP 4: DATA LOADING & CLEANING ────────────────────────────────────
    category_dfs = []
    for cat in args.categories:
        # Load raw data from S3 (Requirement: S3 input/output)
        path = f"s3://{args.s3_bucket}/raw_input/{cat}/"
        try:
            df = spark.read.json(path).limit(args.max_per_category) # Use dynamic limit
            df = df.withColumn("category", lit(cat))
            
            # Cleaning logic: Lowecase and trim to remove noise
            df = df.withColumn("review_body", lower(trim(col("review_body"))))
            
            # Feature Engineering: Simple Topic detection
            df = df.withColumn("detected_topics", 
                when(col("review_body").contains("price"), "Pricing")
                .when(col("review_body").contains("delivery"), "Logistics")
                .otherwise("Quality"))
            
            # Sentiment Analysis (Handle 'rating' or 'overall' columns)
            rating_col = "rating" if "rating" in df.columns else "overall"
            df = df.withColumn("sentiment_spark", 
                when(col(rating_col) >= 4, "positive")
                .when(col(rating_col) <= 2, "negative")
                .otherwise("neutral"))
                
            category_dfs.append(df)
        except Exception as e:
            print(f"Warning: Could not load {cat}: {e}")

    # Union all categories and Repartition for Big Data performance (2 workers * 4 cores = 8)
    df_master = reduce(lambda a, b: a.union(b), category_dfs).repartition(32)

    # ── STEP 5: SPLITTING & EDA ────────────────────────────────────────────
    # Requirement: Show sample count per split
    train_df, val_df, test_df = df_master.randomSplit([0.8, 0.1, 0.1], seed=42)
    
    train_n = perform_eda(train_df, "train")
    val_n   = perform_eda(val_df, "val")
    test_n  = perform_eda(test_df, "test")

    # ── STEP 6: INSTRUCTION GENERATION ─────────────────────────────────────
    templates_br = spark.sparkContext.broadcast(INSTRUCTION_TEMPLATES)
    generate_udf = udf(lambda row: generate_instruction(row.asDict(), templates_br.value), StringType())
    
    # Format the training split for fine-tuning
    df_final = train_df.select(generate_udf(struct([train_df[c] for c in train_df.columns])).alias("text"))

    # ── STEP 7: SAVE TO S3 (Requirement: S3 Screenshot) ────────────────────
    # We save as text/JSONL format which is required by the fine-tuning libraries.
    df_final.write.mode("overwrite").text(args.output_path + "/train.jsonl")
    val_df.select(generate_udf(struct([val_df[c] for c in val_df.columns]))).write.mode("overwrite").text(args.output_path + "/val.jsonl")
    test_df.select(generate_udf(struct([test_df[c] for c in test_df.columns]))).write.mode("overwrite").text(args.output_path + "/test.jsonl")

    print(f"\n✅ ETL COMPLETE. Data stored in s3://{args.s3_bucket}/processed/")

if __name__ == "__main__":
    from pyspark.sql.functions import lit
    main()
