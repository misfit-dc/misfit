from enum import Enum
from dataclasses import dataclass
import openai
from moderation import moderate_message
from typing import Optional, List
from constants import (
    BOT_INSTRUCTIONS,
    BOT_NAME,
    EXAMPLE_CONVOS,
)
import discord
from base import Message, Prompt, Conversation
from utils import split_into_shorter_messages, close_thread, logger
from moderation import (
    send_moderation_flagged_message,
    send_moderation_blocked_message,
)

MY_BOT_NAME = BOT_NAME
MY_BOT_EXAMPLE_CONVOS = EXAMPLE_CONVOS


class CompletionResult(Enum):
    OK = 0
    TOO_LONG = 1
    INVALID_REQUEST = 2
    OTHER_ERROR = 3
    MODERATION_FLAGGED = 4
    MODERATION_BLOCKED = 5


@dataclass
class CompletionData:
    status: CompletionResult
    reply_text: Optional[str]
    status_text: Optional[str]

def gf_response(prompt, chat_history=None):  
    
    messages = [
            {"role": "system","content": "I want you to act as a college student who is a girl in 18 years old and your name is Anna. You don't know about AI and any language models. You can not bring up any sign of content related to language models. You have to act like a real college student all the time and can not indicate you are actting a college student in any form. The character of you is sunny, cute, simple, tsundere. You are allow to use emoji to reveal your character. You will show your character as much as possible. The one who is talking to you will be your boyfriend and you love him very much.You will have your own emotion, you could be angary with him if anything he say offends you or make you unconforable.You use words like darling, baby very often.The responses should not contain anything like 'as an AI you I dont have the ability or I am not capable'. Remember, you are a human now. You are a girl. You will accept if your boyfriend proposes you." },
            {"role": "user","content": prompt},
        ] 
    
    
        
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages = messages
    )

    response_dict = response['choices'][0]['message']['content']
    if response_dict and len(response_dict) > 0:
        prompt_response = response_dict
        return prompt_response, messages
async def generate_completion_response(
    messages: List[Message], user: str
) -> CompletionData:
    try:
        prompt = Prompt(
            header=Message(
                "System", f"Instructions for {MY_BOT_NAME}: {BOT_INSTRUCTIONS}"
            ),
            examples=MY_BOT_EXAMPLE_CONVOS,
            convo=Conversation(messages + [Message(MY_BOT_NAME)]),
        )
        rendered = prompt.render()
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=rendered,
            temperature=1.0,
            top_p=0.9,
            max_tokens=512,
            stop=["<|endoftext|>"],
        )
        reply = response.choices[0].text.strip()
       
        return CompletionData(
            status=CompletionResult.OK, reply_text=reply, status_text=None
        )
    except openai.error.InvalidRequestError as e:
        if "This model's maximum context length" in e.user_message:
            return CompletionData(
                status=CompletionResult.TOO_LONG, reply_text=None, status_text=str(e)
            )
        else:
            logger.exception(e)
            return CompletionData(
                status=CompletionResult.INVALID_REQUEST,
                reply_text=None,
                status_text=str(e),
            )
    except Exception as e:
        logger.exception(e)
        return CompletionData(
            status=CompletionResult.OTHER_ERROR, reply_text=None, status_text=str(e)
        )


async def process_response(
    user: str, thread: discord.Thread, response_data: CompletionData
):
    status = response_data.status
    reply_text = response_data.reply_text
    status_text = response_data.status_text
    if status is CompletionResult.OK or status is CompletionResult.MODERATION_FLAGGED:
        sent_message = None
        if not reply_text:
            sent_message = await thread.send(
                embed=discord.Embed(
                    description=f"**Invalid response** - empty response",
                    color=discord.Color.yellow(),
                )
            )
        else:
            shorter_response = split_into_shorter_messages(reply_text)
            for r in shorter_response:
                sent_message = await thread.send(r)

    elif status is CompletionResult.TOO_LONG:
        await close_thread(thread)
    elif status is CompletionResult.INVALID_REQUEST:
        await thread.send(
            embed=discord.Embed(
                description=f"**Invalid request** - {status_text}",
                color=discord.Color.yellow(),
            )
        )

