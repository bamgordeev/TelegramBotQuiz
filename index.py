#telegram-bot Bot Cloud Quizes for Yandex.Cloud CloudFunction

import telebot
from telebot import types
import json
import db_utils as db
import psycopg2 as sql
import copy

# import message_handler
import random


# Telegram Access
token = "6661386149:AAEQm0gZAf2qz9c1ncpHSm2Zqp9Ti7cT6wg"
bot = telebot.TeleBot(token, threaded=False)

conn = None
users = []
create_quiz_data = {}
take_quiz_data = {}

view_quiz = []

users = None
quizes_data = {
    100: None
}
quizes_results = {
    100: None
}





# Cloud Function Handler
def handler(event,context):
    global conn
    global quizes_data
    global quizes_results
    global users

    conn = db.open_connection(event, context)
    quizes_data.update(db.init_quizes_data(conn))
    quizes_results.update(db.init_quizes_results(conn, 100))
    users = db.select_all_users(conn)


    body = json.loads(event['body'])
    update = telebot.types.Update.de_json(body)
    bot.process_new_updates([update])

# Buttons
button_choose_quiz = types.KeyboardButton('Пройти опросы')
button_manage_quiz = types.KeyboardButton('Управление опросами')

button_view_statistics = types.KeyboardButton('Cтатистика')
button_create_quiz = types.KeyboardButton('Создать опрос')


button_take_quiz = types.KeyboardButton('Начать')
button_back_to_start = types.KeyboardButton('Назад')


# Keyboards
keyboard_start = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
keyboard_start.add(button_choose_quiz, button_manage_quiz)

keyboard_manage_quiz = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
keyboard_manage_quiz.add(button_view_statistics, button_create_quiz, button_back_to_start)

keyboard_take_quiz = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
keyboard_take_quiz.add(button_take_quiz, button_back_to_start)

keyboard_back_to_main = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
keyboard_back_to_main.add(button_back_to_start)

# TEMPLATES
msg_template = {
    'chat_id': None,
    'text': None,
    'reply_markup': None
}


# TEST
@bot.message_handler(commands=['test'])
def test_message(message):
    bot.send_message(chat_id=message.chat.id, text=f'{quizes_data}')

# Start
@bot.message_handler(commands=['start'])
def start_helper(message):
    global conn
    try:
        if conn == None:
            conn = db.open_connection1()
        if message.chat.id not in users:
            db.insert_user(conn, (message.from_user.id, message.chat.id))
            users.append(message.chat.id)
    except (Exception, sql.DatabaseError) as err:
        bot.send_message(message.chat.id, f'Чето не так с БД: {err}')

    start_message = f'Привет!🖐️ Я бот-опросник. Благодаря мне ты можешь создавать и проходить опросы.\n'
    start_message += f'🔎Все ответы, разумеется, остаются анонимными🔎'
    bot.send_message(chat_id=message.chat.id, text=start_message, reply_markup=keyboard_start)


@bot.message_handler(regexp="Управление опросами")
def manage_quiz(message):
    msg_data = copy.deepcopy(msg_template)
    msg_data['chat_id'] = message.chat.id
    msg_data['text'] = 'Вы можете управлять опросами!'
    msg_data['reply_markup'] = keyboard_manage_quiz
    send_message(msg_data)

@bot.message_handler(regexp="Назад")
def back_to_start_menu(message):
    chat_id = message.chat.id
    clear_states(chat_id)
    msg_data = copy.deepcopy(msg_template)
    msg_data['chat_id'] = chat_id
    msg_data['text'] = 'Главное меню'
    msg_data['reply_markup'] = keyboard_start
    send_message(msg_data)

@bot.message_handler(regexp="Начать")
def begin_quiz(message):
    chat_id = message.chat.id
    take_quiz_data[chat_id]['temp_question'] = 1
    take_quiz_data[chat_id]['take_state'] = 2
    bot.send_message(chat_id, '⚡Начинаем⚡', reply_markup=keyboard_back_to_main)
    handle_update(message)

@bot.message_handler(regexp="Cтатистика")
def get_statistic(message):
    chat_id = message.chat.id
    view_quiz.append(chat_id)
    topics = get_own_quizes_topic(chat_id)
    if topics != '':
        answer = '👇ВЫБЕРИТЕ НОМЕР ВАШЕГО ОПРОСА👇\n\n' + topics
    else:
        answer = 'Вы ещё не создали ни одного опроса!!!😒'
    bot.send_message(chat_id, answer)
    #handle_update(message)


# MAIN HANDLER ----------------------------------------------------------------------------------------
@bot.message_handler(content_types=["text"])
def handle_update(message):
    chat_id = message.chat.id
    msg_data = copy.deepcopy(msg_template)
    try:
        msg_data['chat_id'] = chat_id
        msg_data['text'], msg_data['reply_markup'] = answer_message(chat_id, message.text)
        send_message(msg_data)
    except Exception as err:
        bot.send_message(chat_id=message.chat.id, text=f'Что-то пошло не так: {err}')


# MAIN WORKER ------------------------------------------------------------------------------------------
def answer_message(chat_id, text):
    answer = 'None'
    reply_markup = None
    if text == 'Создать опрос':
        clear_states(chat_id)
        create_quiz_data[chat_id] = {'create_state': 1}
        answer = f'Введите название опроса'
    elif text == 'Пройти опросы':
        clear_states(chat_id)
        take_quiz_data[chat_id] = {'take_state': 1}
        answer = f'👇ВЫБЕРИТЕ НОМЕР ОПРОСА👇\n\n' + get_quizes_topics()
    elif chat_id in view_quiz:
        quiz_id = 100 + int(text)
        statistic = calculate_statistics(quiz_id)
        if statistic != False:
            show_statistics(chat_id, statistic)
            view_quiz.remove(chat_id)
            answer = f'Это конец✔️'
        else:
            answer = f'Пока ещё никто не прошел этот опрос😭'
    elif chat_id in create_quiz_data.keys():
        #answer = f'{create_quiz_data}'
        match create_quiz_data[chat_id]['create_state']:
            case 1:
                create_quiz_data[chat_id]['topic'] = text
                create_quiz_data[chat_id]['create_state'] = 2
                answer = 'Введите количество вопросов'
            case 2:
                create_quiz_data[chat_id]['questions_amount'] = int(text)
                create_quiz_data[chat_id]['temp_input_question'] = 1
                create_quiz_data[chat_id]['questions'] = {}
                create_quiz_data[chat_id]['create_state'] = 3
                answer = f'Введите текст вопроса номер 1'
            case 3:
                question_number = create_quiz_data[chat_id]['temp_input_question']
                create_quiz_data[chat_id]['last_input_question'] = text
                create_quiz_data[chat_id]['questions'][text] = {}
                create_quiz_data[chat_id]['create_state'] = 4
                answer = f'Введите количество вариантов ответов на данный вопрос'
            case 4:
                last_input_question = create_quiz_data[chat_id]['last_input_question']
                create_quiz_data[chat_id]['questions'][last_input_question]['options'] = {}
                create_quiz_data[chat_id]['questions'][last_input_question]['options_amount'] = int(text)
                create_quiz_data[chat_id]['questions'][last_input_question]['temp_input_option'] = 1
                create_quiz_data[chat_id]['create_state'] = 5
                answer = f'Введите текст варианта ответа номер 1'
            case 5:
                last_input_question = create_quiz_data[chat_id]['last_input_question']
                options_amount = create_quiz_data[chat_id]['questions'][last_input_question]['options_amount']
                temp_input_option = create_quiz_data[chat_id]['questions'][last_input_question]['temp_input_option']

                questions_amount = create_quiz_data[chat_id]['questions_amount']
                temp_input_question = create_quiz_data[chat_id]['temp_input_question']
            
                create_quiz_data[chat_id]['questions'][last_input_question]['options'][temp_input_option] = text
                create_quiz_data[chat_id]['questions'][last_input_question]['temp_input_option'] += 1
                answer = f'Введите текст варианта ответа номер {temp_input_option + 1}'

                if temp_input_option + 1 > options_amount:
                    if temp_input_question + 1 <= questions_amount:
                        create_quiz_data[chat_id]['temp_input_question'] += 1
                        create_quiz_data[chat_id]['create_state'] = 3
                        answer = f'Введите текст вопроса номер {temp_input_question + 1}'
                    else:
                        add_new_quiz_data(chat_id, create_quiz_data[chat_id])
                        create_quiz_data.pop(chat_id)
                        answer = f'Опрос успешно создан и опубликован!'
                        reply_markup = keyboard_start
    elif chat_id in take_quiz_data.keys():
        match take_quiz_data[chat_id]['take_state']:
            case 1:
                try:
                    choosen_quiz = 100 + int(text)
                except ValueError:
                    return ('Ожидается номер опроса', reply_markup)    

                take_quiz_data[chat_id]['choosen_quiz'] = choosen_quiz
                answer = quiz_info(choosen_quiz)
                reply_markup = keyboard_take_quiz
            case 2:
                choosen_quiz = take_quiz_data[chat_id]['choosen_quiz']
                take_quiz_data[chat_id]['take_state'] = 3
                take_quiz_data[chat_id]['selections'] = {}
                answer = question_info(take_quiz_data[chat_id]['temp_question'], take_quiz_data[chat_id]['choosen_quiz'])
            case 3:
                try:
                    select_option = int(text)
                except ValueError:
                    return ('Ожидается номер ответа', reply_markup)
                

                temp_question = take_quiz_data[chat_id]['temp_question']
                choosen_quiz = take_quiz_data[chat_id]['choosen_quiz']

                if select_option > quizes_data[choosen_quiz]['questions'][temp_question]['options_amount']:
                    return ('❌Нет такого варианта ответа❌', reply_markup)

                take_quiz_data[chat_id]['selections'][temp_question] = select_option
                
                if temp_question + 1 <= quizes_data[choosen_quiz]['questions_amount']:
                    take_quiz_data[chat_id]['temp_question'] += 1
                    answer = question_info(temp_question + 1, choosen_quiz)
                else:
                    #bot.send_message(chat_id, f'{take_quiz_data}')
                    add_new_quiz_result(chat_id, take_quiz_data[chat_id])
                    take_quiz_data.pop(chat_id)
                    answer = '🔥Спасибо за прохождение опроса🔥'
                    reply_markup = keyboard_start

    return (answer, reply_markup)


# Parse data -------------------------------------------------------------------------------------------
def add_new_quiz_data(chat_id, create_data):
    new_quiz_id = max(quizes_data.keys()) + 1
    new_quiz_data = {
        'owner': chat_id,
        'topic': create_data['topic'],
        'questions_amount': create_data['questions_amount'],
        'questions': {}
    }

    current_question = 1
    for key, val in create_data['questions'].items():
        if key not in ('options_amount', 'temp_input_option'):
            new_quiz_data['questions'][current_question] = {'text': key, 'options_amount': val['options_amount']}
            new_quiz_data['questions'][current_question]['options'] = copy.deepcopy(val['options'])
            current_question += 1

    quizes_data[new_quiz_id] = copy.deepcopy(new_quiz_data)
    db.insert_quiz(conn, new_quiz_id, new_quiz_data)


# Parse result --------------------------------------------------------------------------------------------
def add_new_quiz_result(chat_id, result_data):
    new_quiz_result_id = max(quizes_results.keys()) + 1
    new_quiz_result = {
        'owner': chat_id,
        'quiz_id': result_data['choosen_quiz'],
        'selections': {}
    }

    questions_matching = db.select_questions_matching(conn, result_data['choosen_quiz'])
    optoins_matching = db.select_options_matching(conn, result_data['choosen_quiz'])
    for key, val in result_data['selections'].items():
        qstn_id = questions_matching[key]
        optn_id = None
        for optn_rn, p_optn_id, qstn_qstn_id in optoins_matching:
            if optn_rn == val and qstn_qstn_id == qstn_id:
                optn_id = p_optn_id
                break
        new_quiz_result['selections'][qstn_id] = optn_id
    

    quizes_results[new_quiz_result_id] = copy.deepcopy(new_quiz_result)
    db.insert_quiz_result(conn, new_quiz_result)
    



# Usefull defintions -----------------------------------------------------------------------------------------
def get_quizes_topics():
    topics = ''
    for key, val in quizes_data.items():
        if val == None:
            continue
        topics += f'{key-100}. {val["topic"]}\n'
    return topics

def get_own_quizes_topic(usr_id):
    topics = ''
    for key, val in quizes_data.items():
        if val == None:
            continue
        # if val['owner'] == usr_id:
        topics += f'{key-100}. {val["topic"]}\n'
    return topics

def clear_states(chat_id):
    if chat_id in create_quiz_data.keys():
        create_quiz_data.pop(chat_id)
    if chat_id in take_quiz_data.keys():
        take_quiz_data.pop(chat_id)
    if chat_id in view_quiz:
        view_quiz.remove(chat_id)


def quiz_info(choosen_quiz):
    
    def average_time(questions_amount):
        time = '0'
        if 1 <= questions_amount <= 5:
            time = '3-5'
        elif 6 <= questions_amount <= 10:
            time = '5-10'
        elif 11 <= questions_amount <= 20:
            time = '10-15'
        else:
            time = '15+'
        return time

    info = "👉КРАТКАЯ ИНФОРМАЦИЯ ОБ ОПРОСЕ👈\n\n"
    info += f'Тема опроса: {quizes_data[choosen_quiz]["topic"]}\n'
    info += f'Количество вопросов: {quizes_data[choosen_quiz]["questions_amount"]}\n'
    info += f'Время прохождения: {average_time(quizes_data[choosen_quiz]["questions_amount"])} мин.'
    return info


def question_info(number, quiz_id):
    question =  f'ВОПРОС {number}✍🏻\n\n'
    question += f'{quizes_data[quiz_id]["questions"][number]["text"]}\n'
    for key, val in quizes_data[quiz_id]["questions"][number]["options"].items():
        question += f'  {key}. {val}\n'
    return question
    
    
def calculate_statistics(quiz_id):
    all_pass = 0
    selections = {}
    for result in quizes_results.values():
        if result == None: 
            continue
        if result['quiz_id'] == quiz_id:
            all_pass += 1
            for qstn_id, optn_id in result['selections'].items():
                if (qstn_id, optn_id) in selections.keys():
                    selections[(qstn_id, optn_id)] += 1
                else:
                    selections[(qstn_id, optn_id)] = 1

    if all_pass == 0:
        return False

    matching = db.select_question_option_from_quiz_id(conn, quiz_id)
    questions_names = db.select_questions_from_quiz_id(conn, quiz_id)
    options_names = db.select_optinons_from_quiz_id(conn, quiz_id)
    statistic = {}
    last_qstn_id = None
    temp_qstn_text = None
    for qstn_id, optn_id in matching:
        if qstn_id != last_qstn_id:
            temp_qstn_text = questions_names[qstn_id]
            statistic[temp_qstn_text] = {}
            last_qstn_id = qstn_id

        if (qstn_id, optn_id) in selections.keys():
            statistic[temp_qstn_text][options_names[optn_id]] = (selections[(qstn_id, optn_id)] / all_pass) * 100
        else:
            statistic[temp_qstn_text][options_names[optn_id]] = 0

    return statistic


def show_statistics(chat_id, statistic):
    question_counter = 1
    for question, options in statistic.items():
        msg = f'❗ВОПРОС {question_counter}❗\n\n'
        msg += f'{question}\n'
        option_counter = 1
        for option, stat in options.items():
            msg += f'\t{option_counter}. {option}  ➡  {stat}%\n'
            option_counter += 1
        bot.send_message(chat_id, msg)
        question_counter += 1




'''
# Send photo
@bot.message_handler(regexp="Хочу котиков")
def send_kitty(message):
    file = str(random.randint(1,10))+'.jpg'
    photo = 'BUCKET_URL' + file
    send_photo(msg_id=message.chat.id, photo=photo, reply_markup=keyboard_continue)
'''

def send_message(data):
    bot.send_message(chat_id=data['chat_id'], text=data['text'], reply_markup=data['reply_markup'])
