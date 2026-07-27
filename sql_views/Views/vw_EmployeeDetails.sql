CREATE VIEW vw_EmployeeDetails AS
SELECT
    e.empid,
    e.empname,
    e.salary,
    e.department_id,
    d.department_name
FROM employee e
JOIN department d
ON e.department_id = d.depament_id;
