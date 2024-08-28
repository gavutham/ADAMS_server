# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
import requests
from flask import Flask, request, make_response, jsonify
from fire_base import firebase_server
from fire_base.firebase_server import set_attendance_data, set_attendance_flag, is_session_started, initiate_session, get_session_students, update_session_students, get_session_details, get_session_details_with_classname, update_session_ips, get_session_ips
from mark_attendance import mark_attendance
from mongo import mongo
import threading 
import time


app = Flask(__name__)


@app.route('/')
def hello_world():
    return "Hello world!"

#done
@app.route("/get-student-uuid/<year>/<dep>/<sec>/<email>", methods=["GET"])
def get_student_uuid(year, dep, sec, email):
    std_data = get_session_students(year, dep, sec)
    updated_data = []
    uuid = ""

    if not(std_data):
        return 403
    else:
        for i in std_data:
            if i["email"] == email:
                uuid = i["uuid"]
                i["ready"] = True
                updated_data.append(i)
            else:
                updated_data.append(i)

    if uuid == "":
        return "Student not found!", 404

    update_session_students(year, dep, sec, updated_data)
    return uuid, 200

#done
# Top level function - TEACHER APP
@app.route("/start-session/<year>/<dep>/<sec>")
def start_session(year, dep, sec):
    timeout_thread = threading.Thread(target=stop_session_thread, args=(year, dep, sec))
    timeout_thread.start()

    if is_session_started(year, dep, sec):
        return "Session already started!", 404
      
    session_students = firebase_server.generate_sec_uuids(year, dep, sec)
    initiate_session(year, dep, sec, session_students)

    set_attendance_flag(year, dep, sec, True)  
    
    return "Success", 200

#done
def stop_session_thread(year, dep, sec):
    time.sleep(180)
    stop_session(year, dep, sec)


@app.route("/stop-session/<year>/<dep>/<sec>")
def stop_session(year, dep, sec):

    if is_session_started(year, dep, sec):
        std_data = get_session_students(year, dep, sec)
        print("\nSTOPPING SESSION!\n")
        present = []
        absent = []
        for i in std_data:
            if i["pp_verify"]:
                present.append(i["email"])
            else:
                absent.append(i["email"])
        
        print("\nPRESENT:\n")
        print(present)
        print("\nABSENT\n")
        print(absent)

        set_attendance_data(year, dep, sec, present, absent) #store the result in firebase
        set_attendance_flag(year, dep, sec, False)
        
        return "Session stopped!", 200
    else:
        return "Session not started yet!", 404

#done
@app.route("/is-session-started/<year>/<dep>/<sec>")
def is_session_start(year, dep, sec):
    if is_session_started(year, dep, sec):
        return "true";
    else:
        return "false";


@app.route("/post-beacon-details/<ip>/<classroom>", methods=["POST"])
def post_beacon_details(ip, classroom):
    ips = []
    try:
        ips = get_session_details_with_classname(classroom)["ips"]
    except KeyError:
        ips = []
    ips.append(ip)

    update_session_ips(classroom, ips)

    return "Done!", 200


@app.route("/pp-status-verify/<year>/<dep>/<sec>/<email>")
def pp_status_verify(year, dep, sec, email):
    if not is_session_started(year, dep, sec):
        return "Session not started!", 403
    else:
        students = get_session_students(year, dep, sec)
        student = list(filter(lambda x: x["email"] == email, students))[0]
        
        if student["pp_verify"] == True:
            return "true", 200
        else:
            return "false", 200


# PP-VERIFY - Accessed by teacher at the first. Then accessed by students.
@app.route("/pp-verify/<year>/<dep>/<sec>", methods=["POST"])
def pp_verify(year, dep, sec):
    yds = year+dep+sec
    if not is_session_started(year, dep, sec):
        return "Session not started!", 403
    req = request.get_json()

    req_pp_list = list(req) # list of dictionaries with keys uuid and rssi parsed from request.
    std_data = get_session_students(year, dep, sec)
    std_uuids = [i["uuid"] for i in std_data]
    print("STD UUIDS:")
    print(std_uuids)

    # Parse and add to pp_list
    pp_valid = [i for i in req_pp_list if i["uuid"] in std_uuids]
    pp_sorted = sorted(pp_valid, key=lambda i: i["rssi"], reverse=True)

    count = 0;
    pp_top = []

    updated_students = []

    for i in pp_sorted:
        student = list(filter(lambda x: x["uuid"] == i["uuid"], std_data))[0]

        updated = False

        if (student["bb_rssi"] < i["rssi"] and count < 2):
            updated = True
            student["pp_verify"] = True
            count += 1

        if (student["pp_rssi"] < i["rssi"]):
            updated = True
            student["pp_rssi"] = i["rssi"]
        
        if (updated):
            updated_students.append(student)

    
    data_to_write = []

    for stud in std_data:
        student = list(filter(lambda x: x["uuid"] == stud["uuid"], updated_students))
        if(len(student) > 0):
            data_to_write.append(student[0])
        else:
            data_to_write.append(stud)
            
    

    update_session_students(year, dep, sec, data_to_write)

    return pp_top, 200


@app.route("/get-beacon-ips/<year>/<dep>/<sec>", methods=["GET"])
def get_beacon_ips(year, dep, sec):
    ips = get_session_ips(year, dep, sec)
    return jsonify(ips)
 

@app.route("/bb-verify/<year>/<dep>/<sec>", methods=["POST"])
def bb_verify(year, dep, sec):

    req = request.get_json()
    print(req)

    std_data = get_session_students(year, dep, sec)


    updated_students = []

    for scan in req:
        scan_results = scan["scan_results"]
        for device in scan_results:
            print(device)
            student = list(filter(lambda x: x["uuid"] == device["uuid"].lower(), std_data))[0]
            
            if (student["bb_rssi"] < device["rssi"]):
                student["bb_rssi"] = device["rssi"]
                updated_students.append(student)

    data_to_write = []

    for stud in std_data:
        student = list(filter(lambda x: x["uuid"] == stud["uuid"], updated_students))
        if(len(student) > 0):
            data_to_write.append(student[0])
        else:
            data_to_write.append(stud)
            

    update_session_students(year, dep, sec, data_to_write)\
    
    print("Req: ", req)
    return "Done!", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
