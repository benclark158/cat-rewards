import os
import json
import requests
import random

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from google import genai

app = Flask(__name__)
CORS(app)

client = genai.Client(api_key=os.getenv('GOOGLE_GEMINI_KEY'))


# ─────────────────────────────────────────────
#  REWARD REGISTRY
#  To add a new reward type in future:
#    1. Add an entry here with a weight & description
#    2. Add a resolver in `resolve_rewards()`
# ─────────────────────────────────────────────
REWARD_TYPES = {
    "gif": {
        "weight": 20,
        "description": "A funny or adorable gif of the a cat - the most valuable reward",
    },
    "image": {
        "weight": 10,
        "description": "A random image of a cat",
    },
    "fact": {
        "weight": 1,
        "description": "A fact about cats - easy achievable fact",
    },
}


def build_reward_schema_description():
    lines = []
    for name, meta in REWARD_TYPES.items():
        lines.append(f'  - "{name}" (weight {meta["weight"]}): {meta["description"]}')
    return "\n".join(lines)


def resolve_rewards(raw: list[dict]) -> dict:
    """Turn the LLM's raw reward object into a fully hydrated reward."""
    outputs = []

    num_images = len([ reward for reward in raw if reward.get('type') == 'image'])
    num_facts = len([ reward for reward in raw if reward.get('type') == 'fact'])
    gifs = [ reward for reward in raw if reward.get('type') == 'gif' ]

    img_response = requests.get(f'https://api.thecatapi.com/v1/images/search?limit={num_images}')
    fact_response = requests.get(f'https://catfact.ninja/facts?limit={num_facts}')

    for img in img_response.json():
        outputs.append({
            "type": "image",
            "title": '',
            "description": '',
            "url": img.get('url'),
            "theme": '',
        })

    cats = ['🐈‍⬛', '🐈', '😻', '🐾']

    for fact in fact_response.json().get('data', []):
        outputs.append({
            "type": "fact",
            "title": "Did you know?",
            "content": fact.get("fact", ""),
            "emoji": random.choice(cats),
        })

    for gif in gifs:
        random_i = random.randint(1, 1000)
        outputs.append({
            "type": "gif",
            "title": '',
            "description": '',
            "url": f'https://cataas.com/cat/gif?r={random_i}',
            "theme": '',
        })

    random.shuffle(outputs)

    return outputs


@app.route("/api/evaluate", methods=["POST"])
def evaluate():
    data = request.get_json()
    task = (data or {}).get("task", "").strip()

    if not task:
        return jsonify({"error": "No task provided"}), 400

    reward_schema = build_reward_schema_description()

    prompt = f"""You are a reward system evaluator. A user has just completed a task and you must decide what rewards they deserve.

Available reward types (with relative weights – higher weight = more valuable):
{reward_schema}

The user's completed task:
\"\"\"{task}\"\"\"

Rules:
- Grant between 1 and 10 rewards total, based on how impressive/effortful the task was.
- More impressive tasks deserve more rewards and more high-weight reward types.
- You may give any combination of reward types (repeats allowed).
- You need to generate a score that is between 0 and 10
- A score of zero should get 1 fact
- A score of 10 should get 5x gifs, 3x images and 2x facts
- All rewards should use these two examples and the upper and lower bound.
- A score of 5 could have 5x gifs or 5x images or a mix, or 10x facts. Gauge the task based on the context provided by the person.
- Do not over reward tasks.

Respond ONLY with a valid JSON object in this exact format (no markdown, no explanation):
{{
  "rewards": [
    {{
      "type": "image",
    }},
    {{
      "type": "fact",
    }}
  ],
  "message": "A short, warm, personalised congratulatory message (1-2 sentences) for completing this task.",
  "score": 7.9,
}}"""

    response = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=prompt,
    )

    raw_text = response.text.strip()

    # Strip accidental markdown fences
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
    raw_text = raw_text.strip()

    parsed = json.loads(raw_text)
    hydrated_rewards = resolve_rewards(parsed.get("rewards", []))

    return jsonify(
        {
            "rewards": hydrated_rewards,
            "message": parsed.get("message", "Great work!"),
            "reward_types": {
                name: meta["weight"] for name, meta in REWARD_TYPES.items()
            },
        }
    )

@app.route("/")
def index():
    frontend_dir = os.path.dirname(__file__)
    return send_from_directory(frontend_dir, "index.html")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
