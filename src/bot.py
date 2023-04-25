import logging
import os
from datetime import datetime, timedelta
import requests
import gzip
import shutil
from itertools import groupby
import pytz
import locale
import sqlite3
import validators
from urllib.parse import urlparse
import sys
import core_worker
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

init_questions=["Una ilustración o ejemplo para explicar algún punto principal del párrafo",
                "Una experiencia en concreto, aportando referencias exactas, que esté muy relacionada con el párrafo",
                "¿Qué me enseña este párrafo sobre Jehová?",
                "Una explicación sobre uno de los textos que aparezcan, que aplique al párrafo. Usa la Biblia de Estudio de los Testigos de Jehová.",
                "¿Cómo poner en práctica el contenido del párrafo?",
                "Algún comentario adicional que no responda la pregunta principal y que sea de utilidad"]

def all_equal(iterable):
    g = groupby(iterable)
    return next(g, True) and not next(g, False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("START - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4}".format(user.id, user.first_name, user.last_name, user.username, user.language_code))

    await update.message.reply_html(rf"""¡Bienvenido! 😊

Este bot le ayudará a prepararse las reuniones usando técnicas avanzadas de Inteligencia Artificial, aplicadas especialmente a la relación de datos en la literatura de la organización.

<u>El funcionamiento es el siguiente</u>:
  1. Introduzca la URL de jw.org de la Atalaya que quiera preparar con el comando /url [URL]
  2. Introduzca las preguntas que quiera hacer. Defina las preguntas y se aplicarán a <b>todos</b> los párrafos, con un máximo de 10. Por defecto, hay 6 preguntas incluidas. Se usa con /q1 [PREGUNTA_1], /q2 [PREGUNTA_2].... Para consultar las preguntas configuradas, usa /show_q
  3. Si no quiere perder datos, envíe su archivo de copia de seguridad de su aplicación de JW Library en formato <code>.jwlibrary</code> usando /send_backup y acto seguido enviando el archivo. Recomendamos que el artículo que quiera prepararse esté vacío para evitar problemas de posible corrupción de datos.
  4. Una vez haya elegido sus parámetros, ejecute /begin y espere unos minutos a que se genere el archivo <code>.jwlibrary</code>
  5. Descárguelo y restaure esta copia en su app JW Library.

<u>Repositorio oficial:</u> https://github.com/DrumSergio/jwlibrary-plus
<u>Descargo de Responsabilidad:</u> El software aquí presente se ofrece tal cual, sin ninguna garantía.
<u>Nota Importante:</u> Cada vez que ejecute /start , sus preguntas guardadas se <b>borrarán</b> y comenzará con las que el software ofrece por defecto.""")
    
    user_id = update.effective_user.id
    connection = sqlite3.connect("dbs/main.db")
    cursor = connection.cursor()
    cursor.execute("INSERT OR IGNORE INTO Main (UserId) VALUES ({0})".format(user_id))
    cursor.execute("UPDATE Main SET q1 = '{0}', q2 = '{1}', q3 = '{2}', q4 = '{3}', q5 = '{4}', q6 = '{5}', q7 = '', q8 = '', q9 = '', q10 = '' WHERE UserId = {6}".format(init_questions[0], init_questions[1], init_questions[2], init_questions[3], init_questions[4], init_questions[5], user_id))
    connection.commit()
    connection.close()


async def url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Testeando URL, espere por favor")
    url = context.args[0]
    user = update.effective_user
    logger.info("URL - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4} - URL: {5}".format(user.id, user.first_name, user.last_name, user.username, user.language_code, url))
    if(validators.url(url)):
        u = urlparse(url)
        if(u.netloc == "www.jw.org"):
            user_id = update.effective_user.id
            connection = sqlite3.connect("dbs/main.db")
            cursor = connection.cursor()
            cursor.execute("UPDATE Main SET Url = '{0}' WHERE UserId = {1}".format(url, user_id))
            connection.commit()
            connection.close()
            title, articleId, articleN = core_worker.extract_html("", url, get_all=False)
            articleNformatted = articleN.lower().split(" ")[-1]
            await update.message.reply_html("URL guardada.\nEn esta URL se encuentra la revista del año <b>{0}</b>, número <b>{1}</b>, artículo de estudio <b>{2}</b>.\nEl título de la Atalaya es <b>{3}</b>".format(articleId[:4], articleId[4:-2], articleNformatted, title))
        else:
            await update.message.reply_text("No es un una URL de www.jw.org")
    else:
        await update.message.reply_text("No es un una URL válida")


async def q1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = ' '.join(context.args[:]).replace('"', '').replace("'", "").replace(";", "").replace("(", "").replace(")", "") # TODO: Prevent user from messing with the input
    user = update.effective_user
    logger.info("Q1 - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4} - Question: {5}".format(user.id, user.first_name, user.last_name, user.username, user.language_code, question))
    if(len(question) < 200):
        user_id = update.effective_user.id
        connection = sqlite3.connect("dbs/main.db")
        cursor = connection.cursor()
        cursor.execute("UPDATE Main SET {0} = '{1}' WHERE UserId = {2}".format(sys._getframe().f_code.co_name, question, user_id))
        connection.commit()
        connection.close()
        await update.message.reply_text("Pregunta {0} guardada correctamente".format(sys._getframe().f_code.co_name[1:]))
    else:
        await update.message.reply_text("La pregunta debe tener menos de 200 caracteres")


async def q2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = ' '.join(context.args[:])
    user = update.effective_user
    logger.info("Q2 - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4} - Question: {5}".format(user.id, user.first_name, user.last_name, user.username, user.language_code, question))
    if(len(question) < 200):
        user_id = update.effective_user.id
        connection = sqlite3.connect("dbs/main.db")
        cursor = connection.cursor()
        cursor.execute("UPDATE Main SET {0} = '{1}' WHERE UserId = {2}".format(sys._getframe().f_code.co_name, question, user_id))
        connection.commit()
        connection.close()
        await update.message.reply_text("Pregunta {0} guardada correctamente".format(sys._getframe().f_code.co_name[1:]))
    else:
        await update.message.reply_text("La pregunta debe tener menos de 200 caracteres")
        

async def q3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = ' '.join(context.args[:])
    user = update.effective_user
    logger.info("Q3 - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4} - Question: {5}".format(user.id, user.first_name, user.last_name, user.username, user.language_code, question))
    if(len(question) < 200):
        user_id = update.effective_user.id
        connection = sqlite3.connect("dbs/main.db")
        cursor = connection.cursor()
        cursor.execute("UPDATE Main SET {0} = '{1}' WHERE UserId = {2}".format(sys._getframe().f_code.co_name, question, user_id))
        connection.commit()
        connection.close()
        await update.message.reply_text("Pregunta {0} guardada correctamente".format(sys._getframe().f_code.co_name[1:]))
    else:
        await update.message.reply_text("La pregunta debe tener menos de 200 caracteres")
        
        
async def q4(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = ' '.join(context.args[:])
    user = update.effective_user
    logger.info("Q4 - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4} - Question: {5}".format(user.id, user.first_name, user.last_name, user.username, user.language_code, question))
    if(len(question) < 200):
        user_id = update.effective_user.id
        connection = sqlite3.connect("dbs/main.db")
        cursor = connection.cursor()
        cursor.execute("UPDATE Main SET {0} = '{1}' WHERE UserId = {2}".format(sys._getframe().f_code.co_name, question, user_id))
        connection.commit()
        connection.close()
        await update.message.reply_text("Pregunta {0} guardada correctamente".format(sys._getframe().f_code.co_name[1:]))
    else:
        await update.message.reply_text("La pregunta debe tener menos de 200 caracteres")
        

async def q5(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = ' '.join(context.args[:])
    user = update.effective_user
    logger.info("Q5 - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4} - Question: {5}".format(user.id, user.first_name, user.last_name, user.username, user.language_code, question))
    if(len(question) < 200):
        user_id = update.effective_user.id
        connection = sqlite3.connect("dbs/main.db")
        cursor = connection.cursor()
        cursor.execute("UPDATE Main SET {0} = '{1}' WHERE UserId = {2}".format(sys._getframe().f_code.co_name, question, user_id))
        connection.commit()
        connection.close()
        await update.message.reply_text("Pregunta {0} guardada correctamente".format(sys._getframe().f_code.co_name[1:]))
    else:
        await update.message.reply_text("La pregunta debe tener menos de 200 caracteres")
        

async def q6(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = ' '.join(context.args[:])
    user = update.effective_user
    logger.info("Q6 - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4} - Question: {5}".format(user.id, user.first_name, user.last_name, user.username, user.language_code, question))
    if(len(question) < 200):
        user_id = update.effective_user.id
        connection = sqlite3.connect("dbs/main.db")
        cursor = connection.cursor()
        cursor.execute("UPDATE Main SET {0} = '{1}' WHERE UserId = {2}".format(sys._getframe().f_code.co_name, question, user_id))
        connection.commit()
        connection.close()
        await update.message.reply_text("Pregunta {0} guardada correctamente".format(sys._getframe().f_code.co_name[1:]))
    else:
        await update.message.reply_text("La pregunta debe tener menos de 200 caracteres")
        

async def q7(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = ' '.join(context.args[:])
    user = update.effective_user
    logger.info("Q7 - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4} - Question: {5}".format(user.id, user.first_name, user.last_name, user.username, user.language_code, question))
    if(len(question) < 200):
        user_id = update.effective_user.id
        connection = sqlite3.connect("dbs/main.db")
        cursor = connection.cursor()
        cursor.execute("UPDATE Main SET {0} = '{1}' WHERE UserId = {2}".format(sys._getframe().f_code.co_name, question, user_id))
        connection.commit()
        connection.close()
        await update.message.reply_text("Pregunta {0} guardada correctamente".format(sys._getframe().f_code.co_name[1:]))
    else:
        await update.message.reply_text("La pregunta debe tener menos de 200 caracteres")
        

async def q8(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = ' '.join(context.args[:])
    user = update.effective_user
    logger.info("Q8 - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4} - Question: {5}".format(user.id, user.first_name, user.last_name, user.username, user.language_code, question))
    if(len(question) < 200):
        user_id = update.effective_user.id
        connection = sqlite3.connect("dbs/main.db")
        cursor = connection.cursor()
        cursor.execute("UPDATE Main SET {0} = '{1}' WHERE UserId = {2}".format(sys._getframe().f_code.co_name, question, user_id))
        connection.commit()
        connection.close()
        await update.message.reply_text("Pregunta {0} guardada correctamente".format(sys._getframe().f_code.co_name[1:]))
    else:
        await update.message.reply_text("La pregunta debe tener menos de 200 caracteres")


async def q9(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = ' '.join(context.args[:])
    user = update.effective_user
    logger.info("Q9 - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4} - Question: {5}".format(user.id, user.first_name, user.last_name, user.username, user.language_code, question))
    if(len(question) < 200):
        user_id = update.effective_user.id
        connection = sqlite3.connect("dbs/main.db")
        cursor = connection.cursor()
        cursor.execute("UPDATE Main SET {0} = '{1}' WHERE UserId = {2}".format(sys._getframe().f_code.co_name, question, user_id))
        connection.commit()
        connection.close()
        await update.message.reply_text("Pregunta {0} guardada correctamente".format(sys._getframe().f_code.co_name[1:]))
    else:
        await update.message.reply_text("La pregunta debe tener menos de 200 caracteres")


async def q10(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    question = ' '.join(context.args[:])
    user = update.effective_user
    logger.info("Q10 - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4} - Question: {5}".format(user.id, user.first_name, user.last_name, user.username, user.language_code, question))
    if(len(question) < 200):
        user_id = update.effective_user.id
        connection = sqlite3.connect("dbs/main.db")
        cursor = connection.cursor()
        cursor.execute("UPDATE Main SET {0} = '{1}' WHERE UserId = {2}".format(sys._getframe().f_code.co_name, question, user_id))
        connection.commit()
        connection.close()
        await update.message.reply_text("Pregunta {0} guardada correctamente".format(sys._getframe().f_code.co_name[1:]))
    else:
        await update.message.reply_text("La pregunta debe tener menos de 200 caracteres")


async def show_q(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("SHOW_Q - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4}".format(user.id, user.first_name, user.last_name, user.username, user.language_code))
    
    user_id = update.effective_user.id
    connection = sqlite3.connect("dbs/main.db")
    cursor = connection.cursor()
    cursor.execute("SELECT q1,q2,q3,q4,q5,q6,q7,q8,q9,q10 FROM Main WHERE UserId = {0} LIMIT 1".format(user_id))
    data = cursor.fetchall()[0]
    connection.close()
    await update.message.reply_html("""<u>Tus preguntas actuales:</u>
1. {0}
2. {1}
3. {2}
4. {3}
5. {4}
6. {5}
7. {6}
8. {7}
9. {8}
10. {9}""". format(data[0],data[1],data[2],data[3],data[4],data[5],data[6],data[7],data[8],data[9]))


async def delete_q(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("DELETE_Q - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4}".format(user.id, user.first_name, user.last_name, user.username, user.language_code))
    
    connection = sqlite3.connect("dbs/main.db")
    cursor = connection.cursor()
    cursor.execute("UPDATE Main SET q1 = null, q2 = null, q3 = null, q4 = null, q5 = null, q6 = null, q7 = null, q8 = null, q9 = null, q10 = null WHERE UserId = '{0}'".format(user.id))
    connection.commit()
    connection.close()

    await update.message.reply_html("All questions were correctly unset")

# async def bulk_q(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None: # Not working because there is no \n in input
#     logger.info(context.args)
#     user = update.effective_user
#     questions_user = ' '.join(context.args[:]).replace('"', '').replace("'", "").replace(";", "").replace("(", "").replace(")", "") # TODO: Prevent user from messing with the input
#     logger.info("BULK_Q - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4} - Questions from User: {5}".format(user.id, user.first_name, user.last_name, user.username, user.language_code, questions_user))
    
#     connection = sqlite3.connect("dbs/main.db")
#     cursor = connection.cursor()

#     i=1
#     for q in questions_user.split("\n"):
#         if i < 11:
#             cursor.execute("UPDATE Main SET q{0} = '{1}' WHERE UserId = {2}".format(i, q, user.id))
#             i+=1
    
#     connection.commit()
#     connection.close()

#     await update.message.reply_text("Serie de preguntas guardadas con éxito")

async def send_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("SEND_BACKUP - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4}".format(user.id, user.first_name, user.last_name, user.username, user.language_code))
    
    await update.message.reply_html("Envíe su archivo <code>.jwlibrary</code> cuando desee, siempre será tomado en cuenta el último archivo que suba")


async def downloader(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    file = await context.bot.get_file(update.message.document)
    logger.info("SENDBACKUP - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4} - File ID: {5} - File Path: {6}".format(user.id, user.first_name, user.last_name, user.username, user.language_code, file.file_id, file.file_path))

    if(file.file_path.endswith(".jwlibrary")):
        await file.download_to_drive('/app/userBackups/{0}.jwlibrary'.format(user.id))
        await update.message.reply_text("Archivo correctamente subido y listo para utilizar")
    else:
        await update.message.reply_text("Formato de archivo erróneo")


async def delete_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("DELETE_BACKUP - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4}".format(user.id, user.first_name, user.last_name, user.username, user.language_code))
    
    os.remove('/app/userBackups/{0}.jwlibrary'.format(user.id))
    await update.message.reply_html("Archivo <code>.jwlibrary</code> eliminado del servidor")


async def describe_backup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("DESCRIBE_BACKUP - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4}".format(user.id, user.first_name, user.last_name, user.username, user.language_code))
    
    jwfile = "userBackups/{0}.jwlibrary".format(user.id)
    if os.path.isfile(jwfile):
        notesN, inputN, tagMaptN, tagN, bookmarkN, lastModified, userMarkN = core_worker.describe_jwlibrary(user.id)
        await update.message.reply_html("""Estado de su archivo <code>.jwlibrary</code>:
<u>Notas:</u> {0}
<u>Tags individuales:</u> {1}
<u>Notas con tags:</u> {2}
<u>Escritos en cuadros de texto:</u> {3}
<u>Favoritos:</u> {4}
<u>Frases subrayadas:</u> {5}
<u>Última vez modificado:</u> {6}""".format(notesN, tagN, tagMaptN, inputN, bookmarkN, userMarkN, lastModified))
    else:
        await update.message.reply_text("No se ha encontrado su archivo. El fichero se borra tras computar el resultado, envíelo de nuevo actualizado")


async def show_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("SHOW_URL - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4}".format(user.id, user.first_name, user.last_name, user.username, user.language_code))
    connection = sqlite3.connect("dbs/main.db")
    cursor = connection.cursor()
    cursor.execute("SELECT Url FROM Main WHERE UserId = {0} LIMIT 1".format(user.id))
    url = cursor.fetchall()[0][0]
    connection.close()

    logger.info(url)
    if url:
        await update.message.reply_html("La URL configurada es {0}".format(url))
    else:
        await update.message.reply_text("No hay URL configurada")


async def delete_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("DELETE_URL - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4}".format(user.id, user.first_name, user.last_name, user.username, user.language_code))
    
    connection = sqlite3.connect("dbs/main.db")
    cursor = connection.cursor()
    cursor.execute("SELECT Url FROM Main WHERE UserId = {0} LIMIT 1".format(user.id))
    url = cursor.fetchall()[0][0]

    if url:
        cursor.execute("UPDATE Main SET Url = null WHERE UserId = '{0}'".format(user.id))
        await update.message.reply_text("URL eliminada")
    else:
        await update.message.reply_text("URL no encontrada")
    connection.commit()
    connection.close()


async def select_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("SELECT_DATE - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4}".format(user.id, user.first_name, user.last_name, user.username, user.language_code))
    
    await delete_url(update, context)

    locale.setlocale(locale.LC_ALL, "es_ES") # TODO: Not working in Linux (but it does in Windows), asked in StackOverflow. locale.setlocale(locale.LC_ALL, user.language_code)
    now = datetime.now(pytz.timezone('Europe/Madrid')) # TODO: Check if UTC better
    start = now - timedelta(days=now.weekday())
    week_ranges = []

    for week in range(4):
        end = start + timedelta(days=6)
        if start.month == end.month:
            week_ranges.append(f"{start.strftime('%e')}-{end.strftime('%e de %B')}")
        else:
            week_ranges.append(f"{start.strftime('%e de %B')}-{end.strftime('%e de %B').strip()}")
        start = end + timedelta(days=1)

    keyboard = []
    for i, button in enumerate(week_ranges):
        keyboard.append([InlineKeyboardButton(button, callback_data=i)])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text('Elija fecha:', reply_markup=reply_markup)


async def select_date_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("SELECT_DATE_BUTTON - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4}".format(user.id, user.first_name, user.last_name, user.username, user.language_code))

    query = update.callback_query
    await query.answer()

    await query.edit_message_text(text=f"Opción seleccionada: {query.data}")
    connection = sqlite3.connect("dbs/main.db")
    cursor = connection.cursor()
    cursor.execute("UPDATE Main SET Date = {0} WHERE UserId = {1} LIMIT 1".format(query.data, user.id)) 
    connection.commit()
    connection.close()


async def show_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("SHOW_DATE - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4}".format(user.id, user.first_name, user.last_name, user.username, user.language_code))
    
    connection = sqlite3.connect("dbs/main.db")
    cursor = connection.cursor()
    cursor.execute("SELECT Date FROM Main WHERE UserId = {0} LIMIT 1".format(user.id))
    date = cursor.fetchall()[0][0]
    connection.close()

    if date:
        await update.message.reply_html("La semana configurada es la {0}".format(date)) # TODO: Actualmente solo responde 0, 1 ,2 o 3 dependiendo de la semana
    else:
        await update.message.reply_text("No hay semana configurada")


async def delete_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("DELETE_DATE - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4}".format(user.id, user.first_name, user.last_name, user.username, user.language_code))
    
    connection = sqlite3.connect("dbs/main.db")
    cursor = connection.cursor()
    cursor.execute("SELECT Date FROM Main WHERE UserId = {0} LIMIT 1".format(user.id))
    date = cursor.fetchall()[0][0]
    if date:
        cursor.execute("UPDATE Main SET Date = null WHERE UserId = '{0}'".format(user.id))
        await update.message.reply_text("Semana eliminada")
    else:
        await update.message.reply_text("Semana no encontrada")
    connection.commit()
    connection.close()


async def begin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    logger.info("BEGIN - User ID: {0} - First Name: {1} - Last Name: {2} - Username: {3} - Language Code: {4}".format(user.id, user.first_name, user.last_name, user.username, user.language_code))
 
    await update.message.reply_text("Comenzando. Podría tardar incluso más de 10 minutos dependiendo del número de preguntas y de la velocidad de respuesta de ChatGPT")
    user_id = update.effective_user.id
    connection = sqlite3.connect("dbs/main.db")
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM Main WHERE UserId = {0} LIMIT 1".format(user_id))
    data = cursor.fetchall()[0]
    connection.close()

    url = data[1]
    date = data[2]
    qs = data[3:]

    if any(qs):
        if url:
            filename = core_worker.main(url, date,user_id, qs) # Call to core_worker.py
            if(os.path.isfile('userBackups/{0}.jwlibrary'.format(user_id))):
                await update.message.reply_text("Aquí tiene su fichero, impórtelo a JW Library. Recuerde hacer una <b>copia de seguridad</b> para no perder los datos, ya que no ha proporcionado su archivo .jwlibrary")
            else:
                await update.message.reply_text("Aquí tiene su fichero, impórtelo a JW Library. Al haber proporcionado su copia de seguridad, puede estar seguro de que no perderá datos aun si se corrompiera su app, ya que dispone de cómo restaurarla")
            await update.message.reply_document(document=open(filename, "rb"))
            os.remove(filename)

        if date:
            now = datetime.now(pytz.timezone('Europe/Madrid')) # TODO: Check if UTC better
            start_date = now - timedelta(days=now.weekday()) + timedelta(date*7)
            sd_1 = start_date.strftime("%Y-%m-%d")
            sd_2 = (start_date - timedelta(7)).strftime("%Y-%m-%d")
            sd_3 = (start_date - timedelta(14)).strftime("%Y-%m-%d")
            sd_4 = (start_date - timedelta(21)).strftime("%Y-%m-%d")
            sd_5 = (start_date - timedelta(28)).strftime("%Y-%m-%d")


            jsonurl = requests.get("https://app.jw-cdn.org/catalogs/publications/v4/manifest.json")
            manifest_id = jsonurl.json()['current']
            catalog = requests.get("https://app.jw-cdn.org/catalogs/publications/v4/" + manifest_id + "/catalog.db.gz")
            open('catalog.db.gz', 'wb').write(catalog.content)
            with gzip.open("catalog.db.gz", "rb") as f:
                with open('dbs/catalog.db', 'wb') as f_out:
                    shutil.copyfileobj(f, f_out)
            connection = sqlite3.connect("dbs/catalog.db")
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM DatedText WHERE Class = 68 AND (Start = '{0}' OR Start = '{1}' OR Start = '{2}' OR Start = '{3}' OR Start = '{4}')".format(sd_1, sd_2, sd_3, sd_4, sd_5))
            datas = cursor.fetchall()

            if all_equal([x[1] for x in datas]):
                # get pubid
            else:
                # get pubid of the first or second item of set() https://stackoverflow.com/questions/12897374/get-unique-values-from-a-list-in-python
            cursor.execute("SELECT PublicationId FROM DatedText WHERE ")

        else:
            await update.message.reply_text("No ha seleccionado ninguna fecha o URL")
    else:
        await update.message.reply_text("Todas las preguntas están vacías")





def main() -> None:

    application = Application.builder().token(os.environ["TOKEN"]).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("url", url))
    application.add_handler(CommandHandler("q1", q1))
    application.add_handler(CommandHandler("q2", q2))
    application.add_handler(CommandHandler("q3", q3))
    application.add_handler(CommandHandler("q4", q4))
    application.add_handler(CommandHandler("q5", q5))
    application.add_handler(CommandHandler("q6", q6))
    application.add_handler(CommandHandler("q7", q7))
    application.add_handler(CommandHandler("q8", q8))
    application.add_handler(CommandHandler("q9", q9))
    application.add_handler(CommandHandler("q10", q10))
    application.add_handler(CommandHandler("show_q", show_q))
    application.add_handler(CommandHandler("delete_q", delete_q))
    #application.add_handler(CommandHandler("bulk_q", bulk_q)) # TODO: No funciona \n
    application.add_handler(CommandHandler("send_backup", send_backup))
    application.add_handler(MessageHandler(filters.Document.ALL, downloader))
    application.add_handler(CommandHandler("describe_backup", describe_backup))
    application.add_handler(CommandHandler("delete_backup", delete_backup))
    application.add_handler(CommandHandler("show_url", show_url))
    application.add_handler(CommandHandler("delete_url", delete_url))
    application.add_handler(CommandHandler("select_date", select_date))
    application.add_handler(CallbackQueryHandler(select_date_button))
    application.add_handler(CommandHandler("show_date", show_date))
    application.add_handler(CommandHandler("delete_date", delete_date))
    # TODO: Hacer filter para URL pillar todo
    application.add_handler(CommandHandler("begin", begin))

    application.run_polling()

if __name__ == "__main__":
    main()