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
    'name': 'Employee Bonus',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'description': """
Employee Bonus
==============
    """,
    'author':'Michael Telahun Makonnen <mmakonnen@gmail.com>',
    'website':'http://miketelahun.wordpress.com',
    'depends': [
        'hr_payroll_extension',
        'hr_security',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'wizard/batch_employee_add_view.xml',
        'bonus_data.xml',
        'bonus_view.xml',
        'bonus_workflow.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
