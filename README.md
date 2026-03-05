# TaskReward

A task-completion reward app powered by Claude AI.

## Setup

### 1. Backend (Python / Flask)

```bash
cd backend
pip install -r requirements.txt
export GOOGLE_GEMINI_KEY=your_key_here
python app.py
```

The server runs on **http://localhost:5000**.

---

## Adding New Reward Types

Open `backend/app.py` and find the `REWARD_TYPES` dictionary:

```python
REWARD_TYPES = {
    "image": {"weight": 2, "description": "..."},
    "fact":  {"weight": 1, "description": "..."},
    # Add yours here:
    "quote": {"weight": 1, "description": "An inspiring quote related to the achievement"},
}
```

Then add a resolver branch in `resolve_rewards()`:

```python
if rtype == "quote":
    return {
        "type": "quote",
        "title": raw.get("title", "Words of Wisdom"),
        "content": raw.get("content", ""),
        "author": raw.get("author", ""),
    }
```

Finally, render it in the frontend's `renderCard()` function in `frontend/index.html`:

```js
if (reward.type === 'quote') {
  return `<div>..."${reward.content}" — ${reward.author}</div>`;
}
```

No other changes needed — the LLM prompt is built automatically from `REWARD_TYPES`.
