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

CHAIRMAN_PROMPT = """You are the Chairman of the Dragon Tiger AI Council. Two expert analysts have reviewed the recent game history and provided their opinions on what will come next.

Game History (Chronological):
{history}

Council Opinions:
{opinions}

Your job is to synthesize these opinions and make a final prediction for the next round.
You MUST choose either "Dragon", "Tiger", or "Tie". (Note: Tie is rare, so only choose it if you are highly confident).

Format your response EXACTLY as valid JSON:
{{
  "prediction": "Dragon / Tiger / Tie",
  "confidence": "HIGH / MEDIUM / LOW",
  "reasoning": "A short 1-line explanation of why in English or Hindi."
}}

IMPORTANT: Return ONLY the JSON, no other text or markdown formatting."""

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
                    timeout=15
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get('choices', [{}])[0].get('message', {}).get('content', '')
            except Exception:
                pass
        
        return "[ALL_MODELS_FAILED]"

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
        user_prompt = f"Recent History: {history_str}\nWhat is your analysis for the next round?"

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
        chairman_response = self._call_ai('You are a JSON-only API. Output strict JSON.', chairman_user_prompt, max_tokens=200)

        # 3. Parse JSON
        result = {
            "prediction": "Tiger", # default fallback
            "confidence": "LOW",
            "reasoning": "Failed to parse chairman JSON.",
            "opinions": opinions
        }
        
        try:
            content = chairman_response.replace("```json", "").replace("```", "").strip()
            idx_start = content.find('{')
            idx_end = content.rfind('}') + 1
            if idx_start != -1 and idx_end > idx_start:
                parsed = json.loads(content[idx_start:idx_end])
                result["prediction"] = parsed.get("prediction", "Tiger").strip()
                result["confidence"] = parsed.get("confidence", "LOW").strip()
                result["reasoning"] = parsed.get("reasoning", "Council agreed.").strip()
        except Exception:
            pass

        return result
