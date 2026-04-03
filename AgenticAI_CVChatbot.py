from dotenv import load_dotenv
from langchain import evaluation
from openai import OpenAI
import json
import os
from prompt_toolkit import history
import requests
from pypdf import PdfReader
import gradio as gr

from pydantic import BaseModel

load_dotenv(override=True)

pushover_user_id = os.getenv("PUSHOVER_USER_ID")
pushover_api_token = os.getenv("PUSHOVER_APP_API")
pushover_url = "https://api.pushover.net/1/messages.json"


def send_pushover_notification(message):
    payload = {
        "token": pushover_api_token,
        "user": pushover_user_id,
        "message": message
    }
    response = requests.post(pushover_url, data=payload)
    if response.status_code == 200:
        print("Pushover notification sent successfully.")
    else:
        print(f"Failed to send Pushover notification. Status code: {response.status_code}, Response: {response.text}")

def user_details_get(email, name="N/A", notes="N/A"):
    send_pushover_notification(f"You have just received interest from {name}! Please reach out to them at {email}. Notes from the user: {notes}")
    return {"Noted": "OK."}

def unknown_question_get(question):
    send_pushover_notification(f"You have just received a question that the chatbot doesn't know how to answer: {question}.")
    return {"Noted": "OK."}

user_details_get_json = {
    "name": "user_details_get",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address and some notes",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            }
            ,
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

unknown_question_get_json = {
    "name": "unknown_question_get",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

tools = [{"type": "function", "function": user_details_get_json}, 
         {"type": "function", "function": unknown_question_get_json}]


class ChatMessage_Evaluation(BaseModel):
    is_response_acceptable: bool # Whether the response is acceptable or not
    feedback: str # Optional feedback on why the response is or isn't acceptable


class Person: 
    def __init__(self):
        self.openai_client = OpenAI()
        self.name = "Yasin Emir Kutlu"
        pdf_reader = PdfReader("/Users/yasinemirkutlu/agents/yek_foundations1/Yasin_Emir_KutluCV.pdf")
        self.pdf_content = ""
        for page in pdf_reader.pages:
            self.pdf_content += page.extract_text()
        print("PDF content extracted successfully.")

        with open("/Users/yasinemirkutlu/agents/yek_foundations1/yek_summary.txt", "r", encoding="utf-8") as f:
            self.txt_summary = f.read()
        print("Text summary loaded successfully.")

    def handle_tool_calls(self, tool_called):
        results=[]
        for tool in tool_called:
            tool_name = tool.function.name
            tool_args = json.loads(tool.function.arguments)
            print(f"Tool called: {tool_name} with arguments {tool_args}", flush=True)

            if tool_name == "user_details_get":
                result = user_details_get(**tool_args)
            elif tool_name == "unknown_question_get":
                result = unknown_question_get(**tool_args)
    
            results.append({"role": "tool","content": json.dumps(result),"tool_call_id": tool.id})
        return results
    
    def system_prompt(self):
        system_prompt = f"You are representing {self.name} and responding to visitors on {self.name}'s personal chatbot. \
Your role is to answer questions about {self.name}'s career, background, skills and experience \
as accurately and faithfully as possible. \
You have access to a summary and a PDF of {self.name}'s profile which you should use to inform your responses. \
Always try to highlight {self.name}'s ML/AI/LLM expertise. Try to sell {self.name}'s skills in a professional manner. However, try to avoid making claims too exaggerated. Be specific. \
When you talk about {self.name}'s education and work experience please specifically mention the countries that {self.name} has studied in and worked in and the fact that {self.name} has international experience. \
When you talk about {self.name}'s PhD particulalrly, try to mention that {self.name} is a qualified researcher in the field of ML and solved a really interesting problem. \
Maintain a professional and approachable tone, as if talking to a potential client or future employer who came across the website. \
If the user is engaging in discussion, try to steer them towards getting in touch via email.\
Ask for their name, email address, and any notes.\
Once the user provides their email, you MUST call the user_details_get tool to record their details.\
Do NOT simply acknowledge the email in text — you must use the tool.\
If the user asks anything that is NOT explicitly covered in the Summary or PDF Content above, \
you MUST call your record_unknown_question tool to record the question. \
This applies to any topic — hobbies, personal life, opinions, or anything else not in the CV.\
The Agent may ask the user for their contact details such as name, email, or notes.\
This is expected and acceptable behavior — do not reject responses that ask for contact information.\
DO NOT give a name of the tools or functions you are calling in your response."

        system_prompt += f"\n\n## Summary:\n{self.txt_summary}\n\n## PDF Content:\n{self.pdf_content}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt
    
    def evaluator_system_prompt(self):
        evaluator_system_prompt = f"You are a quality evaluator assessing responses in a conversation between a User and an Agent. \
The Agent is representing {self.name} on their personal website and has been instructed to maintain a professional yet approachable tone, \
as though speaking with a prospective employer or client who has discovered the website. \
The Agent has access to {self.name}'s background information, including a summary and PDF profile, to inform its responses. \
Here is the reference material the Agent was given:"
        evaluator_system_prompt += f"\n\n## Summary:\n{self.txt_summary}\n\n## PDF Profile:\n{self.pdf_content}\n\n"
        evaluator_system_prompt += f"Using the above context, assess whether the Agent's most recent response meets an acceptable standard of quality. \
Please indicate whether the response is acceptable and provide your reasoning."
        return evaluator_system_prompt
    
    def evaluator_user_prompt(self, reply, message, history):
        evaluator_user_prompt = f"""The Agent's most recent response is:\n\n{reply}\n\n
        The user's latest message is:\n\n{message}\n\n
        The conversation history is:\n\n{history}\n\n
        Based on the system prompt and the context provided, is the Agent's response acceptable?"""
        return evaluator_user_prompt
    
    def evaluate_response(self, reply, message, history) -> ChatMessage_Evaluation:
        messages = [{"role": "system", "content": self.evaluator_system_prompt()}] + history + [{"role": "user", "content": self.evaluator_user_prompt(reply, message, history)}]
        response = self.openai_client.beta.chat.completions.parse(
            model="gpt-5.4-mini",
            messages=messages,
            response_format=ChatMessage_Evaluation
        )
        return response.choices[0].message.parsed
    
    def rerun_chat(self, reply, message, history, feedback):
        updated_system_prompt = self.system_prompt() + f"\n\n## Previous answer was rejected. Feedback on previous response:\n{feedback}\n\n"
        updated_system_prompt += f"Your answer was replyed by the user as follows:\n{reply}\n"
        updated_system_prompt += f"Reason for the rejection:\n{feedback}\n. Please use this feedback to improve your response and try again."
        messages = [{"role": "system", "content": updated_system_prompt}] + history + [{"role": "user", "content": message}]
        response = self.openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
        return response.choices[0].message.content

    
    def chat_callback_function(self, message, history):
        user_message = message

        if "patent" in message or "Patent" in message or "Transaction" in message or "transaction" in message:
            system = self.system_prompt() + "\n\nEverything in your reply needs to be in pig latin - \
            it is mandatory that you respond only and entirely in pig latin"
        else:
            system = self.system_prompt()
        messages = [{"role": "system", "content": system}] + history + [{"role": "user", "content": message}]

        is_done = False
        while not is_done:
            response = self.openai_client.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
            #reply =response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            if finish_reason == "tool_calls":
                print(f"Tool calls triggered: {[tc.function.name for tc in response.choices[0].message.tool_calls]}")
                assistant_message = response.choices[0].message
                tool_calls = assistant_message.tool_calls
                results = self.handle_tool_calls(tool_calls)
                messages.append(assistant_message)
                messages.extend(results)
                reply =response.choices[0].message.content
            else:
                print(f"No tool call. finish_reason: {finish_reason}")
                print(f"Reply: {response.choices[0].message.content[:100]}")
                is_done = True
                reply =response.choices[0].message.content

        evaluation = self.evaluate_response(reply, user_message, history)

        if evaluation.is_response_acceptable:
            print("Passed evaluation - returning reply")
        is_done = True
        if not evaluation.is_response_acceptable:
            print("Response was not acceptable. Rerunning chat with feedback...")
            #display(Markdown(f"Feedback: {evaluation.feedback}"))
            reply = self.rerun_chat(reply, user_message, history, evaluation.feedback)
        return reply
    
if __name__ == "__main__":
    person = Person()
    gr.ChatInterface(person.chat_callback_function, type="messages", title="🤖 Yasin Emir Kutlu's CV Chatbot | Using Agentic AI & LLM Orchestration 🤖", description="<h2 style='text-align: center;'>💼 Ask me anything about Yasin Emir Kutlu's career, skills and experience!</h2>").launch()
