#-*- coding:utf-8 -*-
##############################################################################//
#
#    Copyright (c) 2014 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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
    'name': 'Create Attendance Records by Department',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'author':'Michael Telahun Makonnen <mmakonnen@gmail.com>',
    'description': """
Create Attendance Records from Weekly Department Records
========================================================
    - Create perfect attendance records for the whole month
    - Modify weekly attendances as time keepers hand in attendance
    """,
    'website':'http://miketelahun.wordpress.com',
    'depends': [
        'hr_attendance',
        'hr_attendance_batch_entry',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'wizard/create_weekly_view.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
