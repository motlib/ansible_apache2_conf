# apache2_conf

`apache2_conf` is a module for [Ansible] to configure the [Apache] 2 webserver.

There is already an `apache2_module` plugin distributed with Ansible, so why
another one? `apache2_conf` can not only enable or disable modules, but can also
work on sites and configurations.

# License

The `apache2_conf` module is distributed under the terms of the GNU GPL
version 3. See `COPYING.txt` for details.

# Installation

To use this module, check out this git repository and put the `apache2_conf.py`
module into the library folder in your Ansible project.

## Requirements

The plugin requires the tools `a2query`, `a2enITEM` and `a2disITEM` (where ITEM
is one of `conf`, `mod` or `site`) on the hosts controlled by ansible.

# Usage

You can in one task enable or disable one item, i.e. either a configuration, a
site or a module.

## Parameters

These are the supported parameters:

-   `item`: One of 'module', 'config' or 'site. This is the thing you want to
    work on.
-   `name`: The name of the item, i.e. the name of a configuration, a site or a
    module of Apache to enable or disable.
-   `state`: Either `absent` to disable the item or `present` to enable the
    item.

## Return values

If the task succeeds, the returned JSON only contains the result message in the
`msg` attribute.

Example success return value:

```json
{
  "changed": true,
  "msg": "site 'testsite' is present"
}
```

If the task fails, the returned JSON contains the exit code `rc` of the underlying
tool and its `stdout` and `stderr` output.

Example failure return value:

```json
{
  "changed": false,
  "msg": "site 'testsitenonexist' is unknown",
  "rc": 1,
  "stderr": "No site matches testsitenonexist\n",
  "stdout": ""
}
```


## Examples

Here are some examples:

Enable the `charset` module:

```yaml
apache2_conf:
  item: module
  name: charset
  state: present
```

Disable the same module:

```yaml
apache2_conf:
  item: module
  name: charset
  state: absent
```

[Ansible]: https://ansible.com
[Apache]: https://www.apache.org
