#!/usr/bin/python
# encoding=UTF-8

# Copyright © 2007, 2008, 2009 Jakub Wilk <ubanus@users.sf.net>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License, version 2, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
# for more details.


'''Parse and generate DIME messages.

DIME specification: <http://xml.coverpages.org/draft-nielsen-dime-02.txt>.
'''

__author__ = 'Jakub Wilk <ubanus@users.sf.net>'
__version__ = '0.2'
__all__ = \
[
    'Message',
    'Record',
    'Type',
    'NoneType',
    'MediaType',
    'TypeByUri',
    'UnchangedType',
    'UnknownType',
    'UnsupportedType',
]

SOAP_NS = 'http://schemas.xmlsoap.org/soap/envelope/'

import struct as _struct

def _typecheck_str(value, bits):
    if not isinstance(value, str):
        raise TypeError()
    if len(value) > (1 << bits):
        raise ValueError()

def _typecheck_int(value, bits):
    if not isinstance(value, int):
        raise TypeError()
    if not (0 <= value < (1 << bits)):
        raise ValueError()

def _typecheck(value, klass):
    if not isinstance(value, klass):
        raise ValueError()

class Type(object):

    '''Please don't subclass Type, unless you know what you're doing.
    Please don't isntantiate Type. Instead, use one of its subclasses.'''

    def __init__(self, value = ''):
        if self.__class__ == Type:
            raise TypeError(
                '''Please use one of the Type's subclasses: %s.''' %
                ', '.join(klass.__name__ for klass in Type.__subclasses__())
            )
        _typecheck_str(value, 16)
        try:
            if self.require_empty_value and value != '':
                raise ValueError()
        except AttributeError:
            pass
        self.tnf = self._code
        self.value = value
    
    @staticmethod
    def load_string(tnf, value):
        _typecheck_int(tnf, 4)
        for klass in Type.__subclasses__():
            if klass._code == tnf:
                return klass(value)
        return UnsupportedType(tnf, value)
    
    def as_mime(self):
        from email.MIMEBase import MIMEBase
        return MIMEBase('application', 'octet-stream')

class UnchangedType(Type):

    '''This type must be used in all middle record chunks and terminating
    record chunks used in chunked payloads.
    It must not be used in any other record.'''

    _code = 0x00
    require_empty_value = True

    def __str__(self):
        return '<unchanged>'

class MediaType(Type):

    '''A type which is identified by a media type construct.'''

    _code = 0x01

    def __str__(self):
        return self.value

    def as_mime(self):
        from email.MIMEBase import MIMEBase
        maintype, subtype = self.value.split('/')
        return MIMEBase(maintype, subtype)

class TypeByUri(Type):
    
    '''A type which is identified by a URI construct.'''

    _code = 0x02

    def __str__(self):
        return self.value

    def as_mime(self):
        from email.MIMEBase import MIMEBase
        if self.value == SOAP_NS:
            return MIMEBase('text', 'xml')
        else:
            return Type.as_mime(self)

class UnknownType(Type):

    '''Indicate that type of the payload is unknown.'''

    _code = 0x03
    require_empty_value = True

    def __str__(self):
        return '<?>'

class NoneType(Type):

    '''Indicate that there is no type or payload associated with this record.'''

    _code = 0x04
    require_empty_value = True

    def __str__(self):
        return '<none>'

class UnsupportedType(Type):

    '''An unsupported type.'''

    _code = None

    def __init__(self, tnf, value):
        Type.__init__(self, value)
        self.tnf = tnf
    
    def __str__(self):
        return '<unsupported>'

def _write1(stream, value):
    stream.write(_struct.pack('>B', value))

def _write2(stream, value):
    stream.write(_struct.pack('>H', value))

def _write4(stream, value):
    stream.write(_struct.pack('>I', value))

def _write_padded(stream, value):
    stream.write(value)
    stream.write('\0' * (4 - len(value) & 3))
    
def _read1(stream):
    value, = _struct.unpack('>B', stream.read(1))
    return value

def _read2(stream):
    value, = _struct.unpack('>H', stream.read(2))
    return value

def _read4(stream):
    value, = _struct.unpack('>I', stream.read(4))
    return value

def _read_padded(stream, count):
    value = stream.read(count)
    stream.read(4 - count & 3)
    return value

DEFAULT_VERSION = 1
DEFAULT_TYPE = UnknownType()
SUPPORTED_VERSIONS = (1,)

class Record(object):

    class FaultyRecord(Exception):
        pass

    class UnsupportedVersion(Exception):
        pass

    def __init__(self, id = None, type = DEFAULT_TYPE, data = '', mb = 0, me = 0, cf = 0, version = DEFAULT_VERSION):
        if id is None:
            from uuid import uuid4
            id = 'uuid:%s' % uuid4()
        _typecheck_str(id, 16)
        _typecheck(type, Type)
        _typecheck(data, str)
        for v in mb, me, cf:
            _typecheck_int(v, 1)
        _typecheck_int(version, 5)
        self.data = data
        self.type = type
        self.version = version
        self.id = id
        self.mb = mb
        self.me = me
        self.cf = cf

    def __repr__(self):
        head = object.__repr__(self).split(' object ')[0]
        flags = ','.join(flag for flag in ('mb', 'me', 'cf') if getattr(self, flag))
        if flags == '':
            flags = 0
        return '%s with id=%s, type=%s, flags=%s>' % (head, repr(self.id), self.type, flags)

    def save(self, stream):
        dose = self.cf | self.me << 1 | self.mb << 2 | self.version << 3;
        _write1(stream, dose)
        dose = self.type.tnf << 4;
        _write1(stream, dose)
        options = '' # options are not supported
        for q in (options, self.id, self.type.value):
            _write2(stream, len(q))
        _write4(stream, len(self.data))
        for q in (options, self.id, self.type.value, self.data):
            _write_padded(stream, q)

    @staticmethod
    def load(stream):
        dose = _read1(stream)
        mb = bool(dose & 4)
        me = bool(dose & 2)
        cf = bool(dose & 1)
        version = dose >> 3
        if version not in SUPPORTED_VERSIONS:
            raise Record.UnsupportedVersion(version)
        dose = _read1(stream)
        if (dose & 15) != 0:
            raise Record.FaultyRecord()
        tnf = dose >> 4
        options_length = _read2(stream)
        id_length = _read2(stream)
        type_length = _read2(stream)
        data_length = _read4(stream)
        options = _read_padded(stream, options_length)
        del options # options are not supported
        id = _read_padded(stream, id_length)
        type = _read_padded(stream, type_length)
        data = _read_padded(stream, data_length)
        return Record(id, Type.load_string(tnf, type), data, mb, me, cf, version)
    
    @staticmethod
    def load_all(stream):
        while True:
            record = Record.load(stream)
            yield record
            if record.me:
                break

    def as_mime(self):
        from email.Encoders import encode_7or8bit as encode
        attachment = self.type.as_mime()
        attachment.set_payload(self.data)
        attachment['Content-Length'] = str(len(self.data))
        attachment['Content-Id'] = '<%s>' % self.id
        encode(attachment)
        return attachment

class Message(object):

    def __init__(self, records):
        self.records = list(records)
        self.dict = dict((record.id, record) for record in self.records)
    
    def __repr__(self):
        head = object.__repr__(self).split(' object ')[0]
        return '%s with records=%s>' % (head, self.records)

    @staticmethod
    def load(stream):
        return Message(records = Record.load_all(stream))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.records[key]
        else:
            return self.dict[key]

    def __iter__(self):
        return iter(self.records)

    def normalize(self):
        for record in self.records:
            record.mb = 0
            record.me = 0
        self.records[0].mb = 1
        self.records[-1].me = 1

    def save(self, stream):
        self.normalize()
        for record in self.records:
            record.save(stream)

    def as_mime(self):
        from email.MIMEMultipart import MIMEMultipart
        message = MIMEMultipart()
        message.preamble = 'This is a multi-part message in MIME format. It was automatically converted from a DIME message.\n'
        message.epilogue = ''
        for record in self.records:
            message.attach(record.as_mime())
        return message

# vim:ts=4 sw=4 et
