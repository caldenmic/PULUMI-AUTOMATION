import pulumi.automation as auto
import pulumi_azure_native as azure
import azure_config

def destroy_project(project_name: str, stack_name: str, program: callable):
    stack = auto.create_or_select_stack(stack_name=stack_name, project_name=project_name, program=program)
    stack.refresh(on_output=print)
    stack.destroy(on_output=print)
    print(f"Stack \"{stack_name}\" in Project \"{project_name}\" deleted")

def pass_function():
    pass

try:
    config_object = azure_config.get_config_object('./config_snapshot.json')
    stack = destroy_project(config_object['projectName'], config_object['stackName'], pass_function)
except Exception as e:
    raise e