# -*- encoding: utf-8 -*-
##############################################################################
#
#    Clock Reader for OpenERP
#    Copyright (C) 2004-2009 Moldeo Interactive CT
#    (<http://www.moldeointeractive.com.ar>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time

from openerp.osv import fields, orm

class registration_report(orm.TransientModel):
    
    _name = 'hr.clock_reader.registration'
    _description = 'Registration Quality Wizard'
    
    _columns = {
        'date_from': fields.date('Start', required=True),
        'date_to': fields.date('End', required=True),
    }
    
    _defaults = {
        'date_from': time.strftime('%Y-%m-%d'),
        'date_to': time.strftime('%Y-%m-%d'),
    }
    
    def print_report(self, cr, uid, ids, context=None):

        if context is None:
            context = {}
        datas = {'form': self.read(cr, uid, ids)[0],
                 'model': 'hr.attendance'}
        datas['ids'] = []
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'hr_clock_reader.registration_quality_report',
            'datas': datas,
        }
