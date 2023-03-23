from db_functions import *


async def dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != int(variables.CHAT_ID):
        return
    bot = context.bot
    if hasattr(update.callback_query, "data"):
        for_who = update.callback_query.data.split()
        if for_who.__len__() > 1:
            if for_who[0] == "close":
                await bot.delete_message(chat_id=variables.CHAT_ID, message_id=int(for_who[1]))
                return
            user = context.bot_data[for_who[1]]
            if for_who[0] == "restrict":
                await add_user(context, user, "INSCRIPTION_USERS_STATUS")
                await update_subscription_user_status("restricted", context, user)
                await bot.delete_message(chat_id=variables.CHAT_ID,
                                         message_id=user.last_mess.last_group_message.message_id)
                if user.username is None:
                    uid = "`" + user.first_name + " `(" + user_chat_link(user) + ")"
                else:
                    uid = user.name
                # noinspection PyUnboundLocalVariable
                message = await bot.sendMessage(chat_id=variables.CHAT_ID,
                                                text="🔒 *Restriction*\n\n" + uid + "` has been"
                                                " restricted from sending requests.`\n\n🆘 If you made a mistake,"
                                                " you can ask @AleLntr to fix that for you.\n\n",
                                                parse_mode='MARKDOWN')

                keyboard = [[InlineKeyboardButton("Cancel", callback_data="close " + str(message.message_id))]]
                await bot.editMessageReplyMarkup(chat_id=variables.CHAT_ID, message_id=message.message_id,
                                                 reply_markup=InlineKeyboardMarkup(keyboard))
                user.last_mess.last_group_message = user.last_mess.first_group_message

            elif for_who[0] == "not_restrict":
                if user.username is None:
                    uid = user.first_name + " (" + user_chat_link(user) + ")"
                else:
                    uid = user.name
                # noinspection PyUnboundLocalVariable
                keyboard = [
                    [InlineKeyboardButton("Cancel", callback_data="close " +
                                                                  str(user.last_mess.last_group_message.message_id))]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await bot.editMessageText(text="🔓 " + uid + " hasn't been restricted.\n"
                                               "\nℹ️ You can still restrict this user with inline commands. "
                                               "Send `/help` for details\n\n",
                                          chat_id=variables.CHAT_ID,
                                          message_id=user.last_mess.last_group_message.message_id,
                                          parse_mode='MARKDOWN', reply_markup=reply_markup)
                user.last_mess.last_group_message = user.last_mess.first_group_message

    else:
        # Commands responses for executive group
        for_who = update.message.text.split()
        if for_who.__len__() == 1:
            # No-needed-arguments-commands
            if "flagged" in for_who:
                res = await db_functions.get_flagged_users(context)
                if res.__len__() > 0:
                    string = ""
                    c = 1
                    for i in res:
                        string += str(c) + ". @" + i[0] + "\n"
                        c += 1
                    await bot.delete_message(chat_id=variables.CHAT_ID, message_id=update.message.message_id)
                    message = await bot.send_message(chat_id=variables.CHAT_ID,
                                                     text="👁️‍🗨️ Those users already cancelled the "
                                                          "confirmation request in the past:\n\n"
                                                          + string)
                    keyboard = [
                        [InlineKeyboardButton("Cancel", callback_data="close " + str(message.message_id))]
                    ]
                    await bot.editMessageReplyMarkup(chat_id=variables.CHAT_ID, message_id=message.message_id,
                                                     reply_markup=InlineKeyboardMarkup(keyboard))
                else:
                    await bot.delete_message(chat_id=variables.CHAT_ID, message_id=update.message.message_id)
                    message = await bot.send_message(chat_id=variables.CHAT_ID,
                                                     text="👁️‍🗨️ No users have cancelled the"
                                                          " confirmation request in the past.")
                    keyboard = [
                        [InlineKeyboardButton("Cancel", callback_data="close " + str(message.message_id))]
                    ]
                    await bot.editMessageReplyMarkup(chat_id=variables.CHAT_ID, message_id=message.message_id,
                                                     reply_markup=InlineKeyboardMarkup(keyboard))
