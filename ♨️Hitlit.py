import streamlit as st
import requests
import pandas as pd
from langchain_core.messages import AIMessage, HumanMessage
from dotenv import load_dotenv
import re
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# FastAPI endpoint
API_URL = "http://localhost:8000/generate/"

# Initialize session state variables
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "search_history" not in st.session_state:
    st.session_state.search_history = {}

# Set up the Streamlit app
st.set_page_config(page_title="HitLit", page_icon="🤖", initial_sidebar_state="expanded")

# Add custom CSS to style the title
st.markdown("""
    <style>
    .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        #stDecoration {display:none;}
    .header-container {
        display: flex;
        justify-content: flex-start;
        align-items: center;
        padding: 0;
        margin: 0;
    }
    .title {
        font-size: 35px;
        font-weight: bold;
        margin: 0;
        padding: 0;
        text-align: center;
        font-family: 'Courier New', Courier, monospace;
        color: #FF5733;
    }
    </style>
    """, unsafe_allow_html=True)

# Add the custom title
st.markdown('<div class="header-container"><span class="title">♨️ HITLIT</span></div>', unsafe_allow_html=True)

# Load the CSV file
@st.cache_data
def load_csv(file_path):
    return pd.read_csv(file_path)

# Replace with your CSV file path
csv_file_path = r"\\kor2fs03\V-V--Testing$\03_Validation_Software\LLBP\VALSW_LL_BP_SPL_V1.1.csv"
csv_data = load_csv(csv_file_path)

def clean_and_split_query(query):
    filler_words = {'um', 'like', 'you', 'know', 'so', 'well', 'actually', 'basically', 'just', 'really'}
    stop_words = {'is', 'are', 'was', 'were', 'what', 'who', 'how', 'where', 'when', 'why',
                  'i', 'me', 'you', 'his', 'her', 'ok', 'bye', 'i am sorry', 'it is what it is', 'it','is','on','over','under','inside','an','a','the', 'does','con',
                  'get', 'got', 'have', 'had', 'has', 'should', 'not', 'use', 'mobile','team','Team','Verdict','an','no','not','but','T','15','with'}
    cleaned_query = re.sub(r'[^\w\s]', '', query)
    words = cleaned_query.lower().split()
    filtered_words = [word for word in words if word not in filler_words and word not in stop_words]
    return filtered_words

def query_csv(query):
    search_column = 'ASIC/Module'
    answer_columns = ['Problem', 'Solution', 'Root cause', 'Preventive action', 'LL/BP', 'Reference document folder', 'Year', 'Project', 'Author']
    keywords = clean_and_split_query(query)
    csv_data['match_score'] = csv_data[search_column].apply(lambda x: sum(keyword in str(x).lower() for keyword in keywords))
    best_match_index = csv_data['match_score'].idxmax()
    best_match = csv_data.loc[best_match_index]
    row_answers = []
    if csv_data['match_score'].max() > 0:
        for answer_col in answer_columns:
            if pd.notna(best_match[answer_col]):
                if answer_col == 'Reference document folder':
                    if re.match(r'http[s]?://', str(best_match[answer_col])):
                        row_answers.append(f"**{answer_col}:** [Open Document]({best_match[answer_col]})")
                    else:
                        row_answers.append(f"**{answer_col}:**\n{best_match[answer_col]}")
                else:
                    row_answers.append(f"**{answer_col}:**\n{best_match[answer_col]}")
        return "\n\n".join(row_answers)
    else:
        return "Sorry, I don't understand."

def detect_greeting(query):
    greetings = {
        "hi": "Hello! How can I assist you today?",
        "hello": "Hello! Have a great day.",
        "hey": "Hello! How can I assist you today?",
        "good morning": "Good morning! Have a nice day.",
        "good afternoon": "Good afternoon! Have a great day.",
        "good evening": "Good evening! Go and have snacks.",
        "good night": "Good night! Sleep well."
    }
    for key, value in greetings.items():
        if key in query.lower():
            return value
    return None

def detect_inappropriate_language(query):
    inappropriate_phrases = ["brutal", "badword", "i hate you", "fuck you", "i love you", "i want to marry you"]
    return any(phrase in query.lower() for phrase in inappropriate_phrases)

def get_response(query):
    query_lower = query.lower()
    
    if query_lower in ["yes","Yes","Yes you too","seri", "okay", "ok"]:
        if query_lower == "yes":
            return "Seri! Okay"
        if query_lower in ["okay", "ok"]:
            return "ok"

    if "sorry" in query_lower:
        return "It's okay! Don't cry. Go and Work!"
    if "thank you" in query_lower:
        return "Aww! So sweet of you! You're Welcome"

    # Adjust the search condition to be more flexible
    keywords_to_search = ["cfi", "flashing", "error", "issue", "problem"]
    if any(keyword in query_lower for keyword in keywords_to_search):
        return query_csv(query)

    greeting_response = detect_greeting(query)
    if greeting_response:
        return greeting_response

    if detect_inappropriate_language(query):
        return "I didn't get you..."

    try:
        response = requests.post(API_URL, json={"text": query})
        response.raise_for_status()
        response_json = response.json()
        return response_json.get('response', "Sorry, I couldn't process the request.")
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404:
            return query_csv(query)
        return f"HTTP error occurred: {http_err}"
    except requests.exceptions.RequestException as req_err:
        return f"Request error occurred: {req_err}"
    except json.JSONDecodeError as json_err:
        return f"JSON decode error occurred: {json_err}"


# Sidebar
st.sidebar.title("Search History")
# sidebar_option = st.sidebar.radio("Choose an option", ["Home", "Clear Chat", "Settings"])

# if sidebar_option == "Clear Chat":
#     if st.sidebar.button("Clear Chat History"):
#         st.session_state.chat_history = []
#         st.experimental_rerun()

# Display conversation
for message in st.session_state.chat_history:
    if isinstance(message, HumanMessage):
        with st.chat_message("Human"):
            st.markdown(message.content)
    else:
        with st.chat_message("AI"):
            st.markdown(message.content)

# User input
user_query = st.chat_input("Your message")
if user_query:
    st.session_state.chat_history.append(HumanMessage(user_query))

    with st.chat_message("Human"):
        st.markdown(user_query)

    with st.chat_message("AI"):
        ai_response = get_response(user_query)
        st.markdown(ai_response)

    st.session_state.chat_history.append(AIMessage(ai_response))
