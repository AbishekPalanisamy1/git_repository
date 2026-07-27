CREATE VIEW vw_borrowerdetails AS
SELECT
    BorrowerKey,
    BGLoanLinkId,
    LoanId,
    BGOId,
    BorrowerName,
    BorrowerRole,
    PrimaryFlag,
    City,
    StateCode,
    ZipCode,
    IsCurrent
FROM DimBorrower;