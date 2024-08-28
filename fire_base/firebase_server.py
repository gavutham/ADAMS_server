import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from time import time
from datetime import date
from firebase_admin import db
import os
from dotenv import load_dotenv
import json
import uuid as uuid_gen

load_dotenv()
firebaseKey = json.loads(os.getenv("FIREBASE_KEY"))

cred_obj = credentials.Certificate(firebaseKey)

firebase_admin = firebase_admin.initialize_app(cred_obj, {'databaseURL': "https://adams-a4aae-default-rtdb.asia-southeast1.firebasedatabase.app"})

firestore_db = firestore.client()


def get_rcd(std):
    users_ref = firestore_db.collection(std)
    docs = users_ref.stream()
    lis = []

    for doc in docs:
        lis.append(doc.to_dict())

    return lis


def generate_sec_uuids(year,department,section,std='students'):
    std_records = get_rcd(std)
    req_stdlis = []

    for std in std_records:
        if std['year'] == year and std['department'] == department and std['section'] == section:
            #adding uuid to the students
            uuid = str(uuid_gen.uuid1())
            std['uuid'] = uuid
            std['pp_verify'] = std['ready'] = False; # ready = logged in
            # std['bb_verify'] = True; # Default considered to be inside classroom.
            std["pp_rssi"] = std["bb_rssi"] = -1000000000
            print(std)
            req_stdlis.append(std)
    return req_stdlis


# print(generate_sec_uuids('I','MECH','A','students'))

def set_attendance_data(year, department, section, present, absent):
    data = {
        "time": firestore.firestore.SERVER_TIMESTAMP,
        "present": present,
        "absent": absent,
        "year": year,
        "department": department,
        "section": section
    }

    current_millis = str(time())
    today = str(date.today())

    firestore_db.collection("attendance").document(year).collection(department).document(section).collection(today).document(current_millis).set(data)


def set_attendance_flag(year, department, section, state):
    data = {
        section: state
    }

    url = (f"{year}/{department}")
    print(url)
    ref = db.reference(url)

    ref.update(data)


def is_session_started(year, department, section):
    flag_ref = db.reference(f"{year}/{department}/{section}")
    return flag_ref.get()


def initiate_session(year, department, section, studentsData):
    data = {
        "students": studentsData,
        "ips": []
    }

    session_ref = db.reference(f"/sessions/{year+department+section}")
    session_ref.set(data)


def get_session_students(year, department, section):
    response = get_session_details(year, department, section)

    return response["students"]

def get_session_ips(year, department, section):
    response = get_session_details(year, department, section)

    try:
        return response["ips"]
    except KeyError:
        return []


def update_session_students(year, department, section, data): 
    session_ref = db.reference(f"/sessions/{year+department+section}")
    
    session_ref.update({
        "students": data
    })


def get_session_details(year, department, section):
    session_ref = db.reference(f"/sessions/{year+department+section}")
    return session_ref.get()


def get_session_details_with_classname(classname):
    session_ref = db.reference(f"/sessions/{classname}")
    return session_ref.get()

def update_session_ips(classname, data):
    session_ref = db.reference(f"/sessions/{classname}")
    
    return session_ref.update({
        "ips": data
    })
