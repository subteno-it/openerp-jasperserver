# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP, Management module for Jasper Server
#    Copyright (C) 2010 SYLEAM Info Services (<http://www.syleam.fr/>)
#              Christophe CHAUVET
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

from osv import osv
from osv import fields


class IrValues(osv.osv):
    _inherit = 'ir.values'

    def get(self, cr, uid, key, key2, models, meta=False, context=None, res_id_req=False, without_user=True, key2_req=True):
        if context is None:
            context = {}
        res = super(IrValues, self).get(cr, uid, key, key2, models, meta, context, res_id_req, without_user, key2_req)
        if key == 'action' and key2 == 'client_print_multi':
            ## Add jasper report
            jd_obj = self.pool.get('jasper.document')
            mod_ids = self.pool.get('ir.model').search(cr, uid, [('model', '=', models[0][0])], context=context)
            if not mod_ids:
                return res
            model_id = mod_ids[0]
            jd_ids = jd_obj.search(cr, uid, [('model_id', '=', model_id), ('enabled', '=', True)], context=context)
            for e in jd_obj.browse(cr, uid, jd_ids, context=context):
                if e.ctx and not eval(e.ctx, {'context': context}):
                    continue
                d = {
                    'groups_id': [x.id for x in e.group_ids],
                     'multi': e.toolbar,
                     'name': e.name,
                     'wiz_name': 'jasper.%s' % e.service,
                     'jasper': False,
                     'usage': False,
                     'model': models[0][0],
                     'type': u'ir.actions.wizard',
                     'id': e.id,
                }

                r = (e.id, e.name, d)
                res.append(r)
        return res

IrValues()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
