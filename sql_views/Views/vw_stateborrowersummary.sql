CREATE VIEW vw_stateborrowersummary AS
SELECT
    StateCode,
    COUNT(BorrowerKey) AS TotalBorrowers,
    COUNT(DISTINCT LoanId) AS TotalLoans
FROM DimBorrower
GROUP BY StateCode;