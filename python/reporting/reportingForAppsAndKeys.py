import sys, urllib, argparse
sys.path.append( '../lib/' )
import masheryV2, masheryDate

def apiName(apis, apiId):
  for api in apis['result']['items']:
    if (api['service_key'] == apiId):
      return api['name']

def main(argv):
  
  parser = argparse.ArgumentParser()
  parser.add_argument("apikey", type=str, help="Mashery V2 API Key")
  parser.add_argument("secret", type=str, help="Mashery V2 API Secret")
  parser.add_argument("siteId", type=str, help="Mashery Area/Site ID")
  parser.add_argument("startDate", type=str, help="Start Date")
  parser.add_argument("endDate", type=str, help="End Date")
  parser.add_argument("outputFile", type=str, help="Output Filename")
  parser.add_argument('--apis',  nargs='+', help='List of APIs by name, space separated')
  parser.add_argument('--keys',  nargs='+', help='List of keys to include in results, space separated')
  parser.add_argument('--fields',  nargs='+', help='List of key/app fields to retrieve, space separated')
  args = parser.parse_args()
  
  apikey = args.apikey
  secret = args.secret
  siteId = args.siteId
  startDate = args.startDate
  endDate = args.endDate
  outputFile = args.outputFile

  if masheryDate.dayGap(startDate, endDate) < 1:
    print 'ERROR: endDate must be at least 1 day past startDate'
    return

  apis = args.apis

  if args.apis == None:
    apis = []

  # get list of APIs
  all_apis = masheryV2.post(siteId, apikey, secret, '{"method":"object.query","id":1,"params":["select * from services ITEMS 1000"]}')

  keys = args.keys

  if args.keys == None:
    keys = []

  results = []

  dates = masheryDate.daysToReportOn(startDate, endDate)
  
  for api in all_apis['result']['items']:
    try:
        if (len(apis) > 0):
          str(apis.index(api['name'])) + ' ' + api['name']

        print 'Processing...' + api['name']
        for date in dates:
          urlParams = '&start_date=' + urllib.quote_plus(date[0]) + '&end_date=' + urllib.quote_plus(date[1]) + '&format=json&limit=1000'
          results.extend(masheryV2.get(siteId, apikey, secret, '/reports/calls/developer_activity/service/' + api['service_key'], urlParams))

    except ValueError:
        pass

  f = open(outputFile,'w')
  customFields = 'application.name'
  if (args.fields != None):
    customFields = ','.join(args.fields)

  headers = customFields + ',service.name,service.id,key.apikey,startDate,endDate,successful,blocked,other,total\n'

  f.write(headers)
  for result in results:

    try:
        if (len(keys) > 0):
          keys.index(result['serviceDevKey'])

        key = masheryV2.post(siteId, apikey, secret, '{"method":"object.query","id":1,"params":["select ' + customFields + ' from keys where apikey = \'' + result['serviceDevKey']  + '\'"]}')

        application_name = '<UNKNOWN>'
        if (key['result']['total_items'] > 0) :
          customFieldValues = ''
          if (args.fields != None):
              
            for field in args.fields:
              splitFields = field.split('.')
              if len(splitFields) == 2:
                customFieldValues = customFieldValues + '"' + key['result']['items'][0][splitFields[0]][splitFields[1]] + '",'
              else:
                customFieldValues = customFieldValues + '"' + key['result']['items'][0][splitFields[0]] + '",'

        f.write(customFieldValues + result['serviceKey'] + ',"' + apiName(all_apis, result['serviceKey']) + '",'+ result['serviceDevKey']  + ',' + result['startDate']  + ',' + result['endDate']  + ','+ str(result['callStatusSuccessful'])  + ',' + str(result['callStatusBlocked']) + ',' + str(result['callStatusOther']) + ',' + str(result['callStatusSuccessful'] +  result['callStatusBlocked'] + result['callStatusOther']) + '\n')
    except TypeError:
        pass
    except ValueError:
        pass

  f.close()
if __name__ == "__main__":
    main(sys.argv[1:])