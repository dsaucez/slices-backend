from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
import oai
import yaml
import oai.gen_oai

class PosScriptData(BaseModel):
    name: str
    description: str
    deploy_node: str
    xp_url: str
    params_5g: dict

    class Config:
        # Example of content for documentation
        json_schema_extra = {
            "example": {
              "name": "name_of_the_xp",
              "description": "Nice description",
              "deploy_node": "sopnode-w3",
              "xp_url": "http://www.exmaple.org/xp.tar.gz",
              "params_5g": {}
            }
        }

def to_yaml(data):
    return yaml.safe_dump(data).strip()


template_dir = 'templates'
env = Environment(loader=FileSystemLoader(template_dir))
env.filters.update({'to_yaml': to_yaml})


def generate_script(data: PosScriptData, user: dict, id: str):
  template = env.get_template('deploy.sh.j2')  
  script = template.render(dict(data) | { "k8s_user": user["preferred_username"] } | { "project": user['proj_name'] })
  
  return script

def generate_inventory(data: PosScriptData, user: dict, id: str):
  template = env.get_template('hosts.yaml.j2')
  inventory = template.render(data)

  return inventory

def generate_dmi(data: PosScriptData, user: dict, id: str):
  template = env.get_template('params_dmi.yaml.j2')

  dmi = template.render(dict(data) | user | {"id": id})

  return dmi

def generate_params(data: PosScriptData, user: dict, id: str):
  template = env.get_template('params.yaml.j2')

  params = template.render(dict(data) | user | {"id": id})

  return params

def generate_params5g(data: PosScriptData, user: dict, id: str):
  template = env.get_template('params.5g.yaml.j2')

  params = template.render(dict(data) | user | {"id": id})

  return params


def generate_playbook_5g(data: PosScriptData, user: dict, id: str):
  template = env.get_template('5g.yaml.j2')
  playbook = template.render(data)

  return playbook

def generate_playbook(data: PosScriptData, user: dict, id: str):
  template = env.get_template('provision.yaml.j2')
  playbook = template.render(data)

  return playbook

def generate_oai(data: PosScriptData, user: dict, id: str, gip, zip_buffer):
   oai.gen_oai.build(data = dict(data), gip=gip, zip_buffer=zip_buffer)
   return {}


def generate_xp(data: PosScriptData, user: dict, id: str):
  template = env.get_template('get_xp.sh.j2')
  get_xp = template.render(data)

  return get_xp