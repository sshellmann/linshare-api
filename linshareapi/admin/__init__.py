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

from linshareapi.core import CoreCli
from linshareapi.core import ApiNotImplementedYet as ANIY
from linshareapi.admin.domains import Domains
from linshareapi.admin.domains import Domains2
from linshareapi.admin.domainpatterns import DomainPatterns
from linshareapi.admin.domainpatterns import DomainPatterns2
from linshareapi.admin.functionalities import Functionalities
from linshareapi.admin.threads import  Threads
from linshareapi.admin.threadmembers import ThreadsMembers
from linshareapi.admin.users import Users
from linshareapi.admin.iusers import InconsistentUsers
from linshareapi.admin.ldapconnections import LdapConnections
from linshareapi.admin.ldapconnections import LdapConnections2
from linshareapi.admin.domainpolicies import DomainPolicies


# -----------------------------------------------------------------------------
class AdminCli(CoreCli):
    # pylint: disable=R0902

    VERSION = 1
    VERSIONS = [0, 1]

    def __init__(self, host, user, password, verbose, debug, api_version=None):
        super(AdminCli, self).__init__(host, user, password, verbose, debug)
        if api_version is None:
            api_version = self.VERSION
        if api_version not in self.VERSIONS:
            raise ValueError("API version not supported : " + str(api_version))
        self.base_url = "linshare/webservice/rest/admin"
        # Default API
        self.threads = ANIY(self, api_version, "threads")
        self.thread_members = ANIY(self, api_version, "thread_members")
        self.users = ANIY(self, api_version, "users")
        self.iusers = ANIY(self, api_version, "iusers")
        self.domains = ANIY(self, api_version, "domains")
        self.ldap_connections = ANIY(self, api_version, "ldap_connections")
        self.domain_patterns = ANIY(self, api_version, "domain_patterns")
        self.funcs = ANIY(self, api_version, "funcs")
        self.domain_policies = ANIY(self, api_version, "domain_policies")
        # API declarations
        if api_version == 0:
            self.threads = Threads(self)
            self.thread_members = ThreadsMembers(self)
            self.users = Users(self)
            self.iusers = InconsistentUsers(self)
            self.domains = Domains(self)
            self.ldap_connections = LdapConnections(self)
            self.domain_patterns = DomainPatterns(self)
            self.funcs = Functionalities(self)
            self.domain_policies = DomainPolicies(self)
        elif api_version == 1:
            self.threads = Threads(self)
            self.thread_members = ThreadsMembers(self)
            self.users = Users(self)
            self.iusers = InconsistentUsers(self)
            self.domains = Domains2(self)
            self.ldap_connections = LdapConnections2(self)
            self.domain_patterns = DomainPatterns2(self)
            self.funcs = Functionalities(self)
            self.domain_policies = DomainPolicies(self)
        self.init_handlers()
