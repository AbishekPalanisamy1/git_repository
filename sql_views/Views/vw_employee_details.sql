CREATE VIEW vw_employee_details AS
SELECT
    e.empid,
    e.emp_name,
    e.gender,
    e.salary,
    d.department_name
FROM employee e
LEFT JOIN department d
ON e.department_id = d.department_id;


