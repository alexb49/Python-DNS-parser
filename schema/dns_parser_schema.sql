-- MySQL dump 10.13  Distrib 5.6.29-76.2, for Linux (x86_64)
--
-- Host:    Database: 
-- ------------------------------------------------------
-- Server version	5.6.29-76.2-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `environment`
--

DROP TABLE IF EXISTS `environment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `environment` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `location`
--

DROP TABLE IF EXISTS `location`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `location` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `machine`
--

DROP TABLE IF EXISTS `machine`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `machine` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `hostname` varchar(255) NOT NULL DEFAULT '',
  `mac_address` varchar(255) DEFAULT NULL,
  `mac_address_idrac` varchar(255) DEFAULT NULL,
  `ip_address` varchar(255) DEFAULT NULL,
  `ip_address_idrac` varchar(255) DEFAULT NULL,
  `associated_ips_json_list` text,
  `service_tag` varchar(255) DEFAULT NULL,
  `asset_tag` varchar(255) DEFAULT NULL,
  `location_id` int(11) NOT NULL COMMENT 'Reference to location.id',
  `environment_id` int(11) NOT NULL COMMENT 'Reference to environment.id',
  `rack` varchar(255) DEFAULT NULL,
  `rack_position` varchar(255) DEFAULT NULL,
  `cage_number` varchar(255) DEFAULT NULL,
  `pdu_outlet` varchar(255) DEFAULT NULL,
  `parent_id` int(11) DEFAULT NULL COMMENT 'Reference to machine.id',
  `os_type_id` int(11) DEFAULT NULL COMMENT 'Reference to machine_os_type.id',
  `os` varchar(255) DEFAULT NULL,
  `os_version` varchar(255) DEFAULT NULL,
  `created_date` datetime NOT NULL,
  `last_updated` datetime DEFAULT NULL,
  `in_use` int(11) NOT NULL DEFAULT '0',
  `is_monitored` int(11) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_host` (`hostname`,`location_id`,`environment_id`),
  KEY `ip_address` (`ip_address`),
  KEY `ip_address_idrac` (`ip_address_idrac`)
) ENGINE=InnoDB AUTO_INCREMENT=603 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `machine_os_type`
--

DROP TABLE IF EXISTS `machine_os_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `machine_os_type` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `os_type` varchar(255) NOT NULL DEFAULT '',
  `comment` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_os_type` (`os_type`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `network_dns_record_class`
--

DROP TABLE IF EXISTS `network_dns_record_class`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `network_dns_record_class` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(45) NOT NULL DEFAULT '',
  `description` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `network_dns_record_type`
--

DROP TABLE IF EXISTS `network_dns_record_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `network_dns_record_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(45) NOT NULL DEFAULT '',
  `description` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=39 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `network_dns_zone`
--

DROP TABLE IF EXISTS `network_dns_zone`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `network_dns_zone` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `machine_id` int(11) NOT NULL,
  `ttl` varchar(255) DEFAULT NULL COMMENT 'Refers to $INCLUDE in DNS file',
  `include_list` varchar(255) DEFAULT NULL COMMENT 'Refers to $INCLUDE in DNS file',
  `created` datetime DEFAULT NULL,
  `updated` datetime DEFAULT NULL,
  `in_use` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_domain_per_location` (`machine_id`,`name`)
) ENGINE=InnoDB AUTO_INCREMENT=49 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `network_dns_zone_origin`
--

CREATE TABLE `network_dns_zone_origin` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `network_dns_zone_id` int(11) NOT NULL COMMENT 'Reference to network_dns_zone.id',
  `name` varchar(255) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_origin_per_zone` (`name`,`network_dns_zone_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

--
-- Table structure for table `network_dns_zone_record`
--

DROP TABLE IF EXISTS `network_dns_zone_record`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `network_dns_zone_record` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `network_dns_zone_id` int(11) NOT NULL COMMENT 'Reference to network_dns_zone.id',
  `name` varchar(45) NOT NULL DEFAULT '',
  `network_dns_zone_origin_id` int(11) DEFAULT NULL COMMENT 'Reference to network_dns_zone_origin.id',
  `ttl` varchar(11) DEFAULT NULL,
  `network_dns_record_type_id` int(11) DEFAULT NULL COMMENT 'Reference to network_dns_record_type.id',
  `network_dns_record_class_id` int(11) NOT NULL COMMENT 'Reference to network_dns_record_class.id',
  `rdata` text NOT NULL,
  `created` datetime DEFAULT NULL,
  `updated` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_record` (`network_dns_zone_id`,`name`,`network_dns_zone_origin_id`,`network_dns_record_type_id`,`network_dns_record_class_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `network_dns_zone_record_soa`
--

DROP TABLE IF EXISTS `network_dns_zone_record_soa`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `network_dns_zone_record_soa` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `network_dns_zone_id` int(11) NOT NULL COMMENT 'Reference to network_dns_zone.id',
  `network_dns_zone_origin_id` int(11) DEFAULT NULL COMMENT 'Reference to network_dns_origin.id',
  `network_dns_record_class_id` int(11) DEFAULT NULL COMMENT 'Reference to network_dns_record_class.id',
  `network_dns_record_type_id` int(11) DEFAULT NULL COMMENT 'Reference to network_dns_record_type.id',
  `ttl` varchar(45) DEFAULT '86400',
  `primary_name_server` varchar(255) DEFAULT NULL,
  `responsible_party` varchar(11) DEFAULT NULL,
  `serial` int(11) DEFAULT NULL,
  `refresh` varchar(45) DEFAULT '3H',
  `retry` varchar(45) DEFAULT '15M',
  `expire` varchar(45) DEFAULT '1w',
  `minimum` varchar(45) DEFAULT '3h',
  `created` datetime DEFAULT NULL,
  `updated` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_conf_per_domain` (`network_dns_zone_id`)
) ENGINE=InnoDB AUTO_INCREMENT=45 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `raw_network_dns_configuration`
--

DROP TABLE IF EXISTS `raw_network_dns_configuration`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `raw_network_dns_configuration` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `hostname` varchar(255) NOT NULL DEFAULT '' COMMENT 'Hostname where the file lives',
  `zone` varchar(255) NOT NULL DEFAULT '' COMMENT 'Zone name',
  `data_json` longtext NOT NULL,
  `processed` tinyint(1) DEFAULT NULL COMMENT 'Has this data already been processed?',
  `created` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
  `updated` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_zone_per_hostname` (`hostname`,`zone`)
) ENGINE=InnoDB AUTO_INCREMENT=49 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;
