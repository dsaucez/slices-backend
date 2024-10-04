import os
import yaml
from jinja2 import Environment, FileSystemLoader, BaseLoader

import requests

def to_yaml(data):
    return yaml.safe_dump(data).strip()

def createFile(content, filename):
  with open(filename, mode="w", encoding="utf-8") as file:
    file.write(content)

def genIPs(gcn, gip):
  # net = ipaddr.IPNetwork(gcn['multus']['network'])
  # base_ip = net.ip + 2
  hostInterface = gcn['multus']['hostInterface']

  reserved = list()
  for i in range(0, 18):
    rip = gip(cluster_name="central_multus")
    reserved.append(rip)

  prefixlen = reserved[0]["prefixlen"]

  lb_ip = gip(cluster_name="central_lb")

  ips = {
    "amf": {
      "n2": {'ip': reserved[0]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface}
    },
    "smf": {
      "n4": {'ip': reserved[1]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface}
    },
    "upf": {
      "n3": {'ip': reserved[2]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface},
      "n4": {'ip': reserved[3]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface},
      "n6": {'ip': reserved[4]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface}
    },
    "gnb": {
      "n2": {'ip': reserved[5]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface},
      "n3": {'ip': reserved[6]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface},
    },
    "du": {
      "f1": {'ip': reserved[7]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface}
    }, #
    "cu": {
      "f1": {'ip': reserved[8]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface},
      "n2": {'ip': reserved[9]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface},
      "n3": {'ip': reserved[10]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface}
    },
    "cucp": {
      "e1": {'ip': reserved[11]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface},
      "n2": {'ip': reserved[12]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface},
      "f1": {'ip': reserved[8]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface}
    },
    "cuup": {
      "e1": {'ip': reserved[14]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface},
      "n3": {'ip': reserved[15]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface},
      "f1": {'ip': reserved[16]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface}
    },
    "trafficserver": {
      'ip': reserved[17]['ip'], 'prefixlen': prefixlen, 'hostInterface': hostInterface
    },
    "nrf": {
      "loadBalancerIP": lb_ip #gcn['core']['nrfLoadBalancerIP']
    },
  }
  return ips

def plmnSupportList(gcn):
  slices = gcn['slices']
  plnms: []

  nssais = []
  for _slice in slices:
    nssais.append(_slice['snssai'])

  return [
    {
      'mcc': gcn['mcc'],
      'mnc': gcn['mnc'],
      'tac': gcn['tac'],
      'nssai': nssais
      }
    ]

def smfInfo(gcn):
  slices = gcn['slices']

  items = list()
  for _slice in slices:
    item = {
      'sNssai': _slice['snssai'],
      'dnnSmfInfoList': []
      }
    for dnn in _slice['dnns']:
      item['dnnSmfInfoList'].append({'dnn': dnn})
    items.append(item)
  return {'sNssaiSmfInfoList': items}

def servedGuamiList(gcn):
  return [
    {
      'mcc': gcn['mcc'],
      'mnc': gcn['mnc'],
      'amf_region_id': '01',
      'amf_set_id': '001',
      'amf_pointer': '01'
      }
      ]


def readFile(path):
  with open(path, "r") as file:
    content = file.read()
  return content

def render(environment, templatepath, gcn):
  template = environment.get_template(templatepath)

  slices = gcn['slices']
  dnns    = gcn['dnns']

  smf_info = smfInfo(gcn)
  plmn_support_list = plmnSupportList(gcn)
  served_guami_list = servedGuamiList(gcn)

  content = template.render(
      mcc     = gcn['mcc'],
      mnc     = gcn['mnc'],
      tac     = gcn['tac'],
      slices  = slices,
      dnns    = dnns,
      smf_info = smf_info,
      plmn_support_list = plmn_support_list,
      served_guami_list = served_guami_list,
      network = gcn['multus'],
      core = gcn
  )

  return content

import zipfile

def build(data: dict, gip, zip_buffer):
  # ==============================================================================
  # load configurations
  #manifest = os.environ['manifest']
  dir = "oai/v2.0.1/templates"
  manifest = f"{dir}/manifest.yaml"
  templates_dir = f"{dir}/oai-cn5g-fed/charts"

  with open(manifest, "r") as file:
    tpls = yaml.safe_load(file)

  core = data['params_5g']
  # core = yaml.safe_load(os.environ['params_5g'])
  gcn = core['GCN']

  # Prepare rendering environment
  environment = Environment(loader=FileSystemLoader(templates_dir))
  environment.filters.update({'to_yaml': to_yaml})

  if 'multus' in gcn:
    if "ips" not in gcn['multus']:
      gcn['multus']['ips'] = genIPs(gcn, gip)


  # Render files
  for item in tpls["templates"]:
    path = item['template']
    torender = True if 'render' not in item.keys() else item['render']

    if torender:
      content = render(environment, path, gcn)
    else:
      content = readFile("/".join([tpls["templates_dir"], path ]))
    # createFile(content, item['output'])
    with zipfile.ZipFile(zip_buffer, "a") as zip_file:
      zip_file.writestr(item['output'], content)
    print ("added")