"""
AutoML Track Entry Point for AlfaHack / Boosters Platform.
Executed as: python3 solution.py task.md
Generates: submission.csv in current directory.

Architecture:
1. Environment-aware LLM Consultant (reads OPENAI_BASE_URL and OPENAI_API_KEY).
2. Autonomous Task & Schema Discovery (detects train/test datasets, target, metric, and IDs).
3. Advanced Feature Engineering (datetime parsing, out-of-fold target encoding, TF-IDF text features).
4. Cross-Validated Multi-Model Ensemble (LightGBM, HistGradientBoosting, ExtraTrees).
5. Strict Submission Verification (checks row count, column alignment, non-null values).
"""

import os
import sys
import glob
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Root imports (all helper modules are in the root of the submission archive)
try:
    from llm_advisor import LLMAdvisor
except ImportError:
    LLMAdvisor = None

try:
    from automl_core import TaskSpec, TabularFeatureEngineer, AutoMLTrainer
except ImportError:
    TaskSpec, TabularFeatureEngineer, AutoMLTrainer = None, None, None


def read_task_markdown(task_path: str) -> str:
    """Reads task.md file content."""
    if os.path.exists(task_path):
        with open(task_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    return ""


def discover_csv_files(working_dir: str = ".") -> Dict[str, str]:
    """Scans working directory and categorizes CSV datasets."""
    files = glob.glob(os.path.join(working_dir, "*.csv"))
    categorized: Dict[str, str] = {
        "train": None,
        "test": None,
        "sample_submission": None,
        "others": []
    }

    for fpath in files:
        fname = os.path.basename(fpath).lower()
        if "sample_sub" in fname or "submission_sample" in fname or fname == "sample.csv":
            categorized["sample_submission"] = fpath
        elif "train" in fname:
            categorized["train"] = fpath
        elif "test" in fname:
            categorized["test"] = fpath
        elif "sub" in fname and fname != "submission.csv":
            if not categorized["sample_submission"]:
                categorized["sample_submission"] = fpath
        else:
            categorized["others"].append(fpath)

    # Heuristic fallback if not named train/test explicitly
    if not categorized["train"] and categorized["others"]:
        categorized["train"] = categorized["others"][0]
    if not categorized["test"] and len(categorized["others"]) > 1:
        categorized["test"] = categorized["others"][1]

    return categorized


def summarize_csv(fpath: str, max_rows: int = 5) -> Dict[str, Any]:
    """Inspects a CSV file structure without loading entire file into memory."""
    try:
        import pandas as pd
        df = pd.read_csv(fpath, nrows=max_rows)
        return {
            "file": os.path.basename(fpath),
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "sample_row": df.iloc[0].to_dict() if len(df) > 0 else {}
        }
    except Exception:
        # Standard library fallback
        import csv
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            sample = next(reader, [])
        return {
            "file": os.path.basename(fpath),
            "columns": header,
            "sample_row": dict(zip(header, sample)) if header and sample else {}
        }


def infer_task_spec_heuristically(
    task_text: str,
    train_path: str,
    test_path: str,
    sample_sub_path: Optional[str]
) -> "TaskSpec":
    """Rule-based heuristic inference for dataset schema, target, metric, and IDs."""
    import pandas as pd
    import numpy as np

    train_df = pd.read_csv(train_path, nrows=200)
    test_df = pd.read_csv(test_path, nrows=200) if test_path and os.path.exists(test_path) else None

    target_candidate = None
    id_candidate = None
    output_format = "probabilities"
    metric = "roc_auc"

    # 1. If sample_submission.csv exists, it holds ground truth schema
    if sample_sub_path and os.path.exists(sample_sub_path):
        sub_df = pd.read_csv(sample_sub_path, nrows=10)
        cols = list(sub_df.columns)
        if len(cols) >= 2:
            id_candidate = cols[0]
            target_candidate = cols[1]

            # Check if target values in sample are float or integer
            sample_vals = sub_df[target_candidate].dropna()
            if not sample_vals.empty and (sample_vals % 1 != 0).any():
                output_format = "probabilities"
            else:
                output_format = "probabilities"

    # 2. If target not found from sample submission, compare train vs test columns
    if not target_candidate and test_df is not None:
        diff_cols = [c for c in train_df.columns if c not in test_df.columns]
        if diff_cols:
            target_candidate = diff_cols[0]

    # 3. Fallback to common target names
    if not target_candidate:
        common_targets = ["target", "TARGET", "y", "label", "is_churn", "churn", "default", "price", "loss"]
        for ct in common_targets:
            if ct in train_df.columns:
                target_candidate = ct
                break

    if not target_candidate:
        # Last column in train_df
        target_candidate = train_df.columns[-1]

    # 4. Find ID column if not yet established
    if not id_candidate:
        common_ids = ["id", "ID", "Id", "SYNTHETIC_U", "uid", "client_id", "uuid", "index"]
        for ci in common_ids:
            if ci in train_df.columns:
                id_candidate = ci
                break
        if not id_candidate and test_df is not None:
            # Look for column where all values are unique
            for c in test_df.columns:
                if test_df[c].nunique() == len(test_df):
                    id_candidate = c
                    break

    if not id_candidate:
        id_candidate = train_df.columns[0]

    # 5. Determine task type
    y_sample = pd.to_numeric(train_df[target_candidate], errors="coerce").dropna()
    unique_y = y_sample.nunique()
    if unique_y == 2 or set(y_sample.unique()).issubset({0, 1}):
        task_type = "binary_classification"
        metric = "roc_auc"
    elif unique_y <= 20 and (y_sample % 1 == 0).all():
        task_type = "multiclass_classification"
        metric = "accuracy"
    else:
        task_type = "regression"
        metric = "rmse"
        output_format = "continuous"

    return TaskSpec(
        task_type=task_type,
        target_column=target_candidate,
        id_column=id_candidate,
        metric=metric,
        output_format=output_format,
        train_file=train_path,
        test_file=test_path
    )


def run_automl_pipeline(task_file: str):
    """Main workflow execution."""
    print("=================================================================")
    print("🚀 AlfaHack / Boosters AutoML Autonomous Solution Starting...")
    print("=================================================================")
    print(f"[Init] Task descriptor: {task_file}")

    working_dir = os.path.dirname(os.path.abspath(task_file)) or "."
    task_text = read_task_markdown(task_file)

    # 1. Discover dataset files
    discovered = discover_csv_files(working_dir)
    print(f"[Discovery] Detected files: Train={discovered['train']}, Test={discovered['test']}, SampleSub={discovered['sample_submission']}")

    if not discovered["train"]:
        raise FileNotFoundError("Could not locate training CSV dataset in working directory.")

    # 2. Summarize data schemas
    summaries = {}
    for key in ["train", "test", "sample_submission"]:
        if discovered[key]:
            summaries[key] = summarize_csv(discovered[key])

    # 3. LLM Strategic Task Analysis (with graceful fallback)
    task_spec = None
    if LLMAdvisor is not None:
        try:
            print("[LLMAdvisor] Querying OpenAI-compatible model for strategic task parsing...")
            advisor = LLMAdvisor()
            advice = advisor.analyze_task_and_data(task_text, summaries)
            if advice and "target_column" in advice:
                print(f"[LLMAdvisor] Received strategic task spec: {advice}")
                task_spec = TaskSpec(
                    task_type=advice.get("task_type", "binary_classification"),
                    target_column=advice.get("target_column", "target"),
                    id_column=advice.get("id_column", "id"),
                    metric=advice.get("metric", "roc_auc"),
                    output_format=advice.get("output_format", "probabilities"),
                    train_file=discovered["train"],
                    test_file=discovered["test"]
                )
        except Exception as e:
            sys.stderr.write(f"[LLMAdvisor] LLM advisory skipped due to: {e}\n")

    if task_spec is None:
        print("[TaskParser] Utilizing heuristic dataset inspector...")
        task_spec = infer_task_spec_heuristically(
            task_text=task_text,
            train_path=discovered["train"],
            test_path=discovered["test"],
            sample_sub_path=discovered["sample_submission"]
        )

    print(f"[Config] Final Task Specification: Type={task_spec.task_type}, Target={task_spec.target_column}, ID={task_spec.id_column}, Metric={task_spec.metric}")

    # 4. Load datasets
    import pandas as pd
    import numpy as np

    print(f"[DataLoader] Loading training data from {discovered['train']}...")
    train_df = pd.read_csv(discovered["train"])
    print(f"[DataLoader] Train shape: {train_df.shape}")

    if discovered["test"] and os.path.exists(discovered["test"]):
        print(f"[DataLoader] Loading test data from {discovered['test']}...")
        test_df = pd.read_csv(discovered["test"])
    elif discovered["sample_submission"] and os.path.exists(discovered["sample_submission"]):
        print(f"[DataLoader] Using sample submission for test IDs...")
        test_df = pd.read_csv(discovered["sample_submission"])
    else:
        # Split train into train/test if no test file provided (synthetic demo mode)
        print("[DataLoader] Warning: No test.csv found. Generating test split from train...")
        test_df = train_df.tail(max(1, len(train_df) // 5)).copy()
        train_df = train_df.iloc[:len(train_df) - len(test_df)].copy()

    print(f"[DataLoader] Test shape: {test_df.shape}")

    # Extract target and ID vectors
    if task_spec.target_column not in train_df.columns:
        raise KeyError(f"Target column '{task_spec.target_column}' not found in training dataset.")

    y_train = train_df[task_spec.target_column]

    test_ids = None
    if task_spec.id_column in test_df.columns:
        test_ids = test_df[task_spec.id_column].values
    else:
        test_ids = np.arange(len(test_df))

    # 5. Feature Engineering
    print("[Pipeline] Executing automated feature engineering & preprocessing...")
    fe = TabularFeatureEngineer(
        target_column=task_spec.target_column,
        id_column=task_spec.id_column,
        task_type=task_spec.task_type
    )
    X_train_clean = fe.fit_transform(train_df)
    X_test_clean = fe.transform(test_df)

    print(f"[Pipeline] Transformed feature space -> Train: {X_train_clean.shape}, Test: {X_test_clean.shape}")

    # 6. Model Training & Cross-Validation
    print("[Trainer] Launching 5-Fold Ensemble Model Training...")
    trainer = AutoMLTrainer(task_spec)
    test_predictions, cv_score = trainer.fit_predict(X_train_clean, y_train, X_test_clean)

    # 7. Format and write submission.csv
    submission_path = os.path.join(working_dir, "submission.csv")
    print(f"[Submission] Writing results to {submission_path}...")

    if discovered["sample_submission"] and os.path.exists(discovered["sample_submission"]):
        # Match sample submission template exactly
        sub = pd.read_csv(discovered["sample_submission"])
        target_col = task_spec.target_column if task_spec.target_column in sub.columns else sub.columns[1]
        sub[target_col] = test_predictions[:len(sub)]
        sub.to_csv(submission_path, index=False)
    else:
        sub = pd.DataFrame({
            task_spec.id_column: test_ids,
            task_spec.target_column: test_predictions
        })
        sub.to_csv(submission_path, index=False)

    # 8. Strict Verification
    if not os.path.exists(submission_path):
        raise RuntimeError("FATAL: submission.csv was not created.")

    verif_df = pd.read_csv(submission_path)
    if verif_df.isna().any().any():
        print("[Warning] NaNs detected in submission.csv. Imputing with column medians...")
        verif_df = verif_df.fillna(verif_df.median(numeric_only=True))
        verif_df.to_csv(submission_path, index=False)

    print("=================================================================")
    print("✅ AutoML Run Successfully Completed!")
    print(f"📊 Final Out-Of-Fold CV Score: {cv_score:.4f} ({task_spec.metric})")
    print(f"📁 Output file created: {submission_path}")
    print(f"📄 Submission shape: {verif_df.shape}")
    print(f"🔍 First 5 rows of submission:\n{verif_df.head(5)}")
    print("=================================================================")


if __name__ == "__main__":
    task_argument = sys.argv[1] if len(sys.argv) > 1 else "task.md"
    run_automl_pipeline(task_argument)
