CREATE VIEW vw_EmployeeDetails AS
SELECT
    e.empid,
    e.empname,
    e.salary,
    e.department_id,
    d.department_name
FROM employee e
JOIN department d
<<<<<<< HEAD
ON e.department_id = d.deparent_id;
=======
ON e.department_id = d.deparment_id;
>>>>>>> 505dfd7867965af02e80e5818dfcd6de4376871a
