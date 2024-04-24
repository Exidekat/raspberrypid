import threading
from datetime import timedelta
import time
import pandas as pd
import openai

from config import *


class Assistant:
    def __init__(self):
        self.user = ""
        self.thread = threading.Thread(target=self.run)
        self.thread.start()

    def run(self):
        print("STARTING ASSISTANT")
        while self.user == "":
            time.sleep(0.5)
        self.user_input = "Hi assistant!"
        self.conversation = []
        client = openai.OpenAI()
        assistant = client.beta.assistants.create(
            name="Friend",
            instructions="You are an assistant to the user. Have a pleasant conversation with them.",
            tools=[{"type": "code_interpreter"}],
            model="gpt-3.5-turbo",
        )
        thread = client.beta.threads.create()

        while self.user_input != "exit":
            message = client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=self.user_input
            )
            self.run = client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant.id,
                instructions=f"Please address the user as {self.user}. The user has a premium account."
            )
            while self.run.status in ['queued', 'in_progress', 'cancelling']:
                time.sleep(1)  # Wait for 1 second
                self.run = client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=self.run.id
                )

            if self.run.status == 'completed':
                messages = client.beta.threads.messages.list(
                    thread_id=thread.id
                )
                #print(messages.data[0].content[0].text.value)
                self.conversation.append(messages.data[0].content[0].text.value)
            else:
                print(self.run.status)

            self.user_input = ""
            while self.user_input == "":
                time.sleep(0.1)

    def set_input(self, user_input):
        self.user_input = user_input
        self.conversation.append(user_input)

    def set_user(self, user):
        self.user = user

    def get_conversation(self):
        return self.conversation

assistant = Assistant()
