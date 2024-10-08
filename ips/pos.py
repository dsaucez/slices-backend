from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
import uuid

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

template_dir = 'templates'
env = Environment(loader=FileSystemLoader(template_dir))

def generate_script(data: PosScriptData, user: dict, id: str):
  template = env.get_template('deploy.sh.j2')  
  script = template.render(dict(data) | {"k8s_user": user["preferred_username"]})
  
  return script

def generate_inventory(data: PosScriptData, user: dict, id: str):
  template = env.get_template('hosts.yaml.j2')
  inventory = template.render(data)

  return inventory

def generate_dmi(data: PosScriptData, user: dict, id: str):
  template = env.get_template('params_dmi.yaml.j2')

  dmi = template.render(dict(data) | user | {"id": id})

  return dmi

def generate_playbook_5g(data: PosScriptData, user: dict, id: str):
  data = {}

  template = env.get_template('5g.yaml.j2')
  playbook = template.render(data)

  return playbook

def generate_playbook(data: PosScriptData, user: dict, id: str):
  data = {}

  template = env.get_template('provision.yaml.j2')
  playbook = template.render(data)

  return playbook

import oai
def generate_oai(data: PosScriptData, user: dict, id: str, gip, zip_buffer):
   oai.gen_oai.build(data = dict(data), gip=gip, zip_buffer=zip_buffer)
   return {}