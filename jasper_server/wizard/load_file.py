# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP,
#    Copyright (C) 2014 Mirounga (<http://www.mirounga.fr/>)
#                            Christophe CHAUVET <christophe.chauvet@gmail.com>
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

# from openerp.osv import osv
from openerp.osv import orm
from openerp.osv import fields
import base64


class LoadFile(orm.TransientModel):
    _name = 'load.jrxml.file'
    _description = 'Load file in the jasperdocument'

    _columns = {
        'datafile': fields.binary('File', required=True,
                                  help='Select file to transfert'),
    }

    def import_file(self, cr, uid, ids, context=None):
        print context
        this = self.browse(cr, uid, ids[0], context=context)
        content = base64.decodestring(this.datafile)
        self.pool['jasper.document'].parse_jrxml(
            cr, uid, context.get('active_ids'), content, context=context)

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
