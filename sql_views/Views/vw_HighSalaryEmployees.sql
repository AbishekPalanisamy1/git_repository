CREATE VIEW vw_HighSalaryEmployees AS
SELECT
    empid,
    empname,
    saary,
    department_id
FROM employee
WHERE salary < 60000;