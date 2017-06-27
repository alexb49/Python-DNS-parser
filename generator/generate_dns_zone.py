#!/usr/bin/python2
"""
author: alexis
email: abezard@guardiananalytics.com || alexisbezard@gmail.com
project: cmdb
"""

"""


TODO:
  - 
"""

import os
import sys
import json
import getopt
from os import path
sys.path.append( path.dirname( path.dirname( path.abspath(__file__) ) ) )

from utility.query import QueryCMDB, SqlStringOrNull
from utility.logger import *



def CheckData(query_result_line):
  """ Make sure we don't have an empty field in a line returned by a query

  Args:
    result returned by a query (only 1 line)

  Returns: True or False
  """

  # valid data set?
  valid_data = True

  # explore all the keys in the query
  for key in query_result_line.keys():
    if not query_result_line[key]:
      if key != 'ttl':
        Log("Unable to generate the following record: %s / No value found for the following field: %s." % (query_result_line, key), logging.ERROR)
        valid_data = False

  return valid_data


def GenerateRecords(zone_id,zone_name):
  """ for a specific zone, generates all the records

  Args:
    zone ID
    zone Name

  Returns: 
  """

  zone_data = []

  # get global ttl
  global_ttl = GetTTL(zone_id,zone_name)

  # get SOA for the zone we're working on
  global_soa = GetSOA(zone_id,zone_name)

  # if we didn't get an SOA
  if not global_soa:
    Log("Failed to generate the zone file. Could not find an SOA for: %s" % zone_name, logging.ERROR)
    return None

  # if we didn't get a TTL
  if not global_ttl:
    Log("Failed to generate the zone file. Could not find a TTL for: %s" % zone_name, logging.ERROR)
    return None

  print '$TTL\t' + global_ttl
  print global_soa

  # then generate all the records, per ORIGIN
  sql_get_all_origins = "SELECT * FROM network_dns_zone_origin WHERE network_dns_zone_id = %s" % SqlStringOrNull(zone_id)
  get_all_origins = QueryCMDB(sql_get_all_origins)

  # if the query returned something
  if get_all_origins:
    # for each origin
    for origin in get_all_origins:

      print
      print '$ORIGIN\t' + origin['name']

      # let's get all the records using this origin in this zone
      sql_get_all_records = """SELECT ndzr.name AS record_name, ndzr.ttl, ndrc.name AS class, ndrt.name AS type, ndzr.rdata 
                               FROM network_dns_zone_record ndzr, network_dns_record_class ndrc, network_dns_record_type ndrt 
                               WHERE ndrt.id = ndzr.network_dns_record_type_id 
                               AND ndrc.id = ndzr.network_dns_record_class_id 
                               AND network_dns_zone_id = %s 
                               AND network_dns_zone_origin_id = %s
                               ORDER BY type, rdata""" % (SqlStringOrNull(zone_id),SqlStringOrNull(origin['id']))
      all_records = QueryCMDB(sql_get_all_records)

      # if the query returned something
      if all_records:

        # for each record
        for record in all_records:

          # Make sure we don't have an empty field
          valid_data = CheckData(record)

          # if nothing is missing for this record
          if valid_data:

            # if somehow we don't have a ttl, use the global
            if not record['ttl']:
              record['ttl'] = global_ttl

            # deal with tab
            if len(record['record_name']) < 8:
              if global_ttl == record['ttl']:
                first_tab = '\t\t\t\t'
              else:
                first_tab = '\t\t\t'
            elif len(record['record_name']) < 16:
              if global_ttl == record['ttl']:
                first_tab = '\t\t\t'
              else:
                first_tab = '\t\t'
            elif len(record['record_name']) < 24:
              if global_ttl == record['ttl']:
                first_tab = '\t\t'
              else:
                first_tab = '\t'
            else:
              first_tab = '\t'

            # if local ttl is the same than global ttl, we don't print it
            if global_ttl == record['ttl']:
              print record['record_name'] + first_tab + record['class'] + '\t' + record['type'] + '\t' + record['rdata'] 
            else:
              print record['record_name'] + first_tab + record['ttl'] + '\t' + record['class'] + '\t' + record['type'] + '\t' + record['rdata'] 

          else:
            Log("Skipping the following record: %s." % (record), logging.WARN)
            continue

      else:
        Log("No record using ORIGIN = %s for: %s" % (origin['name'],zone_name), logging.WARN)

  else:
    Log("No record found beside a TTL and the SOA for: %s" % zone_name, logging.WARN)

  # return zone_data



def GetTTL(zone_id,zone_name):
  """ with a zone_id, go and get its global TTL

  Args:
    zone ID
    zone Name

  Returns: TTL line
  """
  
  # variable
  final_ttl = ''

  # query
  sql_get_ttl = "SELECT * FROM network_dns_zone WHERE id = %s" % SqlStringOrNull(zone_id)
  get_ttl = QueryCMDB(sql_get_ttl)

  # if the query returned something
  if get_ttl:

    get_ttl = get_ttl[0]

    # make sure the field is not empty
    if get_ttl['ttl']:
      final_ttl = get_ttl['ttl']

  # if we didn't find any ttl, search in the includes
  if not final_ttl:

    # check if the zone we're working on is included in an other zone
    sql_check_zone_is_included = "SELECT * FROM network_dns_zone WHERE include_list LIKE %s" % SqlStringOrNull('%\"' + zone_name + '\"%')
    check_zone_is_included = QueryCMDB(sql_check_zone_is_included)
    
    # if the zone is included in an other zone
    if check_zone_is_included:
      check_zone_is_included = check_zone_is_included[0]

      # retry to get an TTL
      final_ttl = GetTTL(check_zone_is_included['id'],check_zone_is_included['name'])

    # check if there is an include in that zone
    else:

      # get the include list for the zone we're working on
      sql_check_zone_has_includes = "SELECT * FROM network_dns_zone WHERE id = %s" % SqlStringOrNull(zone_id)
      check_zone_has_includes = QueryCMDB(sql_check_zone_has_includes)

      # if the include list is not empty
      if check_zone_has_includes[0]['include_list']:

        # explore each entry in this list
        for entry in json.loads(check_zone_has_includes[0]['include_list']):
          
          # for the entry we're working on, try to find its data
          sql_include_data = "SELECT * FROM network_dns_zone WHERE name = %s" % SqlStringOrNull(entry)
          include_data = QueryCMDB(sql_include_data)

          # if we find data
          if include_data:
            include_data = include_data[0]

            # try to retrieve the TTL of the entry we're working on
            final_ttl = GetTTL(include_data['id'],include_data['name'])

            # once we get the TTL, we just leave
            # as the include_list is a list of include and they appear in the same order than in the file
            if final_ttl:
              break

  
  return final_ttl


def GetSOA(zone_id,zone_name):
  """ With a zone id, go and gets its SOA configuration

  Args:
    zone ID
    zone Name

  Returns: SOA line
  """

  # variable
  final_soa = ''

  # query
  sql_get_soa = """SELECT ndz.name AS zone_name, ndzo.name AS origin, ndrc.name AS class, ndrt.name AS type, ndzs.ttl, ndzs.primary_name_server, ndzs.responsible_party, ndzs.serial, ndzs.refresh, ndzs.retry, ndzs.expire, ndzs.minimum
                   FROM network_dns_zone_record_soa ndzs, network_dns_zone ndz, network_dns_zone_origin ndzo, network_dns_record_class ndrc, network_dns_record_type ndrt
                   WHERE ndzs.network_dns_zone_id = ndz.id
                   AND ndzs.network_dns_zone_origin_id = ndzo.id
                   AND ndzs.network_dns_zone_id = ndzo.network_dns_zone_id
                   AND ndzs.network_dns_record_class_id = ndrc.id
                   AND ndzs.network_dns_record_type_id = ndrt.id
                   AND ndz.id = %s""" % SqlStringOrNull(zone_id)
  get_soa = QueryCMDB(sql_get_soa)

  # make sure we got an SOA
  if get_soa:

    # only one line should be returned anyway
    get_soa = get_soa[0]

    # make sure we don't have any empty field
    valid_data = CheckData(get_soa)

    if valid_data:
      final_soa = get_soa['origin'] + ' ' + get_soa['ttl'] + ' ' + get_soa['class'] + ' ' + get_soa['type'] + ' ' + get_soa['primary_name_server'] + ' ' + get_soa['responsible_party'] + ' ' + str(get_soa['serial']) + ' ' + get_soa['refresh'] + ' ' + get_soa['retry'] + ' ' + get_soa['expire'] + ' ' + get_soa['minimum']

    else:
      return None

  # if we didn't find anything on the first path
  else:

    # check if the zone we're working on is included in an other zone
    sql_check_zone_is_included = "SELECT * FROM network_dns_zone WHERE include_list LIKE %s" % SqlStringOrNull('%\"' + zone_name + '\"%')
    check_zone_is_included = QueryCMDB(sql_check_zone_is_included)
    
    # if the zone is included in an other zone
    if check_zone_is_included:
      check_zone_is_included = check_zone_is_included[0]

      # retry to get an SOA
      final_soa = GetSOA(check_zone_is_included['id'],check_zone_is_included['name'])

    # check if there is an include in that zone
    else:

      # get the include list for the zone we're working on
      sql_check_zone_has_includes = "SELECT * FROM network_dns_zone WHERE id = %s" % SqlStringOrNull(zone_id)
      check_zone_has_includes = QueryCMDB(sql_check_zone_has_includes)

      # if the include list is not empty
      if check_zone_has_includes[0]['include_list']:

        # explore each entry in this list
        for entry in json.loads(check_zone_has_includes[0]['include_list']):
          
          # for the entry we're working on, try to find its data
          sql_include_data = "SELECT * FROM network_dns_zone WHERE name = %s" % SqlStringOrNull(entry)
          include_data = QueryCMDB(sql_include_data)

          # if we find data
          if include_data:
            include_data = include_data[0]

            # try to retrieve the SOA of the entry we're working on
            final_soa = GetSOA(include_data['id'],include_data['name'])

            # once we get an SOA, we just leave
            # as the include_list is a list of include and they appear in the same order than in the file
            if final_soa:
              break

  
  return final_soa


def Usage(error=None, perform_sys_exit=True):
  """ Basic usage """

  # If we are going to print usage and (maybe) exit...
  if error:
    print '\nERROR: %s' % error
    status_code = 1
  else:
    status_code = 0

  # the nicely formatted usage message
  print '\nUSAGE: %s -h <host>' % sys.argv[0]

  print '  -h, --host            The host you want to run the script against'
  print '  -e, --environment     The environment you want to run the script against'
  print '  -l, --location        The location you want to run the script against'
  print '  -z, --zone            The zone name you want to run the script against'
  print '  -?, --help            Usage\n'


  # If we want to exit, do so
  if perform_sys_exit:
    sys.exit(status_code)


def Main(args=None):
  """Main function

  Args:
    -

  Returns: None
  """

  # Logs
  # SetupLogger('/var/log/cmdb/database/discoverers.log')

  if not args:
    args = []

  # Variables
  zone_name = ''
  host = ''
  environment = ''
  location = ''

  # get options
  long_options = ['help', 'host=', 'environment=', 'location=', 'zone=']

  try:
    (options, args) = getopt.getopt(args, '?h:e:l:z:', long_options)
  except getopt.GetoptError, err:
    Usage(err)

  # Process out CLI options
  for (option, value) in options:
    # Help
    if option in ('-?', '--help'):
      Usage()

    # Define which host
    elif option in ('-h', '--host'):
      if (value != '' and not value.startswith('-')):
        host = value

    # Define the environment
    elif option in ('-e', '--environment'):
      if (value != '' and not value.startswith('-')):
        environment = value

    # Define the location
    elif option in ('-l', '--location'):
      if (value != '' and not value.startswith('-')):
        location = value

    # Define the location
    elif option in ('-t', '--zone'):
      if (value != '' and not value.startswith('-')):
        zone_name = value

  # Query to get the zone infos
  sql_zone_list = """SELECT ndz.* 
                     FROM network_dns_zone ndz, machine m, location l, environment e, location_environment le 
                     WHERE ndz.machine_id = m.id
                     AND m.environment_id = e.id 
                     AND m.location_id = l.id 
                     AND le.location_id = m.location_id 
                     AND le.environment_id = m.environment_id"""

  # if we have a zone name provided
  if zone_name:
    sql_zone_list  += " AND ndz.name = %s" % SqlStringOrNull(zone_name)

  # if we have an host provided
  if host:
    sql_zone_list  += " AND m.hostname = %s" % SqlStringOrNull(host)

  # if we have an env
  if environment:
    sql_zone_list  += " AND e.name = %s" % SqlStringOrNull(environment)

  # if we have a location
  if location:
    sql_zone_list  += " AND l.name = %s" % SqlStringOrNull(location)

  # execute the query
  zone_list = QueryCMDB(sql_zone_list)

  # make sure we've got a result
  if not zone_list:
    Log("The following query didn't return anything - %s." % sql_zone_list, logging.ERROR)

  else:

    # for each zone returned by the query
    for zone in zone_list:

      zone_data = []

      # make sure the zone is in use.
      if zone['in_use'] == 1:

        # logging
        Log('Generating configuration file for the following zone: %s' % zone['name'])

        # Functions
        GenerateRecords(zone['id'],zone['name'])

      else:
        Log("Skipping - %s . This zone is tagged as 'not in use'." % zone['name'], logging.WARN)



if __name__ == '__main__':
  Main(sys.argv[1:])
