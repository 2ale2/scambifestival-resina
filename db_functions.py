import os
import sqlite3
from dataclasses import dataclass

from utils import *
from utils import _reply


@dataclass
class Connection:
    session: sqlite3.Connection
    cursor: sqlite3.dbapi2.Cursor


def connect():
    con = Connection
    con.session = sqlite3.connect("database/usernames.db")
    con.cursor = con.session.cursor()
    return con


# noinspection PyUnboundLocalVariable
async def user_in_db(context: CallbackContext, user: variables.UserInfos, table_name: str,
                     action_performed: str | None):
    conn = connect()
    c = conn.cursor
    if table_name == "FLAGGED_USERS":
        query = "SELECT user_id FROM " + table_name + " WHERE user_id = '" + str(user.id) \
                + "' AND action_performed =' " + action_performed + "'"
    else:
        query = "SELECT user_id FROM " + table_name + " WHERE user_id = '" + str(user.id) + "'"
    try:
        res = c.execute(query)
    except sqlite3.Error as e:
        await db_errors_handler(e, context)
        return None
    # qualora io mi chieda se un utente abbia già cancellato una richiesta, in caso di esito negativo,
    # aggiungo direttamente l'utente alla tabella
    if table_name == "FLAGGED_USERS":
        if res.fetchall().__len__() == 0:
            await add_user(context, user, "FLAGGED_USERS", "confirmation_request_cancelled")
            res = False

    return res


async def add_user(context: CallbackContext, user: variables.UserInfos, table_name: str, action_performed: str | None):
    conn = connect()
    c = conn.cursor
    if table_name == "INSCRIPTION_USERS_STATUS":
        values = "('" + user.id + "', '0', '0', '<null>')"
        # id_utente, stato, id_richiesta_conferma, data_richiesta

    elif table_name == "FLAGGED_USERS":
        values = "('" + user.id + "', '" + action_performed + "')"

    elif table_name == "USERS_INFOS":
        if user.username is not None:
            username = user.username
        else:
            username = "<null>"
        values = "('" + user.id + "', '" + username + "', '" + user.first_name + "', '" + user.last_name + "')"

    try:
        # noinspection PyUnboundLocalVariable
        c.execute(
            "INSERT OR IGNORE INTO " + table_name + " VALUES " + values
        )
    except sqlite3.Error as e:
        await db_errors_handler(e, context)
        if table_name == "INSCRIPTION_USERS_STATUS":
            keyboard = [
                [InlineKeyboardButton("⬅ Back to main menu", callback_data="start_over")],
                [InlineKeyboardButton("❌ Stop the bot", callback_data="stop")]
            ]
            await _reply(user, context, text="There was an error while working with internal database.\n"
                                             "I already contacted the staff about this. I cannot help you with "
                                             "this until it's fixed. 😓",
                         reply_markup=InlineKeyboardMarkup(keyboard))
            conn.session.close()
            return

    conn.session.commit()
    conn.session.close()


async def delete_user(context: CallbackContext, user: variables.UserInfos, table_name: str):
    conn = connect()
    c = conn.cursor
    try:
        c.execute("DELETE FROM " + table_name + " WHERE user_id = '" + user.id + "'")
    except sqlite3.Error as e:
        await db_errors_handler(e, context)

    conn.session.commit()
    conn.cursor.close()


async def update_subscription_user_status(new_status: str, request_sent: str, time: str, context: CallbackContext,
                                          user: variables.UserInfos):
    conn = connect()
    c = conn.cursor
    try:
        c.execute(
            "UPDATE INSCRIPTION_USERS_STATUS SET status = '" + new_status + "' WHERE user_id = '" + user.id + "'"
        )
        c.execute(
            "UPDATE INSCRIPTION_USERS_STATUS SET confirmation_request = '" + str(request_sent) + "' " +
            "WHERE user_id = '" + user.id + "'"
        )
        if time != "":
            c.execute(
                "UPDATE INSCRIPTION_USERS_STATUS SET request_date = '" + time + "' WHERE user_id = '" + user.id + "'"
            )
    except sqlite3.Error as e:
        await db_errors_handler(e, context)

    conn.session.commit()
    conn.cursor.close()


async def get_user_inscription_info(user: variables.UserInfos, context: ContextTypes.DEFAULT_TYPE, info: str):
    conn = connect()
    c = conn.cursor

    # possible infos:
    # 1 status
    # 2 confirmation_request
    # 3 request_date

    try:
        res = c.execute("SELECT " + info + " FROM INSCRIPTION_USERS_STATUS WHERE user_id = '" + user.id + "'")
    except sqlite3.Error as e:
        await db_errors_handler(e, context)
        return None

    if info == "confirmation_request":
        return res.fetchall()[0][0]  # ritorna ZERO oppure un id del messaggio di richiesta

    return res.fetchone()[0]


async def get_user_info(context: CallbackContext, user_id: str):
    conn = connect()
    c = conn.cursor

    try:
        res = c.execute("SELECT * FROM USERS_INFOS WHERE user_id = '" + user_id + "'")
    except sqlite3.Error as e:
        await db_errors_handler(e, context)
        keyboard = [
            [InlineKeyboardButton("⬅ Back to main menu", callback_data="start_over")],
            [InlineKeyboardButton("❌ Stop the bot", callback_data="stop")]
        ]
        await context.bot.send_message(chat_id=user_id,
                                       text="There was an error while working with internal database.\n"
                                            "I already contacted the staff about this. I cannot help you with "
                                            "this until it's fixed. 😓",
                                       reply_markup=InlineKeyboardMarkup(keyboard))
        res = None

    return res


async def get_flagged_users(context: ContextTypes.DEFAULT_TYPE, action_performed: str | None):
    conn = connect()
    c = conn.cursor

    if action_performed is None:
        query = "SELECT * FROM FLAGGED_USERS"
    else:
        query = "SELECT * FROM FLAGGED_USERS WHERE action_performed = '" + action_performed + "'"

    try:
        res = c.execute(query)
    except sqlite3.OperationalError as e:
        res = await db_errors_handler(e, context)
        return res

    return res.fetchall()


async def db_errors_handler(e: sqlite3.Error, context: ContextTypes.DEFAULT_TYPE):
    message = await context.bot.send_message(chat_id=variables.CHAT_ID,
                                             text="❌ `ERROR WHILE WORKING ON DATABASE`\n\n_Error name_: `" +
                                                  e.sqlite_errorname + "`\n_Error code_: `" + str(e.sqlite_errorcode) +
                                                  "`\n\nA message was sent to @AleLntr about this.",
                                             parse_mode='MARKDOWN')
    keyboard = [
        [InlineKeyboardButton("Cancel", callback_data="cancel " + str(message.message_id))]
    ]

    await context.bot.editMessageReplyMarkup(chat_id=variables.CHAT_ID, message_id=message.message_id,
                                             reply_markup=InlineKeyboardMarkup(keyboard))
    await context.bot.send_message(chat_id=os.environ.get('MY_ID'),
                                   text="❌ `ERROR WHILE WORKING ON DATABASE`\n\n_Error name_: `" +
                                        e.sqlite_errorname + "`\n_Error code_: `" + str(e.sqlite_errorcode) +
                                        "`\n_Message_: `" + e.args[0] + "`", parse_mode='MARKDOWN')
    res = str(e.sqlite_errorname)
    return res
