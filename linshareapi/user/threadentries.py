#! /usr/bin/env python
# -*- coding: utf-8 -*-


# This file is part of Linshare api.
#
# LinShare api is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# LinShare api is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with LinShare api.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2014 Frédéric MARTIN
#
# Contributors list :
#
#  Frédéric MARTIN frederic.martin.fma@gmail.com
#


from __future__ import unicode_literals

from linshareapi.core import ResourceBuilder
from linshareapi.cache import Cache as CCache
from linshareapi.cache import Invalid as IInvalid
from linshareapi.user.core import GenericClass
from linshareapi.user.core import Time as CTime
from linshareapi.user.core import CM


# pylint: disable=C0111
# Missing docstring
# pylint: disable=R0903
# Too few public methods
# -----------------------------------------------------------------------------
class Time(CTime):
    def __init__(self, suffix, **kwargs):
        super(Time, self).__init__('tdocuments.' + suffix, **kwargs)


# -----------------------------------------------------------------------------
class Cache(CCache):
    def __init__(self, **kwargs):
        super(Cache, self).__init__(CM, 'tdocuments', **kwargs)


# -----------------------------------------------------------------------------
class Invalid(IInvalid):
    def __init__(self, **kwargs):
        super(Invalid, self).__init__(CM, 'tdocuments', **kwargs)


# -----------------------------------------------------------------------------
class ThreadEntries(GenericClass):

    @Time('get')
    def get(self, thread_uuid, uuid):
        url = "threads/%s/entries/%s" % (thread_uuid, uuid)
        return self.core.get(url)

    @Time('list')
    @Cache()
    def list(self, thread_uuid):
        url = "threads/%s/entries" % thread_uuid
        return self.core.list(url)

    @Time('invalid')
    @Invalid()
    def invalid(self):
        """Invalid local cache"""
        return "invalid : ok"

    @Time('upload')
    @Invalid(whole_familly=True)
    def upload(self, thread_uuid, file_path, description=None):
        """ Upload a file to LinShare using its rest api.
        The uploaded document uuid will be returned"""
        url = "threads/%s/entries" % thread_uuid
        return self.core.upload(file_path, url, description)

    @Time('download')
    def download(self, thread_uuid, uuid, directory=None):
        if thread_uuid is None:
            raise ValueError("missing thread_uuid")
        if uuid is None:
            raise ValueError("missing uuid")
        url = "threads/%s/entries/%s/download" % (thread_uuid, uuid)
        return self.core.download(uuid, url, directory=directory)

    @Time('thumbnail')
    def thumbnail(self, thread_uuid, uuid, directory=None):
        if thread_uuid is None:
            raise ValueError("missing thread_uuid")
        if uuid is None:
            raise ValueError("missing uuid")
        url = "threads/%s/entries/%s/thumbnail" % (thread_uuid, uuid)
        return self.core.download(uuid, url, directory=directory)

    @Time('delete')
    @Invalid(whole_familly=True)
    def delete(self, thread_uuid, uuid):
        res = self.get(thread_uuid, uuid)
        url = "threads/%s/entries/%s" % (thread_uuid, uuid)
        self.core.delete(url)
        return res

    def get_rbu(self):
        rbu = ResourceBuilder("documents")
        rbu.add_field('name')
        rbu.add_field('size')
        rbu.add_field('uuid')
        rbu.add_field('creationDate')
        rbu.add_field('modificationDate')
        rbu.add_field('type', extended=True)
        rbu.add_field('expirationDate', extended=True)
        rbu.add_field('ciphered', extended=True)
        rbu.add_field('description', extended=True)
        rbu.add_field('sha256sum', extended=True)
        rbu.add_field('metaData', extended=True)
        return rbu


# -----------------------------------------------------------------------------
class WorkgroupContent(ThreadEntries):

    local_base_url = "work_groups"

    @Time('get')
    @Cache()
    def get(self, wg_uuid, uuid):
        """ Get one workgroup member."""
        url = "%(base)s/%(wg_uuid)s/nodes/%(uuid)s" % {
            'base': self.local_base_url,
            'wg_uuid': wg_uuid,
            'uuid': uuid
        }
        return self.core.get(url)

    @Time('list')
    @Cache()
    def list(self, wg_uuid):
        url = "%(base)s/%(wg_uuid)s/nodes" % {
            'base': self.local_base_url,
            'wg_uuid': wg_uuid
        }
        return self.core.list(url)

    @Time('upload')
    @Invalid(whole_familly=True)
    def upload(self, wg_uuid, file_path, description=None):
        """ Upload a file to LinShare using its rest api.
        The uploaded document uuid will be returned"""
        url = "%(base)s/%(wg_uuid)s/nodes" % {
            'base': self.local_base_url,
            'wg_uuid': wg_uuid
        }
        return self.core.upload(file_path, url, description)

    @Time('download')
    def download(self, wg_uuid, uuid, directory=None):
        if wg_uuid is None:
            raise ValueError("missing workgroup_uuid")
        if uuid is None:
            raise ValueError("missing uuid")
        url = "%(base)s/%(wg_uuid)s/nodes/%(uuid)s/download" % {
            'base': self.local_base_url,
            'wg_uuid': wg_uuid,
            'uuid': uuid
        }
        return self.core.download(uuid, url, directory=directory)

    @Time('thumbnail')
    def thumbnail(self, wg_uuid, uuid, directory=None):
        if wg_uuid is None:
            raise ValueError("missing workgroup_uuid")
        if uuid is None:
            raise ValueError("missing uuid")
        url = "%(base)s/%(wg_uuid)s/nodes/%(uuid)s/thumbnail" % {
            'base': self.local_base_url,
            'wg_uuid': wg_uuid,
            'uuid': uuid
        }
        return self.core.download(uuid, url, directory=directory)

    @Time('delete')
    @Invalid(whole_familly=True)
    def delete(self, wg_uuid, uuid):
        res = self.get(wg_uuid, uuid)
        url = "%(base)s/%(wg_uuid)s/nodes/%(uuid)s" % {
            'base': self.local_base_url,
            'wg_uuid': wg_uuid,
            'uuid': uuid
        }
        self.core.delete(url)
        return res

    def get_rbu(self):
        rbu = ResourceBuilder("documents")
        rbu.add_field('name', required=True)
        rbu.add_field('size')
        rbu.add_field('type', value="FOLDER")
        rbu.add_field('uuid')
        rbu.add_field('creationDate')
        rbu.add_field('uploadDate')
        rbu.add_field('modificationDate')
        rbu.add_field('parent')
        rbu.add_field('lastAuthor', extended=True)
        rbu.add_field('mimeType', extended=True)
        rbu.add_field('nodeType', extended=True)
        rbu.add_field('hasRevision', extended=True)
        rbu.add_field('hasThumbnail', extended=True)
        rbu.add_field('description', extended=True)
        rbu.add_field('sha256sum', extended=True)
        rbu.add_field('workGroup', extended=True)
        rbu.add_field('metaData', extended=True)
        return rbu

#            "lastAuthor": {
#                      "accountType": "INTERNAL",
#                      "mail": "user1@linshare.org",
#                      "name": "John Doe",
#                      "uuid": "eb84401d-1a60-4aaf-b843-3292a36da825"
#                    },


# -----------------------------------------------------------------------------
class WorkgroupFolders(WorkgroupContent):

    def get_rbu(self):
        print "pouet"
        rbu = ResourceBuilder("folders")
        rbu.add_field('uuid')
        rbu.add_field('name', required=True)
        rbu.add_field('type', value="FOLDER", required=True)
        rbu.add_field('nodeType', value="FOLDER", required=True)
        rbu.add_field('creationDate')
        rbu.add_field('modificationDate')
        rbu.add_field('parent')
        rbu.add_field('workGroup', arg="wg_uuid", extended=True, required=True)
        # rbu.add_field('lastAuthor', extended=True)
        rbu.add_field('description', extended=True)
        rbu.add_field('metaData', extended=True)
        return rbu

    @Time('create')
    @Invalid()
    def create(self, data):
        self.debug(data)
        self._check(data)
        wg_uuid = data.get('workGroup')
        print "fred"
        self.log.debug("wg_uuid : %s " % wg_uuid)
        url = "%(base)s/%(wg_uuid)s/nodes" % {
            'base': self.local_base_url,
            'wg_uuid': wg_uuid
        }
        return self.core.create(url, data)
