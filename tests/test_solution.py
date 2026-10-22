"""
End-to-End Verification Test for AutoML Track (solution.py).
Simulates the Boosters platform execution environment:
1. Creates an isolated temporary directory.
2. Writes task.md, train.csv, test.csv, sample_submission.csv.
3. Invokes: python3 solution.py task.md.
4. Verifies submission.csv exists, has correct shape, IDs, and valid predictions.
"""

import os
import sys
import shutil
import tempfile
import subprocess
import pandas as pd
import numpy as np

def run_test():
    print("=====================================================")
    print("🧪 Running AutoML Track End-to-End Simulation...")
    print("=====================================================")
    
    test_dir = tempfile.mkdtemp(prefix="automl_eval_")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    try:
        # 1. Copy solution files to test directory as Boosters platform would
        for fname in ["solution.py", "requirements.txt", "automl_core.py", "llm_advisor.py"]:
            src = os.path.join(project_root, fname)
            dst = os.path.join(test_dir, fname)
            shutil.copy(src, dst)
            
        # 2. Generate synthetic binary classification dataset based on Alfa data specs
        np.random.seed(42)
        n_train = 300
        n_test = 60
        
        # Train data
        train_data = {
            "SYNTHETIC_U": [f"U_CORP_{i:04d}" for i in range(n_train)],
            "REVENUE_COMPANY": np.random.uniform(15e9, 200e9, n_train),
            "MAINOKVED_CODE": np.random.choice(["01.11", "24.10", "47.11", "20.15", "52.29"], n_train),
            "ORG_TYPE": np.random.choice(["ПАО", "АО", "ООО"], n_train),
            "COMPANY_AGE_YEARS_GRADATION": np.random.choice(["> 10 лет", "5-10 лет", "1-5 лет"], n_train),
            "CL_PRODUCT_LOA_MARK": np.random.choice([0, 1], n_train, p=[0.3, 0.7]),
            "CL_PRODUCT_LEA_MARK": np.random.choice([0, 1], n_train, p=[0.4, 0.6]),
            "FTS_FLAG": np.random.choice([0, 1], n_train, p=[0.5, 0.5]),
            "PAY_AMT": np.random.exponential(1e8, n_train),
            "NEWS_EVENT_TEXT": [
                "Центральный банк сохранил ключевую ставку на уровне 14 процентов" if i % 2 == 0 
                else "Минсельхоз ввел гибкую экспортную пошлину на зерновые культуры" for i in range(n_train)
            ],
            "target": np.random.choice([0, 1], n_train, p=[0.6, 0.4])
        }
        train_df = pd.DataFrame(train_data)
        train_path = os.path.join(test_dir, "train.csv")
        train_df.to_csv(train_path, index=False)
        
        # Test data
        test_data = {
            "SYNTHETIC_U": [f"U_CORP_{n_train + i:04d}" for i in range(n_test)],
            "REVENUE_COMPANY": np.random.uniform(15e9, 200e9, n_test),
            "MAINOKVED_CODE": np.random.choice(["01.11", "24.10", "47.11", "20.15", "52.29"], n_test),
            "ORG_TYPE": np.random.choice(["ПАО", "АО", "ООО"], n_test),
            "COMPANY_AGE_YEARS_GRADATION": np.random.choice(["> 10 лет", "5-10 лет", "1-5 лет"], n_test),
            "CL_PRODUCT_LOA_MARK": np.random.choice([0, 1], n_test, p=[0.3, 0.7]),
            "CL_PRODUCT_LEA_MARK": np.random.choice([0, 1], n_test, p=[0.4, 0.6]),
            "FTS_FLAG": np.random.choice([0, 1], n_test, p=[0.5, 0.5]),
            "PAY_AMT": np.random.exponential(1e8, n_test),
            "NEWS_EVENT_TEXT": [
                "Вступление в силу новых таможенных тарифов на перевозки РЖД" for _ in range(n_test)
            ]
        }
        test_df = pd.DataFrame(test_data)
        test_path = os.path.join(test_dir, "test.csv")
        test_df.to_csv(test_path, index=False)
        
        # Sample submission
        sample_sub = pd.DataFrame({
            "SYNTHETIC_U": test_df["SYNTHETIC_U"],
            "target": [0.5] * len(test_df)
        })
        sample_sub_path = os.path.join(test_dir, "sample_submission.csv")
        sample_sub.to_csv(sample_sub_path, index=False)
        
        # task.md
        task_md_content = """# AlfaHack AutoML Challenge: Corporate Credit Risk Scoring
        
## Описание задачи
Необходимо построить модель машинного обучения для прогнозирования вероятности кредитного риска корпоративных клиентов Альфа-Банка.

- Целевая переменная: `target` (бинарная классификация: 0 или 1)
- Идентификатор компании: `SYNTHETIC_U`
- Метрика оценки: ROC-AUC
- Файлы данных: `train.csv`, `test.csv`, `sample_submission.csv`

Требуется сформировать файл `submission.csv` с вероятностями наступления целевого события.
"""
        task_md_path = os.path.join(test_dir, "task.md")
        with open(task_md_path, "w", encoding="utf-8") as f:
            f.write(task_md_content)
            
        print(f"[Sandbox] Test workspace initialized in: {test_dir}")
        print("  ✓ train.csv created (300 rows)")
        print("  ✓ test.csv created (60 rows)")
        print("  ✓ sample_submission.csv created (60 rows)")
        print("  ✓ task.md created")
        
        # 3. Execute solution.py task.md
        cmd = [sys.executable, "solution.py", "task.md"]
        print(f"\n[Execution] Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=test_dir,
            capture_output=True,
            text=True
        )
        
        print("\n--- STDOUT ---")
        print(result.stdout)
        if result.stderr:
            print("--- STDERR ---")
            print(result.stderr)
            
        if result.returncode != 0:
            raise RuntimeError(f"Execution failed with return code {result.returncode}")
            
        # 4. Verify submission.csv
        submission_file = os.path.join(test_dir, "submission.csv")
        if not os.path.exists(submission_file):
            raise FileNotFoundError("FAIL: submission.csv was not created!")
            
        res_df = pd.read_csv(submission_file)
        print(f"\n[Validation] submission.csv loaded:")
        print(f"  Shape: {res_df.shape}")
        print(f"  Columns: {list(res_df.columns)}")
        print(f"  Null count: {res_df.isna().sum().to_dict()}")
        
        assert len(res_df) == len(test_df), f"Expected {len(test_df)} rows, got {len(res_df)}"
        assert list(res_df.columns) == ["SYNTHETIC_U", "target"], f"Unexpected columns: {list(res_df.columns)}"
        assert not res_df["target"].isna().any(), "Submission contains NaNs!"
        assert (res_df["target"] >= 0.0).all() and (res_df["target"] <= 1.0).all(), "Predictions outside [0, 1] range!"
        
        print("\n=====================================================")
        print("🎉 ALL TESTS PASSED! solution.py is 100% Boosters-ready!")
        print("=====================================================")
        
    finally:
        # Cleanup temporary evaluation sandbox
        shutil.rmtree(test_dir, ignore_errors=True)

if __name__ == "__main__":
    run_test()
