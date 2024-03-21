import pulumi
import json
import pulumi.automation as auto
import pulumi_azure as azure
import pulumi_tls as tls
import pulumi_std as std
import pulumi_azuread as azuread

def get_config_object(config_file_path):
    with open(config_file_path, 'r') as config_file:
        config_data = json.load(config_file)
    pulumi.runtime.config.CONFIG.set(config_data)
    return pulumi.runtime.config.CONFIG.get()

def create_azure_vm():
    config_object = get_config_object('./config.json')
    os_image_publisher, os_image_offer, os_image_sku, os_image_version = config_object['osImage'].split(":")

    # Create an SSH key
    ssh_key = tls.PrivateKey(
        "ssh-key",
        algorithm = "RSA",
        rsa_bits = 4096,
    )

    resource_group_name = config_object['resourceGroupName']
    resource_group_id = config_object['resourceGroupId']
    vnet_name = config_object['vnetName']
    security_group_name = config_object['securityGroupName']
    network_interface_name = config_object['networkInterfaceName']
    vm_name = config_object['vnetName']
    vm_location = config_object['location']
    vm_size = config_object['vmSize']
    admin_username = config_object['adminUsername']
    storage_account_type = config_object['storageAccountType']


    # Use existing Resource Group
    resource_group = azure.core.ResourceGroup.get(resource_name=resource_group_name, id=resource_group_id)

    # Use existing Virtual Network
    existing_vnet = azure.network.get_virtual_network(resource_group_name=resource_group_name, name=vnet_name)

    # Use existing Network Security Group
    existing_network_security_group = azure.network.get_network_security_group(name=security_group_name, resource_group_name=resource_group_name)

    # Create a public IP address for the VM
    public_ip = azure.network.PublicIp(
        resource_name="public-ip",
        resource_group_name=resource_group.name,
        allocation_method="Dynamic",
    )

    # Create a network interface
    network_interface = azure.network.NetworkInterface(
        network_interface_name,
        resource_group_name=resource_group.name,
        ip_configurations=[azure.network.NetworkInterfaceIpConfigurationArgs(
            name=f"{vm_name}-ipconfiguration",
            subnet_id=f"{resource_group_id}/providers/Microsoft.Network/virtualNetworks/test-vnet/subnets/{existing_vnet.subnets[0]}",
            private_ip_address_allocation="Dynamic",
            public_ip_address_id=public_ip.id
        )],
    )

    network_security_group_association = azure.network.NetworkInterfaceSecurityGroupAssociation(
        f"{existing_network_security_group.name}-{network_interface_name}-association",
        network_interface_id=network_interface.id,
        network_security_group_id=existing_network_security_group.id,
    )

    # Create the virtual machine
    vm = azure.compute.LinuxVirtualMachine(
        resource_name=vm_name,
        resource_group_name=resource_group.name,
        location=vm_location,
        size=vm_size,
        admin_username=admin_username,
        network_interface_ids=[network_interface.id],
        admin_ssh_keys=[azure.compute.LinuxVirtualMachineAdminSshKeyArgs(
            username=admin_username,
            public_key=ssh_key.public_key_openssh,
        )],
        os_disk=azure.compute.LinuxVirtualMachineOsDiskArgs(
            caching="ReadWrite",
            storage_account_type=storage_account_type,
        ),
        source_image_reference=azure.compute.LinuxVirtualMachineSourceImageReferenceArgs(
            publisher=os_image_publisher,
            offer=os_image_offer,
            sku=os_image_sku,
            version=os_image_version,
        )
    )

def deploy_project(project_name: str, stack_name: str, program: callable):
    stack = auto.create_or_select_stack(stack_name=stack_name, project_name=project_name, program=program)
    stack.refresh(on_output=print)
    stack.up(on_output=print)
    return stack

def destroy_project(project_name: str, stack_name: str, program: callable):
    stack = auto.create_or_select_stack(stack_name=stack_name, project_name=project_name, program=program)
    stack.destroy(on_output=print)
    stack.workspace.remove_stack(stack_name)
    print(f"stack {stack_name} in project {project_name} removed")

def pass_function():
    pass

try:
    config_object = get_config_object('./config.json')
    # stack = deploy_project(config_object['projectName'], config_object['stackName'], create_azure_vm)
    destroy_project(config_object['projectName'], config_object['stackName'], pass_function)
except Exception as e:
    print(e)