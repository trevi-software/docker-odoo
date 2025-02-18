#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2012 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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
    'name': 'Ethiopia - Leave Application',
    'version': '1.0',
    'category': 'Localization/Human Resources',
    'description': """
HR Leaves (Holidays) Localization for Ethiopia
===============================================

    """,
    'author':'Michael Telahun Makonnen <mmakonnen@gmail.com>',
    'website':'http://miketelahun.wordpress.com',
    'depends': [
        'ethiopic_calendar',
        'hr_holidays_extension',
        'hr_parameters',
        'report_aeroo',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'report/all_reports.xml',
        'hr_holidays_view.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}