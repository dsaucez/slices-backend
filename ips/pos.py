from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
from typing import Optional
import oai
import yaml
import oai.gen_oai
import json

class PosScriptData(BaseModel):
    experiment_id: str
    name: str
    description: str
    deploy_node: str
    resources: Optional[list]
    xp_url: str
    params_5g: dict
    scientificDomains: Optional[list] = ['network']
    scientificSubdomains: Optional[list] = ['5G']
    version: Optional[str] = "v0.1"
    license: Optional[str] = "BSD-3-Clause"

    class Config:
        # Example of content for documentation
        json_schema_extra = {
            "example": {
              "experiment_id": "exp_expauth.ilabt.imec.be_abcdefghijklmnopqrstuvwxyz",
              "name": "name_of_the_xp",
              "description": "Nice description",
              "deploy_node": "sopnode-w3",
              "xp_url": "http://www.exmaple.org/xp.tar.gz",
              "params_5g": {},
              "scientificDomains": ['network'],
              "scientificSubdomains": ['5G'],
              "version": "v0.1",
              "license": "BSD-3-Clause"
            }
        }

def to_yaml(data):
    return yaml.safe_dump(data).strip()


template_dir = 'templates'
env = Environment(loader=FileSystemLoader(template_dir))
env.filters.update({'to_yaml': to_yaml})

import re
def generate_script(data: PosScriptData, user: dict, id: str):
  template = env.get_template('deploy.sh.j2')

  script = template.render(dict(data) | { "k8s_user": user["preferred_username"] } | { "project": user['proj_name']})
  
  return script

def generate_sh5g(data: PosScriptData, user: dict, id: str):
  template = env.get_template('5g.sh.j2')  
  script = template.render(dict(data) | { "k8s_user": user["preferred_username"] } | { "project": user['proj_name'] })
  
  return script

def generate_variables(data: PosScriptData, user: dict, id: str):
  template = env.get_template('variables.yaml.j2')

  match = re.search(r'_(\w+)$', data.experiment_id)
  xp_id=match.group(1)
  _variables = template.render({ "xp_id": xp_id })
  
  return _variables

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

  # XXX TODO dsaucez change, this is just a quickfix
  if 'config_files' in data.params_5g['GCN']:
    data.params_5g['GCN']['config_files'] = 'oai-cn5g-fed-custom/'

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

def generate_oai(data: PosScriptData, user: dict, id: str, zip_buffer):
   _oai = oai.gen_oai.build(data = dict(data), zip_buffer=zip_buffer)

   return json.dumps(_oai)


def generate_xp(data: PosScriptData, user: dict, id: str):
  template = env.get_template('get_xp.sh.j2')
  get_xp = template.render(data)

  return get_xp