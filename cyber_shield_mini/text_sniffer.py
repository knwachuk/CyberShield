import json
import re

import torch
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline

sentiment_analyzer = pipeline("sentiment-analysis")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


# Step 1: Load abusive words from file
def load_abusive_words(file_path):
    """
    Loads a list of abusive words from a file.

    Each line in the file should contain a single word. The function reads all lines,
    strips whitespace, converts them to lowercase, and returns the list of words.

    Args:
        file_path (str): The path to the file containing abusive words.

    Returns:
        list[str]: A list of abusive words in lowercase.
    """
    with open(file_path, "r") as file:
        return [word.strip().lower() for word in file.readlines()]
    # patterns=[re.compile(rf'\b{re.escape(word)}\b', re.IGNORECASE) for word in words]
    # return words, patterns


# Step 2: Analyze sentiment of the input text
def analyze_sentiment(text):
    """
    Analyzes the sentiment of the given text using a sentiment analyzer.

    Args:
        text (str): The input text to analyze.

    Returns:
        dict: A dictionary containing:
            - 'sentiment' (str): The predicted sentiment label (e.g., 'POSITIVE', 'NEGATIVE').
            - 'confidence' (float): The confidence score of the prediction, rounded to three decimals.
    """
    result = sentiment_analyzer(text)[0]
    return {"sentiment": result["label"], "confidence": round(result["score"], 3)}


# Step 3: Check text for abusive words
def detect_abuse(text, abusive_words, similarity_threshold=0.6):
    """
    Detects abusive words in a given text using semantic similarity and sentiment analysis.

    Args:
        text (str): The input text to analyze for abusive content.
        abusive_words (list of str): A list of abusive words to compare against.
        similarity_threshold (float, optional): The minimum cosine similarity score to consider a word as abusive. Defaults to 0.6.

    Returns:
        dict: If abusive words are found, returns a dictionary with the key "abusive-words-found" containing a list of detected abusive words and their details.
              Each detected word includes:
                  - word_in_text (str): The word from the input text.
                  - matched_with (str): The abusive word it matched with.
                  - similarity (float): The similarity score.
                  - severity (str): Severity level ("high" or "medium").
                  - text_analyzed (str): The original input text.
                  - sentiment (dict): Sentiment analysis report for the text.
              If no abusive words are found, returns a dictionary with:
                  - abusive-words_found (list): An empty list.
                  - sentiment (dict): Sentiment analysis report for the text.
                  - text_analyze (str): The original input text.

    Note:
        Requires `embedding_model`, `util`, and `torch` to be defined in the global scope.
        Also requires an `analyze_sentiment` function to be available.
    """
    detected = []
    words_in_text = text.lower().split()  # Split input text into words
    sentiment_report = analyze_sentiment(text)
    text_embeddings = embedding_model.encode(words_in_text, convert_to_tensor=True)
    abusive_embeddings = embedding_model.encode(abusive_words, convert_to_tensor=True)

    for i, word_embeeding in enumerate(text_embeddings):
        cosine_scores = util.cos_sim(word_embeeding, abusive_embeddings)[0]
        max_score = torch.max(cosine_scores).item()
        if max_score >= similarity_threshold:
            matched_index = torch.argmax(cosine_scores).item()
            matched_word = abusive_words[matched_index]
            detected.append(
                {
                    "word_in_text": words_in_text[i],
                    "matched_with": matched_word,
                    "similarity": round(max_score, 3),
                    "severity": "high" if max_score > 0.8 else "medium",
                    "text_analyzed": text,
                    "sentiment": sentiment_report,
                }
            )

    # sentiment_report=analyze_sentiment(text)
    if detected:
        return {
            "abusive-words-found": detected,
            #'sentiment':sentiment_report
        }
    else:
        return {
            "abusive-words_found": [],
            "sentiment": sentiment_report,  # this one
            "text_analyze": text,
        }
