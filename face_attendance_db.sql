-- phpMyAdmin SQL Dump
-- version 5.2.0
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Dec 09, 2025 at 10:41 AM
-- Server version: 8.0.30
-- PHP Version: 8.3.13

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `face_attendance_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `attendance`
--

CREATE TABLE `attendance` (
  `id` int NOT NULL,
  `student_id` int DEFAULT NULL,
  `nim` varchar(20) DEFAULT NULL,
  `name` varchar(100) DEFAULT NULL,
  `date` date NOT NULL,
  `time` time NOT NULL,
  `status` varchar(20) DEFAULT 'Hadir',
  `confidence` float DEFAULT NULL,
  `lighting_condition` varchar(50) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------

--
-- Table structure for table `students`
--

CREATE TABLE `students` (
  `id` int NOT NULL,
  `nim` varchar(20) NOT NULL,
  `name` varchar(100) NOT NULL,
  `face_id` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `students`
--

INSERT INTO `students` (`id`, `nim`, `name`, `face_id`, `created_at`) VALUES
(4, '22081010049', 'Gevanno', 0, '2025-12-09 09:56:50'),
(5, '22043010122', 'Gavrila', 1, '2025-12-09 09:58:08');

-- --------------------------------------------------------

--
-- Table structure for table `system_logs`
--

CREATE TABLE `system_logs` (
  `id` int NOT NULL,
  `activity` varchar(255) DEFAULT NULL,
  `details` text,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `system_logs`
--

INSERT INTO `system_logs` (`id`, `activity`, `details`, `created_at`) VALUES
(1, 'New student registered: Gevanno', 'NIM: 22081010049, Face ID: 0', '2025-12-09 09:40:41'),
(2, 'New student registered: Tes', 'NIM: 2208101099, Face ID: 1', '2025-12-09 09:44:10'),
(3, 'Attendance recorded for Gevanno', 'NIM: 22081010049, Confidence: 65.36', '2025-12-09 09:44:51'),
(4, 'Attendance recorded for Tes', 'NIM: 2208101099, Confidence: 65.33', '2025-12-09 09:45:06'),
(5, 'New student registered: Gevanno', 'NIM: 22081010049, Face ID: 0', '2025-12-09 09:49:56'),
(6, 'Attendance recorded for Gevanno', 'NIM: 22081010049, Confidence: 60.88', '2025-12-09 09:52:04'),
(7, 'Attendance recorded for Gevanno', 'NIM: 22081010049, Confidence: 60.65', '2025-12-09 09:54:00'),
(8, 'New student registered: Gevanno', 'NIM: 22081010049, Face ID: 0', '2025-12-09 09:56:50'),
(9, 'New student registered: Gavrila', 'NIM: 22043010122, Face ID: 1', '2025-12-09 09:58:08'),
(10, 'Attendance recorded for Gevanno', 'NIM: 22081010049, Confidence: 64.12', '2025-12-09 09:58:23'),
(11, 'Attendance recorded for Gavrila', 'NIM: 22043010122, Confidence: 61.47', '2025-12-09 09:59:12'),
(12, 'Attendance recorded for Gevanno', 'NIM: 22081010049, Confidence: 65.1', '2025-12-09 10:12:47'),
(13, 'Attendance recorded for Gavrila', 'NIM: 22043010122, Confidence: 60.2', '2025-12-09 10:15:23'),
(14, 'Attendance recorded for Gevanno', 'NIM: 22081010049, Confidence: 60.8', '2025-12-09 10:18:15');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `attendance`
--
ALTER TABLE `attendance`
  ADD PRIMARY KEY (`id`),
  ADD KEY `student_id` (`student_id`);

--
-- Indexes for table `students`
--
ALTER TABLE `students`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `nim` (`nim`);

--
-- Indexes for table `system_logs`
--
ALTER TABLE `system_logs`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `attendance`
--
ALTER TABLE `attendance`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=10;

--
-- AUTO_INCREMENT for table `students`
--
ALTER TABLE `students`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT for table `system_logs`
--
ALTER TABLE `system_logs`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=15;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `attendance`
--
ALTER TABLE `attendance`
  ADD CONSTRAINT `attendance_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
