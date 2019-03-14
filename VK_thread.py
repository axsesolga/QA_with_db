import os
import sqlite3
from shutil import copyfile


class _userVK:
    onMenu = 0

    def __init__(self, id, flname, superUser=0):
        self.id = id
        self.flname = flname
        if superUser is 1:
            self.superUser = True
        else:
            self.superUser = False

    def __repr__(self):
        return 'https://vk.com/id' + (str(self.id) + ' | ' + str(self.flname) + ' | SuperUser ' + str(self.superUser))

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
        print(row[0], row[1], row[2])
        users.append(_userVK(id=row[0], superUser=row[1], flname=row[2]))
    connection.close()
    return users

def changeSuperUser_VK(id, superUser, path='QA.db'):
    if superUser is True:
        superUser = 1
    if superUser is False:
        superUser = 0

    connection = sqlite3.connect(path)
    c = connection.cursor()
    print('''UPDATE OR IGNORE usersVK SET superUser = %s WHERE id = %s''' % (superUser, id))
    c.execute('''UPDATE OR IGNORE usersVK SET superUser = %s WHERE id = %s''' % (superUser, id))
    connection.commit()

def addUser_VK(id, flname, superUser=0, path='QA.db'):
    connection = sqlite3.connect(path)
    c = connection.cursor()
    if superUser is True:
        superUser = 1
    if superUser is False:
        superUser = 0
    c.execute(
        '''INSERT OR IGNORE INTO usersVK (id, superUser, name_sur) VALUES (%s,%s,"%s")''' % (id, superUser, flname))
    connection.commit()
    connection.close()
    return getUsersFromDB_VK(path)


def removeUser_VK(id, path='QA.db'):
    connection = sqlite3.connect(path)
    c = connection.cursor()
    c.execute('''DELETE FROM usersVK WHERE id = %s''' % (id))
    connection.commit()
    connection.close()
    return getUsersFromDB_VK(path)

import json
import threading
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import time

import bot_logic
import DB_methods
import file_creator

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
            [get_vk_button(label="Загрузить список вопросов", color="primary")],
            [get_vk_button(label="Добавить вопрос в базу данных", color="primary")],  # menu id 2
            [get_vk_button(label="Удалить вопрос из базы данных", color="primary")], # menu id 7
            [get_vk_button(label="Помощь", color="primary")]

        ]
    }

    vk_super_keyboard = {
        "one_time": False,
        "buttons": [
            [get_vk_button(label="Загрузить список админов", color="primary")],
            [get_vk_button(label="Загрузить список вопросов", color="primary")],
            [get_vk_button(label="Добавить вопрос в базу данных", color="primary")],  # menu id 2
            [get_vk_button(label="Удалить вопрос из базы данных", color="primary")], # menu id 7
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
            [get_vk_button(label="Отменить", color="primary")]
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

    def getAdminList(self, vkadminlist):
        adminList = ''
        print('=============================')
        for pers in vkadminlist:
            adminList += 'ID: ' + str(pers.id) + '\t| Name: ' + pers.flname + '\t| Super: ' + str(pers.superUser) + '\n\n'
        print(adminList)
        print('=============================')
        return adminList

    def sendFile(self, receiver, dfile, name):
        import requests
        import json
        vkapi = self.vk_session.get_api()
        upload_url = vkapi.docs.getMessagesUploadServer(peer_id=receiver)['upload_url']
        response = requests.post(upload_url, files={'file': open(dfile, 'rb')})
        result = json.loads(response.text)
        file = result['file']
        json = vkapi.docs.save(file=file, title=name, tags=[])
        owner_id = json['doc']['owner_id']
        doc_id = json['doc']['id']
        attach = 'doc' + str(owner_id) + '_' + str(doc_id)
        messages = vkapi.messages.send(user_id=receiver, attachment=attach, random_id='0')


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

        null_q_arr = DB_methods.getNullQuestionsFromDB()
        model = bot_logic.trainModel('QA.w2v', null_q_arr, restart=True)
        question_model = bot_logic.getQuestionModel(null_q_arr, model, loadOldModel=False)
        print('VK ready')
        while True:
            try:
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

                                elif vk_admin_list[admin_id].onMenu == 2:
                                    text_arr = str(event.text).split('___')
                                    if len(text_arr) == 2:
                                        new_qa = DB_methods.qa(0, text_arr[0], text_arr[1], nullForm=False)
                                        print(list(question_model.wv.vocab))
                                        model, question_model = DB_methods.addNewQAtoBase(new_qa)
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
                                        vkk = self.vk_session.get_api()
                                        res = vkk.users.get(user_ids=event.text)
                                        new_admin = self.getId(int(res[0]['id']), vk_admin_list)
                                        if new_admin == -1:
                                            new_user = _userVK(id= int(res[0]['id']), superUser=0, flname=str(res[0]['first_name'] + ' ' + res[0]['last_name']))
                                            vk_admin_list.append(new_user)

                                            addUser_VK(id=new_user.id, superUser=new_user.superUser, flname=new_user.flname)

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
                                                                'message': 'Введите корректную ссылку для добавления администратора',
                                                                'random_id': 0, 'keyboard': self.vk_mini_keyboard})
                                elif vk_admin_list[admin_id].onMenu == 4:
                                    try:
                                        vkk = self.vk_session.get_api()
                                        res = vkk.users.get(user_ids=event.text)
                                        new_admin = self.getId(int(res[0]['id']), vk_admin_list)
                                        if new_admin == -1:
                                            temp_user = _userVK(id=int(res[0]['id']), superUser=1, flname=str(res[0]['first_name'] + ' ' + res[0]['last_name']))
                                            vk_admin_list.append(temp_user)

                                            sup = 0
                                            if temp_user.superUser:
                                                sup = 1
                                            addUser_VK(id=temp_user.id, superUser=sup, flname=temp_user.flname)

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
                                                                'message': 'Введите корректный id для добавление супер администратора', #TODO: буст с адмена до супера кидает эксепт
                                                                'random_id': 0, 'keyboard': self.vk_mini_keyboard})

                                elif vk_admin_list[admin_id].onMenu == 5:
                                    try:
                                        vkk = self.vk_session.get_api()
                                        res = vkk.users.get(user_ids=event.text)
                                        admin_for_delete = self.getId(int(res[0]['id']), vk_admin_list)
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
                                        vkk = self.vk_session.get_api()
                                        res = vkk.users.get(user_ids=event.text)
                                        admin_for_clear = self.getId(int(res[0]['id']), vk_admin_list)
                                        if admin_for_clear != -1:
                                            vk_admin_list[admin_for_clear].superUser = False

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

                                elif vk_admin_list[admin_id].onMenu == 7:
                                    try:
                                        DB_methods.removeQuestionFromDB(int(event.text))
                                        self.vk_session.method('messages.send',
                                                               {'user_id': event.user_id,
                                                                'message': 'Вопрос удален',
                                                                'random_id': 0, 'keyboard': self.return_keyboard(
                                                                   vk_admin_list[admin_id])})
                                    except:
                                        self.vk_session.method('messages.send',
                                                               {'user_id': event.user_id,
                                                                'message': 'Введите корректный id',
                                                                'random_id': 0, 'keyboard': self.vk_mini_keyboard})

                            elif str(event.text) == "Добавить вопрос в базу данных":
                                self.vk_session.method('messages.send',
                                                       {'user_id': event.user_id,
                                                        'message': 'Введите вопрос в формате Вопрос ___ Ответ',
                                                        'random_id': 0, 'keyboard': self.vk_mini_keyboard})
                                vk_admin_list[admin_id].onMenu = 2
                            elif str(event.text) == "Удалить вопрос из базы данных":
                                self.vk_session.method('messages.send',
                                                       {'user_id': event.user_id,
                                                        'message': 'Введите id вопроса, который хотите удалить',
                                                        'random_id': 0, 'keyboard': self.vk_mini_keyboard})

                                vk_admin_list[admin_id].onMenu = 7
                            elif str(event.text) == "Помощь":
                                #TODO: ОТПРАВКА ФАЙЛА HSE_FAQ_BOT_Инструкция_для_администратора.pdf
                                _file = 'HSE_FAQ_BOT_admin.pdf'
                                self.sendFile(event.user_id, _file, 'Инструкция')

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
                                    admList = self.getAdminList(vk_admin_list)
                                    self.vk_session.method('messages.send',
                                                           {'user_id': event.user_id,
                                                            'message': 'Введите id человека, которому хотите снять права администратора\n' + admList,
                                                            'random_id': 0, 'keyboard': self.vk_mini_keyboard})
                                    vk_admin_list[admin_id].onMenu = 5
                                elif str(event.text) == "Удалить супер права":
                                    admList = self.getAdminList(vk_admin_list)
                                    self.vk_session.method('messages.send',
                                                           {'user_id': event.user_id,
                                                            'message': 'Введите id человека, которому хотите снять супер права, при этом человек останется администратором\n' + admList,
                                                            'random_id': 0, 'keyboard': self.vk_mini_keyboard})
                                    vk_admin_list[admin_id].onMenu = 6
                                elif str(event.text) == 'Загрузить список админов':
                                    _file = file_creator.createXLSFileOfUsers_VK()
                                    self.sendFile(event.user_id, _file, 'Список Админов')

                                elif str(event.text) == '/usersTG':
                                    _file = file_creator.createXLSFileOfUsers_TG()
                                    self.sendFile(event.user_id, _file, 'Список Админов')

                                elif str(event.text) == 'Загрузить список вопросов':
                                    _file = file_creator.createXLSFileOfQuestions()
                                    self.sendFile(event.user_id, _file, 'Список Вопросов')

                                else:
                                    answers = bot_logic.getAnswers(str(event.text), model, question_model, DB_methods.getListOfQAfromDB(),
                                                         addNewQuestionToModel=False)
                                    print(answers)
                                    self.vk_session.method('messages.send',
                                                           {'user_id': event.user_id,
                                                            'message': answers[0],
                                                            'random_id': 0, 'keyboard': self.vk_super_keyboard})
                            else:
                                answers = bot_logic.getAnswers(str(event.text), model, question_model, DB_methods.getListOfQAfromDB(),
                                                     addNewQuestionToModel=False)
                                print(answers)
                                self.vk_session.method('messages.send',
                                                       {'user_id': event.user_id,
                                                        'message': answers[0],
                                                        'random_id': 0, 'keyboard': self.vk_keyboard})

                        else:
                            answers = bot_logic.getAnswers(str(event.text), model, question_model, DB_methods.getListOfQAfromDB(),
                                                 addNewQuestionToModel=False)
                            print(answers)
                            self.vk_session.method('messages.send',
                                                   {'user_id': event.user_id,
                                                    'message': answers[0],
                                                    'random_id': 0, 'keyboard': self.vk_null_keyboard})
            except:
                print('connection lost. Trying to reconect...')
                time.sleep(1)