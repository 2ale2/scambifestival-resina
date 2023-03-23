import logging

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram import __version__ as TG_VER
from telegram.ext import *

import db_functions
import exec_dispatcher
import utils
import variables
import dispatcher
from utils import _reply
from variables import _set

TOKEN = variables.TOKEN

# noinspection DuplicatedCode
try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This example is not compatible with your current PTB version {TG_VER}. To view the "
        f"{TG_VER} version of this example, "
        f"visit https://docs.python-telegram-bot.org/en/v{TG_VER}/examples.html"
    )

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Stati - Differenzio le funzioni
ISCRIZIONE, DBEDITING, UPDATE = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    outcome = 0
    if not hasattr(update.callback_query, "data"):
        if update.effective_chat.type != telegram.Chat.PRIVATE:
            return

    actual_user = utils.get_user(update, context)
    if str(actual_user.id) not in context.bot_data:
        res = await db_functions.user_in_db(context, actual_user, "USERS_INFOS", None)
        if res is not None and res.fetchall().__len__() != 0:
            # L'utente è già presente nel database; posso evitare di chiedere il nome e il cognome
            await _set(context, actual_user, update.message, True)
            outcome = ConversationHandler.END
        else:
            # Salvo le information sull'utente
            await _set(context, actual_user, update.message, False)
            return await utils.data_gatherer(update, context, context.bot_data[str(actual_user.id)])

    actual_user = context.bot_data[str(actual_user.id)]

    if actual_user.checks.fullname_check is not True:
        outcome = await utils.data_gatherer(update, context, actual_user)

    if actual_user.checks.fullname_check is True:
        keyboard = [
            [
                InlineKeyboardButton("Sign me up!", callback_data=str(ISCRIZIONE)),
                InlineKeyboardButton("I need to edit Pino.", callback_data=str(DBEDITING)),
            ],
            [InlineKeyboardButton("I need an update on a group current tasks.", callback_data=str(UPDATE))],
        ]

        if not hasattr(update.callback_query, "data"):
            # vuol dire che l'utente non ha interagito con i tasti proposti da Resina, quindi non è stato mandato alcun
            # messaggio da parte sua
            message = await context.bot.send_message(actual_user.id,
                                                     text="Hi, {}!\nMy name is Resina and I'm a digital Scambi staff"
                                                     " member. I can do several things; please choose from the"
                                                     " keyboard below. 😊".format(actual_user.first_name),
                                                     reply_markup=InlineKeyboardMarkup(keyboard))
            actual_user.last_mess.last_user_message = message

        else:
            await _reply(actual_user, context, text="Hi, {}!\nMy name is Resina and I'm a digital Scambi staff"
                                                    " member. I can do several things; please choose from the"
                                                    " keyboard below. 😊".format(actual_user.first_name),
                         reply_markup=InlineKeyboardMarkup(keyboard))

    return outcome


async def user_signin_up(update: Update, context: CallbackContext):
    for_who = update.callback_query.data.split()
    if for_who.__len__() == 1:
        # L'utente richiedente ha interagito
        actual_user = context.bot_data[str(update.callback_query.from_user.id)]
    else:
        # Il gruppo del direttivo ha interagito
        # NOTA: l'utente per il cui il gruppo ha interagito deve essere presente in context.bot_data
        # dal momento che il gruppo può interagire solo se l'utente lo ha fatto per primo (adesso bot_data è anche
        # persistente)
        actual_user = context.bot_data[for_who[1]]

    res = await db_functions.user_in_db(context, actual_user, "INSCRIPTION_USERS_STATUS", None)
    if res is not None and res.fetchall().__len__() == 0:
        await db_functions.add_user(context, actual_user, "INSCRIPTION_USERS_STATUS", None)
    elif update.callback_query.data != str(ISCRIZIONE):
        if update.callback_query.data == "cancel_payment_confirmation_request":
            await db_functions.delete_user(context, actual_user, "INSCRIPTION_USERS_STATUS")
        elif await db_functions.get_user_inscription_info(actual_user, context, "status") != "restricted":
            sent = await db_functions.get_user_inscription_info(actual_user, context, "confirmation_request")
            await db_functions.update_subscription_user_status(for_who[0], sent, "", context, actual_user)

    await dispatcher.dispatcher(actual_user, update, context, ISCRIZIONE)
    if update.callback_query.data == "cancel_payment_confirmation_request":
        await start(update, context)
    return


async def executive_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await exec_dispatcher.dispatcher(update, context)


def main():
    persistence = PicklePersistence(filepath="pers.persistence")
    app = Application.builder().token(variables.TOKEN).persistence(persistence=persistence).build()

    # Definizione degli handler

    # Handler che lancia la funzione iniziale
    # app.add_handler(CommandHandler("start", start))
    #
    # # Handlers per la raccolta delle informazioni sull'utente
    # app.add_handler(CallbackQueryHandler(start, pattern="full_name_correct"))
    # app.add_handler(CallbackQueryHandler(start, pattern="full_name_not_correct"))
    # app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))

    fullname_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            0: [CallbackQueryHandler(start, pattern="full_name_not_correct")],
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, start)]
        },
        fallbacks=[CallbackQueryHandler(start, pattern="full_name_correct")]
    )
    app.add_handler(fullname_conv_handler)
    # Handler per rimostrare il menu principale
    app.add_handler(CommandHandler("start", start))
    # Handlers che gestiscono la feature d'iscrizione. A ogni handler corrisponde uno stato.
    app.add_handler(CallbackQueryHandler(user_signin_up, pattern="^" + str(ISCRIZIONE) + "$"))
    app.add_handler(CallbackQueryHandler(user_signin_up, pattern="cancel_payment_confirmation_request"))
    app.add_handler(CallbackQueryHandler(user_signin_up, pattern="user_payment_not_confirmed"))
    app.add_handler(CallbackQueryHandler(user_signin_up, pattern="user_awaiting_answer"))
    app.add_handler(CallbackQueryHandler(user_signin_up, pattern="user_send_another_request"))
    app.add_handler(CallbackQueryHandler(user_signin_up, pattern="^user_payment_confirmed"))
    app.add_handler(CallbackQueryHandler(user_signin_up, pattern="^admin_payment_confirmed"))
    app.add_handler(CallbackQueryHandler(user_signin_up, pattern="^admin_payment_not_confirmed"))
    app.add_handler(CallbackQueryHandler(user_signin_up, pattern="^payment_not_confirmed"))
    app.add_handler(CallbackQueryHandler(user_signin_up, pattern="^payment_confirmed"))
    app.add_handler(CallbackQueryHandler(start, pattern="start_over"))

    # Handlers per la gestione delle richieste dal direttivo
    app.add_handler(CallbackQueryHandler(executive_handler, pattern="^restrict"))
    app.add_handler(CallbackQueryHandler(executive_handler, pattern="^not_restrict"))
    app.add_handler(CallbackQueryHandler(executive_handler, pattern="^close"))
    app.add_handler(CommandHandler("flagged", executive_handler))
    app.add_handler(CommandHandler("remove", executive_handler))

    # inscription_handler = ConversationHandler(
    #     entry_points=[CallbackQueryHandler(user_signin_up, pattern="^" + str(ISCRIZIONE) + "$")],
    #     states={
    #         ISCRIZIONE: [
    #             CallbackQueryHandler(user_signin_up, pattern="user_payment_confirmed"),
    #             CallbackQueryHandler(user_signin_up, pattern="user_payment_not_confirmed"),
    #             CallbackQueryHandler(user_signin_up, pattern="admin_payment_confirmed"),
    #             CallbackQueryHandler(user_signin_up, pattern="admin_payment_not_confirmed"),
    #             CallbackQueryHandler(user_signin_up, pattern="payment_not_confirmed")
    #         ]
    #     },
    #     fallbacks=[CallbackQueryHandler(start, pattern="start_over")]
    # )
    # app.add_handler(inscription_handler)
    app.run_polling()


if __name__ == "__main__":
    main()
