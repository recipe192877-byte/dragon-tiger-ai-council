import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

# Top free models verified on OpenRouter (4+ Star Rating only)
MODELS_TO_TRY = [
    'meta-llama/llama-3.3-70b-instruct:free',
    'deepseek/deepseek-r1:free',
    'deepseek/deepseek-chat:free',
    'nousresearch/hermes-3-llama-3.1-405b:free',
    'google/gemma-4-31b-it:free'
]

COUNCIL_MEMBERS = [
    {
        'name': 'Streak Analyst',
        'role': 'Momentum & Trend Expert',
        'style': 'You are the Streak Analyst for Dragon Tiger. Your ONLY job is to analyze momentum. Look for long streaks (e.g., D-D-D-D) or broken streaks. Tell me if the current momentum favors Dragon or Tiger. Be concise.'
    },
    {
        'name': 'Zigzag Expert',
        'role': 'Alternation & Reversal Expert',
        'style': 'You are the Zigzag Expert for Dragon Tiger. Your ONLY job is to analyze alternation patterns (e.g., D-T-D-T or D-D-T-T-D-D). Look for reversals. Tell me if the pattern suggests Dragon or Tiger next. Be concise.'
    }
]

CHAIRMAN_PROMPT = """You are the Chairman of the Dragon Tiger AI Council.

Game History (most recent on the right):
{history}

Council Opinions:
{opinions}

RULES:
1. Look at the LAST 5-10 results carefully.
2. Count how many times Dragon appeared vs Tiger in recent history.
3. Analyze if there is a streak or alternation pattern.
4. Make your prediction: choose EXACTLY ONE of "Dragon" or "Tiger".
5. Only choose "Tie" if you see very strong evidence.

You MUST respond with ONLY this JSON (no markdown, no explanation before or after):
{{"prediction": "Dragon", "confidence": "HIGH", "reasoning": "reason here"}}

Replace the values with your actual prediction. The prediction field must be exactly "Dragon" or "Tiger" or "Tie"."""

class DragonTigerCouncil:
    def __init__(self):
        self.api_key = os.environ.get('OPENROUTER_API_KEY', '').strip()

    def _call_ai(self, system_prompt, user_prompt, max_tokens=250):
        if not self.api_key:
            return "[API_KEY_MISSING]"

        for model in MODELS_TO_TRY:
            try:
                response = requests.post(
                    OPENROUTER_URL,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {self.api_key}',
                        'HTTP-Referer': 'https://dragon-tiger-ai.local',
                        'X-Title': 'Dragon Tiger AI Council'
                    },
                    json={
                        'model': model,
                        'messages': [
                            {'role': 'system', 'content': system_prompt},
                            {'role': 'user', 'content': user_prompt}
                        ],
                        'max_tokens': max_tokens,
                        'temperature': 0.7
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get('choices', [{}])[0].get('message', {}).get('content', '')
            except Exception:
                pass
        
        return "[ALL_MODELS_FAILED]"

    def _smart_fallback(self, history):
        """If AI fails, use simple frequency-based fallback instead of always Tiger."""
        recent = history[-10:] if len(history) >= 10 else history
        d_count = recent.count('Dragon')
        t_count = recent.count('Tiger')
        # Predict whichever appeared LESS (mean reversion)
        if d_count < t_count:
            return "Dragon"
        elif t_count < d_count:
            return "Tiger"
        else:
            # Equal — check last result and predict opposite
            return "Dragon" if history[-1] == "Tiger" else "Tiger"

    def get_prediction(self, history):
        if not history:
            return {
                "prediction": "Wait",
                "confidence": "LOW",
                "reasoning": "Need some history first to analyze.",
                "opinions": []
            }
            
        if not self.api_key:
            return {
                "prediction": "Error",
                "confidence": "LOW",
                "reasoning": "OPENROUTER_API_KEY is not set in the environment.",
                "opinions": []
            }

        history_str = " -> ".join(history)
        user_prompt = f"Recent History (oldest to newest): {history_str}\nWhat is your analysis for the next round? Should it be Dragon or Tiger?"

        opinions = []
        opinions_text = ""
        
        # 1. Gather Opinions
        for member in COUNCIL_MEMBERS:
            response = self._call_ai(member['style'], user_prompt, max_tokens=150)
            clean_resp = response.strip()
            opinions.append({
                "name": member['name'],
                "analysis": clean_resp
            })
            opinions_text += f"--- {member['name']} ---\n{clean_resp}\n\n"
            time.sleep(1) # Prevent rate limits

        # 2. Chairman Synthesizes
        chairman_user_prompt = CHAIRMAN_PROMPT.format(history=history_str, opinions=opinions_text)
        chairman_response = self._call_ai(
            'You are a prediction API. You MUST output ONLY valid JSON with keys: prediction, confidence, reasoning. No other text.',
            chairman_user_prompt,
            max_tokens=200
        )

        # 3. Parse JSON with robust fallback
        fallback_pred = self._smart_fallback(history)
        result = {
            "prediction": fallback_pred,
            "confidence": "LOW",
            "reasoning": "AI response unclear, used pattern-based fallback.",
            "opinions": opinions
        }
        
        if chairman_response and '[ALL_MODELS_FAILED]' not in chairman_response:
            try:
                import re
                content = chairman_response.replace("```json", "").replace("```", "").strip()
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
                
                parsed_json = None
                idx_start = content.find('{')
                idx_end = content.rfind('}') + 1
                if idx_start != -1 and idx_end > idx_start:
                    try:
                        parsed_json = json.loads(content[idx_start:idx_end])
                    except Exception:
                        pass
                
                # 1. Try JSON parsing
                if parsed_json:
                    pred = parsed_json.get("prediction", "").strip().lower()
                    if "dragon" in pred:
                        result["prediction"] = "Dragon"
                    elif "tiger" in pred:
                        result["prediction"] = "Tiger"
                    elif "tie" in pred:
                        result["prediction"] = "Tie"
                        
                    result["confidence"] = parsed_json.get("confidence", "MEDIUM").strip()
                    result["reasoning"] = parsed_json.get("reasoning", "Council agreed.").strip()
                
                # 2. Try Regex fallback if JSON failed or prediction was empty
                if not parsed_json or result["prediction"] not in ["Dragon", "Tiger", "Tie"]:
                    match = re.search(r'"?prediction"?\s*[:=]\s*"?([a-zA-Z]+)"?', content, re.IGNORECASE)
                    if match:
                        pred_val = match.group(1).lower()
                        if "dragon" in pred_val:
                            result["prediction"] = "Dragon"
                            result["reasoning"] = "Recovered from malformed JSON (Dragon)."
                        elif "tiger" in pred_val:
                            result["prediction"] = "Tiger"
                            result["reasoning"] = "Recovered from malformed JSON (Tiger)."
                    else:
                        # 3. Super desperate fallback: just count mentions
                        if content.lower().count("dragon") > content.lower().count("tiger"):
                            result["prediction"] = "Dragon"
                            result["reasoning"] = "Recovered from raw text context."
                        elif content.lower().count("tiger") > content.lower().count("dragon"):
                            result["prediction"] = "Tiger"
                            result["reasoning"] = "Recovered from raw text context."
                            
            except Exception as e:
                print(f"[Chairman Parse Error]: {e}")

        return result
