#!/usr/bin/python
# -*- coding: utf-8 -*-

# Authors:
#   Thomas Woerner <twoerner@redhat.com>
#
# Copyright (C) 2019  Red Hat
# see file 'COPYING' for use and warranty information
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os
import uuid
import tempfile
import shutil
import gssapi
from datetime import datetime
from ipalib import api
from ipalib.config import Env
from ipalib.constants import DEFAULT_CONFIG, LDAP_GENERALIZED_TIME_FORMAT
try:
    from ipalib.install.kinit import kinit_password, kinit_keytab
except ImportError:
    from ipapython.ipautil import kinit_password, kinit_keytab
from ipapython.ipautil import run
from ipaplatform.paths import paths
from ipalib.krb_utils import get_credentials_if_valid


def valid_creds(module, principal):
    """
    Get valid credintials matching the princial, try GSSAPI first
    """
    if "KRB5CCNAME" in os.environ:
        module.debug('KRB5CCNAME set to %s' %
                     os.environ.get('KRB5CCNAME', None))
        try:
            cred = gssapi.creds.Credentials()
        except gssapi.raw.misc.GSSError as e:
            module.fail_json(msg='Failed to find default ccache: %s' % e)
        else:
            module.debug("Using principal %s" % str(cred.name))
            return True

    elif "KRB5_CLIENT_KTNAME" in os.environ:
        keytab = os.environ.get('KRB5_CLIENT_KTNAME', None)
        module.debug('KRB5_CLIENT_KTNAME set to %s' % keytab)

        ccache_name = "MEMORY:%s" % str(uuid.uuid4())
        os.environ["KRB5CCNAME"] = ccache_name

        try:
            cred = kinit_keytab(principal, keytab, ccache_name)
        except gssapi.raw.misc.GSSError as e:
            module.fail_json(msg='Kerberos authentication failed : %s' % e)
        else:
            module.debug("Using principal %s" % str(cred.name))
            return True

    creds = get_credentials_if_valid()
    if creds and \
       creds.lifetime > 0 and \
       "%s@" % principal in creds.name.display_as(creds.name.name_type):
        return True
    return False


def temp_kinit(principal, password):
    """
    kinit with password using a temporary ccache
    """
    if not password:
        raise RuntimeError("The password is not set")
    if not principal:
        principal = "admin"

    ccache_dir = tempfile.mkdtemp(prefix='krbcc')
    ccache_name = os.path.join(ccache_dir, 'ccache')

    try:
        kinit_password(principal, password, ccache_name)
    except RuntimeError as e:
        raise RuntimeError("Kerberos authentication failed: {}".format(e))

    return ccache_dir, ccache_name


def temp_kdestroy(ccache_dir, ccache_name):
    """
    Destroy temporary ticket and remove temporary ccache
    """
    if ccache_name is not None:
        run([paths.KDESTROY, '-c', ccache_name], raiseonerr=False)
    if ccache_dir is not None:
        shutil.rmtree(ccache_dir, ignore_errors=True)


def api_connect():
    """
    Create environment, initialize api and connect to ldap2
    """
    env = Env()
    env._bootstrap()
    env._finalize_core(**dict(DEFAULT_CONFIG))

    api.bootstrap(context='server', debug=env.debug, log=None)
    api.finalize()
    api.Backend.ldap2.connect()


def api_command(module, command, name, args):
    """
    Call ipa.Command, use AnsibleModule.fail_json for error handling
    """
    try:
        return api.Command[command](name, **args)
    except Exception as e:
        module.fail_json(msg="%s: %s" % (command, e))


def execute_api_command(module, principal, password, command, name, args):
    """
    Get KRB ticket if not already there, initialize api, connect,
    execute command and destroy ticket again if it has been created also.
    """
    ccache_dir = None
    ccache_name = None
    try:
        if not valid_creds(module, principal):
            ccache_dir, ccache_name = temp_kinit(principal, password)
        api_connect()

        return api_command(module, command, name, args)
    except Exception as e:
        module.fail_json(msg=str(e))

    finally:
        temp_kdestroy(ccache_dir, ccache_name)


def date_format(value):
    accepted_date_formats = [
        LDAP_GENERALIZED_TIME_FORMAT,  # generalized time
        '%Y-%m-%dT%H:%M:%SZ',  # ISO 8601, second precision
        '%Y-%m-%dT%H:%MZ',     # ISO 8601, minute precision
        '%Y-%m-%dZ',           # ISO 8601, date only
        '%Y-%m-%d %H:%M:%SZ',  # non-ISO 8601, second precision
        '%Y-%m-%d %H:%MZ',     # non-ISO 8601, minute precision
    ]

    for date_format in accepted_date_formats:
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            pass
    raise ValueError("Invalid date '%s'" % value)


def compare_args_ipa(module, args, ipa):
    for key in args.keys():
        if key not in ipa:
            return False
        else:
            arg = args[key]
            ipa_arg = ipa[key]
            # If ipa_arg is a list and arg is not, replace arg
            # with list containing arg. Most args in a find result
            # are lists, but not all.
            if isinstance(ipa_arg, list) and not isinstance(arg, list):
                arg = [arg]
            # module.warn("%s <=> %s" % (arg, ipa_arg))
            if arg != ipa_arg:
                return False

    return True
