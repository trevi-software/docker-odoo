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
    'name': 'Performance Incentive - Bonus',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'description': """
Performance Incentive by Departimental Bonus Points
===================================================
Each department is assigned bonus points based on pre-determined evaluation
criteria (configurable from Human Resources -> Configuration -> Bonus).

Adds a new 'worked_days' statistic: BNS1
The number_of_days and number_of_hours field contain the average points in
the department the job belongs to. The 'rate' contains the bonus amount
specified in the bonus sheet.
    """,
    'author':'Michael Telahun Makonnen <mmakonnen@gmail.com>',
    'website':'http://miketelahun.wordpress.com',
    'depends': [
        'hr',
        'hr_payroll_extension',
        'hr_security',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'wizard/evaluation_sheet_view.xml',
        'bonus_data.xml',
        'bonus_view.xml',
        'bonus_workflow.xml',
        'res_config_view.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
