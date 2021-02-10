# vmware_guest_vgpu
Ansible module for managing shared PCI devices specifically NVIDIA vGPU under VMware

## setup and use
The fastest way for me was to download the file into my default Ansible modules folder. You can find it by typing the following:

```
ansible --version

ansible 2.10.3
  config file = ~/ansible.cfg
  configured module search path = ['~/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
  ansible python module location = /usr/local/lib/python3.9/site-packages/ansible
  executable location = /usr/local/bin/ansible
  python version = 3.9.0
```
For my user it was inside the *~/.ansible/plugins/modules* folder

Then use one of the following examples. Remember to fill the vCenter variables within your inventory.

## Examples Adding vGPU
```
- hosts: localhost
  gather_facts: no
  tasks:
    - name: add pci
      vmware_guest_pci:
        hostname: "{{ vcenter_hostname }}"
        username: "{{ vcenter_username }}"
        password: "{{ vcenter_password }}"
        datacenter: "{{ datacenter_name }}"
        name: UbuntuTest
        pci_id: 'grid_m10-8q'
        state: present
      register: vgpu_facts

    - name: Generating vGPU facts logs
      debug: var=vgpu_facts

```

## Examples Removing vGPU
```
- hosts: localhost
  gather_facts: no
  tasks:
    - name: add pci
      vmware_guest_pci:
        hostname: "{{ vcenter_hostname }}"
        username: "{{ vcenter_username }}"
        password: "{{ vcenter_password }}"
        datacenter: "{{ datacenter_name }}"
        name: UbuntuTest
        pci_id: 'grid_m10-8q'
        state: absent
      register: vgpu_facts

    - name: Generating vGPU facts logs
      debug: var=vgpu_facts

```
