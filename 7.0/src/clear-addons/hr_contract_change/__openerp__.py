# -*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Clear ICT Solutions <info@clearict.com>.
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
    'name': 'Change Employee Contract Values',
    'summary': 'Change the values of some fields in employee contracts',
    'description': """
Change Employee Contract Values
===============================
This module allows the HR Manager to change some fields on a confirmed employee
contract. A record of the changes is kept in Human Resources -> Change Log
    """,
    'author': 'Clear ICT Solutions <info@clearict.com>',
    'website': 'http://www.clearict.com',
    'version': '1.0',
    'category': 'Human Resources',
    'depends': [
        'hr_contract',
        'hr_contract_state',
        'hr_employee_change_uniqueid',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/change_view.xml',
        'hr_view.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
