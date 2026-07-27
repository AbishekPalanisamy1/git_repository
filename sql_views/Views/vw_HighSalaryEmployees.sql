CREATE VIEW vw_HighSalaryEmployees AS
SELECT
    empid,
    empname,
    salary,
    department_id
FROM employee
WHERE salary > 50000;