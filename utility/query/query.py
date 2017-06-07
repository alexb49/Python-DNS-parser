import mysql.connector
import unicodedata

import logging

from utility.logger import Log


# connection info for the cmdb
CMDB_HOST = "DB_HOST"
CMDB_USER = "DB_USER"
CMDB_PASSWD = open('/root/secure/PASSWORD_FILE').read().strip()
CMDB_NAME = "DB_NAME"
CMDB_PORT = "DB_PORT"


def QueryCMDB(sql, data=None):
  """Connect to database and runs mysql statement.

  Args:
    sql (string): mysql statement
    data (dict or list): python formatting of sql string, handles quoting

  Returns: (list of dicts): rows
  """
  global CMDB_USER
  global CMDB_PASSWD
  global CMDB_HOST
  global CMDB_NAME

  conn = mysql.connector.connect(user=CMDB_USER, password=CMDB_PASSWD, host=CMDB_HOST, database=CMDB_NAME)
  cursor = conn.cursor(dictionary=True)
  
  if data == None:
    cursor.execute(sql)
  else:
    print 'SQL: %s  Data: %s' % (sql, data)
    cursor.execute(sql % data)

  if sql.upper().startswith('INSERT'):
    result = cursor.lastrowid
    conn.commit()
  elif sql.upper().startswith('UPDATE') or sql.upper().startswith('DELETE'):
    conn.commit()
    result = None
  elif sql.upper().startswith('SELECT'):
    result = cursor.fetchall()
  else:
    result = None

  cursor.close()
  conn.close()

  return result


def Query(db_user, db_passwd, host, database, sql, data=None):
  """Connect to database and runs mysql statement.

  Args:
    sql (string): mysql statement
    data (dict or list): python formatting of sql string, handles quoting

  Returns: (list of dicts): rows
  """
  # create database connection.
  conn = mysql.connector.connect(user=db_user, password=db_passwd, host=host, database=database)
  cursor = conn.cursor(dictionary=True)

  if data == None:
    # print 'SQL: %s' % sql
    cursor.execute(sql)
  else:
    print 'SQL: %s  Data: %s' % (sql, data)
    cursor.execute(sql, data)

  if sql.upper().startswith('INSERT'):
    result = cursor.lastrowid
    conn.commit()
  elif sql.upper().startswith('UPDATE') or sql.upper().startswith('DELETE'):
    conn.commit()
    result = None
  elif sql.upper().startswith('SELECT'):
    result = cursor.fetchall()
  else:
    result = None

  cursor.close()
  conn.close()

  return result


def SanitizeSQL(text):
  """Simple SQL santization

  Args:
    text (string): parses string for single quotes.

  Raises: 
    UnicodeEncodeError

  Returns: (string): with no single quotes creating valid mysql string.
  """
  if text == None:
    text = 'NULL'
  else:
    try:
      text = str(text)
      
    except UnicodeEncodeError, e:
      text = str(text.decode('ascii', 'ignore'))
  
  return text.replace("'", "''").replace('\\', '\\\\')

def SqlStringOrNull(value):
    """Sanatized or NULL

    Args:
      value (string): input

    Returns: SQL quoted ('') and sanitized string or an unquoted NULL to go with MySQL requirements.
    """
    if value != None:
        return "'%s'" % SanitizeSQL(value)

    else:
        return 'NULL'


def EncodeDicttoList(item_dict,pattern):
  """Convert a dictionary into a list

  Args:
    Item in dictionary

  Returns: list
  """
  if not item_dict:
    result_list = []
  else:
    result=[]
    for item in item_dict:
      result.append(item[pattern])

    result_list=[x.encode('utf-8') for x in result]

  return result_list


def CreateLookupDict(data_list, key, key_separator='.', key_separator_strict=True):
  """Returns a dict, keyed on the "key" field of the dicts in the data_list (list)"""
  data = {}
  
  for item in data_list:
    # Single value key (not a sequence)
    if type(key) not in (list, tuple):
      data[item[key]] = item
    
    # Else, this is a sequence of keys, so multi-value key them with key_separator
    else:
      # Get pieces of the key
      key_values = []
      for key_part in key:
        if key_separator_strict and key_separator in item[key_part]:
          raise Exception('Key Separator "%s" is found in data for key "%s", split separation will not be possible: %s' % \
                          (key_separator, key_part, item[key_part]))
        
        key_values.append(item[key_part])
      
      # Combine pieces together with separator to form our combination key
      key_string = key_separator.join(key_values)
      
      # Save the item to the combination key spot
      data[key_string] = item
  
  return data

class MySQLCursorDict(mysql.connector.cursor.MySQLCursor):
  def _row_to_python(self, rowdata, desc=None):
    row = super(MySQLCursorDict, self)._row_to_python(rowdata, desc)
    if row:
      return dict(zip(self.column_names, row))
    return None
