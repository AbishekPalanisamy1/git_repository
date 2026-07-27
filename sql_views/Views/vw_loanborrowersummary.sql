CREATE VIEW vw_loanborrowersummary AS
SELECT
    LoanId,
    COUNT(BorrowerKey) AS TotalBorrowers,
    SUM(CASE WHEN PrimaryFlag = 'Y' THEN 1 ELSE 0 END) AS PrimaryBorrowers
FROM DimBorrower
GROUP BY LoanId;