import json
import torch 
from text_sniffer import load_abusive_words, detect_abuse

if __name__ == "__main__":
    # Load abusive words
    abusive_words = load_abusive_words("abusive_words.txt")
    
    # Ask user for input
   #user_text = input("Enter text to analyze: ")
    file_path="user_entry.json"
    
    #Open and read the file
    try:
       with open(file_path,'r')as file:
           content_object = json.load(file)
    except FileNotFoundError:
        print('File not found. Please check the path and try again.')


    report_dict={}
    for user_entry in content_object:
        user_text=content_object[user_entry]["TEXT"]
        report = detect_abuse(user_text, abusive_words)
        report_dict[user_entry]=report
    
    with open("abuse_report.json", "w") as f:
        json.dump(report_dict, f, indent=4)  
    
    print("Analysis complete! Report saved to 'abuse_report.json'.")
    #print("\nComaprison Results:")
    #print(report)
    