"""
LLM Advisor Module for AutoML Track (AlfaHack / Boosters).
Handles OpenAI-compatible communication with the competition AI model:
- Primary Base URL: https://changellenge.up.railway.app/v1
- Fallback Base URL: https://api.alfahack-gateway26.ru/v1
- Model: qwen/qwen3.8-27b (or from OPENAI_MODEL env)
- Reads OPENAI_BASE_URL and OPENAI_API_KEY from environment conforming to competition rules.

Provides both standard OpenAI client and zero-dependency urllib fallback.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List

# Competition Defaults
DEFAULT_BASE_URL = "https://changellenge.up.railway.app/v1"
FALLBACK_BASE_URL = "https://api.alfahack-gateway26.ru/v1"
DEFAULT_MODEL = "google/gemma-4-26b-a4b-it"
FALLBACK_MODELS = ["google/gemma-4-26b-a4b-it", "qwen/qwen3.6-35b-a3b", "deepseek/deepseek-v4.1-flash"]

def _load_local_env():
    env_paths = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(os.getcwd(), ".env")
    ]
    for p in env_paths:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("\"'")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass
            break

_load_local_env()
LOCAL_FALLBACK_KEY = os.getenv("OPENAI_API_KEY", "")



class LLMAdvisor:
    """Autonomous LLM consultant for task parsing, feature engineering, and modeling strategy."""

    def __init__(self):
        self.base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.api_key = os.getenv("OPENAI_API_KEY", LOCAL_FALLBACK_KEY)
        self.model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
        self.client = None

        # Attempt to initialize standard openai client if available
        try:
            from openai import OpenAI
            self.client = OpenAI(
                base_url=self.base_url,
                api_key=self.api_key or "sk-dummy"
            )
        except Exception:
            self.client = None

    def query_chat_completion(self, system_prompt: str, user_prompt: str, timeout: int = 25) -> Optional[str]:
        """Calls /chat/completions using openai SDK or raw urllib fallback."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # 1. Try official SDK if initialized
        if self.client is not None:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1500,
                    timeout=timeout,
                )
                if response.choices and response.choices[0].message:
                    return response.choices[0].message.content
            except Exception as e:
                # Log and fallback to direct HTTP / fallback URL
                sys.stderr.write(f"[LLMAdvisor] OpenAI SDK error: {e}. Trying raw HTTP...\n")

        # 2. Raw HTTP request trying primary base_url, then alternative gateways
        all_gateways = [
            self.base_url,
            DEFAULT_BASE_URL,
            FALLBACK_BASE_URL
        ]
        urls_to_try = []
        seen = set()
        for gw in all_gateways:
            clean = gw.rstrip("/")
            if clean and clean not in seen:
                seen.add(clean)
                urls_to_try.append(f"{clean}/chat/completions")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 1500,
        }
        data_bytes = json.dumps(payload).encode("utf-8")

        for url in urls_to_try:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "User-Agent": "AlfaHack-AutoML-Solution/1.0"
                }
                req = urllib.request.Request(url, data=data_bytes, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status == 200:
                        res_json = json.loads(resp.read().decode("utf-8"))
                        choices = res_json.get("choices", [])
                        if choices:
                            return choices[0].get("message", {}).get("content", "")
            except urllib.error.HTTPError as he:
                try:
                    err_body = he.read().decode("utf-8", errors="ignore")
                except Exception:
                    err_body = ""
                sys.stderr.write(f"[LLMAdvisor] HTTP {he.code} from {url}: {err_body}\n")
            except Exception as ex:
                sys.stderr.write(f"[LLMAdvisor] Connection error to {url}: {ex}\n")

        return None

    def analyze_task_and_data(
        self,
        task_markdown: str,
        csv_summaries: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Asks the LLM to inspect task.md and data schema to extract:
        - target_column
        - id_column
        - task_type (binary_classification, multiclass_classification, regression)
        - metric (roc_auc, f1, accuracy, logloss, rmse, r2)
        - recommended_features / special notes
        """
        system_prompt = (
            "You are an expert AutoML competition architect. Analyze the task description and data summaries.\n"
            "Respond ONLY with a valid JSON object with the following schema:\n"
            "{\n"
            '  "target_column": "<name of column to predict>",\n'
            '  "id_column": "<name of ID column for submission>",\n'
            '  "task_type": "binary_classification" | "multiclass_classification" | "regression",\n'
            '  "metric": "roc_auc" | "f1" | "accuracy" | "logloss" | "rmse" | "mae" | "r2",\n'
            '  "train_file": "<filename of training dataset>",\n'
            '  "test_file": "<filename of test dataset>",\n'
            '  "output_format": "probabilities" | "discrete_labels",\n'
            '  "feature_strategy": "<brief notes>"\n'
            "}"
        )

        user_prompt = (
            f"=== TASK.MD DESCRIPTION ===\n{task_markdown[:3000]}\n\n"
            f"=== AVAILABLE DATA FILES & SCHEMAS ===\n{json.dumps(csv_summaries, ensure_ascii=False, indent=2)[:3000]}\n\n"
            f"Extract the exact target, ID, task type, metric, and files. Return JSON only."
        )

        raw_output = self.query_chat_completion(system_prompt, user_prompt, timeout=20)
        if not raw_output:
            return None

        # Extract JSON from markdown fences if present
        clean_text = raw_output.strip()
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()

        try:
            parsed = json.loads(clean_text)
            return parsed
        except Exception as e:
            sys.stderr.write(f"[LLMAdvisor] Failed to parse JSON response: {e}\nRaw output: {raw_output[:200]}\n")
            return None
