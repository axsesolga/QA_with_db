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
#Kutuzov A., Kuzmenko E. (2017) WebVectors: A Toolkit for Building Web Interfaces for Vector Semantic Models. In: Ignatov D. et al.
#(eds) Analysis of Images, Social Networks and Texts. AIST 2016. Communications in Computer and Information Science, vol 661. Springer, Cham
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
                tagged_propn.append('%s_%s' % (lemma, pos))
                continue
            morph = {el.split('=')[0]: el.split('=')[1] for el in feats.split('|')}
            if 'Case' not in morph or 'Number' not in morph:
                tagged_propn.append('%s_%s' % (lemma, pos))
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
                    tagged_propn.append(past_lemma + '_PROPN ')
            else:
                named = False
                past_lemma = '::'.join(memory)
                memory = []
                tagged_propn.append(past_lemma + '_PROPN ')
                tagged_propn.append('%s_%s' % (lemma, pos))
        else:
            if not named:
                if pos == 'NUM' and token.isdigit():  # Заменяем числа на xxxxx той же длины
                    lemma = num_replace(token)
                tagged_propn.append('%s_%s' % (lemma, pos))
            else:
                named = False
                past_lemma = '::'.join(memory)
                memory = []
                tagged_propn.append(past_lemma + '_PROPN ')
                tagged_propn.append('%s_%s' % (lemma, pos))

    if not keep_punct:
        tagged_propn = [word for word in tagged_propn if word.split('_')[1] != 'PUNCT']
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
#End of RusVectores code
########################################################################################################################


def stringNullifier(str):
    #print('simplify to null form: ', str)
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

def getStringWithWordsFromModel(q_, srcModel, nullForm = False):
    #print('simplify to null form with words from model: ', q_)
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
    def __init__(self, id, question, answer, nullForm = False):
        self.id = id
        self.answer = answer

        if not nullForm:
            self.null_question = stringNullifier(question)
        else:
            self.null_question = question

    def __str__(self):
        return str(self.id) + ' || question=' + self.null_question + ' || answer= ' + self.answer

#при чтении если отсуствует элемент в null_questions сам его создает
def getListOfQAfromDB(path = 'QA.db'):
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
        #qa(id, question, answer, nullQuestionGiven)
        if not row[3]:
            new_q = qa(row[0], row[1], row[2], nullForm=False)

            c.execute('''UPDATE qa SET null_question = %s WHERE id = %s''' %('"' + new_q.null_question + '"', str(new_q.id)))
            connection.commit()
            out.append(new_q)
        else:
            out.append(qa(row[0], row[3], row[2], nullForm=True))
    connection.close()
    return out

def getNullQuestionsFromDB(path = 'QA.db'):
    null_q_arr = []
    for item in getListOfQAfromDB(path):
        null_q_arr.append(item.null_question.split(' '))
    return null_q_arr

def addNewQAtoBase(question, answer, nullFrom = False, path = 'QA.db'):
    null_q = question
    if not nullFrom:
        null_q = stringNullifier(question)

    connection = sqlite3.connect(path)
    c = connection.cursor()
    c.execute('''INSERT OR IGNORE INTO qa (question, answer, null_question) VALUES (%s,%s,%s)''' % ('\'' + question + '\'', '\'' + answer + '\'', '\''+null_q+'\''))
    connection.commit()
    connection.close()

########################################################################################################################

def trainModel(path, wordsArr, restart=False):
    if restart or not os.path.isfile(path):
        model = Word2Vec(wordsArr, min_count=1)
        model.save(path)
    return Word2Vec.load(path)

def countVectorForNullQuestion(question, model):
    arr_q = question.split(' ')
    good_words = []

    #print('getting vector for question:', arr_q)
    for word in arr_q:
        if (model.wv.__contains__(word)):
            good_words.append(word)
    vector = model.wv.__getitem__(good_words[0])*1
    for word in good_words:
        vector = vector + model.wv.__getitem__(word)
    return vector

def getQuestionModel(null_q_arr, srcModel, loadOldModel = False):
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
        question_model.wv.add(weights=countVectorForNullQuestion(question, model=srcModel), entities=question, replace=False)

    question_model.save('question_model.w2v')
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

def getAnswers(question, srcModel, targetModel, QAlist, addNewQuestionToModel=False, targetModelPath='question_model.w2v'):
    #print('searching for answer: ', question)
    null_q = getStringWithWordsFromModel(question, srcModel, nullForm=False)
    print(null_q)
    if addNewQuestionToModel:
        targetModel.wv.add(weights=countVectorForNullQuestion(null_q, model=srcModel), entities=null_q, replace=False)
        targetModel.save(targetModelPath)

    questions = question_model.wv.similar_by_vector(countVectorForNullQuestion(null_q, model=srcModel))
    answers = []
    for q in questions:
        for qa in QAlist:
            if q[0] == qa.null_question:
                answers.append(qa.answer)
                continue
    return answers



########################################################################################################################




null_q_arr = getNullQuestionsFromDB()
model = trainModel('QA.w2v', null_q_arr, restart=True)
question_model = getQuestionModel(null_q_arr, model, loadOldModel=False)
print(model.wv.vocab)
#showModel(model)

'''
import telebot

token = '774853254:AAFB-BStBb4f3p9ts3TZ7i7Qx5Sw6m_vWJk'
bot = telebot.TeleBot(token)

print('ready')
@bot.message_handler(content_types=["text"])
def repeat_all_messages(message):

    first_m = 'Здравствуйте! Этот FAQ-бот поможет Вам получить ответы на самые часто задаваемые вопросы касательно учебы в ВШЭ. Правила пользования ботом:\n' \
              '-Содержание вопросов должно быть сформулировано кратко и без лишней информации\n-Слова в вопросе не должны содержать ошибок\n' \
              'Так как проект новый, база вопросов не столь велика, но мы работаем над ее увеличением!\n Ожидание ответа: до 20 секунд'
    if message.text == '/start':
        bot.send_message(message.chat.id, first_m)
    else:
        answers = getAnswers(message.text, model, question_model, getListOfQAfromDB(), addNewQuestionToModel=True)
        print(answers)
        bot.send_message(message.chat.id, answers[0])

if __name__ == '__main__':
 bot.polling(none_stop=True)
'''