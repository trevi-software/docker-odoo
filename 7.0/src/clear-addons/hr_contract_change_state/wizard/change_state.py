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

from openerp import netsvc
from openerp.osv import fields, orm
from openerp.tools.translate import _

class hr_contract(orm.TransientModel):

    _name ='hr.contract.wizard.state.change'
    _description = 'Change state of contracts in batches'
    
    _columns = {
        'contract_ids': fields.many2many('hr.contract', 'hr_contract_state_change_wizard_rel',
                                    'wizard_id', 'contract_id', 'Contracts'),
        'do_approve': fields.boolean('Approve'),
        'do_trial_ok': fields.boolean('Successful Trial Period'),
    }
    
    def _get_active_records(self, cr, uid, context=None):
        
        res = []
        if context.get('active_ids', False):
            res = context['active_ids']
        
        return res
    
    _defaults = {
        'contract_ids': _get_active_records,
    }
    
    def onchange_approve(self, cr, uid, ids, twiddle_knob, context=None):
        
        res = {}
        if twiddle_knob:
            res.update({'value': {'do_trial_ok': False}})
        return res
    
    def onchange_trialok(self, cr, uid, ids, twiddle_knob, context=None):
        
        res = {}
        if twiddle_knob:
            res.update({'value': {'do_approve': False}})
        return res
    
    def change_state(self, cr, uid, ids, context=None):
        
        wizard = self.browse(cr, uid, ids[0], context=context)
        wkf = netsvc.LocalService('workflow')
        if wizard.do_approve:
            for contract in wizard.contract_ids:
                if contract.state == 'draft':
                    wkf.trg_validate(uid, 'hr.contract', contract.id, 'signal_confirm', cr)
        elif wizard.do_trial_ok:
            for contract in wizard.contract_ids:
                if contract.state in  ['trial', 'trial_ending']:
                    wkf.trg_validate(uid, 'hr.contract', contract.id, 'signal_open', cr)
        
        return {'type': 'ir.actions.act_window_close'}
