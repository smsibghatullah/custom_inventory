# -*- coding: utf-8 -*-
{
    "name": "User Employee Attendance Access",
    "version": "17.0.1.0.0",
    "category": "Human Resources/Attendances",
    "summary": "Show attendance based on employees selected on the user, ignoring company restrictions",
    "description": """
This module adds Allowed Attendance Employees on users.
Attendance records are shown based on those selected employees, across all companies.
""",
    "author": "",
    "depends": [
        "base",
        "hr",
        "hr_attendance",
    ],
    "data": [
        "security/security.xml",
        "views/res_users_views.xml",
        "views/hr_attendance_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
