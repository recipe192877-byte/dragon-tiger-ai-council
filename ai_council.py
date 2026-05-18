"""
Dragon Tiger AI Council v2.0 — Multi-Model Swarm Intelligence
4 AI experts analyze patterns independently, then a Chairman synthesizes consensus.
Uses OpenRouter API with top-rated free models.
"""
import os
import json
import re
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

# Top free models verified on OpenRouter (Rating 3.8+) — May 2026
MODELS_TO_TRY = [
    'nousresearch/hermes-3-llama-3.1-405b:free',
    'meta-llama/llama-3.3-70b-instruct:free',
    'nvidia/nemotron-3-super-120b-a12b:free',
    'deepseek/deepseek-r1:free',
    'deepseek/deepseek-chat:free',
    'google/gemma-4-31b-it:free',
    'qwen/qwen3-next-80b-a3b-instruct:free',
    'deepseek/deepseek-v4-flash:free',
    'nvidia/nemotron-3-nano-30b-a3b:free',
]

# 4 Council Members — each AI has a unique analytical personality
COUNCIL_MEMBERS = [
    {
        'name': 'StreakBot',
        'role': 'Momentum & Trend Expert',
        'style': 'You are StreakBot for Dragon Tiger. Analyze ONLY momentum and streaks. Look for long runs (D-D-D-D or T-T-T), broken streaks, and momentum shifts. State clearly if momentum favors Dragon or Tiger. Give your prediction as EXACTLY "Dragon" or "Tiger". Be concise (2-3 sentences max).'
    },
    {
        'name': 'ZigzagAI',
        'role': 'Alternation & Reversal Expert',
        'style': 'You are ZigzagAI for Dragon Tiger. Analyze ONLY alternation patterns. Look for zigzag (D-T-D-T), double-runs (D-D-T-T), and reversal points. State which pattern is active and predict if it continues or breaks. Give your prediction as EXACTLY "Dragon" or "Tiger". Be concise (2-3 sentences max).'
    },
    {
        'name': 'FreqMaster',
        'role': 'Frequency & Distribution Analyst',
        'style': 'You are FreqMaster for Dragon Tiger. Analyze ONLY frequency distribution. Count Dragon vs Tiger in the last 10-15 results. Apply mean reversion theory — if one side appeared too much, predict the other. Give your prediction as EXACTLY "Dragon" or "Tiger". Be concise (2-3 sentences max).'
    },
    {
        'name': 'RiskGuard',
        'role': 'Risk Assessment & Confidence Officer',
        'style': 'You are RiskGuard for Dragon Tiger. Analyze the OVERALL risk level. Look at volatility (how unpredictable the pattern is), agreement between other patterns, and whether this is a safe round to play or skip. Rate risk as HIGH/MEDIUM/LOW and give your prediction as EXACTLY "Dragon" or "Tiger". Be concise (2-3 sentences max).'
    },
]

CHAIRMAN_PROMPT = """You are the Chairman of the Dragon Tiger AI Council.

Game History (oldest → newest, last result on right):
{history}

Quick Stats:
- Total rounds: {total}
- Dragon count: {d_count} | Tiger count: {t_count}
- Last 5: {last5}

Council Expert Opinions:
{opinions}

RULES:
1. Carefully read each expert's analysis.
2. Count how many experts chose Dragon vs Tiger.
3. Go with the MAJORITY vote. If it's a tie, use the last 5 results to break it.
4. Rate confidence: HIGH if 3-4 agree, MEDIUM if 2-2, LOW if unclear.
5. Choose EXACTLY ONE of "Dragon" or "Tiger". Only choose "Tie" with very strong evidence.

You MUST respond with ONLY this JSON (no markdown, no explanation):
{{"prediction": "Dragon", "confidence": "HIGH", "reasoning": "reason in Hindi/English mix"}}

Replace values with your actual analysis. The prediction field MUST be exactly "Dragon" or "Tiger"."""


class DragonTigerCouncil:
    """Multi-AI Swarm Intelligence for Dragon Tiger predictions."""

    def __init__(self):
        load_dotenv(override=False)
        self.api_key = os.environ.get('OPENROUTER_API_KEY', '').strip()
        if self.api_key:
            masked = self.api_key[:8] + '...' + self.api_key[-4:]
            print(f"[DT-COUNCIL] API Key loaded: {masked}")
        else:
            print("[DT-COUNCIL] ⚠️ WARNING: No OPENROUTER_API_KEY! Set in Render Dashboard → Environment.")

    def _call_ai(self, system_prompt, user_prompt, max_tokens=250):
        """Call AI models with multi-model fallback."""
        if not self.api_key:
            return None

        for model in MODELS_TO_TRY:
            try:
                response = requests.post(
                    OPENROUTER_URL,
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {self.api_key}',
                        'HTTP-Referer': 'https://dragon-tiger-ai-council.onrender.com',
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
                    content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                    if content:
                        return content
                else:
                    print(f"[DT-COUNCIL] {model} failed ({response.status_code}). Trying fallback...")
            except Exception as e:
                print(f"[DT-COUNCIL] Error calling {model}: {e}")
        
        return None

    def _smart_fallback(self, history):
        """If AI fails, use frequency-based mean reversion fallback."""
        recent = history[-10:] if len(history) >= 10 else history
        d_count = recent.count('Dragon')
        t_count = recent.count('Tiger')
        if d_count < t_count:
            return "Dragon"
        elif t_count < d_count:
            return "Tiger"
        else:
            return "Dragon" if history[-1] == "Tiger" else "Tiger"

    def _parse_ai_json(self, raw_response):
        """Robust JSON parser that handles markdown fences, <think> tags, etc."""
        if not raw_response:
            return None
        try:
            cleaned = raw_response.strip()
            # Strip markdown code fences
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            # Strip <think>...</think> tags (DeepSeek R1)
            cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL).strip()
            
            json_start = cleaned.find('{')
            json_end = cleaned.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                return json.loads(cleaned[json_start:json_end])
        except json.JSONDecodeError:
            pass
        return None

    def get_prediction(self, history):
        """Hold an AI Council meeting and return consensus prediction."""
        if not history:
            return {
                "prediction": "Wait",
                "confidence": "LOW",
                "reasoning": "History mein koi data nahi hai. Pehle kuch results add karo.",
                "opinions": [],
                "council_members": 0,
                "duration": 0
            }
            
        if not self.api_key:
            fallback = self._smart_fallback(history) if history else "Wait"
            return {
                "prediction": fallback,
                "confidence": "LOW",
                "reasoning": "API Key missing — pattern fallback used. Set OPENROUTER_API_KEY in Render Dashboard.",
                "opinions": [],
                "council_members": 0,
                "duration": 0
            }

        meeting_start = time.time()
        history_str = " → ".join(history[-30:])  # Last 30 for context
        d_count = history.count('Dragon')
        t_count = history.count('Tiger')
        last5 = " → ".join(history[-5:]) if len(history) >= 5 else " → ".join(history)
        
        user_prompt = f"Recent History (oldest → newest): {history_str}\n\nDragon: {d_count} | Tiger: {t_count} | Last 5: {last5}\n\nWhat is your analysis for the next round?"

        # Step 1: Gather individual expert opinions
        opinions = []
        opinions_text = ""
        
        for member in COUNCIL_MEMBERS:
            print(f"[DT-COUNCIL] {member['name']} analyzing...")
            response = self._call_ai(member['style'], user_prompt, max_tokens=150)
            
            analysis = response.strip() if response else f"[{member['name']} could not respond]"
            opinions.append({
                "name": member['name'],
                "role": member['role'],
                "analysis": analysis
            })
            opinions_text += f"--- {member['name']} ({member['role']}) ---\n{analysis}\n\n"
            time.sleep(0.8)

        # Step 2: Chairman synthesizes consensus
        print("[DT-COUNCIL] Chairman synthesizing consensus...")
        chairman_user_prompt = CHAIRMAN_PROMPT.format(
            history=history_str,
            total=len(history),
            d_count=d_count,
            t_count=t_count,
            last5=last5,
            opinions=opinions_text
        )
        
        chairman_response = self._call_ai(
            'You are a prediction API. You MUST output ONLY valid JSON with keys: prediction, confidence, reasoning. No other text.',
            chairman_user_prompt,
            max_tokens=200
        )

        # Step 3: Parse with robust fallback chain
        fallback_pred = self._smart_fallback(history)
        result = {
            "prediction": fallback_pred,
            "confidence": "LOW",
            "reasoning": "AI response unclear, pattern-based fallback used.",
            "opinions": opinions,
            "council_members": len([o for o in opinions if '[' not in o['analysis'][:5]]),
            "duration": 0
        }
        
        if chairman_response:
            # Try JSON parsing
            parsed = self._parse_ai_json(chairman_response)
            if parsed:
                pred = str(parsed.get("prediction", "")).strip().lower()
                if "dragon" in pred:
                    result["prediction"] = "Dragon"
                elif "tiger" in pred:
                    result["prediction"] = "Tiger"
                elif "tie" in pred:
                    result["prediction"] = "Tie"
                    
                result["confidence"] = str(parsed.get("confidence", "MEDIUM")).strip().upper()
                result["reasoning"] = str(parsed.get("reasoning", "Council agreed.")).strip()
            else:
                # Regex fallback
                match = re.search(r'"?prediction"?\s*[:=]\s*"?([a-zA-Z]+)"?', chairman_response, re.IGNORECASE)
                if match:
                    pred_val = match.group(1).lower()
                    if "dragon" in pred_val:
                        result["prediction"] = "Dragon"
                        result["reasoning"] = "Recovered from partial AI response (Dragon)."
                    elif "tiger" in pred_val:
                        result["prediction"] = "Tiger"
                        result["reasoning"] = "Recovered from partial AI response (Tiger)."
                else:
                    # Count mentions
                    d_mentions = chairman_response.lower().count("dragon")
                    t_mentions = chairman_response.lower().count("tiger")
                    if d_mentions > t_mentions:
                        result["prediction"] = "Dragon"
                        result["reasoning"] = "Extracted from raw AI context (Dragon dominant)."
                    elif t_mentions > d_mentions:
                        result["prediction"] = "Tiger"
                        result["reasoning"] = "Extracted from raw AI context (Tiger dominant)."

        result["duration"] = round(time.time() - meeting_start, 1)
        print(f"[DT-COUNCIL] Meeting complete in {result['duration']}s → {result['prediction']} ({result['confidence']})")
        return result
