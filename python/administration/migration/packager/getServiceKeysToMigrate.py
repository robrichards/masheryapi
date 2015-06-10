import os, sys, urllib, argparse, time, requests, json, logging, random, string
import base

def updateKeyWithPackageData(key, apis, packages):
  key_to_migrate = {}
  key_to_migrate['apikey'] = key['apikey']
  key_to_migrate['service_key'] = key['service_key']

  for api in apis:
    if (api['service_key'] == key['service_key']):
      for package in packages:
        if (package['name'] == api['name']):
          key_to_migrate['package_id'] = package['id']
          plan_name = api['name']
          if (key['developer_class'] != None):
            plan_name = key['developer_class']['name']

          for plan in package['plans']:
            if (plan['name'] == plan_name):
              key_to_migrate['plan_id'] = plan['id']
  return key_to_migrate

def main(argv):
    # set up logging to file - see previous section for more details
  logging.basicConfig(level=logging.INFO,
                      format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                      datefmt='%m-%d %H:%M',
                      filename='myapp.log',
                      filemode='w')
  # define a Handler which writes INFO messages or higher to the sys.stderr
  console = logging.StreamHandler()
  console.setLevel(logging.INFO)
  # set a format which is simpler for console use
  formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
  # tell the handler to use this format
  console.setFormatter(formatter)
  # add the handler to the root logger
  logging.getLogger('').addHandler(console)
  logging.getLogger('requests').setLevel(logging.ERROR)

  global loggerMigrator
  loggerMigrator = logging.getLogger('migrator')

  parser = argparse.ArgumentParser()
  parser.add_argument("apikey", type=str, help="Mashery V2 API Key")
  parser.add_argument("secret", type=str, help="Mashery V2 API Secret")
  parser.add_argument("site_id", type=str, help="Mashery Area/Site ID")

  args = parser.parse_args()

  apikey = args.apikey
  secret = args.secret
  site_id = args.site_id

  apis = base.fetch(site_id, apikey, secret, 'service_definitions', '*, service, service_definition_endpoints, service.service_classes, service.service_classes.developer_class', '')
  packages = base.fetch(site_id, apikey, secret, 'packages', '*, plans', '')
  applications = base.fetch(site_id, apikey, secret, 'applications', '*, keys, keys.developer_class', '')

  applications_to_migrate = []
  for application in applications:
    if (application['is_packaged'] == True):
      continue
      
    application_to_migrate = {}
    application_to_migrate['id'] = application['id']
    application_to_migrate['name'] = application['name']
    application_to_migrate['username'] = application['username']
    application_to_migrate['keys'] = []
    for key in application['keys']:
      key_to_migrate = updateKeyWithPackageData(key, apis, packages)
      application_to_migrate['keys'].append(key_to_migrate)
    applications_to_migrate.append(application_to_migrate)

  f = open('keysToMigrate2.json','w')
  f.write(json.dumps(applications_to_migrate, indent=4, sort_keys=True))
  f.close()

if __name__ == "__main__":
    main(sys.argv[1:])    
