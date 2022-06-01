#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Clear ICT Solutions <info@clearict.com>.
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Delete Employee Record - Payroll Amendment',
    'summary': 'Permanently delete an employee\'s post-closing payroll amendments',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Delete Employee Record - Post-closing Payroll Amendments
========================================================
This module allows the HR Manager to permanently delete an employee record from the
system. All records pertaining to the employee will be deleted.

Removed data includes:
    * Post-closing Payroll Amendments
    """,
    'author':'Clear ICT Solutions <info@clearict.com>',
    'website':'http://www.clearict.com',
    'depends': [
        'hr_employee_delete',
        'hr_employee_delete_attendance_weekly',
        'hr_payroll_amendment',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'hr_view.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
