import language_cleaner_RusVectores
import sys
import wget as wget
from gensim.models import Word2Vec
from ufal.udpipe import Model, Pipeline
import os

NULL_VECTOR = ['NIL']

#С помощтю ufal приводит каждое слово в строке в инфинитив
def stringNullifier(str):
    # print('simplify to null form: ', str)
    # URL of the UDPipe model
    # на случай если файла нет скачиваем. Нужно для обработки русского текста
    udpipe_model_url = 'https://rusvectores.org/static/models/udpipe_syntagrus.model'
    if not os.path.isfile('udpipe_syntagrus.model'):
        print('UDPipe model not found. Downloading...', file=sys.stderr)
        wget.download(udpipe_model_url)

    model = Model.load('udpipe_syntagrus.model')
    ##########################################
    #само приведение в инфинитивы
    process_pipeline = Pipeline(model, 'tokenize', Pipeline.DEFAULT, Pipeline.DEFAULT, 'conllu')
    res = language_cleaner_RusVectores.unify_sym(str.strip())
    output = language_cleaner_RusVectores.process(process_pipeline, text=res)

    return ' '.join(output)

#В соотвествии со словарем из модели оставляет в строке только слова из этого словаря
def getStringWithWordsFromModel(q_, srcModel, nullForm=False):
    # print('simplify to null form with words from model: ', q_)
    if nullForm:
        q_ = stringNullifier(q_)

    q = q_.split(' ')
    good_words = []
    for word in q:
        print('check word in vocab:', word)
        if word in srcModel.wv.vocab:
            good_words.append(word)
    return ' '.join(good_words)

#получение файла .model из массива предложений, где каждое предложение - массив слов [ [,,,], [,,,] ]
def trainModel(path, wordsArr, restart=False):
    if restart or not os.path.isfile(path):
        model = Word2Vec(wordsArr, min_count=1) #min_count - минимальное число любого слова необходимое для занесение его в саму модель
        model.save(path)
    return Word2Vec.load(path)

#на основе векторов слов из model считает для строки-предложения вес
def countVectorForNullQuestion(question, model):
    arr_q = question.split(' ')
    good_words = []
    for word in arr_q:
        if (model.wv.__contains__(word)):
            good_words.append(word)

    flag = False
    for word in good_words:
        if len(word) <= 1:
            flag = True

    if len(good_words) is 0 or flag is True:
        return NULL_VECTOR

    vector = model.wv.__getitem__(good_words[0]) * 1
    for word in good_words:
        vector = vector + model.wv.__getitem__(word)

    #print('vec for q', question, vector)
    return vector

#подгрузка модели вопросов из файла или создание новой
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
        cur_vec = countVectorForNullQuestion(question, model=srcModel)
        if cur_vec is NULL_VECTOR:
            continue

        question_model.wv.add(weights=cur_vec, entities=question,
                              replace=False)

    question_model.save('question_model.w2v')


    return question_model

#графическое представление слов в модели в двумерном пространтсве (нигде не используется)
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
#Возвращает 10 ближайших ответов в порядке наиболее схожести
def getAnswers(question, srcModel, targetModel, QAlist, addNewQuestionToModel=False,
               targetModelPath='question_model.w2v'):
    null_q = getStringWithWordsFromModel(question, srcModel, nullForm=True)

    #добавляет в базу вопросов только сам вопрос, новые слова в изначальную модель не добавляются
    if addNewQuestionToModel:
        targetModel.wv.add(weights=countVectorForNullQuestion(null_q, model=srcModel), entities=null_q, replace=False)
        targetModel.save(targetModelPath)

    #подсчет вектороного проедставляения question
    this_q = countVectorForNullQuestion(null_q, model=srcModel)

    if this_q is NULL_VECTOR:
        return ['Вы задали некорректный вопрос или пока такого вопроса нет в базе. Пожалуйста, перефразируете вопрос или свяжитесь с администрацией']


    #поиск ближайшего вектора-вопроса к текущему question
    questions = targetModel.wv.similar_by_vector(countVectorForNullQuestion(null_q, model=srcModel))
    answers = []
    for q in questions:
        for qa in QAlist:
            if q[0] == qa.null_question:
                answers.append(qa.answer)
                continue


    return answers

#получение ответов из одной строки вопроса. Минусы - каждыый новый вопрос заного подгружает базу
import DB_methods
import  datetime
def getAnswers_simpleVersion(question, answer = '', path='QA.bd'):
    #print('getAnswersSimple_start\t', question)
    #получение из БД вопросов в виде массива массивов (массива предложений, каждое предложение - массив слов)
    null_q_arr = DB_methods.getListOfQAfromDB(path)
    #подгрузка модели всех слов вопросов
    model = trainModel('QA.w2v', null_q_arr)
    #подгрузка модели вопросов
    question_model = getQuestionModel(null_q_arr, model, loadOldModel=True)
    answers = getAnswers(question, model, question_model, null_q_arr)
    #print('getAnswersSimple_end\t', question, answers[0], datetime.datetime.now())

    #для парелельной работы методов
    from multiprocessing import Value
    answer.value = answers[0]
    return answers


'''

'''