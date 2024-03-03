# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
from flask import Flask, request, make_response
from fire_base import firebase_server
from mark_attendance import mark_attendance
from mongo import mongo
from pymongo import MongoClient

import time


client = MongoClient('localhost', 27017, username='root', password='1234')

db = client["adams_server_db"]
sessions_col = db["sessions"]

# at_dict = dict()
pp_list = dict()

app = Flask(__name__)

@app.route('/')
def hello_world():
    #have to give the variables to the display _students dynamically in post request
    std = firebase_server.display_students('I','MECH','A')
    return std


@app.route("/<year>/<dep>/<sec>", methods=["GET"])
def get_students(year, dep, sec):
    return mongo.get_session_students(sessions_col, year, dep, sec), 200


@app.route("/get-student-uuid/<year>/<dep>/<sec>/<email>", methods=["GET"])
def get_student_uuid(year, dep, sec, email):
    std_data = mongo.get_session_students(sessions_col, year, dep, sec)
    if not(std_data):
        return 403
    else:
        for i in std_data:
            if i["email"] == email:
                sessions_col.update_one({"email": email}, {"$set": {"ready": True}})
                return str(i["uuid"]), 200
        return "Student not found!", 404


# Top level function - TEACHER APP
@app.route("/start-session/<year>/<dep>/<sec>")
def start_session(year, dep, sec):
    if mongo.is_session_started(sessions_col, year, dep, sec):
        return "Session already started!", 404
    session_students = firebase_server.generate_sec_uuids(year, dep, sec)
    sessions_col.insert_many(session_students)
    mark_attendance.wait_for_login_threshold(year, dep, sec, sessions_col) # Waits until 80% threshold reached.
    # mark_attendance.pp_start_session(year, dep, sec)
    ready_uuids = [i["uuid"] for i in
                   mongo.get_session_students(sessions_col, year, dep, sec)
                   if (i["ready"]) == True] # Only ready.
    return ready_uuids, 200
    # return "Done!", 200
    # return at_dict # for testing


@app.route("/stop-session/<year>/<dep>/<sec>")
def stop_session(year, dep, sec):
    if mongo.is_session_started(sessions_col, year, dep, sec):
        sessions_col.delete_many({"year": year, "department": dep, "section": sec})
        return "Session stopped!", 200
    else:
        return "Session not started yet!", 404


# @app.route("/pp-verify/<year>/<dep>/<sec>/<email>")
# def pp_verify(year, dep, sec, email):
#     if not (year+dep+sec in at_dict):
#         return "Session not started yet!", 403;
#     else:
#         students = at_dict[year+dep+sec]
#         for i in students:
#             if (i["email"] == email):
#                 i["pp_verify"] = True;
#         print(at_dict)
#         resp = make_response("PP Verified", 200)
#         resp.set_cookie('email', email)
#         return resp


# # Student app
# @app.route("/ready/<year>/<dep>/<sec>/<email>")
# def ready(year, dep, sec, email):
#     if mongo.is_session_started(sessions_col, year, dep, sec):
#         sessions_col.update_one({"email": email}, {"$set": {"ready": True}})
#         return "Ready status marked.", 200
#     else:
#         return "Session not started!", 403


@app.route("/pp-status-verify/<year>/<dep>/<sec>/<email>")
def pp_status_verify(year, dep, sec, email):
    if not mongo.is_session_started(sessions_col, year, dep, sec):
        return "Session not started!", 403
    else:
        student = sessions_col.find_one({"year": year, "department": dep, "section": sec})
        if student["pp_verify"] == True:
            return "true", 200
        else:
            return "false", 200


# PP-VERIFY - Accessed by teacher at the first. Then accessed by students.
@app.route("/pp-verify/<year>/<dep>/<sec>", methods=["POST"])
def pp_verify(year, dep, sec):
    if not mongo.is_session_started(sessions_col, year, dep, sec):
        return "Session not started!", 403
    req = request.get_json()

    req_pp_list = list(req) # list of dictionaries with keys uuid and rssi parsed from request.

    # Parse and add to pp_list
    pp_top5 = sorted(req_pp_list, key=lambda i: i['rssi'], reverse=True)[:5]
    print(pp_top5)

    for i in pp_top5:
        sessions_col.update_one({"uuid": i["uuid"]}, {"$set": {"pp_verify": True}})
    # pp_list[year+dep+sec].update(req_pp_list)
    # Set pp_verify = True for closest 5 students.
    return pp_top5, 200


# @app.route("/test-time/<timeout>")
# def test_timeout(timeout):
#     time.sleep(int(timeout))
#     return "Success. We waited for {} seconds!".format(timeout), 200;


if __name__ == '__main__':
    app.run(host='192.168.29.95', port=5000, debug=True)