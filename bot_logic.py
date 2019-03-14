import language_cleaner_RusVectores



import sys
import wget as wget
from gensim.models import Word2Vec
from ufal.udpipe import Model, Pipeline
import os

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
    res = language_cleaner_RusVectores.unify_sym(str.strip())
    output = language_cleaner_RusVectores.process(process_pipeline, text=res)

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

def trainModel(path, wordsArr, restart=False):
    if restart or not os.path.isfile(path):
        model = Word2Vec(wordsArr, min_count=1)
        model.save(path)
    return Word2Vec.load(path)


def countVectorForNullQuestion(question, model):
    arr_q = question.split(' ')
    good_words = []

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
#Возвращает 10 ближайших ответов в порядке наиболее схожести
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