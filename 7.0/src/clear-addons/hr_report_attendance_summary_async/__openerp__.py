# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Clear ICT Solutions <info@clearict.com>.
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify it
#    under the terms of the GNU Affero General Public License as published by
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
    'name': 'Employee Attendance Summary - Asynchronous',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
View Summarized Employee Attendance
===================================

The report includes:
    * Days Present
    * Days on Leave
    * Days Absent
    """,
    'author': 'ClearICT Solutions',
    'website': 'http://www.clearict.com',
    'depends': [
        'hr_report_payroll_attendance_summary',
        'connector',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'report.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
