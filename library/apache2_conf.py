#!/usr/bin/python
# coding: utf-8 -*-

# (c) 2020, Andreas Schroeder <andreas@a-netz.de>
# GNU General Public License v3.0+ (see COPYING or
# https://www.gnu.org/licenses/gpl-3.0.txt)
#
# Inspiration taken from `apache2_module` module by
# Christian Berendt <berendt@b1-systems.de>

'''Ansible module to enable or disable configurations, sites and modules for
Apache 2.'''

from __future__ import absolute_import, division, print_function

# pylint: disable=invalid-name
__metaclass__ = type

# import module snippets
from ansible.module_utils.basic import AnsibleModule


ANSIBLE_METADATA = {'metadata_version': '0.0',
                    'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = '''
---
module: apache2_conf
version_added: 2.9.4
author:
    - Andreas Schroeder (@motlib)
short_description: Enables/disables a configuration, site or module of the Apache2 webserver.
description:
   - Enables/disables a configuration, site or module (in the following called *item*) of the Apache2 webserver.
options:
   name:
     description:
        - Name of the item to enable/disable as given to C(a2query) and C(a2en.../a2dis...) tools.
     required: true
   state:
     description:
        - Desired state of the module.
     choices: ['present', 'absent']
     default: present
requirements: ["a2query","a2enconf","a2disconf"]
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
RC_A2QUERY_ENABLED = 0
RC_A2QUERY_NOT_FOUND = 32
RC_A2QUERY_DISABLED = 33
RC_A2QUERY_UNKNOWN = 1

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
        error_msg = "Required command '%s' not found." % cmd
        module.fail_json(msg=error_msg)

    result, stdout, stderr = module.run_command(
        "%s %s" % (cmd_bin, params))

    return (result, stdout, stderr)


def _get_state(module, itemcfg, name):
    '''Return the current state of an apache item.

    :param module: Ansible module object.
    :param itemcfg: Item configuration structure.
    :param str name: Name of the item to query.

    :returns: True if the item is enabled, False if disabled and None if the
      item is unknown. '''

    result, _, stderr = _run_cmd(
        module,
        cmd='a2query',
        params='%s %s' % (itemcfg['query_flag'], name))

    if result == RC_A2QUERY_ENABLED:
        return True
    if result == RC_A2QUERY_UNKNOWN:
        error_msg = "%s '%s' is unknown" % (itemcfg['name'], name)
        module.fail_json(msg=error_msg)
        return None
    if result in (RC_A2QUERY_DISABLED, RC_A2QUERY_NOT_FOUND):
        return False

    error_msg = "Error executing a2query: %i %s" % (result, stderr)
    module.fail_json(msg=error_msg)

    return None


def _set_state(module, itemcfg, name, state):
    '''Set the state (enabled / disabled) of an apache item.

    :param module: Ansible module object.
    :param itemcfg: Item configuration structure.
    :param str name: The item to enable or disable.
    :param bool state: True to enable, False to disable.'''

    cur_state = _get_state(module, itemcfg, name)

    if cur_state == state:
        # nothing to do
        return

    cmd = itemcfg['enable_bin'] if state else itemcfg['disable_bin']
    param = "-q -f %s" % name
    (result, _, stderr) = _run_cmd(module, cmd, param)

    if result != RC_A2TOOL_OK:
        error_msg = "Failed to execute '%s %s': %s" % (cmd, param, stderr)
        module.fail_json(msg=error_msg)


def main():
    '''Module entrypoint.'''

    module = AnsibleModule(
        argument_spec=dict(
            name=dict(required=True),
            item=dict(required=True, choices=[
                ITEM_KEY_MODULE,
                ITEM_KEY_CONFIG,
                ITEM_KEY_SITE]),
            state=dict(default='present', choices=['absent', 'present']),
        ),
        supports_check_mode=True,
    )

    module.warnings = []

    name = module.params['name']
    item = module.params['item']

    itemcfg = SETTINGS[item]

    req_state = module.params['state'] == 'present'
    cur_state = _get_state(module, itemcfg, name)

    changed_state = (cur_state != req_state)

    # Only run _set_state if not in check mode
    if not module.check_mode:
        _set_state(module, itemcfg, name, req_state)

    success_msg = "%s '%s' is %s" % (itemcfg['name'], name, module.params['state'])

    module.exit_json(
        changed=changed_state,
        result=success_msg,
        warnings=module.warnings)

if __name__ == '__main__':
    main()
