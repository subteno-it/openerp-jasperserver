# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP, 
#    Copyright (C) 2010 SYLEAM Info Services (<http://www.syleam.fr/>) Christophe CHAUVET
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
import base64

init_form = """<?xml version="1.0" ?>
<form string="Make template">
  <field name="model" colspan="4" width="300"/>
  <field name="depth"/>
  <field name="model_id"/>
</form>
"""

init_fields = {
    'model': {'string': 'Model', 'type': 'many2one', 'relation': 'ir.model', 'required': True},
    'depth': {'string': 'Depth', 'type': 'integer', 'required': True, 'default': 3},
    'model_id': {'string': 'Id', 'type': 'integer', 'required': True, 'default': 1},
}

def _init(self, cr, uid, data, context):
    print 'DATA: %r' % data
    print 'CONTEXT: %r' % context
    return {}

save_form = """<?xml version="1.0" ?>
<form string="Save template">
  <field name="datas" filename="filename"/>
  <field name="filename" invisible="1"/>
</form>
"""

save_fields = {
    'datas': {'string': 'Data', 'type': 'binary', 'readonly': True},
    'filename': {'string': 'Filename', 'type': 'char', 'size': 128},
}


def _generate(self, cr, uid, data, context):
    
    print 'GENERATE'
    datas = base64.encodestring('TEST')
    filename = 'jasper.xml'
    res = {'datas': datas , 'filename': filename}
    return res

class make_template(wizard.interface):

    states = {
        'init' : {
            'actions': [_init],
            'result': {
                'type': 'form',
                'arch': init_form,
                'fields': init_fields,
                'state': [('end','Cancel','gtk-cancel'), ('valid', 'OK', 'gtk-ok', True)],
            }
        },
        'valid': {
            'actions': [_generate],
            'result': {
                'type': 'form',
                'arch': save_form,
                'fields': save_fields,
                'state': [('end', 'Done', 'gtk-ok')],
            }
        }
    }

make_template('jasper_server.make_template')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
