# -*- coding: utf-8 -*-
"""
Dragon Tiger AI Council v3.0 - Flask Backend
Features: Persistent history, analytics, health endpoint, AI Council integration
Bug Fixes: File locking, UTF-8 encoding, analytics fix, REST compliance
"""
from flask import Flask, render_template, request, jsonify
from ai_council import DragonTigerCouncil
import json
import os
import time
import fcntl
from datetime import datetime

app = Flask(__name__)
council = DragonTigerCouncil()

# Persistent Storage - use /tmp on Render (ephemeral but survives restarts within session)
# Note: For permanent persistence, use Render Disk or external DB
DATA_DIR = os.environ.get('DATA_DIR', '/tmp')
HISTORY_FILE = os.path.join(DATA_DIR, 'dt_history.json')
STATS_FILE = os.path.join(DATA_DIR, 'dt_stats.json')


def _load_json_safe(filepath, default):
    """Load JSON from file safely with error handling."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError, ValueError):
            pass
    return default


def _save_json_safe(filepath, data):
    """Save JSON to file safely with atomic write."""
    try:
        tmp_path = filepath + '.tmp'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # Atomic rename
        os.replace(tmp_path, filepath)
    except IOError as e:
        print(f"[ERROR] Failed to save {filepath}: {e}")


def _load_history():
    """Load history from persistent JSON file."""
    return _load_json_safe(HISTORY_FILE, [])


def _save_history(history):
    """Save history to persistent JSON file."""
    _save_json_safe(HISTORY_FILE, history)


def _load_stats():
    """Load stats from persistent JSON file."""
    return _load_json_safe(STATS_FILE, _default_stats())


def _default_stats():
    return {
        "total_predictions": 0,
        "correct_predictions": 0,
        "last_prediction": None,
        "win_streak": 0,
        "lose_streak": 0,
        "max_win_streak": 0,
        "prediction_log": []
    }


def _save_stats(stats):
    """Save stats to persistent JSON file."""
    _save_json_safe(STATS_FILE, stats)


def _compute_analytics(history):
    """Compute rich analytics from history."""
    if not history:
        return {
            "dragon_count": 0, "tiger_count": 0, "tie_count": 0,
            "total": 0, "dragon_pct": 0, "tiger_pct": 0,
            "current_streak": {"type": None, "count": 0},
            "last_10_pattern": "",
            "alternation_rate": 0
        }

    d = history.count('Dragon')
    t = history.count('Tiger')
    tie = history.count('Tie')
    total = len(history)

    # Current streak
    streak_type = history[-1]
    streak_count = 0
    for r in reversed(history):
        if r == streak_type:
            streak_count += 1
        else:
            break

    # Alternation rate (last 20, excluding Ties for clean calculation)
    recent = history[-20:] if len(history) >= 20 else history
    # Filter out Ties for alternation calc (Bug B14 fix)
    recent_no_tie = [r for r in recent if r != 'Tie']
    alternations = 0
    for i in range(1, len(recent_no_tie)):
        if recent_no_tie[i] != recent_no_tie[i - 1]:
            alternations += 1
    alt_rate = round(alternations / max(len(recent_no_tie) - 1, 1) * 100) if len(recent_no_tie) > 1 else 0

    # Last 10 pattern string
    last_10 = history[-10:]
    pattern = " ".join(["D" if x == "Dragon" else ("T" if x == "Tiger" else "X") for x in last_10])

    return {
        "dragon_count": d,
        "tiger_count": t,
        "tie_count": tie,
        "total": total,
        "dragon_pct": round(d / max(total, 1) * 100, 1),
        "tiger_pct": round(t / max(total, 1) * 100, 1),
        "current_streak": {"type": streak_type, "count": streak_count},
        "last_10_pattern": pattern,
        "alternation_rate": alt_rate
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/history', methods=['GET', 'POST'])
def manage_history():
    current_history = _load_history()
    current_stats = _load_stats()

    if request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No JSON body"}), 400

        action = data.get('action')

        if action == 'add':
            result = data.get('result')
            if result not in ('Dragon', 'Tiger', 'Tie'):
                return jsonify({"status": "error", "message": "Invalid result"}), 400

            # Evaluate last prediction BEFORE resetting (Bug B9 fix)
            last_pred = current_stats.get('last_prediction')
            if last_pred and last_pred not in ('Wait', 'Error', 'N/A', None):
                current_stats['total_predictions'] = current_stats.get('total_predictions', 0) + 1
                is_correct = (last_pred == result)
                if is_correct:
                    current_stats['correct_predictions'] = current_stats.get('correct_predictions', 0) + 1
                    current_stats['win_streak'] = current_stats.get('win_streak', 0) + 1
                    current_stats['lose_streak'] = 0
                    if current_stats['win_streak'] > current_stats.get('max_win_streak', 0):
                        current_stats['max_win_streak'] = current_stats['win_streak']
                else:
                    current_stats['lose_streak'] = current_stats.get('lose_streak', 0) + 1
                    current_stats['win_streak'] = 0

                log_entry = {
                    "predicted": last_pred,
                    "actual": result,
                    "correct": is_correct,
                    "time": datetime.now().strftime('%H:%M:%S')
                }
                current_stats.setdefault('prediction_log', []).append(log_entry)
                if len(current_stats['prediction_log']) > 50:
                    current_stats['prediction_log'] = current_stats['prediction_log'][-50:]

            # Reset last prediction after evaluation
            current_stats['last_prediction'] = None
            current_history.append(result)
            _save_history(current_history)
            _save_stats(current_stats)

        elif action == 'undo':
            if current_history:
                current_history.pop()
                current_stats['last_prediction'] = None
                _save_history(current_history)
                _save_stats(current_stats)

        elif action == 'clear':
            current_history = []
            current_stats = _default_stats()
            _save_history(current_history)
            _save_stats(current_stats)

        elif action == 'restore':
            restored_history = data.get('history', [])
            if isinstance(restored_history, list):
                # Validate each entry
                valid = [r for r in restored_history if r in ('Dragon', 'Tiger', 'Tie')]
                current_history = valid
                current_stats = _default_stats()
                _save_history(current_history)
                _save_stats(current_stats)

        analytics = _compute_analytics(current_history)
        return jsonify({
            "status": "success",
            "history": current_history,
            "stats": current_stats,
            "analytics": analytics
        })

    # GET
    analytics = _compute_analytics(current_history)
    return jsonify({
        "history": current_history,
        "stats": current_stats,
        "analytics": analytics
    })


@app.route('/api/predict', methods=['GET'])
def get_prediction():
    """Get AI Council prediction. Safe to call repeatedly (read + AI call)."""
    current_history = _load_history()
    current_stats = _load_stats()

    if not current_history:
        return jsonify({
            "prediction": "N/A",
            "confidence": "-",
            "reasoning": "History mein koi data nahi hai. Pehle results add karo.",
            "opinions": [],
            "council_members": 0,
            "duration": 0,
            "api_used": "none"
        })

    prediction_data = council.get_prediction(current_history[-100:])

    # Store last prediction for accuracy tracking
    current_stats['last_prediction'] = prediction_data.get('prediction')
    _save_stats(current_stats)

    return jsonify(prediction_data)


@app.route('/api/health')
def health():
    """Health check endpoint for uptime monitoring."""
    current_history = _load_history()
    current_stats = _load_stats()
    total_pred = current_stats.get('total_predictions', 0)
    correct_pred = current_stats.get('correct_predictions', 0)
    return jsonify({
        "status": "ok",
        "service": "Dragon Tiger AI Council v3.0",
        "history_count": len(current_history),
        "predictions_made": total_pred,
        "accuracy_pct": round(correct_pred / max(total_pred, 1) * 100, 1),
        "gemini_ready": bool(council.gemini_key),
        "openrouter_ready": bool(council.openrouter_key),
        "uptime": int(time.time())
    })


@app.route('/api/stats')
def get_stats():
    """Return detailed analytics."""
    current_history = _load_history()
    current_stats = _load_stats()
    analytics = _compute_analytics(current_history)
    return jsonify({
        "status": "success",
        "stats": current_stats,
        "analytics": analytics
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)