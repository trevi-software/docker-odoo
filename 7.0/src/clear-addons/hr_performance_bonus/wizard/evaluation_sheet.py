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

from datetime import datetime, timedelta

from openerp.addons import decimal_precision as dp
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT

from openerp.addons.hr_performance_bonus.bonus import ITYPE_SELECTION

class evaluation_sheet(osv.TransientModel):
    
    _name = 'hr.bonus.evaluation.wizard'
    _description = 'Bonus Evaluation Recording Format'
    
    _columns = {
        'sheet_id': fields.many2one('hr.bonus.sheet', 'Bonus Sheet', required=True),
        'date_start': fields.date('Start Date', required=True, readonly=True),
        'date_end': fields.date('End Date', required=True, readonly=True),
        'department_id': fields.many2one('hr.department', 'Department', required=True, readonly=True),
        'line_ids': fields.one2many('hr.bonus.evaluation.wizard.line', 'wizard_id', 'Evaluation Records'),
        'daily_line_ids': fields.one2many('hr.bonus.evaluation.wizard.daily.line', 'wizard_id', 'Daily Records'),
        'incentive_type': fields.selection(ITYPE_SELECTION, 'Incentive Type', readonly=True),
    }
    
    def _get(self, cr, uid, context=None):
        
        if context == None:
            context= {}
        sheet_id = context.get('active_id', False)
        return  self.pool.get('hr.bonus.sheet').read(cr, uid, sheet_id,
                                                    ['date_start', 'date_end', 'department_id',
                                                     'recorder_id', 'incentive_type'],
                                                    context=context)
    
    def _get_sheet(self, cr, uid, context=None):
        
        return self._get(cr, uid, context=context)['id']
    
    def _get_start(self, cr, uid, context=None):
        
        return self._get(cr, uid, context=context)['date_start']
    
    def _get_end(self, cr, uid, context=None):
        
        return self._get(cr, uid, context=context)['date_end']
    
    def _get_department(self, cr, uid, context=None):
        
        return self._get(cr, uid, context=context)['department_id'][0]
    
    def _get_incentive(self, cr, uid, context=None):
        
        return self._get(cr, uid, context=context)['incentive_type']

    def _get_lines(self, cr, uid, context=None):
        
        res = []
        sheet_id = self._get_sheet(cr, uid, context=context)
        sheet = self.pool.get('hr.bonus.sheet').browse(cr, uid, sheet_id, context=context)
        if sheet.incentive_type == 'fixed':
            for criteria in sheet.criteria_collection_id.criteria_ids:
                vals = {
                    'criteria_id': criteria.id,
                }
                res.append(vals)
        
        return res

    def _get_daily_lines(self, cr, uid, context=None):
        
        res = []
        sheet_id = self._get_sheet(cr, uid, context=context)
        sheet = self.pool.get('hr.bonus.sheet').browse(cr, uid, sheet_id, context=context)
        if sheet.incentive_type == 'daily':
            dStart = datetime.strptime(sheet.date_start, OE_DFORMAT).date()
            dEnd = datetime.strptime(sheet.date_end, OE_DFORMAT).date()
            dCount = dStart
            while dCount <= dEnd:
                res.append({'date': dCount.strftime(OE_DFORMAT), 'points': 0.00})
                dCount += timedelta(days= +1)
        
        return res
    
    _defaults = {
        'sheet_id': _get_sheet,
        'date_start': _get_start,
        'date_end': _get_end,
        'department_id': _get_department,
        'incentive_type': _get_incentive,
        'line_ids': _get_lines,
        'daily_line_ids': _get_daily_lines,
    }
    
    def add_records(self, cr, uid, ids, context=None):
        
        sheet_obj = self.pool.get('hr.bonus.sheet')
        wizard = self.browse(cr, uid, ids[0], context=context)
        sheet_obj.action_delete_lines(cr, uid, [wizard.sheet_id.id], context=context)
        if wizard.incentive_type == 'fixed':
            return self.add_records_fixed(cr, uid, wizard, context=context)
        elif wizard.incentive_type == 'daily':
            return self.add_records_daily(cr, uid, wizard, context=context)
        return
    
    def add_records_fixed(self, cr, uid, wizard, context=None):
        
        crit_vals = []
        for line in wizard.line_ids:
            
            points = 0
            if line.points > 0:
                points = line.points
            crit_vals.append((0, 0, {'criteria_id': line.criteria_id.id, 'points': points}))
        line_val = {
            'sheet_id': wizard.sheet_id.id,
            'line_ids': crit_vals,
        }
        eval_id = self.pool.get('hr.bonus.evaluation.fixed').create(cr, uid, line_val,
                                                                    context=context)
        sheet_obj = self.pool.get('hr.bonus.sheet')
        sheet_obj.write(cr, uid, wizard.sheet_id.id, {'eval_fixed_id': eval_id},
                        context=context)
        
        return {'type': 'ir.actions.act_window_close'}
    
    def add_records_daily(self, cr, uid, wizard, context=None):
        
        vals = [(0, 0, {'date': line.date, 'points': line.points}) for line in wizard.daily_line_ids]
        sheet_obj = self.pool.get('hr.bonus.sheet')
        sheet_obj.write(cr, uid, wizard.sheet_id.id, {'eval_daily_ids': vals},
                        context=context)
        
        return {'type': 'ir.actions.act_window_close'}

class wizard_line(osv.TransientModel):
    
    _name = 'hr.bonus.evaluation.wizard.line'
    _description = 'Bonus Evaluation Format Line Item'
    
    _columns = {
        'wizard_id': fields.many2one('hr.bonus.evaluation.wizard', 'Wizard'),
        'criteria_id': fields.many2one('hr.bonus.criteria', 'Criteria', readonly=True),
        'points': fields.float('Points', digits_compute=dp.get_precision('Payroll'), required=True),
    }

class wizard_daily_line(osv.TransientModel):
    
    _name = 'hr.bonus.evaluation.wizard.daily.line'
    _description = 'Daily Bonus Evaluation Wizard Line Item'
    
    _columns = {
        'wizard_id': fields.many2one('hr.bonus.evaluation.wizard', 'Wizard'),
        'date': fields.date('Date', required=True),
        'points': fields.float('Bonus', digits_compute=dp.get_precision('Payroll'), required=True),
    }
