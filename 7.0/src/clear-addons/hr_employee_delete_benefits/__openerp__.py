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
    'name': 'Delete Employee Record - Benefits',
    'summary': 'Permanently delete an employee\'s benefit policies',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Delete Employee Record - Benefit Policies
=========================================
This module allows the HR Manager to permanently delete an employee record from the
system. All records pertaining to the employee will be deleted.

Removed data includes:
    * Benefit Policies
    * Claims
    * Premium Payments
    """,
    'author':'Clear ICT Solutions <info@clearict.com>',
    'website':'http://www.clearict.com',
    'depends': [
        'hr_employee_delete',
        'benefit_management',
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
