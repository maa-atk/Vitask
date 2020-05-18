// Called at the beginning of the app
export const LOGIN_VTOP_REQUEST = "LOGIN_VTOP_REQUEST"
export const LOGIN_VTOP_SUCCESS = "LOGIN_VTOP_SUCCESS"
export const LOGIN_VTOP_ERROR = "LOGIN_VTOP_ERROR"

// Called at the beginning of app, Timetable doesnot changes
export const FETCH_TIMETABLE_REQUEST = "FETCH_TIMETABLE_REQUEST"
export const FETCH_TIMETABLE_SUCCESS = "FETCH_TIMETABLE_SUCCESS"
export const FETCH_TIMETABLE_ERROR = "FETCH_TIMETABLE_ERROR"

// Will sync Attendance details
export const FETCH_ATTENDANCE_REQUEST = "FETCH_ATTENDANCE_REQUEST"
export const FETCH_ATTENDANCE_SUCCESS = "FETCH_ATTENDANCE_SUCCESS"
export const FETCH_ATTENDANCE_ERROR = "FETCH_ATTENDANCE_ERROR"

export const SYNC_VTOP_REQUEST = "SYNC_VTOP_REQUEST"
export const SYNC_VTOP_SUCCESS = "SYNC_VTOP_SUCCESS"
export const SYNC_VTOP_ERROR = "SYNC_VTOP_ERROR"


// Will sync Marks details
export const FETCH_MARKS_REQUEST = "FETCH_MARKS_REQUESTS"
export const FETCH_MARKS_SUCCESS = "FETCH_MARKS_SUCCESS"
export const FETCH_MARKS_ERROR = "FETCH_MARKS_ERROR"

export const LOGIN_MOODLE_REQUEST = "LOGIN_MOODLE_REQUEST"
export const LOGIN_MOODLE_SUCCESS = "LOGIN_MOODLE_SUCCESS"
export const LOGIN_MOODLE_ERROR = "LOGIN_MOODLE_ERROR"

export const MOODLE_ASSIGNMENTS_SYNC_REQUEST = "MOODLE_ASSIGNMENTS_SYNC_REQUEST"
export const MOODLE_ASSIGNMENTS_SYNC_SUCCESS = "MOODLE_ASSIGNMENTS_SYNC_SUCCESS"
export const MOODLE_ASSIGNMENTS_SYNC_ERROR = "MOODLE_ASSIGNMENTS_SYNC_ERROR"

export const FETCH_ACADHISTORY_REQUEST = "FETCH_ACADHISTORY_REQUEST"
export const FETCH_ACADHISTORY_SUCCESS = "FETCH_ACADHISTORY_SUCCESS"
export const FETCH_ACADHISTORY_ERROR = "FETCH_ACADHISTORY_SUCCESS"

export const STORE_STATE_FROM_ASYNC = "STORE_STATE_FROM_ASYNC"

// These are only for using developement purpose to save api calls, instead api calls are done to dummy server
export const DEV_LOAD_ATTENDANCE = "DEV_LOAD_ATTENDANCE"
export const DEV_LOAD_PROFILE = "DEV_LOAD_PROFILE"
export const DEV_LOAD_TIMETABLE = "DEV_LOAD_TIMETABLE"


// Formatting data, only called first time
export const REFORMAT_DATA = "REFORMAT_DATA"
// Will be called after Logging into Moodle
const LOGIN_MOODLE = "LOGIN_MOODLE"
// Get the Bulk assignments
const SYNC_ASSIGNMENTS = "ASSIGNMENT"
// Get the resources for the subject
const SYNC_RESOURCES = "RESOURCES"

