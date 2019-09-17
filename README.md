# Ansible role 'freeipa'

An Ansible role for setting up a FreeIPA stack.

This role is now an adaptation of [the official collection](https://github.com/freeipa/ansible-freeipa).
Much of the work is a straight up copy of the original, and I suggest that you use that one instead.
This one is stripped down to fit my personal needs.

## Requirements
* RHEL/CentOS 7.4+
* Fedora 26+
* Ubuntu
* Debian 10+ (ipaclient only, no server or replica!)

* /usr/bin/kinit is required on the controller if a one time password (OTP) is used
* python3-gssapi is required on the controller if a one time password (OTP) is used with keytab to install the client.

## Role Variables
| Variable		| Default		| Comments (type) |
| :---			| :---			| :---		  |

## Dependencies

## Example Playbook
```Yaml
- hosts: foo
  roles:
    - role: freeipa
```

## Testing

## License

GPLv3

## Contributors

Issues, feature requests, ideas, suggestions, etc. are appreciated and can be posted in the Issues section. Pull requests are also very welcome. Please create a topic branch for your proposed changes, it's the easiest way to merge back into the project.

- [Oscar Petersson](https://github.com/oscpe262/) (Maintainer)
