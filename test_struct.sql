/*
 Navicat Premium Data Transfer

 Source Server         : tidb-local
 Source Server Type    : MySQL
 Source Server Version : 80011 (8.0.11-TiDB-v8.5.1)
 Source Host           : localhost:4000
 Source Schema         : test

 Target Server Type    : MySQL
 Target Server Version : 80011 (8.0.11-TiDB-v8.5.1)
 File Encoding         : 65001

 Date: 13/05/2025 11:15:58
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for alembic_version
-- ----------------------------
DROP TABLE IF EXISTS `alembic_version`;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`) /*T![clustered_index] CLUSTERED */
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for api_keys
-- ----------------------------
DROP TABLE IF EXISTS `api_keys`;
CREATE TABLE `api_keys` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` int NOT NULL AUTO_INCREMENT,
  `description` varchar(100) NOT NULL,
  `hashed_secret` varchar(255) NOT NULL,
  `api_key_display` varchar(100) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `user_id` char(32) NOT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  UNIQUE KEY `hashed_secret` (`hashed_secret`),
  KEY `fk_1` (`user_id`),
  CONSTRAINT `fk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for chat_engines
-- ----------------------------
DROP TABLE IF EXISTS `chat_engines`;
CREATE TABLE `chat_engines` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(256) NOT NULL,
  `engine_options` json DEFAULT NULL,
  `is_default` tinyint(1) NOT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `llm_id` int DEFAULT NULL,
  `fast_llm_id` int DEFAULT NULL,
  `reranker_id` int DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`fast_llm_id`),
  KEY `fk_2` (`llm_id`),
  KEY `fk_3` (`reranker_id`),
  CONSTRAINT `fk_1` FOREIGN KEY (`fast_llm_id`) REFERENCES `llms` (`id`),
  CONSTRAINT `fk_2` FOREIGN KEY (`llm_id`) REFERENCES `llms` (`id`),
  CONSTRAINT `fk_3` FOREIGN KEY (`reranker_id`) REFERENCES `reranker_models` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=90001;

-- ----------------------------
-- Table structure for chat_messages
-- ----------------------------
DROP TABLE IF EXISTS `chat_messages`;
CREATE TABLE `chat_messages` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` int NOT NULL AUTO_INCREMENT,
  `ordinal` int NOT NULL,
  `role` varchar(64) NOT NULL,
  `content` text DEFAULT NULL,
  `error` text DEFAULT NULL,
  `sources` json DEFAULT NULL,
  `trace_url` varchar(512) DEFAULT NULL,
  `finished_at` datetime DEFAULT NULL,
  `chat_id` char(32) NOT NULL,
  `user_id` char(32) DEFAULT NULL,
  `graph_data` json DEFAULT NULL,
  `post_verification_result_url` varchar(512) DEFAULT NULL,
  `meta` json DEFAULT NULL,
  `is_best_answer` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`chat_id`),
  KEY `fk_2` (`user_id`),
  KEY `ix_chat_message_is_best_answer` (`is_best_answer`),
  CONSTRAINT `fk_1` FOREIGN KEY (`chat_id`) REFERENCES `chats` (`id`),
  CONSTRAINT `fk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=60001;

-- ----------------------------
-- Table structure for chat_meta
-- ----------------------------
DROP TABLE IF EXISTS `chat_meta`;
CREATE TABLE `chat_meta` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` int NOT NULL AUTO_INCREMENT,
  `chat_id` char(32) NOT NULL,
  `key` varchar(256) NOT NULL,
  `value` text DEFAULT NULL,
  `expires_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`chat_id`),
  KEY `ix_chat_meta_chat_id` (`chat_id`),
  UNIQUE KEY `ix_chat_meta_chat_id_key` (`chat_id`,`key`),
  KEY `ix_chat_meta_key` (`key`),
  CONSTRAINT `fk_1` FOREIGN KEY (`chat_id`) REFERENCES `chats` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for chats
-- ----------------------------
DROP TABLE IF EXISTS `chats`;
CREATE TABLE `chats` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` char(32) NOT NULL,
  `title` varchar(256) NOT NULL,
  `engine_id` int DEFAULT NULL,
  `engine_options` json DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `user_id` char(32) DEFAULT NULL,
  `browser_id` varchar(50) DEFAULT NULL,
  `origin` varchar(256) DEFAULT NULL,
  `visibility` int NOT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`engine_id`),
  KEY `fk_2` (`user_id`),
  KEY `ix_chats_id` (`id`),
  CONSTRAINT `fk_1` FOREIGN KEY (`engine_id`) REFERENCES `chat_engines` (`id`),
  CONSTRAINT `fk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for chunks_60001
-- ----------------------------
DROP TABLE IF EXISTS `chunks_60001`;
CREATE TABLE `chunks_60001` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` char(32) NOT NULL,
  `hash` varchar(64) NOT NULL,
  `text` text DEFAULT NULL,
  `meta` json DEFAULT NULL,
  `embedding` vector(2048) NOT NULL,
  `document_id` int DEFAULT NULL,
  `relations` json DEFAULT NULL,
  `source_uri` varchar(512) DEFAULT NULL,
  `index_status` enum('NOT_STARTED','PENDING','RUNNING','COMPLETED','FAILED') NOT NULL,
  `index_result` text DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`document_id`),
  KEY `ix_chunks_60001_id` (`id`),
  VECTOR INDEX `vec_idx_embedding`((VEC_COSINE_DISTANCE(`embedding`))),
  CONSTRAINT `fk_1` FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for data_sources
-- ----------------------------
DROP TABLE IF EXISTS `data_sources`;
CREATE TABLE `data_sources` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(256) NOT NULL,
  `description` varchar(512) NOT NULL,
  `data_source_type` varchar(256) NOT NULL,
  `config` json DEFAULT NULL,
  `build_kg_index` tinyint(1) NOT NULL,
  `user_id` char(32) DEFAULT NULL,
  `llm_id` int DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`user_id`),
  KEY `fk_2` (`llm_id`),
  CONSTRAINT `fk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_2` FOREIGN KEY (`llm_id`) REFERENCES `llms` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=90001;

-- ----------------------------
-- Table structure for database_connections
-- ----------------------------
DROP TABLE IF EXISTS `database_connections`;
CREATE TABLE `database_connections` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(256) NOT NULL,
  `description` varchar(512) NOT NULL,
  `description_for_llm` text DEFAULT NULL,
  `table_descriptions` json DEFAULT NULL COMMENT '表描述信息，格式: {table_name: description}',
  `column_descriptions` json DEFAULT NULL COMMENT '列描述信息，格式: {table_name: {column_name: description}}',
  `accessible_roles` json DEFAULT NULL,
  `database_type` varchar(32) NOT NULL,
  `config` json DEFAULT NULL,
  `user_id` char(32) DEFAULT NULL,
  `read_only` tinyint(1) NOT NULL DEFAULT '1',
  `connection_status` varchar(32) NOT NULL DEFAULT 'disconnected',
  `last_connected_at` datetime DEFAULT NULL,
  `metadata_cache` json DEFAULT NULL,
  `metadata_updated_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`user_id`),
  KEY `ix_database_connections_id` (`id`),
  CONSTRAINT `fk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for database_query_history
-- ----------------------------
DROP TABLE IF EXISTS `database_query_history`;
CREATE TABLE `database_query_history` (
  `id` int NOT NULL AUTO_INCREMENT,
  `chat_id` char(32) NOT NULL,
  `chat_message_id` int DEFAULT NULL,
  `user_id` char(32) DEFAULT NULL,
  `connection_id` int NOT NULL,
  `connection_name` varchar(256) NOT NULL,
  `database_type` varchar(32) NOT NULL,
  `question` text NOT NULL,
  `query` text NOT NULL,
  `is_successful` tinyint(1) NOT NULL DEFAULT '1',
  `error_message` text DEFAULT NULL,
  `result_summary` json DEFAULT NULL,
  `result_sample` json DEFAULT NULL,
  `execution_time_ms` int NOT NULL DEFAULT '0',
  `rows_returned` int NOT NULL DEFAULT '0',
  `routing_score` float DEFAULT NULL,
  `routing_context` json DEFAULT NULL,
  `user_feedback` int DEFAULT NULL,
  `user_feedback_comments` text DEFAULT NULL,
  `meta` json DEFAULT NULL,
  `executed_at` datetime NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`chat_id`),
  KEY `fk_2` (`chat_message_id`),
  KEY `fk_3` (`connection_id`),
  KEY `fk_4` (`user_id`),
  KEY `ix_database_query_history_chat_id` (`chat_id`),
  KEY `ix_database_query_history_chat_message_id` (`chat_message_id`),
  KEY `ix_database_query_history_connection_id` (`connection_id`),
  KEY `ix_database_query_history_user_id` (`user_id`),
  KEY `ix_database_query_history_executed_at` (`executed_at`),
  KEY `ix_db_query_history_chat_id_executed_at` (`chat_id`,`executed_at`),
  KEY `ix_db_query_history_connection_id_executed_at` (`connection_id`,`executed_at`),
  CONSTRAINT `fk_1` FOREIGN KEY (`chat_id`) REFERENCES `chats` (`id`),
  CONSTRAINT `fk_2` FOREIGN KEY (`chat_message_id`) REFERENCES `chat_messages` (`id`),
  CONSTRAINT `fk_3` FOREIGN KEY (`connection_id`) REFERENCES `database_connections` (`id`),
  CONSTRAINT `fk_4` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for documents
-- ----------------------------
DROP TABLE IF EXISTS `documents`;
CREATE TABLE `documents` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` int NOT NULL AUTO_INCREMENT,
  `hash` varchar(32) NOT NULL,
  `name` varchar(256) NOT NULL,
  `content` mediumtext DEFAULT NULL,
  `mime_type` varchar(128) NOT NULL,
  `source_uri` varchar(512) NOT NULL,
  `meta` json DEFAULT NULL,
  `last_modified_at` datetime DEFAULT NULL,
  `index_status` enum('NOT_STARTED','PENDING','RUNNING','COMPLETED','FAILED') NOT NULL,
  `index_result` text DEFAULT NULL,
  `data_source_id` int DEFAULT NULL,
  `knowledge_base_id` int DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_d_on_data_source_id` (`data_source_id`),
  KEY `fk_d_on_knowledge_base_id` (`knowledge_base_id`),
  CONSTRAINT `fk_d_on_data_source_id` FOREIGN KEY (`data_source_id`) REFERENCES `data_sources` (`id`),
  CONSTRAINT `fk_d_on_knowledge_base_id` FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=90001;

-- ----------------------------
-- Table structure for embedding_models
-- ----------------------------
DROP TABLE IF EXISTS `embedding_models`;
CREATE TABLE `embedding_models` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(64) NOT NULL,
  `provider` varchar(32) NOT NULL,
  `model` varchar(256) NOT NULL,
  `config` json DEFAULT NULL,
  `credentials` blob DEFAULT NULL,
  `is_default` tinyint(1) NOT NULL,
  `vector_dimension` int NOT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=30001;

-- ----------------------------
-- Table structure for entities_60001
-- ----------------------------
DROP TABLE IF EXISTS `entities_60001`;
CREATE TABLE `entities_60001` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(512) NOT NULL,
  `description` text DEFAULT NULL,
  `meta` json DEFAULT NULL,
  `entity_type` enum('original','synopsis') NOT NULL,
  `synopsis_info` json DEFAULT NULL,
  `description_vec` vector(2048) NOT NULL,
  `meta_vec` vector(2048) NOT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `idx_entity_name` (`name`),
  KEY `idx_entity_type` (`entity_type`),
  VECTOR INDEX `vec_idx_description_vec`((VEC_COSINE_DISTANCE(`description_vec`))),
  VECTOR INDEX `vec_idx_meta_vec`((VEC_COSINE_DISTANCE(`meta_vec`)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=30001;

-- ----------------------------
-- Table structure for evaluation_dataset_items
-- ----------------------------
DROP TABLE IF EXISTS `evaluation_dataset_items`;
CREATE TABLE `evaluation_dataset_items` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` int NOT NULL AUTO_INCREMENT,
  `query` text DEFAULT NULL,
  `reference` text DEFAULT NULL,
  `retrieved_contexts` json DEFAULT NULL,
  `extra` json DEFAULT NULL,
  `evaluation_dataset_id` int DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`evaluation_dataset_id`),
  CONSTRAINT `fk_1` FOREIGN KEY (`evaluation_dataset_id`) REFERENCES `evaluation_datasets` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for evaluation_datasets
-- ----------------------------
DROP TABLE IF EXISTS `evaluation_datasets`;
CREATE TABLE `evaluation_datasets` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `user_id` char(32) DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`user_id`),
  CONSTRAINT `fk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for evaluation_task_items
-- ----------------------------
DROP TABLE IF EXISTS `evaluation_task_items`;
CREATE TABLE `evaluation_task_items` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` int NOT NULL AUTO_INCREMENT,
  `chat_engine` varchar(255) NOT NULL,
  `status` varchar(32) NOT NULL,
  `query` text DEFAULT NULL,
  `reference` text DEFAULT NULL,
  `response` text DEFAULT NULL,
  `retrieved_contexts` json DEFAULT NULL,
  `extra` json DEFAULT NULL,
  `error_msg` text DEFAULT NULL,
  `factual_correctness` float DEFAULT NULL,
  `semantic_similarity` float DEFAULT NULL,
  `evaluation_task_id` int DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`evaluation_task_id`),
  CONSTRAINT `fk_1` FOREIGN KEY (`evaluation_task_id`) REFERENCES `evaluation_tasks` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for evaluation_tasks
-- ----------------------------
DROP TABLE IF EXISTS `evaluation_tasks`;
CREATE TABLE `evaluation_tasks` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `user_id` char(32) DEFAULT NULL,
  `dataset_id` int DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`user_id`),
  CONSTRAINT `fk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for feedbacks
-- ----------------------------
DROP TABLE IF EXISTS `feedbacks`;
CREATE TABLE `feedbacks` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `feedback_type` enum('LIKE','DISLIKE') NOT NULL,
  `comment` varchar(500) NOT NULL,
  `id` int NOT NULL AUTO_INCREMENT,
  `chat_id` char(32) NOT NULL,
  `chat_message_id` int NOT NULL,
  `user_id` char(32) DEFAULT NULL,
  `origin` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`chat_id`),
  KEY `fk_2` (`chat_message_id`),
  KEY `fk_3` (`user_id`),
  CONSTRAINT `fk_1` FOREIGN KEY (`chat_id`) REFERENCES `chats` (`id`),
  CONSTRAINT `fk_2` FOREIGN KEY (`chat_message_id`) REFERENCES `chat_messages` (`id`),
  CONSTRAINT `fk_3` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for knowledge_base_datasources
-- ----------------------------
DROP TABLE IF EXISTS `knowledge_base_datasources`;
CREATE TABLE `knowledge_base_datasources` (
  `knowledge_base_id` int NOT NULL,
  `data_source_id` int NOT NULL,
  PRIMARY KEY (`knowledge_base_id`,`data_source_id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`data_source_id`),
  CONSTRAINT `fk_1` FOREIGN KEY (`data_source_id`) REFERENCES `data_sources` (`id`),
  CONSTRAINT `fk_2` FOREIGN KEY (`knowledge_base_id`) REFERENCES `knowledge_bases` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for knowledge_bases
-- ----------------------------
DROP TABLE IF EXISTS `knowledge_bases`;
CREATE TABLE `knowledge_bases` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `description` mediumtext DEFAULT NULL,
  `index_methods` json DEFAULT NULL,
  `llm_id` int DEFAULT NULL,
  `embedding_model_id` int DEFAULT NULL,
  `documents_total` int NOT NULL,
  `data_sources_total` int NOT NULL,
  `created_by` char(32) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_by` char(32) DEFAULT NULL,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `deleted_by` char(32) DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `chunking_config` json DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`created_by`),
  KEY `fk_2` (`deleted_by`),
  KEY `fk_3` (`embedding_model_id`),
  KEY `fk_4` (`llm_id`),
  KEY `fk_5` (`updated_by`),
  CONSTRAINT `fk_1` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_2` FOREIGN KEY (`deleted_by`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_3` FOREIGN KEY (`embedding_model_id`) REFERENCES `embedding_models` (`id`),
  CONSTRAINT `fk_4` FOREIGN KEY (`llm_id`) REFERENCES `llms` (`id`),
  CONSTRAINT `fk_5` FOREIGN KEY (`updated_by`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=90001;

-- ----------------------------
-- Table structure for llms
-- ----------------------------
DROP TABLE IF EXISTS `llms`;
CREATE TABLE `llms` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(64) NOT NULL,
  `provider` varchar(32) NOT NULL,
  `model` varchar(256) NOT NULL,
  `config` json DEFAULT NULL,
  `credentials` blob DEFAULT NULL,
  `is_default` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=60001;

-- ----------------------------
-- Table structure for recommend_questions
-- ----------------------------
DROP TABLE IF EXISTS `recommend_questions`;
CREATE TABLE `recommend_questions` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` int NOT NULL AUTO_INCREMENT,
  `questions` json DEFAULT NULL,
  `chat_message_id` int NOT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`chat_message_id`),
  KEY `ix_recommend_questions_chat_message_id` (`chat_message_id`),
  CONSTRAINT `fk_1` FOREIGN KEY (`chat_message_id`) REFERENCES `chat_messages` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=30001;

-- ----------------------------
-- Table structure for relationships_60001
-- ----------------------------
DROP TABLE IF EXISTS `relationships_60001`;
CREATE TABLE `relationships_60001` (
  `id` int NOT NULL AUTO_INCREMENT,
  `description` text DEFAULT NULL,
  `meta` json DEFAULT NULL,
  `weight` int NOT NULL,
  `source_entity_id` int NOT NULL,
  `target_entity_id` int NOT NULL,
  `last_modified_at` datetime DEFAULT NULL,
  `document_id` int DEFAULT NULL,
  `chunk_id` char(32) DEFAULT NULL,
  `description_vec` vector(2048) NOT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`source_entity_id`),
  KEY `fk_2` (`target_entity_id`),
  VECTOR INDEX `vec_idx_description_vec`((VEC_COSINE_DISTANCE(`description_vec`))),
  CONSTRAINT `fk_1` FOREIGN KEY (`source_entity_id`) REFERENCES `entities_60001` (`id`),
  CONSTRAINT `fk_2` FOREIGN KEY (`target_entity_id`) REFERENCES `entities_60001` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=30001;

-- ----------------------------
-- Table structure for reranker_models
-- ----------------------------
DROP TABLE IF EXISTS `reranker_models`;
CREATE TABLE `reranker_models` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `name` varchar(64) NOT NULL,
  `provider` varchar(32) NOT NULL,
  `model` varchar(256) NOT NULL,
  `top_n` int NOT NULL,
  `config` json DEFAULT NULL,
  `is_default` tinyint(1) NOT NULL,
  `id` int NOT NULL AUTO_INCREMENT,
  `credentials` blob DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=30001;

-- ----------------------------
-- Table structure for semantic_cache
-- ----------------------------
DROP TABLE IF EXISTS `semantic_cache`;
CREATE TABLE `semantic_cache` (
  `id` int NOT NULL AUTO_INCREMENT,
  `query` text DEFAULT NULL,
  `query_vec` vector(1536) DEFAULT NULL COMMENT 'hnsw(distance=cosine)',
  `value` text DEFAULT NULL,
  `value_vec` vector(1536) DEFAULT NULL COMMENT 'hnsw(distance=cosine)',
  `meta` json DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin /*T![ttl] TTL=`created_at` + INTERVAL 1 MONTH */ /*T![ttl] TTL_ENABLE='ON' */ /*T![ttl] TTL_JOB_INTERVAL='1h' */;

-- ----------------------------
-- Table structure for site_settings
-- ----------------------------
DROP TABLE IF EXISTS `site_settings`;
CREATE TABLE `site_settings` (
  `created_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6),
  `updated_at` datetime(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(256) NOT NULL,
  `data_type` varchar(256) NOT NULL,
  `value` json DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=60001;

-- ----------------------------
-- Table structure for staff_action_logs
-- ----------------------------
DROP TABLE IF EXISTS `staff_action_logs`;
CREATE TABLE `staff_action_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action` varchar(255) NOT NULL,
  `action_time` datetime DEFAULT CURRENT_TIMESTAMP,
  `target_type` varchar(255) NOT NULL,
  `target_id` int NOT NULL,
  `before` json DEFAULT NULL,
  `after` json DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=30001;

-- ----------------------------
-- Table structure for uploads
-- ----------------------------
DROP TABLE IF EXISTS `uploads`;
CREATE TABLE `uploads` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `size` int NOT NULL,
  `path` varchar(255) NOT NULL,
  `mime_type` varchar(128) NOT NULL,
  `user_id` char(32) DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`user_id`),
  CONSTRAINT `fk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=90001;

-- ----------------------------
-- Table structure for user_sessions
-- ----------------------------
DROP TABLE IF EXISTS `user_sessions`;
CREATE TABLE `user_sessions` (
  `token` varchar(43) NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `user_id` char(32) NOT NULL,
  PRIMARY KEY (`token`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_1` (`user_id`),
  CONSTRAINT `fk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `id` char(32) NOT NULL,
  `email` varchar(255) NOT NULL,
  `hashed_password` varchar(255) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `is_verified` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  UNIQUE KEY `ix_users_email` (`email`),
  KEY `ix_users_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

SET FOREIGN_KEY_CHECKS = 1;
