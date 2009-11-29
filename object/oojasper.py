# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP, 
#    Copyright (C) 2009 SYLEAM Info Services (<http://www.syleam.fr/>) Christophe CHAUVET
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

class jasper_server(osv.osv):
    """
    Class to store the Jasper Server configuration
    """
    _name = 'jasper.server'
    _description = 'Jasper server configuration'
    _rec_name = 'host'

    _columns = {
        'host': fields.char('Host', size=128, required=True, help='Enter hostname or IP address'),
        'port': fields.integer('Port'),
        'user': fields.char('Username', size=128, required=True, help='Enter the username for JasperServer user, by default is jasperadmin'),
        'pass': fields.char('Password', size=128, required=True, help='Enter the password for the user, by defaul is jasperadmin'),
        'repo': fields.char('Repository', size=256, required=True, help='Enter the address of the repository'),
        'wsdl': fields.char('WSDL', size=256, help='Enter the address of the WSDL description'),
    }

    _defaults = {
        'host': lambda *a: 'localhost',
        'port': lambda *a: 8080,
        'user': lambda *a: 'jasperadmin',
        'pass': lambda *a: 'jasperadmin',
        'repo': lambda *a: '/jasperserver/services/repository',
        'wsdl': lambda *a: '/jasperserver/services/repository?wsdl',
    }

jasper_server()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
