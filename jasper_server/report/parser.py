# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP,
#    Copyright (C) 2010-2011 SYLEAM Info Services (<http://www.syleam.fr/>)
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

from cStringIO import StringIO
from HTMLParser import HTMLParser
from lxml.etree import parse
from tempfile import mkstemp
from dime import Message
import os


class HTML2Text(HTMLParser):
    """
    Instance the HTML for decode the message
    return by the JasperServer
    """
    def __init__(self):
        HTMLParser.__init__(self)
        self.output = StringIO()
        self.is_valid = True
        self.is_linefeed = True
        self.is_title = True

    def get_text(self):
        return self.output.getvalue()

    def handle_data(self, data):
        if not self.is_valid:
            self.output.write(data)
        if self.is_linefeed:
            self.output.write('\n')
        elif self.is_title:
            self.output.write('\n')

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.is_valid = False
        elif tag == 'p':
            self.is_linefeed = False
        elif tag.startswith('h'):
            self.is_title = False

    def handle_endtag(self, tag):
        if tag == "body":
            self.is_valid = True
        elif tag == 'p':
            self.is_linefeed = True
        elif tag.startswith('h'):
            self.is_title = True


def ParseDIME(source, list_file):
    """
    We must decompose the dime record to return the PDF only
    """
    fp = StringIO(source)
    a = Message.load(fp)
    for x in a.records:
        if x.type.value == 'application/pdf':
            content = x.data
            # Store the PDF in TEMP directory
            fd, f_name = mkstemp(suffix='.pdf', prefix='jasper')
            list_file.append(f_name)
            fpdf = open(f_name, 'w+b')
            fpdf.write(content)
            fpdf.close()
            os.close(fd)


def ParseXML(source):
    """
    Read the JasperServer Error code
    and return the code and the message
    """
    fp = StringIO(source)
    tree = parse(fp)
    fp.close()
    r = tree.xpath('//runReportReturn')
    if not r:
        raise Exception('Error, invalid Jasper Message')
    fp = StringIO(r[0].text)
    tree = parse(fp)
    fp.close()
    return (tree.xpath('//returnCode')[0].text,
            tree.xpath('//returnMessage')[0].text)


def ParseHTML(source):
    """
    Read the HTML content return by an authentification error
    """
    p = HTML2Text()
    p.feed(source)
    return p.get_text()


def ParseContent(source):
    """
    Parse the content and return a decode stream

    """
    fp = StringIO(source)
    a = Message.load(fp)
    content = ''
    for x in a.records:
        if x.type.value == 'application/pdf':
            content = x.data
    return content


def WriteContent(content, list_file):
    """
    Write content in tempory file
    """
    __, f_name = mkstemp(suffix='.pdf', prefix='jasper')
    list_file.append(f_name)
    fpdf = open(f_name, 'w+b')
    fpdf.write(content)
    fpdf.close()

if __name__ == '__main__':
    print ParseHTML("""<html><head><title>Apache Tomcat/5.5.20 - Rapport d'erreur</title>
<style><!--H1 {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:22px;}
           H2 {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:16px;}
           H3 {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:14px;}
           BODY {font-family:Tahoma,Arial,sans-serif;color:black;background-color:white;}
           B {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;}
           P {font-family:Tahoma,Arial,sans-serif;background:white;color:black;font-size:12px;}
           A {color : black;}A.name {color : black;}HR {color : #525D76;}--></style>
</head><body>
<h1>Etat HTTP 401 - Bad credentials</h1>
<HR size="1" noshade="noshade"><p><b>type</b> Rapport d'état</p>
<p><b>message</b> <u>Bad credentials</u></p><p><b>description</b>
<u>La requête nécessite une authentification HTTP (Bad credentials).</u></p>
<HR size="1" noshade="noshade"><h3>Apache Tomcat/5.5.20</h3>
</body></html>""")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
