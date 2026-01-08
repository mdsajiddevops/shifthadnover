-- Problem Tickets Tables Migration
-- Run this SQL to create the Problem Ticket and Problem Task tables

-- Problem Ticket table
CREATE TABLE IF NOT EXISTS problem_ticket (
    id INT AUTO_INCREMENT PRIMARY KEY,
    problem_number VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    app_name VARCHAR(255),
    priority VARCHAR(32) NOT NULL DEFAULT 'Medium',
    status VARCHAR(32) NOT NULL DEFAULT 'Open',
    root_cause TEXT,
    workaround TEXT,
    resolution TEXT,
    owner_id INT,
    created_date DATETIME,
    target_resolution_date DATETIME,
    actual_resolution_date DATETIME,
    account_id INT NOT NULL,
    team_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES team_member(id) ON DELETE SET NULL,
    FOREIGN KEY (account_id) REFERENCES account(id) ON DELETE CASCADE,
    FOREIGN KEY (team_id) REFERENCES team(id) ON DELETE CASCADE,
    UNIQUE KEY _team_problem_number_uc (team_id, problem_number)
);

-- Problem Task (PTask) table
CREATE TABLE IF NOT EXISTS problem_task (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ptask_number VARCHAR(50) NOT NULL,
    problem_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'Open',
    assigned_to_id INT,
    due_date DATETIME,
    completion_date DATETIME,
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (problem_id) REFERENCES problem_ticket(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to_id) REFERENCES team_member(id) ON DELETE SET NULL
);

-- Create indexes for better performance
CREATE INDEX idx_problem_ticket_status ON problem_ticket(status);
CREATE INDEX idx_problem_ticket_priority ON problem_ticket(priority);
CREATE INDEX idx_problem_ticket_team ON problem_ticket(team_id);
CREATE INDEX idx_problem_ticket_account ON problem_ticket(account_id);
CREATE INDEX idx_problem_task_status ON problem_task(status);
CREATE INDEX idx_problem_task_problem ON problem_task(problem_id);

