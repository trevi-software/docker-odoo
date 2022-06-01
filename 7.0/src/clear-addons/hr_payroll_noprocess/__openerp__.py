#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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
    'name': 'Payroll - No Process List',
    'summary': 'Do not process payroll for specific employees',
    'description': """
Payroll No Process List
=======================
    """,
    'category': 'Human Resources',
    'author': 'Clear ICT Solutions',
    'website': 'http://www.clearict.com',
    'version': '1.0',
    'depends': [
        'hr_payroll_period',
        'hr_security',
    ],
    'init_xml': [],
    'update_xml': [
        'security/ir.model.access.csv',
        'views/hr_payroll_view.xml',
     ],
    'test': [
    ],
    'demo_xml': [],
    'active': False,
    'installable': True,
}
