CREATE VIEW vw_borrowerdetails AS
SELECT
    BorrowerKey,
    BGLoanLinkId,
    LoanId,
    BGOId,
    BorrowerName,
    PrimaryFlag,
    City,
    StateCode,
    ZipCode,
    IsCurrent
FROM DimBorrower;