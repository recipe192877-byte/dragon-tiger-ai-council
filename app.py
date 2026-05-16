from flask import Flask, render_template, request, jsonify
from ai_council import DragonTigerCouncil

app = Flask(__name__)
council = DragonTigerCouncil()

# In-memory state
history = []
stats = {
    "total_predictions": 0,
    "correct_predictions": 0,
    "last_prediction": None
}

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
                # Evaluate last prediction if exists
                if stats['last_prediction'] and stats['last_prediction'] != 'Wait' and stats['last_prediction'] != 'Error':
                    stats['total_predictions'] += 1
                    if stats['last_prediction'] == result:
                        stats['correct_predictions'] += 1
                
                # Reset last prediction since we just evaluated it
                stats['last_prediction'] = None
                history.append(result)

        elif action == 'undo':
            if len(history) > 0:
                history.pop()
                # We can't perfectly undo stats without keeping a deep log, 
                # but we reset last_prediction to avoid false evaluations.
                stats['last_prediction'] = None
        elif action == 'clear':
            history = []
            stats = {"total_predictions": 0, "correct_predictions": 0, "last_prediction": None}
            
        return jsonify({"status": "success", "history": history, "stats": stats})
        
    return jsonify({"history": history, "stats": stats})

@app.route('/api/predict', methods=['GET'])
def get_prediction():
    global history, stats
    if not history:
        return jsonify({
            "prediction": "N/A",
            "confidence": "-",
            "reasoning": "No history available. Please add results first.",
            "opinions": []
        })
        
    # Pass up to last 100 history to AI so it learns, but doesn't crash token limits
    prediction_data = council.get_prediction(history[-100:])
    
    # Store the prediction to evaluate it on the next turn
    stats['last_prediction'] = prediction_data.get('prediction')
    
    return jsonify(prediction_data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
