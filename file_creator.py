import xlsxwriter
import VK_thread
import TG_thread
import DB_methods

def createXLSFileOfQuestions(path='QA.db'):
    file_name = 'QA.xlsx'
    questions = DB_methods.getListOfQAfromDB(path)
    workbook = xlsxwriter.Workbook(file_name)
    worksheet = workbook.add_worksheet(name='Main')
    row = 0

    worksheet.write_string(row, 0, "ID\t\t")
    worksheet.write_string(row, 1, "question\t\t")
    worksheet.write_string(row, 2, "answer\t\t")
    worksheet.write_string(row, 3, "zero form question\t\t")
    row += 1

    for _qa in questions:
        worksheet.write_number(row, 0, _qa.id)
        worksheet.write_string(row, 1, _qa.question)
        worksheet.write_string(row, 2, _qa.answer)
        worksheet.write_string(row, 3, _qa.null_question)
        row += 1
    workbook.close()
    return file_name
def createXLSFileOfUsers_TG(path='QA.db'):
    users = TG_thread.getUsersFromDB_TG(path)
    file_name = 'users_TG.xlsx'
    workbook = xlsxwriter.Workbook(file_name)
    worksheet = workbook.add_worksheet(name='Main')
    row = 0
    worksheet.write_string(row, 0, "TG login")
    worksheet.write_string(row, 1, "Super Admin")
    row += 1
    for _user in users:
        worksheet.write_string(row, 0, _user.login)
        worksheet.write_boolean(row, 1, _user.superUser)
        row += 1
    workbook.close()
    return file_name
def createXLSFileOfUsers_VK(path='QA.db'):
    users = VK_thread.getUsersFromDB_VK(path)
    file_name = 'users_VK.xlsx'
    workbook = xlsxwriter.Workbook(file_name)
    worksheet = workbook.add_worksheet(name='Main')
    row = 0

    worksheet.write_string(row, 0, "VK id")
    worksheet.write_string(row, 1, "Super Admin")
    worksheet.write_string(row, 2, "VK Name")
    row += 1
    for _user in users:
        worksheet.write_number(row, 0, _user.id)
        worksheet.write_boolean(row, 1, _user.superUser)
        worksheet.write_string(row, 2, _user.flname)
        row += 1
    workbook.close()
    return file_name