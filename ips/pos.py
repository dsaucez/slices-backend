from jinja2 import Environment, FileSystemLoader

template_dir = 'templates'
env = Environment(loader=FileSystemLoader(template_dir))


def generate_script(deploy_node: str):
  data = {
    "deploy_node": deploy_node, 
    "demo_name": "my_demo",
    "k8s_user": "user1",
    "project": "slices5gcore",
    }

  template = env.get_template('deploy.sh.j2')  
  script = template.render(data)
  
  return script

def generate_inventory(deploy_node: str):
  data = {
    "deploy_node": deploy_node, 
    }

  template = env.get_template('hosts.yaml.j2')
  inventory = template.render(data)

  return inventory

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