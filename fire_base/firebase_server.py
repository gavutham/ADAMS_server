import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from uuid_gen import uuid_generator

cred_obj = credentials.Certificate('credentials.json')
default_app = firebase_admin.initialize_app(cred_obj)

db = firestore.client()


def get_rcd(std):
    users_ref = db.collection(std)
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
            # uuid = uuid_generator.generate_uuid().hex
            uuid = str(uuid_generator.generate_uuid())
            std['uuid'] = uuid
            std['pp_verify'] = std['ready'] = std['att_verified'] = False; # ready = logged in
            std['bb_verify'] = True; # Default considered to be inside classroom.
            std["pp_rssi"] = float('inf') * -1
            print(std)
            req_stdlis.append(std)
    return req_stdlis


# print(generate_sec_uuids('I','MECH','A','students'))
