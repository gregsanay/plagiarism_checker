# app.py
from flask import Flask, request, render_template
import requests
from bs4 import BeautifulSoup
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    pipeline = None
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    TfidfVectorizer = None
    cosine_similarity = None
from rapidfuzz import fuzz
import os
import random
import hashlib

app = Flask(__name__)

paraphraser = None
paraphraser_unavailable = False
PARAPHRASER_MODEL = "Vamsi/T5_Paraphrase_Paws"
PARAPHRASE_REPLACEMENTS = {
    "important": "significant",
    "show": "demonstrate",
    "use": "employ",
    "help": "assist",
    "start": "begin",
    "end": "finish",
    "buy": "purchase",
    "big": "large",
    "small": "minor",
    "good": "strong",
    "bad": "weak",
    "because": "since",
    "also": "as well",
    "many": "numerous",
    "much": "a lot of",
}


def get_paraphraser():
    global paraphraser, paraphraser_unavailable
    if not TRANSFORMERS_AVAILABLE:
        return None
    if paraphraser_unavailable:
        return None
    if paraphraser is None:
        try:
            # Allow optional remote model download by setting ALLOW_MODEL_DOWNLOAD=true
            allow_download = os.getenv("ALLOW_MODEL_DOWNLOAD", "false").lower() == "true"
            paraphraser = pipeline(
                "text2text-generation",
                model=PARAPHRASER_MODEL,
                local_files_only=not allow_download,
            )
        except Exception:
            paraphraser_unavailable = True
            return None
    return paraphraser


def offline_paraphrase(text, num_return_sequences=3):
    # Deterministic pseudo-randomness based on text so results are stable
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16) & 0xFFFFFFFF
    rnd = random.Random(seed)

    tokens = text.split()

    def apply_replacements(select_indices=None):
        out = []
        for i, word in enumerate(tokens):
            stripped = word.strip(".,!?;:")
            key = stripped.lower()
            replacement = PARAPHRASE_REPLACEMENTS.get(key)
            if replacement and (select_indices is None or i in select_indices):
                new_word = replacement
                if stripped and stripped[0].isupper():
                    new_word = replacement.capitalize()
                new_word = word.replace(stripped, new_word, 1)
                out.append(new_word)
            else:
                out.append(word)
        s = " ".join(out)
        s = s.strip()
        if s and s[-1] not in ".!?":
            s += "."
        return s

    # find indices where a replacement exists
    repl_indices = [i for i, w in enumerate(tokens) if w.strip(".,!?;:").lower() in PARAPHRASE_REPLACEMENTS]

    variants = []

    # Variant 1: apply all replacements
    if repl_indices:
        variants.append(apply_replacements(select_indices=set(repl_indices)))
    else:
        variants.append(text if text.endswith(('.', '!', '?')) else text + '.')

    # Additional variants: selective replacements for variety
    for v in range(1, num_return_sequences):
        if not repl_indices:
            # no replacements possible; just produce the original text once
            variants.append(variants[0])
            continue
        # choose a deterministic subset size (at least one)
        subset_size = max(1, len(repl_indices) // (v + 1))
        chosen = set(rnd.sample(repl_indices, subset_size))
        candidate = apply_replacements(select_indices=chosen)
        variants.append(candidate)

    # Deduplicate while preserving order
    seen = set()
    out = []
    for s in variants:
        if s not in seen:
            seen.add(s)
            out.append(s)

    return out



def fetch_article_text(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; plagiarism-checker/1.0)"}
        res = requests.get(url, timeout=10, headers=headers)
        if res.status_code != 200:
            return "Error: Unable to fetch URL."
        soup = BeautifulSoup(res.text, "html.parser")
        # Try several heuristics to extract the main article text
        # 1) <article>
        article = soup.find('article')
        if article:
            text = " ".join(p.get_text() for p in article.find_all(['p', 'div']))
            if text.strip():
                return text.strip()

        # 2) <main>
        main = soup.find('main')
        if main:
            text = " ".join(p.get_text() for p in main.find_all('p'))
            if text.strip():
                return text.strip()

        # 3) all paragraphs
        paragraphs = soup.find_all('p')
        if paragraphs:
            article_text = " ".join(p.get_text() for p in paragraphs)
            if article_text.strip():
                return article_text.strip()

        # 4) fallback: largest <div>
        divs = soup.find_all('div')
        if divs:
            best = max(divs, key=lambda d: len(d.get_text()), default=None)
            if best and best.get_text().strip():
                return best.get_text().strip()

        # 5) meta description
        meta = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', property='og:description')
        if meta and meta.get('content'):
            return meta['content'].strip()

        return "Error: No article text found on page."
    except Exception as e:
        return f"Error: {str(e)}"

def compare_texts(text1, text2):
    if not text1.strip() or not text2.strip():
        return 0, 0

    # Fuzzy similarity (token sort ratio)
    fuzzy_score = fuzz.token_sort_ratio(text1, text2)
    
    # Cosine similarity on TF-IDF vectors (if sklearn available)
    cosine_sim = 0
    if SKLEARN_AVAILABLE:
        try:
            vectorizer = TfidfVectorizer().fit_transform([text1, text2])
            vectors = vectorizer.toarray()
            cosine_sim = cosine_similarity([vectors[0]], [vectors[1]])[0][0]
        except Exception:
            cosine_sim = fuzzy_score / 100.0  # fallback: use normalized fuzzy score
    else:
        cosine_sim = fuzzy_score / 100.0  # fallback: use normalized fuzzy score
    
    return fuzzy_score, cosine_sim

def paraphrase_text(text, num_return_sequences=3):
    input_text = f"paraphrase: {text} </s>"
    model = get_paraphraser()
    if model is not None:
        try:
            results = model(
                input_text,
                max_length=512,
                num_return_sequences=num_return_sequences,
                do_sample=True,
                top_k=50,
                top_p=0.95,
                temperature=1.5,
                early_stopping=True,
            )
            # Return list of paraphrased texts
            return [res["generated_text"] for res in results]
        except Exception:
            pass

    return offline_paraphrase(text, num_return_sequences=num_return_sequences)



@app.route("/", methods=["GET", "POST"])
def home():
    result = ""
    url = ""
    student_text = ""
    if request.method == "POST":
        url = request.form.get("url", "")
        student_text = request.form.get("student_text", "")
        action = request.form.get("action")

        if action == "compare":
            article_text = fetch_article_text(url)
            if article_text.startswith("Error:"):
                result = article_text
            else:
                fuzzy, cosine = compare_texts(article_text, student_text)
                result = f"""
                🔍 <strong>Fuzzy Similarity:</strong> {fuzzy:.2f}%<br>
                🧠 <strong>Cosine Similarity:</strong> {cosine:.2f}
                """
        elif action == "paraphrase":
            if not student_text.strip():
                result = "Please enter text to paraphrase."
            else:
                paraphrased = paraphrase_text(student_text)
                result = "<strong>Paraphrased Text:</strong><br>" + "<br><br>".join(paraphrased)

    return render_template("index.html", result=result, url=url, student_text=student_text)

if __name__ == "__main__":
    app.run(debug=True)
