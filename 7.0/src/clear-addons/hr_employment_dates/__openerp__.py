# -*- coding:utf-8 -*-
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
    'name': 'Calculate Employment Dates',
    'summary': 'Calculate an employee\'s employment dates based on contracts',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Employment Dates
================
This module sets starting and ending (if any) employment dates on an employee
record based on contract start and end dates.
    """,
    'author': 'Clear ICT Solutions <info@clearict.com>',
    'website': 'http://www.clearict.com',
    'depends': [
        'hr',
        'hr_contract',
        'hr_employee_seniority',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'views/hr_view.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
