#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

try:
    from pyVmomi import vim
except ImportError:
    pass

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.community.vmware.plugins.module_utils.vmware import (
    PyVmomi, vmware_argument_spec, wait_for_task)


class PyVmomiHelper(PyVmomi):
    def __init__(self, module):
        super(PyVmomiHelper, self).__init__(module)

    def _vgpu_absent(self, vm_obj):
        result = {}
        vgpu_prfl = self.params['vgpu']
        vgpu_VirtualDevice_obj = self._get_vgpu_VirtualDevice_object(vm_obj, vgpu_prfl)
        if vgpu_VirtualDevice_obj is None:
            changed = False
            failed = False
        else:
            vgpu_fact = self._gather_vgpu_profile_facts(vm_obj)
            changed, failed = self._remove_vgpu_profile_from_vm(vm_obj, vgpu_VirtualDevice_obj, vgpu_prfl)
        result = {'changed': changed, 'failed': failed, 'vgpu': vgpu_fact}
        return result

    def _remove_vgpu_profile_from_vm(self, vm_obj, vgpu_VirtualDevice_obj, vgpu_prfl):
        changed = False
        failed = False
        vm_current_vgpu_profile = self._get_vgpu_profile_in_the_vm(vm_obj)
        if vgpu_prfl in vm_current_vgpu_profile:
            vdspec = vim.vm.device.VirtualDeviceSpec()
            vmConfigSpec = vim.vm.ConfigSpec()
            vdspec.operation = 'remove'
            vdspec.device = vgpu_VirtualDevice_obj
            vmConfigSpec.deviceChange.append(vdspec)

            try:
                task = vm_obj.ReconfigVM_Task(spec=vmConfigSpec)
                wait_for_task(task)
                changed = True
                return changed, failed
            except Exception as exc:
                failed = True
                self.module.fail_json(msg="Failed to delete vGPU profile"
                                          " '{}' from vm {}.".format(vgpu_prfl, vm_obj.name),
                                          detail=exc.msg)
        return changed, failed

    def _vgpu_present(self, vm_obj):
        result = {}
        vgpu_prfl = self.params['vgpu']
        vgpu_profile_name = self._get_vgpu_profiles_name(vm_obj, vgpu_prfl)
        if vgpu_profile_name is None:
            self.module.fail_json(msg="vGPU Profile '{}'"
                                      " does not exist.".format(vgpu_prfl))

        changed, failed = self._add_vgpu_profile_to_vm(vm_obj, vgpu_profile_name, vgpu_prfl)
        vgpu_fact = self._gather_vgpu_profile_facts(vm_obj)
        result = {'changed': changed, 'failed': failed, 'vgpu': vgpu_fact}
        return result

    def _add_vgpu_profile_to_vm(self, vm_obj, vgpu_profile_name, vgpu_prfl):
        changed = False
        failed = False
        vm_current_vgpu_profile = self._get_vgpu_profile_in_the_vm(vm_obj)
        if self.params['force'] or vgpu_prfl not in vm_current_vgpu_profile:
            vgpu_p = vgpu_profile_name.vgpu
            backing = vim.VirtualPCIPassthroughVmiopBackingInfo(vgpu=vgpu_p)
            summary = "NVIDIA GRID vGPU " + vgpu_prfl
            deviceInfo = vim.Description(summary=summary ,label="PCI device 0")
            hba_object = vim.VirtualPCIPassthrough(backing=backing, deviceInfo=deviceInfo)
            new_device_config = vim.VirtualDeviceConfigSpec(device=hba_object)
            new_device_config.operation = "add"
            vmConfigSpec = vim.vm.ConfigSpec()
            vmConfigSpec.deviceChange = [new_device_config]
            vmConfigSpec.memoryReservationLockedToMax = True

            #spec = vim.VirtualMachineConfigSpec()
            #spec.deviceChange = [vim.VirtualDeviceConfigSpec()]
            #spec.deviceChange[0] = VirtualDeviceConfigSpec()
            #spec.deviceChange[0].operation = 'add'
            #spec.deviceChange[0].device = vim.VirtualPCIPassthrough()
            #spec.deviceChange[0].device.deviceInfo = vim.Description()
            #spec.deviceChange[0].device.deviceInfo.summary = ''
            #spec.deviceChange[0].device.deviceInfo.label = 'New Shared PCI device vGPU'
            #spec.deviceChange[0].device.backing = vim.VirtualPCIPassthroughVmiopBackingInfo()
            #spec.deviceChange[0].device.backing.vgpu = vgpuprfl

            try:
                task = vm_obj.ReconfigVM_Task(spec=vmConfigSpec)
                wait_for_task(task)
                changed = True
            except Exception as exc:
                failed = True
                self.module.fail_json(msg="Failed to add vGPU Profile"
                                          " '{}' to vm {}.".format(vgpu_prfl, vm_obj.name),
                                          detail=exc.msg)
        else:
            return changed, failed
        return changed, failed



    def _get_vgpu_profile_in_the_vm(self, vm_obj):
        vm_current_vgpu_profile = []
        for vgpu_VirtualDevice_obj in vm_obj.config.hardware.device:
            if hasattr(vgpu_VirtualDevice_obj.backing, 'vgpu'):
                vm_current_vgpu_profile.append(vgpu_VirtualDevice_obj.backing.vgpu)
        return vm_current_vgpu_profile

    def _get_vgpu_VirtualDevice_object(self, vm_obj, vgpu_prfl):
        for vgpu_VirtualDevice_obj in vm_obj.config.hardware.device:
            if hasattr(vgpu_VirtualDevice_obj.backing, 'vgpu'):
                if vgpu_VirtualDevice_obj.backing.vgpu == vgpu_prfl:
                    return vgpu_VirtualDevice_obj
                    break
        return None

    def _get_vgpu_profiles_name(self, vm_obj, vgpu_prfl):
        vm_host = vm_obj.runtime.host
        vgpu_profiles = vm_host.config.sharedGpuCapabilities
        for vgpu_profile_name in vgpu_profiles:
            if vgpu_profile_name.vgpu == vgpu_prfl:
                return vgpu_profile_name
                break
        return None

    def _gather_vgpu_profile_facts(self, vm_obj):
        """
        Gather facts about VM's vGPU profile settings
        Args:
            vm_obj: Managed object of virtual machine
        Returns: vGPU device and a list of dict video card configuration
        """
        vgpu_facts = dict()
        for vgpu_VirtualDevice_obj in vm_obj.config.hardware.device:
            if hasattr(vgpu_VirtualDevice_obj.backing, 'vgpu'):
                vgpu_facts = dict(
                    Vgpu = vgpu_VirtualDevice_obj.backing.vgpu,
                    Key = vgpu_VirtualDevice_obj.key,
                    Summary = vgpu_VirtualDevice_obj.deviceInfo.summary,
                    Label = vgpu_VirtualDevice_obj.deviceInfo.label,
                    Unit_Number = vgpu_VirtualDevice_obj.unitNumber,
                    Controller_Key = vgpu_VirtualDevice_obj.controllerKey,
                )
                break
        return vgpu_facts


def main():
    argument_spec = vmware_argument_spec()
    argument_spec.update(
        name=dict(type='str'),
        uuid=dict(type='str'),
        use_instance_uuid=dict(type='bool', default=False),
        moid=dict(type='str'),
        folder=dict(type='str'),
        datacenter=dict(type='str', default='ha-datacenter'),
        esxi_hostname=dict(type='str'),
        cluster=dict(type='str'),
        vgpu=dict(type='str'),
        force=dict(type='bool', default=False),
        state=dict(type='str', default='present', choices=['absent', 'present'])
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[
            ['cluster', 'esxi_hostname']
        ],
        required_one_of=[
            ['name', 'uuid', 'moid']
        ],
        # supports_check_mode=True
    )

    pyv = PyVmomiHelper(module)
    vm = pyv.get_vm()

    if not vm:
        vm_id = (module.params.get('uuid') or module.params.get('name') or module.params.get('moid'))
        module.fail_json(msg="Unable to manage vGPU profile for non-existing VM {}".format(vm_id))

    if module.params['state'] == 'present':
        result = pyv._vgpu_present(vm)
    elif module.params['state'] == 'absent':
        result = pyv._vgpu_absent(vm)

    if 'failed' not in result:
        result['failed'] = False

    if result['failed']:
        module.fail_json(**result)
    else:
        module.exit_json(**result)


if __name__ == '__main__':
    main()
