# ruff: noqa: E402
############################################################################
## Django ORM Standalone Python Template
############################################################################
"""Here we'll import the parts of Django we need. It's recommended to leave
these settings as is, and skip to START OF APPLICATION section below"""

# Turn off bytecode generation
import sys

sys.dont_write_bytecode = True

# Import settings
import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

# setup django environment
import django


django.setup()

# Import your models for use in your script
from db.models import User, Conversation


############################################################################
## START OF APPLICATION
############################################################################
""" Replace the code below with your own """
import anvil.server
import anvil.tables as tables

from typing import List, Dict, Any
import json
import random

db_instance = None

secrets = json.load(open("secrets.json"))
# load secrets
OPEN_API_KEY = secrets["openai_key"]
DB_PWD = secrets["db_pwd"]
UPLINK_KEY = secrets["uplink_key"]
ELEVEN_KEY = secrets["eleven_key"]

anvil.server.connect(UPLINK_KEY)


################## User Management ##################
class UserNotFoundException(Exception): ...


@anvil.server.callable
def verify_password(email, password):
    try:
        _ = anvil.users.login_with_email(email, password)
        return True
    except anvil.users.AuthenticationFailed:
        return False


@anvil.server.callable
@tables.in_transaction
def set_user_field(email: str, field: str, value: Any):
    user = tables.users.get(email=email)
    if not user:
        raise UserNotFoundException(
            f"User with email: {email} not found, when setting: {value}"
        )
    try:
        user[field] = value
    except anvil.tables.TableError as e:
        print(f"Unable to modify user. Field: {field}, value: {value}\n{e}")


@anvil.server.callable
def set_user_marketing_pref(email: str, pref: bool):
    set_user_field(email, "marketing_optin", pref)


@anvil.server.callable
def set_user_displayname(email: str, name: str):
    set_user_field(email, "displayname", name, str)


@anvil.server.callable
def set_default_displayname(email: str):
    name = "user_" + str(random.randint(0, 1000000)).zfill(6)
    set_user_displayname(email, name)


################## /User Management ##################


class ExternalDB:
    def ensure_user(self, email: str):
        user, created = User.objects.get_or_create(email=email)
        return created

    def insert_conversation(self, email: str, role: str, content: str):
        user = User.objects.get(email=email)
        Conversation.objects.create(user=user, role=role, content=content)
        print(f"Conversation Entry: {email}|{role}|{content or 'None'}")

    def get_conversation(self, email: str):
        user = User.objects.get(email=email)
        conversations = Conversation.objects.filter(user=user).order_by("timestamp")
        return [(conv.role, conv.content) for conv in conversations]


def get_db_instance():
    global db_instance
    if db_instance is None:
        db_instance = ExternalDB()  # Initialize only once
    return db_instance


@anvil.server.callable
def db_ensure_user(email: str):
    try:
        get_db_instance().ensure_user(email)
        print(f"User {email} ensured.")
        return True
    except Exception as e:
        print(f"Error ensuring user: {e}")
        return False


@anvil.server.callable
def db_get_conversation(email: str):
    return get_db_instance().get_conversation(email)


@anvil.server.callable
def db_insert_conversation(email: str, role: str, content: str):
    get_db_instance().insert_conversation(email, role, content)
    return True


################## /DB ##################

################## OpenAI ##################
from openai import OpenAI


MAIN_MODEL = "o1-mini"
client = None


def get_openai_client():
    global client
    if client is None:
        client = OpenAI(api_key=OPEN_API_KEY)
    return client


@anvil.server.callable
def openai_get_conversations(email: str):
    db = get_db_instance()
    convs = db.get_conversation(email)
    messages = []
    for role, content in convs:
        messages.append({"role": role, "content": content})
    return messages


@anvil.server.callable
def openai_get_dm_response(messages: List[Dict[str, str]]):
    # generate a response from AI
    completion = get_openai_client().chat.completions.create(
        model=MAIN_MODEL, messages=messages
    )
    return completion.choices[0].message.content


################## /OpenAI ##################


################## Misc ##################
@anvil.server.callable
def healthcheck():
    return True


################## /Misc ##################

anvil.server.wait_forever()
