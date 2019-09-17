#!/usr/bin/python
# -*- coding: utf-8 -*-

# Authors:
#   Thomas Woerner <twoerner@redhat.com>
#
# Copyright (C) 2019 Red Hat
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

ANSIBLE_METADATA = {
    "metadata_version": "1.0",
    "supported_by": "community",
    "status": ["preview"],
}

DOCUMENTATION = """
---
module: ipagroup
short description: Manage FreeIPA groups
description: Manage FreeIPA groups
options:
  ipaadmin_principal:
    description: The admin principal
    default: admin
  ipaadmin_password:
    description: The admin password
    required: false
  name:
    description: The group name
    required: false
    aliases: ["cn"]
  description:
    description: The group description
    required: false
  gid:
    description: The GID
    required: false
    aliases: ["gidnumber"]
  nonposix:
    description: Create as a non-POSIX group
    required: false
    type: bool
  external:
    description: Allow adding external non-IPA members from trusted domains
    required: false
    type: bool
  nomembers:
    description: Suppress processing of membership attributes
    required: false
    type: bool
  user:
    description: List of user names assigned to this group.
    required: false
    type: list
  group:
    description: List of group names assigned to this group.
    required: false
    type: list
  service:
    description: List of service names assigned to this group.
    required: false
    type: list
  action:
    description: Work on group or member level
    default: group
    choices: ["member", "group"]
  state:
    description: State to ensure
    default: present
    choices: ["present", "absent"]
author:
    - Thomas Woerner
"""

EXAMPLES = """
# Create group ops with gid 1234
- ipagroup:
    ipaadmin_password: MyPassword123
    name: ops
    gidnumber: 1234

# Create group sysops
- ipagroup:
    ipaadmin_password: MyPassword123
    name: sysops

# Create group appops
- ipagroup:
    ipaadmin_password: MyPassword123
    name: appops

# Add user member pinky to group sysops
- ipagroup:
    ipaadmin_password: MyPassword123
    name: sysops
    action: member
    user:
    - pinky

# Add user member brain to group sysops
- ipagroup:
    ipaadmin_password: MyPassword123
    name: sysops
    action: member
    user:
    - brain

# Add group members sysops and appops to group sysops
- ipagroup:
    ipaadmin_password: MyPassword123
    name: ops
    group:
    - sysops
    - appops

# Remove goups sysops, appops and ops
- ipagroup:
    ipaadmin_password: MyPassword123
    name: sysops,appops,ops
    state: absent
"""

RETURN = """
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_text
from ansible.module_utils.ansible_freeipa_module import temp_kinit, \
    temp_kdestroy, valid_creds, api_connect, api_command, compare_args_ipa


def find_group(module, name):
    _args = {
        "all": True,
        "cn": to_text(name),
    }

    _result = api_command(module, "group_find", to_text(name), _args)

    if len(_result["result"]) > 1:
        module.fail_json(
            msg="There is more than one group '%s'" % (name))
    elif len(_result["result"]) == 1:
        return _result["result"][0]
    else:
        return None


def gen_args(description, gid, nonposix, external, nomembers):
    _args = {}
    if description is not None:
        _args["description"] = description
    if gid is not None:
        _args["gidnumber"] = str(gid)
    if nonposix is not None:
        _args["nonposix"] = nonposix
    if external is not None:
        _args["external"] = external
    if nomembers is not None:
        _args["nomembers"] = nomembers

    return _args


def gen_member_args(user, group, service):
    _args = {}
    if user is not None:
        _args["member_user"] = user
    if group is not None:
        _args["member_group"] = group
    if service is not None:
        _args["member_service"] = service

    return _args


def main():
    ansible_module = AnsibleModule(
        argument_spec=dict(
            # general
            ipaadmin_principal=dict(type="str", default="admin"),
            ipaadmin_password=dict(type="str", required=False, no_log=True),

            name=dict(type="list", aliases=["cn"], default=None,
                      required=True),
            # present
            description=dict(type="str", default=None),
            gid=dict(type="int", aliases=["gidnumber"], default=None),
            nonposix=dict(required=False, type='bool', default=None),
            external=dict(required=False, type='bool', default=None),
            nomembers=dict(required=False, type='bool', default=None),
            user=dict(required=False, type='list', default=None),
            group=dict(required=False, type='list', default=None),
            service=dict(required=False, type='list', default=None),
            action=dict(type="str", default="group",
                        choices=["member", "group"]),
            # state
            state=dict(type="str", default="present",
                       choices=["present", "absent",
                                "member_present", "member_absent"]),
        ),
        supports_check_mode=True,
    )

    ansible_module._ansible_debug = True

    # Get parameters

    # general
    ipaadmin_principal = ansible_module.params.get("ipaadmin_principal")
    ipaadmin_password = ansible_module.params.get("ipaadmin_password")
    names = ansible_module.params.get("name")

    # present
    description = ansible_module.params.get("description")
    gid = ansible_module.params.get("gid")
    nonposix = ansible_module.params.get("nonposix")
    external = ansible_module.params.get("external")
    nomembers = ansible_module.params.get("nomembers")
    user = ansible_module.params.get("user")
    group = ansible_module.params.get("group")
    service = ansible_module.params.get("service")
    action = ansible_module.params.get("action")
    # state
    state = ansible_module.params.get("state")

    # Check parameters

    if state == "present":
        if len(names) != 1:
            ansible_module.fail_json(
                msg="Only one group can be added at a time.")
        if action == "member":
            invalid = ["description", "gid", "nonposix", "external",
                       "nomembers"]
            for x in invalid:
                if vars()[x] is not None:
                    ansible_module.fail_json(
                        msg="Argument '%s' can not be used with action "
                        "'%s'" % (x, action))

    if state == "absent":
        if len(names) < 1:
            ansible_module.fail_json(
                msg="No name given.")
        invalid = ["description", "gid", "nonposix", "external", "nomembers"]
        if action == "group":
            invalid.extend(["user", "group", "service"])
        for x in invalid:
            if vars()[x] is not None:
                ansible_module.fail_json(
                    msg="Argument '%s' can not be used with state '%s'" %
                    (x, state))

    # Init

    changed = False
    exit_args = {}
    ccache_dir = None
    ccache_name = None
    try:
        if not valid_creds(ansible_module, ipaadmin_principal):
            ccache_dir, ccache_name = temp_kinit(ipaadmin_principal,
                                                 ipaadmin_password)
        api_connect()

        commands = []

        for name in names:
            # Make sure group exists
            res_find = find_group(ansible_module, name)

            # Create command
            if state == "present":
                # Generate args
                args = gen_args(description, gid, nonposix, external,
                                nomembers)

                if action == "group":
                    # Found the group
                    if res_find is not None:
                        # For all settings is args, check if there are
                        # different settings in the find result.
                        # If yes: modify
                        if not compare_args_ipa(ansible_module, args,
                                                res_find):
                            commands.append([name, "group_mod", args])
                    else:
                        commands.append([name, "group_add", args])
                        # Set res_find to empty dict for next step
                        res_find = {}

                    member_args = gen_member_args(user, group, service)
                    if not compare_args_ipa(ansible_module, member_args,
                                            res_find):
                        # Generate addition and removal lists
                        user_add = list(
                            set(user or []) -
                            set(res_find.get("member_user", [])))
                        user_del = list(
                            set(res_find.get("member_user", [])) -
                            set(user or []))
                        group_add = list(
                            set(group or []) -
                            set(res_find.get("member_group", [])))
                        group_del = list(
                            set(res_find.get("member_group", [])) -
                            set(group or []))
                        service_add = list(
                            set(service or []) -
                            set(res_find.get("member_service", [])))
                        service_del = list(
                            set(res_find.get("member_service", [])) -
                            set(service or []))

                        # Add members
                        if len(user_add) > 0 or len(group_add) > 0 or \
                           len(service_add) > 0:
                            commands.append([name, "group_add_member",
                                             {
                                                 "user": user_add,
                                                 "group": group_add,
                                                 "service": service_add,
                                             }])
                        # Remove members
                        if len(user_del) > 0 or len(group_del) > 0 or \
                           len(service_del) > 0:
                            commands.append([name, "group_remove_member",
                                             {
                                                 "user": user_del,
                                                 "group": group_del,
                                                 "service": service_del,
                                             }])
                elif action == "member":
                    if res_find is None:
                        ansible_module.fail_json(msg="No group '%s'" % name)

                    user_add = list(
                        set(user or []) -
                        set(res_find.get("member_user", [])))
                    group_add = list(
                        set(group or []) -
                        set(res_find.get("member_group", [])))
                    service_add = list(
                        set(service or []) -
                        set(res_find.get("member_service", [])))

                    # Add members
                    if len(user_add) > 0 or len(group_add) > 0 or \
                       len(service_add) > 0:
                        commands.append([name, "group_add_member",
                                         {
                                             "user": user,
                                             "group": group,
                                             "service": service,
                                         }])

            elif state == "absent":
                if action == "group":
                    if res_find is not None:
                        commands.append([name, "group_del", {}])

                elif action == "member":
                    if res_find is None:
                        ansible_module.fail_json(msg="No group '%s'" % name)

                    # Remove intersection member
                    user_del = list(
                        set(user or []) &
                        set(res_find.get("member_user", [])))
                    group_del = list(
                        set(group or []) &
                        set(res_find.get("member_group", [])))
                    service_del = list(
                        set(service or []) &
                        set(res_find.get("member_service", [])))

                    # Remove members
                    if len(user_del) > 0 or len(group_del) > 0 or \
                       len(service_del) > 0:
                        commands.append([name, "group_remove_member",
                                         {
                                             "user": user,
                                             "group": group,
                                             "service": service,
                                         }])
            else:
                ansible_module.fail_json(msg="Unkown state '%s'" % state)

        # Execute commands

        for name, command, args in commands:
            try:
                api_command(ansible_module, command, to_text(name), args)
                changed = True
            except Exception as e:
                ansible_module.fail_json(msg="%s: %s: %s" % (command, name,
                                                             str(e)))

    except Exception as e:
        ansible_module.fail_json(msg=str(e))

    finally:
        temp_kdestroy(ccache_dir, ccache_name)

    # Done

    ansible_module.exit_json(changed=changed, **exit_args)


if __name__ == "__main__":
    main()
