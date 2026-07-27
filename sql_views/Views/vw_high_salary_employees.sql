CREATE VIEW vw_high_salary_employees AS
SELECT
    empid,
    emp_name,
    department_id,
    salary
FROM employee
WHERE salary > (
    SELECT AV(salary)
    FROM employee
);


--aggregate function 