# MIR User Employee Attendance Access

## Purpose

This Odoo 17 module adds `employee_ids` on `res.users`.

The selected employees decide which `hr.attendance` records the user can see.

## Behavior

- User form gets `Allowed Attendance Employees`.
- The field can show employees from all companies.
- Attendance records are filtered by selected employees.
- Company rules do not affect attendance visibility.
- Actual attendance remains in `hr.attendance`; no duplicate attendance table is created.

## Important

On installation, the post-init hook disables existing `hr.attendance` record rules except this module's own rule.
It also disables company-based `hr.employee` rules so employees from all companies can be selected.

## Install

Copy folder to your Odoo 17 addons path:

```bash
cp -r mir_user_employee_attendance_access /path/to/odoo/custom_addons/
```

Restart Odoo and update apps list:

```bash
./odoo-bin -d YOUR_DB -u mir_user_employee_attendance_access
```

Then open:

Settings > Users > select user > Attendance Access Employees

Select employees. That user will see attendance only for those employees.
