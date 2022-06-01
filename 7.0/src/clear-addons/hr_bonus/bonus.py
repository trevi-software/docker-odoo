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

from datetime import datetime

from openerp import netsvc
from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _

class hr_bonus_sheet(osv.Model):
    
    _name = 'hr.bonus'
    _description = 'Individual Bonus'
    
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    
    _columns = {
        'date_end': fields.date('To', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'recorder_id': fields.many2one('hr.employee', 'Prepared By', readonly=True,
                                       states={'draft': [('readonly', False)]}),
        'state': fields.selection([('draft', 'Draft'),
                                   ('approve', 'Approved'),
                                   ('cancel', 'Cancelled'),
                                  ],
                                  'State', readonly=True),
        'line_ids': fields.one2many('hr.bonus.line', 'sheet_id', 'Bonus Lines'),
    }
    
    _defaults = {
        'state': 'draft',
    }
    
    _order = 'date_end desc'

    def _check_date(self, cr, uid, ids):
        for sheet in self.browse(cr, uid, ids):
            sheet_ids = self.search(cr, uid, [('date_end', '=', sheet.date_end),
                                              ('id', '<>', sheet.id)])
            if len(sheet_ids) > 0:
                return False
        return True
    
    _constraints = [
        (_check_date,
         _('You cannot have more than one bonus sheet per date.'),
         ['date_start','date_end']),
    ] 
    
    _track = {
        'state': {
            'hr_bonus.mt_alert_approved': lambda self, cr,uid, obj, ctx=None: obj['state'] == 'approve',
        },
    }

    def name_get(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        res = []
        datas = self.read(cr, uid, ids, ['date_end'], context=context)
        for data in datas:
            name = 'Bonus Sheet ' + data['date_end']
            res.append((data['id'], name))
        
        return res
    
    def _needaction_domain_get(self, cr, uid, context=None):
        
        domain = []
        if self.pool.get('res.users').has_group(cr, uid, 'base.group_hr_bonus'):
            domain = [('state','=','draft')]
        
        if len(domain) == 0:
            return False
        
        return domain
    
    def action_delete_lines(self, cr, uid, ids, context=None):
        
        line_obj = self.pool.get('hr.bonus.line')
        line_ids = line_obj.search(cr, uid, [('sheet_id', 'in', ids)], context=context)
        if len(line_ids) > 0:
            line_obj.unlink(cr, uid, line_ids, context=context)
        return True

    def set_to_draft(self, cr, uid, ids, context=None):
        
        self.write(cr, uid, ids, {
            'state': 'draft',
        })
        wf_service = netsvc.LocalService("workflow")
        for i in ids:
            wf_service.trg_delete(uid, 'hr.bonus', i, cr)
            wf_service.trg_create(uid, 'hr.bonus', i, cr)
        return True

class hr_bonus_evaluation_daily(osv.Model):
    
    _name = 'hr.bonus.line'
    _description = 'Bonus Employee Line'
    
    _columns = {
        'sheet_id': fields.many2one('hr.bonus', 'Bonus Sheet'),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'amount': fields.float('Bonus Amount', digits_compute=dp.get_precision('Payroll'),
                               required=True),
        'type': fields.selection([('percent', 'Percentage'), ('fix', 'Fixed')], 'Type',
                                 required=True),
    }
    
    _defaults = {
        'type': 'percent',
    }

    def name_get(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        bonus_obj = self.pool.get('hr.bonus')
        res = []
        for line in self.browse(cr, uid, ids, context=context):
            data = bonus_obj.name_get(cr, uid, [line.sheet_id.id], context=context)
            name = data[0][1]
            name += ' ' + line.employee_id.name
            res.append((line.id, name))
        
        return res
