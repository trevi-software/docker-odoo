#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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
    'name': 'Record Demerits',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'author':'Michael Telahun Makonnen <mmakonnen@gmail.com>',
    'description': """
Record Demerits with Bulk Entry of Attendance Data
==================================================
    """,
    'website':'http://miketelahun.wordpress.com',
    'depends': [
        'hr_attendance_batch_entry',
        'hr_payroll_extension',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'demerit_view.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
