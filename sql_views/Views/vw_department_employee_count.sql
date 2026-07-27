CREATE VIEW vw_department_employee_count AS
SELECT
    d.department_id,
    d.department_name,
    COUNT(e.empid) AS employee_count
FROM department d
LEFT JOIN employee e
ON d.department_id = e.department_id
GROUP BY d.department_id, d.department_name;