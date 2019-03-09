from __future__ import print_function
from __future__ import division

import sys
from pathlib import Path

import numpy
import wget as wget
from numpy import dot
from gensim import matutils
from gensim.models import Word2Vec
from ufal.udpipe import Model, Pipeline
import codecs
import os
import re


########################################################################################################################
# This is RusVectores code from https://github.com/akutuzov/webvectors/blob/master/preprocessing/rus_preprocessing_udpipe.py
#
# Kutuzov A., Kuzmenko E. (2017) WebVectors: A Toolkit for Building Web Interfaces for Vector Semantic Models. In: Ignatov D. et al.
# (eds) Analysis of Images, Social Networks and Texts. AIST 2016. Communications in Computer and Information Science, vol 661. Springer, Cham
#######################################################################################################################
def list_replace(search, replacement, text):
    search = [el for el in search if el in text]
    for c in search:
        text = text.replace(c, replacement)
    return text


def unify_sym(text):  # принимает строку в юникоде
    text = list_replace \
        ('\u00AB\u00BB\u2039\u203A\u201E\u201A\u201C\u201F\u2018\u201B\u201D\u2019', '\u0022', text)

    text = list_replace \
        ('\u2012\u2013\u2014\u2015\u203E\u0305\u00AF', '\u2003\u002D\u002D\u2003', text)

    text = list_replace('\u2010\u2011', '\u002D', text)

    text = list_replace \
            (
            '\u2000\u2001\u2002\u2004\u2005\u2006\u2007\u2008\u2009\u200A\u200B\u202F\u205F\u2060\u3000',
            '\u2002', text)

    text = re.sub('\u2003\u2003', '\u2003', text)
    text = re.sub('\t\t', '\t', text)

    text = list_replace \
            (
            '\u02CC\u0307\u0323\u2022\u2023\u2043\u204C\u204D\u2219\u25E6\u00B7\u00D7\u22C5\u2219\u2062',
            '.', text)

    text = list_replace('\u2217', '\u002A', text)

    text = list_replace('…', '...', text)

    text = list_replace('\u2241\u224B\u2E2F\u0483', '\u223D', text)

    text = list_replace('\u00C4', 'A', text)  # латинская
    text = list_replace('\u00E4', 'a', text)
    text = list_replace('\u00CB', 'E', text)
    text = list_replace('\u00EB', 'e', text)
    text = list_replace('\u1E26', 'H', text)
    text = list_replace('\u1E27', 'h', text)
    text = list_replace('\u00CF', 'I', text)
    text = list_replace('\u00EF', 'i', text)
    text = list_replace('\u00D6', 'O', text)
    text = list_replace('\u00F6', 'o', text)
    text = list_replace('\u00DC', 'U', text)
    text = list_replace('\u00FC', 'u', text)
    text = list_replace('\u0178', 'Y', text)
    text = list_replace('\u00FF', 'y', text)
    text = list_replace('\u00DF', 's', text)
    text = list_replace('\u1E9E', 'S', text)

    currencies = list \
            (
            '\u20BD\u0024\u00A3\u20A4\u20AC\u20AA\u2133\u20BE\u00A2\u058F\u0BF9\u20BC\u20A1\u20A0\u20B4\u20A7\u20B0\u20BF\u20A3\u060B\u0E3F\u20A9\u20B4\u20B2\u0192\u20AB\u00A5\u20AD\u20A1\u20BA\u20A6\u20B1\uFDFC\u17DB\u20B9\u20A8\u20B5\u09F3\u20B8\u20AE\u0192'
        )

    alphabet = list \
            (
            '\t\n\r абвгдеёзжийклмнопрстуфхцчшщьыъэюяАБВГДЕЁЗЖИЙКЛМНОПРСТУФХЦЧШЩЬЫЪЭЮЯ,.[]{}()=+-−*&^%$#@!~;:0123456789§/\|"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ')

    alphabet.append("'")

    allowed = set(currencies + alphabet)

    cleaned_text = [sym for sym in text if sym in allowed]
    cleaned_text = ''.join(cleaned_text)

    return cleaned_text


def process(pipeline, text='Строка', keep_pos=True, keep_punct=False):
    # Если частеречные тэги не нужны (например, их нет в модели), выставьте pos=False
    # в этом случае на выход будут поданы только леммы
    # По умолчанию знаки пунктуации вырезаются. Чтобы сохранить их, выставьте punct=True

    entities = {'PROPN'}
    named = False
    memory = []
    mem_case = None
    mem_number = None
    tagged_propn = []

    # обрабатываем текст, получаем результат в формате conllu:
    processed = pipeline.process(text)

    # пропускаем строки со служебной информацией:
    content = [l for l in processed.split('\n') if not l.startswith('#')]

    # извлекаем из обработанного текста леммы, тэги и морфологические характеристики
    tagged = [w.split('\t') for w in content if w]

    for t in tagged:
        if len(t) != 10:
            continue
        (word_id, token, lemma, pos, xpos, feats, head, deprel, deps, misc) = t
        token = clean_token(token, misc)
        lemma = clean_lemma(lemma, pos)
        if not lemma or not token:
            continue
        if pos in entities:
            if '|' not in feats:
                tagged_propn.append('%s' % (lemma))
                continue
            morph = {el.split('=')[0]: el.split('=')[1] for el in feats.split('|')}
            if 'Case' not in morph or 'Number' not in morph:
                tagged_propn.append('%s' % (lemma))
                continue
            if not named:
                named = True
                mem_case = morph['Case']
                mem_number = morph['Number']
            if morph['Case'] == mem_case and morph['Number'] == mem_number:
                memory.append(lemma)
                if 'SpacesAfter=\\n' in misc or 'SpacesAfter=\s\\n' in misc:
                    named = False
                    past_lemma = '::'.join(memory)
                    memory = []
                    tagged_propn.append(past_lemma)
            else:
                named = False
                past_lemma = '::'.join(memory)
                memory = []
                tagged_propn.append(past_lemma)
                tagged_propn.append('%s' % (lemma))
        else:
            if not named:
                if pos == 'NUM' and token.isdigit():  # Заменяем числа на xxxxx той же длины
                    lemma = num_replace(token)
                tagged_propn.append('%s' % (lemma))
            else:
                named = False
                past_lemma = '::'.join(memory)
                memory = []
                tagged_propn.append(past_lemma)
                tagged_propn.append('%s' % (lemma))

    if not keep_pos:
        tagged_propn = [word.split('_')[0] for word in tagged_propn]
    return tagged_propn


def num_replace(word):
    newtoken = 'x' * len(word)
    return newtoken


def clean_token(token, misc):
    """
    :param token:  токен (строка)
    :param misc:  содержимое поля "MISC" в CONLLU (строка)
    :return: очищенный токен (строка)
    """
    out_token = token.strip().replace(' ', '')
    if token == 'Файл' and 'SpaceAfter=No' in misc:
        return None
    return out_token


def clean_lemma(lemma, pos):
    """
    :param lemma: лемма (строка)
    :param pos: часть речи (строка)
    :return: очищенная лемма (строка)
    """
    out_lemma = lemma.strip().replace(' ', '').replace('_', '').lower()
    if '|' in out_lemma or out_lemma.endswith('.jpg') or out_lemma.endswith('.png'):
        return None
    if pos != 'PUNCT':
        if out_lemma.startswith('«') or out_lemma.startswith('»'):
            out_lemma = ''.join(out_lemma[1:])
        if out_lemma.endswith('«') or out_lemma.endswith('»'):
            out_lemma = ''.join(out_lemma[:-1])
        if out_lemma.endswith('!') or out_lemma.endswith('?') or out_lemma.endswith(',') \
                or out_lemma.endswith('.'):
            out_lemma = ''.join(out_lemma[:-1])
    return out_lemma


########################################################################################################################
# End of RusVectores code
########################################################################################################################


def stringNullifier(str):
    # print('simplify to null form: ', str)
    # URL of the UDPipe model
    udpipe_model_url = 'https://rusvectores.org/static/models/udpipe_syntagrus.model'

    if not os.path.isfile('udpipe_syntagrus.model'):
        print('UDPipe model not found. Downloading...', file=sys.stderr)
        wget.download(udpipe_model_url)

    model = Model.load('udpipe_syntagrus.model')
    ##########################################

    process_pipeline = Pipeline(model, 'tokenize', Pipeline.DEFAULT, Pipeline.DEFAULT, 'conllu')
    res = unify_sym(str.strip())
    output = process(process_pipeline, text=res)

    return ' '.join(output)


def getStringWithWordsFromModel(q_, srcModel, nullForm=False):
    # print('simplify to null form with words from model: ', q_)
    if not nullForm:
        q_ = stringNullifier(q_)

    q = q_.split(' ')
    good_words = []
    for word in q:
        print('check word in vocab:', word)
        if word in srcModel.wv.vocab:
            good_words.append(word)
    return ' '.join(good_words)


########################################################################################################################

import sqlite3
from shutil import copyfile


class qa:
    def __init__(self, id, question, answer, nullForm=False):
        self.id = id
        self.answer = answer
        self.question = question
        if not nullForm:
            self.null_question = stringNullifier(question)
        else:
            self.null_question = question

    def __str__(self):
        return str(self.id) + ' || question=' + self.null_question + ' || answer= ' + self.answer


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


############################
## для добавления из admin состояния
import time


def addNewQAtoBase(_qa, srcModel, targetModel, path='QA.db'):
    connection = sqlite3.connect(path)
    c = connection.cursor()
    c.execute('''INSERT OR IGNORE INTO qa (question, answer, null_question) VALUES (%s,%s,%s)''' % (
        '\'' + _qa.question + '\'', '\'' + _qa.answer + '\'', '\'' + _qa.null_question + '\''))
    connection.commit()
    connection.close()
    # доучиваем модель

    null_q_arr = getNullQuestionsFromDB()
    srcModel = trainModel('QA.w2v', null_q_arr, restart=True)
    targetModel = getQuestionModel(null_q_arr, srcModel, loadOldModel=False)
    return srcModel, targetModel


########################################################################################################################

def trainModel(path, wordsArr, restart=False):
    if restart or not os.path.isfile(path):
        model = Word2Vec(wordsArr, min_count=1)
        model.save(path)
    return Word2Vec.load(path)


def countVectorForNullQuestion(question, model):
    arr_q = question.split(' ')
    good_words = []

    # print('getting vector for question:', arr_q)
    # print(model.wv.vocab)
    # print(arr_q)
    for word in arr_q:
        if (model.wv.__contains__(word)):
            good_words.append(word)
    vector = model.wv.__getitem__(good_words[0]) * 1
    for word in good_words:
        vector = vector + model.wv.__getitem__(word)
    return vector


def getQuestionModel(null_q_arr, srcModel, loadOldModel=False):
    if loadOldModel:
        if os.path.isfile('question_model.w2v'):
            print('old question model uploaded.')
            question_model = Word2Vec.load('question_model.w2v')
            return question_model
        else:
            print('no old question model founded.')

    question_model = Word2Vec()

    for line in null_q_arr:
        question = ' '.join(line)
        question_model.wv.add(weights=countVectorForNullQuestion(question, model=srcModel), entities=question,
                              replace=False)

    question_model.save('question_model.w2v')

    null_vector = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                   0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    question_model.wv.add(weights=null_vector,
                          entities='Вы задали некорректный вопрос или пока такого вопроса нет в базе. Пожалуйста, перефразируете вопрос или свяжитесь с администрацией',
                          replace=False)

    return question_model


def showModel(model):
    from sklearn.decomposition import PCA
    from matplotlib import pyplot

    # fit a 2d PCA model to the vectors
    X = model[model.wv.vocab]
    pca = PCA(n_components=2)
    result = pca.fit_transform(X)
    # create a scatter plot of the projection
    pyplot.scatter(result[:, 0], result[:, 1])
    pyplot.xlim(-0.003, 0.003)
    pyplot.ylim(-0.003, 0.003)
    words = model.wv.vocab
    for i, word in enumerate(words):
        pyplot.annotate(word, xy=(result[i, 0], result[i, 1]))

    pyplot.show()


########################################################################################################################

def getAnswers(question, srcModel, targetModel, QAlist, addNewQuestionToModel=False,
               targetModelPath='question_model.w2v'):
    # print('searching for answer: ', question)
    null_q = getStringWithWordsFromModel(question, srcModel, nullForm=False)
    # print(null_q)
    if addNewQuestionToModel:
        targetModel.wv.add(weights=countVectorForNullQuestion(null_q, model=srcModel), entities=null_q, replace=False)
        targetModel.save(targetModelPath)

    questions = targetModel.wv.similar_by_vector(countVectorForNullQuestion(null_q, model=srcModel))
    answers = []
    for q in questions:
        for qa in QAlist:
            if q[0] == qa.null_question:
                answers.append(qa.answer)
                continue
    return answers


########################################################################################################################
# admin fucntions
class _userVK:
    onMenu = 0

    def __init__(self, id, superUser=0):
        self.id = id
        if superUser is 1:
            self.superUser = True
        else:
            self.superUser = False

    def __repr__(self):
        return (str(self.id) + ' | SuperUser = ' + str(self.superUser))


class _userTG:
    onMenu = 0

    def __init__(self, login, superUser=0):
        self.login = login
        if superUser is 1:
            self.superUser = True
        else:
            self.superUser = False

    def __repr__(self):
        return (str(self.id) + ' | SuperUser = ' + str(self.superUser))


def getUsersFromDB_VK(path='QA.db'):
    users = []

    if not os.path.isfile(path):
        copyfile("backup\\QA_zero_backup.db", path)

    connection = sqlite3.connect(path)
    c = connection.cursor()

    list_ = []
    for line in c.execute('''SELECT * FROM usersVK'''):
        list_.append(line)

    for row in list_:
        # qa(id, question, answer, nullQuestionGiven)
        # print(row)
        print(row[0], row[1])
        users.append(_userVK(row[0], row[1]))
    connection.close()
    return users


def getUsersFromDB_TG(path='QA.db'):
    users = []

    if not os.path.isfile(path):
        copyfile("backup\\QA_zero_backup.db", path)

    connection = sqlite3.connect(path)
    c = connection.cursor()

    list_ = []
    for line in c.execute('''SELECT * FROM usersTG'''):
        list_.append(line)

    for row in list_:
        # qa(id, question, answer, nullQuestionGiven)
        new_user = _userTG(row[0], row[1])
        users.append(new_user)
    connection.close()
    return users


def changeSuperUser_VK(id, superUser, path='QA.db'):
    connection = sqlite3.connect(path)
    c = connection.cursor()
    c.execute('''UPDATE OR IGNORE usersVK SET superUser = %s WHERE id = %s''' % (superUser, id))
    connection.commit()


def changeSuperUser_TG(login, superUser, path='QA.db'):
    connection = sqlite3.connect(path)
    c = connection.cursor()
    c.execute('''UPDATE OR IGNORE usersTG SET superUser = %s WHERE login = %s''' % (superUser, login))
    connection.commit()


def addUser_VK(id, superUser=0, path='QA.db'):
    connection = sqlite3.connect(path)
    c = connection.cursor()
    if superUser is True:
        superUser = 1
    if superUser is False:
        superUser = 0
    c.execute('''INSERT OR IGNORE INTO usersVK (id, superUser) VALUES (%s,%s)''' % (id, superUser))
    connection.commit()
    connection.close()
    return getUsersFromDB_VK(path)


def addUser_TG(login, superUser=0, path='QA.db'):
    connection = sqlite3.connect(path)
    c = connection.cursor()
    c.execute('''INSERT OR IGNORE INTO usersTG (login, superUser) VALUES (%s,%s)''' % ('"' + login + '"', superUser))
    connection.commit()
    connection.close()
    return getUsersFromDB_TG(path)


def removeUser_VK(id, path='QA.db'):
    connection = sqlite3.connect(path)
    c = connection.cursor()
    c.execute('''DELETE FROM usersVK WHERE id = %s''' % (id))
    connection.commit()
    connection.close()
    return getUsersFromDB_VK(path)


def removeUser_TG(login, path='QA.db'):
    connection = sqlite3.connect(path)
    c = connection.cursor()
    c.execute('''DELETE FROM usersTG WHERE login = "%s"''' % (login))
    connection.commit()
    connection.close()
    return getUsersFromDB_TG(path)


########################################################################################################################


# print(model.wv.vocab)
# print(question_model.wv.vocab)
##showModel(model)

# test_qa = qa(-1, 'военная кафедра', 'answer2', nullForm= False)
# model, question_model = addNewQAtoBase(test_qa, model, question_model) # пример добавление новго вопроса в базу. Так же переучиваются текущие модели

# print(model.wv.vocab)
# print(question_model.wv.vocab)


##################################################################################################################################################################################

import json
import threading
import telebot

telegram_admin_list = []


class TelegramThread(threading.Thread):
    telegram_token = '713680560:AAG65APKYH5mZy69dpPcwLYHZ47Rv1JavRE'
    bot = telebot.TeleBot(telegram_token)
    first_m = 'Здравствуйте! Этот FAQ-бот поможет Вам получить ответы на самые часто задаваемые вопросы касательно учебы в ВШЭ. Правила пользования ботом:\n' \
              '-Содержание вопросов должно быть сформулировано кратко и без лишней информации\n-Слова в вопросе не должны содержать ошибок\n' \
              'Так как проект новый, база вопросов не столь велика, но мы работаем над ее увеличением!\n Ожидание ответа: до 20 секунд'

    telegram_keyboard = telebot.types.ReplyKeyboardMarkup()
    telegram_super_keyboard = telebot.types.ReplyKeyboardMarkup()
    telegram_mini_keyboard = telebot.types.ReplyKeyboardMarkup()
    telegram_null_keyboard = telebot.types.ReplyKeyboardRemove(selective=False)

    download_button = telebot.types.KeyboardButton('Загрузить базу данных')
    add_ask_button = telebot.types.KeyboardButton('Добавить вопрос в базу данных')
    add_admin_button = telebot.types.KeyboardButton('Добавить администратора')
    add_super_button = telebot.types.KeyboardButton('Добавить супер права')
    delete_admin_button = telebot.types.KeyboardButton('Удалить администратора')
    delete_super_button = telebot.types.KeyboardButton('Удалить супер права')
    help_button = telebot.types.KeyboardButton('Помощь')
    cancel_button = telebot.types.KeyboardButton('Отменить')

    def getId(self, id, admin_list):
        for idx, val in enumerate(admin_list):
            if val.id == id:
                return idx
        return -1

    def return_keyboard(self, admin):
        if admin.superUser:
            return self.telegram_super_keyboard
        else:
            return self.telegram_keyboard

    def run(self):

        self.telegram_keyboard.add(self.download_button, self.add_ask_button, self.help_button)
        self.telegram_super_keyboard.add(self.download_button, self.add_ask_button, self.help_button,
                                         self.add_admin_button,
                                         self.add_super_button, self.delete_admin_button, self.delete_super_button,
                                         self.help_button)
        self.telegram_mini_keyboard.add(self.help_button, self.cancel_button)

        telegram_admin_list = getUsersFromDB_TG()

        null_q_arr = getNullQuestionsFromDB()
        model = trainModel('QA.w2v', null_q_arr, restart=True)
        question_model = getQuestionModel(null_q_arr, model, loadOldModel=False)

        print('TG ready')
        @self.bot.message_handler(content_types=["text"])
        def repeat_all_messages(message):
            admin_id = self.getId(message.chat.username, telegram_admin_list)
            if message.text == '/start':
                self.bot.send_message(message.chat.id, self.first_m)


            elif admin_id != -1:
                if telegram_admin_list[admin_id].onMenu != 0:
                    if message.text == "Отменить":
                        self.bot.send_message(message.chat.id, 'Отмененно',
                                              reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))
                        telegram_admin_list[admin_id].onMenu = 0

                    elif message.text == "Помощь":
                        if telegram_admin_list[admin_id].superUser:
                            self.bot.send_message(message.chat.id,
                                                  'супер админ ыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыы',
                                                  reply_markup=self.telegram_mini_keyboard)
                        else:
                            self.bot.send_message(message.chat.id,
                                                  'обычный админ ыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыы',
                                                  reply_markup=self.telegram_mini_keyboard)

                    elif telegram_admin_list[admin_id].onMenu == 2:
                        text_arr = message.text.split(':');
                        if len(text_arr) == 2:
                            new_qa = qa(0, text_arr[0], text_arr[1], nullForm=False)
                            print(list(question_model.wv.vocab))
                            model, question_model = addNewQAtoBase(new_qa, model, question_model)
                            print(list(question_model.wv.vocab))

                            telegram_admin_list[admin_id].onMenu = 0
                            self.bot.send_message(message.chat.id,
                                                  'Вопрос добавлен',
                                                  reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))
                        else:
                            self.bot.send_message(message.chat.id,
                                                  'Введите корректный вопрос',
                                                  reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))
                    elif telegram_admin_list[admin_id].onMenu == 3:
                        try:
                            new_admin = self.getId(int(message.text), telegram_admin_list)
                            if new_admin == -1:
                                new_user = _userTG(int(message.text), 0)
                                telegram_admin_list.append(new_user)

                                addUser_TG(new_user.id, new_user.superUser)

                                telegram_admin_list[admin_id].onMenu = 0
                                self.bot.send_message(message.chat.id,
                                                      'Админ добавлен',
                                                      reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))
                            else:
                                self.bot.send_message(message.chat.id,
                                                      'Админ с таким id уже существует',
                                                      reply_markup=self.telegram_mini_keyboard)
                        except:
                            self.bot.send_message(message.chat.id,
                                                  'Введите корректный id',
                                                  reply_markup=self.telegram_mini_keyboard)
                    elif telegram_admin_list[admin_id].onMenu == 4:
                        try:
                            new_admin = self.getId(int(message.text), telegram_admin_list)
                            if new_admin == -1:
                                temp_user = _userTG(int(message.text), 1)
                                telegram_admin_list.append(temp_user)

                                sup = 0
                                if temp_user.superUser:
                                    sup = 1
                                addUser_TG(temp_user.id, sup)

                                telegram_admin_list[admin_id].onMenu = 0
                                self.bot.send_message(message.chat.id,
                                                      'Супер администратор добавлен',
                                                      reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))
                            else:

                                changeSuperUser_TG(telegram_admin_list[new_admin].id,
                                                   telegram_admin_list[admin_id].superUser)
                                telegram_admin_list[admin_id].onMenu = 0
                                telegram_admin_list[new_admin].superUser = True

                                self.bot.send_message(message.chat.id,
                                                      'Супер администратор добавлен',
                                                      reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))
                        except:
                            self.bot.send_message(message.chat.id,
                                                  'Введите корректный id',
                                                  reply_markup=self.telegram_mini_keyboard)
                    elif telegram_admin_list[admin_id].onMenu == 5:
                        try:
                            admin_for_delete = self.getId(int(message.text), telegram_admin_list)
                            if not admin_for_delete is -1:
                                removeUser_TG(telegram_admin_list[admin_for_delete].id)
                                telegram_admin_list.remove(telegram_admin_list[admin_for_delete])

                                telegram_admin_list[admin_id].onMenu = 0
                                self.bot.send_message(message.chat.id,
                                                      'Администратор удален',
                                                      reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))
                            else:
                                self.bot.send_message(message.chat.id,
                                                      'Нет админа с таким id',
                                                      reply_markup=self.telegram_mini_keyboard)
                        except:
                            self.bot.send_message(message.chat.id,
                                                  'Введите корректный id',
                                                  reply_markup=self.telegram_mini_keyboard)
                    elif telegram_admin_list[admin_id].onMenu == 6:
                        try:
                            admin_for_clear = self.getId(int(message.text), telegram_admin_list)
                            if admin_for_clear != -1:
                                telegram_admin_list[admin_for_clear].superUser = 0

                                changeSuperUser_TG(telegram_admin_list[admin_for_clear].id,
                                                   telegram_admin_list[admin_for_clear].superUser)

                                telegram_admin_list[admin_id].onMenu = 0
                                self.bot.send_message(message.chat.id,
                                                      'Супер пользователь добавлен',
                                                      reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))
                            else:
                                self.bot.send_message(message.chat.id,
                                                      'Нет админа с таким id',
                                                      reply_markup=self.telegram_mini_keyboard)
                        except:
                            self.bot.send_message(message.chat.id,
                                                  'Введите корректный id',
                                                  reply_markup=self.telegram_mini_keyboard)
                elif message.text == "Загрузить базу данных":
                    self.bot.send_message(message.chat.id,
                                          'baza',
                                          reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))
                elif message.text == "Добавить вопрос в базу данных":
                    self.bot.send_message(message.chat.id,
                                          'Введите вопрос в формате Вопрос : Ответ',
                                          reply_markup=self.telegram_mini_keyboard)
                    telegram_admin_list[admin_id].onMenu = 2
                elif message.text == "Помощь":
                    if telegram_admin_list[admin_id].superUser:
                        self.bot.send_message(message.chat.id,
                                              'супер админ ыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыы',
                                              reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))
                    else:
                        self.bot.send_message(message.chat.id,
                                              'обычный админ ыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыы',
                                              reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))

                elif telegram_admin_list[admin_id].superUser:
                    if message.text == "Добавить администратора":
                        self.bot.send_message(message.chat.id,
                                              'Введите id человека, которому хотите дать права администратора',
                                              reply_markup=self.telegram_mini_keyboard)

                        telegram_admin_list[admin_id].onMenu = 3

                    elif message.text == "Добавить супер права":
                        self.bot.send_message(message.chat.id,
                                              'Введите id человека, которому хотите дать супер права',
                                              reply_markup=self.telegram_mini_keyboard)
                        telegram_admin_list[admin_id].onMenu = 4
                    elif message.text == "Удалить администратора":
                        self.bot.send_message(message.chat.id,
                                              'Введите id человека, которому хотите снять права администратора',
                                              reply_markup=self.telegram_mini_keyboard)
                        telegram_admin_list[admin_id].onMenu = 5
                    elif message.text == "Удалить супер права":
                        self.bot.send_message(message.chat.id,
                                              'Введите id человека, которому хотите снять супер права, при этом человек останется администратором',
                                              reply_markup=self.telegram_mini_keyboard)

                        telegram_admin_list[admin_id].onMenu = 6
                    else:
                        answers = getAnswers(str(event.text), model, question_model, getListOfQAfromDB(),
                                            addNewQuestionToModel=False)
                        print(answers)
                        self.bot.send_message(message.chat.id,
                                              answers[0],
                                              reply_markup=self.telegram_super_keyboard)
                else:
                    answers = getAnswers(str(event.text), model, question_model, getListOfQAfromDB(),
                                        addNewQuestionToModel=False)
                    print(answers)
                    self.bot.send_message(message.chat.id,
                                          answers[0],
                                          reply_markup=self.telegram_keyboard)
            else:
                answers = getAnswers(str(event.text), model, question_model, getListOfQAfromDB(),
                                     addNewQuestionToModel=True)
                print(answers)
                self.bot.send_message(message.chat.id,
                                      answers[0],
                                      reply_markup=self.telegram_null_keyboard)

        self.bot.polling(none_stop=True)


##################################################################################################################################################################################

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType


class VkThread(threading.Thread):
    vk_token = "570036a833509d794b32224e32890ed0be12aee9624e0ed0905548f5a6cbcc559ad1be9c9a83ce3c50c27"
    vk_session = vk_api.VkApi(token=vk_token)
    longpoll = VkLongPoll(vk_session)

    def get_vk_button(label, color, payload=""):
        return {
            "action": {
                "type": "text",
                "payload": json.dumps(payload),
                "label": label
            },
            "color": color
        }

    vk_keyboard = {
        "one_time": False,
        "buttons": [
            [get_vk_button(label="Загрузить базу данных", color="primary")],
            [get_vk_button(label="Добавить вопрос в базу данных", color="primary")],  # menu id 2
            [get_vk_button(label="Помощь", color="primary")]

        ]
    }

    vk_super_keyboard = {
        "one_time": False,
        "buttons": [
            [get_vk_button(label="Загрузить базу данных", color="primary")],
            [get_vk_button(label="Добавить вопрос в базу данных", color="primary")],  # menu id 2
            [get_vk_button(label="Добавить администратора", color="primary")],  # menu id 3
            [get_vk_button(label="Добавить супер права", color="primary")],  # menu id 4
            [get_vk_button(label="Удалить администратора", color="primary")],  # menu id 5
            [get_vk_button(label="Удалить супер права", color="primary")],  # menu id 6
            [get_vk_button(label="Помощь", color="primary")]

        ]
    }

    vk_mini_keyboard = {
        "one_time": False,
        "buttons": [
            [get_vk_button(label="Отменить", color="primary")],
            [get_vk_button(label="Помощь", color="primary")]

        ]
    }

    vk_null_keyboard = {
        "one_time": True,
        "buttons": []
    }

    def getId(self, id, admin_list):

        for idx, val in enumerate(admin_list):
            if val.id == id:
                return idx
        return -1

    def return_keyboard(self, admin):
        if admin.superUser:
            return self.vk_super_keyboard
        else:
            return self.vk_keyboard

    def run(self):
        self.vk_keyboard = json.dumps(self.vk_keyboard, ensure_ascii=False).encode('utf-8')
        self.vk_super_keyboard = json.dumps(self.vk_super_keyboard, ensure_ascii=False).encode('utf-8')
        self.vk_mini_keyboard = json.dumps(self.vk_mini_keyboard, ensure_ascii=False).encode('utf-8')
        self.vk_null_keyboard = json.dumps(self.vk_null_keyboard, ensure_ascii=False).encode('utf-8')

        self.vk_super_keyboard = str(self.vk_super_keyboard.decode('utf-8'))
        self.vk_keyboard = str(self.vk_keyboard.decode('utf-8'))
        self.vk_mini_keyboard = str(self.vk_mini_keyboard.decode('utf-8'))
        self.vk_null_keyboard = str(self.vk_null_keyboard.decode('utf-8'))

        vk_admin_list = getUsersFromDB_VK()

        null_q_arr = getNullQuestionsFromDB()
        model = trainModel('QA.w2v', null_q_arr, restart=True)
        question_model = getQuestionModel(null_q_arr, model, loadOldModel=False)
        print('VK ready')
        while True:
            for event in self.longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.from_user and not event.from_me:
                    admin_id = self.getId(event.user_id, vk_admin_list)
                    if admin_id != -1:
                        if vk_admin_list[admin_id].onMenu != 0:
                            if str(event.text) == "Отменить":
                                self.vk_session.method('messages.send',
                                                       {'user_id': event.user_id,
                                                        'message': 'Отмененно',
                                                        'random_id': 0,
                                                        'keyboard': self.return_keyboard(vk_admin_list[admin_id])})
                                vk_admin_list[admin_id].onMenu = 0

                            elif str(event.text) == "Помощь":
                                if vk_admin_list[admin_id].superUser:
                                    self.vk_session.method('messages.send',
                                                           {'user_id': event.user_id,
                                                            'message': 'супер админ ыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыы',
                                                            'random_id': 0, 'keyboard': self.vk_mini_keyboard})
                                else:
                                    self.vk_session.method('messages.send',
                                                           {'user_id': event.user_id,
                                                            'message': 'обычный админ ыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыы',
                                                            'random_id': 0, 'keyboard': self.vk_mini_keyboard})

                            elif vk_admin_list[admin_id].onMenu == 2:
                                text_arr = str(event.text).split(':');
                                if len(text_arr) == 2:
                                    new_qa = qa(0, text_arr[0], text_arr[1], nullForm=False)
                                    print(list(question_model.wv.vocab))
                                    model, question_model = addNewQAtoBase(new_qa, model, question_model)
                                    print(list(question_model.wv.vocab))

                                    vk_admin_list[admin_id].onMenu = 0
                                    self.vk_session.method('messages.send',
                                                           {'user_id': event.user_id,
                                                            'message': 'Вопрос добавлен',
                                                            'random_id': 0,
                                                            'keyboard': self.return_keyboard(vk_admin_list[admin_id])})

                                else:
                                    self.vk_session.method('messages.send',
                                                           {'user_id': event.user_id,
                                                            'message': 'Введите корректный вопрос',
                                                            'random_id': 0, 'keyboard': self.vk_mini_keyboard})
                            elif vk_admin_list[admin_id].onMenu == 3:
                                try:
                                    new_admin = self.getId(int(event.text), vk_admin_list)
                                    if new_admin == -1:
                                        new_user = _userVK(int(event.text), 0)
                                        vk_admin_list.append(new_user)

                                        addUser_VK(new_user.id, new_user.superUser)

                                        vk_admin_list[admin_id].onMenu = 0
                                        self.vk_session.method('messages.send',
                                                               {'user_id': int(event.user_id),
                                                                'message': 'Админ добавлен',
                                                                'random_id': 0, 'keyboard': self.return_keyboard(
                                                                   vk_admin_list[admin_id])})
                                    else:
                                        self.vk_session.method('messages.send',
                                                               {'user_id': event.user_id,
                                                                'message': 'Администратор с таким id уже существует',
                                                                'random_id': 0, 'keyboard': self.vk_mini_keyboard})

                                except:
                                    self.vk_session.method('messages.send',
                                                           {'user_id': event.user_id,
                                                            'message': 'Введите корректный id для добавления администратора',
                                                            'random_id': 0, 'keyboard': self.vk_mini_keyboard})
                            elif vk_admin_list[admin_id].onMenu == 4:
                                try:
                                    new_admin = self.getId(int(event.text), vk_admin_list)
                                    if new_admin == -1:
                                        temp_user = _userVK(int(event.text), 1)
                                        vk_admin_list.append(temp_user)

                                        sup = 0
                                        if temp_user.superUser:
                                            sup = 1
                                        addUser_VK(temp_user.id, sup)

                                        vk_admin_list[admin_id].onMenu = 0
                                        self.vk_session.method('messages.send',
                                                               {'user_id': event.user_id,
                                                                'message': 'Супер администратор добавлен',
                                                                'random_id': 0, 'keyboard': self.return_keyboard(
                                                                   vk_admin_list[admin_id])})
                                    else:

                                        changeSuperUser_VK(vk_admin_list[new_admin].id,
                                                           vk_admin_list[admin_id].superUser)
                                        vk_admin_list[admin_id].onMenu = 0
                                        vk_admin_list[new_admin].superUser = True

                                        self.vk_session.method('messages.send',
                                                               {'user_id': event.user_id,
                                                                'message': 'Супер администратор добавлен',
                                                                'random_id': 0, 'keyboard': self.return_keyboard(
                                                                   vk_admin_list[admin_id])})

                                except:
                                    self.vk_session.method('messages.send',
                                                           {'user_id': event.user_id,
                                                            'message': 'Введите корректный id для добавление супер администратора',
                                                            'random_id': 0, 'keyboard': self.vk_mini_keyboard})

                            elif vk_admin_list[admin_id].onMenu == 5:
                                try:
                                    admin_for_delete = self.getId(int(event.text), vk_admin_list)
                                    if not admin_for_delete is -1:

                                        removeUser_VK(vk_admin_list[admin_for_delete].id)

                                        vk_admin_list.remove(vk_admin_list[admin_for_delete])

                                        vk_admin_list[admin_id].onMenu = 0
                                        self.vk_session.method('messages.send',
                                                               {'user_id': event.user_id,
                                                                'message': 'Админ удален',
                                                                'random_id': 0, 'keyboard': self.return_keyboard(
                                                                   vk_admin_list[admin_id])})
                                    else:

                                        self.vk_session.method('messages.send',
                                                               {'user_id': event.user_id,
                                                                'message': 'Нет админа с таким id',
                                                                'random_id': 0, 'keyboard': self.vk_mini_keyboard})
                                except:
                                    self.vk_session.method('messages.send',
                                                           {'user_id': event.user_id,
                                                            'message': 'Введите корректный id администратора, которого хотите удалить',
                                                            'random_id': 0, 'keyboard': self.vk_mini_keyboard})

                            elif vk_admin_list[admin_id].onMenu == 6:
                                try:
                                    admin_for_clear = self.getId(int(event.text), vk_admin_list)
                                    if admin_for_clear != -1:
                                        vk_admin_list[admin_for_clear].superUser = 0

                                        changeSuperUser_VK(vk_admin_list[admin_for_clear].id,
                                                           vk_admin_list[admin_for_clear].superUser)

                                        vk_admin_list[admin_id].onMenu = 0
                                        self.vk_session.method('messages.send',
                                                               {'user_id': event.user_id,
                                                                'message': 'Права успешно удалены',
                                                                'random_id': 0, 'keyboard': self.return_keyboard(
                                                                   vk_admin_list[admin_id])})
                                    else:
                                        self.vk_session.method('messages.send',
                                                               {'user_id': event.user_id,
                                                                'message': 'Нет админа с таким id',
                                                                'random_id': 0, 'keyboard': self.vk_mini_keyboard})
                                except:
                                    self.vk_session.method('messages.send',
                                                           {'user_id': event.user_id,
                                                            'message': 'Введите корректный id',
                                                            'random_id': 0, 'keyboard': self.vk_mini_keyboard})
                        elif str(event.text) == "Загрузить базу данных":
                            self.vk_session.method('messages.send',
                                                   {'user_id': event.user_id,
                                                    'message': 'baza',
                                                    'random_id': 0, 'keyboard': self.return_keyboard(
                                                       vk_admin_list[admin_id])})
                        elif str(event.text) == "Добавить вопрос в базу данных":
                            self.vk_session.method('messages.send',
                                                   {'user_id': event.user_id,
                                                    'message': 'Введите вопрос в формате Вопрос : Ответ',
                                                    'random_id': 0, 'keyboard': self.vk_mini_keyboard})
                            vk_admin_list[admin_id].onMenu = 2
                        elif str(event.text) == "Помощь":
                            if vk_admin_list[admin_id].superUser:
                                self.vk_session.method('messages.send',
                                                       {'user_id': event.user_id,
                                                        'message': 'супер админ ыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыы',
                                                        'random_id': 0, 'keyboard': self.return_keyboard(
                                                           vk_admin_list[admin_id])})
                            else:
                                self.vk_session.method('messages.send',
                                                       {'user_id': event.user_id,
                                                        'message': 'обычный админ ыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыыы',
                                                        'random_id': 0, 'keyboard': self.return_keyboard(
                                                           vk_admin_list[admin_id])})

                        elif vk_admin_list[admin_id].superUser:
                            if str(event.text) == "Добавить администратора":
                                self.vk_session.method('messages.send',
                                                       {'user_id': event.user_id,
                                                        'message': 'Введите id человека, которому хотите дать права администратора',
                                                        'random_id': 0, 'keyboard': self.vk_mini_keyboard})
                                vk_admin_list[admin_id].onMenu = 3

                            elif str(event.text) == "Добавить супер права":
                                self.vk_session.method('messages.send',
                                                       {'user_id': event.user_id,
                                                        'message': 'Введите id человека, которому хотите дать супер права',
                                                        'random_id': 0, 'keyboard': self.vk_mini_keyboard})
                                vk_admin_list[admin_id].onMenu = 4
                            elif str(event.text) == "Удалить администратора":
                                self.vk_session.method('messages.send',
                                                       {'user_id': event.user_id,
                                                        'message': 'Введите id человека, которому хотите снять права администратора',
                                                        'random_id': 0, 'keyboard': self.vk_mini_keyboard})
                                vk_admin_list[admin_id].onMenu = 5
                            elif str(event.text) == "Удалить супер права":
                                self.vk_session.method('messages.send',
                                                       {'user_id': event.user_id,
                                                        'message': 'Введите id человека, которому хотите снять супер права, при этом человек останется администратором',
                                                        'random_id': 0, 'keyboard': self.vk_mini_keyboard})
                                vk_admin_list[admin_id].onMenu = 6
                            else:
                                answers =  getAnswers(str(event.text), model, question_model, getListOfQAfromDB(),
                                  addNewQuestionToModel=False)
                                print(answers)
                                self.vk_session.method('messages.send',
                                                       {'user_id': event.user_id,
                                                        'message': answers[0],
                                                        'random_id': 0, 'keyboard': self.vk_super_keyboard})
                        else:
                            answers =  getAnswers(str(event.text), model, question_model, getListOfQAfromDB(),
                              addNewQuestionToModel=False)
                            print(answers)
                            self.vk_session.method('messages.send',
                                                   {'user_id': event.user_id,
                                                    'message': answers[0],
                                                    'random_id': 0, 'keyboard': self.vk_keyboard})

                    else:
                        answers =  getAnswers(str(event.text), model, question_model, getListOfQAfromDB(),
                         addNewQuestionToModel=False)
                        print(answers)
                        self.vk_session.method('messages.send',
                                               {'user_id': event.user_id,
                                                'message': answers[0],
                                                'random_id': 0, 'keyboard': self.vk_null_keyboard})


##########################################################################################################################################################################


vk = VkThread()
tel = TelegramThread()

vk_admin_list = getUsersFromDB_VK()

vk.start()
tel.start()


