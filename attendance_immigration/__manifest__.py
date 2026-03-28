{
    "name": "Attendance Immigration",
    "version": "17.0.1.0",
    "summary": "Immigration Rate in Attendance",
    "depends": ["hr_attendance", "hr","custom_inventory","hr_hourly_cost"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/hr_employee_view.xml",
        "views/hr_attendance_view.xml"
    ],
    "installable": True,
    "application": False
}
