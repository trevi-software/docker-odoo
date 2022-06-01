#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Clear ICT Solutions <http://clearict.com>.
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

from openerp.osv import fields, orm
from openerp.tools.translate import _

class hr_payslip_employees(orm.TransientModel):

    _name ='hr.job.wizard.state.change'
    _description = 'Change recruitment state of jobs in batches'
    
    _columns = {
        'job_ids': fields.many2many('hr.job', 'hr_job_state_change_wizard_rel',
                                    'wizard_id', 'job_id', 'Jobs'),
        'do_open': fields.boolean('Close Recruitment'),
        'do_recruit': fields.boolean('Open for Recruitment'),
    }
    
    def _get_jobs(self, cr, uid, context=None):
        
        res = []
        if context.get('active_ids', False):
            res = context['active_ids']
        
        return res
    
    _defaults = {
        'job_ids': _get_jobs,
    }
    
    def onchange_open(self, cr, uid, ids, do_open, context=None):
        
        res = {}
        if do_open:
            res.update({'value': {'do_recruit': False}})
        return res
    
    def onchange_recruit(self, cr, uid, ids, do_recruit, context=None):
        
        res = {}
        if do_recruit:
            res.update({'value': {'do_open': False}})
        return res
    
    def change_state(self, cr, uid, ids, context=None):
        
        job_obj = self.pool.get('hr.job')
        wizard = self.browse(cr, uid, ids[0], context=context)
        if wizard.do_open:
            job_obj.job_open(cr, uid, [j.id for j in wizard.job_ids])
        elif wizard.do_recruit:
            job_obj.job_recruitement(cr, uid, [j.id for j in wizard.job_ids])
        
        return {'type': 'ir.actions.act_window_close'}
