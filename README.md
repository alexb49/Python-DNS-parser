# Python-DNS-parser
Python script + MySQL schema that allows you to parse DNS configuration files


Format for the FQDN:
hostname.environment.location.domain
hostname.location.domain

i.e.
machine-1.mv.example.com


# parser_dns.py script
Variables that should/could be edited:

CONF_PATH       => Path to all the DNS zone files
CONF_PATH_GLOB  => Path to the DNS directory containing 1 directory for each DNS server
OUTPUT_PATH     => Path to the directory where you want the JSON files to be put

example:
with a DNS server FQDN = 'machine-1.aws.example.com' and azone file named named 'test.example.com'
PATH TO THE FILE = '/opt/cmdb/dns/machine-1.aws.example.com/test.example.com'
CONF_PATH = '/opt/cmdb/dns/*'
CONF_PATH_GLOB = '/opt/cmdb/dns/'_GLOB
