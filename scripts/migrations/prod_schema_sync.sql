-- =============================================================================
-- prod_schema_sync.sql
-- Safe, idempotent schema migration for production.
--
-- SAFE TO RUN MULTIPLE TIMES — uses IF NOT EXISTS / information_schema checks.
-- Never drops columns, never modifies existing data.
-- Run BEFORE deploying the new code.
--
-- Usage (on the prod VM):
--   docker-compose -f docker-compose.prod.yml exec -T db \
--     mysql -u root -p"$(cat ./secrets/mysql_root_password)" shift_handover \
--     < scripts/migrations/prod_schema_sync.sql
-- =============================================================================

SET NAMES utf8mb4;
SET foreign_key_checks = 0;   -- allow table creation in any order

-- =============================================================================
-- SECTION 1: NEW TABLES
-- CREATE TABLE IF NOT EXISTS is safe — skipped if table already exists.
-- =============================================================================

CREATE TABLE IF NOT EXISTS `app_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `config_key` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `config_value` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `category` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `checkin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `team_member_id` int NOT NULL,
  `user_id` int DEFAULT NULL,
  `status` varchar(32) NOT NULL,
  `checkin_time` datetime NOT NULL,
  `checkout_time` datetime DEFAULT NULL,
  `location` varchar(128) DEFAULT NULL,
  `notes` text,
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `idx_checkin_member` (`team_member_id`),
  KEY `idx_checkin_time` (`checkin_time`),
  CONSTRAINT `checkin_log_ibfk_1` FOREIGN KEY (`team_member_id`) REFERENCES `team_member` (`id`),
  CONSTRAINT `checkin_log_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `draft_change_info` (
  `id` int NOT NULL AUTO_INCREMENT,
  `shift_id` int NOT NULL,
  `temp_id` varchar(64) NOT NULL,
  `application_name` varchar(128) DEFAULT NULL,
  `change_number` varchar(64) DEFAULT NULL,
  `description` text,
  `change_datetime` varchar(64) DEFAULT NULL,
  `responsible_engineer_id` int DEFAULT NULL,
  `status` varchar(32) DEFAULT NULL,
  `created_by_id` int NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_by_id` int DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `version` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_draft_changeinfo` (`shift_id`,`temp_id`),
  KEY `responsible_engineer_id` (`responsible_engineer_id`),
  KEY `created_by_id` (`created_by_id`),
  KEY `updated_by_id` (`updated_by_id`),
  KEY `ix_draft_change_info_shift_id` (`shift_id`),
  CONSTRAINT `draft_change_info_ibfk_1` FOREIGN KEY (`shift_id`) REFERENCES `shift` (`id`),
  CONSTRAINT `draft_change_info_ibfk_2` FOREIGN KEY (`responsible_engineer_id`) REFERENCES `team_member` (`id`),
  CONSTRAINT `draft_change_info_ibfk_3` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`),
  CONSTRAINT `draft_change_info_ibfk_4` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `draft_incident` (
  `id` int NOT NULL AUTO_INCREMENT,
  `shift_id` int NOT NULL,
  `temp_id` varchar(64) NOT NULL,
  `incident_type` varchar(32) NOT NULL,
  `app_name` varchar(128) DEFAULT NULL,
  `incident_id` varchar(64) DEFAULT NULL,
  `title` varchar(256) DEFAULT NULL,
  `description` text,
  `priority` varchar(32) DEFAULT NULL,
  `status` varchar(32) DEFAULT NULL,
  `assigned_to` varchar(128) DEFAULT NULL,
  `escalated_to` varchar(128) DEFAULT NULL,
  `resolution` text,
  `created_by_id` int NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_by_id` int DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `version` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_draft_incident` (`shift_id`,`temp_id`),
  KEY `created_by_id` (`created_by_id`),
  KEY `updated_by_id` (`updated_by_id`),
  KEY `idx_draft_incident_shift` (`shift_id`),
  KEY `ix_draft_incident_shift_id` (`shift_id`),
  CONSTRAINT `draft_incident_ibfk_1` FOREIGN KEY (`shift_id`) REFERENCES `shift` (`id`),
  CONSTRAINT `draft_incident_ibfk_2` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`),
  CONSTRAINT `draft_incident_ibfk_3` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `draft_kb_update` (
  `id` int NOT NULL AUTO_INCREMENT,
  `shift_id` int NOT NULL,
  `temp_id` varchar(64) NOT NULL,
  `application_name` varchar(128) DEFAULT NULL,
  `kb_number` varchar(64) DEFAULT NULL,
  `description` text,
  `responsible_person_id` int DEFAULT NULL,
  `status` varchar(32) DEFAULT NULL,
  `created_by_id` int NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_by_id` int DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `version` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_draft_kbupdate` (`shift_id`,`temp_id`),
  KEY `responsible_person_id` (`responsible_person_id`),
  KEY `created_by_id` (`created_by_id`),
  KEY `updated_by_id` (`updated_by_id`),
  KEY `ix_draft_kb_update_shift_id` (`shift_id`),
  CONSTRAINT `draft_kb_update_ibfk_1` FOREIGN KEY (`shift_id`) REFERENCES `shift` (`id`),
  CONSTRAINT `draft_kb_update_ibfk_2` FOREIGN KEY (`responsible_person_id`) REFERENCES `team_member` (`id`),
  CONSTRAINT `draft_kb_update_ibfk_3` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`),
  CONSTRAINT `draft_kb_update_ibfk_4` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `draft_key_point` (
  `id` int NOT NULL AUTO_INCREMENT,
  `shift_id` int NOT NULL,
  `temp_id` varchar(64) NOT NULL,
  `description` text NOT NULL,
  `status` varchar(32) DEFAULT NULL,
  `responsible_engineer_id` int DEFAULT NULL,
  `jira_id` varchar(64) DEFAULT NULL,
  `created_by_id` int NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_by_id` int DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  `version` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_draft_keypoint` (`shift_id`,`temp_id`),
  KEY `responsible_engineer_id` (`responsible_engineer_id`),
  KEY `created_by_id` (`created_by_id`),
  KEY `updated_by_id` (`updated_by_id`),
  KEY `ix_draft_key_point_shift_id` (`shift_id`),
  CONSTRAINT `draft_key_point_ibfk_1` FOREIGN KEY (`shift_id`) REFERENCES `shift` (`id`),
  CONSTRAINT `draft_key_point_ibfk_2` FOREIGN KEY (`responsible_engineer_id`) REFERENCES `team_member` (`id`),
  CONSTRAINT `draft_key_point_ibfk_3` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`),
  CONSTRAINT `draft_key_point_ibfk_4` FOREIGN KEY (`updated_by_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `email_delivery_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `subject` varchar(500) NOT NULL,
  `recipients` text NOT NULL,
  `cc_recipients` text,
  `sender` varchar(255) DEFAULT NULL,
  `source_type` varchar(50) NOT NULL,
  `source_id` int DEFAULT NULL,
  `status` varchar(50) NOT NULL,
  `error_message` text,
  `smtp_server` varchar(255) DEFAULT NULL,
  `smtp_port` int DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `sent_at` datetime DEFAULT NULL,
  `duration_seconds` float DEFAULT NULL,
  `account_id` int DEFAULT NULL,
  `team_id` int DEFAULT NULL,
  `triggered_by_id` int DEFAULT NULL,
  `recipient_count` int DEFAULT NULL,
  `retry_count` int DEFAULT NULL,
  `uns_event_id` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_uns_event_id` (`uns_event_id`),
  KEY `idx_email_log_status` (`status`),
  KEY `idx_email_log_sent_at` (`sent_at`),
  KEY `idx_email_log_team_date` (`team_id`,`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `failed_tasks` (
  `id` int NOT NULL AUTO_INCREMENT,
  `task_name` varchar(256) NOT NULL,
  `task_id` varchar(36) DEFAULT NULL,
  `args` text,
  `kwargs` text,
  `exception` text,
  `traceback` text,
  `status` varchar(32) NOT NULL DEFAULT 'failed',
  `retry_count` int NOT NULL DEFAULT 0,
  `max_retries` int NOT NULL DEFAULT 3,
  `created_at` datetime NOT NULL,
  `last_attempted_at` datetime DEFAULT NULL,
  `resolved_at` datetime DEFAULT NULL,
  `account_id` int DEFAULT NULL,
  `team_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_failed_tasks_status` (`status`),
  KEY `idx_failed_tasks_created` (`created_at`),
  KEY `idx_failed_tasks_task_name` (`task_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `handover_change` (
  `id` int NOT NULL AUTO_INCREMENT,
  `shift_id` int NOT NULL,
  `user_id` int NOT NULL,
  `change_type` varchar(32) NOT NULL,
  `section_type` varchar(32) NOT NULL,
  `item_id` varchar(64) DEFAULT NULL,
  `field_name` varchar(64) DEFAULT NULL,
  `old_value` text,
  `new_value` text,
  `created_at` datetime DEFAULT NULL,
  `version` int DEFAULT NULL,
  `synced` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `ix_handover_change_shift_id` (`shift_id`),
  KEY `ix_handover_change_synced` (`synced`),
  KEY `ix_handover_change_created_at` (`created_at`),
  KEY `idx_change_sync` (`shift_id`,`synced`,`created_at`),
  CONSTRAINT `handover_change_ibfk_1` FOREIGN KEY (`shift_id`) REFERENCES `shift` (`id`),
  CONSTRAINT `handover_change_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `handover_draft` (
  `id` int NOT NULL AUTO_INCREMENT,
  `shift_id` int NOT NULL,
  `ydoc_state` blob,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_handover_draft_shift_id` (`shift_id`),
  KEY `ix_handover_draft_updated_at` (`updated_at`),
  CONSTRAINT `handover_draft_ibfk_1` FOREIGN KEY (`shift_id`) REFERENCES `shift` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `handover_session` (
  `id` int NOT NULL AUTO_INCREMENT,
  `shift_id` int NOT NULL,
  `user_id` int NOT NULL,
  `session_token` varchar(64) NOT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `joined_at` datetime DEFAULT NULL,
  `last_heartbeat` datetime DEFAULT NULL,
  `left_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `session_token` (`session_token`),
  KEY `user_id` (`user_id`),
  KEY `ix_handover_session_shift_id` (`shift_id`),
  KEY `ix_handover_session_is_active` (`is_active`),
  CONSTRAINT `handover_session_ibfk_1` FOREIGN KEY (`shift_id`) REFERENCES `shift` (`id`),
  CONSTRAINT `handover_session_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `incident_assignment` (
  `id` int NOT NULL AUTO_INCREMENT,
  `handover_request_id` int NOT NULL,
  `incident_number` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `incident_title` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `incident_description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `incident_priority` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `incident_status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `incident_url` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `assigned_to_id` int NOT NULL,
  `assigned_by_id` int NOT NULL,
  `assignment_status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'pending',
  `assignment_notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `assigned_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `responded_at` datetime DEFAULT NULL,
  `estimated_completion` datetime DEFAULT NULL,
  `actual_completion` datetime DEFAULT NULL,
  `requires_handover` tinyint(1) DEFAULT '0',
  `handover_notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `handover_deadline` datetime DEFAULT NULL,
  `handover_completed_at` datetime DEFAULT NULL,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `incident_type` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'open',
  `incident_category` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `escalated_to_id` int DEFAULT NULL,
  `escalation_reason` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `escalation_datetime` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `handover_request_id` (`handover_request_id`),
  KEY `assigned_to_id` (`assigned_to_id`),
  KEY `assigned_by_id` (`assigned_by_id`),
  KEY `escalated_to_id` (`escalated_to_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `incident_assignment_ibfk_1` FOREIGN KEY (`handover_request_id`) REFERENCES `handover_request` (`id`),
  CONSTRAINT `incident_assignment_ibfk_2` FOREIGN KEY (`assigned_to_id`) REFERENCES `user` (`id`),
  CONSTRAINT `incident_assignment_ibfk_3` FOREIGN KEY (`assigned_by_id`) REFERENCES `user` (`id`),
  CONSTRAINT `incident_assignment_ibfk_4` FOREIGN KEY (`escalated_to_id`) REFERENCES `user` (`id`),
  CONSTRAINT `incident_assignment_ibfk_5` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `incident_assignment_ibfk_6` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `incident_assignment_response` (
  `id` int NOT NULL AUTO_INCREMENT,
  `incident_assignment_id` int NOT NULL,
  `responded_by_id` int NOT NULL,
  `response_status` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `response_comments` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `estimated_completion_time` datetime DEFAULT NULL,
  `responded_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `incident_assignment_id` (`incident_assignment_id`),
  KEY `responded_by_id` (`responded_by_id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `incident_assignment_response_ibfk_1` FOREIGN KEY (`incident_assignment_id`) REFERENCES `incident_assignment` (`id`),
  CONSTRAINT `incident_assignment_response_ibfk_2` FOREIGN KEY (`responded_by_id`) REFERENCES `user` (`id`),
  CONSTRAINT `incident_assignment_response_ibfk_3` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `incident_assignment_response_ibfk_4` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `password_reset_tokens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `token` varchar(255) NOT NULL,
  `created_at` datetime NOT NULL,
  `expires_at` datetime NOT NULL,
  `used` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `password_reset_tokens_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `problem_ticket` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(256) NOT NULL,
  `description` text,
  `status` varchar(32) NOT NULL DEFAULT 'Open',
  `priority` varchar(16) NOT NULL DEFAULT 'Medium',
  `app_name` varchar(128) DEFAULT NULL,
  `jira_id` varchar(64) DEFAULT NULL,
  `account_id` int NOT NULL,
  `team_id` int NOT NULL,
  `created_by_id` int NOT NULL,
  `assigned_to_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `resolved_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  KEY `created_by_id` (`created_by_id`),
  KEY `assigned_to_id` (`assigned_to_id`),
  CONSTRAINT `problem_ticket_ibfk_1` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `problem_ticket_ibfk_2` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`),
  CONSTRAINT `problem_ticket_ibfk_3` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`),
  CONSTRAINT `problem_ticket_ibfk_4` FOREIGN KEY (`assigned_to_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `problem_task` (
  `id` int NOT NULL AUTO_INCREMENT,
  `problem_id` int NOT NULL,
  `title` varchar(256) NOT NULL,
  `description` text,
  `status` varchar(32) NOT NULL DEFAULT 'Open',
  `assigned_to_id` int DEFAULT NULL,
  `due_date` date DEFAULT NULL,
  `created_by_id` int NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `completed_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `problem_id` (`problem_id`),
  KEY `assigned_to_id` (`assigned_to_id`),
  KEY `created_by_id` (`created_by_id`),
  CONSTRAINT `problem_task_ibfk_1` FOREIGN KEY (`problem_id`) REFERENCES `problem_ticket` (`id`) ON DELETE CASCADE,
  CONSTRAINT `problem_task_ibfk_2` FOREIGN KEY (`assigned_to_id`) REFERENCES `user` (`id`),
  CONSTRAINT `problem_task_ibfk_3` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `roster_assignments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `team_id` int NOT NULL,
  `account_id` int NOT NULL,
  `member_id` int NOT NULL,
  `shift_date` date NOT NULL,
  `shift_code` varchar(10) NOT NULL,
  `is_protected` tinyint(1) NOT NULL,
  `source` varchar(16) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `member_id` (`member_id`),
  KEY `team_id` (`team_id`),
  KEY `account_id` (`account_id`),
  CONSTRAINT `roster_assignments_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `team_member` (`id`),
  CONSTRAINT `roster_assignments_ibfk_2` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`),
  CONSTRAINT `roster_assignments_ibfk_3` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `secret_store` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `encrypted_value` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `category` varchar(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'general',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `secret_audit_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `secret_id` int NOT NULL,
  `action` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `performed_by_id` int NOT NULL,
  `details` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `performed_at` datetime NOT NULL,
  `ip_address` varchar(45) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `secret_id` (`secret_id`),
  KEY `performed_by_id` (`performed_by_id`),
  CONSTRAINT `secret_audit_log_ibfk_1` FOREIGN KEY (`secret_id`) REFERENCES `secret_store` (`id`),
  CONSTRAINT `secret_audit_log_ibfk_2` FOREIGN KEY (`performed_by_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `section_lock` (
  `id` int NOT NULL AUTO_INCREMENT,
  `shift_id` int NOT NULL,
  `user_id` int NOT NULL,
  `section_type` varchar(32) NOT NULL,
  `item_id` varchar(64) NOT NULL,
  `locked_at` datetime DEFAULT NULL,
  `expires_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_section_lock` (`shift_id`,`section_type`,`item_id`),
  KEY `user_id` (`user_id`),
  KEY `idx_lock_expiry` (`expires_at`),
  CONSTRAINT `section_lock_ibfk_1` FOREIGN KEY (`shift_id`) REFERENCES `shift` (`id`),
  CONSTRAINT `section_lock_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `servicenow_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `account_id` int DEFAULT NULL,
  `team_id` int DEFAULT NULL,
  `instance_url` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `username` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `encrypted_password` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `sync_incidents` tinyint(1) NOT NULL DEFAULT '1',
  `sync_ctasks` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `account_id` (`account_id`),
  KEY `team_id` (`team_id`),
  CONSTRAINT `servicenow_config_ibfk_1` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `servicenow_config_ibfk_2` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `shift_coverage_requirements` (
  `id` int NOT NULL AUTO_INCREMENT,
  `team_id` int NOT NULL,
  `account_id` int NOT NULL,
  `shift_code` varchar(10) NOT NULL,
  `min_staff` int NOT NULL DEFAULT '1',
  `preferred_staff` int NOT NULL DEFAULT '2',
  `requires_lead` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_coverage_team_shift` (`team_id`,`shift_code`),
  KEY `account_id` (`account_id`),
  CONSTRAINT `shift_coverage_requirements_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`),
  CONSTRAINT `shift_coverage_requirements_ibfk_2` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `team_email_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `team_id` int NOT NULL,
  `account_id` int NOT NULL,
  `email_type` varchar(50) NOT NULL,
  `recipients` text,
  `cc_recipients` text,
  `subject_prefix` varchar(100) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_team_email_type` (`team_id`,`email_type`),
  KEY `account_id` (`account_id`),
  KEY `created_by_id` (`created_by_id`),
  CONSTRAINT `team_email_config_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`),
  CONSTRAINT `team_email_config_ibfk_2` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `team_email_config_ibfk_3` FOREIGN KEY (`created_by_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `email_config_audit_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `config_id` int NOT NULL,
  `action` varchar(20) NOT NULL,
  `old_values` json DEFAULT NULL,
  `new_values` json DEFAULT NULL,
  `change_reason` text,
  `performed_by` int NOT NULL,
  `performed_at` datetime NOT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `config_id` (`config_id`),
  KEY `performed_by` (`performed_by`),
  CONSTRAINT `email_config_audit_log_ibfk_1` FOREIGN KEY (`config_id`) REFERENCES `team_email_config` (`id`),
  CONSTRAINT `email_config_audit_log_ibfk_2` FOREIGN KEY (`performed_by`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `team_feature_config` (
  `id` int NOT NULL AUTO_INCREMENT,
  `team_id` int NOT NULL,
  `account_id` int NOT NULL,
  `feature_name` varchar(64) NOT NULL,
  `is_enabled` tinyint(1) NOT NULL DEFAULT '1',
  `config_json` text,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_team_feature` (`team_id`,`feature_name`),
  KEY `account_id` (`account_id`),
  CONSTRAINT `team_feature_config_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`),
  CONSTRAINT `team_feature_config_ibfk_2` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `team_shift_configs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `team_id` int NOT NULL,
  `shift_code` varchar(10) NOT NULL,
  `start_time` time NOT NULL,
  `end_time` time NOT NULL,
  `is_overnight` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_team_shift` (`team_id`,`shift_code`),
  CONSTRAINT `team_shift_configs_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `team_shift_timing_configs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `team_id` int NOT NULL,
  `account_id` int NOT NULL,
  `shift_code` varchar(10) NOT NULL,
  `start_hour` int NOT NULL,
  `end_hour` int NOT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT '1',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_timing_team_shift` (`team_id`,`shift_code`),
  KEY `account_id` (`account_id`),
  CONSTRAINT `team_shift_timing_configs_ibfk_1` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`),
  CONSTRAINT `team_shift_timing_configs_ibfk_2` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `user_team_memberships` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `team_id` int NOT NULL,
  `account_id` int NOT NULL,
  `is_primary` tinyint(1) DEFAULT '0',
  `role` varchar(50) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `added_by_id` int DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_team` (`user_id`,`team_id`),
  KEY `team_id` (`team_id`),
  KEY `account_id` (`account_id`),
  KEY `added_by_id` (`added_by_id`),
  CONSTRAINT `user_team_memberships_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`),
  CONSTRAINT `user_team_memberships_ibfk_2` FOREIGN KEY (`team_id`) REFERENCES `team` (`id`),
  CONSTRAINT `user_team_memberships_ibfk_3` FOREIGN KEY (`account_id`) REFERENCES `account` (`id`),
  CONSTRAINT `user_team_memberships_ibfk_4` FOREIGN KEY (`added_by_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


-- =============================================================================
-- SECTION 2: NEW COLUMNS ON EXISTING TABLES
-- Uses information_schema check — skipped if column already exists.
-- The helper procedure is dropped and recreated each run so this script is
-- fully idempotent even if a prior run was interrupted mid-way.
-- =============================================================================

DROP PROCEDURE IF EXISTS add_column_if_missing;

DELIMITER //
CREATE PROCEDURE add_column_if_missing(IN tbl VARCHAR(64), IN col VARCHAR(64), IN col_def TEXT)
BEGIN
    IF (SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME  = tbl
          AND COLUMN_NAME = col) = 0 THEN
        SET @_ddl = CONCAT('ALTER TABLE `', tbl, '` ADD COLUMN `', col, '` ', col_def);
        PREPARE _s FROM @_ddl;
        EXECUTE _s;
        DEALLOCATE PREPARE _s;
    END IF;
END //
DELIMITER ;

-- incident table
CALL add_column_if_missing('incident', 'description',   'TEXT NULL');
CALL add_column_if_missing('incident', 'assigned_to',   'VARCHAR(128) NULL');
CALL add_column_if_missing('incident', 'escalated_to',  'VARCHAR(128) NULL');
CALL add_column_if_missing('incident', 'is_resolved',   'TINYINT(1) NOT NULL DEFAULT 0');
CALL add_column_if_missing('incident', 'resolved_at',   'DATETIME NULL');

-- team_member table
CALL add_column_if_missing('team_member', 'availability_status', 'VARCHAR(50) NULL DEFAULT ''available''');
CALL add_column_if_missing('team_member', 'last_checkin',        'DATETIME NULL');
CALL add_column_if_missing('team_member', 'checkin_location',    'VARCHAR(255) NULL');
CALL add_column_if_missing('team_member', 'scheduling_role',     'VARCHAR(16) NOT NULL DEFAULT ''support''');
CALL add_column_if_missing('team_member', 'lead_shift',          'VARCHAR(8) NULL DEFAULT ''E''');

-- team table
CALL add_column_if_missing('team', 'email_recipients',          'TEXT NULL');
CALL add_column_if_missing('team', 'priority_alert_recipients', 'TEXT NULL');

-- shift_key_point table
CALL add_column_if_missing('shift_key_point', 'jira_id',       'VARCHAR(64) NULL');
CALL add_column_if_missing('shift_key_point', 'account_id',    'INT NOT NULL DEFAULT 1');
CALL add_column_if_missing('shift_key_point', 'team_id',       'INT NOT NULL DEFAULT 1');
CALL add_column_if_missing('shift_key_point', 'created_at',    'DATETIME NULL DEFAULT CURRENT_TIMESTAMP');
CALL add_column_if_missing('shift_key_point', 'created_by_id', 'INT NULL');

-- shift_change_info table
CALL add_column_if_missing('shift_change_info', 'status',     'VARCHAR(16) NOT NULL DEFAULT ''New''');
CALL add_column_if_missing('shift_change_info', 'account_id', 'INT NOT NULL DEFAULT 1');
CALL add_column_if_missing('shift_change_info', 'team_id',    'INT NOT NULL DEFAULT 1');
CALL add_column_if_missing('shift_change_info', 'created_at', 'DATETIME NULL DEFAULT CURRENT_TIMESTAMP');

-- shift_kb_update table (same pattern as shift_change_info)
CALL add_column_if_missing('shift_kb_update', 'account_id', 'INT NOT NULL DEFAULT 1');
CALL add_column_if_missing('shift_kb_update', 'team_id',    'INT NOT NULL DEFAULT 1');
CALL add_column_if_missing('shift_kb_update', 'created_at', 'DATETIME NULL DEFAULT CURRENT_TIMESTAMP');

-- user table
CALL add_column_if_missing('user', 'role',                  'VARCHAR(32) NOT NULL DEFAULT ''user''');
CALL add_column_if_missing('user', 'first_name',            'VARCHAR(64) NULL');
CALL add_column_if_missing('user', 'last_name',             'VARCHAR(64) NULL');
CALL add_column_if_missing('user', 'profile_picture',       'VARCHAR(255) NULL');
CALL add_column_if_missing('user', 'first_login',           'TINYINT(1) NULL DEFAULT 1');
CALL add_column_if_missing('user', 'onboarding_completed',  'TINYINT(1) NULL DEFAULT 0');
CALL add_column_if_missing('user', 'last_login',            'DATETIME NULL');
CALL add_column_if_missing('user', 'created_at',            'DATETIME NULL');
CALL add_column_if_missing('user', 'updated_at',            'DATETIME NULL');
CALL add_column_if_missing('user', 'last_activity',         'DATETIME NULL');
CALL add_column_if_missing('user', 'session_token',         'VARCHAR(64) NULL');
CALL add_column_if_missing('user', 'session_created_at',    'DATETIME NULL');
CALL add_column_if_missing('user', 'sessions_terminated_at','DATETIME NULL');

-- shift table
CALL add_column_if_missing('shift', 'additional_notes', 'TEXT NULL');
CALL add_column_if_missing('shift', 'submitted_at',     'DATETIME NULL');
CALL add_column_if_missing('shift', 'created_at',       'DATETIME NULL DEFAULT CURRENT_TIMESTAMP');

-- scheduled_shifts — add created_by_id if missing
CALL add_column_if_missing('scheduled_shifts', 'created_by_id', 'INT NULL');

-- email_delivery_log — add uns_event_id if table predates it
CALL add_column_if_missing('email_delivery_log', 'uns_event_id', 'VARCHAR(100) NULL');

-- =============================================================================
-- SECTION 3: ALEMBIC VERSION — tells Flask-Migrate not to re-run migrations
-- =============================================================================

CREATE TABLE IF NOT EXISTS `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT IGNORE INTO `alembic_version` VALUES ('fix_scheduling_role_nullable');

-- =============================================================================
-- SECTION 4: PERFORMANCE INDEXES (from add_performance_indexes.sql)
-- Uses IF NOT EXISTS — safe to run even if indexes already exist.
-- =============================================================================

-- Check and add missing indexes on high-traffic tables
SET @idx = (SELECT COUNT(*) FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='shift' AND INDEX_NAME='idx_shift_date_status');
SET @sql = IF(@idx=0, 'ALTER TABLE shift ADD INDEX idx_shift_date_status (date, status)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET @idx = (SELECT COUNT(*) FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='incident' AND INDEX_NAME='idx_incident_shift_type');
SET @sql = IF(@idx=0, 'ALTER TABLE incident ADD INDEX idx_incident_shift_type (shift_id, type)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET @idx = (SELECT COUNT(*) FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='shift_key_point' AND INDEX_NAME='idx_kp_team_status');
SET @sql = IF(@idx=0, 'ALTER TABLE shift_key_point ADD INDEX idx_kp_team_status (team_id, status)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET @idx = (SELECT COUNT(*) FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='audit_log' AND INDEX_NAME='idx_audit_timestamp');
SET @sql = IF(@idx=0, 'ALTER TABLE audit_log ADD INDEX idx_audit_timestamp (timestamp)', 'SELECT 1');
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET foreign_key_checks = 1;

-- Clean up helper procedure — not needed after migration
DROP PROCEDURE IF EXISTS add_column_if_missing;

SELECT 'prod_schema_sync.sql completed successfully' AS result;
