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
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
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
from lxml import etree
from StringIO import StringIO

import socket
import re
import email
import os

KNOWN_FORMAT = [
    'PDF', 'XLS', 'XLSX', 'HTML', 'RTF',
    'CSV', 'XML', 'DOCX', 'ODT', 'ODS',
    'JPRINT'
]


# Create some exception
class JasperException(Exception):
    pass


class ServerNotFound(JasperException):
    pass


class AuthError(JasperException):
    pass


class NotMultipartContent(JasperException):
    pass


class UnknownResponse(JasperException):
    pass


class ServerError(JasperException):
    pass


class UnknownFormat(JasperException):
    pass


# Create some XML element to resourceDescriptor
class Request(etree.ElementBase):
    TAG = 'request'

    def __init__(self, operationName='runReport', locale='en_US'):
        super(Request, self).__init__(operationName=operationName,
                                      locale=locale)


class RequestRD(etree.ElementBase):
    TAG = 'resourceDescriptor'

    def __init__(self, wsType, name='', uriString=''):
        super(RequestRD, self).__init__(name=name, wsType=wsType,
                                        uriString=uriString)


class RequestArgument(etree.ElementBase):
    TAG = 'argument'

    def __init__(self, name='', value=''):
        super(RequestArgument, self).__init__(name=name)
        self.text = value


class SoapEnv(object):

    NSMAP = {
        'SOAP-ENV': "http://schemas.xmlsoap.org/soap/envelope/",
        'xsd': "http://www.w3.org/2001/XMLSchema",
        'xsi': "http://www.w3.org/2001/XMLSchema-instance",
        'SOAP-ENC': "http://schemas.xmlsoap.org/soap/encoding/",
        'ns4': "http://www.jaspersoft.com/client",
    }

    def __init__(self, wsType='list', action=''):
        self.soap = etree.Element('{%s}Envelope' % self.NSMAP['SOAP-ENV'],
                                  nsmap=self.NSMAP)
        body = etree.SubElement(self.soap, '{%s}Body' %
                                self.NSMAP['SOAP-ENV'])
        action_body = etree.SubElement(body, '{%s}%s' % (self.NSMAP['ns4'],
                                                         wsType))
        request = etree.SubElement(action_body, 'request')
        request.set('{%s}type' % (self.NSMAP['xsi'],), 'xsd:string')
        request.text = action

    def output(self,):
        return etree.tostring(self.soap, pretty_print=True)


class Jasper(object):

    def __init__(self, host='localhost', port=8080, user='jasperadmin',
                 pwd='jasperadmin'):
        """
        Initialise new Jasper Object
        """
        self.cnx = Http()

        self.host = host
        self.port = port
        self.user = user
        self.pwd = pwd
        self.repo = 'jasperserver/services/repository'
        self.uri = 'http://%s:%s/%s' % (self.host, self.port, self.repo)

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

        # Generate a soap query to verify the authentification
        rq = Request(operationName='list', locale='fr_FR')
        rq.append(RequestRD('folder', '', '/'))
        self.body = SoapEnv('list', etree.tostring(rq)).output()
        try:
            res, content = self.cnx.request(self.uri, 'POST', self.body,
                                            self.headers)
        except socket.error:
            raise ServerNotFound('Server not found')

        if res.get('status', '200') == '401':
            raise AuthError('Authentification Failed !')
        elif res.get('status', '200') != '200':
            return False

        return True

    def send(self, soapQuery=''):
        try:
            res, content = self.cnx.request(self.uri, 'POST', soapQuery,
                                            self.headers)
        except socket.error:
            raise ServerNotFound('Server not found')

        if res.get('status', '200') == '401':
            raise AuthError('Authentification Failed !')
        elif res.get('status', '200') != '200':
            return False

        try:
            return self.parseMultipart(content)
        except NotMultipartContent:
            fp = StringIO(content)
            tree = etree.parse(fp)
            fp.close()
            r = tree.xpath('//runReportReturn')
            if not r:
                raise UnknownResponse(content)

            fp = StringIO(r[0].text.encode('utf-8'))
            tree = etree.parse(fp)
            fp.close()

            raise ServerError('[' +
                              tree.xpath('//returnCode')[0].text.encode('utf-8')  # noqa
                              + ']' +
                              tree.xpath('//returnMessage')[0].text.encode('utf-8'))  # noqa

    def create_request(self, operation='list', wsType='', uri='/', name='',
                       arguments=None, params=None):
        if arguments is None:
            arguments = {}

        if params is None:
            params = {}

        rq = Request(operationName=operation, locale='fr_FR')
        for k in arguments:
            rq.append(RequestArgument(name=k, value=arguments[k]))

        # Add resource descriptor
        rd = RequestRD(operation, name, uri)
        label = etree.SubElement(rd, 'label')
        label.text = 'null'

        # Add query parameters
        for k, v in params.items():
            p = etree.SubElement(rd, 'parameter', name=k)
            if isinstance(v, basestring):
                p.text = v
            else:
                p.text = str(v)

        rq.append(rd)
        return etree.tostring(rq, pretty_print=True)

    def run_report(self, uri='/', output='PDF', params=None):
        """
        Launch a runReport in Jasper
        """
        if output not in KNOWN_FORMAT:
            raise UnknownFormat(output)

        args = {
            'RUN_OUTPUT_FORMAT': output,
            'PAGE': '0',
        }

        return self.create_request(operation='runReport', wsType='reportUnit',
                                   uri=uri, arguments=args, params=params)

    @staticmethod
    def parseMultipart(res):
        srch = re.search(r'----=[^\r\n]*', res)
        if srch is None:
            raise NotMultipartContent()

        boundary = srch.group()
        res = " \n" + res
        res = "Content-Type: multipart/alternative; boundary=%s\n%s" % \
              (boundary, res)
        message = email.message_from_string(res)
        attachment = message.get_payload()[1]
        return {'content-type': attachment.get_content_type(),
                'data': attachment.get_payload()}

    def log_last_request(self,):
        """
        Return the last SOAP query as text
        """
        return self.body

if __name__ == '__main__':
    tjs_host = os.environ.get('JS_HOST', 'localhost')
    tjs_port = os.environ.get('JS_PORT', 8080)
    tjs_user = os.environ.get('JS_USER', 'jasperadmin')
    tjs_pass = os.environ.get('JS_PASS', 'jasperadmin')

    try:
        js = Jasper(tjs_host, int(tjs_port), tjs_user, tjs_pass)
        js.auth()
    except ServerNotFound:
        print 'Error, server not found %s %d' % (js.host, js.port)
    except AuthError:
        print 'Error, Authentification failed for %s/%s' % (js.user, js.pwd)

    params = {
        'OERP_COMPANY_ID': 1,
        'OERP_ACTIVE_ID': 1,
        'OERP_ACTIVE_IDS': '1,2,3',
    }
    try:
        envelop = js.run_report(uri='/reports/samples/AllAccounts',
                                output='PDF', params=params)
        a = js.send(SoapEnv('runReport', envelop).output())
        f = file('AllAccounts.pdf', 'w')
        f.write(a['data'])
        f.close()
    except ServerNotFound:
        print 'Error, server not found %s %d' % (js.host, js.port)
    except AuthError:
        print 'Error, Authentification failed for %s/%s' % (js.user, js.pwd)

    try:
        envelop = js.run_report(uri='/reports/samples/AllAccounts',
                                output='XLS', params=params)
        a = js.send(SoapEnv('runReport', envelop).output())
        f = file('AllAccounts.xls', 'w')
        f.write(a['data'])
        f.close()
    except ServerNotFound:
        print 'Error, server not found %s %d' % (js.host, js.port)
    except AuthError:
        print 'Error, Authentification failed for %s/%s' % (js.user, js.pwd)
    except ServerError, e:
        print str(e)

    try:
        envelop = js.run_report(uri='/reports/samples/AllAccounts',
                                output='ODS', params=params)
        a = js.send(SoapEnv('runReport', envelop).output())
        f = file('AllAccounts.ods', 'w')
        f.write(a['data'])
        f.close()
    except ServerNotFound:
        print 'Error, server not found %s %d' % (js.host, js.port)
    except AuthError:
        print 'Error, Authentification failed for %s/%s' % (js.user, js.pwd)
    except ServerError, e:
        print str(e)

    # Check unknown format
    try:
        envelop = js.run_report(uri='/reports/samples/AllAccounts',
                                output='PDX', params=params)
        a = js.send(SoapEnv('runReport', envelop).output())
        f = file('AllAccounts.pdf', 'w')
        f.write(a['data'])
        f.close()
    except ServerNotFound:
        print 'Error, server not found %s %d' % (js.host, js.port)
    except AuthError:
        print 'Error, Authentification failed for %s/%s' % (js.user, js.pwd)
    except UnknownFormat as e:
        pass

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
