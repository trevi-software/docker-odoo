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
    'name': 'Period Wage Adjustment Policy',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'description': """
Automatic Wage Adjustments
==========================
Define wage adjustments that are intiated on a fixed schedule: weekly, monthly, annually.
Each policy has an effective date and related policy lines. Each policy specifies the
frequency of the calculations and a list of templates to use for the wage adjustment. The
templates specify how the calculation is done at which milestones. The milestones are the
number of months the employee has been employed at the time of the calculation.
    """,
    'author':'Michael Telahun Makonnen <mmakonnen@gmail.com>',
    'website':'http://miketelahun.wordpress.com',
    'depends': [
        'hr_contract_state',
        'hr_employee_seniority',
        'hr_policy_group',
        'hr_wage_increment',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'security/ir.model.access.csv',
        'hr_policy_cron.xml',
        'hr_policy_view.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
