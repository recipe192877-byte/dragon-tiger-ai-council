# -*- coding: utf-8 -*-
"""
Dragon Tiger AI Council v3.0 - Multi-Model Swarm Intelligence
Primary: Google Gemini Flash (fast + reliable)
Fallback: OpenRouter (free models)
4 AI experts analyze patterns, then Chairman synthesizes consensus.
"""
import os
import json
import re
import time
import requests
import concurrent.futures
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# API Configuration
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '').strip()
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '').strip()

GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent'
OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

# OpenRouter fallback model list
OPENROUTER_MODELS = [
    'google/gemma-2-9b-it:free',
    'meta-llama/llama-3-8b-instruct:free',
    'mistralai/mistral-7b-instruct:free',
    'qwen/qwen-2.5-7b-instruct:free',
    'openrouter/auto',
]

# 4 Council Members
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
        'style': 'You are FreqMaster for Dragon Tiger. Analyze ONLY frequency distribution. Count Dragon vs Tiger in the last 10-15 results. Apply mean reversion theory - if one side appeared too much, predict the other. Give your prediction as EXACTLY "Dragon" or "Tiger". Be concise (2-3 sentences max).'
    },
    {
        'name': 'RiskGuard',
        'role': 'Risk Assessment & Confidence Officer',
        'style': 'You are RiskGuard for Dragon Tiger. Analyze the OVERALL risk level. Look at volatility (how unpredictable the pattern is), agreement between other patterns, and whether this is a safe round to play or skip. Rate risk as HIGH/MEDIUM/LOW and give your prediction as EXACTLY "Dragon" or "Tiger". Be concise (2-3 sentences max).'
    },
]

CHAIRMAN_PROMPT = """You are the Chairman of the Dragon Tiger AI Council.

Game History (oldest to newest, last result on right):
{history}

Quick Stats:
- Total rounds: {total}
- Dragon count: {d_count} | Tiger count: {t_count}
- Last 5: {last5}

Council Expert Opinions:
{opinions}

RULES:
1. Carefully read each expert analysis.
2. Count how many experts chose Dragon vs Tiger.
3. Go with the MAJORITY vote. If tied, use the last 5 results to break it.
4. Rate confidence: HIGH if 3-4 agree, MEDIUM if 2-2, LOW if unclear.
5. Choose EXACTLY ONE of "Dragon" or "Tiger". Only choose "Tie" with very strong evidence.

You MUST respond with ONLY this JSON (no markdown, no explanation):
{{"prediction": "Dragon", "confidence": "HIGH", "reasoning": "reason in 1-2 sentences"}}

Replace values with your actual analysis. The prediction field MUST be exactly "Dragon" or "Tiger"."""


class DragonTigerCouncil:
    """Multi-AI Swarm Intelligence for Dragon Tiger predictions.
    Primary: Gemini Flash API. Fallback: OpenRouter free models.
    """

    def __init__(self):
        self.gemini_key = GEMINI_API_KEY
        self.openrouter_key = OPENROUTER_API_KEY
        self.use_gemini = bool(self.gemini_key)
        self.use_openrouter = bool(self.openrouter_key)

        if self.gemini_key:
            masked = self.gemini_key[:8] + '...' + self.gemini_key[-4:]
            print(f"[DT-COUNCIL] Gemini API ready: {masked}")
        else:
            print("[DT-COUNCIL] WARNING: No GEMINI_API_KEY found.")

        if self.openrouter_key:
            masked = self.openrouter_key[:12] + '...' + self.openrouter_key[-4:]
            print(f"[DT-COUNCIL] OpenRouter fallback ready: {masked}")
        else:
            print("[DT-COUNCIL] WARNING: No OPENROUTER_API_KEY. No fallback available.")

    def _call_gemini(self, system_prompt, user_prompt, max_tokens=300):
        """Call Gemini Flash API. Returns text or None on failure."""
        if not self.gemini_key:
            return None
        try:
            url = f"{GEMINI_URL}?key={self.gemini_key}"
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": full_prompt}]}
                ],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.3,
                    "topP": 0.8,
                }
            }
            resp = requests.post(url, json=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get('candidates', [])
                if candidates:
                    content = candidates[0].get('content', {})
                    parts = content.get('parts', [])
                    if parts:
                        text = parts[0].get('text', '').strip()
                        if text:
                            return text
            else:
                print(f"[DT-COUNCIL] Gemini error {resp.status_code}: {resp.text[:200]}")
                if resp.status_code in (400, 401, 403):
                    return None
        except Exception as e:
            print(f"[DT-COUNCIL] Gemini exception: {e}")
        return None

    def _call_openrouter(self, system_prompt, user_prompt, max_tokens=200):
        """Call OpenRouter with model fallback chain. Returns text or None."""
        if not self.openrouter_key:
            return None
        headers = {
            'Authorization': f'Bearer {self.openrouter_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://dragon-tiger-ai-council.onrender.com',
            'X-Title': 'Dragon Tiger AI Council',
        }
        for model in OPENROUTER_MODELS:
            try:
                payload = {
                    'model': model,
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_prompt},
                    ],
                    'max_tokens': max_tokens,
                    'temperature': 0.3,
                }
                resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                    if content:
                        print(f"[DT-COUNCIL] OpenRouter success via {model}")
                        return content
                else:
                    print(f"[DT-COUNCIL] OpenRouter {model} failed ({resp.status_code})")
                    if resp.status_code in (401, 402, 403):
                        break
            except Exception as e:
                print(f"[DT-COUNCIL] OpenRouter {model} exception: {e}")
        return None

    def _call_ai(self, system_prompt, user_prompt, max_tokens=200):
        """Call Gemini first. If it fails, fall back to OpenRouter."""
        if self.gemini_key:
            result = self._call_gemini(system_prompt, user_prompt, max_tokens)
            if result:
                return result
            print("[DT-COUNCIL] Gemini failed, trying OpenRouter fallback...")
        if self.openrouter_key:
            result = self._call_openrouter(system_prompt, user_prompt, max_tokens)
            if result:
                return result
        return None

    def _smart_fallback(self, history):
        """If all AI fails, use frequency-based mean reversion fallback."""
        if not history:
            return "Dragon"
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
        """Robust JSON parser - handles markdown fences, think tags, extra text."""
        if not raw_response:
            return None
        try:
            cleaned = raw_response.strip()
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE)
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
                "duration": 0,
                "api_used": "none"
            }

        if not self.gemini_key and not self.openrouter_key:
            fallback = self._smart_fallback(history)
            return {
                "prediction": fallback,
                "confidence": "LOW",
                "reasoning": "Koi API key set nahi hai. Pattern-based fallback use hua. Render Dashboard mein GEMINI_API_KEY set karo.",
                "opinions": [],
                "council_members": 0,
                "duration": 0,
                "api_used": "pattern_fallback"
            }

        meeting_start = time.time()
        history_str = " -> ".join(history[-30:])
        d_count = history.count('Dragon')
        t_count = history.count('Tiger')
        last5 = " -> ".join(history[-5:]) if len(history) >= 5 else " -> ".join(history)

        user_prompt = (
            f"Recent History (oldest -> newest): {history_str}\n\n"
            f"Dragon: {d_count} | Tiger: {t_count} | Last 5: {last5}\n\n"
            f"What is your analysis for the next round?"
        )

        # Step 1: Gather expert opinions in parallel
        opinions = [None] * len(COUNCIL_MEMBERS)

        def run_member(index, member):
            print(f"[DT-COUNCIL] {member['name']} analyzing...")
            try:
                response = self._call_ai(member['style'], user_prompt, max_tokens=150)
                analysis = response.strip() if response else f"[{member['name']} could not respond]"
            except Exception as e:
                analysis = f"[{member['name']} failed: {e}]"
            return index, {
                "name": member['name'],
                "role": member['role'],
                "analysis": analysis
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(run_member, idx, m) for idx, m in enumerate(COUNCIL_MEMBERS)]
            for future in concurrent.futures.as_completed(futures, timeout=60):
                try:
                    idx, opinion = future.result()
                    opinions[idx] = opinion
                except Exception as e:
                    print(f"[DT-COUNCIL] Expert execution failed: {e}")

        # Build opinions text
        opinions_text = ""
        valid_opinions = []
        for o in opinions:
            if o:
                opinions_text += f"--- {o['name']} ({o['role']}) ---\n{o['analysis']}\n\n"
                valid_opinions.append(o)

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

        chairman_system = (
            'You are a prediction API. Output ONLY valid JSON with keys: '
            'prediction, confidence, reasoning. No other text, no markdown.'
        )

        chairman_response = self._call_ai(chairman_system, chairman_user_prompt, max_tokens=250)

        api_used = "pattern_fallback"
        if chairman_response:
            api_used = "gemini" if self.gemini_key else "openrouter"

        # Step 3: Parse with robust fallback chain
        fallback_pred = self._smart_fallback(history)
        result = {
            "prediction": fallback_pred,
            "confidence": "LOW",
            "reasoning": "AI response unclear, pattern-based fallback used.",
            "opinions": valid_opinions,
            "council_members": len([o for o in valid_opinions if not o['analysis'].startswith('[')]),
            "duration": 0,
            "api_used": api_used
        }

        if chairman_response:
            parsed = self._parse_ai_json(chairman_response)
            if parsed:
                pred = str(parsed.get("prediction", "")).strip().lower()
                if "dragon" in pred:
                    result["prediction"] = "Dragon"
                elif "tiger" in pred:
                    result["prediction"] = "Tiger"
                elif "tie" in pred:
                    result["prediction"] = "Tie"

                conf = str(parsed.get("confidence", "MEDIUM")).strip().upper()
                if conf not in ("HIGH", "MEDIUM", "LOW"):
                    conf = "MEDIUM"
                result["confidence"] = conf
                result["reasoning"] = str(parsed.get("reasoning", "Council agreed.")).strip()
            else:
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
                    d_mentions = chairman_response.lower().count("dragon")
                    t_mentions = chairman_response.lower().count("tiger")
                    if d_mentions > t_mentions:
                        result["prediction"] = "Dragon"
                        result["reasoning"] = "Extracted from raw AI context (Dragon dominant)."
                    elif t_mentions > d_mentions:
                        result["prediction"] = "Tiger"
                        result["reasoning"] = "Extracted from raw AI context (Tiger dominant)."

        result["duration"] = round(time.time() - meeting_start, 1)
        print(
            f"[DT-COUNCIL] Meeting done in {result['duration']}s -> "
            f"{result['prediction']} ({result['confidence']}) via {result['api_used']}"
        )
        return result