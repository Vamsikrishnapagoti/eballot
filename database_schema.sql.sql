-- database_schema.sql
-- EBallot Database Schema

-- Create Database
CREATE DATABASE IF NOT EXISTS eballot_db;
USE eballot_db;

-- Voters Table
CREATE TABLE voters (
    voter_id VARCHAR(20) PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    middle_name VARCHAR(50),
    last_name VARCHAR(50) NOT NULL,
    mobile VARCHAR(10) NOT NULL UNIQUE,
    aadhar VARCHAR(12) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    date_of_birth DATE NOT NULL,
    residential_address TEXT NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    registered_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_email (email),
    INDEX idx_mobile (mobile),
    INDEX idx_aadhar (aadhar)
);

-- Elections Table
CREATE TABLE elections (
    election_id VARCHAR(50) PRIMARY KEY,
    election_name VARCHAR(200) NOT NULL,
    description TEXT,
    start_date DATETIME NOT NULL,
    end_date DATETIME NOT NULL,
    status ENUM('upcoming', 'active', 'completed') DEFAULT 'upcoming',
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_dates (start_date, end_date)
);

-- Candidates Table
CREATE TABLE candidates (
    candidate_id INT AUTO_INCREMENT PRIMARY KEY,
    election_id VARCHAR(50) NOT NULL,
    candidate_name VARCHAR(100) NOT NULL,
    party_name VARCHAR(100),
    description TEXT,
    photo_url VARCHAR(255),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (election_id) REFERENCES elections(election_id) ON DELETE CASCADE,
    INDEX idx_election (election_id)
);

-- Votes Table
CREATE TABLE votes (
    vote_id INT AUTO_INCREMENT PRIMARY KEY,
    voter_id VARCHAR(20) NOT NULL,
    election_id VARCHAR(50) NOT NULL,
    candidate_id INT NOT NULL,
    vote_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    FOREIGN KEY (voter_id) REFERENCES voters(voter_id) ON DELETE CASCADE,
    FOREIGN KEY (election_id) REFERENCES elections(election_id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    UNIQUE KEY unique_vote (voter_id, election_id),
    INDEX idx_voter (voter_id),
    INDEX idx_election (election_id),
    INDEX idx_candidate (candidate_id)
);

-- Audit Log Table
CREATE TABLE audit_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    voter_id VARCHAR(20),
    action VARCHAR(100) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_voter (voter_id),
    INDEX idx_timestamp (timestamp)
);

-- Sample Data for Testing
INSERT INTO elections (election_id, election_name, description, start_date, end_date, status) VALUES
('presidential2025', 'Presidential Election 2025', 'National Presidential Election', '2025-11-01 00:00:00', '2025-11-15 23:59:59', 'active'),
('governor2025', 'State Governor Election', 'State Governor Election 2025', '2025-11-03 00:00:00', '2025-11-20 23:59:59', 'active'),
('council2025', 'City Council Election', 'Local City Council Election', '2025-10-28 00:00:00', '2025-11-10 23:59:59', 'active');

INSERT INTO candidates (election_id, candidate_name, party_name, description) VALUES
('presidential2025', 'John Anderson', 'Democratic Party', 'Focus on Education & Healthcare'),
('presidential2025', 'Sarah Mitchell', 'Republican Party', 'Economic Growth & Security'),
('presidential2025', 'Robert Chen', 'Independent', 'Climate Action & Technology'),
('presidential2025', 'Maria Rodriguez', 'Green Party', 'Environmental Justice & Reform'),
('governor2025', 'Michael Brown', 'Democratic Party', 'Infrastructure Development'),
('governor2025', 'Emily White', 'Republican Party', 'Tax Reform & Business Growth'),
('council2025', 'David Lee', 'Independent', 'Community Safety & Parks'),
('council2025', 'Jessica Taylor', 'Green Party', 'Sustainability & Green Spaces');
