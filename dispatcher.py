from datetime import datetime

import telegram.error

import utils
from db_functions import *
from utils import _reply

# Features
ISCRIZIONE, DBEDITING, UPDATE = range(3)


# Gestisce il valore di query.data, lanciando l'opportuna funzione
async def dispatcher(actual_user: variables.UserInfos, update: Update, context: CallbackContext, feature: range):
    # Ogni feature va trattata a se. A seconda della feature scelta, seguo il ramo adeguato.
    # NOTA: potrei gestire insieme tutti gli stati senza distinguere i tre rami, ma lo faccio per questioni di ordine.
    if feature == int(ISCRIZIONE):
        if update.callback_query.data == "cancel_payment_confirmation_request":
            await cancel_payment_confirmation_request(context, actual_user)
            return
        # L'utente ha scelto d'iscriversi. Controllo il database per verificare lo stato del processo.
        last_status = await get_user_inscription_info(actual_user, context, "status")

        if last_status == "restricted":
            # L'utente è stato limitato dal gruppo dell'esecutivo
            await user_cannot_request(context, actual_user)
            return

        if last_status == str(ISCRIZIONE):
            await user_payment_confirmation_request(context, actual_user)

        elif last_status == "user_payment_confirmed" or last_status == "admin_payment_confirmed" \
                or last_status == "admin_payment_not_confirmed" or last_status == "user_awaiting_answer" or \
                last_status == "user_send_another_request":
            await admin_payment_confirmation_request(last_status, update, context, actual_user)

        elif last_status == "user_payment_not_confirmed":
            await user_payment_not_confirmed(actual_user, context)
            await db_functions.update_subscription_user_status(str(ISCRIZIONE), str(0), "", context, actual_user)

        elif last_status == "payment_confirmed" or last_status == "payment_not_confirmed":
            if update.callback_query.data != str(ISCRIZIONE):
                await payment_confirmation_answer(last_status, context, actual_user)
            else:
                await payment_already_checked(actual_user, context, last_status)

    elif feature == int(DBEDITING):
        print("hai scelto editing")

    else:
        print("hai scelto update")


async def user_payment_confirmation_request(context: CallbackContext, actual_user: variables.UserInfos):
    payment_request_keyboard = [
        [
            InlineKeyboardButton("Yes!", callback_data="user_payment_confirmed"),
            InlineKeyboardButton("No, I haven't yet.", callback_data="user_payment_not_confirmed")
        ],
        [InlineKeyboardButton("⬅ Back to main menu", callback_data="start_over")]
    ]

    await _reply(actual_user, context,
                 "🖋 *Scambi staff subscription*\n\nOk! I guess we are gonna have a new member. 😎"
                 "\n\nHave you paid the membership fee yet?",
                 reply_markup=InlineKeyboardMarkup(payment_request_keyboard))


async def admin_payment_confirmation_request(status: str, update: Update, context: CallbackContext,
                                             actual_user: variables.UserInfos):
    bot = context.bot
    if status == "user_payment_confirmed":
        from_chat = str(update.callback_query.message.chat_id)
        sent = await db_functions.get_user_inscription_info(actual_user, context, "confirmation_request")

        if from_chat != variables.CHAT_ID:
            # Avviso l'utente che sto chiedendo conferma al direttivo
            # noinspection PyTypeChecker
            await bot.delete_message(chat_id=actual_user.id,
                                     message_id=actual_user.last_mess.last_user_message.message_id)
            if sent is not None:
                if sent == "<null>" or not int(sent):
                    keyboard = [
                        [InlineKeyboardButton("Cancel ❌", callback_data="cancel_payment_confirmation_request")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    message = await bot.send_message(actual_user.id,
                                                     text="Got it! Before we can proceed, I need a"
                                                          " confirmation from the executive staff.\n\n"
                                                          "📩  `Confirmation request sent. Awaiting the answer..`\n\n"
                                                          "⏳ Please note that this can take a while depending on when "
                                                          "a staff member will answer to the Telegram confirmation "
                                                          "message.\n\n💡 Meanwhile you can contact someone from the "
                                                          "Scambi team to be confirmed sooner.",
                                                     reply_markup=reply_markup,
                                                     parse_mode='MARKDOWN')
                    actual_user.last_mess.last_user_message = message

                elif int(sent) > 1:

                    request_time = await db_functions.get_user_inscription_info(actual_user, context, "request_date")

                    if (datetime.now() - datetime.strptime(request_time, "%Y-%m-%d %H:%M:%S")).days == 0:
                        message = await bot.send_message(chat_id=actual_user.id,
                                                         text="ℹ️ You already send a confirmation request less than "
                                                              "24 hours ago. Please wait until the staff answer your"
                                                              " request or come back later.\n\n💡 You can also contact"
                                                              " someone from the Scambi team to be confirmed sooner."
                                                              "\n\nSend /start to go back to the main menu.")
                        # potrei valutare di aggiungere un tasto che cancelli questo messaggio

                    else:
                        keyboard = [
                            [InlineKeyboardButton("Wait ⏱", callback_data="user_awaiting_answer")],
                            [InlineKeyboardButton("Send a new request 📩", callback_data="user_send_another_request")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        message = await bot.send_message(chat_id=actual_user.id,
                                                         text="ℹ️ You already send a confirmation request in the past"
                                                              " which has not been answered yet.\n\nIf some time is "
                                                              "passed since you made that request, I suggest to delete "
                                                              "the previous one and send a new one; otherwise "
                                                              "you can wait for the first request to be answered.",
                                                         reply_markup=reply_markup)
                    actual_user.last_mess.last_user_message = message

                    return

                elif int(sent) == -1:

                    request_time = await db_functions.get_user_inscription_info(actual_user, context, "request_date")

                    if (datetime.now() - datetime.strptime(request_time, "%Y-%m-%d %H:%M:%S")).days == 0:
                        keyboard = [
                            [InlineKeyboardButton("Contact the staff", url="https://t.me/AleLntr")]
                        ]
                        message = await bot.send_message(chat_id=actual_user.id,
                                                         text="ℹ️ You already send a confirmation request in the past "
                                                              "which has been deleted. However, you cannot make "
                                                              "another request before 24 hours from the previuos one. "
                                                              "Please come back later or contact the staff."
                                                              "\n\nSend /start to go back to the main menu.",
                                                         reply_markup=InlineKeyboardMarkup(keyboard))

                    else:
                        keyboard = [
                            [InlineKeyboardButton("Send a new request 📩", callback_data="user_send_another_request")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        message = await bot.send_message(chat_id=actual_user.id,
                                                         text="ℹ️ You already send a confirmation request in the past "
                                                              "which has been deleted.\n\nI suggest to send a new one.",
                                                         reply_markup=reply_markup)
                    actual_user.last_mess.last_user_message = message

                    return

                elif int(sent) != 1:
                    message = await bot.send_message(chat_id=actual_user.id,
                                                     text="❌ *ERROR*\n\nAn error occurred while "
                                                          "trying to find if you already made the "
                                                          "confirmation request.\n\n`A notification"
                                                          " has been sent to the staff.`",
                                                     parse_mode="MARKDOWN")
                    actual_user.last_mess.last_user_message = message

                    return

        # Codice eseguito se sent == 0 o sent == 1
        keyboard = [
            [
                InlineKeyboardButton("✅ Fee verified", callback_data="admin_payment_confirmed " + actual_user.id),
                InlineKeyboardButton("❌ Fee not verified", callback_data="admin_payment_not_confirmed "
                                                                         + actual_user.id)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "⚠️ *PAY CONFIRMATION REQUEST* ⚠️\n\nThe following user asked to be signed up to Scambi staff." \
               "\n\n_Full name_: " + actual_user.full_name + "\n_Username_: " + user_chat_link(actual_user) + \
               "\n\n➡️ Did this user already pay the fee?"

        if from_chat == variables.CHAT_ID:
            # if executive group wants to retreat a decision
            await bot.editMessageText(text=text, chat_id=variables.CHAT_ID,
                                      message_id=actual_user.last_mess.last_group_message.message_id,
                                      reply_markup=reply_markup, parse_mode='MARKDOWN')
            await db_functions.update_subscription_user_status("user_payment_confirmed", "", "", context, actual_user)
        else:
            # if the user didn't send a request before
            message = await bot.send_message(variables.CHAT_ID, text=text,
                                             reply_markup=reply_markup, parse_mode='MARKDOWN')

            await db_functions.update_subscription_user_status("user_payment_confirmed", str(message.id),
                                                               str(message.date)[:len(str(message.date)) - 6],
                                                               context, actual_user)
            actual_user.last_mess.last_group_message = message
            if sent is not None and sent == "<null>":
                actual_user.last_mess.first_group_message = message
        return

    elif status == "user_awaiting_answer":
        try:
            request_id = await db_functions.get_user_inscription_info(actual_user, context, "confirmation_request")

            if "waiting for the request to be answered" in actual_user.last_mess.last_group_message.text:
                await bot.delete_message(chat_id=variables.CHAT_ID,
                                         message_id=actual_user.last_mess.last_group_message.message_id)

            message = await bot.send_message(chat_id=variables.CHAT_ID,
                                             text=actual_user.name + " is waiting for the request to be answered!",
                                             reply_to_message_id=request_id)
            await bot.editMessageText(text="OK! I'll urge the Scambi Staff to process your request. ⏩",
                                      chat_id=actual_user.id,
                                      message_id=actual_user.last_mess.last_user_message.message_id)

            actual_user.last_mess.last_group_message = message
            await db_functions.update_subscription_user_status("user_payment_confirmed", request_id, "", context,
                                                               actual_user)
        except telegram.error.BadRequest:
            keyboard = [
                [InlineKeyboardButton("Send a new request 📩", callback_data="user_send_another_request")],
                [InlineKeyboardButton("Contact the staff directly", url="https://t.me/AleLntr",
                                      callback_data="user_payment_confirmed")]
            ]
            await bot.editMessageText("🤔 Sorry but I cannot find your request message in the staff group. However, you"
                                      " can send a new one.",
                                      chat_id=actual_user.id,
                                      message_id=actual_user.last_mess.last_user_message.message_id,
                                      reply_markup=InlineKeyboardMarkup(keyboard))
            await db_functions.update_subscription_user_status("user_payment_confirmed", str(-1), "", context,
                                                               actual_user)

        # else:
        #     await db_functions.update_subscription_user_status("user_payment_confirmed", str(message.message_id),
        #                                                        context, actual_user)
        # questo codice non va bene perché devo sapere qual è l'id del messaggio di richiesta, del resto non mi frega

    elif status == "user_send_another_request":
        res = int(await db_functions.get_user_inscription_info(actual_user, context, "confirmation_request"))
        await bot.editMessageText(text="OK! I'll send a new request.", chat_id=actual_user.id,
                                  message_id=actual_user.last_mess.last_user_message.message_id)
        if res > 0:
            try:
                await bot.delete_message(chat_id=variables.CHAT_ID, message_id=res)
            except error.BadRequest:
                logging.warning("Message to delete not found. Skipping this step...")

            await db_functions.update_subscription_user_status("user_payment_confirmed", str(1), "", context,
                                                               actual_user)

        # invio la richiesta
        await admin_payment_confirmation_request("user_payment_confirmed", update, context, actual_user)

        keyboard = [
            [InlineKeyboardButton("Cancel ❌", callback_data="cancel_payment_confirmation_request")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = await bot.send_message(actual_user.id,
                                         text="📩  `Confirmation request sent. Awaiting the answer..`\n\n"
                                              "⏳ Please note that this can take a while depending on when "
                                              "a staff member will answer to the Telegram confirmation "
                                              "message.\n\n💡 Meanwhile you can contact someone from the "
                                              "Scambi team to be confirmed sooner.", reply_markup=reply_markup,
                                         parse_mode='MARKDOWN')
        actual_user.last_mess.last_user_message = message

    # Chiedo la conferma della conferma (non si sa mai)
    if status == "admin_payment_confirmed":
        keyboard = [
            [
                InlineKeyboardButton("Yes.", callback_data="payment_confirmed " + actual_user.id),
                InlineKeyboardButton("No, go back.", callback_data="user_payment_confirmed " + actual_user.id)
            ]
        ]
        await bot.editMessageText(chat_id=variables.CHAT_ID,
                                  message_id=actual_user.last_mess.last_group_message.message_id,
                                  text="✅️ *PAY CONFIRMATION REQUEST* ✅️\n\nYou just confirmed"
                                       " the payment from " + actual_user.full_name + " (" + user_chat_link(actual_user)
                                       + ").\n\n*Are you sure?*\nPlease note that this operation cannot be"
                                         " cancelled.",
                                  reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MARKDOWN')

    elif status == "admin_payment_not_confirmed":
        keyboard = [
            [
                InlineKeyboardButton("Yes.", callback_data="payment_not_confirmed " + actual_user.id),
                InlineKeyboardButton("No, go back.", callback_data="user_payment_confirmed " + actual_user.id)
            ]
        ]
        await bot.editMessageText(chat_id=variables.CHAT_ID,
                                  message_id=actual_user.last_mess.last_group_message.message_id,
                                  text="❌️ *PAY CONFIRMATION REQUEST* ❌️\n\nYou *didn't confirm*"
                                       " the payout from " + actual_user.full_name + " (" + user_chat_link(actual_user)
                                       + ").\n\n*Are you sure?*\nPlease note that this operation cannot be cancelled.",
                                  reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MARKDOWN')


async def payment_confirmation_answer(status: str, context: CallbackContext, actual_user: variables.UserInfos):
    bot = context.bot
    await bot.delete_message(chat_id=actual_user.id, message_id=actual_user.last_mess.last_user_message.message_id)
    await bot.delete_message(chat_id=variables.CHAT_ID, message_id=actual_user.last_mess.last_group_message.message_id)

    if status == "payment_confirmed":

        message = await bot.send_message(actual_user.id,
                                         text="✅ *Payment confirmed* ✅\n\nSorry for the wait! The executive"
                                              " group just _confirmed_ your fee payment. Now we can"
                                              " proceed with your subscription. 🤗", parse_mode='MARKDOWN')

        group_message = await bot.send_message(variables.CHAT_ID,
                                               text="✅ The subscription fee payment from " + actual_user.full_name +
                                                    " (" + user_chat_link(actual_user) + ") *has been confirmed*."
                                                    "\nThe user will be registered to Scambi staff.",
                                               parse_mode='MARKDOWN')

    elif status == "payment_not_confirmed":
        keyboard = [
            [InlineKeyboardButton("⬅ Back to main menu", callback_data="start_over")],
            [InlineKeyboardButton("❌ Stop the bot", callback_data="stop")]
        ]

        message = await bot.send_message(actual_user.id,
                                         text="❌ *Payment not confirmed* ❌\n\nSorry, the executive group did not "
                                              "confirmed you fee payment.\n\nℹ️ If you think there is a problem,"
                                              " feel free to contact the staff to eventually fix that.",
                                         reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MARKDOWN')

        group_message = await bot.send_message(variables.CHAT_ID,
                                               text="❌ The subscription fee payment from " + actual_user.full_name +
                                                    " (" + user_chat_link(actual_user) + ") *has not been confirmed*.\n"
                                                    "The user will not be able to be enrolled to the staff.\n\n"
                                                    "🆘️ If you made a mistake you can still manually add this user"
                                                    " by yourself or ask @AleLntr to cancel your decision.\n",
                                               parse_mode='MARKDOWN')

    # noinspection PyUnboundLocalVariable
    context.bot_data[actual_user.id].last_mess.last_user_message = message
    # noinspection PyUnboundLocalVariable
    context.bot_data[actual_user.id].last_mess.last_group_message = group_message
    return


async def payment_already_checked(actual_user: variables.UserInfos, context: CallbackContext, status: str):
    if status == "payment_confirmed":
        print()
    else:
        bot = context.bot
        keyboard = [
            [InlineKeyboardButton("⬅ Back to main menu", callback_data="start_over")],
            [InlineKeyboardButton("❌ Stop the bot", callback_data="stop")]
        ]
        await bot.editMessageText(chat_id=actual_user.id, message_id=actual_user.last_mess.last_user_message.message_id,
                                  text="⚠️ Your payment hasn't been confirmed in the past.\n\n🆘️ If "
                                       "you paid the subscription please ask for help to the staff in "
                                       "order to allow me adding you to the shareholders' register now.",
                                  reply_markup=InlineKeyboardMarkup(keyboard))


async def user_payment_not_confirmed(actual_user: variables.UserInfos, context: CallbackContext):
    bot = context.bot
    keyboard = [
        [InlineKeyboardButton("⬅ Back to main menu", callback_data="start_over")],
        [InlineKeyboardButton("❌ Stop the bot", callback_data="stop")]
    ]
    await bot.editMessageText(text="❗ *You didn't confirm you payment*\n\nI cannot help you with signing up "
                                   "if don't pay the subscription fee first. 🙁", chat_id=actual_user.id,
                              message_id=actual_user.last_mess.last_user_message.message_id,
                              reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MARKDOWN')


async def cancel_payment_confirmation_request(context: CallbackContext, actual_user: variables.UserInfos):
    bot = context.bot
    group_message = actual_user.last_mess.last_group_message.message_id
    user_message = actual_user.last_mess.last_user_message.message_id
    if await user_in_db(context, actual_user, "FLAGGED_USERS", "confirmation_request_cancelled"):
        keyboard = [
            [
                InlineKeyboardButton("🔒 Restrict user", callback_data="restrict send_requests " + actual_user.id),
                InlineKeyboardButton("🔓 Do not restrict", callback_data="not_restrict send_requests " + actual_user.id)
            ]
        ]
        await bot.editMessageText(text="❌️ " + actual_user.first_name + " (" + user_chat_link(actual_user) +
                                       ") cancelled the request.\n\nℹ️ `This user already cancelled the request"
                                       " in the past. Do you want me to restrict " + actual_user.name + "?`",
                                  chat_id=variables.CHAT_ID,
                                  message_id=group_message,
                                  reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MARKDOWN')
        await bot.editMessageText(text="ℹ️ The confirmation payment request has been canceled.\n\n"
                                       "`This message will self delete within 5 seconds.`", chat_id=actual_user.id,
                                  message_id=user_message,
                                  parse_mode='MARKDOWN')

    else:
        await bot.editMessageText(text="❌️ " + actual_user.first_name + " (" + user_chat_link(actual_user) +
                                       ") cancelled the request.\n\n`This message will self delete within 5 seconds.`",
                                  chat_id=variables.CHAT_ID,
                                  message_id=group_message,
                                  parse_mode='MARKDOWN')
        await bot.editMessageText(text="ℹ️ The confirmation payment request has been canceled.\n\n"
                                       "`This message will self delete within 5 seconds.`", chat_id=actual_user.id,
                                  message_id=user_message,
                                  parse_mode='MARKDOWN')
        data = {
            "function": "delete_message",
            "params": {
                "chat_id": variables.CHAT_ID,
                "message_id": actual_user.last_mess.last_group_message.message_id
            }
        }
        context.job_queue.run_once(utils.job_dispatcher, when=5.0, data=data)
        actual_user.last_mess.last_group_message = actual_user.last_mess.first_group_message
    actual_user.checks.signin_up_note_check = False


async def user_cannot_request(context: CallbackContext, actual_user: variables.UserInfos):
    bot = context.bot
    keyboard = [
        [InlineKeyboardButton("⬅ Back to main menu", callback_data="start_over")],
        [InlineKeyboardButton("❌ Stop the bot", callback_data="stop")]
    ]
    await bot.editMessageText(text="🔒 *You have been restricted*\n\n"
                                   "Sorry, the executive group restricted you from performing this action.",
                              chat_id=actual_user.id, message_id=actual_user.last_mess.last_user_message.message_id,
                              reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MARKDOWN')
