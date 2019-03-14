#Требуется свободное подключение к серверам Телеграма (VPN или прокси на все подключения)
import os
import sqlite3
from shutil import copyfile




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

def changeSuperUser_TG(login, superUser, path='QA.db'):
    if superUser is True:
        superUser = 1
    if superUser is False:
        superUser = 0

    connection = sqlite3.connect(path)
    c = connection.cursor()
    c.execute('''UPDATE OR IGNORE usersTG SET superUser = %s WHERE login = "%s"''' % (superUser, login))
    connection.commit()

def addUser_TG(login, superUser=0, path='QA.db'):
    if superUser is True:
        superUser = 1
    if superUser is False:
        superUser = 0

    connection = sqlite3.connect(path)
    c = connection.cursor()
    c.execute('''INSERT OR IGNORE INTO usersTG (login, superUser) VALUES ("%s",%s)''' % (login, superUser))
    connection.commit()
    connection.close()
    return getUsersFromDB_TG(path)


def removeUser_TG(login, path='QA.db'):
    connection = sqlite3.connect(path)
    c = connection.cursor()
    c.execute('''DELETE FROM usersTG WHERE login = "%s"''' % (login))
    connection.commit()
    connection.close()
    return getUsersFromDB_TG(path)

import threading
import telebot

import bot_logic
import DB_methods

class TelegramThread(threading.Thread):
    #TODO тэк токен поменяйте
    #telegram_token = '713680560:AAG65APKYH5mZy69dpPcwLYHZ47Rv1JavRE'
    telegram_token = '774853254:AAFB-BStBb4f3p9ts3TZ7i7Qx5Sw6m_vWJk'
    bot = telebot.TeleBot(telegram_token)
    first_m = 'Здравствуйте! Этот FAQ-бот поможет Вам получить ответы на самые часто задаваемые вопросы касательно учебы в ВШЭ. Правила пользования ботом:\n' \
              '-Содержание вопросов должно быть сформулировано кратко и без лишней информации\n-Слова в вопросе не должны содержать ошибок\n' \
              'Так как проект новый, база вопросов не столь велика, но мы работаем над ее                                        увеличением!\n Ожидание ответа: до 20 секунд'

    telegram_keyboard = telebot.types.ReplyKeyboardMarkup()
    telegram_super_keyboard = telebot.types.ReplyKeyboardMarkup()
    telegram_mini_keyboard = telebot.types.ReplyKeyboardMarkup()
    telegram_null_keyboard = telebot.types.ReplyKeyboardRemove(selective=False)

    add_ask_button = telebot.types.KeyboardButton('Добавить вопрос в базу данных')
    add_admin_button = telebot.types.KeyboardButton('Добавить администратора')
    add_super_button = telebot.types.KeyboardButton('Добавить супер права')
    delete_admin_button = telebot.types.KeyboardButton('Удалить администратора')
    delete_super_button = telebot.types.KeyboardButton('Удалить супер права')
    help_button = telebot.types.KeyboardButton('Помощь')
    cancel_button = telebot.types.KeyboardButton('Отменить')

    def getId(self, id, admin_list):
        for idx, val in enumerate(admin_list):
            if val.login == id:
                return idx
        return -1

    def return_keyboard(self, admin):
        if admin.superUser:
            return self.telegram_super_keyboard
        else:
            return self.telegram_keyboard

    def run(self):

        self.telegram_keyboard.add(self.add_ask_button, self.help_button)
        self.telegram_super_keyboard.add(self.add_ask_button,
                                         self.add_admin_button,
                                         self.add_super_button, self.delete_admin_button, self.delete_super_button,
                                         self.help_button)
        self.telegram_mini_keyboard.add(self.cancel_button)

        telegram_admin_list = getUsersFromDB_TG()

        null_q_arr = DB_methods.getNullQuestionsFromDB()
        modelTG = bot_logic.trainModel('QA.w2v', null_q_arr, restart=True)
        question_modelTG = bot_logic.getQuestionModel(null_q_arr, modelTG, loadOldModel=False)

        print('TG ready')

        @self.bot.message_handler(content_types=["text"])
        def repeat_all_messages(message):
            admin_id = self.getId(message.chat.username, telegram_admin_list)
            if message.text == '/start':
                self.bot.send_message(message.chat.id, self.first_m)


            elif admin_id != -1:
                if telegram_admin_list[admin_id].onMenu != 0:
                    if message.text == "Отменить":
                        self.bot.send_message(message.chat.id, 'Отменено',
                                              reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))
                        telegram_admin_list[admin_id].onMenu = 0

                    elif telegram_admin_list[admin_id].onMenu == 2:
                        text_arr = message.text.split('___');
                        if len(text_arr) == 2:
                            new_qa = DB_methods.qa(0, text_arr[0], text_arr[1], nullForm=False)
                            print(list(question_modelTG.wv.vocab))
                            model, question_model = DB_methods.addNewQAtoBase(new_qa)
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
                            new_admin = self.getId(message.text, telegram_admin_list)
                            if new_admin == -1:
                                new_user = _userTG(message.text, 0)
                                telegram_admin_list.append(new_user)

                                addUser_TG(new_user.login, new_user.superUser)

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
                                                  'Введите корректный login для для добавления администратора',
                                                  reply_markup=self.telegram_mini_keyboard)
                    elif telegram_admin_list[admin_id].onMenu == 4:
                        try:
                            new_admin = self.getId(message.text, telegram_admin_list)
                            if new_admin == -1:
                                temp_user = _userTG(message.text, 1)
                                telegram_admin_list.append(temp_user)

                                addUser_TG(temp_user.login, temp_user.superUser)

                                telegram_admin_list[admin_id].onMenu = 0
                                self.bot.send_message(message.chat.id,
                                                      'Супер администратор создан',
                                                      reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))
                            else:

                                telegram_admin_list[admin_id].onMenu = 0
                                telegram_admin_list[new_admin].superUser = True
                                changeSuperUser_TG(telegram_admin_list[new_admin].login,
                                                   telegram_admin_list[new_admin].superUser)

                                self.bot.send_message(message.chat.id,
                                                      'Супер права добавлены',
                                                      reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))
                        except:
                            self.bot.send_message(message.chat.id,
                                                  'Введите корректный login для добавления супер прав',
                                                  reply_markup=self.telegram_mini_keyboard)
                    elif telegram_admin_list[admin_id].onMenu == 5:
                        try:
                            admin_for_delete = self.getId(message.text, telegram_admin_list)
                            if not admin_for_delete is -1:
                                removeUser_TG(telegram_admin_list[admin_for_delete].login)
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
                                                  'Введите корректный login для удаления администратора',
                                                  reply_markup=self.telegram_mini_keyboard)
                    elif telegram_admin_list[admin_id].onMenu == 6:
                        try:
                            admin_for_clear = self.getId(message.text, telegram_admin_list)
                            if admin_for_clear != -1:
                                telegram_admin_list[admin_for_clear].superUser = 0

                                changeSuperUser_TG(telegram_admin_list[admin_for_clear].login,
                                                   telegram_admin_list[admin_for_clear].superUser)

                                telegram_admin_list[admin_id].onMenu = 0
                                self.bot.send_message(message.chat.id,
                                                      'Супер права удалены',
                                                      reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))
                            else:
                                self.bot.send_message(message.chat.id,
                                                      'Нет админа с таким id',
                                                      reply_markup=self.telegram_mini_keyboard)
                        except:
                            self.bot.send_message(message.chat.id,
                                                  'Введите корректный login для удаления супер прав пользователя',
                                                  reply_markup=self.telegram_mini_keyboard)

                elif message.text == "Добавить вопрос в базу данных":
                    self.bot.send_message(message.chat.id,
                                          'Введите вопрос в формате Вопрос ___ Ответ',
                                          reply_markup=self.telegram_mini_keyboard)
                    telegram_admin_list[admin_id].onMenu = 2
                elif message.text == "Помощь":
                    if telegram_admin_list[admin_id].superUser:
                        self.bot.send_message(message.chat.id,
                                              'Справка для супер админа находится в руководстве пользователя на страницах 1234',
                                              reply_markup=self.return_keyboard(telegram_admin_list[admin_id]))
                    else:
                        self.bot.send_message(message.chat.id,
                                              'Справка для админа находится в руководстве пользователя на страницах 1234',
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
                        answers = bot_logic.getAnswers(str(message.text), modelTG, question_modelTG, DB_methods.getListOfQAfromDB(),
                                             addNewQuestionToModel=False)
                        print(answers)
                        self.bot.send_message(message.chat.id,
                                              answers[0],
                                              reply_markup=self.telegram_super_keyboard)
                else:
                    answers = bot_logic.getAnswers(str(message.text), modelTG, question_modelTG, DB_methods.getListOfQAfromDB(),
                                         addNewQuestionToModel=False)
                    print(answers)
                    self.bot.send_message(message.chat.id,
                                          answers[0],
                                          reply_markup=self.telegram_keyboard)
            else:
                answers = bot_logic.getAnswers(str(message.text), modelTG, question_modelTG, DB_methods.getListOfQAfromDB(),
                                     addNewQuestionToModel=True)
                print(answers)
                self.bot.send_message(message.chat.id,
                                      answers[0],
                                      reply_markup=self.telegram_null_keyboard)

        self.bot.polling(none_stop=True)
