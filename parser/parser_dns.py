#!/usr/bin/env python
"""
author: alexis
email: alexisbezard@gmail.com
project: 
"""

"""
Parses DNS configuration files and put the data into a Database or in a JSON file.

TODO:
  - Improve how I handle SRV records.
"""

import datetime
import logging
import os
import getopt
import re
import json
import glob
import sys

from os import path
sys.path.append( path.dirname( path.dirname( path.abspath(__file__) ) ) )

from utility.query import QueryCMDB, SqlStringOrNull, SanitizeSQL
from utility.logger import *

# Default global path
# Where the zone directories are
CONF_PATH = '/opt/cmdb/dns/*'
CONF_PATH_GLOB = '/opt/cmdb/dns'

# JSON Path
OUTPUT_PATH = "../data/dns-json-output/"

# Do we want a JSON output?
JSON_OUTPUT = False


def ProcessFile(filepath,machine_name):
  """ Processes the file and formats the data a first time

  Args:
    filepath
    machine_name

  Returns: formatted data
  """

  # first let's make sure it's a legit DNS configuration file
  with open(filepath, 'r') as f:
    first_line = f.readline()

  # if first line is not correct
  if '$ORIGIN' not in first_line and '$TTL' not in first_line and '$INCLUDE' not in first_line:
    # log
    Log('Skipping - %s does not seem to be a valid DNS file.' % filepath, logging.ERROR)

    # return
    return None


  # open the file and get the data
  data = open(filepath).read()
  
  # logs
  Log("Parsing - %s" % filepath)
  
  # Strip out any comments, and strip() the lines
  lines = []

  # keep track of the current resource record name & last origin
  resource_record_name = ''
  last_origin = ''

  # True when we are processing a multiline element (wrapped in () )
  multiline_key = None

  for line in data.split('\n'):
    
    # if line is not empty
    if line:

      # If we arent doing multiline processing
      if not multiline_key:

        # Skip comments
        if line.startswith(';'):
          continue
        # separate the comments at the end of the line and the semicolon within quotes
        if ';' in line:
          # if we have double quotes in before the first semicolon 
          if '"' in line.split(';')[0]:

            # variables
            temp_line = line.split(';')
            final_line = ''
            semicolon_in_quote_check = False

            # for each part in the splitted line
            for i in temp_line:
              # if we have at least one double quote in the part
              if '"' in i:
                # if modulus of the number of doubles quotes equal 0
                if i.count('"') % 2 == 0:
                  # if we had an odd number of double quote in the previous part
                  if semicolon_in_quote_check:
                    # and if the final line is currently empty
                    if not final_line:
                      # how can you have one single double quote in the previous part and still have an emtpy line
                      Log('How did you get there - %s' % line, logging.WARN)
                    else:
                      # add current to final line
                      final_line = ";".join([final_line, i])
                  # if we didn't have an odd number of double quote in the previous part
                  else:
                    # then turn off the semicolon in quote check
                    semicolon_in_quote_check = False
                    # add the data to the final line and break, we're done here
                    if not final_line:
                      final_line = i
                      break
                    else:
                      final_line = ";".join([final_line, i])
                      break
                # if we have an odd number of double quote
                else:
                  # if we had an odd number of double quote in the previous part
                  if semicolon_in_quote_check:
                    # then we re done, add the data to the final line and break
                    if not final_line:
                      final_line = i
                      break
                    else:
                      final_line = ";".join([final_line, i])
                      break
                  # if we didn't have an odd number of double quote in the previous part
                  else:
                    semicolon_in_quote_check = True
                    if not final_line:
                      final_line = i
                    else:
                      final_line = ";".join([final_line, i])
              # if we don't have a quote in that part
              else:
                if not final_line:
                  final_line = i
                else:
                  final_line = ";".join([final_line, i])
          # if we don't have a quote in the line
          else:
            line = line.split(';')[0]
        
        # deal with an empty/@ resource record name
        if re.match(r'[ \t]', line):
          line = resource_record_name + ' ' + line[1:]
        # if line starts with @
        elif line.startswith('@'):
          line = line.replace('@',last_origin)
        # if line starts with $
        elif line.startswith('$'):
          # if it's an ORIGIN, store it
          if line.startswith('$ORIGIN'):
            resource_record_name = line.split(' ')[1]
            last_origin = line.split(' ')[1]
        else:
          line = line.strip()
          resource_record_name = line[0]

        # if we find a parenthese in the line
        if '(' in line and ')' not in line:
          multiline_key = line
        else:
          line = line.strip()
          lines.append(line)
      
      # Else, multiline processing
      else:

        # Skip comments
        if line.startswith(';'):
          continue
        # Skip comments at the end of the line
        if ';' in line:
          line = line.split(';')[0]
          # line = line.strip()

        # add the line to the multikey string
        multiline_key += ' ' + line

        # If this is the closing line
        if ')' in line:
          lines.append(multiline_key)
          multiline_key = None

  # return result
  return lines



def ProcessData(machine_name,zone,results):
  """Populates the raw table

  Args:
    

  Returns: None
  """
  
  # dictionnary
  zone_dict = {}
  zone_dict[zone] = {}
  include_list = []
  record_list = []

  # default origin
  current_origin = ''

  # store previous class
  previous_class = ''

  # default ttl
  zone_dict[zone]['$TTL'] = ''

  # for each line in the DNS file
  for item in results:

    # reset variable
    formatted_line = ''
    line = []
    temp_entry = ''

    item = item.strip()
    # line = item.split()

    # By default the double quote check
    double_quotes_check = False

    # we need to format the splitted to handle the double quotes
    for i in item.split():
      # if the string starts with quote
      if i.startswith('"'):
        double_quotes_check = True
      # if we have a quote opened
      if double_quotes_check:
        temp_entry = " ".join([temp_entry, i])
        # if the string ends with quote
        if i.endswith('"'):
          double_quotes_check = False
          line.append(temp_entry.strip())
          # reset our temp_entry variable
          temp_entry = ''
      else:
        line.append(i)
    # if the line is not empty
    if item and len(line) >= 2:
      
      # handle the INCLUDE
      if line[0] == '$INCLUDE':
        include_list.append(line[-1].replace('"',''))

      # get the most recent ORIGIN
      elif line[0] == '$ORIGIN':
        current_origin = line[1]

      # handle the TTL
      elif line[0] == '$TTL':
        zone_dict[zone]['$TTL'] = line[1]

      # handle the GENERATE thing specific to BIND
      elif line[0] == '$GENERATE':
        
        # default
        generate_range = line[1]
        generate_lhs = line[2]

        # if the line is properly formatted
        if len(line) == 6:
          generate_class = line[3]
          generate_type = line[4]
          generate_rhs = line[5]
        # if length == 5 we assume we're just missing the record class
        elif len(line) == 5:
          generate_class = None
          generate_type = line[3]
          generate_rhs = line[4]
        # else ignore
        else:
          Log('Skipping - \"%s\" \'. $GENERATE DOES NOT SEEM PROPERLY FORMATTED.' % (item), logging.WARN)
          continue

        # deal with the range step
        if "/" in generate_range:
          generate_range_step = generate_range.split('/')[1]
          generate_range = generate_range.split('/')[0]
        else:
          generate_range_step = 1

        # deal with the lhs
        if '{' in generate_lhs and '}' in generate_lhs:
          generate_lhs_params = re.search(r"\{(.+)\}", generate_lhs).group(1)
          generate_lhs = generate_lhs.split('{')[0]

          # if not a decimal, we don't handle it yet
          if generate_lhs_params.split(',')[2] != 'd':
            Log('Skipping - \"%s\" \'. $GENERATE HAS AN UNKNOWN TYPE IN ITS LHS SPECIFIER: %s.' % (item, generate_lhs_params.split(',')[2]), logging.WARN)
            continue

          generate_lhs_params_offset = int(generate_lhs_params.split(',')[0])
          generate_lhs_params_width = int(generate_lhs_params.split(',')[1])
        # else give default values
        else:
          generate_lhs_params_offset = 0
          generate_lhs_params_width = 1

        # deal with the rhs
        if '{' in generate_rhs and '}' in generate_rhs:
          generate_rhs_params = re.search(r"\{(.+)\}", generate_rhs).group(1)
          generate_rhs = generate_rhs.split('{')[0]
          
          # if not a decimal, we don't handle it yet
          if generate_rhs_params.split(',')[2] != 'd':
            Log('Skipping - \"%s\" \'. $GENERATE HAS AN UNKNOWN TYPE IN ITS RHS SPECIFIER: %s.' % (item, generate_rhs_params.split(',')[2]), logging.WARN)
            continue

          generate_rhs_params_offset = int(generate_rhs_params.split(',')[0])
          generate_rhs_params_width = int(generate_rhs_params.split(',')[1])
        # else give default values
        else:
          generate_rhs_params_offset = 0
          generate_rhs_params_width = 1

        # for each entry that would be generated by the GENERATE // Have to do '+1' ro handle the flaw in the range function
        for iteration in range(int(generate_range.split('-')[0]), int(generate_range.split('-')[1]) + 1, int(generate_range_step)):
          
          # reset
          generate_line = []

          # define the iterator value for lhs
          lhs_iterator_value = str(iteration - generate_lhs_params_offset)
          if len(lhs_iterator_value) < generate_lhs_params_width:
            
            for i in range(0, generate_lhs_params_width - len(lhs_iterator_value)):
              lhs_iterator_value = str(0) + lhs_iterator_value

          # define the iterator value for rhs
          rhs_iterator_value = str(iteration - generate_rhs_params_offset)
          if len(rhs_iterator_value) < generate_rhs_params_width:
            
            for i in range(0, generate_rhs_params_width - len(rhs_iterator_value)):
              rhs_iterator_value = str(0) + rhs_iterator_value

          # print  generate_lhs.replace('$', lhs_iterator_value) + ' ' + generate_class + ' ' + generate_type + ' ' + generate_rhs.replace('$', rhs_iterator_value)
          # generate our line
          generate_line.append(generate_lhs.replace('$', lhs_iterator_value))
          if generate_class:
            generate_line.append(generate_class)
          generate_line.append(generate_type)
          generate_line.append(generate_rhs.replace('$', rhs_iterator_value))

          # process the line
          formatted_line = ProcessLine(generate_line,current_origin,previous_class,zone_dict[zone]['$TTL'])
          
          # if we got a valid return
          if formatted_line:
            record_list.append(formatted_line)

            # Get the value of the last class
            for (name, record) in formatted_line.items():
              for (entry, value) in record.items():
                if entry == 'class':
                  previous_class = value

      # if line has a $ but is not INCLUDE/TTL/ORIGIN
      elif '$' in line[0]:
        Log('Skipping - \"%s\" \'. FORMAT NOT SUPPORTED.' % item, logging.WARN)
        continue

      # otherwise process line
      elif len(line) >= 3:
        formatted_line = ProcessLine(line,current_origin,previous_class,zone_dict[zone]['$TTL'])
        
        # if we got a valid return
        if formatted_line:
          record_list.append(formatted_line)

          # Get the value of the last class
          for (name, record) in formatted_line.items():
            for (entry, value) in record.items():
              if entry == 'class':
                previous_class = value

      else:
        Log('Skipping - \"%s\" \'. FORMAT NOT SUPPORTED.' % item, logging.WARN)
        continue        


  # if we found includes in the DNS file
  if include_list:
    zone_dict[zone]['$INCLUDE'] = include_list

  # if we have records 
  zone_dict[zone]['RECORDS'] = record_list

  # if we don't want to just output the data in JSON format
  if not JSON_OUTPUT:

    # Put the RAW Data in the DB
    sql_raw_data = "SELECT * FROM raw_network_dns_configuration WHERE hostname = %s AND zone = %s" % (SqlStringOrNull(machine_name),SqlStringOrNull(zone))
    raw_data = QueryCMDB(sql_raw_data)

    # format JSON data
    value_json = json.dumps(zone_dict, sort_keys=True)

    # if an entry already exists
    if raw_data:
      raw_data = raw_data[0]
    
      # check if there was an update
      if (SqlStringOrNull(raw_data['data_json']) != SqlStringOrNull(value_json)):

        Log('UPDATE / host: %s - zone: %s' % (machine_name, zone))

        sql_update = """UPDATE raw_network_dns_configuration
                        SET processed = 0, updated = NOW(), data_json = %s 
                        WHERE id = %s""" % (SqlStringOrNull(value_json), SqlStringOrNull(raw_data['id']))
        QueryCMDB(sql_update)

    else:
      Log('INSERT / host: %s - zone: %s' % (machine_name, zone))

      sql_insert = """INSERT INTO raw_network_dns_configuration
                      (hostname, zone, data_json, processed, created) 
                      VALUES (%s, %s, %s, 0, NOW())""" % (SqlStringOrNull(machine_name), SqlStringOrNull(zone), SqlStringOrNull(value_json))
      QueryCMDB(sql_insert)

  # else if we want JSON format data
  else:
    # Open and dump JSON file
    with open(OUTPUT_PATH + machine_name + '_' + zone + '.json' , 'w') as outfile:
      json.dump(zone_dict, outfile)


def ProcessLine(line,last_origin,last_class,global_ttl):
  """ Process line

  Args:
    line
    last_origin
    last_class
    global_ttl
    

  Returns: Dictionary or None
  """

  # define variables
  final_class = ''
  final_type = ''
  final_name = ''

  # local dictionnary
  record_dict = {}

  # get all the different record types
  sql_record_types = "SELECT * FROM network_dns_record_type"
  record_types = QueryCMDB(sql_record_types)

  # get all the different record classes 
  sql_record_classes = "SELECT * FROM network_dns_record_class"
  record_classes = QueryCMDB(sql_record_classes)
  
  # find out with which record type we are working with
  for item in line:
    for record_type in record_types:
      if item == record_type['name']:
        final_type = item
    for record_class in record_classes:
      if item == record_class['name']:
        final_class = item

  # make sure we have a valid type
  if final_type:
    # get name
    final_name = line[0]

    # if SOA record
    if final_type == 'SOA':
      if len(line) == 13:

        # dict
        record_dict[final_name] = {}
        record_dict[final_name]['origin'] = line[0]
        record_dict[final_name]['ttl'] = line[1]
        record_dict[final_name]['class'] = line[2]
        record_dict[final_name]['type'] = line[3]
        record_dict[final_name]['primary_name_server'] = line[4]
        record_dict[final_name]['responsible_party'] = line[5]
        record_dict[final_name]['serial'] = line[7]
        record_dict[final_name]['refresh'] = line[8]
        record_dict[final_name]['retry'] = line[9]
        record_dict[final_name]['expire'] = line[10]
        record_dict[final_name]['minimum'] = line[11]

    # if not SOA, we support A / CNAME / NS record
    elif final_type == 'A' or final_type == 'CNAME' or final_type == 'NS' or final_type == 'TXT':
      record_dict[final_name] = {}
      record_dict[final_name]['origin'] = last_origin
      record_dict[final_name]['type'] = final_type
      record_dict[final_name]['rdata'] = line[-1]

      # if length = 3 we know we are missing the TTL and the class
      if len(line) == 3:
        record_dict[final_name]['ttl'] = global_ttl
        record_dict[final_name]['class'] = last_class

      # if length = 4 we know we are missing the TTL or the class
      elif len(line) == 4:
        if final_class:
          record_dict[final_name]['ttl'] = global_ttl
          record_dict[final_name]['class'] = final_class
        else:
          record_dict[final_name]['ttl'] = line[1]
          record_dict[final_name]['class'] = last_class

      # if length = 5 we are not missing anything
      elif len(line) == 5:
        record_dict[final_name]['ttl'] = line[1]
        record_dict[final_name]['class'] = final_class

      else:
        Log('Skipping - \"%s\". NOT PROPERLY FORMATTED. NUMBER OF ENTRIES IN THE LINE = %s' % (line,len(line)), logging.WARN)
        return None
      
    # handle SRV records
    elif final_type == 'SRV':
      # if we have a properly formatted SRV record
      if len(line) == 8:
        record_dict[final_name] = {}
        record_dict[final_name]['origin'] = last_origin
        record_dict[final_name]['type'] = final_type
        record_dict[final_name]['ttl'] = line[1]
        record_dict[final_name]['class'] = final_class
        record_dict[final_name]['rdata'] = line[-4] + " " + line[-3] + " " + line[-2] + " " + line[-1]
      else:
        Log('Skipping - \"%s\". SRV RECORD NOT PROPERLY FORMATTED. NUMBER OF ENTRIES IN THE LINE = %s' % (line,len(line)), logging.WARN)
        return None   
                                                                
    # handle the MX records
    elif final_type == 'MX':
      record_dict[final_name] = {}
      record_dict[final_name]['origin'] = last_origin
      record_dict[final_name]['type'] = final_type
      
      # if length of line == 6
      if len(line) == 6:
        # rdata receives join of the 2 last columns
        record_dict[final_name]['rdata'] = " ".join([line[-2], line[-1]])
        record_dict[final_name]['ttl'] = line[1]
        record_dict[final_name]['class'] = final_class

      # if len is not 6, we need to figure out if we are missing the ttl, the class or the priority
      elif len(line) == 5:
        # if we are missing the class, use the one from the previous line
        if not final_class:
          record_dict[final_name]['class'] = last_class
          record_dict[final_name]['rdata'] = " ".join([line[-2], line[-1]])
          record_dict[final_name]['ttl'] = line[1]

        # else are we missing the ttl or the priority
        else:
          # let's get the position of the final_type
          # if position == 2 then we're missing the ttl
          if line.index(final_type) == 2:
            record_dict[final_name]['class'] = final_class
            record_dict[final_name]['ttl'] = global_ttl
            record_dict[final_name]['rdata'] = " ".join([line[-2], line[-1]])
            
          # else we're missing the priority and don't handle it
          else:
            Log('Skipping - \"%s\". THIS MX RECORD DOES NOT HAVE A PRIORITY. NOT SUPPORTED.' % line, logging.WARN)
            return None

      else:
        Log('Skipping - \"%s\". THIS MX RECORD FORMAT IS NOT SUPPORTED YET.' % line, logging.WARN)
        return None
        
    else:
      Log('Skipping - \"%s\". RECORD TYPE NOT SUPPORTED YET.' % line, logging.WARN)
      return None
    
  else:
    Log('Skipping - \"%s\". NO VALID RECORD TYPE FOUND.' % line, logging.WARN)
    return None

  if record_dict:
    if (len(record_dict[final_name]) == 5) or (len(record_dict[final_name]) == 11 and final_type == 'SOA'):
      return record_dict
    else:
      Log('Skipping - \"%s\". PROBLEM WHILE PARSING THIS LINE.' % line, logging.WARN)
      return None
  else:
    Log('Skipping - \"%s\". PROBLEM WHILE PARSING THIS LINE.' % line, logging.WARN)
    return None


def CheckHostname(fqdn):
  """ Takes an fqdn and returns its id or null

  Args:
    hostname

  Returns: machine id or null
  """

  # get the hostname by splitting the FQDN
  hostname = fqdn.split('.')[0]

  machine_id = ''

  sql_get_machine_id = """SELECT m.id, m.hostname, e.name as environment, l.name as location, le.domain 
                        FROM machine m, location l, environment e, location_environment le
                        WHERE m.location_id = l.id
                        AND m.environment_id = e.id
                        AND le.location_id = l.id
                        AND le.environment_id = e.id
                        AND m.hostname = %s""" % SqlStringOrNull(hostname)
  get_machine_id = QueryCMDB(sql_get_machine_id)

  for entry in get_machine_id:
    if (entry['hostname'] + '.' + entry['environment'] + '.' + entry['location'] + '.' + entry['domain'] == fqdn) or (entry['hostname'] + '.' + entry['location'] + '.' + entry['domain'] == fqdn):
      machine_id = entry['id']

  if machine_id:
    return machine_id
  else:
    return None



def ImportRawDNSConfiguration(machine_id,zone,data):
  """ Imports the RAW data

  Args:
    machine_id
    zone
    data

  Returns: None
  """

  # variables
  valid_record_list = []
  include_list = []
  global_ttl = ''
  records = []

  # Spread the data
  for (key, value) in data[zone].items():
    if key == '$TTL':
      global_ttl = value
    elif key == '$INCLUDE':
      include_list = json.dumps(value)
    elif key == 'RECORDS':
      records = value


  # first deal with the zone
  sql_zone_data = "SELECT * FROM network_dns_zone WHERE name = %s and machine_id = %s" % (SqlStringOrNull(zone), SqlStringOrNull(machine_id))
  zone_data = QueryCMDB(sql_zone_data)

  # if we already have an entry, update
  if zone_data:
    zone_data = zone_data[0]

    # if zone tagged as not in used, then skip it
    if zone_data['in_use'] == 0:
      Log('Skipping import for - %s. This zone is apparently not in use anymore.' % zone, logging.WARN)
      return False
    else:
      # get dns_zone_id
      dns_zone_id = zone_data['id']

      if (zone_data['ttl'] != global_ttl) or (zone_data['include_list'] != include_list):
        sql_zone_update = "UPDATE network_dns_zone SET "

        if global_ttl:
          sql_zone_update += "ttl = %s, " % (SqlStringOrNull(global_ttl))

        if include_list:
          sql_zone_update += "include_list = %s, " % (SqlStringOrNull(include_list))


        sql_zone_update += " updated = NOW() WHERE id = %s" % (SqlStringOrNull(zone_data['id']))
        QueryCMDB(sql_zone_update)


  # else insert
  else:

    sql_zone_insert = "INSERT INTO network_dns_zone (name, machine_id, ttl, include_list, created) "
    if ttl:
      sql_zone_insert += "VALUES (%s, %s, %s," % (SqlStringOrNull(zone), SqlStringOrNull(machine_id),SqlStringOrNull(global_ttl))
    else:
      sql_zone_insert += "VALUES (%s, %s, NULL," %  (SqlStringOrNull(zone), SqlStringOrNull(machine_id))
    if include_list:
      sql_zone_insert += " %s, NOW())" % (SqlStringOrNull(include_list))
    else:
      sql_zone_insert += " NULL, NOW())"

    # get the dns_zone_id
    dns_zone_id = QueryCMDB(sql_zone_insert)
  
  
  # time to explore the records
  for record in records:
    for name in record:
      
      # reset origin_id
      origin_id = None
      
      # SanitizeData
      name = name.encode("ascii","replace")
      for entry in record[name]:
        entry = entry.encode("ascii","replace")
        if not record[name][entry]:
          record[name][entry] = None

      # grab the origin ID
      if record[name]['origin']:
        origin_id = HandleOriginID(dns_zone_id,record[name]['origin'])
          
      # get class ID
      sql_get_class_id = "SELECT id FROM network_dns_record_class WHERE name = %s" % SqlStringOrNull(record[name]['class'])
      get_class_id = QueryCMDB(sql_get_class_id)

      if get_class_id:
        class_id = get_class_id[0]['id']
      else:
        Log('Skipping - %s. UNABLE TO FIND A CLASS ID.' % record, logging.WARN)
        continue

      # get type ID
      sql_get_type_id = "SELECT id FROM network_dns_record_type WHERE name = %s" % SqlStringOrNull(record[name]['type'])
      get_type_id = QueryCMDB(sql_get_type_id)

      if get_type_id:
        type_id = get_type_id[0]['id']
      else:
        Log('Skipping - %s. UNABLE TO FIND A TYPE ID.' % record, logging.WARN)
        continue


      # if SOA record
      if record[name]['type'] == 'SOA':
        zone_soa = ''

        # check if we already have an SOA for this zone
        sql_zone_soa = "SELECT * FROM network_dns_zone_record_soa WHERE network_dns_zone_id = %s" % SqlStringOrNull(dns_zone_id)
        zone_soa = QueryCMDB(sql_zone_soa)
 
        # if it already exists, update
        if zone_soa:
          zone_soa = zone_soa[0]
          
          sql_update_zone_soa = """UPDATE network_dns_zone_record_soa
                                   SET network_dns_zone_origin_id = %s, network_dns_record_class_id = %s, network_dns_record_type_id = %s, ttl = %s, primary_name_server = %s, responsible_party = %s, serial = %s, refresh = %s, retry = %s, expire = %s, minimum = %s, updated = NOW()
                                   WHERE id = %s""" % (SqlStringOrNull(origin_id), SqlStringOrNull(class_id), SqlStringOrNull(type_id), SqlStringOrNull(record[name]['ttl']), SqlStringOrNull(record[name]['primary_name_server']), SqlStringOrNull(record[name]['responsible_party']), SqlStringOrNull(record[name]['serial']), SqlStringOrNull(record[name]['refresh']), SqlStringOrNull(record[name]['retry']), SqlStringOrNull(record[name]['expire']), SqlStringOrNull(record[name]['minimum']), SqlStringOrNull(zone_soa['id']))
          QueryCMDB(sql_update_zone_soa)

        else:
          sql_insert_zone_soa = """INSERT INTO network_dns_zone_record_soa
                                   (network_dns_record_class_id, network_dns_zone_origin_id, network_dns_record_type_id, network_dns_zone_id, ttl, primary_name_server, responsible_party, serial, refresh, retry, expire, minimum, created) 
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())""" % (SqlStringOrNull(class_id), SqlStringOrNull(origin_id), SqlStringOrNull(type_id), SqlStringOrNull(dns_zone_id), SqlStringOrNull(record[name]['ttl']), SqlStringOrNull(record[name]['primary_name_server']), SqlStringOrNull(record[name]['responsible_party']), SqlStringOrNull(record[name]['serial']), SqlStringOrNull(record[name]['refresh']), SqlStringOrNull(record[name]['retry']), SqlStringOrNull(record[name]['expire']), SqlStringOrNull(record[name]['minimum']))
          QueryCMDB(sql_insert_zone_soa)
 
      # if not a SOA record, insert it in the regular record table
      else:
      
        # Put ttl = NULL if current ttl = global_ttl
        if global_ttl == record[name]['ttl']:
          record[name]['ttl'] = None
          
        # instanciate variables
        zone_record = ''

        # check if we already have this record
        sql_zone_record = """SELECT * 
                             FROM network_dns_zone_record 
                             WHERE network_dns_zone_id = %s
                             AND network_dns_record_class_id = %s
                             AND network_dns_record_type_id = %s
                             AND name = %s
                             AND rdata = %s 
                             AND network_dns_zone_origin_id = %s """ % (SqlStringOrNull(dns_zone_id), SqlStringOrNull(class_id), SqlStringOrNull(type_id), SqlStringOrNull(name), SqlStringOrNull(record[name]['rdata']),SqlStringOrNull(origin_id))
        zone_record = QueryCMDB(sql_zone_record)

        # if we found an entry for the select
        if zone_record:
          zone_record = zone_record[0]

          # add it to the valid record list
          valid_record_list.append(zone_record['id'])

          sql_update_zone_record = """UPDATE network_dns_zone_record
                                   SET ttl = %s, network_dns_zone_origin_id = %s, rdata = %s, updated = NOW()
                                   WHERE id = %s""" % (SqlStringOrNull(record[name]['ttl']), SqlStringOrNull(origin_id), SqlStringOrNull(record[name]['rdata']), SqlStringOrNull(zone_record['id']))
          QueryCMDB(sql_update_zone_record)

        else:
          sql_insert_zone_record = """INSERT INTO network_dns_zone_record
                                   (network_dns_zone_id, name, network_dns_zone_origin_id, ttl, network_dns_record_type_id, network_dns_record_class_id, rdata, created) 
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())""" % (SqlStringOrNull(dns_zone_id), SqlStringOrNull(name), SqlStringOrNull(origin_id), SqlStringOrNull(record[name]['ttl']), SqlStringOrNull(type_id), SqlStringOrNull(class_id), SqlStringOrNull(record[name]['rdata']))
          insert_zone_record = QueryCMDB(sql_insert_zone_record)

          # add it to the valid record list
          valid_record_list.append(insert_zone_record)

  # Clean the network_dns_zone_record table up
  if dns_zone_id:
    sql_cleanup = "SELECT id FROM network_dns_zone_record WHERE network_dns_zone_id = %s" % SqlStringOrNull(dns_zone_id)
    ClearTable(valid_record_list,sql_cleanup,'network_dns_zone_record')
  else:
    Log('No DNS Zone ID found - Can\'t clean up.', logging.WARN)

  return True


def HandleOriginID(zone_id,origin):
  """ Provide the zone id and the origin name and returns the origin id

  Args:
    zone id
    origin name
    

  Returns: origin ID
  """

  # check if the entry already exists
  sql_check_origin = "SELECT id FROM network_dns_zone_origin WHERE network_dns_zone_id = %s AND name = %s" % (SqlStringOrNull(zone_id),SqlStringOrNull(origin))
  check_origin = QueryCMDB(sql_check_origin)

  # if the entry already exists
  if check_origin:
    check_origin = check_origin[0]
    return check_origin['id']

  else:
    sql_insert_origin = """INSERT INTO network_dns_zone_origin
                         (network_dns_zone_id, name)
                         VALUES (%s, %s)""" % (SqlStringOrNull(zone_id), SqlStringOrNull(origin))
    origin_id = QueryCMDB(sql_insert_origin)
    return origin_id
    
          
def ClearTable(valid_id_list,sql_cleanup,table):
  """ Clear a specified table in CMDB based on an id list

  Args:
    valid_id_list
    sql_cleanup
    table

  Returns: None
  """
  
  # get all the ids living in the table
  all_ids = QueryCMDB(sql_cleanup)

  # explore all the ids
  for item in all_ids:
    if item['id'] not in valid_id_list:

      Log('DELETE / table: %s - id: %s' % (table, item['id']))

      # deletion query
      sql_deletion = "DELETE FROM %s WHERE id = %s" % (table, SqlStringOrNull(item['id']))
      QueryCMDB(sql_deletion)

      
def Usage(error=None, perform_sys_exit=True):
  """ Basic usage """

  # If we are going to print usage and (maybe) exit...
  if error:
    print '\nERROR: %s' % error
    status_code = 1
  else:
    status_code = 0

  # the nicely formatted usage message
  print '\nUSAGE: %s -f <file>' % sys.argv[0]

  print '  -d, --dir             Path of the directory where the files you want to parse live.'
  print '  -f, --file            Path of the file you want to parse.'
  print '  -m, --machine         The DNS server\'s host FQDN. i.e. < dc1infra01.dc1.fm-hosted | dc1infra01-edns.dc1.fm-hostedl >. If none, will use the dir path to get the hostname'
  print '  --json                Export the dictionnary in a JSON file. Default path : %s' % OUTPUT_PATH
  print '  -?, --help            Usage\n'

  print
  print '  --dir and --file are exclusive.'

  # If we want to exit, do so
  if perform_sys_exit:
    sys.exit(status_code)


def Main(args=None):
  """Main function

  Args:
    None

  Returns: None
  """

  # globals
  global JSON_OUTPUT

  # if no arguments
  if not args:
    args = []

  # logs
  SetupLogger('/var/log/cmdb/database/parsers.log')

  # get options
  long_options = ['help', 'file=', 'path=', 'machine=', 'json',]
  exclusive_options = ''

  try:
    (options, args) = getopt.getopt(args, '?h:f:d:m:', long_options)
  except getopt.GetoptError, err:
    Usage(err)

  # Process out CLI options
  for (option, value) in options:
    # Help
    if option in ('-?', '--help'):
      Usage()

    # Define a file path
    elif option in ('-f', '--file'):
      if (value != '' and not value.startswith('-')):
        file_path = value
        exclusive_options += '-f'

    # Define a dir path
    elif option in ('-d', '--dir'):
      if (value != '' and not value.startswith('-')):
        directory_path = value
        exclusive_options += '-d'

    # Define a type for the dns
    elif option in ('-m', '--machine'):
      if (value != '' and not value.startswith('-')):
        machine_name = value
        exclusive_options += '-m'

    # Define if we output the result in JSON
    elif option in ('--json'):
      JSON_OUTPUT = True


  # handle the options
  if '-f' in exclusive_options and '-d' in exclusive_options:
    Log('You can\'t provide a directory path and a file path in the same command.', logging.ERROR)
    Usage()

  elif '-f' in exclusive_options or '-d' in exclusive_options:

    # if the user didn't provide a server tag
    if '-m' not in exclusive_options:
      machine_name = file_path.split("/")[6]
      Log('No FQDN specified, gonna use the following value found in the directory path: %s' % (machine_name))


    # if file
    if '-f' in exclusive_options:

      # check if the file exists
      if not os.path.isfile(file_path):
        Log('Skipping - %s is not a valid file on this host.' % file_path, logging.ERROR)

      # else parse the file
      else:
        # get zone
        zone = file_path.split("/")[-1]
        
        # process file
        lines = ProcessFile(file_path,machine_name)

        # process the data
        ProcessData(machine_name,zone,lines)

    # if path
    elif '-d' in exclusive_options:

      # list of files
      files = []

      # check if the directory exists
      if not os.path.exists(directory_path):
        Log('Skipping - %s is not a valid directory on this host.' % directory_path, logging.ERROR)

      else:
        entities = os.listdir(directory_path)

        # for all the entities in the directory
        for entity in entities:

          # build file path
          temp_path = ''
          temp_path = os.path.abspath(os.path.join(directory_path, entity))

          # check if it's a file
          if not os.path.isfile(temp_path):
            Log('Skipping - %s is not a file.' % temp_path, logging.WARN)

          else:
            files.append(temp_path)

        # if we don't have files in our list
        if not files:
          Log('Skipping - %s does not have valid file.' % directory_path, logging.ERROR)
        else:
          # Process all the files
          for file_path in files:

            # get zone
            zone = file_path.split("/")[-1]
            
            # process file
            lines = ProcessFile(file_path,machine_name)

            # process the data
            ProcessData(machine_name,zone,lines)
  
  # if we didn't get any file/dir path
  else:
    
    # Get Default path
    paths = glob.glob(CONF_PATH)

    # get all the dirs in the default path
    for path in paths:
      
      # get machine name
      machine_name = path.split('/')[-1]
      files = glob.glob(path + '/*')

      # for each file in the directory
      for file_path in files:

        # get zone
        zone = file_path.split("/")[-1]
        
        # process file
        lines = ProcessFile(file_path,machine_name)

        # process the data
        ProcessData(machine_name,zone,lines)

  if not JSON_OUTPUT:

    # Now let's import the data from the RAW table
    sql = "SELECT * FROM raw_network_dns_configuration WHERE processed = 0"
    items = QueryCMDB(sql)
    
    # Process each item
    for item in items:

      # load json data
      data = json.loads(item['data_json'])
      
      # get the hostname & zone name
      hostname = item['hostname']
      zone = item['zone']

      # get machine id
      machine_id = CheckHostname(hostname)

      if machine_id:

        # log
        Log('IMPORT: host: %s - zone: %s' % (hostname, zone))

        updated = ImportRawDNSConfiguration(machine_id,zone,data)

        # if the zone has been updated and not skipped
        if updated:

          # done processing the entry in the raw table, let's turn processed to 1
          sql_processed = """UPDATE raw_network_dns_configuration
                             SET processed = 1
                             WHERE id = %s""" % SqlStringOrNull(item['id'])
          QueryCMDB(sql_processed)

      else:
        Log('Skipping - %s could not be found in the machine table.' % hostname, logging.WARN)



if __name__ == '__main__':
  Main(sys.argv[1:])
