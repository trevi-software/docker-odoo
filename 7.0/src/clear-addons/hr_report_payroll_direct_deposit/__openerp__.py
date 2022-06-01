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
    'name': 'Payroll Register Direct Deposit Report',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'description': """
Payroll Direct Deposit Report
============================
    - Complete list of
        - Employees
        - Net Pay
        - Bank Account
    - Only applies to employees who have opted for Direct Deposit
    """,
    'author':'Michael Telahun Makonnen <mmakonnen@gmail.com>',
    'website':'http://miketelahun.wordpress.com',
    'depends': [
        'currency_denomination',
        'hr_payroll_direct_deposit',
        'hr_payroll_register',
        'report_aeroo',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'hr_payroll_dd_report.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
