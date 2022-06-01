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
    'name': 'Payroll Period Processing',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'description': """
Payroll Period Processing
============================
Allows the user to efficiently process payroll
    """,
    'author':'Clear ICT Solutions <info@clearict.com>',
    'website':'http://www.clearict.com',
    'depends': [
        'hr',
        'hr_attendance_batch_entry',
        'hr_payroll',
        'hr_payroll_period',
        'hr_performance_bonus',
        'hr_security',
        'hr_wage_increment',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'wizard/process_view.xml',
        'hr_payroll_view.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
