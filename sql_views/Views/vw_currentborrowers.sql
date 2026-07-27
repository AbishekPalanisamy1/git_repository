CREATE VIEW vw_currentborrowers AS
SELECT
    BorrowerKey,
    BGLoanLinkId,
    LoanId,
    BorrowerName,
    BorrowerRole,
    City,
    StateCode
FROM DimBorrower
WHERE IsCurrent = 1;