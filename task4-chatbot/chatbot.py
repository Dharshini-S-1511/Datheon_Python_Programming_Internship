"""Rule-Based Interactive Terminal Assistant / Chatbot.

A support assistant for the Datheon Python Programming Internship. It:
  - normalizes user input and matches it against regex/keyword rules
  - recognizes several intents in one message (multi-intent matching)
  - keeps conversational state (greeting -> listening -> resolved -> exit)
  - remembers context (user's name, last topic) for follow-up questions
  - falls back gracefully when it does not understand
  - exits cleanly on 'bye', 'exit' or 'quit'

Knowledge comes from two JSON files, so the bot can be edited without
touching the code:
  - sample_faq.json : the provided dataset ("greetings" + "faqs" Q&A pairs);
                      each question is turned into regex rules automatically
  - faq.json        : extra hand-written intents with regex patterns/variants
Run with:  python chatbot.py
"""
import difflib
import json
import re
import textwrap
from pathlib import Path

BOT_NAME = "TechBot"
BASE_DIR = Path(__file__).resolve().parent
FAQ_FILE = BASE_DIR / "faq.json"
SAMPLE_FILE = BASE_DIR / "sample_faq.json"
MAX_INPUT_LENGTH = 300
MAX_INTENTS_PER_REPLY = 3

# Conversation states
LISTENING = "LISTENING"   # waiting for the user's question
RESOLVED = "RESOLVED"     # answered; asked if anything else is needed
EXIT = "EXIT"

EXIT_RE = re.compile(r"\b(bye|exit|quit|goodbye)\b")
YES_RE = re.compile(r"^(yes|yeah|yep|yup|sure|ok|okay|please)\b")
NO_RE = re.compile(
    r"^(no|nope|nah|nothing|not now)\b|\b(that'?s all|thats all|i'?m good|im good|all good)\b")
NAME_RE = re.compile(r"\b(?:my name is|call me)\s+([a-z]+)")
FOLLOWUP_RE = re.compile(r"^(and|what about|how about|also|then)\b")
LOW_PRIORITY = {"greeting", "thanks", "help"}
STOPWORDS = {
    "what", "are", "your", "you", "how", "when", "where", "who", "why", "will",
    "the", "and", "for", "can", "does", "did", "have", "has", "get", "with",
    "from", "this", "that", "our", "its", "any", "there", "would", "could",
    "should", "about", "into", "than", "then", "them", "they", "was", "were",
}

# Used only if faq.json is missing or broken, so the bot never crashes.
FALLBACK_INTENTS = [
    {"name": "hours", "topic": "store hours",
     "patterns": [r"\b(hours?|open|clos(e|ing)|timings?)\b"],
     "response": "We operate Monday through Friday from 9:00 AM to 6:00 PM IST."},
    {"name": "contact", "topic": "contacting support",
     "patterns": [r"\b(contact|support|email)\b"],
     "response": "Please use your Student Workspace on the Datheon website for help."},
]


def say(message):
    """Print a bot message, wrapped to the terminal width."""
    for i, line in enumerate(message.split("\n")):
        prefix = f"{BOT_NAME}: " if i == 0 else "    "
        print(textwrap.fill(prefix + line, width=78, subsequent_indent="    "))


def normalize(text):
    """Lowercase, strip whitespace/punctuation and collapse spaces."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def compile_intent(intent):
    """Pre-compile the regex patterns of an intent for fast matching."""
    compiled = dict(intent)
    compiled["_patterns"] = [re.compile(p) for p in intent["patterns"]]
    compiled["_variants"] = [
        (re.compile(v["pattern"]), v["response"])
        for v in intent.get("variants", [])
    ]
    return compiled


def stem(word):
    """Very small suffix stripper so 'hours' also matches 'hour'."""
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[:-len(suffix)]
    return word


def faq_to_intents(faqs):
    """Turn {"question", "answer"} pairs into regex-based intents."""
    intents = []
    for number, item in enumerate(faqs, 1):
        question, reply = item.get("question"), item.get("answer")
        if not question or not reply:
            continue
        words = []
        for word in normalize(question).split():
            if word in STOPWORDS or len(word) < 3:
                continue
            if stem(word) not in words:
                words.append(stem(word))
        if not words:
            continue
        intents.append({
            "name": f"faq_{number}",
            "topic": question.rstrip("?"),
            "question": question,
            "patterns": [rf"\b{re.escape(w)}\w*" for w in words],
            # short questions match on one keyword, longer ones need two
            "min_score": 1 if len(words) <= 2 else 2,
            "response": reply,
        })
    return intents


def read_json(path):
    """Read a JSON file; return None (with a warning) if it is unusable."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise TypeError("top level must be a JSON object")
        return data
    except FileNotFoundError:
        print(f"[Warning] {path.name} not found, skipping it.")
    except (json.JSONDecodeError, TypeError, OSError) as exc:
        print(f"[Warning] Could not read {path.name} ({exc}), skipping it.")
    return None


def load_faq():
    """Load intents from faq.json and sample_faq.json, then compile them."""
    raw_intents, greetings = [], []
    for path in (FAQ_FILE, SAMPLE_FILE):
        data = read_json(path)
        if not data:
            continue
        raw_intents += data.get("intents", [])
        raw_intents += faq_to_intents(data.get("faqs", []))
        greetings += data.get("greetings", [])

    if not raw_intents:
        print("[Warning] No FAQ data found. Using the built-in mini FAQ.")
        raw_intents = [dict(i) for i in FALLBACK_INTENTS]

    if greetings:  # merge the dataset's greeting words into the greeting rule
        pattern = r"\b(" + "|".join(re.escape(g) for g in greetings) + r")\b"
        for intent in raw_intents:
            if intent.get("name") == "greeting":
                intent["patterns"] = list(intent["patterns"]) + [pattern]
                break
        else:
            raw_intents.append({
                "name": "greeting", "topic": "", "patterns": [pattern],
                "response": "Hello! How can I help you today?", "ask_more": False})

    intents = []
    for raw in raw_intents:
        try:
            intents.append(compile_intent(raw))
        except (re.error, KeyError, TypeError) as exc:
            print(f"[Warning] Skipping bad intent '{raw.get('name', '?')}': {exc}")
    return intents


def match_intents(text, intents):
    """Return [(score, intent)] for every intent whose rules match the text."""
    scored = []
    for intent in intents:
        score = sum(1 for pattern in intent["_patterns"] if pattern.search(text))
        if score and score >= intent.get("min_score", 1):
            scored.append((score, intent))
    scored.sort(key=lambda item: -item[0])  # stable: ties keep file order
    return scored


def answer(intent, text):
    """Pick the most specific response (variant) for the user's wording."""
    for pattern, response in intent["_variants"]:
        if pattern.search(text):
            return response
    return intent["response"]


def topic_menu(intents):
    topics = [i["topic"] for i in intents if i.get("topic")]
    return "\n".join(f"  - {t}" for t in topics)


def closest_question(text, intents):
    """Best-guess FAQ question when confidence is low (None if too far off)."""
    best, best_ratio = None, 0.0
    for intent in intents:
        question = intent.get("question")
        if not question:
            continue
        ratio = difflib.SequenceMatcher(None, text, normalize(question)).ratio()
        if ratio > best_ratio:
            best, best_ratio = question, ratio
    return best if best_ratio >= 0.5 else None


def fallback_reply(text, intents, ctx):
    """Graceful fallback; suggests a question, then shows the topic list."""
    ctx["misses"] += 1
    if ctx["misses"] == 1:
        guess = closest_question(text, intents)
        if guess:
            return (f"I'm not sure I understood. Did you mean: \"{guess}\" "
                    "Ask it again and I'll answer.")
        return ("Sorry, I didn't quite get that. Could you rephrase it? "
                "You can ask me about hours, submitting your project or certificates.")
    ctx["misses"] = 0
    return ("I'm still not sure what you mean. Here is what I can help with:\n"
            + topic_menu(intents)
            + "\nOr type 'bye' to leave.")


def handle_query(text, intents, ctx):
    """Return (reply, ask_if_more_help_needed) for one user message."""
    prefix = ""
    name_match = NAME_RE.search(text)
    if name_match:
        ctx["name"] = name_match.group(1).title()
        prefix = f"Nice to meet you, {ctx['name']}! "

    matches = match_intents(text, intents)

    # Ignore polite filler when a real question is also present.
    if len(matches) > 1:
        real = [m for m in matches if m[1]["name"] not in LOW_PRIORITY]
        matches = real or matches
    matches = matches[:MAX_INTENTS_PER_REPLY]

    if matches:
        ctx["misses"] = 0
        ctx["last_intent"] = matches[0][1]
        ask_more = any(i.get("ask_more", True) for _, i in matches)
        if len(matches) == 1:
            return prefix + answer(matches[0][1], text), ask_more
        lines = [f"{n}) {answer(i, text)}" for n, (_, i) in enumerate(matches, 1)]
        return (prefix + f"I found {len(matches)} questions in your message:\n"
                + "\n".join(lines)), ask_more

    # Follow-up such as "and on weekends?" refers to the previous topic.
    last = ctx["last_intent"]
    if last and FOLLOWUP_RE.match(text):
        for pattern, response in last["_variants"]:
            if pattern.search(text):
                ctx["misses"] = 0
                return prefix + response, True

    if prefix:
        return prefix + "What can I help you with?", False
    return fallback_reply(text, intents, ctx), False


def farewell(ctx):
    who = f", {ctx['name']}" if ctx["name"] else ""
    return f"Thank you for chatting with Datheon support{who}! Goodbye and good luck with your project."


def chat():
    intents = load_faq()
    ctx = {"name": None, "last_intent": None, "misses": 0}

    print("=" * 60)
    print(f"{'Datheon Internship - Support Assistant':^60}")
    print(f"{'(type bye, exit or quit to leave)':^60}")
    print("=" * 60)
    say("Hello! Welcome to the Datheon Internship Support Assistant. How can I help you today?")
    state = LISTENING

    while state != EXIT:
        try:
            raw = input("\nYou: ")
        except (EOFError, KeyboardInterrupt):
            print()
            say(farewell(ctx))
            break

        text = normalize(raw)
        if not text:
            say("I didn't catch anything. Please type your question.")
            continue
        if len(raw) > MAX_INPUT_LENGTH:
            say("That message is a bit long. Could you shorten it?")
            continue
        if EXIT_RE.search(text):
            say(farewell(ctx))
            state = EXIT
            continue

        if state == RESOLVED:
            if NO_RE.search(text):
                say(farewell(ctx))
                state = EXIT
                continue
            if YES_RE.match(text) and len(text.split()) <= 2:
                say("Great! What would you like to know?")
                state = LISTENING
                continue
            state = LISTENING  # treat as a new question

        reply, ask_more = handle_query(text, intents, ctx)
        say(reply)
        if ask_more:
            say("Is there anything else I can help you with?")
            state = RESOLVED


if __name__ == "__main__":
    chat()
