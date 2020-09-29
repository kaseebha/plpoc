import json
import pprint
import os
import boto3
import ct_tfextn_common
import requests
import base64
import pprint
import git
import logging
from botocore.exceptions import ClientError

#Get the Azure DevOps personal access token from Secrets Manager
git_secret_name = "cftfextn_ado_git_token"
git_secret = ct_tfextn_common.get_secret(git_secret_name)
pat = git_secret['cftfextn_ado_git_token']

#Convert ADO Personal Access Token to base64 and return
def getAuthorization():
    authorization = str(base64.b64encode(bytes(':'+pat, 'ascii')), 'ascii')
    return authorization 



#Generate the .tfvars file for the baseline repo
def generate_tfvars(baseline_repo_name, org_name, project_name, terraform_vars_map):
    #authorization = getAuthorization()
    print(f"Generating new tfvars file and adding to: {baseline_repo_name}")
    new_repo_path = f"/tmp/{baseline_repo_name}"
    os.mkdir(new_repo_path)
    
    #Prevents Git credentials from getting logged
    logging.getLogger("git").setLevel(logging.WARNING)
    repo_url = f"https://{pat}@dev.azure.com/{org_name}/{project_name}/_git/{baseline_repo_name}"
    
    git_user_name = "pl-css-admin"
    git_user_email = "admin@pacificlife.com"

    commit_env = os.environ
    commit_env['GIT_AUTHOR_NAME'] = 'PLUser'
    commit_env['GIT_AUTHOR_EMAIL'] = 'PL@pacificlife.com'
    commit_env['GIT_COMMITTER_NAME'] = 'PLUser'
    commit_env['GIT_COMMITTER_EMAIL'] = 'PL@pacificlife.com'

    git.exec_command('clone', repo_url, new_repo_path)
    
    #Write and commit the tfvars file to the baseline repo
    f = open(new_repo_path+"/terraform.auto.tfvars", "w")
    f.write("## tfvars ##\n\n")
    for k,v in terraform_vars_map.items():
        f.write(f"{k}    =   \"{v}\" \n")
    f.close()   

    #Commit the tfvars file
    git.exec_command('add','terraform.auto.tfvars', cwd=new_repo_path)
    git.exec_command('commit','-m','added auto.tfvars', cwd=new_repo_path)
    git.exec_command('push', cwd=new_repo_path)

#Get the project Id for a given project name
def getProjectId(org, project_name):
    
    authorization = getAuthorization()

    headers = {
    'Accept': 'application/json',
    'Authorization': 'Basic '+authorization,
    'Content-Type': 'application/json'
    }

    url = f"https://dev.azure.com/{org}/_apis/projects?api-version=6.0"
    print(url)
    response = requests.get(url=url, headers=headers)
    print(response)
    #Get the project id from the resulting json
    result_list = response.json().get('value')
    for x in result_list:
        if x.get('name') == project_name:
            project_id = x.get('id')
            break

    #print(project_id)
    return project_id

#Get the parentRepository Id for a given account type
def getRepositoryId(org, project_name, repo_name):

    authorization = getAuthorization()

    headers = {
    'Accept': 'application/json',
    'Authorization': 'Basic '+authorization,
    'Content-Type': 'application/json'
    }

    url = f"https://dev.azure.com/{org}/{project_name}/_apis/git/repositories?api-version=6.0"

    response = requests.get(url=url, headers=headers)

    result_list = response.json().get('value')
    for x in result_list:
        if x.get('name') == repo_name:
            repo_id = x.get('id')
            break

    #print(repo_id)
    return repo_id

#Fork the template repository for the specified account type. Eg. sandbox account forks the sandbox template repository
def fork_repository(baseline_repo_template_name, baseline_repo_name, org, project_name, terraform_vars_map):

    authorization = getAuthorization()

    headers = {
    'Accept': 'application/json',
    'Authorization': 'Basic '+authorization,
    'Content-Type': 'application/json'
    }

    project_id = getProjectId(org, project_name)
    parent_repository_id = getRepositoryId(org, project_name, baseline_repo_template_name)

    payload = {
        "name": baseline_repo_name,
        "project": {
            "id": project_id
        },
        "parentRepository": {
            "id": parent_repository_id,
            "project": {
                "id": project_id
            }
        }
    }

    #Fork the template repository into a new repository for the given account
    url = f"https://dev.azure.com/{org}/_apis/git/repositories?api-version=6.0"

    response = requests.post(url=url, data=json.dumps(payload), headers=headers)

    #print(response.text)

    baseline_repo_name = response.json().get('name')
    print(baseline_repo_name)

    #Generate the tfvars file in the newly created baseline repository
    generate_tfvars(baseline_repo_name, org, project_name, terraform_vars_map)

    #print(response.status_code)
    #print(response.webUrl)
    return response.status_code

#Creates a new repository in a specific ADO project and organization
def create_repository(org, project_name, repo_name):
    
    authorization = getAuthorization()

    headers = {
    'Accept': 'application/json',
    'Authorization': 'Basic '+authorization,
    'Content-Type': 'application/json'
    }

    project_id = getProjectId(org, project_name)

    payload = {
        "name": repo_name,
        "project": {
            "name": project_name,
            "id": project_id
            }
    }

    print("Creating the new application repository")
    url = f"https://dev.azure.com/{org}/{project_name}/_apis/git/repositories?api-version=6.0"
    response = requests.post(url=url, data=json.dumps(payload), headers=headers)

    print(response.text)
    return response.status_code

#Creates a new subdirectory under baseline repo - "aws-account-baselines"
def create_baseline_subdirectory(org, project_name, baseline_repo_name, subdir_name):
    
    #Make tmp directory to checkout Git repo
    local_repo_path = f"/tmp/{baseline_repo_name}"
    os.mkdir(local_repo_path)
    
    #Prevents Git credentials from getting logged
    logging.getLogger("git").setLevel(logging.WARNING)
    baseline_repo_url = f"https://{pat}@dev.azure.com/{org}/{project_name}/_git/{baseline_repo_name}"
    
    git_user_name = "pl-css-admin"
    git_user_email = "admin@pacificlife.com"

    commit_env = os.environ
    commit_env['GIT_AUTHOR_NAME'] = 'PLUser'
    commit_env['GIT_AUTHOR_EMAIL'] = 'PL@pacificlife.com'
    commit_env['GIT_COMMITTER_NAME'] = 'PLUser'
    commit_env['GIT_COMMITTER_EMAIL'] = 'PL@pacificlife.com'

    git.exec_command('clone', baseline_repo_url, local_repo_path)
       
    #Define subdir path
    subdir_path = f"{local_repo_path}/{subdir_name}"
    # define the access rights
    access_rights = 0o755
    
    try:
        os.mkdir(subdir_path, access_rights)
    except FileExistsError as e:
        print(f"The baseline sub-directory: {subdir_name} already exists, skipping changes")
        
    else:
        print(f"Successfully created the account baseline sub-directory: {subdir_name}")
        
        #Creating test file to commit
        f = open(subdir_path+"/terraform.auto.tfvars", "w")
        f.write("## Autogenerated terraform.auto.tfvars ##\n\n")
        f.close()   

        #Commit the tfvars file
        print(f"Committing changes")
        git.exec_command('add','-A', cwd=local_repo_path)
        git.exec_command('commit','-m','added auto.tfvars', cwd=local_repo_path)
        git.exec_command('push', cwd=local_repo_path)

#Check if a given repository already exists
def check_repo_exists(org, project_name, repo_name):
    authorization = getAuthorization()

    headers = {
    'Accept': 'application/json',
    'Authorization': 'Basic '+authorization,
    'Content-Type': 'application/json'
    }

    url = f"https://dev.azure.com/{org}/{project_name}/_apis/git/repositories?api-version=6.0"
    response = requests.get(url=url, headers=headers)

    #pp.pprint(response.text)
    repo_list = response.json().get('value')
    
    #print(repo_list)
    for r in repo_list:
        if r.get('name') == repo_name:
            print(f"Found existing repository: {repo_name}")
            return True

def handler_inner(event, context):

    account_id = event["AccountId"]
    #Retrieve account details from the metadata DDB table
    account_info = ct_tfextn_common.get_account_metadata(account_id, 'ct-tf-extn-account-metadata')
    account_type = account_info['Item']['request_details']['account_type']
    account_name = account_info['Item']['request_details']['account_name']
    baseline_repo_template_name = f"ct-tf-baseline-{account_type}"

    #pp.pprint(account_name)
    #Retrieve the baseline repository details
    baseline_git_details = account_info['Item']['git_tfe_details']['baseline']
    baseline_repo =  baseline_git_details["git"].split('/')[-4:]
    #baseline_repo_name = baseline_repo[-1].replace(".git","")
    baseline_repo_name = "aws-account-baselines"
    org_name = baseline_repo[0]
    project_name = baseline_repo[1]

    #Retrieve the application repository details
    application_git_details = account_info['Item']['git_tfe_details']['application']
    application_repo =  application_git_details["git"].split('/')[-4:]
    application_repo_name = application_repo[-1].replace(".git","")

    #Retrieve the Terraform variables 
    terraform_vars_map = account_info['Item']['request_details']['account_variables']

    #Check if repos exist and only continue if they don't
    #if not check_repo_exists(org_name, project_name, baseline_repo_name):
    #     #Fork and create a new baseline repository and populate the tfvars file
    #     print(f"Creating baseline repository: {baseline_repo_name}")
    #     fork_repository(baseline_repo_template_name, baseline_repo_name, org_name, project_name, terraform_vars_map)
        
    #Create a subdirectory under the baseline repo if this is a new AWS account
    subdir_name = f"{account_name}-baseline"
    if check_repo_exists(org_name, project_name, baseline_repo_name):
        create_baseline_subdirectory(org_name, project_name, baseline_repo_name, subdir_name)
    else:
        print(f"Unable to find baseline repository.")
    # if not check_repo_exists(org_name, project_name, application_repo_name):
    #     print(f"Creating application repositories: {application_repo_name}")
    #     #Create the application repository
    #     create_repository(org_name, project_name, application_repo_name)

def lambda_handler(event, context):
    
    try:
        account_id = event["AccountId"]
        handler_inner(event, context)
    except ClientError as e:
        body = f"Unexpected error : {e}"
        print(body)
        print(account_id)
        sub  = "ERROR: TFE Create Git repositories"
        raise e

    #pp.pprint(terraform_vars_map)

if __name__ == "__main__":
    from optparse import OptionParser
    import pprint
    import json
    import sys

    parser = OptionParser()
    parser.add_option("-a", "--account_number", dest="account_number", help="Account number to test")
    pp = pprint.PrettyPrinter(indent=4)
    (options, args) = parser.parse_args(sys.argv)
    event = { "AccountId": f"{options.account_number}"}
    lambda_handler(event, None)
