import pulumi
import json
import pulumi.automation as auto
import pulumi_azure as azure
import pulumi_tls as tls
import pulumi_azuread as azuread

def get_config_object(config_file_path):
    with open(config_file_path, 'r') as config_file:
        config_data = json.load(config_file)
    pulumi.runtime.config.CONFIG.set(config_data)
    return pulumi.runtime.config.CONFIG.get()

def restore_from_snapshot():
    config_object = get_config_object('./config_snapshot.json')
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
    vm_name = config_object['vmName']
    location = config_object['location']
    vm_size = config_object['vmSize']
    stack_name = config_object['stackName']
    admin_username = config_object['adminUsername']
    storage_account_type = config_object['storageAccountType']
    ip_configuration_name = config_object['ipConfigurationName']
    ip_address_resource_name = config_object['ipAddressResourceName']
    snapshot_name = config_object['snapshotName']
    managed_disk_name = config_object['managedDiskName']


    # Use existing Resource Group
    resource_group = azure.core.ResourceGroup.get(resource_name=resource_group_name, id=resource_group_id)

    # Use existing Virtual Network
    existing_vnet = azure.network.get_virtual_network(resource_group_name=resource_group_name, name=vnet_name)

    # Use existing Network Security Group
    existing_network_security_group = azure.network.get_network_security_group(name=security_group_name, resource_group_name=resource_group_name)

    # Create a public IP address for the VM
    public_ip = azure.network.PublicIp(
        resource_name=ip_address_resource_name,
        resource_group_name=resource_group.name,
        allocation_method="Static",
    )

    # Create a network interface
    network_interface = azure.network.NetworkInterface(
        network_interface_name,
        resource_group_name=resource_group.name,
        ip_configurations=[azure.network.NetworkInterfaceIpConfigurationArgs(
            name=ip_configuration_name,
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

    snapshot = azure.compute.Snapshot.get(
        resource_name=snapshot_name,
        resource_group_name=resource_group.name,
        id=f"{resource_group_id}/providers/Microsoft.Compute/snapshots/{snapshot_name}"
    )

    managed_disk = azure.compute.ManagedDisk(
        resource_name=managed_disk_name,
        resource_group_name=resource_group_name,
        source_resource_id=snapshot.id,
        create_option="Copy",
        storage_account_type=storage_account_type
    )

    vm = azure.compute.VirtualMachine(
        resource_name=vm_name,
        vm_size=vm_size,
        resource_group_name=resource_group.name,
        network_interface_ids=[network_interface.id],
        storage_os_disk=azure.compute.VirtualMachineStorageOsDiskArgs(
            create_option="Attach",
            name=managed_disk.name,
            managed_disk_id=managed_disk.id,
            os_type="Linux"
        )
    )

    pulumi.export('ip_address', public_ip.ip_address)
    pulumi.export('public_key', ssh_key.public_key_pem)
    pulumi.export('private_key', ssh_key.private_key_pem)

def deploy_project(project_name: str, stack_name: str, program: callable):
    stack = auto.create_or_select_stack(stack_name=stack_name, project_name=project_name, program=program)
    stack.refresh(on_output=print)
    stack.up(on_output=print)
    return stack

def destroy_project(project_name: str, stack_name: str, program: callable):
    stack = auto.create_or_select_stack(stack_name=stack_name, project_name=project_name, program=program)
    stack.refresh(on_output=print)
    stack.destroy(on_output=print)
    print(f"stack {stack_name} in project {project_name} removed")

def pass_function():
    pass

try:
    config_object = get_config_object('./config_snapshot.json')
    stack = deploy_project(config_object['projectName'], config_object['stackName'], restore_from_snapshot)
    # destroy_project(config_object['projectName'], config_object['stackName'], pass_function)
except Exception as e:
    print(e)