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
    'name': 'Performance Incentive',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'description': """
Performance Incentive
=====================

This module adds an additional payroll rule for performance incentive. The incentive is
based on attendance (such as number of days late or absent) and disciplinary actions (such
as the number of warnings received in a month, etc.).

A wide number of data are gather to aid in calculating performance. These are placed in
the worked_days dict so that they can be accessed in rules. They are:
    * NFRA - number of infractions for not taking care of equipment/materials and for not following company rules and regulations
    * TARDY - number of attendance alerts for being late for work
    * WARNW - number of written warnings
    * WARNV - number of verbal warnings
    * UNAOTD - unapproved normal over time
    * UNAOTN - unapproved nightly over time (does not work yet; lumped with UNAOTD for now)
    * UNAOTR - unapproved rest day over time
    * UNAOTH - unapproved holiday over time
    """,
    'author':'Michael Telahun Makonnen <mmakonnen@gmail.com>',
    'website':'http://miketelahun.wordpress.com',
    'depends': [
        'hr_infraction',
        'hr_payroll_extension',
        'hr_schedule',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'hr_performance_incentive_data.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
