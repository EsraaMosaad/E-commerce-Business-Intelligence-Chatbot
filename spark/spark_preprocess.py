import argparse
import random
import sys
import json
from functools import reduce
from pyspark import StorageLevel
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
    text = row.get("text", "")
    if text is None: text = ""
    rating = row.get("rating") or row.get("overall")
    topics = row.get("detected_topics", "Unknown")
    category = row.get("category", "General")
    context_snippet = text[:400]
    rating_int = int(float(rating)) if rating is not None else 3
    
    template = random.choice(templates)
    instruction = template["instruction"].replace("[Context]", context_snippet).replace("[Category]", category)
    
    # ── ADVANCED RESPONSE LOGIC ──
    # Extract a short snippet from the actual review to make every response 100% unique
    clean_text = text.replace('\n', ' ').strip()
    snippet = clean_text[:40] + "..." if len(clean_text) > 40 else clean_text
    
    if template["task_type"] == "full_swot":
        s = random.choice([f"High Quality focus in {category}.", "Strong brand loyalty.", "Excellent customer feedback."])
        w = random.choice([f"Issues reported regarding {topics}.", "Inconsistent product delivery.", "Pricing concerns from budget buyers."])
        o = random.choice([f"Expand premium line for {category}.", "Bundling opportunities.", "Improve marketing on social media."])
        t = random.choice(["Competitor pricing pressure.", f"Supply chain issues impacting {topics}.", "Market saturation."])
        
        s_desc = random.choice(["Internal metrics indicate strong customer loyalty in this segment.", "Our brand trust remains unmatched here.", "This is heavily driving our repeat-purchase rate."])
        w_desc = random.choice([f"Recent reviews specifically mention: '{snippet}'", "This requires immediate attention from the operations team.", "Customer friction here is causing cart abandonment."])
        o_desc = random.choice(["Market analysis suggests a growing consumer demand here.", "We can leverage this for our Q4 holiday push.", "There is an untapped demographic we can reach."])
        t_desc = random.choice(["External market pressures could erode our market share.", "Competitors are actively launching campaigns against us here.", "We risk losing our competitive moat if we do not adapt."])
        
        output = f"## Executive SWOT Analysis: {category} Division\n\nBased on the recent influx of customer feedback, we have identified the following strategic matrix for the {category} department.\n\n### Strengths (S)\n- {s}\n- {s_desc}\n\n### Weaknesses (W)\n- {w}\n- {w_desc}\n\n### Opportunities (O)\n- {o}\n- {o_desc}\n\n### Threats (T)\n- {t}\n- {t_desc}\n\n**Executive Recommendation**: Allocate additional resources to resolve the identified weaknesses while aggressively marketing our core strengths to retain market dominance."
        
    elif template["task_type"] == "swot_threats":
        level = "HIGH" if rating_int < 3 else random.choice(["MODERATE", "LOW"])
        primary = random.choice([f"Customer dissatisfaction with {topics}.", f"Increasing complaints in {category}.", "Aggressive competitor discounting."])
        mitigation = random.choice(["Immediate quality audit required.", "Review pricing strategy.", "Enhance customer support response times."])
        
        impact = random.choice([
            f"If this threat is not mitigated, we project a potential 5-8% decrease in quarterly revenue. Customer retention is highly sensitive to issues involving {topics}.",
            f"Failure to address this could lead to significant churn within the {category} segment. Trends indicate {topics} is a major pain point.",
            f"We are observing a troubling correlation between {topics} complaints and subscription cancellations. Users are explicitly citing issues like: '{snippet}'"
        ])
        directive = random.choice([
            "Department heads must submit a resolution plan by end-of-week.",
            "Immediate task force to be assembled by the VP of Operations.",
            "Marketing must temporarily pause campaigns for this line until resolved."
        ])
        
        output = f"## Risk Assessment Report: {category}\n\nOur data pipeline has flagged potential risks within the {category} sector based on recent customer sentiment analysis. \n\n- **Primary Threat Identified**: {primary}\n- **Calculated Risk Level**: {level}\n\n### Business Impact\n{impact}\n\n### Mitigation Strategy\n- **Action Item 1**: {mitigation}\n- **Action Item 2**: Deploy a targeted email retention campaign offering discounts to affected customers.\n\n**CEO Directive**: {directive}"

    elif template["task_type"] == "swot_strengths":
        asset = random.choice([f"Reliable {topics} performance.", f"Strong market presence in {category}.", "High customer satisfaction."])
        second_asset = random.choice(["Exceptional brand recognition.", "A highly engaged user base that generates organic word-of-mouth marketing.", "Superior supply chain logistics compared to peers."])
        advantage = random.choice([
            f"Our dominance in {topics} creates a significant moat against new competitors entering the market.",
            f"Customers consistently praise our ecosystem, with feedback such as: '{snippet}'",
            f"This asset allows us to maintain higher profit margins than the industry average."
        ])
        
        output = f"## Internal Asset Audit: {category}\n\nThe latest analytics report confirms that the {category} division remains one of our strongest performing sectors.\n\n### Core Strengths\n- **Primary Asset**: {asset}\n- **Secondary Asset**: {second_asset}\n\n### Strategic Advantage\n{advantage}\n\n### Recommendation\n- **Marketing Alignment**: Highlight this specific strength in the upcoming Q4 national marketing campaign.\n- **Investment**: Increase the R&D budget for {category} by 10% to push our technological advantage even further."

    elif template["task_type"] == "competitor_compare":
        gap = random.choice(["We lead in quality, but lag in shipping speed.", f"Our {topics} is superior, but competitors offer better pricing.", "Competitors have a wider selection."])
        impact = random.choice([
            "Competitors are capturing the price-sensitive demographic, while we continue to dominate the premium sector.",
            "We are losing market share among younger demographics who prioritize fast delivery.",
            f"Our brand loyalty is strong, but {topics} remains a vulnerability that rivals are exploiting. Feedback specifically noted: '{snippet}'"
        ])
        pivot = random.choice([
            f"We must reinforce the value proposition of our {topics}. Customers are willing to pay a premium if the perceived value remains unmatched.",
            "We should launch a counter-campaign highlighting our superior customer service and return policies.",
            "Do not engage in a price war. Instead, bundle products to increase perceived value."
        ])
        
        output = f"## Competitor Gap Analysis: {category} vs. Market\n\nAn analysis of customer pain points reveals critical insights regarding our positioning against top-tier competitors.\n\n### Competitive Intelligence\n- **Key Insight**: {gap}\n- **Market Share Impact**: {impact}\n\n### Strategic Pivot\n{pivot}\n\n**Action Plan**: Adjust pricing model dynamically based on inventory, while launching a campaign that emphasizes our superior quality and lifetime warranty."

    elif template["task_type"] == "trend_prediction":
        trend_label = random.choice(["Premium Premiumization", "Eco-Friendly Packaging", "Subscription Models"]) if rating_int >= 4 else random.choice(["Budget Consolidation", "Value Hunting"])
        trajectory = random.choice([
            "We anticipate this trend will dominate the industry for the next 18-24 months.",
            "This is a fast-moving trend that will define Q3 revenue targets.",
            "This shift in consumer preference is permanent and requires a long-term strategic pivot."
        ])
        strategy = random.choice([
            "If we do not capture this trend immediately, we risk losing our position as industry innovators.",
            f"We have a 6-month window to establish dominance in this new niche before competitors catch up. User sentiment clearly points to this: '{snippet}'",
            "This presents a massive opportunity to upsell our existing customer base."
        ])
        
        output = f"## Market Trend Forecast: {category}\n\nBased on predictive analytics applied to our internal review database, we have identified a major shift in consumer behavior.\n\n### Emerging Trend: {trend_label}\n- **Consumer Behavior**: There is a highly concentrated interest in {topics}. Customers are increasingly vocal about this in their feedback.\n- **Market Trajectory**: {trajectory}\n\n### Executive Strategy\n{strategy}\n- **CEO Recommendation**: Shift 20% of the marketing budget to highlight our initiatives regarding {topics} next quarter.\n- **Product Development**: Expedite the launch of our new line that specifically caters to the {trend_label} movement."
        
    else: # Generic Strategic Insight
        insight = random.choice([f"{topics} remains our key differentiator.", f"We are seeing a shift in {category} preferences.", "Customer retention is stable."])
        sentiment = random.choice([
            "The overall sentiment is stabilizing, but there are isolated pockets of friction regarding shipping logistics and pricing tiers.",
            f"Sentiment regarding {topics} is overwhelmingly positive, driving organic growth.",
            f"We are tracking a slight dip in sentiment related to {category}. Recent reviews highlighted: '{snippet}'"
        ])
        strategy = random.choice([
            "Our focus must remain on expanding our total addressable market (TAM) without alienating our core demographic.",
            "By leveraging our massive logistical network, we can outpace smaller competitors while simultaneously increasing our profit margins.",
            "We must prioritize customer retention programs over new acquisitions for the next two quarters."
        ])
        
        output = f"## Executive Strategic Brief: Our {category}\n\nThis brief summarizes the current operational health and strategic positioning of the {category} department.\n\n### Executive Summary\n- **Key Observation**: {insight}\n- **Sentiment Analysis**: {sentiment}\n\n### Long-term Strategy\n{strategy}\n\n- **Action Plan**: Increase the R&D and Marketing budget for {category} by 15% to maintain our undisputed lead in the e-commerce sector."

    final_text = f"### System:\n{SYSTEM_PROMPT}\n\n### Instruction:\n{instruction}\n\n### Response:\n{output}"
    # Wrap in JSON to ensure it saves as a valid, single-line JSONL format in S3
    return json.dumps({"text": final_text})

def perform_eda(df, split_name):
    """
    Step 3: Exploratory Data Analysis (Requirement for Section 4)
    This function calculates the statistics needed for the 3 required report figures.
    """
    print(f"\n--- EDA REPORT FOR {split_name.upper()} ---")
    
    # Metric 1: Sample Count
    sample_count = df.count()
    print(f"Total Sample Count: {sample_count}")
    
    if sample_count == 0:
        print("No data in this split.")
        return 0

    # Metric 2: Category Distribution
    print("Category Distribution:")
    category_counts = df.groupBy("category").count().collect()
    for row in category_counts:
        print(f"  - {row['category']}: {row['count']}")

    # Metric 3: Sentiment Balance (Class Balance)
    sentiment_counts = df.groupBy("sentiment_spark").count().collect()
    print("Class Balance (Sentiment):")
    for row in sentiment_counts:
        print(f"  - {row['sentiment_spark']}: {row['count']}")
        
    # Metric 4: Topic Distribution
    topic_counts = df.groupBy("detected_topics").count().collect()
    print("Detected Topics Distribution:")
    for row in topic_counts:
        print(f"  - {row['detected_topics']}: {row['count']}")
        
    # Metric 5: Token Length Distribution (Min, Max, Avg)
    from pyspark.sql.functions import avg, length, col, min, max
    token_stats = df.select(
        avg(length(col("text"))).alias("avg_len"),
        min(length(col("text"))).alias("min_len"),
        max(length(col("text"))).alias("max_len")
    ).collect()[0]
    
    print(f"Character Lengths -> Average: {token_stats['avg_len']:.2f} | Min: {token_stats['min_len']} | Max: {token_stats['max_len']}")
    
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
            
            # Cleaning logic: Lowecase and trim to remove noise, and drop nulls
            df = df.filter(col("text").isNotNull())
            df = df.withColumn("text", lower(trim(col("text"))))
            
            # Feature Engineering: Simple Topic detection
            df = df.withColumn("detected_topics", 
                when(col("text").contains("price"), "Pricing")
                .when(col("text").contains("delivery"), "Logistics")
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

    if not category_dfs:
        print("[FATAL ERROR] No categories were loaded. Check your S3 bucket raw_input path!")
        sys.exit(1)

    # Union all categories and Repartition for Big Data performance (2 workers * 4 cores = 8)
    df_master = reduce(lambda a, b: a.unionByName(b, allowMissingColumns=True), category_dfs).repartition(16)
    
    # CRITICAL: Persist the master dataframe to disk so that splitting and EDA 
    # don't re-calculate the entire 1.8M row union from S3 multiple times.
    df_master.persist(StorageLevel.DISK_ONLY)

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

    print(f"\n[SUCCESS] ETL COMPLETE. Data stored in s3://{args.s3_bucket}/processed/")

if __name__ == "__main__":
    from pyspark.sql.functions import lit
    main()
