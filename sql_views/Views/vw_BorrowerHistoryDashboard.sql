CREATE VIEW vw_BorrowerHistoryDashboard
AS
SELECT
    EmpId,
    EmpName,
    Salary
FROM Employee
WHERE Salary > 50000;