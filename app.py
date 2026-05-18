"""
Dragon Tiger AI Council v2.0 — Flask Backend
Features: Persistent history, analytics, health endpoint, AI Council integration
"""
from flask import Flask, render_template, request, jsonify
from ai_council import DragonTigerCouncil
import json
import os
import time
from datetime import datetime

app = Flask(__name__)
council = DragonTigerCouncil()

# ── Persistent Storage ──
HISTORY_FILE = 'history.json'
STATS_FILE = 'stats.json'


def _load_history():
    """Load history from persistent JSON file."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def _save_history(history):
    """Save history to persistent JSON file."""
    try:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f)
    except IOError as e:
        print(f"[ERROR] Failed to save history: {e}")


def _load_stats():
    """Load stats from persistent JSON file."""
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return _default_stats()


def _default_stats():
    return {
        "total_predictions": 0,
        "correct_predictions": 0,
        "last_prediction": None,
        "win_streak": 0,
        "lose_streak": 0,
        "max_win_streak": 0,
        "prediction_log": []  # Last 50 predictions
    }


def _save_stats(stats):
    """Save stats to persistent JSON file."""
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
    except IOError as e:
        print(f"[ERROR] Failed to save stats: {e}")


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

    # Alternation rate (last 20)
    recent = history[-20:] if len(history) >= 20 else history
    alternations = 0
    for i in range(1, len(recent)):
        if recent[i] != recent[i - 1]:
            alternations += 1
    alt_rate = round(alternations / max(len(recent) - 1, 1) * 100)

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


# ── Initialize state from files ──
history = _load_history()
stats = _load_stats()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/history', methods=['GET', 'POST'])
def manage_history():
    global history, stats
    if request.method == 'POST':
        data = request.json
        action = data.get('action')

        if action == 'add':
            result = data.get('result')
            if result in ['Dragon', 'Tiger', 'Tie']:
                # Evaluate last prediction
                if stats['last_prediction'] and stats['last_prediction'] not in ('Wait', 'Error', 'N/A'):
                    stats['total_predictions'] += 1
                    is_correct = (stats['last_prediction'] == result)
                    if is_correct:
                        stats['correct_predictions'] += 1
                        stats['win_streak'] += 1
                        stats['lose_streak'] = 0
                        if stats['win_streak'] > stats.get('max_win_streak', 0):
                            stats['max_win_streak'] = stats['win_streak']
                    else:
                        stats['lose_streak'] += 1
                        stats['win_streak'] = 0

                    # Log prediction result
                    log_entry = {
                        "predicted": stats['last_prediction'],
                        "actual": result,
                        "correct": is_correct,
                        "time": datetime.now().strftime('%H:%M:%S')
                    }
                    stats.setdefault('prediction_log', []).append(log_entry)
                    # Keep last 50
                    if len(stats['prediction_log']) > 50:
                        stats['prediction_log'] = stats['prediction_log'][-50:]

                stats['last_prediction'] = None
                history.append(result)
                _save_history(history)
                _save_stats(stats)

        elif action == 'undo':
            if history:
                history.pop()
                stats['last_prediction'] = None
                _save_history(history)
                _save_stats(stats)

        elif action == 'clear':
            history = []
            stats = _default_stats()
            _save_history(history)
            _save_stats(stats)

        analytics = _compute_analytics(history)
        return jsonify({"status": "success", "history": history, "stats": stats, "analytics": analytics})

    analytics = _compute_analytics(history)
    return jsonify({"history": history, "stats": stats, "analytics": analytics})


@app.route('/api/predict', methods=['GET'])
def get_prediction():
    global stats
    if not history:
        return jsonify({
            "prediction": "N/A",
            "confidence": "-",
            "reasoning": "History mein koi data nahi hai. Pehle results add karo.",
            "opinions": [],
            "council_members": 0,
            "duration": 0
        })

    prediction_data = council.get_prediction(history[-100:])
    stats['last_prediction'] = prediction_data.get('prediction')
    _save_stats(stats)

    return jsonify(prediction_data)


@app.route('/api/health')
def health():
    """Health check endpoint for uptime monitoring."""
    return jsonify({
        "status": "ok",
        "service": "Dragon Tiger AI Council v2.0",
        "history_count": len(history),
        "predictions_made": stats.get('total_predictions', 0),
        "accuracy_pct": round(
            stats.get('correct_predictions', 0) / max(stats.get('total_predictions', 1), 1) * 100, 1
        ),
        "api_key_set": bool(council.api_key),
        "uptime": int(time.time())
    })


@app.route('/api/stats')
def get_stats():
    """Return detailed analytics."""
    analytics = _compute_analytics(history)
    return jsonify({
        "status": "success",
        "stats": stats,
        "analytics": analytics
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)
