# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server_wizard_sample module for OpenERP, Sample to show haw to launch report from wizard
#    Copyright (C) 2011 SYLEAM (<http://www.syleam.fr/>)
#              Christophe CHAUVET <christophe.chauvet@syleam.fr>
#
#    This file is a part of jasper_server_wizard_sample
#
#    jasper_server_wizard_sample is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    jasper_server_wizard_sample is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv
from osv import fields
import time


class ShowSample(osv.osv_memory):
    _name = 'show.sample.wizard'
    _description = 'Demonstration how to launch report from wizard'

    _columns = {
        'name': fields.char('Name', size=64, help='Name of the printing document', required=True),
        'partner_id': fields.many2one('res.partner', 'Partner', required=True),
        'final': fields.boolean('Final'),
        'date_start': fields.date('Start date', required=True),
        'date_end': fields.date('End date', required=True),
    }

    _defaults = {
        'final': lambda *a: False,
        'date_start': lambda *a: time.strftime('%Y-%m-01'),
        'date_end': lambda *a: time.strftime('%Y-%m-10'),
    }

    def launch(self, cr, uid, ids, context=None):
        """
        Launch the report, and pass each value in the form as parameters
        """
        wiz = self.browse(cr, uid, ids, context=context)[0]
        data = {}
        data['ids'] = [wiz.partner_id.id]
        data['model'] = 'res.partner'
        data['jasper'] = {
            'doc_name': wiz.name,
            'final_version': wiz.final,
            'start_date': wiz.date_start,
            'end_data': wiz.date_end,
        }

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'jasper.partner_list',
            'datas': data,
        }

ShowSample()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
