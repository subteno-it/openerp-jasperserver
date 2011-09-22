# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP, Management module for Jasper Server
#    Copyright (C) 2011 SYLEAM (<http://www.syleam.fr/>)
#              Christophe CHAUVET <christophe.chauvet@syleam.fr>
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

from lxml.etree import Element, tostring
from tools.misc import ustr
import logging

_logger = logging.getLogger('jasper_server')

##
# Construct the body template for SOAP
#
BODY_TEMPLATE = """<SOAP-ENV:Envelope
 xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
 xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
 xmlns:ns4="http://www.jaspersoft.com/client"
 SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
<SOAP-ENV:Body>
<ns4:runReport>
<request xsi:type="xsd:string">
    &lt;request operationName=&quot;runReport&quot; locale=&quot;fr&quot;&gt;
        &lt;argument name=&quot;RUN_OUTPUT_FORMAT&quot;&gt;%(format)s&lt;/argument&gt;
        &lt;argument name=&quot;PAGE&quot;&gt;0&lt;/argument&gt;
        &lt;argument name=&quot;USE_DIME_ATTACHMENTS&quot;&gt;
            &lt;![CDATA[1]]&gt;
        &lt;/argument&gt;
        &lt;resourceDescriptor name=&quot;&quot; wsType=&quot;reportUnit&quot; uriString=&quot;%(path)s&quot; isNew=&quot;false&quot;&gt;
            &lt;label&gt;&lt;/label&gt;
            %(param)s
        &lt;/resourceDescriptor&gt;
    &lt;/request&gt;
</request></ns4:runReport>
</SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""


def entities(data):
    """
    Convert XML string to XML entities

    @type  data: str
    @param data: XML String
    @rtype: str
    @return: XML string converted
    """
    data = data.replace('&', '&amp;')
    data = data.replace('<', '&lt;')
    data = data.replace('>', '&gt;')
    data = data.replace('"', '&quot;')
    data = data.replace("'", "&apos;")
    return data


def parameter(dico, resource, special=None):
    """
    Convert value to a parameter for SOAP query

    @type  dico: dict
    @param dico: Contain parameter starts with OERP_
    @type  resource: dict
    @param resource: Contain parameter starts with WIZARD_
    @rtype: xmlstring
    @return: XML String representation
    """
    res = ''
    for key in resource:
        _logger.debug(' PARAMETER -> RESOURCE: %s' % key)
        if key in 'xml_data':
            continue
        e = Element('parameter')
        e.set('name', 'OERP_%s' % key.upper())
        e.text = ustr(resource[key])
        res += tostring(e) + '\n'

    for key in dico:
        _logger.debug(' PARAMETER -> DICO: %s' % key)
        if key in 'params':
            continue
        val = dico[key]
        e = Element('parameter')
        e.set('name', 'WIZARD_%s' % key.upper())
        if isinstance(val, list):
            if isinstance(val[0], tuple):
                e.text = ','.join(map(str, val[0][2]))
            else:
                e.text = ','.join(map(str, val))
        else:
            e.text = val and ustr(val) or ''
        res += tostring(e) + '\n'

    if special is None:
        special = {}

    for key in special:
        _logger.debug(' PARAMETER -> SPECIAL: %s' % key)
        e = Element('parameter')
        e.set('name', key)
        e.text = ustr(special[key])
        res += tostring(e) + '\n'

    res = entities(res)
    if resource.get('xml_data'):
        res += '&lt;parameter class=&quot;java.lang.String&quot; name=&quot;XML_DATA&quot;&gt;'
        res += '&lt;![CDATA[&quot;%s&quot;]]&gt;&lt;/parameter&gt;' % resource['xml_data']
    return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
