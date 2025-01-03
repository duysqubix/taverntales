import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
import anvil.server
import random
import json


from typing import List, Dict, Any


db_instance = None

# load secrets
OPEN_API_KEY = json.load(open("secrets.json"))["openai_key"]
DB_PWD = json.load(open("secrets.json"))["db_pwd"]
UPLINK_KEY = json.load(open("secrets.json"))["uplink_key"]

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

################## DB ##################
import psycopg2
import psycopg2.pool


class ExternalDB:
    def __init__(self):
        self.pool = psycopg2.pool.SimpleConnectionPool(
            1,
            10,  # Min and Max connections in the pool
            dbname="defaultdb",
            user="doadmin",
            password=DB_PWD,
            host="db-postgresql-tavern-tales-do-user-8614367-0.j.db.ondigitalocean.com",
            port="25060",
        )
        print("Initialized ExternalDB with connection pooling.")

    def get_connection(self):
        return self.pool.getconn()

    def release_connection(self, conn):
        self.pool.putconn(conn)

    def ensure_user(self, email: str):
        """
        Ensure that a user exists in the database.
        """
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (email) VALUES (%s) ON CONFLICT DO NOTHING;",
            (email,),
        )
        conn.commit()
        self.release_connection(conn)

    def insert_conversation(self, email: str, role: str, content: str):
        """
        Insert a new conversation
        """
        conn = self.get_connection()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO conversations (email, role, content) VALUES (%s, %s, %s);",
                (email, role, content),
            )
        conn.commit()
        print(f"Conversation Entry: {email}|{role}|{content}")
        self.release_connection(conn)

    def get_conversation(self, email: str):
        """
        Get full conversation of email

        ** expand eventually based on adventure **
        """
        conn = self.get_connection()
        content = None
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    role, content
                FROM conversations 
                WHERE 
                    email = %s 
                ORDER BY timestamp ASC;
                """,
                (email,),
            )
            content = cur.fetchall()
        self.release_connection(conn)
        return content


def get_db_instance():
    global db_instance
    if db_instance is None:
        db_instance = ExternalDB()  # Initialize only once
    return db_instance


@anvil.server.callable
def db_ensure_user(email: str):
    get_db_instance().ensure_user(email)
    print(f"User {email} ensured.")
    return True


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
