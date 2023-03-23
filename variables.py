import os
from dataclasses import dataclass

import telegram
from telegram.ext import *

import db_functions


@dataclass
class LastMessages:
    last_user_message: telegram.Message
    last_group_message: telegram.Message
    first_user_message: telegram.Message
    first_group_message: telegram.Message


@dataclass
class Checks:
    # for user's fullname checking at the start
    fullname_check: bool


# user infos class
@dataclass
class UserInfos:
    link: str
    name: str
    id: str
    username: str
    last_mess: LastMessages
    checks: Checks
    first_name: str = ""
    last_name: str = ""
    full_name: str = ""
    full_name_temp: str = ""


# Bot token
TOKEN = os.environ.get('BOT_TOKEN')
# Executive chat ID
CHAT_ID = os.environ.get('EXECUTIVE_CHAT_ID')
# users dictionary - per l'uso contemporaneo
users_dict = {}


async def _set(context: ContextTypes.DEFAULT_TYPE, starting_infos: telegram.User, starting_message: telegram.Message,
               from_db: bool):
    if from_db is False:
        context.bot_data[str(starting_infos.id)] = UserInfos(
            username=starting_infos.username,
            id=str(starting_infos.id),
            link=starting_infos.link,
            name=starting_infos.name,
            last_mess=LastMessages(
                last_user_message=starting_message,
                last_group_message=starting_message,
                first_user_message=starting_message,
                first_group_message=starting_message
            ),
            checks=Checks(
                fullname_check=False
            )
        )
        if starting_infos.last_name is not None:
            context.bot_data[str(starting_infos.id)].first_name = starting_infos.first_name
            context.bot_data[str(starting_infos.id)].last_name = starting_infos.last_name
            context.bot_data[str(starting_infos.id)].full_name = \
                context.bot_data[str(starting_infos.id)].first_name + " " + \
                context.bot_data[str(starting_infos.id)].last_name
        if starting_infos.username is not None:
            context.bot_data[str(starting_infos.id)].link = "https://t.me/" + starting_infos.username
    else:
        res = await db_functions.get_user_info(context, str(starting_infos.id))
        res = res.fetchall()
        if res is not None and res.__len__() == 1:
            res = res[0]
            context.bot_data[str(starting_infos.id)] = UserInfos(
                username=res[1],
                id=res[0],
                link=starting_infos.link,
                name=starting_infos.name,
                last_mess=LastMessages(
                    last_user_message=starting_message,
                    last_group_message=starting_message,
                    first_user_message=starting_message,
                    first_group_message=starting_message
                ),
                checks=Checks(
                    fullname_check=True
                )
            )
            context.bot_data[str(starting_infos.id)].first_name = res[2]
            context.bot_data[str(starting_infos.id)].last_name = res[3]
            context.bot_data[str(starting_infos.id)].full_name = \
                context.bot_data[str(starting_infos.id)].first_name + " " + \
                context.bot_data[str(starting_infos.id)].last_name
            if starting_infos.username != "<null>":
                context.bot_data[str(starting_infos.id)].link = "https://t.me/" + starting_infos.username
            else:
                context.bot_data[str(starting_infos.id)].username = None
