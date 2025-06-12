import json
import torch
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob

bert_analyzer=pipeline("sentiment-analysis")
roberta_analyzer=pipeline('sentiment-analysis',model="cardiffnlp/twitter-roberta-base-sentiment")

vader_analyzer=SentimentIntensityAnalyzer()
# HateBERT (HateXplain)
hatebert_model_name = "Hate-speech-CNERG/bert-base-uncased-hatexplain"
hatebert_tokenizer = AutoTokenizer.from_pretrained(hatebert_model_name)
hatebert_model = AutoModelForSequenceClassification.from_pretrained(hatebert_model_name)
hatebert_analyzer = pipeline("text-classification", model=hatebert_model, tokenizer=hatebert_tokenizer)

# Step 1: Load abusive words from file
def load_abusive_words(file_path):
    with open(file_path, 'r') as file:
        return [word.strip().lower() for word in file.readlines()]
    
#Step2: Analyze sentiment of the input text
def analyze_sentiment(text):
        bert_result=bert_analyzer(text)[0]
        vader_result=vader_analyzer.polarity_scores(text)
        roberta_result = roberta_analyzer(text)[0]
        hatebert_result = hatebert_analyzer(text)[0]
        textblob_result = TextBlob(text).sentiment

        return{
            "bert":{
            "sentiment": bert_result['label'],
            "confidence": round(bert_result['score'], 3)
            },
            "vader":{
                "sentiment": "positive" if vader_result['compound'] > 0 else 
                        "negative" if vader_result['compound'] < 0 else 
                        "neutral",
            "compound_score": round(vader_result['compound'], 3),
            "positive": round(vader_result['pos'], 3),
            "negative": round(vader_result['neg'], 3),
            "neutral": round(vader_result['neu'], 3)
            },
           "roberta": {
            "sentiment": "positive" if roberta_result['label']=="LABEL_2" else
                        "negative" if roberta_result['label']=='LABEL_0' else
                        "neutral",
            "confidence": round(roberta_result['score'], 3)
        },
        "hatebert": {
            "label": hatebert_result['label'],
            "confidence": round(hatebert_result['score'], 3)
        },
        "textblob": {
            "polarity": round(textblob_result.polarity, 3),
            "subjectivity": round(textblob_result.subjectivity, 3),
            "sentiment": "positive" if textblob_result.polarity > 0 else
                         "negative" if textblob_result.polarity < 0 else
                         "neutral" 
        }}

# Step 3: Check text for abusive words
def detect_abuse(text, abusive_words):
    detected = []
    words_in_text = text.lower().split()  # Split input text into words
    sentiment_report=analyze_sentiment(text)
    for word in abusive_words:
        if word in words_in_text:
            detected.append(
                {"word": word,
                "severity": "high",
                # "text_analyzed": text,
                # "sentiment":sentiment_report
                } 
               
                  
            )
            # })
    #sentiment_report=analyze_sentiment(text)
    if detected:
        return{
            'abusive-words-found':detected,
            #'sentiment':sentiment_report
             "text_analyzed": text,
            "sentiment":sentiment_report
        }
    else:
        return{
            "abusive-words_found":[],
            'sentiment':sentiment_report, #this one 
            "text_analyze":text
        }
    # return {
    #     "abusive_words_found": detected,
    #     #"text_analyzed": text,
        
   #sentiment_report=analyze_sentiment(text)     
    

# Step 4: Main function (runs when script is executed)
# if __name__ == "__main__":
#     # Load abusive words
#     abusive_words = load_abusive_words("abusive_words.txt")
    
#     # Ask user for input
#     user_text = input("Enter text to analyze: ")
    
#     # Detect abusive words
#     report = detect_abuse(user_text, abusive_words)
    
#     # Save report to JSON
#     with open("abuse_report.json", "w") as f:
#         json.dump(report, f, indent=4)  # `indent=4` makes JSON readable
    
#     print("Analysis complete! Report saved to 'abuse_report.json'.")
#     print("\nComaprison Results:")
#     print(f"BERT:{report:['sentiment_anlaysis']['bert']}")
#     print(f"VADER:{report:['sentiment_analysos']['vader']}")
    
