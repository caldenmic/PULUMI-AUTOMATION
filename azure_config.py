import pulumi
import json

def get_config_object(config_file_path):
    with open(config_file_path, 'r') as config_file:
        config_data = json.load(config_file)
    pulumi.runtime.config.CONFIG.set(config_data)
    return pulumi.runtime.config.CONFIG.get()