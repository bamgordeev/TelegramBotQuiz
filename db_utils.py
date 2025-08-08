import psycopg2 as sql


def open_connection(event, context):
    conn = sql.connect(
        database="akfajrdgktu4n620smh0", # Идентификатор подключения
        user="user1", # Пользователь БД
        password=context.token["access_token"],
        host="akfajrdgktu4n620smh0.postgresql-proxy.serverless.yandexcloud.net", # Точка входа
        port=6432,
        sslmode="require")
    return conn


def open_connection1():
    #conn = sql.connect('host=rc1b-hx81zvl5sv3qa4v0.mdb.yandexcloud.net port=6432 dbname=postgres-bot-bd-1 user=user1 password=13371488')
    '''conn = sql.connect(
        database="c9qhh7qeciqbbjf42o05", # Идентификатор подключения
        user="user1", # Пользователь БД
        password=13371488,
        host="c9qhh7qeciqbbjf42o05.postgresql-proxy.serverless.yandexcloud.net", # Точка входа
        port=6432,
        sslmode="verify-full")'''
    conn = sql.connect("host=185.241.194.50 dbname=PostgreSQL-5373 user=user password=x&133Hq99PZ1Vh73d")
    return conn

# Selects -----------------------------------------------------------------------------------------------------------------------
def select_all_users(conn):
    cur = conn.cursor()
    cur.execute('SELECT chat_id FROM Users')
    users = []
    for user in cur.fetchall():
        users.append(user[0])
    return users


def select_questions_matching(conn, quiz_id):
    cur = conn.cursor()
    cur.execute(f'SELECT row_number() over (order by qstn_id) as qstn_rn, qstn_id FROM Questions WHERE quiz_quiz_id = {quiz_id}')
    data = cur.fetchall()
    
    questions_matching = {}
    for matching in data:
        questions_matching[matching[0]] = matching[1]
    return questions_matching



def select_options_matching(conn, quiz_id):
    cur = conn.cursor()
    cur.execute(f'''
        SELECT row_number() over(PARTITION BY op.qstn_qstn_id order by op.optn_id) as optn_rn, 
            op.optn_id, 
            op.qstn_qstn_id 
        FROM Options op
        JOIN Questions qs ON qs.qstn_id = op.qstn_qstn_id
        WHERE qs.quiz_quiz_id = {quiz_id}
    ''')
    option_question_matching = cur.fetchall()
    return option_question_matching


def select_questions_from_quiz_id(conn, quiz_id):
    cur = conn.cursor()
    cur.execute(f'SELECT qstn_id, text FROM Questions WHERE quiz_quiz_id = {quiz_id}')
    matching = cur.fetchall()

    data = {}
    for match in matching:
        data[match[0]] = match[1]
    return data


def select_optinons_from_quiz_id(conn, quiz_id):
    cur = conn.cursor()
    cur.execute(f'''
        SELECT op.optn_id, op.text FROM Options op
        JOIN Questions qt ON qt.qstn_id = op.qstn_qstn_id
        WHERE qt.quiz_quiz_id = {quiz_id}
    ''')
    matching = cur.fetchall()

    data = {}
    for match in matching:
        data[match[0]] = match[1]
    return data


def select_question_option_from_quiz_id(conn, quiz_id):
    cur = conn.cursor()
    cur.execute(f'''        
        SELECT qt.qstn_id, op.optn_id FROM Questions qt
        JOIN Options op ON op.qstn_qstn_id = qt.qstn_id
        WHERE qt.quiz_quiz_id = {quiz_id}
    ''')
    matching = cur.fetchall()
    return matching


# Initialization data ------------------------------------------------------------------------------------------------------------
def init_quizes_data(conn):
    if conn == None:
        conn = open_connection1()
    cur = conn.cursor()

    cur.execute('SELECT * FROM Quizes')
    quizes = cur.fetchall()

    data = {}
    for quiz in quizes:
        quiz_id = quiz[0]
        data[quiz_id] = {'owner': quiz[1], 'topic': quiz[2], 'questions_amount': quiz[3], 'questions': {}}
    
        cur.execute(f'SELECT * FROM Questions WHERE quiz_quiz_id = {quiz_id}')
        questions = cur.fetchall()
        question_counter = 1
        for question in questions:
            qstn_id = question[0]
            data[quiz_id]['questions'][question_counter] = {'text': question[2], 'options_amount': None, 'options': {}}

            cur.execute(f'SELECT * FROM Options WHERE qstn_qstn_id = {qstn_id}')
            options = cur.fetchall()
            options_counter = 1
            for option in options:
                data[quiz_id]['questions'][question_counter]['options'][options_counter] = option[2]
                options_counter += 1

            data[quiz_id]['questions'][question_counter]['options_amount'] = options_counter - 1
            question_counter += 1
    
    return data            



def init_quizes_results(conn, last_result_id):
    if conn == None:
        conn = open_connection1()
    cur = conn.cursor()

    cur.execute('SELECT DISTINCT usr_usr_id, quiz_quiz_id FROM quizes_results')
    quizes_results = cur.fetchall()

    data = {}
    temp_result_id = last_result_id
    for result in quizes_results:
        data[temp_result_id] = {}
        data[temp_result_id]['owner'] = result[0]
        data[temp_result_id]['quiz_id'] = result[1]
        data[temp_result_id]['selections'] = {}
        
        cur1 = conn.cursor()
        cur1.execute(f"""
            SELECT qstn_qstn_id, optn_optn_id FROM quizes_results
            WHERE usr_usr_id = {result[0]} and quiz_quiz_id = {result[1]};
        """)
        for qstn_id, optn_id in cur1.fetchall():
            data[temp_result_id]['selections'][qstn_id] = optn_id
        temp_result_id += 1
    return data    




# Inserts -------------------------------------------------------------------------------------------------------------------------
def insert_user(conn, params):
    cur = conn.cursor()
    cur.execute(f'INSERT INTO Users VALUES ({params[0]}, {params[1]})')
    conn.commit()


def insert_quiz(conn, quiz_id, quiz):
    if conn == None: 
        conn = open_connection1()
    cur = conn.cursor()
    cur.execute(f"INSERT INTO Quizes VALUES ({quiz_id}, {quiz['owner']}, '{quiz['topic']}', {quiz['questions_amount']})")
    conn.commit()

    for i in range(1, quiz['questions_amount'] + 1):
        cur.execute(f"INSERT INTO Questions(quiz_quiz_id, text) VALUES ({quiz_id}, '{quiz['questions'][i]['text']}')")
        conn.commit()

        cur.execute('SELECT max(qstn_id) FROM Questions')
        qstn_id, = cur.fetchone()

        for j in range(1, quiz['questions'][i]['options_amount'] + 1):
            cur.execute(f"INSERT INTO Options(qstn_qstn_id, text) VALUES ({qstn_id}, '{quiz['questions'][i]['options'][j]}')")
            conn.commit()
        

def insert_quiz_result(conn, result):
    if conn == None: 
        conn = open_connection1()
    cur = conn.cursor()
    
    owner = result['owner']
    quiz_id = result['quiz_id']
    for qstn_id, optn_id in result['selections'].items():
        cur.execute(f"""
            INSERT INTO Quizes_results (usr_usr_id, quiz_quiz_id, qstn_qstn_id, optn_optn_id) 
            VALUES ({owner}, {quiz_id}, {qstn_id}, {optn_id})
        """)
        conn.commit()
