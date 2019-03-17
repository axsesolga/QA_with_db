import os
import sqlite3
from shutil import copyfile
import multiprocessing

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

    vk_token = "3100a6756c1f3f6ec91dfcd3212ffc664368f51dc77de964ca67c02e0dd8a255a0f3e78477b845f71a55d"
    vk_session = vk_api.VkApi(token=vk_token)
    longpoll = VkLongPoll(vk_session)

    def run(self):
        vk_admin_list = getUsersFromDB_VK()

        null_q_arr = DB_methods.getNullQuestionsFromDB()
        model = bot_logic.trainModel('QA.w2v', null_q_arr, restart=True)
        question_model = bot_logic.getQuestionModel(null_q_arr, model, loadOldModel=False)
        print('VK ready')
        while True:
            for event in self.longpoll.listen():
                if event.type == VkEventType.MESSAGE_NEW and event.from_user and not event.from_me:
                    user_thread = UserThread(event, vk_admin_list, model, question_model, self.vk_session)
                    user_thread.start()


class UserThread(threading.Thread):
    def __init__(self, event, vk_admin_list, model, question_model, vk_session):
        threading.Thread.__init__(self)
        self.local_event = event
        self.local_vk_admin_list = vk_admin_list
        self.local_model = model
        self.local_question_model = question_model
        self.vk_session = vk_session
        print(event.text)



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
        print("here")
        self.vk_keyboard = json.dumps(self.vk_keyboard, ensure_ascii=False).encode('utf-8')
        self.vk_super_keyboard = json.dumps(self.vk_super_keyboard, ensure_ascii=False).encode('utf-8')
        self.vk_mini_keyboard = json.dumps(self.vk_mini_keyboard, ensure_ascii=False).encode('utf-8')
        self.vk_null_keyboard = json.dumps(self.vk_null_keyboard, ensure_ascii=False).encode('utf-8')

        self.vk_super_keyboard = str(self.vk_super_keyboard.decode('utf-8'))
        self.vk_keyboard = str(self.vk_keyboard.decode('utf-8'))
        self.vk_mini_keyboard = str(self.vk_mini_keyboard.decode('utf-8'))
        self.vk_null_keyboard = str(self.vk_null_keyboard.decode('utf-8'))

        admin_id = self.getId(self.local_event.user_id, self.local_vk_admin_list)
        import datetime
        print(datetime.datetime.now())
        time.sleep(100)
        print(datetime.datetime.now())
