import os
import sqlite3
from shutil import copyfile

import bot_logic

class qa:
    def __init__(self, id, question, answer, nullForm=False):
        self.id = id
        self.answer = answer
        self.question = question
        if not nullForm:
            self.null_question = bot_logic.stringNullifier(question)
        else:
            self.null_question = question

    def __str__(self):
        return 'id=' + str(self.id) + ' || question=' + self.null_question + ' || answer= ' + self.answer


# при чтении если отсуствует элемент в null_questions сам его создает
def getListOfQAfromDB(path='QA.db'):
    # id[0] -> quesiton[1] -> answer[2] -> null_form_question[3]
    if not os.path.isfile(path):
        copyfile("backup\\QA_zero_backup.db", path)

    connection = sqlite3.connect(path)
    c = connection.cursor()

    out = []
    list_ = []
    for line in c.execute('''SELECT * FROM qa'''):
        list_.append(line)

    for row in list_:
        # qa(id, question, answer, nullQuestionGiven)
        if not row[3]:
            new_q = qa(row[0], row[1], row[2], nullForm=False)
            new_q.null_question = new_q.null_question.replace('"', '')
            new_q.null_question = new_q.null_question.replace('  ', ' ')
            c.execute(
                '''UPDATE qa SET null_question = %s WHERE id = %s''' % ('"' + new_q.null_question + '"', str(new_q.id)))
            connection.commit()
            out.append(new_q)
        else:
            out.append(qa(row[0], row[3], row[2], nullForm=True))
    connection.close()
    return out


def getNullQuestionsFromDB(path='QA.db'):
    null_q_arr = []
    for item in getListOfQAfromDB(path):
        null_q_arr.append(item.null_question.split(' '))
    return null_q_arr



def addNewQAtoBase(_qa, path='QA.db'):
    connection = sqlite3.connect(path)
    c = connection.cursor()
    c.execute('''INSERT OR IGNORE INTO qa (question, answer, null_question) VALUES (%s,%s,%s)''' % (
        '\'' + _qa.question + '\'', '\'' + _qa.answer + '\'', '\'' + _qa.null_question + '\''))
    connection.commit()
    connection.close()
    # доучиваем модель

    null_q_arr = getNullQuestionsFromDB()
    srcModel = bot_logic.trainModel('QA.w2v', null_q_arr, restart=True)
    targetModel = bot_logic.getQuestionModel(null_q_arr, srcModel, loadOldModel=False)
    return srcModel, targetModel


def removeQuestionFromDB(id, path='QA.db'):
    connection = sqlite3.connect(path)
    c = connection.cursor()
    c.execute('''DELETE FROM qa WHERE id = %s''' % (id,))
    connection.commit()
    connection.close()
    # доучиваем модель

    null_q_arr = getNullQuestionsFromDB()
    srcModel = bot_logic.trainModel('QA.w2v', null_q_arr, restart=True)
    targetModel = bot_logic.getQuestionModel(null_q_arr, srcModel, loadOldModel=False)
    return srcModel, targetModel


