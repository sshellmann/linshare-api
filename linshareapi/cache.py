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

class Cache(object):
    def __init__(self, cm, key):
        self.cm = cm
        self.key = key

    def __call__(self, original_func):
        def wrapper(*args, **kwargs):
            resourceapi = args[0]
            cli = resourceapi.core
            nocache = cli.nocache
            if nocache:
                cli.log.debug("cache disabled.")
                return original_func(*args, **kwargs)
            key = hashlib.sha256(self.key + "|" + cli.user).hexdigest()
            cli.log.debug("key: " + key)
            if self.cm.has_key(key):
                res = self.cm.get(key)
            else:
                res = original_func(*args, **kwargs)
                self.cm.put(key, res)
            return res
        return wrapper


class Invalid(object):
    def __init__(self, cm, keys):
        self.cm = cm
        self.keys = keys
        if not isinstance(keys, list):
            self.keys = list(keys)

    def __call__(self, original_func):
        def wrapper(*args, **kwargs):
            resourceapi = args[0]
            cli = resourceapi.core
            for k in self.keys:
                key = hashlib.sha256(k + "|" + cli.user).hexdigest()
                cli.log.debug("key: " + key)
                self.cm.evict(key)
            return original_func(*args, **kwargs)
        return wrapper


class CacheManager(object):
    def __init__(self, cachedir="~/.linshare-cache", logger_name="linshareapi.cachemanager"):
        self.cachedir = os.path.expanduser(cachedir)
        if not os.path.isdir(self.cachedir):
            os.makedirs(self.cachedir)
        self.log = logging.getLogger(logger_name)
        self.urls = OrderedDict()
        self.cache_time = 60

    def _get_cachefile(self, key):
        return self.cachedir + "/" + key

    def _has_key(self, key):
        cachefile = self._get_cachefile(key)
        if os.path.isfile(cachefile):
            return True
        return False

    def has_key(self, key):
        if self._has_key(key):
            cachefile = self._get_cachefile(key)
            file_time = os.stat(cachefile).st_mtime
            form = "{da:%Y-%m-%d %H:%M:%S}"
            self.log.debug("cached data : " + str(
                form.format(da=datetime.datetime.fromtimestamp(file_time))))
            if time.time() - self.cache_time < file_time:
                return True
        return False

    def evict(self, key):
        if self._has_key(key):
            cachefile = self._get_cachefile(key)
            self.log.debug("cached data eviction : %s", key)
            os.remove(cachefile)
            return True
        return False

    def get(self, key):
        res = None
        self.log.debug("loading cached data : %s", key)
        cachefile = self._get_cachefile(key)
        with open(cachefile, 'rb') as fde:
            res = json.load(fde)
        return res

    def put(self, key, data):
        self.log.debug("caching data : %s", key)
        cachefile = self._get_cachefile(key)
        cachefile = self._get_cachefile(key)
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
