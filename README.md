# Ansible role 'freeipa'

An Ansible role for setting up a FreeIPA stack in Fedora.
This role is not up to production standard by any means.
The default values aren't studied in detail yet, nor all vars tested.
Any feedback is welcome!

## Requirements
Fedora 27 (might work on other releases, but it is the only one (barely) tested, feedback welcome!)

## Role Variables
| Variable		| Default		| Comments (type) |
| :---			| :---			| :---		  |
| `ad_trust` | `True` | Install with Active Directory trust |
| `with_dns` | `True` | Install with integrated DNS server |

## Dependencies

## Example Playbook
```Yaml
- hosts: foo
  roles:
    - role: freeipa
```

## Testing

## License

BSD

## Contributors

Issues, feature requests, ideas, suggestions, etc. are appreciated and can be posted in the Issues section. Pull requests are also very welcome. Please create a topic branch for your proposed changes, it's the easiest way to merge back into the project.

- [Oscar Petersson](https://github.com/oscpe262/) (Maintainer)
