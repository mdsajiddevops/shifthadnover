-- MySQL dump 10.13  Distrib 8.0.43, for Linux (x86_64)
--
-- Host: localhost    Database: shift_handover
-- ------------------------------------------------------
-- Server version	8.0.43

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `account`
--

DROP TABLE IF EXISTS `account`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `account` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(128) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `status` varchar(16) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `app_config`
--

DROP TABLE IF EXISTS `app_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `app_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `config_key` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `config_value` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `category` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `config_key` (`config_key`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_log`
--

DROP TABLE IF EXISTS `audit_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `username` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `action` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `details` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `timestamp` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15374 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `current_shift_engineers`
--

DROP TABLE IF EXISTS `current_shift_engineers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `current_shift_engineers` (
  `shift_id` int DEFAULT NULL,
  `team_member_id` int DEFAULT NULL,
  KEY `shift_id` (`shift_id`),
  KEY `team_member_id` (`team_member_id`),
  CONSTRAINT `current_shift_engineers_ibfk_1` FOREIGN KEY (`shift_id`) REFERENCES `shift` (`id`),
  CONSTRAINT `current_shift_engineers_ibfk_2` FOREIGN KEY (`team_member_id`) REFERENCES `team_member` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `escalation_matrix_file`
--

DROP TABLE IF EXISTS `escalation_matrix_file`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `escalation_matrix_file` (
  `id` int NOT NULL AUTO_INCREMENT,
  `filename` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `upload_time` datetime NOT NULL,
  `account_id` int DEFAULT NULL,
  `team_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `filename` (`filename`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `escalation_matrix_file_ibfk_1` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `escalation_matrix_file_ibfk_2` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `handover_audit_log`
--

DROP TABLE IF EXISTS `handover_audit_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `handover_audit_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `handover_request_id` int DEFAULT NULL,
  `incident_assignment_id` int DEFAULT NULL,
  `action_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `performed_by_id` int NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `details` json DEFAULT NULL,
  `performed_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ip_address` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_agent` text COLLATE utf8mb4_unicode_ci,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `handover_request_id` (`handover_request_id`),
  KEY `performed_by_id` (`performed_by_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  KEY `handover_audit_log_ibfk_2` (`incident_assignment_id`),
  CONSTRAINT `handover_audit_log_ibfk_1` FOREIGN KEY (`handover_request_id`) REFERENCES `handover_request` (`id`),
  CONSTRAINT `handover_audit_log_ibfk_2` FOREIGN KEY (`incident_assignment_id`) REFERENCES `incident_assignment` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `handover_audit_log_ibfk_3` FOREIGN KEY (`performed_by_id`) REFERENCES `user` (`id`),
  CONSTRAINT `handover_audit_log_ibfk_4` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `handover_audit_log_ibfk_5` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `handover_incident_response_log`
--

DROP TABLE IF EXISTS `handover_incident_response_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `handover_incident_response_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `response_date` date NOT NULL,
  `response_datetime` datetime NOT NULL,
  `from_shift_type` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `to_shift_type` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `from_shift_id` int DEFAULT NULL,
  `to_shift_id` int DEFAULT NULL,
  `assigned_by_id` int NOT NULL,
  `assigned_by_name` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `assigned_by_email` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accepted_by_id` int DEFAULT NULL,
  `accepted_by_name` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accepted_by_email` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `incident_number` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `incident_title` varchar(256) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `incident_description` text COLLATE utf8mb4_unicode_ci,
  `incident_priority` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `incident_status` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `incident_url` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `response_status` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `response_comments` text COLLATE utf8mb4_unicode_ci,
  `estimated_completion_time` datetime DEFAULT NULL,
  `actual_completion_time` datetime DEFAULT NULL,
  `requires_handover` tinyint(1) DEFAULT '0',
  `handover_notes` text COLLATE utf8mb4_unicode_ci,
  `handover_deadline` datetime DEFAULT NULL,
  `handover_completed_at` datetime DEFAULT NULL,
  `escalated_to_id` int DEFAULT NULL,
  `escalated_to_name` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `escalated_to_email` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `escalation_reason` text COLLATE utf8mb4_unicode_ci,
  `escalation_datetime` datetime DEFAULT NULL,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `incident_type` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'open' COMMENT 'Incident type: open/active/handover/closed',
  `incident_category` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT 'Incident category: Application/Network/Infrastructure etc.',
  `assignment_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending' COMMENT 'Assignment status: pending/accepted/rejected/reassigned',
  `assignment_notes` text COLLATE utf8mb4_unicode_ci COMMENT 'Original assignment notes',
  `assigned_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When assignment was created',
  `responded_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'When response was given',
  `estimated_completion` datetime DEFAULT NULL COMMENT 'Expected resolution time',
  `actual_completion` datetime DEFAULT NULL COMMENT 'Actual resolution time',
  `handover_request_id` int DEFAULT NULL COMMENT 'Reference to handover_request table',
  `incident_assignment_id` int DEFAULT NULL COMMENT 'Reference to incident_assignment table',
  `incident_assignment_response_id` int DEFAULT NULL COMMENT 'Reference to incident_assignment_response table',
  PRIMARY KEY (`id`),
  KEY `escalated_to_id` (`escalated_to_id`),
  KEY `from_shift_id` (`from_shift_id`),
  KEY `to_shift_id` (`to_shift_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  KEY `idx_handover_response_log_date` (`response_date`),
  KEY `idx_handover_response_log_incident` (`incident_number`),
  KEY `idx_handover_response_log_priority` (`incident_priority`),
  KEY `idx_handover_response_log_status` (`response_status`),
  KEY `idx_handover_response_log_assigned_by` (`assigned_by_id`),
  KEY `idx_handover_response_log_accepted_by` (`accepted_by_id`),
  CONSTRAINT `handover_incident_response_log_ibfk_1` FOREIGN KEY (`assigned_by_id`) REFERENCES `user` (`id`),
  CONSTRAINT `handover_incident_response_log_ibfk_2` FOREIGN KEY (`accepted_by_id`) REFERENCES `user` (`id`),
  CONSTRAINT `handover_incident_response_log_ibfk_3` FOREIGN KEY (`escalated_to_id`) REFERENCES `user` (`id`),
  CONSTRAINT `handover_incident_response_log_ibfk_4` FOREIGN KEY (`from_shift_id`) REFERENCES `shift` (`id`),
  CONSTRAINT `handover_incident_response_log_ibfk_5` FOREIGN KEY (`to_shift_id`) REFERENCES `shift` (`id`),
  CONSTRAINT `handover_incident_response_log_ibfk_6` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `handover_incident_response_log_ibfk_7` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `handover_notification`
--

DROP TABLE IF EXISTS `handover_notification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `handover_notification` (
  `id` int NOT NULL AUTO_INCREMENT,
  `handover_request_id` int DEFAULT NULL,
  `recipient_id` int NOT NULL,
  `notification_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(256) COLLATE utf8mb4_unicode_ci NOT NULL,
  `message` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_read` tinyint(1) DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `read_at` datetime DEFAULT NULL,
  `expires_at` datetime DEFAULT NULL,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  `action_url` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `action_text` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_dismissed` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `handover_request_id` (`handover_request_id`),
  KEY `recipient_id` (`recipient_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `handover_notification_ibfk_1` FOREIGN KEY (`handover_request_id`) REFERENCES `handover_request` (`id`),
  CONSTRAINT `handover_notification_ibfk_2` FOREIGN KEY (`recipient_id`) REFERENCES `user` (`id`),
  CONSTRAINT `handover_notification_ibfk_3` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `handover_notification_ibfk_4` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `handover_request`
--

DROP TABLE IF EXISTS `handover_request`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `handover_request` (
  `id` int NOT NULL AUTO_INCREMENT,
  `shift_date` date NOT NULL,
  `current_shift_type` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL,
  `next_shift_type` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_by_id` int NOT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `general_notes` text COLLATE utf8mb4_unicode_ci,
  `shift_summary` text COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `expires_at` datetime DEFAULT NULL,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `created_by_id` (`created_by_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `handover_request_ibfk_1` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`),
  CONSTRAINT `handover_request_ibfk_2` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `handover_request_ibfk_3` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `handover_response`
--

DROP TABLE IF EXISTS `handover_response`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `handover_response` (
  `id` int NOT NULL AUTO_INCREMENT,
  `handover_request_id` int NOT NULL,
  `responder_id` int NOT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `comments` text COLLATE utf8mb4_unicode_ci,
  `responded_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `handover_request_id` (`handover_request_id`),
  KEY `responder_id` (`responder_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `handover_response_ibfk_1` FOREIGN KEY (`handover_request_id`) REFERENCES `handover_request` (`id`),
  CONSTRAINT `handover_response_ibfk_2` FOREIGN KEY (`responder_id`) REFERENCES `user` (`id`),
  CONSTRAINT `handover_response_ibfk_3` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `handover_response_ibfk_4` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `incident`
--

DROP TABLE IF EXISTS `incident`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `incident` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `priority` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `handover` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `shift_id` int DEFAULT NULL,
  `type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `assigned_to` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `escalated_to` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `shift_id` (`shift_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `incident_ibfk_1` FOREIGN KEY (`shift_id`) REFERENCES `shift` (`id`),
  CONSTRAINT `incident_ibfk_2` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `incident_ibfk_3` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=64 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `incident_assignment`
--

DROP TABLE IF EXISTS `incident_assignment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `incident_assignment` (
  `id` int NOT NULL AUTO_INCREMENT,
  `handover_request_id` int NOT NULL,
  `incident_id` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `incident_title` varchar(256) COLLATE utf8mb4_unicode_ci NOT NULL,
  `incident_description` text COLLATE utf8mb4_unicode_ci,
  `incident_priority` varchar(16) COLLATE utf8mb4_unicode_ci NOT NULL,
  `incident_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `incident_url` varchar(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `assigned_to_id` int DEFAULT NULL,
  `assigned_by_id` int NOT NULL,
  `assignment_notes` text COLLATE utf8mb4_unicode_ci,
  `estimated_effort_hours` float DEFAULT NULL,
  `requires_handover` tinyint(1) DEFAULT '0',
  `handover_deadline` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  `handover_context` text COLLATE utf8mb4_unicode_ci COMMENT 'Handover instructions and context',
  `assignment_status` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT 'pending' COMMENT 'pending, accepted, rejected, reassigned',
  `assigned_at` datetime DEFAULT CURRENT_TIMESTAMP COMMENT 'When assignment was created',
  `responded_at` datetime DEFAULT NULL COMMENT 'When user responded to assignment',
  PRIMARY KEY (`id`),
  KEY `handover_request_id` (`handover_request_id`),
  KEY `assigned_to_id` (`assigned_to_id`),
  KEY `assigned_by_id` (`assigned_by_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `incident_assignment_ibfk_1` FOREIGN KEY (`handover_request_id`) REFERENCES `handover_request` (`id`),
  CONSTRAINT `incident_assignment_ibfk_2` FOREIGN KEY (`assigned_to_id`) REFERENCES `user` (`id`),
  CONSTRAINT `incident_assignment_ibfk_3` FOREIGN KEY (`assigned_by_id`) REFERENCES `user` (`id`),
  CONSTRAINT `incident_assignment_ibfk_4` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `incident_assignment_ibfk_5` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `incident_assignment_response`
--

DROP TABLE IF EXISTS `incident_assignment_response`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `incident_assignment_response` (
  `id` int NOT NULL AUTO_INCREMENT,
  `incident_assignment_id` int NOT NULL,
  `responder_id` int NOT NULL,
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `comments` text COLLATE utf8mb4_unicode_ci,
  `estimated_completion_time` datetime DEFAULT NULL,
  `responded_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `responder_id` (`responder_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  KEY `incident_assignment_response_ibfk_1` (`incident_assignment_id`),
  CONSTRAINT `incident_assignment_response_ibfk_1` FOREIGN KEY (`incident_assignment_id`) REFERENCES `incident_assignment` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `incident_assignment_response_ibfk_2` FOREIGN KEY (`responder_id`) REFERENCES `user` (`id`),
  CONSTRAINT `incident_assignment_response_ibfk_3` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `incident_assignment_response_ibfk_4` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `leave_request`
--

DROP TABLE IF EXISTS `leave_request`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `leave_request` (
  `id` int NOT NULL AUTO_INCREMENT,
  `requester_id` int NOT NULL,
  `leave_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `leave_date` date NOT NULL,
  `shift_code` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `reason` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `approved_by_id` int DEFAULT NULL,
  `covered_by_id` int DEFAULT NULL,
  `coverage_notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `approval_comments` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `approved_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `requester_id` (`requester_id`),
  KEY `approved_by_id` (`approved_by_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  KEY `covered_by_id` (`covered_by_id`),
  CONSTRAINT `leave_request_ibfk_1` FOREIGN KEY (`requester_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `leave_request_ibfk_2` FOREIGN KEY (`approved_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `leave_request_ibfk_3` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`) ON DELETE CASCADE,
  CONSTRAINT `leave_request_ibfk_4` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`) ON DELETE CASCADE,
  CONSTRAINT `leave_request_ibfk_5` FOREIGN KEY (`covered_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `next_shift_engineers`
--

DROP TABLE IF EXISTS `next_shift_engineers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `next_shift_engineers` (
  `shift_id` int DEFAULT NULL,
  `team_member_id` int DEFAULT NULL,
  KEY `shift_id` (`shift_id`),
  KEY `team_member_id` (`team_member_id`),
  CONSTRAINT `next_shift_engineers_ibfk_1` FOREIGN KEY (`shift_id`) REFERENCES `shift` (`id`),
  CONSTRAINT `next_shift_engineers_ibfk_2` FOREIGN KEY (`team_member_id`) REFERENCES `team_member` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `password_reset_tokens`
--

DROP TABLE IF EXISTS `password_reset_tokens`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `password_reset_tokens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `token` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL,
  `expires_at` datetime NOT NULL,
  `used_at` datetime DEFAULT NULL,
  `ip_address` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_agent` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_password_reset_tokens_token` (`token`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `password_reset_tokens_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `secret_audit_log`
--

DROP TABLE IF EXISTS `secret_audit_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `secret_audit_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `secret_key` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ip_address` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_agent` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `timestamp` datetime NOT NULL,
  `old_value_hash` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `new_value_hash` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `success` tinyint(1) DEFAULT NULL,
  `error_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `ix_secret_audit_log_secret_key` (`secret_key`)
) ENGINE=InnoDB AUTO_INCREMENT=1599 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `secret_store`
--

DROP TABLE IF EXISTS `secret_store`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `secret_store` (
  `id` int NOT NULL AUTO_INCREMENT,
  `key_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `encrypted_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `category` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `is_active` tinyint(1) NOT NULL,
  `requires_restart` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  `created_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `updated_by` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_accessed` datetime DEFAULT NULL,
  `access_count` int DEFAULT NULL,
  `expires_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_secret_store_key_name` (`key_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `servicenow_config`
--

DROP TABLE IF EXISTS `servicenow_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `servicenow_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `config_key` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `config_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `encrypted` tinyint(1) NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `config_key` (`config_key`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `shift`
--

DROP TABLE IF EXISTS `shift`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `shift` (
  `id` int NOT NULL AUTO_INCREMENT,
  `date` date NOT NULL,
  `current_shift_type` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `next_shift_type` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  `submitted_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `shift_ibfk_1` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `shift_ibfk_2` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `shift_key_point`
--

DROP TABLE IF EXISTS `shift_key_point`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `shift_key_point` (
  `id` int NOT NULL AUTO_INCREMENT,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `responsible_engineer_id` int DEFAULT NULL,
  `shift_id` int DEFAULT NULL,
  `jira_id` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `responsible_engineer_id` (`responsible_engineer_id`),
  KEY `shift_id` (`shift_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `shift_key_point_ibfk_1` FOREIGN KEY (`responsible_engineer_id`) REFERENCES `team_member` (`id`),
  CONSTRAINT `shift_key_point_ibfk_2` FOREIGN KEY (`shift_id`) REFERENCES `shift` (`id`),
  CONSTRAINT `shift_key_point_ibfk_3` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `shift_key_point_ibfk_4` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `shift_key_point_update`
--

DROP TABLE IF EXISTS `shift_key_point_update`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `shift_key_point_update` (
  `id` int NOT NULL AUTO_INCREMENT,
  `key_point_id` int NOT NULL,
  `update_text` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `update_date` date NOT NULL,
  `updated_by` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `key_point_id` (`key_point_id`),
  CONSTRAINT `shift_key_point_update_ibfk_1` FOREIGN KEY (`key_point_id`) REFERENCES `shift_key_point` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `shift_roster`
--

DROP TABLE IF EXISTS `shift_roster`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `shift_roster` (
  `id` int NOT NULL AUTO_INCREMENT,
  `date` date NOT NULL,
  `team_member_id` int NOT NULL,
  `shift_code` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `team_member_id` (`team_member_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `shift_roster_ibfk_1` FOREIGN KEY (`team_member_id`) REFERENCES `team_member` (`id`),
  CONSTRAINT `shift_roster_ibfk_2` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `shift_roster_ibfk_3` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=925 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `shift_swap_request`
--

DROP TABLE IF EXISTS `shift_swap_request`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `shift_swap_request` (
  `id` int NOT NULL AUTO_INCREMENT,
  `requester_id` int NOT NULL,
  `swap_with_id` int NOT NULL,
  `reason` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `original_date` date NOT NULL,
  `original_shift_code` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `swap_date` date NOT NULL,
  `swap_shift_code` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `approved_by_id` int DEFAULT NULL,
  `approval_comments` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `approved_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `requester_id` (`requester_id`),
  KEY `swap_with_id` (`swap_with_id`),
  KEY `approved_by_id` (`approved_by_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `shift_swap_request_ibfk_1` FOREIGN KEY (`requester_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `shift_swap_request_ibfk_2` FOREIGN KEY (`swap_with_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `shift_swap_request_ibfk_3` FOREIGN KEY (`approved_by_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `shift_swap_request_ibfk_4` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`) ON DELETE CASCADE,
  CONSTRAINT `shift_swap_request_ibfk_5` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `smtp_config`
--

DROP TABLE IF EXISTS `smtp_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `smtp_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `config_key` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `config_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `encrypted` tinyint(1) NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `config_key` (`config_key`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sso_config`
--

DROP TABLE IF EXISTS `sso_config`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sso_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `provider_type` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `provider_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `enabled` tinyint(1) DEFAULT NULL,
  `config_key` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `config_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `encrypted` tinyint(1) DEFAULT NULL,
  `account_id` int DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `account_id` (`account_id`),
  CONSTRAINT `sso_config_ibfk_1` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=134 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `swap_leave_audit_log`
--

DROP TABLE IF EXISTS `swap_leave_audit_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `swap_leave_audit_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `performed_by_id` int NOT NULL,
  `target_user_id` int DEFAULT NULL,
  `swap_request_id` int DEFAULT NULL,
  `leave_request_id` int DEFAULT NULL,
  `details` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `ip_address` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `user_agent` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `performed_by_id` (`performed_by_id`),
  KEY `target_user_id` (`target_user_id`),
  KEY `swap_request_id` (`swap_request_id`),
  KEY `leave_request_id` (`leave_request_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `swap_leave_audit_log_ibfk_1` FOREIGN KEY (`performed_by_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `swap_leave_audit_log_ibfk_2` FOREIGN KEY (`target_user_id`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `swap_leave_audit_log_ibfk_3` FOREIGN KEY (`swap_request_id`) REFERENCES `shift_swap_request` (`id`) ON DELETE CASCADE,
  CONSTRAINT `swap_leave_audit_log_ibfk_4` FOREIGN KEY (`leave_request_id`) REFERENCES `leave_request` (`id`) ON DELETE CASCADE,
  CONSTRAINT `swap_leave_audit_log_ibfk_5` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`) ON DELETE CASCADE,
  CONSTRAINT `swap_leave_audit_log_ibfk_6` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `swap_leave_notification`
--

DROP TABLE IF EXISTS `swap_leave_notification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `swap_leave_notification` (
  `id` int NOT NULL AUTO_INCREMENT,
  `recipient_id` int NOT NULL,
  `notification_type` varchar(30) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `swap_request_id` int DEFAULT NULL,
  `leave_request_id` int DEFAULT NULL,
  `is_read` tinyint(1) NOT NULL DEFAULT '0',
  `email_sent` tinyint(1) NOT NULL DEFAULT '0',
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `read_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipient_id` (`recipient_id`),
  KEY `swap_request_id` (`swap_request_id`),
  KEY `leave_request_id` (`leave_request_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `swap_leave_notification_ibfk_1` FOREIGN KEY (`recipient_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `swap_leave_notification_ibfk_2` FOREIGN KEY (`swap_request_id`) REFERENCES `shift_swap_request` (`id`) ON DELETE CASCADE,
  CONSTRAINT `swap_leave_notification_ibfk_3` FOREIGN KEY (`leave_request_id`) REFERENCES `leave_request` (`id`) ON DELETE CASCADE,
  CONSTRAINT `swap_leave_notification_ibfk_4` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`) ON DELETE CASCADE,
  CONSTRAINT `swap_leave_notification_ibfk_5` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=122 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `team`
--

DROP TABLE IF EXISTS `team`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `team` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `status` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `account_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `account_id` (`account_id`),
  CONSTRAINT `team_ibfk_1` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `team_member`
--

DROP TABLE IF EXISTS `team_member`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `team_member` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `contact_number` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `team_member_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`),
  CONSTRAINT `team_member_ibfk_2` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `team_member_ibfk_3` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=59 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(120) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `password` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `status` varchar(16) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `account_id` int DEFAULT NULL,
  `team_id` int DEFAULT NULL,
  `first_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_name` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `profile_picture` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `first_login` tinyint(1) DEFAULT '1',
  `onboarding_completed` tinyint(1) DEFAULT '0',
  `last_login` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `user_ibfk_1` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `user_ibfk_2` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=54 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping routines for database 'shift_handover'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-11-22  5:04:31
