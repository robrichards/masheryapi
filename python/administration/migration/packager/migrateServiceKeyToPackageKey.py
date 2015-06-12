import sys, urllib, argparse, time, requests, json, logging
import base, logger

def archive(backup_location, key_data):
    f = open(backup_location + str(key_data['apikey']) + '_' + str(key_data['service_key']) + '.json', 'w')
    f.write(json.dumps(key_data))
    f.write('\n')
    f.close()

def noAppNoMember(keys):
    for key in keys:
        if (key['member'] == None or key['application'] == None):
            return True
    return False

def getPackagePlanForKey(packages, key):
    for plan in packages:
      if (plan['id'] == key['plan_id'] and plan['package']['id'] == key['package_id']):
        return plan

    return None

def getApiForKey(apis, key_data):
    for api in apis:
      if (api['service_key'] == key_data['service_key']):
        return api

    return None

def fetchKey(site_id, apikey, secret, key):
    key_data = None
    # fetch key data
    try:
        key_data = base.fetch(site_id, apikey, secret, 'keys', '*, member, application, service, developer_class', 'WHERE apikey = \'' + key['apikey'] + '\' AND service_key = \'' + key['service_key'] + '\'')
    except ValueError as err:
        loggerMigrator.error('Problem fetching key: %s', json.dumps(err.args))
        return False

    if (len(key_data) == 1):
        key_data = key_data[0]
    else:
        loggerMigrator.error('Problem fetching key for %s', json.dumps(application))
    
    return key_data

def fetchApplication(site_id, apikey, secret, application):
    application_data = None
    if (application['id'] != ''):
        try:
            # get the application from the database
            application_data = base.fetch(site_id, apikey, secret, 'applications', '*, keys', 'WHERE id = ' + str(application['id']))
        except ValueError as err:
            loggerMigrator.error('Problem fetching application: %s', json.dumps(err.args))

        if (len(application_data) == 1):
            application_data = application_data[0]
        else:
            loggerMigrator.error('Problem fetching application for %s', json.dumps(application))

        if (len(application['keys']) != len(application_data['keys'])):
            loggerMigrator.error('Application data missing keys %s', json.dumps(application))

    return application_data

def getPackageKey(key_data, package_data):
    package = {}
    package['id'] = package_data['package']['id']

    plan = {}
    plan['id'] = package_data['id']

    application = {}
    application['id'] = key_data['application']['id']

    key_data['package'] = package
    key_data['plan'] = plan
    key_data['application'] = application

    return key_data

def planContainsService(package_data, service_of_key):
    for plan_service in package_data['plan_services']:
        if (plan_service['service_definition']['service_key'] == service_of_key):
            return True

    return False

def readyToBeMigrated(key_data, api_data, package_data):
    result = {}
    result['Apikey'] = key_data['apikey']
    result['Memberless Key'] = False
    result['Applicationless Key'] = False
    result['Service Not In Plan'] = False

    ready = True
    if (key_data['member'] == None):
        ready = False
        result['Memberless Key'] = True

    if (key_data['application'] == None):
        ready = False
        result['Applicationless Key'] = True
        
    if (package_data['package']['name'] != api_data['name']):
        ready = False
        result['Service Name Does Not Match Package Name'] = True

    if (key_data['developer_class'] != None and package_data['name'] != key_data['developer_class']['name']):
        ready = False
        result['Developer Class Name Does Not Match Plan Name'] = True

    if (planContainsService(package_data, key_data['service_key']) == False):
        ready = False
        result['Service Not In Plan'] = True

    result['ready'] = ready

    return result;

def main(argv):
    # setup logging
    global loggerMigrator
    loggerMigrator =    logger.setup('migrateServiceKeyToPackageKey', 'myapp.log')

    # get arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("apikey", type=str, help="Mashery V2 API Key")
    parser.add_argument("secret", type=str, help="Mashery V2 API Secret")
    parser.add_argument("site_id", type=str, help="Mashery Area/Site ID")
    parser.add_argument("backup_location", type=str, help="Fully qualified path for backup of key data")
    parser.add_argument('migration_map_location',    type=str, help="Fully qualified path for backup of key data")
    parser.add_argument('--nodryrun', action='store_true', default=False, help='specify to perform work, leave off command for dry run')

    args = parser.parse_args()

    apikey = args.apikey
    secret = args.secret
    site_id = args.site_id
    backup_location = args.backup_location
    migration_map_location = args.migration_map_location
    nodryrun = args.nodryrun

    # fetch keys in area, to see if there are any existing
    # memberless or applicationless ones
    try:
        keys = base.fetch(site_id, apikey, secret, 'keys', '*, member, application', '')
    except ValueError as err:
        loggerMigrator.error('Error fetching data: %s', json.dumps(err.args))
        return

    if (noAppNoMember(keys) == True):
        loggerMigrator.error('Applicationless and memberless keys still exist.')
        return 

    # get the input file, containing a json representation
    # of apps to migrate
    try:
        f = open(migration_map_location, 'r')
        file_contents = f.read()
        migration_data = json.loads(file_contents)
        f.close()
    except IOError:
        loggerMigrator.error('Failed opening migration map file.')
        return
    except ValueError:
        loggerMigrator.error('Invalid JSON in migration map file.')
        return

    # get apis and packages
    apis = []
    packages = []
    try:
        apis = base.fetch(site_id, apikey, secret, 'services', '*', '')
        packages = base.fetch(site_id, apikey, secret, 'plans', '*, package, plan_services.service_definition', '')
    except ValueError as err:
        loggerMigrator.error('Error fetching data: %s', json.dumps(err.args))
        return

    # process each application to see if it is ready to go
    for application in migration_data:
        ready = True

        application_data = fetchApplication(site_id, apikey, secret, application)

        if (application_data == None):
            return False

        keys_to_delete = [] # list of keys to delete
        package_keys_to_create = [] # list of package keys to create

        for key in application['keys']:

            # fetch key data
            key_data = fetchKey(site_id, apikey, secret, key)
            if (key_data == None):
                return False

            # fetch api data
            api_data = getApiForKey(apis, key_data)
            if (api_data == None):
                loggerMigrator.error('Problem fetching api: %s', json.dumps(key_data))
                return False

            # fetch package data
            package_data = getPackagePlanForKey(packages, key)
            if (package_data == None):
                loggerMigrator.error('Problem fetching package: %s', json.dumps(key_data))
                return False

            ready_data = readyToBeMigrated(key_data, api_data, package_data)
            #loggerMigrator.info('Migration readiness for %s ::: %s', json.dumps(key_data), json.dumps(ready_data))
            if (ready_data['ready'] == False):
                ready = False

            if (ready == True):
                keys_to_delete.append(key_data)
                package_key = getPackageKey(key_data, package_data)
                package_keys_to_create.append(package_key)
            else:
                loggerMigrator.error('Key not ready to be migrated: %s', json.dumps(application))        

        if (ready == True):
            #loggerMigrator.info('Ready for migration: %s ', json.dumps(application))
            # before enabling app for packager we must delete and archive all keys
            #for key in keys_to_delete:
            #    archive(backup_location, key)

            if (nodryrun == True):
                try:
                    base.delete(site_id, apikey, secret, 'key', keys_to_delete) 
                except ValueError as err:
                    loggerMigrator.error('Problem deleting keys: %s', json.dumps(err.args))
                    return 

            if (nodryrun == True):
                application_data['is_packaged'] = True
                try:
                    base.update(site_id, apikey, secret, 'application', application_data)
                except ValueError as err:
                    loggerMigrator.error('Problem updating application: %s', json.dumps(err.args))
                    return 

                try:                  
                    base.create(site_id, apikey, secret, 'package_key', package_keys_to_create)
                except ValueError as err:
                    loggerMigrator.error('Problem creating package key: %s', json.dumps(err.args))
                    return 

if __name__ == "__main__":
        main(sys.argv[1:])        
