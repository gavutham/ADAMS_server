import firebase_admin
from firebase_admin import credentials, firestore, db as realtime_db
from uuid_gen import uuid_generator


cred_obj = credentials.Certificate('D:/works/python projects/ADAMS_server/creds.json')
config = {'databaseURL': 'https://adams-a4aae-default-rtdb.asia-southeast1.firebasedatabase.app'}
default_app = firebase_admin.initialize_app(cred_obj, config)

db = firestore.client()


def get_rcd(std):
    users_ref = db.collection(std)
    docs = users_ref.stream()
    lis = []

    for doc in docs:
        lis.append(doc.to_dict())

    return lis


def set_attendance_state(year, dept, sec, value):
    path = f'{year}/{dept}'
    print(path)
    ref = realtime_db.reference("I/MECH")
    ref.update({
        sec: value
    })

    return


def generate_sec_uuids(year,department,section,std='students'):
    std_records = get_rcd(std)
    req_stdlis = []
    for std in std_records:
        if std['year'] == year and std['department'] == department and std['section'] == section:
            #adding uuid to the students
            # uuid = uuid_generator.generate_uuid().hex
            uuid = str(uuid_generator.generate_uuid())
            std['uuid'] = uuid
            std['pp_verify'] = std['bb_verify'] = std['ready'] = std['att_verified'] = False; # ready = logged in
            print(std)
            req_stdlis.append(std)
    return req_stdlis
