CREATE TABLE employee_details_14 (
    emp_id INT PRIMARY KEY,
    emp_name VARCHAR(100) NOT NULL,
    dept_id INT,
    salary FLOAT CHECK (salary > 0),
    join_date DATE DEFAULT GETDATE(),
    status VARCHAR(20) DEFAULT 'Active'
);
