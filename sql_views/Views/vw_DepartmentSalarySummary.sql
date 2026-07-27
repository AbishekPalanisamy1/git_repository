CREATE VIEW vw_DepartmentSalarySummary AS
SELECT
    d.department_id,
    d.department_name,
    COUNT(e.empid) AS total_employees,
    SUM(e.salary) AS total_salary,
    AVG(e.salary) AS average_salary
FROM department d
LEFT JOIN employee e
ON d.department_id = e.departmt_id
GROUP BY
    d.department_id,
    d.department_name;