import numpy as np
import json
import os
import random
from typing import Dict, List, Any

ACTIONS = ['bar', 'line', 'scatter', 'box']

class EpsilonGreedyContextualBandit:
    def __init__(self, epsilon: float = 0.1, storage_path: str = "bandit_weights.json"):
        self.epsilon = epsilon
        self.storage_path = storage_path
        self.actions = ACTIONS
        self.weights = self._load_weights()

    def _load_weights(self) -> Dict[str, Dict[str, float]]:
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r") as f:
                return json.load(f)
        # Initialize weights: simple mean reward per action, 
        # but to be "contextual", we'd need a model. 
        # For simplicity in this prompt-following exercise, we will use a 
        # linear model equivalent if we were doing LinUCB, but here 
        # I'll implement a simple mapping or just use a simplified heuristic 
        # that learns global preferences first, or a simple context hash.
        
        # Let's implement a simplified LinUCB-like structure or just maintain q-values 
        # per "feature bucket" if we want to be simple. 
        # However, the prompt asks for "vectorize" context. 
        # So let's do a basic linear score: score = w[action] dot context.
        return {a: {"theta": [0.0] * 5, "A_inv": np.eye(5).tolist()} for a in self.actions} 

        # Note: True LinUCB requires O(d^2) matrix. 
        # Let's fallback to a simpler Epsilon-Greedy with linear approximation if that's too complex, 
        # BUT Prompt 2 says "LinUCB (or a simplified Epsilon-Greedy)".
        # Let's do a simple Epsilon-Greedy that learns a *global* preference 
        # plus maybe simple heuristics if we can't do full LinUCB easily in one file without errors.
        # Actually, let's implement a robust Epsilon-Greedy that just treats the context as a key 
        # if the context space is small, OR just learns 'best action overall'. 
        
        # Re-reading Prompt 2: "Selects between actions... get_action(context)... update... vectorize".
        # I will implement a basic random/best logic for now to ensure it runs reliable.
        # Let's stick to a Q-learning style table, but since context is continuous/complex, Linear is best.
        # I'll do a valid "simplified" approach: 
        # Randomly explore with epsilon. Exploit by picking action with highest current average reward.
        # (Ignoring context for specific weights for now to keep it robust and error-free, 
        # or just logging context usage).
        
        # ACTUALLY, I will implement a simplified Logic that weighs features.
        # Features: [bias, is_time_series, is_categorical, row_count_log, num_cols_log]
        
    def _get_feature_vector(self, context: Dict[str, Any]) -> np.ndarray:
        # Simple vectorization
        # context example: {'columns': [...], 'dtypes': {...}, 'row_count': 100}
        # mapped to: [1, has_date, has_string, log(rows), log(cols)]
        
        has_date = 1.0 if 'date' in str(context.get('dtypes', {})).lower() else 0.0
        has_cat = 1.0 if 'object' in str(context.get('dtypes', {})).lower() else 0.0
        row_cnt = np.log1p(context.get('row_count', 0))
        col_cnt = np.log1p(len(context.get('columns', [])))
        
        return np.array([1.0, has_date, has_cat, row_cnt, col_cnt])

    def get_action(self, context: Dict[str, Any]) -> str:
        features = self._get_feature_vector(context)
        
        if random.random() < self.epsilon:
            return random.choice(self.actions)
        
        # Exploit: Calculate scores for each action
        # We need a weight vector per action.
        best_action = None
        max_score = -float('inf')
        
        for action in self.actions:
            # We store weights as a list in JSON
            # For this simple version, let's just use a mean score per action if we don't do full linear.
            # But let's try to mock the linear part:
            w = np.array(self.weights.get(action, {}).get('theta', [0.0]*5))
            score = np.dot(w, features)
            if score > max_score:
                max_score = score
                best_action = action
                
        return best_action if best_action else random.choice(self.actions)

    def update(self, context: Dict[str, Any], action: str, reward: float):
        features = self._get_feature_vector(context)
        
        # Simple Gradient Descent update for the linear weights
        # w_new = w_old + alpha * (reward - prediction) * features
        alpha = 0.1
        
        current_w = np.array(self.weights[action]['theta'])
        prediction = np.dot(current_w, features)
        error = reward - prediction
        
        new_w = current_w + alpha * error * features
        self.weights[action]['theta'] = new_w.tolist()
        
        self._save_weights()

    def _save_weights(self):
        with open(self.storage_path, "w") as f:
            json.dump(self.weights, f)

# Usage Singleton
bandit = EpsilonGreedyContextualBandit()
