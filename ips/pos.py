from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
import uuid

import oai.gen_oai

class PosScriptData(BaseModel):
    project: str
    name: str
    description: str
    deploy_node: str
    xp_url: str
    k8s_user: str
    params_5g: dict

    class Config:
        # Example of content for documentation
        json_schema_extra = {
            "example": {
              "project": "slices-project",
              "name": "name_of_the_xp",
              "description": "Nice description",
              "deploy_node": "sopnode-w3",
              "xp_url": "http://www.exmaple.org/xp.tar.gz",
              "k8s_user": "my-k8s-user",
              "params_5g": {}
            }
        }

template_dir = 'templates'
env = Environment(loader=FileSystemLoader(template_dir))

def generate_script(data: PosScriptData):
  template = env.get_template('deploy.sh.j2')  
  script = template.render(data)
  
  return script

def generate_inventory(data: PosScriptData):
  template = env.get_template('hosts.yaml.j2')
  inventory = template.render(data)

  return inventory

def generate_dmi(data: PosScriptData, user: dict):
  template = env.get_template('params_dmi.yaml.j2')

  dmi = template.render(dict(data) | user | {"uuid": uuid.uuid4()})

  return dmi

def generate_playbook_5g():
  data = {}

  template = env.get_template('5g.yaml.j2')
  playbook = template.render(data)

  return playbook

def generate_playbook():
  data = {}

  template = env.get_template('provision.yaml.j2')
  playbook = template.render(data)

  return playbook

import oai
def generate_oai(data: PosScriptData, gip, zip_buffer):
   oai.gen_oai.build(data = dict(data), gip=gip, zip_buffer=zip_buffer)
   return {}