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

import os
import re
import sys
import pickle
import hashlib
import logging
import logging.handlers
import base64
import urllib2
import cookielib
import json
import poster
import datetime
from ordereddict import OrderedDict
from progressbar import ProgressBar, FileTransferSpeed, Bar, ETA, Percentage

# pylint: disable=C0111
# Missing docstring
# -----------------------------------------------------------------------------
class LinShareException(Exception):
    pass

#    def __init__(self, code, msg, *args, **kwargs):
#        super(LinShareException, self).__init__(*args, **kwargs)
#        self.code = code
#        self.msg = msg

# -----------------------------------------------------------------------------
def extract_file_name(content_dispo):
    """Extract file name from the input request body"""
    #print type(content_dispo)
    #print repr(content_dispo)
    # convertion of escape string (str type) from server
    # to unicode object
    content_dispo = content_dispo.decode('unicode-escape').strip('"')
    file_name = ""
    for key_val in content_dispo.split(';'):
        param = key_val.strip().split('=')
        if param[0] == "filename":
            file_name = param[1].strip('"')
            break
    return file_name


class FileWithCallback(file):
    def __init__(self, path, mode, callback, size=None, *args):
        file.__init__(self, path, mode)
        if size:
            self._total = size
        else:
            self.seek(0, os.SEEK_END)
            self._total = self.tell()
        self.seek(0)
        self._callback = callback
        self._args = args
        self._seen = 0.0

    def __len__(self):
        return self._total

    def read(self, size):
        data = file.read(self, size)
        self._seen += size
        if self._seen > self._total:
            self._callback(self._total)
        else:
            self._callback(self._seen)
        return data

    def write(self, data):
        if data:
            self._seen += len(data)
        if self._seen > self._total:
            self._callback(self._total)
        else:
            self._callback(self._seen)
        data = file.write(self, data)


# -----------------------------------------------------------------------------
class ApiNotImplementedYet(object):

    def __init__(self, corecli, version, end_point):
        self.core = corecli
        self.end_point = end_point
        self.version = version

    def __getattr__(self, name):
        raise NotImplementedError(
            "The current end point '%(api)s' is not supported in the api \
version '%(version)s'." % {
                'api': self.end_point,
                'version': self.version})


# -----------------------------------------------------------------------------
class CoreCli(object):

    def __init__(self, host, user, verbose=False, debug=0):
        classname = str(self.__class__.__name__.lower())
        self.log = logging.getLogger('linshareapi.' + classname)
        self.verbose = verbose
        self.debug = debug
        self.password = None
        self.host = host
        self.user = user
        self.realm = "Name Of Your LinShare Realm"
        self.last_req_time = None
        self.cache_time = 60
        self.nocache = False
        self.base_url = ""
        # 0 : debug off
        # 1 : debug on
        # 2 : debug on, request result is printed (pretty json)
        # 3 : debug on, urllib debug on,  http headers and request are printed
        self.debuglevel = 0
        self.root_url = None
        self.cookiejar = cookielib.CookieJar()

    def _init_root_url(self):
        if not self.host:
            raise ValueError("invalid host : host url is not set !")
        self.root_url = self.host
        if self.root_url[-1] != "/":
            self.root_url += "/"
        self.root_url += self.base_url
        if self.root_url[-1] != "/":
            self.root_url += "/"
        self.log.debug("root_url : " + self.root_url)

    def _init_handlers(self, auth_handler=None):
        httpdebug = 0
        if self.debuglevel >= 3:
            httpdebug = 1
        # We declare all the handlers useful here.
        # we convert unicode objects to utf8 strings because
        # the authentication module does not handle unicode
        if not auth_handler:
            auth_handler = urllib2.HTTPBasicAuthHandler()
        try:
            auth_handler.add_password(
                realm=self.realm.encode('utf8'),
                uri=self.root_url.encode('utf8'),
                user=self.user.encode('utf8'),
                passwd=self.password.encode('utf8'))
        except UnicodeEncodeError:
            self.log.error(
                "the program was not able to compute "
                + "the basic authentication token.")
        handlers = [
            poster.streaminghttp.StreamingHTTPSHandler(debuglevel=httpdebug),
            auth_handler,
            urllib2.HTTPSHandler(debuglevel=httpdebug),
            urllib2.HTTPHandler(debuglevel=httpdebug),
            poster.streaminghttp.StreamingHTTPHandler(
                debuglevel=httpdebug),
            poster.streaminghttp.StreamingHTTPRedirectHandler(),
            urllib2.HTTPCookieProcessor(self.cookiejar)]
        # Setting handlers
        # pylint: disable=star-args
        urllib2.install_opener(urllib2.build_opener(*handlers))

    def init_cli(self, auth_handler=None):
        self._init_root_url()
        if not self.user:
            raise ValueError("invalid user : " + str(self.user))
        if not self.password:
            raise ValueError("invalid password : password is not set ! ")
        if not self.realm:
            self.realm = "Name Of Your LinShare Realm"
        if self.debug:
            try:
                self.debuglevel = int(self.debug)
            except ValueError:
                self.debuglevel = 1
        self._init_handlers(auth_handler)

    def get_full_url(self, url_frament):
        root_url = self.host
        if root_url[-1] != "/":
            root_url += "/"
        root_url += self.base_url
        if root_url[-1] != "/":
            root_url += "/"
        root_url += url_frament
        return root_url

    def get_cookie_filename(self):
        hash_key = hashlib.sha256()
        hash_key.update(self.root_url)
        hash_key.update(self.user)
        hash_key = hash_key.hexdigest()
        self.log.debug("cookie_filename: " + hash_key)
        return hash_key

    def auth(self, save_cookie=False):
        url = self.get_full_url("authentication/authorized")
        self.log.debug("list url : " + url)
        # Building request
        request = urllib2.Request(url)
        request.add_header('Content-Type', 'application/json; charset=UTF-8')
        request.add_header('Accept', 'application/json')
        # doRequest
        try:
            resultq = urllib2.urlopen(request)
            code = resultq.getcode()
            if code == 200:
                self.log.debug("auth url : ok")
                if save_cookie:
                    directory = os.path.expanduser('~/.linshare-cookies')
                    if not os.path.isdir(directory):
                        os.makedirs(directory)
                    self.cookiejar.save(os.path.join(
                        directory,
                        self.get_cookie_filename())
                    )
        except urllib2.HTTPError as ex:
            msg = ex.msg.decode('unicode-escape').strip('"')
            if ex.code == 401:
                self.log.error(msg + " (" + str(ex.code) + ")")
            else:
                self.log.error(msg + " (" + str(ex.code) + ")")
        return False

    def add_auth_header(self, request):
        base64string = base64.encodestring('%s:%s' % (
            self.user, self.password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
        #request.add_header("Cookie", "JSESSIONID=")

    def get_json_result(self, resultq):
        json_obj = None
        result = resultq.read()
        content_type = resultq.headers.getheader('Content-Type')
        if content_type == "application/json":
            json_obj = json.loads(result)
            if self.debuglevel >= 2:
                self.log.debug("the result is : ")
                self.log.debug(json.dumps(json_obj, sort_keys=True, indent=2))
        else:
            self.log.debug(str(result))
            msg = "Wrong content type in the http response : "
            if content_type:
                msg += content_type
            self.log.error(msg)
            raise ValueError(msg)
        return json_obj

    def do_request(self, request, force_nocontent=False):
        # request start
        self.last_req_time = None
        json_obj = None
        starttime = datetime.datetime.now()
        try:
            # doRequest
            resultq = urllib2.urlopen(request)
            code = resultq.getcode()
            self.log.debug("http return code : " + str(code))
            if code == 200:
                if force_nocontent:
                    json_obj = resultq
                else:
                    json_obj = self.get_json_result(resultq)
            if code == 204:
                json_obj = True
        except urllib2.HTTPError as ex:
            code = "-1"
            if self.debug >= 3:
                print "---------- exception -----------"
                sys.stderr.write(str(type(ex)))
                sys.stderr.write("\n")
                sys.stderr.write(str(dir(ex)))
                sys.stderr.write("\n")
                sys.stderr.write(str(ex.headers))
                sys.stderr.write("\n")
                sys.stderr.write(str(type(ex.msg)))
                sys.stderr.write("\n")
                sys.stderr.write(str(ex))
                sys.stderr.write("\n")
                sys.stderr.write(ex.msg.decode('unicode-escape').strip('"'))
                sys.stderr.write("\n")
                sys.stderr.write("\n")
                print "--------------------------------"
            msg = ex.msg.decode('unicode-escape').strip('"')
            msg = "Http error : " + msg + " (" + str(ex.code) + ")"
            if self.verbose:
                self.log.info(msg)
            else:
                self.log.debug(msg)
            if ex.code == 400 or ex.code == 403 or ex.code == 404:
                json_obj = self.get_json_result(ex)
                code = json_obj.get('errCode')
                msg = json_obj.get('message')
                self.log.debug("Server error code : " + str(code))
                self.log.debug("Server error message : " + str(msg))
            else:
                if self.debug >= 3:
                    sys.stderr.write("payload : " + ex.read())
                    sys.stderr.write("\n")
            # request end
            endtime = datetime.datetime.now()
            self.last_req_time = str(endtime - starttime)
            raise LinShareException(code, msg)
        # request end
        endtime = datetime.datetime.now()
        self.last_req_time = str(endtime - starttime)
        return json_obj

    def list(self, url):
        """ List ressources store into LinShare."""
        url = self.get_full_url(url)
        self.log.debug("list url : " + url)
        # Building request
        request = urllib2.Request(url)
        request.add_header('Content-Type', 'application/json; charset=UTF-8')
        request.add_header('Accept', 'application/json')
        # Do request
        ret = self.do_request(request)
        self.log.debug("""list url : %(url)s : request time : %(time)s""",
                       {"url": url,
                        "time": self.last_req_time})
        return ret

    def get(self, url):
        """ List ressources store into LinShare."""
        url = self.get_full_url(url)
        self.log.debug("get url : " + url)
        # Building request
        request = urllib2.Request(url)
        request.add_header('Content-Type', 'application/json; charset=UTF-8')
        request.add_header('Accept', 'application/json')
        # Do request
        ret = self.do_request(request)
        self.log.debug("""get url : %(url)s : request time : %(time)s""",
                       {"url": url,
                        "time": self.last_req_time})
        return ret

    def delete(self, url, data=None):
        """Delete one ressource store into LinShare."""
        url = self.get_full_url(url)
        self.log.debug("delete url : " + url)
        # Building request
        request = urllib2.Request(url)
        request.add_header('Accept', 'application/json')
        if data:
            # Building request
            post_data = json.dumps(data).encode("UTF-8")
            request = urllib2.Request(url, post_data)
            request.add_header('Accept', 'application/json')
            request.add_header('Content-Type',
                               'application/json; charset=UTF-8')
        request.get_method = lambda: 'DELETE'
        ret = self.do_request(request)
        self.log.debug("""delete url : %(url)s : request time : %(time)s""",
                       {"url": url,
                        "time": self.last_req_time})
        return ret

    def options(self, url):
        url = self.get_full_url(url)
        self.log.debug("options url : " + url)
        # Building request
        request = urllib2.Request(url)
        request.add_header('Content-Type', 'application/json; charset=UTF-8')
        request.add_header('Accept', 'application/json')
        request.get_method = lambda: 'OPTIONS'
        # Do request
        ret = self.do_request(request)
        self.log.debug("""options url : %(url)s : request time : %(time)s""",
                       {"url": url,
                        "time": self.last_req_time})
        return ret

    def head(self, url, **kwargs):
        url = self.get_full_url(url)
        self.log.debug("head url : " + url)
        # Building request
        request = urllib2.Request(url)
        request.add_header('Content-Type', 'application/json; charset=UTF-8')
        request.add_header('Accept', 'application/json')
        request.get_method = lambda: 'HEAD'
        # Do request
        ret = self.do_request(request, **kwargs)
        self.log.debug("""head url : %(url)s : request time : %(time)s""",
                       {"url": url,
                        "time": self.last_req_time})
        return ret

    def create(self, url, data):
        """ create ressources store into LinShare."""
        url = self.get_full_url(url)
        self.log.debug("create url : " + url)
        # Building request
        post_data = json.dumps(data)
        post_data = post_data.encode("UTF-8")
        request = urllib2.Request(url, post_data)
        request.add_header('Content-Type', 'application/json; charset=UTF-8')
        request.add_header('Accept', 'application/json')
        # Do request
        ret = self.do_request(request)
        self.log.debug("""post url : %(url)s : request time : %(time)s""",
                       {"url": url,
                        "time": self.last_req_time})
        return ret

    def update(self, url, data):
        """ update ressources store into LinShare."""
        url = self.get_full_url(url)
        self.log.debug("update url : " + url)
        # Building request
        post_data = json.dumps(data).encode("UTF-8")
        request = urllib2.Request(url, post_data)
        request.add_header('Content-Type', 'application/json; charset=UTF-8')
        request.add_header('Accept', 'application/json')
        request.get_method = lambda: 'PUT'
        # Do request
        ret = self.do_request(request)
        self.log.debug("""put url : %(url)s : request time : %(time)s""",
                       {"url": url,
                        "time": self.last_req_time})
        return ret

    def upload(self, file_path, url, description=None, file_name=None,
               progress_bar=True):
        self.last_req_time = None
        url = self.get_full_url(url)
        self.log.debug("upload url : " + url)
        # Generating datas and headers
        file_size = os.path.getsize(file_path)
        self.log.debug("file_path is : " + file_path)
        if not file_name:
            file_name = os.path.basename(file_path)
        self.log.debug("file_name is : " + file_name)
        if file_size <= 0:
            msg = u"The file '%(filename)s' can not be uploaded  because its size is less or equal to zero." % {"filename": file_name}
            raise LinShareException("-1", msg)
        pbar = None
        stream = file(file_path, 'rb')
        if progress_bar:
            widgets = [FileTransferSpeed(), ' <<<', Bar(), '>>> ',
                       Percentage(), ' ', ETA()]
            pbar = ProgressBar(widgets=widgets, maxval=file_size)
            stream = FileWithCallback(file_path, 'rb', pbar.update,
                                      file_size, file_path)
        post = poster.encode.MultipartParam("file", filename=file_name,
                                            fileobj=stream)
        params = [post,]
        if description:
            params.append(("description", description))
        datagen, headers = poster.encode.multipart_encode(params)
        # Building request
        request = urllib2.Request(url, datagen, headers)
        request.add_header('Accept', 'application/json')
        # request start
        if pbar:
            pbar.start()
        starttime = datetime.datetime.now()
        resultq = None
        try:
            # doRequest
            resultq = urllib2.urlopen(request)
            code = resultq.getcode()
            self.log.debug("http return code : " + str(code))
            if code == 200:
                json_obj = self.get_json_result(resultq)
        except urllib2.HTTPError as ex:
            msg = ex.msg.decode('unicode-escape').strip('"')
            if self.verbose:
                self.log.info(
                    "Http error : " + msg + " (" + str(ex.code) + ")")
            else:
                self.log.debug(
                    "Http error : " + msg + " (" + str(ex.code) + ")")
            json_obj = self.get_json_result(ex)
            code = json_obj.get('errCode')
            msg = json_obj.get('message')
            self.log.debug("Server error code : " + str(code))
            self.log.debug("Server error message : " + str(msg))
            # request end
            endtime = datetime.datetime.now()
            if pbar:
                pbar.finish()
            self.last_req_time = str(endtime - starttime)
            if ex.code == 502:
                self.log.warn(
                    """The file '%(filename)s' was uploaded
                    (%(time)ss) but the proxy cut the connexion. No server
                    acknowledge was received.""",
                    {"filename": file_name,
                     "time": self.last_req_time})
            else:
                self.log.debug(
                    "Can not upload file %(filename)s (%(filepath)s)",
                    {"filename": file_name,
                     "filepath": file_path})
            raise LinShareException(code, msg)
        # request end
        endtime = datetime.datetime.now()
        if pbar:
            pbar.finish()
        self.last_req_time = str(endtime - starttime)
        self.log.debug("upload url : %(url)s : request time : %(time)s",
                       {"url": url,
                        "time": self.last_req_time})
        return json_obj

    def download(self, uuid, url, forced_file_name=None,
                 progress_bar=True, chunk_size=256,
                 directory=None, overwrite=False):
        """ download a file from LinShare using its rest api.
        This method could throw exceptions like urllib2.HTTPError."""
        self.last_req_time = None
        url = self.get_full_url(url)
        self.log.debug("download url : " + url)
        # Building request
        request = urllib2.Request(url)
        #request.add_header('Content-Type', 'application/json; charset=UTF-8')
        #request.add_header('Accept', 'application/json;charset=UTF-8')
        request.add_header('Accept', '*/*; charset=UTF-8')
        # request start
        starttime = datetime.datetime.now()
        # doRequest
        resultq = urllib2.urlopen(request)
        code = resultq.getcode()
        file_name = uuid
        self.log.debug("ret code : '" + str(code) + "'")
        if code == 200:
            content_lenth = resultq.info().getheader('Content-Length')
            if not content_lenth:
                msg = "No content lengh header found !"
                self.log.debug(msg)
                progress_bar = False
            else:
                file_size = int(content_lenth.strip())
            if forced_file_name:
                file_name = forced_file_name
            else:
                content_dispo = resultq.info().getheader('Content-disposition')
                if content_dispo:
                    content_dispo = content_dispo.strip()
                    file_name = extract_file_name(content_dispo)
            if directory:
                if os.path.isdir(directory):
                    file_name = directory + "/" + file_name
            if os.path.isfile(file_name):
                if not overwrite:
                    cpt = 1
                    while 1:
                        if not os.path.isfile(file_name + "." + str(cpt)):
                            file_name += "." + str(cpt)
                            break
                        cpt += 1
                else:
                    self.log.warn("'%s' already exists. It was overwriten.", file_name)
            stream = None
            pbar = None
            if progress_bar:
                widgets = [FileTransferSpeed(), ' <<<', Bar(), '>>> ',
                           Percentage(), ' ', ETA()]
                pbar = ProgressBar(widgets=widgets, maxval=file_size)
                stream = FileWithCallback(file_name, 'w', pbar.update,
                                          file_size, file_name)
                pbar.start()
            else:
                stream = file(file_name, 'w')
            while 1:
                chunk = resultq.read(chunk_size)
                if not chunk:
                    break
                stream.write(chunk)
            stream.flush()
            stream.close()
            if pbar:
                pbar.finish()
        # request end
        endtime = datetime.datetime.now()
        self.last_req_time = str(endtime - starttime)
        self.log.debug("download url : %(url)s : request time : %(time)s",
                       {"url": url,
                        "time": self.last_req_time})
        return (file_name, self.last_req_time)


class ResourceBuilder(object):

    def __init__(self, name=None, required=False):
        self._name = name
        self._fields = OrderedDict()
        self._required = required

    def add_field(self, field, arg=None, value=None, extended=False,
                  hidden=False, e_type=str, required=None):
        if required is None:
            required = self._required
        if arg is None:
            arg = re.sub('(?!^)([A-Z]+)', r'_\1', field).lower()
        self._fields[field] = {
            'field': field,
            'arg': arg,
            'value': value,
            'extended': extended,
            'required': required,
            'e_type': e_type,
            'hidden': hidden
        }

    def get_keys(self, extended=False):
        res = []
        for field in self._fields.values():
            if field['hidden']:
                continue
            if not field['extended']:
                res.append(field['field'])
            if extended and field['extended']:
                res.append(field['field'])
        return res

    def get_fields(self, extended=False, full=False):
        res = []
        if extended:
            for field in self._fields.values():
                if field['extended']:
                    res.append(field['field'])
        elif full:
            for field in self._fields.keys():
                res.append(field)
        else:
            for field in self._fields.values():
                if not field['extended']:
                    res.append(field['field'])
        return res

    def set_arg(self, key, arg):
        field = self._fields.get(key, None)
        if field is not None:
            field['arg'] = arg

    def set_value(self, key, value):
        field = self._fields.get(key, None)
        if field is not None:
            field['value'] = value

    def to_resource(self):
        ret = {}
        for field in self._fields.values():
            ret[field['field']] = field['value']
        return ret

    def load_from_args(self, namespace):
        for field in self._fields.values():
            value = getattr(namespace, field['arg'], None)
            if value is not None:
                field['value'] = value

    def copy(self, data):
        if isinstance(data, dict):
            for field, val in self._fields.items():
                val['value'] = data.get(field, "")

        if isinstance(data, ResourceBuilder):
            for field, val in self._fields.items():
                val['value'] = data[field]['value']

    def __str__(self):
        return json.dumps(self.to_resource(), sort_keys=True, indent=2)

    def check_required_fields(self):
        for field in self._fields.values():
            if field['required']:
                value = field['value']
                if value is None:
                    raise ValueError("missing value for required field : "
                                     + field['field'])
                e_type = field['e_type']
                if e_type == int:
                    int(value)
                if e_type == float:
                    float(value)
