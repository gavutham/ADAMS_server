import mysql.connector
from datetime import date

#create a class for populating mysql values
class mysql_connector:
    
    #initializing the host, user, password and database
    def _init_(self,host,user,password,database):
        self.host = host
        self.user = user
        self.password = password 
        self.database = database
        self.cursor = self.init_mysql_conn()

    #initialize database_connection
    def init_mysql_conn(self):
        try:
            mydb = mysql.connector.connect(
                host = self.host,
                user = self.user,
                password =self.password,
                database = self.database
            )
            print('successfully_connected')
            self.db=mydb
            return mydb.cursor()
        except:
            print('error occured in setting connection with database')

    #fetch all values given a databse,tuple of values
    def fetchall(self,table_name):
        
        self.cursor.execute('select * from ' + table_name)

        results = self.cursor.fetchall()

        for values in results:
            print(values)

    #insert table given table_name,values type is list for 
    def insert_attendance(self,table_name,values:tuple):

        sql = 'INSERT INTO '+ table_name + ' (email, sub_code, prd, attd_date) VALUES ' + str(values)

        self.cursor.execute(sql)

        self.db.commit()

    def mark_attendance_mail_id(self,email,sub_code,prd):
        #function to add the attendance of each individual to the attendance table 

        #input is the (email,sub_code,prd,attd_date)
        #'student21@example.com','PHYS101',1

        #output data is added to db successfully
        #(7, 'student1@example.com', 'PHYS101', 1, datetime.date(2024, 3, 11))

        attd_date = str(date.today())

        print(attd_date)

        self.insert_attendance('attendance',(email,sub_code,prd,attd_date))

    def mark_attendance_lis_dic_students(self,json,sub_code,prd):
        #function to add the attendance of lis of dic of student emails to the attendance table 

        #input is the (json,sub_code,prd,attd_date)
        #'student21@example.com','PHYS101',1

        #output data is added to db successfully
        #(7, 'student1@example.com', 'PHYS101', 1, datetime.date(2024, 3, 11))

        for std_records in json:
            if std_records['att_verified'] == True:
                email = std_records['email']
                self.mark_attendance_mail_id(email, sub_code, prd)



my_db_connect = mysql_connector('localhost','root','password','attendance_management')

my_db_connect.fetchall('attendance')

my_db_connect.mark_attendance_lis_dic_students([{'year': 'I', 'department': 'MECH', 'section': 'A', 'email': 'test1@gmail.com', 'sid': '1IrUbH6dHpQ6HVigZ0Z51tgyVeL2', 'name': 'test1', 'uuid': '694005e8-dfc5-11ee-922b-c16ea0e293c0', 'pp_verify': False, 'bb_verify': False, 'ready': False, 'att_verified': False}, { 'year': 'I', 'department': 'MECH', 'section': 'A', 'email': 'test4@gmail.com', 'sid': '3l5J71uBhtcgqNxz5OMWzzvkfJ02', 'name': 'test4', 'uuid': '694005e9-dfc5-11ee-922b-c16ea0e293c0', 'pp_verify': False, 'bb_verify': False, 'ready': False, 'att_verified': True}],'PHYS101',1)

my_db_connect.fetchall('attendance')