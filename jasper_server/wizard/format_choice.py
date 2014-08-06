# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP,
#    Copyright (C) 2010-2011 SYLEAM Info Services (<http://www.Syleam.fr/>)
#                            Damien CRIER
#
#    This file is a part of jasper_server
#
#    jasper_server is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    jasper_server is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import wizard
import pooler
from tools.translate import _

form = """<?xml version="1.0" ?>
<form string="Format choice">
  <field name="format_choice" colspan="4" width="300"/>
</form>
"""


def _get_formats(self, cr, uid, data, context=None):
    pool = pooler.get_pool(cr.dbname)
    # print 'data %r'%data
    res = pool.get('jasper.document').get_formats(cr, uid, [])
    return res

fields = {
    'format_choice': {'string': 'Format', 'type': 'selection',
                      'selection': _get_formats, 'required': True},
}


class format_choice(wizard.interface):
    """
    If format = multi, compose a wizard to ask the extension of document
    if format = mono, just launch teh report and return the format previously
                      defined
    """

    def _select_format(self, cr, uid, data, context=None):
        if context is None:
            context = {}
        wiz_name = self.wiz_name.replace('jasper.', '')
        pool = pooler.get_pool(cr.dbname)
        document_obj = pool.get('jasper.document')
        doc_ids = document_obj.search(cr, uid, [('service', '=', wiz_name)])
        if not doc_ids:
            raise wizard.except_wizard(_('Error'), _('No report found!'))
        document = document_obj.browse(cr, uid, doc_ids[0], context=context)
        if document.id:
            if document.format_choice == 'mono':
                action = 'create_wizard'
            elif document.format_choice == 'multi':
                action = 'format_choice'
                raise wizard.except_wizard(_('Error'),
                                           _('No implemented yet!'))
        ##
        # Compose the uri to launch to JasperServer
        #
        return action

    def _create_wizard(self, cr, uid, data, context=None):
        wiz_name = self.wiz_name.replace('jasper.', '')
        pool = pooler.get_pool(cr.dbname)
        document_obj = pool.get('jasper.document')
        doc_ids = document_obj.search(cr, uid, [('service', '=', wiz_name)])
        if not doc_ids:
            raise wizard.except_wizard(_('Error'), _('No report found!'))
        document = document_obj.browse(cr, uid, doc_ids[0], context=context)
        option = {
            'id': document.id,
            'attachment': document.attachment,
            'attachment_use': document.attachment_use,
        }
        uri = '/openerp/bases/%s/%s' % (cr.dbname, document.report_unit)
        data['form']['params'] = (document.format, uri, document.mode,
                                  document.depth, option)
        data['form']['ids'] = data['ids']
        return data['form']

    states = {
        'init': {
            'actions': [],
            'result': {'type': 'choice',
                       'next_state': _select_format}
        },
        'format_choice': {
            'actions': [],
            'result': {
                'type': 'form',
                'arch': form,
                'fields': fields,
                'state': (('end', 'Cancel', 'gtk-cancel'),
                          ('create_wizard', 'OK', 'gtk-ok', True))
            }
        },
        'create_wizard': {
            'actions': [_create_wizard],
            'result': {
                'type': 'print',
                'report': 'print.jasper.server',
                'state': 'end'
            }
        },
    }

format_choice('jasper_server.document_print')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
