# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP, Management module for Jasper Server
#    Copyright (C) 2013 SYLEAM (<http://www.syleam.fr/>)
#              Christophe CHAUVET <christophe.chauvet@syleam.fr>
#
#    This file is a part of jasper_server
#
#    jasper_server is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    jasper_server is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from httplib2 import Http
import socket

from lxml import etree


## Create some exception
class JasperException(Exception):
    pass


class ServerNotFound(JasperException):
    pass


class AuthError(JasperException):
    pass


## Create some XML element to resourceDescriptor
class Request(etree.ElementBase):
    TAG = 'request'

    def __init__(self, operationName='runReport', locale='en_US'):
        super(Request, self).__init__(operationName=operationName, locale=locale)


class RequestRD(etree.ElementBase):
    TAG = 'resourceDescriptor'

    def __init__(self, wsType, name='', uriString=''):
        super(RequestRD, self).__init__(name=name, wsType=wsType, uriString=uriString)


class RequestArgument(etree.ElementBase):
    TAG = 'argument'

    def __init__(self, name='', value=''):
        super(RequestArgument, self).__init__(name=name)
        self.text = value

NSMAP = {
    'SOAP-ENV': "http://schemas.xmlsoap.org/soap/envelope/",
    'xsd': "http://www.w3.org/2001/XMLSchema",
    'xsi': "http://www.w3.org/2001/XMLSchema-instance",
    'SOAP-ENC': "http://schemas.xmlsoap.org/soap/encoding/",
    'ns4': "http://www.jaspersoft.com/client",
}


class SoapEnv(object):
    def __init__(self, wsType='list', action=''):
        self.soap = etree.Element('{%s}Envelope' % NSMAP['SOAP-ENV'], nsmap=NSMAP)
        body = etree.Element('{%s}Body' % NSMAP['SOAP-ENV'])
        action_body = etree.Element('{%s}%s' % (NSMAP['ns4'], wsType))
        action_body.text = action
        body.append(action_body)
        self.soap.append(body)

    def output(self,):
        return etree.tostring(self.soap, pretty_print=True)


class Jasper(object):

    def __init__(self, host='localhost', port=8080, user='jasperadmin', pwd='jasperadmin'):
        """
        Initialise new Jasper Object
        """
        self.cnx = Http()

        self.host = host
        self.port = port
        self.user = user
        self.pwd = pwd
        self.repo = 'jasperserver/services/repository'

        self.headers = {
            'Content-type': 'text/xml',
            'charset': 'UTF-8',
            'SOAPAction': 'runReport'
        }
        self.body = ''

    def auth(self,):
        """
        Add credential
        """
        self.cnx.add_credentials(self.user, self.pwd)

        # We must simulate a request if we want to check the auth is correct
        uri = 'http://%s:%s/%s' % (self.host, self.port, self.repo)

        # Generate a soap query to verify the authentification
        rq = Request(operationName='list', locale='fr_FR')
        rq.append(RequestRD('folder', '', '/'))
        self.body = SoapEnv('runReport', etree.tostring(rq)).output()
        try:
            res, content = self.cnx.request(uri, 'POST', self.body, self.headers)
        except socket.error:
            raise ServerNotFound('Server not found')

        if res.get('status', '200') == '401':
            raise AuthError('Authentification Failed !')
        elif res.get('status', '200') != '200':
            return False

        return True

    def create_request(self, arguments=None,):
        if arguments is None:
            arguments = {}

        rq = Request(locale='fr_FR')
        for k in arguments:
            rq.append(RequestArgument(name=k, value=arguments[k]))
        rq.append(RequestRD('runReport', '', '/openerp/bases'))
        return etree.tostring(rq, pretty_print=True)

    def log_last_request(self,):
        """
        Return the last SOAP query as text
        """
        return self.body

if __name__ == '__main__':
    js = Jasper('localhost', 8180, 'jasperadmin', 'jasperadmin')
    try:
        js.auth()
    except ServerNotFound:
        print 'Error, server not found %s %d' % (js.host, js.port)
    except AuthError:
        print 'Error, Authentification failed for %s/%s' % (js.user, js.pwd)

    args = {
        'RUN_OUTPUT_FORMAT': 'PDF',
        'PAGE': '0',
    }
    x = js.create_request(arguments=args)
    print x
    print SoapEnv('list', x).output()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
