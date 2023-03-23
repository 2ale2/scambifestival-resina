# Questo modulo contiene tutte le funzioni che non competono agli altri moduli. Leggere 'struttura.txt' per più info
from telegram import *
from telegram.ext import *

import db_functions
import variables


async def _reply(user: variables.UserInfos, context: CallbackContext, text: str,
                 reply_markup: InlineKeyboardMarkup, parse_mode='MARKDOWN'):
    bot = context.bot

    if "{}" in text:
        message = await bot.editMessageText(text.format(user.first_name), chat_id=user.id,
                                            message_id=user.last_mess.last_user_message.message_id,
                                            parse_mode=parse_mode,
                                            reply_markup=reply_markup)
    else:
        message = await bot.editMessageText(text, chat_id=user.id,
                                            message_id=user.last_mess.last_user_message.message_id,
                                            parse_mode=parse_mode, reply_markup=reply_markup)

    user.last_mess.last_user_message = message
    # context.bot_data[user.username] = user


async def data_gatherer(update: Update, context: ContextTypes.DEFAULT_TYPE, user: variables.UserInfos):
    bot = context.bot
    if hasattr(update.callback_query, "data"):
        if update.callback_query.data == "full_name_correct":
            if user.full_name_temp != "":
                name_dict = user.full_name_temp.split()
                user.first_name = name_dict[0]
                user.last_name = " ".join(name_dict[1:])
                user.full_name = user.full_name_temp
            user.checks.fullname_check = True
            await db_functions.add_user(context, user, "USERS_INFOS", None)
            return ConversationHandler.END
        elif update.callback_query.data == "full_name_not_correct":
            # noinspection PyTypeChecker
            await bot.editMessageText(text="Ok, no problem! Please tell me your correct full name.",
                                      chat_id=user.id, message_id=user.last_mess.last_user_message.message_id)
            return 1

    elif update.message.text == "/start":
        if user.last_name != "":
            # L'utente ha scritto qualcosa nel campo 'Cognome' sul suo profilo Telegram. Chiedo se è corretto.
            full_name = user.first_name + " " + user.last_name
            keyboard = [
                [
                    InlineKeyboardButton("Yes!", callback_data="full_name_correct"),
                    InlineKeyboardButton("No!", callback_data="full_name_not_correct")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = await bot.sendMessage(chat_id=user.id, text="Hi! I'm _Resina_, the Scambi digital helper.\n"
                                                                  "Before we can proceed, I need to know if I got"
                                                                  " your correct full name.\n\nIs *" + full_name +
                                                                  "* your actual full name?",
                                            parse_mode='MARKDOWN', reply_markup=reply_markup)
            user.last_mess.last_user_message = message
            return 0
        else:
            message = await bot.send_message(chat_id=user.id, text="Hi! I'm _Resina_, the Scambi digital helper.\n\n"
                                                                   "Before we can proceed, I need to know your full "
                                                                   "name."
                                                                   "\n\nCan you just write it down? 😊",
                                             parse_mode='MARKDOWN')
            user.last_mess.last_user_message = message
            return 1
    else:
        if user.id == str(update.message.from_user.id):
            # L'utente ha indicato il suo nome, chiedo se è corretto
            user.full_name_temp = update.message.text
            if not user.full_name_temp.replace(" ", "").isalpha():
                message = await bot.sendMessage(chat_id=user.id, text="⚠️ Sorry but your fullname should not contain "
                                                                      "any digit or symbol.\nPlease send it again.")
                user.last_mess.last_user_message = message
                return 1
            if user.full_name_temp.split(" ").__len__() < 2:
                message = await bot.sendMessage(chat_id=user.id, text="⚠️ It seems that you didn't specify your last "
                                                                      "name.\nPlease send your fullname including your"
                                                                      " last name as well.")
                user.last_mess.last_user_message = message
                return 1
            keyboard = [
                [
                    InlineKeyboardButton("Yes!", callback_data="full_name_correct"),
                    InlineKeyboardButton("No!", callback_data="full_name_not_correct")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = await bot.sendMessage(chat_id=user.id, text="`Is \"" + user.full_name_temp + "\" your actual "
                                                                                                   "full name?`",
                                            parse_mode='MARKDOWN', reply_markup=reply_markup)
            user.last_mess.last_user_message = message
            return 0

    # context.bot_data[user.username] = user
    return


def get_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if hasattr(update.callback_query, "from_user"):
        sid = str(update.callback_query.from_user.id)
        if sid in context.bot_data:
            return context.bot_data[sid]
            # con la persistenza, potrebbe essere inutile chiedere "if sid in context.bot_data": la risposta è sempre si
        return update.callback_query.from_user
    else:
        sid = str(update.message.from_user.id)
        if sid in context.bot_data:
            return context.bot_data[sid]
        return update.message.from_user


def user_chat_link(user: variables.UserInfos):
    if user.username is not None:
        return user.name
    return "💬 [userchat](tg://user?id=" + str(user.id) + ")"
