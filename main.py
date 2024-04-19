# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
from flask import Flask, request, make_response, jsonify
from fire_base import firebase_server
from mark_attendance import mark_attendance
from mongo import mongo
from mysql_Server import mysql_server
from pymongo import MongoClient
import threading 

import time

client = MongoClient('localhost', 27017)

db = client["adams_server_db"]
sessions_col = db["sessions"]
beacons_col = db["beacons"]

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
    timeout_thread = threading.Thread(target=stop_session_thread, args=(year, dep, sec))
    timeout_thread.start()
    if mongo.is_session_started(sessions_col, year, dep, sec):
        return "Session already started!", 404
    session_students = firebase_server.generate_sec_uuids(year, dep, sec)
    sessions_col.insert_many(session_students)
    mark_attendance.wait_for_login_threshold(year, dep, sec, sessions_col) # Waits until 80% threshold reached.
    # mark_attendance.pp_start_session(year, dep, sec)
    ready_uuids = [i["uuid"] for i in
                   mongo.get_session_students(sessions_col, year, dep, sec)
                   if (i["ready"]) == True] # Only ready.
    return jsonify(ready_uuids), 200
    # return "Done!", 200
    # return at_dict # for testing


def stop_session_thread(year, dep, sec):
    time.sleep(180)
    stop_session(year, dep, sec)


@app.route("/stop-session/<year>/<dep>/<sec>")
def stop_session(year, dep, sec):
    if mongo.is_session_started(sessions_col, year, dep, sec):
        std_data = mongo.get_session_students(sessions_col, year, dep, sec)
        data = [{"email": i["email"], "att_verified": i["att_verified"]}
                    for i in std_data
                ]
        mysql_server.my_db_connect.mark_attendance_lis_dic_students(data, "test-sub", 9)
        sessions_col.delete_many({"year": year, "department": dep, "section": sec})
        return "Session stopped!", 200
    else:
        return "Session not started yet!", 404

@app.route("/is-session-started/<year>/<dep>/<sec>")
def is_session_started(year, dep, sec):
    if mongo.is_session_started(sessions_col, year, dep, sec):
        return "true";
    else:
        return "false";


@app.route("/post-beacon-details/<ip>/<classroom>", methods=["POST"])
def post_beacon_details(ip, classroom):
    if beacons_col.find({"ip": ip}): # If a beacon server with ip already exists.
        beacons_col.update_one({"ip": ip}, {"$inc": {"classroom": classroom}}) # update classroom.
    else:
        beacons_col.insert_one({"ip": ip, "classroom": classroom}) # init beacon.
    return "Done!", 200


@app.route("/pp-status-verify/<year>/<dep>/<sec>/<email>")
def pp_status_verify(year, dep, sec, email):
    if not mongo.is_session_started(sessions_col, year, dep, sec):
        return "Session not started!", 403
    else:
        student = sessions_col.find_one({"year": year, "department": dep, "section": sec, "email": email})
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
    print(req)

    req_pp_list = list(req) # list of dictionaries with keys uuid and rssi parsed from request.
    std_data = mongo.get_session_students(sessions_col, year, dep, sec)
    std_uuids = [i["uuid"] for i in std_data]
    print("STD UUIDS:")
    print(std_uuids)

    # Parse and add to pp_list
    pp_sorted = sorted(req_pp_list, key=lambda i: i['rssi'], reverse=True)
    pp_top5 = []
    for i in pp_sorted:
        if i["uuid"] in std_uuids and len(pp_top5) < 5:
            pp_top5.append(i)
    print(pp_top5)

    for i in pp_top5[:1]:
        # att_verified = True is hardcoded. Should happen only after both bb-verify and face-auth is done.
        sessions_col.update_one({"uuid": i["uuid"]}, {"$set": {"pp_verify": True, "att_verified": True}})
    # pp_list[year+dep+sec].update(req_pp_list)
    # Set pp_verify = True for closest 5 students.
    return pp_top5, 200


if __name__ == '__main__':
    app.run(host='144.91.106.164', port=8000, debug=True)