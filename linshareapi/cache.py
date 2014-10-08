#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import os
import time
import json
import logging
import datetime
import hashlib
from ordereddict import OrderedDict

class _Cache(object):

    def compute_key(self, cli, familly, discriminant=None):
        hash_key = hashlib.sha256()
        hash_key.update(familly)
        hash_key.update(cli.host)
        hash_key.update(cli.user)
        hash_key.update(cli.password)
        if discriminant:
            hash_key.update(discriminant)
        hash_key = hash_key.hexdigest()
        cli.log.debug("hash_key: " + hash_key)
        return hash_key

class Cache(_Cache):

    def __init__(self, cm, familly, discriminant=None):
        self.cm = cm
        self.familly = familly
        self.discriminant = discriminant

    def __call__(self, original_func):
        def wrapper(*args, **kwargs):
            resourceapi = args[0]
            cli = resourceapi.core
            nocache = cli.nocache
            if nocache:
                cli.log.debug("cache disabled.")
                return original_func(*args, **kwargs)
            hash_key = self.compute_key(cli, self.familly, self.discriminant)
            if self.cm.has_key(hash_key, self.familly):
                res = self.cm.get(hash_key, self.familly)
            else:
                res = original_func(*args, **kwargs)
                self.cm.put(hash_key, res, self.familly)
            return res
        return wrapper


class InvalidFamilies(_Cache):
    def __init__(self, cm, familly):
        self.cm = cm
        self.famillies = familly
        if not isinstance(familly, list):
            self.famillies = [familly,]

    def __call__(self, original_func):
        def wrapper(*args, **kwargs):
            for familly in self.famillies:
                self.cm.evict(group=familly)
            return original_func(*args, **kwargs)
        return wrapper

class Invalid(_Cache):
    def __init__(self, cm, familly, discriminant=None):
        self.cm = cm
        self.familly = familly
        self.discriminant = discriminant

    def __call__(self, original_func):
        def wrapper(*args, **kwargs):
            resourceapi = args[0]
            cli = resourceapi.core
            hash_key = self.compute_key(cli, self.familly, self.discriminant)
            self.cm.evict(hash_key, self.familly)
            return original_func(*args, **kwargs)
        return wrapper


class CacheManager(object):
    def __init__(self, cachedir="~/.linshare-cache", logger_name="linshareapi.cachemanager"):
        self.rootcachedir = os.path.expanduser(cachedir)
        if not os.path.isdir(self.rootcachedir):
            os.makedirs(self.rootcachedir)
        self.log = logging.getLogger(logger_name)
        self.urls = OrderedDict()
        self.cache_time = 60

    def _get_cachedir(self, group=None):
        res = [self.rootcachedir,]
        if group:
            res.append(group)
        res = "/".join(res)
        if not os.path.isdir(res):
            os.makedirs(res)
        return res

    def _get_cachefile(self, key, group=None):
        return self._get_cachedir(group) + "/" + key

    def _has_key(self, key, group=None):
        cachefile = self._get_cachefile(key, group)
        if os.path.isfile(cachefile):
            return True
        return False

    def has_key(self, key, group=None):
        if self._has_key(key, group):
            cachefile = self._get_cachefile(key, group)
            file_time = os.stat(cachefile).st_mtime
            form = "{da:%Y-%m-%d %H:%M:%S}"
            self.log.debug("cached data : " + str(
                form.format(da=datetime.datetime.fromtimestamp(file_time))))
            if time.time() - self.cache_time < file_time:
                return True
        return False

    def evict(self, key=None, group=None):
        if key is None:
            if group:
                cachedir = self._get_cachedir(group)
                for i in os.listdir(cachedir):
                    self.log.debug("cached data eviction : %s : %s", group, i)
                    os.remove(cachedir + "/" + i)
                return True
        else:
            if self._has_key(key, group):
                cachefile = self._get_cachefile(key, group)
                self.log.debug("cached data eviction : %s : %s", group, key)
                os.remove(cachefile)
                return True
        return False

    def get(self, key, group=None):
        res = None
        self.log.debug("loading cached data : %s : %s", group, key)
        cachefile = self._get_cachefile(key, group)
        with open(cachefile, 'rb') as fde:
            res = json.load(fde)
        return res

    def put(self, key, data, group=None):
        self.log.debug("caching data : %s : %s", group, key)
        cachefile = self._get_cachefile(key, group)
        with open(cachefile, 'wb') as fde:
            json.dump(data, fde)


class Time(object):
    def __init__(self, logger_name, return_time=False):
        self.log = logging.getLogger(logger_name)
        self.return_time = return_time

    def __call__(self, original_func):
        def time_wrapper(*args, **kwargs):
            start = time.time()
            res = original_func(*args, **kwargs)
            end = time.time()
            diff = end - start
            self.log.debug("function time : " + str(diff))
            if self.return_time:
                return (diff, res)
            else:
                return res
        return time_wrapper
