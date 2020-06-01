"""---------------------------------------------------------------
                VITask | A Dynamic VTOP API server

        "Any fool can write code that a computer can understand.
        Good programmers write code that humans can understand."
------------------------------------------------------------------"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import db
from PIL import Image
from PIL import ImageFilter
from datetime import timezone,datetime,timedelta
import requests
import urllib3
import time
import pickle
import re
import os
import random
import hashlib
import bcrypt
import requests
import json
import time
import base64
import zipfile
from urllib.request import urlretrieve
import sys
from sys import platform as _platform
from vtop import generate_session
from vtop import get_attandance
from vtop import get_student_profile
from vtop import get_acadhistory
from vtop import get_timetable
from vtop import get_marks
from multiprocessing import Process
from crypto import magichash
from crypto import magiccheck
#For disabling warings this will save msecs..lol
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Initialize Flask app
app = Flask(__name__)

# Set the port for Flask app
port = int(os.environ.get('PORT', 5000))

# Change this to your secret key (can be anything, it's for extra protection)
app.secret_key = 'canada$God7972#'

# Initialize Firebase app
firebase_admin.initialize_app(options={'databaseURL': 'https://vitask.firebaseio.com/'})


# Functions for Moodle begin here
MOODLE_LOGIN_URL = r"https://moodlecc.vit.ac.in/login/index.php"

def get_timestamp():
    """
    Utility function to generate current timstamp
    """
    dt = datetime.now() - timedelta(15)
    utc_time = dt.replace(tzinfo = timezone.utc) 
    return int(utc_time.timestamp())

def get_moodle_session(username, password):
    """
    This function logins in moodle and gets session Id 
    return session object and sess_key
    """
    sess = requests.Session()
    #Moodle passes anchor secretly idk why lol
    payload = {
        "username" : username,
        "password" : password,
        "anchor"   : ""
    }

    #Using verify = False is deadly but moodle's a bitch
    login_text = sess.post(MOODLE_LOGIN_URL,data=payload, verify=False).text

    #TODO : Check is password is correct or not
    #For finding session key. This is where moodle sucks lol. Didn't use useragent check and cookies. F U
    sess_key_index = login_text.find("sesskey")
    sess_key = login_text[sess_key_index+10:sess_key_index+20]

    return sess, sess_key

def get_dashboard_json(sess, sess_key):
    """
    This function returns dashboard json data fields array
    """
    #TODO:Find a better method to format string
    DASHBOARD_URL = "https://moodlecc.vit.ac.in/lib/ajax/service.php?sesskey="+sess_key+"&info=core_calendar_get_action_events_by_timesort"
    
    dashboard_payload = [
        {
            "index":0,
            "methodname":"core_calendar_get_action_events_by_timesort",
            "args":{
                "limitnum":20,
                "timesortfrom":get_timestamp()
                }
        }
    ]

    dashboard_text = sess.post(DASHBOARD_URL, data = json.dumps(dashboard_payload), verify= False).text
    dashboard_json = json.loads(dashboard_text)
    try:
        due_items = dashboard_json[0]["data"]["events"]
    except:
        due_items = None
    return due_items
# Functions for Moodle end here


""" ---------------------------------------------------------------

        We keep our code DRY(Do not repeat yourselves). 
        Thus we have implemented functions ;)

---------------------------------------------------------------"""

def ProfileFunc():
    ref = db.reference('vitask')
    temp_dict = ref.child('profile').child('profile-'+session['id']).child(session['id']).get()
    name = temp_dict['Name']
    school = temp_dict['School']
    branch = temp_dict['Branch']
    program = temp_dict['Program']
    regno = temp_dict['RegNo']
    appno = temp_dict['AppNo']
    email = temp_dict['Email']
    proctoremail = temp_dict['ProctorEmail']
    proctorname = temp_dict['ProctorName']
    api = temp_dict['API']
    
    return (name, school, branch, program, regno, appno, email, proctoremail, proctorname, api)

def parallel_timetable(sess, username, id):
    ref = db.reference('vitask')
    temp = ref.child("timetable").child('timetable-'+id).child(id).child('Timetable').get()
    if(temp is None):
        days = {}
        days, check_timetable = get_timetable(sess, username, id)
        if(check_timetable == "False"):
            session['timetable'] = 0
        else:
            session['timetable'] = 1
    
def parallel_acadhistory(sess, username, id):
    ref = db.reference('vitask')
    temp = ref.child("acadhistory").child('acadhistory-'+id).child(id).child('AcadHistory').get()
    if(temp is None):
        acadHistory = {}
        curriculumDetails = {}
        grades, check_grades = get_acadhistory(sess,username,id)
        if(check_grades == "False"):
            session['acadhistory'] = 0
        else:
            acadHistory = grades['AcadHistory']
            curriculumDetails = grades['CurriculumDetails']
            session['acadhistory'] = 1
        
def parallel_attendance(sess, username, id):
    attend = {}
    q = {}
    attend, q, check_attendance = get_attandance(sess, username, id)
    if(check_attendance == "False"):
        session['classes'] = 0
    else:
        session['classes'] = 1

def parallel_marks(sess, username, id):
    marksDict = {}
    marksDict, check_marks = get_marks(sess, username, id)
    if(check_marks == "False"):
        session['marks'] = 0
    else:
        session['marks'] = 1
    
def runInParallel(*fns):
    proc = []
    for fn in fns:
        p = Process(target=fn)
        p.start()
        proc.append(p)
    for p in proc:
        p.join()


"""---------------------------------------------------------------
                    Functions end here.
---------------------------------------------------------------"""

"""---------------------------------------------------------------
                  Error Pages begin here.
---------------------------------------------------------------"""
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

"""---------------------------------------------------------------
                  Error Pages end here.
---------------------------------------------------------------"""



"""---------------------------------------------------------------
                    VITask API code begins from here

                Note: This code is the heart of VITask,
                think twice before modifying anything ;)

------------------------------------------------------------------"""

#/api/account 
@app.route('/api/account', methods=['GET','POST'])
def getAccount():
    """
    API has been changed to accept only POST requests. Path of API has been changed.
    Now the body of POST must be 
    {
        "username" : 17BECXXXX,
        "password" : password
    }
    """
    # First check if query is okay or not
    data = json.loads(request.data)
    username = data.get("username",None)
    password = data.get("password",None)
    
    if username is None or password is None:
        return jsonify({
            "error" : "Incorrect API Request",
            "code"  : "400" # Bad request
        })
    
    # Now began actual work
    username = username.upper()
    
    # This API is only to get user account information and the required header.
    valid = True
    try:
        sess, valid = generate_session(username, password)
    except Exception as e:
        return jsonify({
            "error" : "Something broke",
            "code"  : "500"
        })
    if not valid:
        # Password incorrect
        return jsonify({
            "error" : "Incorrect Password"
        })
    ref = db.reference('vitask')
    try:
        profile = {}
        profile, check_profile = get_student_profile(sess, username)

        if(check_profile == False):
            return jsonify({"Error": "Internal Error.Please try again."})
    finally:
        appno = profile['appNo']
        header_value = magichash(appno)
        
        temp = ref.child("account").child('account-'+appno).child(appno).get()

        if(temp is None):
            date = datetime.datetime.now()
            current_date = date.strftime("%d/%m/%Y, %H:%M:%S")
            tut_ref = ref.child("account")
            new_ref = tut_ref.child('account-'+appno)
            new_ref.set({
                appno: {
                    'X-VITASK-API': header_value,
                    'Name': profile['name'],
                    'RegNo': profile['regNo'],
                    'Account-Type': 'Free',
                    'API-Calls': 0,
                    'Start-Date': current_date,
                    'End-Date': 'N/A'
                }
            })
            return jsonify({
                'X-VITASK-API': header_value,
                'Name': profile['name'],
                'RegNo': profile['regNo'],
                'Account-Type': 'Free',
                'API-Calls': 0,
                'Start-Date': current_date,
                'End-Date': 'N/A'
            }) 
        else:
            return jsonify({
                'X-VITASK-API': temp['X-VITASK-API'],
                'Name': temp['Name'],
                'RegNo': temp['RegNo'],
                'Account-Type': temp['Account-Type'],
                'API-Calls': temp['API-Calls'],
                'Start-Date': temp['Start-Date'],
                'End-Date': temp['End-Date']
            })

#/api/gettoken 
@app.route('/api/gettoken', methods=['GET','POST'])
def getToken():
    """
    API has been changed to accept only POST requests. Path of API has been changed.
    Headers must contain a value
    {
        "X-VITASK-API": "Secret key"   (From /api/account)
    }
    Now the body of POST must be 
    {
        "username" : 17BECXXXX,
        "password" : password,
    }
    """
    # First check if query is okay or not
    data = json.loads(request.data)
    username = data.get("username",None)
    password = data.get("password",None)
    
    if username is None or password is None:
        return jsonify({
            "error" : "Incorrect API Request",
            "code"  : "400" # Bad request
        })
    check_header = magiccheck(request.headers.get('X-VITASK-API'))
    if(check_header == "False"):
        return jsonify({
            "error" : "Invalid Header",
            "code"  : "403" # Unauthorised
        })
    # Now began actual work
    username = username.upper()
    
    # This API is only to get user token and get personal details. For syncing details, there will be a seperate API
    # This assumes that token is None just like previous authenticate
    valid = True
    try:
        sess, valid = generate_session(username, password)
    except Exception as e:
        return jsonify({
            "error" : "Something broke",
            "code"  : "500"
        })
    if not valid:
        # Password incorrect
        return jsonify({
            "error" : "Incorrect Password"
        })
    ref = db.reference('vitask')
    try:
        profile = {}
        profile, check_profile = get_student_profile(sess, username)
        session['id'] = profile['appNo']
        session['name'] = profile['name']
        session['reg'] = profile['regNo']
        session['loggedin'] = 1
        if(check_profile == "False"):
            return jsonify({"Error": "Internal Error in fetching profile.Please try again."})
    finally:
        name, school, branch, program, regno, appno, email, proctoremail, proctorname, api = ProfileFunc()
        # Timetable,Attendance,Acadhistory and Marks fetching in parallel
        try:
            runInParallel(parallel_timetable(sess, username, session['id']), parallel_attendance(sess, username, session['id']), parallel_acadhistory(sess, username, session['id']), parallel_marks(sess, username, session['id'])) 
        finally:
            # API Calls logging
            temp = ref.child("account").child('account-'+appno).child(appno).get()
            count = int(temp['API-Calls']) + 1
            tut_ref = ref.child("account")
            new_ref = tut_ref.child('account-'+appno)
            new_ref.set({
                appno: {
                    'X-VITASK-API': temp['X-VITASK-API'],
                    'Name': temp['Name'],
                    'RegNo': temp['RegNo'],
                    'Account-Type': temp['Account-Type'],
                    'API-Calls': count,
                    'Start-Date': temp['Start-Date'],
                    'End-Date': temp['End-Date']
                }
            })
            return jsonify({'Name': name,'School': school,'Branch': branch,'Program': program,'RegNo': regno,'AppNo': appno,'Email': email,'ProctorEmail': proctoremail,'ProctorName': proctorname,'APItoken': api})

# /api/vtop/sync
@app.route('/api/vtop/sync', methods=['POST'])
def sync():
    """
    POST Route
    This route will be used to sync all the details, like attendance and marks. Timetable is not required to updated.
    For creating a hard refresh (update the timetable, acad history) pass a parameter as compleeteRefresh true
    Headers must contain a value
    {
        "X-VITASK-API": "Secret key"   (From /api/account)
    }
    Now the body of POST must be 
    {
        "token" : "Your_API_Token"  # Required
        "username" : "Registration Number" # Required
        "password" : "Password"  #Required
        "hardRefresh" : "true"      # Not Complusory
    }
    """
    data = json.loads(request.data)
    username = data.get("username",None)
    password = data.get("password",None)
    refresh = data.get("hardRefresh",None)
    user_token = data.get("token",None)
    # First check the headers
    if username is None or password is None:
        return jsonify({
            "error" : "Incorrect API Request",
            "code"  : "400" # Bad request
        })
    if user_token is None:
        return jsonify({
            "error" : "Unauthorised. Get token from /api/getoken",
            "error" : "403" # Unauthorised
        })
    check_header = magiccheck(request.headers.get('X-VITASK-API'))
    if(check_header == "False"):
        return jsonify({
            "error" : "Invalid Header",
            "code"  : "403" # Unauthorised
        })
    
    username = username.upper()
    if refresh is None or not refresh:
        # Only update Attendance and Marks
        # Frist Decode the token
        temptoken = user_token.encode('ascii')
        try:
            appno = base64.b64decode(temptoken)
        except:
            return jsonify({
                'error': 'Invalid API Token. Get Token from /api/getoken',
                'code' : "400" # bad request
            })
        key = appno.decode('ascii')
        valid = True
        sess = None
        try:
            sess, valid = generate_session(username, password)
        except Exception as e:
            return jsonify({
                "error" : "Something broke",
                "code"  : "500"
            })
        if not valid:
            # Password incorrect
            return jsonify({
                "error" : "Incorrect Password"
            })
        attendance, q, check_attendance = get_attandance(sess, username, key)
        marks, check_marks = get_marks(sess, username, key)
        if(check_attendance == False):
            return jsonify({"Error": "Internal Error in fetching Attendance.Please try again."})
        if(check_marks == False):
            return jsonify({"Error": "Internal Error in fetching Marks.Please try again."})
        
        ref = db.reference('vitask')
        # API Calls logging
        temp = ref.child("account").child('account-'+key).child(key).get()
        count = int(temp['API-Calls']) + 1
        tut_ref = ref.child("account")
        new_ref = tut_ref.child('account-'+key)
        new_ref.set({
            key: {
                'X-VITASK-API': temp['X-VITASK-API'],
                'Name': temp['Name'],
                'RegNo': temp['RegNo'],
                'Account-Type': temp['Account-Type'],
                'API-Calls': count,
                'Start-Date': temp['Start-Date'],
                'End-Date': temp['End-Date']
            }
        })
        
        return jsonify({
            "attendance": attendance,
            "marks" : marks
        })
    else:
        # It is a hard refresh. Get Timetable and Acad History also
        # Frist Decode the token
        temptoken = user_token.encode('ascii')
        try:
            appno = base64.b64decode(temptoken)
        except:
            return jsonify({
                'error': 'Invalid API Token. Get Token from /api/getoken',
                'code' : "400" # bad request
            })
        key = appno.decode('ascii')
        valid = True
        sess = None
        try:
            sess, valid = generate_session(username, password)
        except Exception as e:
            return jsonify({
                "error" : "Something broke",
                "code"  : "500"
            })
        if not valid:
            # Password incorrect
            return jsonify({
                "error" : "Incorrect Password"
            })
        attendance, q, check_attendance = get_attandance(sess, username, key)
        marks, check_marks = get_marks(sess, username, key)
        acadHistory, check_grades = get_acadhistory(sess,username,key)
        days, check_timetable = get_timetable(sess, username, key)
        if(check_attendance == False):
            return jsonify({"Error": "Internal Error in fetching Attendance.Please try again."})
        if(check_marks == False):
            return jsonify({"Error": "Internal Error in fetching Marks.Please try again."})
        if(check_grades == False):
            return jsonify({"Error": "Internal Error in fetching Grades.Please try again."})
        if(check_timetable == False):
            return jsonify({"Error": "Internal Error in fetching Timetable.Please try again."})
        
        ref = db.reference('vitask')
        # API Calls logging
        temp = ref.child("account").child('account-'+key).child(key).get()
        count = int(temp['API-Calls']) + 1
        tut_ref = ref.child("account")
        new_ref = tut_ref.child('account-'+key)
        new_ref.set({
            key: {
                'X-VITASK-API': temp['X-VITASK-API'],
                'Name': temp['Name'],
                'RegNo': temp['RegNo'],
                'Account-Type': temp['Account-Type'],
                'API-Calls': count,
                'Start-Date': temp['Start-Date'],
                'End-Date': temp['End-Date']
            }
        })
        
        return jsonify({
            "attendance": attendance,
            "marks" : marks,
            "acadHistory" : acadHistory,
            "timetable" : days
        })


# /api/vtop/timetable
@app.route('/api/vtop/timetable', methods=['POST'])
def timetableapi():
    """
    POST Route
    This route is only helpful in Android App or Desktop App for getting TimeTable one time.
    This route should NOT be used more than one time. 
    Returns the timetable of the user according to token
    Headers must contain a value
    {
        "X-VITASK-API": "Secret key"   (From /api/account)
    }
    Now the body of POST must be 
    {
        "token" : "Your_API_Token"  # Required
    }
    """
    data = json.loads(request.data)
    user_token = data.get("token",None)
    
    check_header = magiccheck(request.headers.get('X-VITASK-API'))
    if(check_header == "False"):
        return jsonify({
            "error" : "Invalid Header",
            "code"  : "403" # Unauthorised
        })
    if user_token is None:
        return jsonify({
            "error" : "Unauthorised. Get token from /api/getoken",
            "error" : "403" #Unauthorised
        })
    
    # Now begin actual work. It just gets the value from firebase and use it.
    ref = db.reference('vitask')

    temptoken = user_token.encode('ascii')
    try:
        appno = base64.b64decode(temptoken)
    except:
        return jsonify({
            'error': 'Invalid API Token. Get Token from /api/getoken',
            'code' : "400" # bad request
        })
    key = appno.decode('ascii')

    temp = ref.child("timetable").child('timetable-'+key).child(key).child("Timetable").get()

    if(temp is not None):
        session['id'] = key
        days = temp
        
        # API Calls logging
        temp = ref.child("account").child('account-'+key).child(key).get()
        count = int(temp['API-Calls']) + 1
        tut_ref = ref.child("account")
        new_ref = tut_ref.child('account-'+key)
        new_ref.set({
            key: {
                'X-VITASK-API': temp['X-VITASK-API'],
                'Name': temp['Name'],
                'RegNo': temp['RegNo'],
                'Account-Type': temp['Account-Type'],
                'API-Calls': count,
                'Start-Date': temp['Start-Date'],
                'End-Date': temp['End-Date']
            }
        })

        return jsonify({'timetable': days})

    else:
        return jsonify({
            'error': 'Invalid API Token. Get Token from /api/getoken',
            'code' : "400" # bad request
        })

# /api/vtop/attendance
@app.route('/api/vtop/attendance', methods=['POST'])
def attendanceapi():
    """
    POST Route
    This is not meant to use again and again like Timetable API, use /api/aysnc to get data at one place.
    This API is designed only for showing nice messages at the start of app
    Returns the timetable of the user according to token
    Headers must contain a value
    {
        "X-VITASK-API": "Secret key"   (From /api/account)
    }
    Now the body of POST must be 
    {
        "token" : "Your_API_Token"  # Required
    }
    """
    data = json.loads(request.data)
    user_token = data.get("token",None)
    
    check_header = magiccheck(request.headers.get('X-VITASK-API'))
    if(check_header == "False"):
        return jsonify({
            "error" : "Invalid Header",
            "code"  : "403" # Unauthorised
        })
    if user_token is None:
        return jsonify({
            "error" : "Unauthorised. Get token from /api/getoken",
            "error" : "403" #Unauthorised
        })
    
    # Now begin actual work. It just gets the value from firebase and use it
    ref = db.reference('vitask')

    temptoken = user_token.encode('ascii')
    try:
        appno = base64.b64decode(temptoken)
    except:
        return jsonify({
            'error': 'Invalid API Token. Get Token from /api/getoken',
            'code' : "400" # bad request
        })
    key = appno.decode('ascii')

    temp = ref.child('attendance').child('attendance-'+key).child(key).get()

    #Checking if data is already there or not in firebase(if there then no need to acces VTOP again)
    if(temp is not None):
        attend = ref.child("attendance").child('attendance-'+key).child(key).child('Attendance').get()
        q = ref.child("attendance").child('attendance-'+key).child(key).child('Track').get()
            
        # API Calls logging
        temp = ref.child("account").child('account-'+key).child(key).get()
        count = int(temp['API-Calls']) + 1
        tut_ref = ref.child("account")
        new_ref = tut_ref.child('account-'+key)
        new_ref.set({
            key: {
                'X-VITASK-API': temp['X-VITASK-API'],
                'Name': temp['Name'],
                'RegNo': temp['RegNo'],
                'Account-Type': temp['Account-Type'],
                'API-Calls': count,
                'Start-Date': temp['Start-Date'],
                'End-Date': temp['End-Date']
            }
        })

        return jsonify({'attendance': attend})

    else:
        return jsonify({
            'error': 'Invalid API Token. Get Token from /api/getoken',
            'code' : "400" # bad request
        })

# /api/vtop/marks
@app.route('/api/vtop/marks', methods=['POST'])
def marksapi():
    """
    Just like other APIs, it is not meant to be used again and again. 
    This is developed for showing nice messages on loading screen. Use /api/sync
    Headers must contain a value
    {
        "X-VITASK-API": "Secret key"   (From /api/account)
    }
    Now the body of POST must be 
    {
        "token" : "Your_API_Token"  # Required
    }
    """
    data = json.loads(request.data)
    user_token = data.get("token",None)
    
    check_header = magiccheck(request.headers.get('X-VITASK-API'))
    if(check_header == "False"):
        return jsonify({
            "error" : "Invalid Header",
            "code"  : "403" # Unauthorised
        })
    if user_token is None:
        return jsonify({
            "error" : "Unauthorised. Get token from /api/getoken",
            "error" : "403" #Unauthorised
        })
    ref = db.reference('vitask')
    
    # Decoding API token
    temptoken = user_token.encode('ascii')
    try:
        appno = base64.b64decode(temptoken)
    except:
        return jsonify({
            'error': 'Invalid API Token. Get Token from /api/getoken',
            'code' : "400" # bad request
        })
    key = appno.decode('ascii')

    temp = ref.child("marks").child('marks-'+key).child(key).child("Marks").get()
    
    if(temp is not None):
        session['id'] = key
        marksDict = temp
        
        # API Calls logging
        temp = ref.child("account").child('account-'+key).child(key).get()
        count = int(temp['API-Calls']) + 1
        tut_ref = ref.child("account")
        new_ref = tut_ref.child('account-'+key)
        new_ref.set({
            key: {
                'X-VITASK-API': temp['X-VITASK-API'],
                'Name': temp['Name'],
                'RegNo': temp['RegNo'],
                'Account-Type': temp['Account-Type'],
                'API-Calls': count,
                'Start-Date': temp['Start-Date'],
                'End-Date': temp['End-Date']
            }
        })

        return jsonify({'marks': marksDict})
    
    else:
        return jsonify({
            'error': 'Invalid API Token. Get Token from /api/getoken',
            'code' : "400" # bad request
        })

# /api/vtop/history
@app.route('/api/vtop/history', methods=['POST'])
def acadhistoryapi():
    """
    This API is not meant to use again and is not updated. Use /api/vtop/sync with hardrefresh to get new data
    This is only made to show messages on Android App.
    Headers must contain a value
    {
        "X-VITASK-API": "Secret key"   (From /api/account)
    }
    Now the body of POST must be 
    {
        "token" : "Your_API_Token"  # Required
    }
    """
    data = json.loads(request.data)
    user_token = data.get("token",None)
    
    check_header = magiccheck(request.headers.get('X-VITASK-API'))
    if(check_header == "False"):
        return jsonify({
            "error" : "Invalid Header",
            "code"  : "403" # Unauthorised
        })
    if user_token is None:
        return jsonify({
            "error" : "Unauthorised. Get token from /api/getoken",
            "error" : "403" #Unauthorised
        })
    ref = db.reference('vitask')
    
    # Decoding API token
    temptoken = user_token.encode('ascii')
    try:
        appno = base64.b64decode(temptoken)
    except:
        return jsonify({
            'error': 'Invalid API Token. Get Token from /api/getoken',
            'code' : "400" # bad request
        })
    key = appno.decode('ascii')
    temp = ref.child("acadhistory").child('acadhistory-'+key).child(key).child("AcadHistory").get()
        
    if(temp is not None):
        session['id'] = key
        acadHistory = temp
        curriculumDetails = ref.child("acadhistory").child('acadhistory-'+session['id']).child(key).child("CurriculumDetails").get()
        
        # API Calls logging
        temp = ref.child("account").child('account-'+key).child(key).get()
        count = int(temp['API-Calls']) + 1
        tut_ref = ref.child("account")
        new_ref = tut_ref.child('account-'+key)
        new_ref.set({
            key: {
                'X-VITASK-API': temp['X-VITASK-API'],
                'Name': temp['Name'],
                'RegNo': temp['RegNo'],
                'Account-Type': temp['Account-Type'],
                'API-Calls': count,
                'Start-Date': temp['Start-Date'],
                'End-Date': temp['End-Date']
            }
        })

        return jsonify({'acadHistory': acadHistory,'CurriculumDetails': curriculumDetails})
    
    else:
        return jsonify({
            'error': 'Invalid API Token. Get Token from /api/getoken',
            'code' : "400" # bad request
        })

# These are moodle APIs, note than for syncing Moodle and VTOP needs to be sync sepearately
# /api/moodle Routes
# API Token still refers to token from /api/getToken

# /api/moodle/login
@app.route('/api/moodle/login', methods=['POST'])
def moodleLoginapi():
    """
    This is meant to be used when logging into moodle for first time. Do not use this to sync data.
    It just updates the data on Firebase and send you data. 
    Headers must contain a value
    {
        "X-VITASK-API": "Secret key"   (From /api/account)
    }
    Now the body of POST must be 
    {
        "username" : 17BECXXXX  #Required
        "password" : password  #Required
        "token"    : token   #Required for setting values in Firebase
    }
    """
    data = json.loads(request.data)
    username = data.get("username",None)
    password = data.get("password",None)
    user_token = data.get("token",None)
    
    check_header = magiccheck(request.headers.get('X-VITASK-API'))
    if(check_header == "False"):
        return jsonify({
            "error" : "Invalid Header",
            "code"  : "403" # Unauthorised
        })
    if user_token is None:
        return jsonify({
            "error" : "Unauthorised. Get token from /api/getoken",
            "error" : "403" #Unauthorised
        })
    # This route will assume that you are loging first time and overwrite previous data
    
    # Decoding API token
    temptoken = user_token.encode('ascii')
    try:
        appno = base64.b64decode(temptoken)
    except:
        return jsonify({
            'error': 'Invalid API Token. Get Token from /api/getoken',
            'code' : "400" # bad request
        })
    key = appno.decode('ascii')
    session['id'] = key

    ref = db.reference('vitask')
    moodle_username =  username
    moodle_password = password
    sess, sess_key = get_moodle_session(moodle_username.lower(),moodle_password)
    due_items = get_dashboard_json(sess, sess_key)
    assignments = []
    if due_items is None:
        assignments.append({
            "course" : "No Assignments"
        })
    else:
        for item in due_items:
            assignment = {}
            assignment['id'] = item['id']
            assignment['name'] = item['name']
            assignment['description'] = item['description']
            assignment['time'] =  datetime.fromtimestamp(int(item['timesort'])).strftime('%d-%m-%Y %H:%M:%S') 
            assignment['url'] = item['url']
            assignment['course'] = item['course']['fullname']
            assignment['show'] = True                # 0 == False, 1 == True
            assignments.append(assignment)
    ref = db.reference('vitask')
    
    # For the last time BASE64 IS NOT ENCRYPTION (LMAO stares at NOT FFCS)
    api_gen = moodle_password
    api_token = api_gen.encode('ascii')
    temptoken = base64.b64encode(api_token)
    token = temptoken.decode('ascii')
    api_gen = moodle_password
    api_token = api_gen.encode('ascii')
    temptoken = base64.b64encode(api_token)
    token = temptoken.decode('ascii')

    
    tut_ref = ref.child("moodle")
    new_ref = tut_ref.child("moodle-"+key)
    new_ref.set({
        key: {
            'Username': moodle_username,
            'Password': token,
            'Assignments': assignments 
        }
    })
    
    # API Calls logging
    temp = ref.child("account").child('account-'+key).child(key).get()
    count = int(temp['API-Calls']) + 1
    tut_ref = ref.child("account")
    new_ref = tut_ref.child('account-'+key)
    new_ref.set({
        key: {
            'X-VITASK-API': temp['X-VITASK-API'],
            'Name': temp['Name'],
            'RegNo': temp['RegNo'],
            'Account-Type': temp['Account-Type'],
            'API-Calls': count,
            'Start-Date': temp['Start-Date'],
            'End-Date': temp['End-Date']
        }
    })
    return jsonify({'Assignments': assignments})


# /api/moodle/sync
@app.route('/api/moodle/sync', methods=['POST'])
def moodleSyncapi():
    """
    This function is used to sync data from moodle and then sends the live assignments info
    This route assumes that you have already sign in using /api/moodle/login
    Headers must contain a value
    {
        "X-VITASK-API": "Secret key"   (From /api/account)
    }
    Now the body of POST must be 
    {
        "token"    : token   #Required for setting values in Firebase
    }
    """
    data = json.loads(request.data)
    user_token = data.get("token",None)

    # TODO: I'm against this, but since we only have users, cool 
    # Now we assume that you have already signed in moodle
    check_header = magiccheck(request.headers.get('X-VITASK-API'))
    if(check_header == "False"):
        return jsonify({
            "error" : "Invalid Header",
            "code"  : "403" # Unauthorised
        })
    if user_token is None:
        return jsonify({
            "error" : "Unauthorised. Get token from /api/getoken",
            "error" : "403" #Unauthorised
        })
    # This route will assume that you are loging first time and overwrite previous data
    temptoken = user_token.encode('ascii')
    try:
        appno = base64.b64decode(temptoken)
    except:
        return jsonify({
            'error': 'Invalid API Token. Get Token from /api/getoken',
            'code' : "400" # bad request
        })
    key = appno.decode('ascii')

    ref = db.reference('vitask')
    temp = ref.child("moodle").child('moodle-'+key).child(key).child('Username').get()
    
    
    if(temp is None):
        return jsonify({
            "error" : "Unauthorized. You are not signed Moodle. First visit /api/moodle/login",
            "error" : "403" #Unauthorised
        })
    else:
        session['id'] = key
        username = ref.child("moodle").child('moodle-'+session['id']).child(key).child('Username').get()
        b64_password = ref.child("moodle").child('moodle-'+session['id']).child(key).child('Password').get()
        # Now first decode the password
        temp_password = b64_password.encode('ascii')

        password = base64.b64decode(temp_password).decode('ascii')

        # Now signin moodle and then get the latest assignments
        sess, sess_key = get_moodle_session(username.lower(),password)
        due_items = get_dashboard_json(sess, sess_key)
        assignments = []
        if due_items is None:
            assignments.append({
                "course" : "No Assignments"
            })
            tut_ref = ref.child("moodle")
            new_ref = tut_ref.child("moodle-"+session['id'])
            new_ref.set({
                session['id']: {
                    'Username': username,
                    'Password': b64_password,
                    'Assignments': assignments 
                }
            })
            
            # API Calls logging
            temp = ref.child("account").child('account-'+session['id']).child(session['id']).get()
            count = int(temp['API-Calls']) + 1
            tut_ref = ref.child("account")
            new_ref = tut_ref.child('account-'+session['id'])
            new_ref.set({
                session['id']: {
                    'X-VITASK-API': temp['X-VITASK-API'],
                    'Name': temp['Name'],
                    'RegNo': temp['RegNo'],
                    'Account-Type': temp['Account-Type'],
                    'API-Calls': count,
                    'Start-Date': temp['Start-Date'],
                    'End-Date': temp['End-Date']
                }
            })
            return jsonify({'Assignments' : assignments})
        else:
            for item in due_items:
                assignment = {}
                assignment['id'] = item['id']
                assignment['name'] = item['name']
                assignment['description'] = item['description'] # This is Raw HTML, either parse at client end or display accordingly
                assignment['time'] =  datetime.fromtimestamp(int(item['timesort'])).strftime('%d-%m-%Y %H:%M:%S')
                assignment['url'] = item['url']
                assignment['course'] = item['course']['fullname']
                assignment['show'] = True                # 0 == False, 1 == True
                assignments.append(assignment)
        
            # Now match the assignments with prev assignments
            # As the time of assignements may be changed, 
            # So, using previous assginments, just change the status of assignments
            # If due items is NOT None, then only use prev assignments else dont.
            prev_assignments = ref.child("moodle").child('moodle-'+session['id']).child(key).child('Assignments').get()
            for assignment in assignments:
                assigmentID = assignment['id']
                for prev in prev_assignments:
                    if prev['id'] == assigmentID:
                        assignment['show'] = prev['show']
                        break
            # Now set the new assignment as the data 
            tut_ref = ref.child("moodle")
            new_ref = tut_ref.child("moodle-"+session['id'])
            new_ref.set({
                session['id']: {
                    'Username': username,
                    'Password': b64_password,
                    'Assignments': assignments 
                }
            })
            
            # API Calls logging
            temp = ref.child("account").child('account-'+session['id']).child(session['id']).get()
            count = int(temp['API-Calls']) + 1
            tut_ref = ref.child("account")
            new_ref = tut_ref.child('account-'+session['id'])
            new_ref.set({
                session['id']: {
                    'X-VITASK-API': temp['X-VITASK-API'],
                    'Name': temp['Name'],
                    'RegNo': temp['RegNo'],
                    'Account-Type': temp['Account-Type'],
                    'API-Calls': count,
                    'Start-Date': temp['Start-Date'],
                    'End-Date': temp['End-Date']
                }
            })
            
            return jsonify({'Assignments' : assignments})


# /api/moodle/toggleshow/
@app.route('/api/moodle/toggleshow', methods=['POST'])
def assignmentToggleShowapi():
    """
    POST Request
    This API can be used in bulk and single manner. In bulk mode, pass multiple ids of assignements to be marked opposite
    This API reverse the show property of all the assignments whose Id will be provided.
    I'm relying on Moodle and hoping that IDs are unique
    Headers must contain a value
    {
        "X-VITASK-API": "Secret key"   (From /api/account)
    }
    Now the body of POST must be 
    {
        "token"    : token   #Required for setting values in Firebase
        "ids"      : [ id1, id2, id3] # Required, List of Ids
    }
    """
    data = json.loads(request.data)
    user_token = data.get("token",None)
    ids = data.get("ids",None)
    
    # Even if only one ID is there, pass it in array
    check_header = magiccheck(request.headers.get('X-VITASK-API'))
    if(check_header == "False"):
        return jsonify({
            "error" : "Invalid Header",
            "code"  : "403" # Unauthorised
        })
    if ids is None:
        return jsonify({
            "error" : "Incorrect API Request",
            "code"  : "400" # Bad request
        })
    if user_token is None:
        return jsonify({
            "error" : "Unauthorised. Get token from /api/getoken",
            "error" : "403" #Unauthorised
        })
    
    # Now first get all the asssignments
    temptoken = user_token.encode('ascii')
    try:
        appno = base64.b64decode(temptoken)
    except:
        return jsonify({
            'error': 'Invalid API Token. Get Token from /api/getoken',
            'code' : "400" # bad request
        })
    key = appno.decode('ascii')
    session['id'] = key
    ref = db.reference('vitask')
    
    moodleData = ref.child("moodle").child('moodle-'+session['id']).child(key).get()
    username = moodleData['Username']
    password = moodleData['Password']
    assignments = moodleData['Assignments']
    for i in range(len(assignments)):
        if assignments[i]['id'] in ids:
            assignments[i]['show'] = not assignments[i]['show']
    # Now assign data and return the new data
    tut_ref = ref.child("moodle")
    new_ref = tut_ref.child("moodle-"+session['id'])
    new_ref.set({
        session['id']: {
            'Username': username,
            'Password': password,
            'Assignments': assignments 
        }
    })
    
    # API Calls logging
    temp = ref.child("account").child('account-'+session['id']).child(session['id']).get()
    count = int(temp['API-Calls']) + 1
    tut_ref = ref.child("account")
    new_ref = tut_ref.child('account-'+session['id'])
    new_ref.set({
        session['id']: {
            'X-VITASK-API': temp['X-VITASK-API'],
            'Name': temp['Name'],
            'RegNo': temp['RegNo'],
            'Account-Type': temp['Account-Type'],
            'API-Calls': count,
            'Start-Date': temp['Start-Date'],
            'End-Date': temp['End-Date']
        }
    })
    return jsonify({'Assignments' : assignments})
        
"""---------------------------------------------------------------
                    VITask API code ends here
------------------------------------------------------------------"""


"""---------------------------------------------------------------
            VITask Web Application code begins from here

      “Make it work, make it right, make it fast.” – Kent Beck
------------------------------------------------------------------"""

# Homepage for VITask
@app.route('/', methods=['GET'])
def home():
    return render_template('home.html')

# Team Page
@app.route('/ourteam' , methods=['GET'])
def ourteam():
    return render_template('team.html')

# Downloads Page
@app.route('/downloads' , methods=['GET'])
def downloads():
    return render_template('downloads.html')

# Privacy Policy Page
@app.route('/policy' , methods=['GET'])
def policy():
    return render_template('policy.html')


# Sitemap
@app.route('/sitemap.xml' , methods=['GET'])
def sitemap():
    return render_template('sitemap.xml')

# Login path for VITask Web app
@app.route('/login', methods=['GET', 'POST'])
def index():
    try:
        if(session['loggedin']==1):
            return redirect(url_for('profile'))
        else:
            return render_template('login.html',correct=True)
    except:
        session['loggedin'] = 0
        return render_template('login.html',correct=True)

# Web login route(internal don't use for anything on user side)
@app.route('/signin', methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        session['timetable'] = 0
        session['classes'] = 0
        session['moodle'] = 0
        session['acadhistory'] = 0
        session['loggedin'] = 0

        username = request.form['username'].upper()
        password = request.form['password']
        try:
            sess, valid = generate_session(username, password)
        finally:
            if( valid == False ):
                return render_template('login.html',correct=False)

            else:
                try:
                    profile = {}
                    profile, check_profile = get_student_profile(sess, username)
                    if(check_profile == False):
                        return render_template('login.html',correct=False)
                    session['id'] = profile['appNo']
                    session['name'] = profile['name']
                    session['reg'] = profile['regNo']
                    session['loggedin'] = 1
                finally:
                    # Timetable,Attendance,Acadhistory and Marks fetching in parallel
                    try:
                        runInParallel(parallel_timetable(sess, username, session['id']), parallel_attendance(sess, username, session['id']), parallel_acadhistory(sess, username, session['id']), parallel_marks(sess, username, session['id'])) 
                    finally:
                        return redirect(url_for('profile'))
                       
    else:
        return redirect(url_for('index'))
                                  
# Profile route
@app.route('/profile')
def profile():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        name, school, branch, program, regno, appno, email, proctoremail, proctorname, api = ProfileFunc()
        ref = db.reference('vitask')
        temp = ref.child("account").child('account-'+session['id']).child(session['id']).get()
        return render_template('profile.html',name=name,school=school,branch=branch,program=program,regno=regno,email=email,proctoremail=proctoremail,proctorname=proctorname,appno=appno,account_type=temp['Account-Type'])

# Timetable route
@app.route('/timetable')
def timetable():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        ref = db.reference('vitask')
        days = ref.child("timetable").child('timetable-'+session['id']).child(session['id']).child('Timetable').get()
        return render_template('timetable.html',name=session['name'],id=session['id'],tt=days)


# Attendance route
@app.route('/classes')
def classes():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        ref = db.reference('vitask')
        attend = ref.child("attendance").child('attendance-'+session['id']).child(session['id']).child('Attendance').get()
        q = ref.child("attendance").child('attendance-'+session['id']).child(session['id']).child('Track').get()
        return render_template('attendance.html',name = session['name'],id = session['id'],dicti = attend,q = q)

# Academic History route
@app.route('/acadhistory')
def acadhistory():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        ref = db.reference('vitask')
        acadHistory = ref.child("acadhistory").child('acadhistory-'+session['id']).child(session['id']).child('AcadHistory').get()
        curriculumDetails = ref.child("acadhistory").child('acadhistory-'+session['id']).child(session['id']).child('CurriculumDetails').get()
        return render_template('acadhistory.html',name = session['name'],acadHistory = acadHistory,curriculumDetails = curriculumDetails)    

# Marks route
@app.route('/marks')
def marks():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        ref = db.reference('vitask')
        marks = ref.child("marks").child('marks-'+session['id']).child(session['id']).child('Marks').get()
        return render_template('marks.html',name = session['name'], marks = marks)
    
# Upgrade route
@app.route('/upgrade')
def upgrade():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        return render_template('pricing.html',name=session['name'])

        
"""---------------------------------------------------------------

        Code for VITask API Dashboard and Console begins here

 “The mind is furnished with ideas by experience alone”― John Locke

------------------------------------------------------------------"""

        
# API Dashboard 
@app.route('/apidashboard')
def apidashboard():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        name, school, branch, program, regno, appno, email, proctoremail, proctorname, api = ProfileFunc()
        ref = db.reference('vitask')
        temp = ref.child("account").child('account-'+session['id']).child(session['id']).get()
        return render_template('api.html',name=name,regno=regno,account_type=temp['Account-Type'],start_date=temp['Start-Date'],end_date=temp['End-Date'],secret_key=temp['X-VITASK-API'],api=api,api_calls=temp['API-Calls'])

# API Console(Not ready yet)
@app.route('/apiconsole', methods=['GET', 'POST'])
def apiconsole():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        return redirect(url_for('profile'))

"""---------------------------------------------------------------

        Code for VITask API Dashboard and Console ends here

------------------------------------------------------------------"""


"""---------------------------------------------------------------

        Code for VITask Advertisements begins here

------------------------------------------------------------------"""

#Advertisement page
@app.route('/ads')
def adst():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        return render_template("ads.html",name=session['name'])


# Ads route
@app.route('/advert', methods=['GET','POST'])
def advert():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        if request.method == 'POST':
            id = session['id']
            evname = request.form["Eventname"]
            evdesc = request.form["Eventdesc"]
            evtime = request.form["Eventtiming"]

            adsdetails = {}
            adsdetails[0] = evname
            adsdetails[1] = evdesc
            adsdetails[2] = evtime
            adsdetails[3] = session['reg']
            adsdetails[4] = session['name']
            adsdetails[5] = session['id']

            # adsdetails = {'Event Name':evname,'Event Description': evdesc, 'Event Time': evtime}

            ref = db.reference('vitask')
            tut_ref = ref.child("advertisement")
            new_ref = tut_ref.child('advertisement-'+id)
            new_ref.set({
                id: {
                    'Details': adsdetails
                }
            })

    return render_template('adssuccess.html',adsdetails = adsdetails,name=session['name'])


"""---------------------------------------------------------------

        Code for VITask Advertisements ends here

------------------------------------------------------------------"""


"""---------------------------------------------------------------

                    Staff Components begin here

------------------------------------------------------------------"""
# Staff Dashboard
@app.route('/staff', methods=['GET', 'POST'])
def staff():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        ref = db.reference('vitask')
        temp = ref.child("account").child('account-'+session['id']).child(session['id']).get()
        if (temp['Account-Type']=="Staff"):
            user_list = ref.child("profile").get()
            tempdict = {}
            user_info = {}
            display = {}
            for i in user_list:
                tempdict = user_list[i]
                for j in tempdict:
                    user_info = tempdict[j]
                    display[user_info["AppNo"]] = user_info
            users = len(user_list)
            new_user_list = ref.child("account").get()
            new_users = len(new_user_list)
            return render_template('staff_home.html',name=session['name'],users=users,new_users=new_users,display=display)
        else:
            return redirect(url_for('profile'))

"""---------------------------------------------------------------

                    Staff Components end here

------------------------------------------------------------------"""


"""---------------------------------------------------------------

            Code for Moodle Integration begins from here

    “The only true wisdom is in knowing you know nothing.”― Socrates

------------------------------------------------------------------"""


# Moodle Login path for VITask Web app
@app.route('/moodle', methods=['GET', 'POST'])
def moodle():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        ref = db.reference('vitask')
        temp = ref.child("moodle").child('moodle-'+session['id']).child(session['id']).get()
        if(session['moodle']==1 or temp is not None):
            return redirect(url_for('assignments'))
        else:
            return render_template('moodle.html',name=session['name'])

# Path for processing of details from /moodle
@app.route('/moodlelogin', methods=['GET', 'POST'])
def moodlelogin():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        ref = db.reference('vitask')
        temp = ref.child("moodle").child('moodle-'+session['id']).child(session['id']).get()
        if(session['moodle']==1 or temp is not None):
            return redirect(url_for('assignments'))
        else:
            moodle_username =  request.form['username']
            moodle_password = request.form['password']
            sess, sess_key = get_moodle_session(moodle_username.lower(),moodle_password)
            due_items = get_dashboard_json(sess, sess_key)
            assignments = []
            if due_items is None:
                assignments.append({
                    "course" : "No Assignments"
                })
            else:
                for item in due_items:
                    assignment = {}
                    assignment['id'] = item['id']
                    assignment['name'] = item['name']
                    assignment['description'] = item['description']
                    assignment['time'] =  datetime.fromtimestamp(int(item['timesort'])).strftime('%d-%m-%Y %H:%M:%S')
                    assignment['url'] = item['url']
                    assignment['course'] = item['course']['fullname']
                    assignment['show'] = True                # 0 == False, 1 == True
                    assignments.append(assignment)
            ref = db.reference('vitask')

            # For the last time BASE64 IS NOT ENCRYPTION (LMAO stares at NOT FFCS)
            api_gen = moodle_password
            api_token = api_gen.encode('ascii')
            temptoken = base64.b64encode(api_token)
            token = temptoken.decode('ascii')
            api_gen = moodle_password
            api_token = api_gen.encode('ascii')
            temptoken = base64.b64encode(api_token)
            token = temptoken.decode('ascii')


            tut_ref = ref.child("moodle")
            new_ref = tut_ref.child("moodle-"+session['id'])
            new_ref.set({
                session['id']: {
                    'Username': moodle_username,
                    'Password': token,
                    'Assignments': assignments 
                }
            })

            return render_template('assignments.html',name=session['name'],assignment=assignments)
        
# Remove assignments from Moodle
@app.route('/removeassignment', methods=['GET', 'POST'])
def removeassignment():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        if request.method == 'POST' and 'id' in request.form:
            ref = db.reference('vitask')
            temp = ref.child("moodle").child('moodle-'+session['id']).child(session['id']).get()
            
            ids = []
            ids.append(int(request.form['id']))

            if(session['moodle']==1 or temp is not None):
                username = temp['Username']
                password = temp['Password']
                assignments = temp['Assignments']
                
                for i in range(len(assignments)):
                    if assignments[i]['id'] in ids:
                        assignments[i]['show'] = not assignments[i]['show']
                        
                # Now assign data and return the new data
                tut_ref = ref.child("moodle")
                new_ref = tut_ref.child("moodle-"+session['id'])
                new_ref.set({
                    session['id']: {
                        'Username': username,
                        'Password': password,
                        'Assignments': assignments 
                    }
                })
                        
                return redirect(url_for('assignments'))
            else:
                return redirect(url_for('moodle'))
        else:
            return redirect(url_for('moodle'))
        
# Restore assignments from Moodle
@app.route('/restoreassignment', methods=['GET', 'POST'])
def restoreassignment():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        if request.method == 'POST' and 'id' in request.form:
            ref = db.reference('vitask')
            temp = ref.child("moodle").child('moodle-'+session['id']).child(session['id']).get()
            
            ids = []
            ids.append(int(request.form['id']))

            if(session['moodle']==1 or temp is not None):
                username = temp['Username']
                password = temp['Password']
                assignments = temp['Assignments']
                
                for i in range(len(assignments)):
                    if assignments[i]['id'] in ids:
                        assignments[i]['show'] = not assignments[i]['show']
                        
                # Now assign data and return the new data
                tut_ref = ref.child("moodle")
                new_ref = tut_ref.child("moodle-"+session['id'])
                new_ref.set({
                    session['id']: {
                        'Username': username,
                        'Password': password,
                        'Assignments': assignments 
                    }
                })
                        
                return redirect(url_for('assignments'))
            else:
                return redirect(url_for('moodle'))
        else:
            return redirect(url_for('moodle'))
        
# Removed Assignments page for Moodle
@app.route('/noassignments', methods=['GET', 'POST'])
def noassignments():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        ref = db.reference('vitask')
        temp = ref.child("moodle").child('moodle-'+session['id']).child(session['id']).get()
        if(session['moodle']==1 or temp is not None):
            assignment = temp['Assignments']
            
            no_assignment = []
            # Returning only the assignments which have status no
            for i in assignment:
                if(i["show"] == False):
                    no_assignment.append(i)
                    
            return render_template('noassignments.html',name=session['name'],assignment=no_assignment)
        else:
            return redirect(url_for('moodle'))
            
# Assignments page for Moodle
@app.route('/assignments', methods=['GET', 'POST'])
def assignments():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        ref = db.reference('vitask')
        temp = ref.child("moodle").child('moodle-'+session['id']).child(session['id']).get()
        if(session['moodle']==1 or temp is not None):
            assignment = temp['Assignments']
            
            yes_assignment = []
            # Returning only the assignments which have status yes
            for i in assignment:
                if(i["show"]==True):
                    yes_assignment.append(i)
                    
            return render_template('assignments.html',name=session['name'],assignment=yes_assignment)
        else:
            return redirect(url_for('moodle'))
    
# Resync Assignments page for Moodle
@app.route('/moodleresync', methods=['GET', 'POST'])
def moodleresync():
    if(session['loggedin']==0):
        return redirect(url_for('index'))
    else:
        ref = db.reference('vitask')
        moodleData = ref.child("moodle").child('moodle-'+session['id']).child(session['id']).get()
        moodle_username = moodleData['Username']
        pass_token = moodleData['Password']
        
        # Decoding Password
        temptoken = pass_token.encode('ascii')
        temp_pass = base64.b64decode(temptoken)
        key = temp_pass.decode('ascii')
        

        moodle_password = key
        
        # Now signin moodle and then get the latest assignments
        sess, sess_key = get_moodle_session(moodle_username.lower(), moodle_password)
        due_items = get_dashboard_json(sess, sess_key)
        assignments = []
        if due_items is None:
            assignments.append({
                "course" : "No Assignments"
            })
            tut_ref = ref.child("moodle")
            new_ref = tut_ref.child("moodle-"+session['id'])
            new_ref.set({
                session['id']: {
                    'Username': username,
                    'Password': b64_password,
                    'Assignments': assignments 
                }
            })
            return redirect(url_for('assignments'))
        else:
            for item in due_items:
                assignment = {}
                assignment['id'] = item['id']
                assignment['name'] = item['name']
                assignment['description'] = item['description'] # This is Raw HTML, either parse at client end or display accordingly
                assignment['time'] =  datetime.fromtimestamp(int(item['timesort'])).strftime('%d-%m-%Y %H:%M:%S')
                assignment['url'] = item['url']
                assignment['course'] = item['course']['fullname']
                assignment['show'] = True                # 0 == False, 1 == True
                assignments.append(assignment)
        
            # Now match the assignments with prev assignments
            # As the time of assignements may be changed, 
            # So, using previous assginments, just change the status of assignments
            # If due items is NOT None, then only use prev assignments else dont.
            prev_assignments = ref.child("moodle").child('moodle-'+session['id']).child(session['id']).child('Assignments').get()
            for assignment in assignments:
                assigmentID = assignment['id']
                for prev in prev_assignments:
                    if prev['id'] == assigmentID:
                        assignment['show'] = prev['show']
                        break
            # Now set the new assignment as the data 
            tut_ref = ref.child("moodle")
            new_ref = tut_ref.child("moodle-"+session['id'])
            new_ref.set({
                session['id']: {
                    'Username': moodle_username,
                    'Password': pass_token,
                    'Assignments': assignments 
                }
            })

        return redirect(url_for('assignments'))
            
"""---------------------------------------------------------------

            Code for Moodle Integration ends here

------------------------------------------------------------------"""

# Web Logout
@app.route('/logout')
def logout():
    session.pop('id', None)
    session.pop('timetable', 0)
    session.pop('classes', 0)
    session.pop('name', None)
    session.pop('reg', None)
    session.pop('moodle', 0)
    session.pop('acadhistory', 0)
    # session.pop('marks', 0)
    session.pop('loggedin',0)
    return redirect(url_for('home'))



# Run Flask app
if __name__ == '__main__':
	app.run(host='0.0.0.0', port=port, debug=True)