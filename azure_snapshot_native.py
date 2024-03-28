import pulumi
import json
import pulumi.automation as auto
import pulumi_azure_native as azure
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
    vnet_id = config_object['vnetId']
    security_group_name = config_object['securityGroupName']
    network_security_group_id = config_object['networkSecurityGroupId']
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
    subnet_name = config_object['subnetName']


    # Use existing Resource Group
    resource_group = azure.resources.ResourceGroup.get(resource_name=resource_group_name, id=resource_group_id)

    # Use existing Virtual Network
    existing_vnet = azure.network.VirtualNetwork.get(resource_name=vnet_name, id=vnet_id)

    # Use existing Network Security Group
    existing_network_security_group = azure.network.NetworkSecurityGroup.get(resource_name=security_group_name, id=network_security_group_id)

    # Create a public IP address for the VM
    public_ip = azure.network.PublicIPAddress(
        resource_name=ip_address_resource_name,
        resource_group_name=resource_group.name,
        public_ip_allocation_method=azure.network.IpAllocationMethod.STATIC,
    )

    # Create a network interface
    network_interface = azure.network.NetworkInterface(
        resource_name=network_interface_name,
        resource_group_name=resource_group.name,
        network_security_group=azure.network.NetworkSecurityGroupArgs(
            id=existing_network_security_group.id,
        ),
        ip_configurations=[
            azure.network.NetworkInterfaceIPConfigurationArgs(
                name=ip_configuration_name,
                private_ip_allocation_method=azure.network.IpAllocationMethod.DYNAMIC,
                subnet=azure.network.SubnetArgs(
                    id=f"{resource_group_id}/providers/Microsoft.Network/virtualNetworks/{vnet_name}/subnets/{subnet_name}",
                ),
                public_ip_address=azure.network.PublicIPAddressArgs(
                    id=public_ip.id,
                ),
            ),
        ],
    )

    snapshot = azure.compute.Snapshot.get(
        resource_name=snapshot_name,
        id=f"{resource_group_id}/providers/Microsoft.Compute/snapshots/{snapshot_name}"
    )

    managed_disk = azure.compute.Disk(
        resource_name=managed_disk_name,
        creation_data=azure.compute.CreationDataArgs(
            create_option="Copy",
            source_resource_id=snapshot.id
        ),
        resource_group_name=resource_group_name
    )

    vm = azure.compute.VirtualMachine(
        resource_name=vm_name,
        hardware_profile=azure.compute.HardwareProfileArgs(
            vm_size=vm_size,
        ),
        resource_group_name=resource_group.name,
        network_profile=azure.compute.NetworkProfileArgs(
            network_interfaces=[azure.compute.NetworkInterfaceReferenceArgs(
                id=network_interface.id,
                primary=True,
            )],
        ),
        storage_profile=azure.compute.StorageProfileArgs(
            os_disk=azure.compute.OSDiskArgs(
                create_option="Attach",
                name=managed_disk.name,
                managed_disk=azure.compute.ManagedDiskParametersArgs(
                    id=managed_disk.id
                ),
                os_type="Linux"
            ),
        ),
        security_profile=azure.compute.SecurityProfileArgs(
            security_type=azure.compute.SecurityTypes.TRUSTED_LAUNCH
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