SET NAMES utf8mb4;
CREATE DATABASE IF NOT EXISTS dw DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
GRANT ALL PRIVILEGES ON dw.* TO 'didilili'@'%';
USE dw;

DROP TABLE IF EXISTS `artists`;
CREATE TABLE `artists` (`id` FLOAT, `name` VARCHAR(255), PRIMARY KEY (`id`));

DROP TABLE IF EXISTS `albums`;
CREATE TABLE `albums` (`id` FLOAT, `title` VARCHAR(255), `artist_id` FLOAT, PRIMARY KEY (`id`));

DROP TABLE IF EXISTS `employees`;
CREATE TABLE `employees` (`id` FLOAT, `last_name` VARCHAR(255), `first_name` VARCHAR(255), `title` VARCHAR(255), `reports_to` FLOAT, `birth_date` DATETIME, `hire_date` DATETIME, `address` VARCHAR(255), `city` VARCHAR(255), `state` VARCHAR(255), `country` VARCHAR(255), `postal_code` VARCHAR(255), `phone` VARCHAR(255), `fax` VARCHAR(255), `email` VARCHAR(255), PRIMARY KEY (`id`));

DROP TABLE IF EXISTS `customers`;
CREATE TABLE `customers` (`id` FLOAT, `first_name` VARCHAR(255), `last_name` VARCHAR(255), `company` VARCHAR(255), `address` VARCHAR(255), `city` VARCHAR(255), `state` VARCHAR(255), `country` VARCHAR(255), `postal_code` VARCHAR(255), `phone` VARCHAR(255), `fax` VARCHAR(255), `email` VARCHAR(255), `support_rep_id` FLOAT, PRIMARY KEY (`id`));

DROP TABLE IF EXISTS `genres`;
CREATE TABLE `genres` (`id` FLOAT, `name` VARCHAR(255), PRIMARY KEY (`id`));

DROP TABLE IF EXISTS `invoices`;
CREATE TABLE `invoices` (`id` FLOAT, `customer_id` FLOAT, `invoice_date` DATETIME, `billing_address` VARCHAR(255), `billing_city` VARCHAR(255), `billing_state` VARCHAR(255), `billing_country` VARCHAR(255), `billing_postal_code` VARCHAR(255), `total` FLOAT, PRIMARY KEY (`id`));

DROP TABLE IF EXISTS `media_types`;
CREATE TABLE `media_types` (`id` FLOAT, `name` VARCHAR(255), PRIMARY KEY (`id`));

DROP TABLE IF EXISTS `tracks`;
CREATE TABLE `tracks` (`id` FLOAT, `name` VARCHAR(255), `album_id` FLOAT, `media_type_id` FLOAT, `genre_id` FLOAT, `composer` VARCHAR(255), `milliseconds` FLOAT, `bytes` FLOAT, `unit_price` FLOAT, PRIMARY KEY (`id`));

DROP TABLE IF EXISTS `invoice_lines`;
CREATE TABLE `invoice_lines` (`id` FLOAT, `invoice_id` FLOAT, `track_id` FLOAT, `unit_price` FLOAT, `quantity` FLOAT, PRIMARY KEY (`id`));

DROP TABLE IF EXISTS `playlists`;
CREATE TABLE `playlists` (`id` FLOAT, `name` VARCHAR(255), PRIMARY KEY (`id`));

DROP TABLE IF EXISTS `playlist_tracks`;
CREATE TABLE `playlist_tracks` (`playlist_id` FLOAT, `track_id` FLOAT, PRIMARY KEY (`playlist_id`));
