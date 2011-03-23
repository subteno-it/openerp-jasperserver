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

__name__ = "Remove old wizard entry"


def migrate(cr, v):
    """
    Put your explanation here

    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""DELETE
                  FROM   ir_act_wizard
                  WHERE id IN (
                      SELECT res_id
                      FROM   ir_model_data
                      WHERE  module='jasper_server'
                      AND    model = 'ir.actions.wizard')
                  AND model NOT IN ('jasper.document','ir.model')""")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
