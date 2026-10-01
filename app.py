import os
from dotenv import load_dotenv

load_dotenv()

print("AI Chatbot - Saman Naz - HISAB Internship Day 1")
print("Type 'exit' to quit\n")

history = []

while True:
    try:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            print("Bot: Allah Hafiz! Task completed.")
            break
        if not user_input.strip():
            continue
            
        print("Bot is thinking...")
        reply = f"Received: '{user_input}'. This is a demo AI chatbot. Full AI API will be connected soon."
        print(f"Bot: {reply}\n")
        history.append({"you": user_input, "bot": reply})
    except Exception as e:
        print(f"Error: {e}")
