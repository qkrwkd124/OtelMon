CREATE TABLE IF NOT EXISTS alert_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    process_execution_id INT NOT NULL UNIQUE,
    platform_type VARCHAR(200),
    group_name VARCHAR(200),
    process_name VARCHAR(200),
    end_time DATETIME,
    alert_sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
);