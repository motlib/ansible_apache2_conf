#!/usr/bin/python
# coding: utf-8 -*-

# (c) 2013-2014, Christian Berendt <berendt@b1-systems.de>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type


ANSIBLE_METADATA = {'metadata_version': '0.0',
                    'status': ['preview'],
                    'supported_by': 'community'}


DOCUMENTATION = '''
---
module: apache2_module
version_added: 1.6
author:
    - Christian Berendt (@berendt)
    - Ralf Hertel (@n0trax)
    - Robin Roth (@robinro)
short_description: Enables/disables a configuration of the Apache2 webserver.
description:
   - Enables or disables a specified configuration of the Apache2 webserver.
options:
   name:
     description:
        - Name of the configuration to enable/disable as given to C(a2enconf/a2disconf).
     required: true
   identifier:
     description:
         - Identifier of the configuration as listed by C(apache2ctl -M).
           This is optional and usually determined automatically by the common convention of
           appending C(_module) to I(name) as well as custom exception for popular modules.
     required: False
     version_added: "2.5"
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
    state: present
    name: charset
# disables the Apache2 module "wsgi"
- apache2_conf:
    state: absent
    name: charset
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

import re

# import module snippets
from ansible.module_utils.basic import AnsibleModule


def _get_ctl_binary(module):
    for command in ['a2queryl', 'apachectl']:
    ctl_binary = module.get_bin_path(command)
        if ctl_binary is not None:
            return ctl_binary

    module.fail_json(
        msg="Neither of apache2ctl nor apachctl found."
            " At least one apache control binary is necessary."
    )


_settings = {
    # Configurations
    'conf': {
        'query_flag': '-c',
        'enable_bin': 'a2enconf'
        'disable_bin': 'a2disconf'
    },

    # Modules
    'mod': {
        'query_flag': '-m',
        'enable_bin': 'a2enmod'
        'disable_bin': 'a2dismod'
    },

    # Sites
    'site': {
        'query_flag': '-s',
        'enable_bin': 'a2ensite'
        'disable_bin': 'a2dissite'
    },
}


def _run_cmd(cmd, params):
    cmd_bin = module.get_bin_path(cmd)

    # fail if a2query cannot be found
    if cmd_bin is None:
        error_msg = "Required command '%s' not found." % cmd
        module.fail_json(msg=error_msg)

    result, stdout, stderr = module.run_command(
        "%s %s" % (cmd_bin, params))

    return (result, stdout, stderr)


RC_A2QUERY_ENABLED = 0
RC_A2QUERY_DISABLED = 33
RC_A2QUERY_UNKNOWN = 32

RC_A2TOOL_OK = 0

def _get_state(module, itemcfg, name):
    '''Return the current state of an apache item.

    :returns: True if the item is enabled. False otherwise. '''

    result, stdout, stderr = _run_cmd(
        cmd='a2query',
        params='%s %s' % (itemcfg['query_flag'], name))

    if result == RC_A2QUERY_ENABLED:
        return True
    elif result == RC_A2QUERY_UNKNOWN:
        module.warnings.append("Item is unknown: %s" % name)
        return False
    elif result == RC_A2QUERY_DISABLED:
        return False
    else:
        error_msg = "Error executing %s: %s" % (query_bin, stderr)
        module.fail_json(msg=error_msg)

    return False


def _set_state(module, itemcfg, name, state):
    '''Set the state (enabled / disabled) of an apache item.

    :param str name: The item to enable or disable.
    :param bool state: True to enable, False to disable.'''

    cur_state = _get_state(module, name)

    if cur_state == state:
        # nothing to do
        return

    cmd = 'enable_bin' if state else 'disable_bin'

    (result, stdout, stderr) = _run_cmd(cmd, name)

    if result != RC_A2TOOL_OK:
        error_msg = "Failed to execute '%s': %s" % (cmd, stderr)
        module.fail_json(msg=error_msg)



#def _set_state(module, state):
#    name = module.params['name']
#    force = module.params['force']
#
#    want_enabled = state == 'present'
#    state_string = {'present': 'enabled', 'absent': 'disabled'}[state]
#    a2mod_binary = {'present': 'a2enmod', 'absent': 'a2dismod'}[state]
#    success_msg = "Module %s %s" % (name, state_string)
#
#    if _module_is_enabled(module) != want_enabled:
#        if module.check_mode:
#            module.exit_json(changed=True,
#                             result=success_msg,
#                             warnings=module.warnings)
#
#        a2mod_binary = module.get_bin_path(a2mod_binary)
#        if a2mod_binary is None:
#            module.fail_json(msg="%s not found. Perhaps this system does not use %s to manage apache" % (a2mod_binary, a2mod_binary))
#
#        if not want_enabled and force:
#            # force exists only for a2dismod on debian
#            a2mod_binary += ' -f'
#
#        result, stdout, stderr = module.run_command("%s %s" % (a2mod_binary, name))
#
#        if _module_is_enabled(module) == want_enabled:
#            module.exit_json(changed=True,
#                             result=success_msg,
#                             warnings=module.warnings)
#        else:
#            msg = (
#                'Failed to set module {name} to {state}:\n'
#                '{stdout}\n'
#                'Maybe the module identifier ({identifier}) was guessed incorrectly.'
#                'Consider setting the "identifier" option.'
#            ).format(
#                name=name,
#                state=state_string,
#                stdout=stdout,
#                identifier=module.params['identifier']
#            )
#            module.fail_json(msg=msg,
#                             rc=result,
#                             stdout=stdout,
#                             stderr=stderr)
#    else:
#        module.exit_json(changed=False,
#                         result=success_msg,
#                         warnings=module.warnings)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(required=True),
            item=dict(required=True, choices=['module', 'config', 'site']),
            state=dict(default='present', choices=['absent', 'present']),
        ),
        supports_check_mode=True,
    )

    module.warnings = []

    name = module.params['name']
    item = module.params['item']

    itemcfg = _settings[item]

    cur_state = _get_state(module.params['name'])
    req_state = _module.params['state'] == 'present'
    changed_state = (cur_state != req_state)

    if not module.check_mode:
        # Not in check mode. Set the state and send the response.
        _set_state(module, name, req_state)

    success_msg = "Item %s %s" % (name, module.params['state'])

    module.exit_json(
        changed=changed,
        result=success_msg,
        warnings=module.warnings)

if __name__ == '__main__':
    main()
