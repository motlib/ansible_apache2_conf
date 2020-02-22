#!/usr/bin/python
# coding: utf-8 -*-
#
# apache2_conf
# Copyright (C) 2020 Andreas Schroeder <andreas@a-netz.de>
#
# This program is free software: you can redistribute it and/or modify
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# Inspiration taken from `apache2_module` module by
# Christian Berendt <berendt@b1-systems.de>

'''Ansible module to enable or disable configurations, sites and modules for
Apache 2.'''

from __future__ import absolute_import, division, print_function
import re

# pylint: disable=invalid-name
__metaclass__ = type

# import module snippets
from ansible.module_utils.basic import AnsibleModule


ANSIBLE_METADATA = {'metadata_version': '1.1',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: apache2_conf
version_added: '2.9.4'
author:
    - Andreas Schroeder (@motlib)
short_description: Enables/disables a configuration, site or module of the Apache2 webserver.
description:
   - Enables/disables a configuration, site or module (in the following called *item*) of the Apache2 webserver.
options:
   name:
     description:
        - Name of the item or items to enable / disable.
     required: true
   item:
     description:
        - The item to change. Either a configuration, a site or a module.
     choices: ['config', 'module', 'site']
     required: true
   state:
     description:
        - Desired state of the module.
        - 'absent' disables an item
        - 'present' enables an item
        - 'exclusive_present' enables only the listed items and disables all other items.
     choices: ['present', 'exclusive_present', 'absent']
     default: present

requirements: ["a2query", "a2enconf", "a2disconf", "a2enmod", "a2dismod", "a2ensite", "a2dissite"]
'''

EXAMPLES = '''
# enables the Apache2 configuration "charset"
- apache2_conf:
    item: config
    name: charset
    state: present
# disables the Apache2 module "wsgi"
- apache2_conf:
    item: module
    name: charset
    state: absent
# enables the site "www2"
- apache2_conf:
    item: site
    name: www2
    state: present
'''

RETURN = '''
result:
    description: message about action taken
    returned: always
    type: str
warnings:
    description: list of warning messages
    returned: when needed
    type: list
rc:
    description: return code of underlying command
    returned: failed
    type: int
stdout:
    description: stdout of underlying command
    returned: failed
    type: str
stderr:
    description: stderr of underlying command
    returned: failed
    type: str
config:
    description: List of all now enabled configurations.
    returned: always
    type: list of str
module:
    description: List of all now enabled modules.
    returned: always
    type: list of str
site:
    description: List of all now enabled sites.
    returned: always
    type: list of str
'''

ITEM_KEY_CONFIG = 'config'
ITEM_KEY_MODULE = 'module'
ITEM_KEY_SITE = 'site'

# Dictionary with information how to handle items (configs, modules, sites)
SETTINGS = {
    # Configurations
    ITEM_KEY_CONFIG: {
        'name': 'configuration',
        'query_flag': '-c',
        'enable_bin': 'a2enconf',
        'disable_bin': 'a2disconf',
    },

    # Modules
    ITEM_KEY_MODULE: {
        'name': 'module',
        'query_flag': '-m',
        'enable_bin': 'a2enmod',
        'disable_bin': 'a2dismod',
    },

    # Sites
    ITEM_KEY_SITE: {
        'name': 'site',
        'query_flag': '-s',
        'enable_bin': 'a2ensite',
        'disable_bin': 'a2dissite',
    },
}


# Tool return codes
RC_A2QUERY_OK = 0
RC_A2QUERY_NOT_FOUND = 32
RC_A2QUERY_DISABLED = 33
RC_A2QUERY_UNKNOWN = 1

# return code for a2en... / a2dis...
RC_A2TOOL_OK = 0


def _run_cmd(module, cmd, params):
    '''Run a command. If the command is not found, fail the module with an
    error message.

    :param module: Ansible module object.
    :param str cmd: The command (binary) to execute.
    :param str params: String with command-line options.

    :returns: Tuple of (exit code, standard output, standard error output)'''

    cmd_bin = module.get_bin_path(cmd)

    # fail if a2query cannot be found
    if cmd_bin is None:
        error_msg = "Command not found: %s" % cmd
        module.fail_json(msg=error_msg)

    result, stdout, stderr = module.run_command(
        "%s %s" % (cmd_bin, params))

    return (result, stdout, stderr)


def _get_all_states(module):
    '''Return a dictionary mapping the item keys to lists of enabled items.

    :param module: Ansible module object.
    :returns: dict'''

    # initialize states with empty lists
    states = {k: [] for k in SETTINGS}

    for item in states:
        rc, stdout, stderr = _run_cmd(
            module,
            cmd='a2query',
            params='%s' % (SETTINGS[item]['query_flag']))

        if rc == RC_A2QUERY_NOT_FOUND:
            # 32 is returned, if no item is enabled (empty list)
            continue

        if rc != RC_A2QUERY_OK:
            error_msg = "Error executing a2query: %i %s" % (rc, stderr)
            module.fail_json(msg=error_msg, rc=rc, stdout=stdout, stderr=stderr)

        for line in stdout.split('\n'):
            m = re.match(r'^(.*) \(.*\)$', line)
            if m:
                states[item].append(m.group(1))

        states[item].sort()

    return states


def _set_state(module, itemcfg, name, state):
    '''Set the state (enabled / disabled) of an apache item.

    :param module: Ansible module object.
    :param itemcfg: Item configuration structure.
    :param str name: The item to enable or disable.
    :param bool state: True to enable, False to disable.'''

    cmd = itemcfg['enable_bin'] if state else itemcfg['disable_bin']
    param = "-q -f %s" % name
    (rc, stdout, stderr) = _run_cmd(module, cmd, param)

    if rc != RC_A2TOOL_OK:
        error_msg = "Failed to execute '%s %s'" % (cmd, param)
        module.fail_json(msg=error_msg, rc=rc, stdout=stdout, stderr=stderr)


def main():
    '''Module entrypoint.'''

    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type='list', elements='str', required=True),
            item=dict(required=True, choices=[
                ITEM_KEY_MODULE,
                ITEM_KEY_CONFIG,
                ITEM_KEY_SITE]),
            state=dict(default='present', choices=['absent', 'present', 'exclusive_present']),
        ),
        supports_check_mode=True,
    )

    module.warnings = []

    item = module.params['item']
    itemcfg = SETTINGS[item]

    states = _get_all_states(module)


    # generate a dictionary with all requested state changes
    req_states = {}
    if module.params['state'] in ('absent', 'present'):
        for name in module.params['name']:
            req_states[name] = (module.params['state'] == 'present')
    else: # module.params['state'] == 'exclusive_present':
        # first set all items to 'absent', then overwrite for requested modules.
        for name in states[item]:
            req_states[name] = False
        for name in module.params['name']:
            req_states[name] = True


    # Global change state
    any_changed = False

    for name, req_state in req_states.items():
        cur_state = name in states[item]

        changed_state = (cur_state != req_state)
        any_changed |= changed_state

        # Only run _set_state if not in check mode and a change is requested
        if not module.check_mode and changed_state:
            _set_state(module, itemcfg, name, req_state)

    # retrieve all states again after modification.
    new_states = _get_all_states(module)

    success_msg = "%s %s: %s" % (
        itemcfg['name'],
        module.params['state'],
        ', '.join(module.params['name'])
    )

    module.exit_json(
        changed=any_changed,
        diff={
            'before': states,
            'after': new_states},
        msg=success_msg,
        warnings=module.warnings,
        **new_states)

if __name__ == '__main__':
    main()
