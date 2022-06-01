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

from datetime import datetime

import pooler
from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT

class clock_connect(orm.TransientModel):
    
    _name = 'hr.clock_reader.clock.connect'
    _description = 'Clock Reader Connect Wizard'
    
    _columns = {
        'date_start': fields.datetime('Start'),
        'date_end': fields.datetime('End'),
        'clock_ids': fields.many2many('hr_clock_reader.clock', 'hr_clock_reader_connect_wizard_rel',
                                      'clock_id', 'wizard_id', string='Clock Readers'),
        'override': fields.boolean('Override Clock Options'),
        'state': fields.selection([('step1', 'Step 1'), ('step2', 'Step 2')], 'State', required=True),
        
        # First Step
        'unknown': fields.boolean('Create Employees'),
        'complete': fields.boolean('Complete Attendance'),
        'tolerance': fields.integer('Same Entry Tolerance'),
        'ignore_signs': fields.boolean('Ignore sign-in/sign-out'),
        'ignore_restrictions': fields.boolean('Ignore DB Restrictions'),
        
        # Second Step
        'count': fields.integer('Number of Items'),
        'errors': fields.text('Errors'),
    }
    
    def _get_clocks(self, cr, uid, ids, context=None):
        return self.pool.get('hr_clock_reader.clock').search(cr, uid, [], context=context)
    
    _defaults = {
        'clock_ids': _get_clocks,
        'state': 'step1',
        'tolerance': 60,
    }

    
    def _read_clock(self, cr, uid, data, context=None):
        pool = pooler.get_pool(cr.dbname)
        clock_pool = pool.get('hr_clock_reader.clock')
    
        dtStart = None
        dtEnd = None
        if data.get('date_start', False):
            dtStart = datetime.strptime(data['date_start'], OE_DTFORMAT)
        if data.get('date_end', False):
            dtEnd = datetime.strptime(data['date_end'], OE_DTFORMAT)
        
        if data['override']:
            create_unknown_employee = data['unknown']
            complete_attendance = data['complete']
            tolerance = data['tolerance']
            ignore_signs = data['ignore_signs']
            ignore_restrictions = ['ignore_restrictions']
        else:
            create_unknown_employee = None
            complete_attendance = None
            tolerance = None
            ignore_signs = None
            ignore_restrictions = None

        count, errors = self.pool.get('hr_clock_reader.clock').read_clocks(cr, uid, data['clock_ids'],
                                                dtStart=dtStart, dtEnd=dtEnd,
                                                create_unknown_employee=create_unknown_employee,
                                                complete_attendance=complete_attendance,
                                                tolerance=tolerance,
                                                ignore_sign_inout=ignore_signs,
                                                ignore_restrictions=ignore_restrictions,
                                                context=context)

        return {'count': count, 'errors': '\n'.join(errors)}
    
    def action_next(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        data = self.read(cr, uid, ids[0], [], context=context)
        
        vals = self._read_clock(cr, uid, data, context)
        vals.update({'state': 'step2'})
        
        # update state to  step2
        self.write(cr, uid, ids, vals, context=context)
        
        #return view
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.clock_reader.clock.connect',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': ids[0],
            'views': [(False, 'form')],
            'target': 'new',
             }
