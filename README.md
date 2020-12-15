# AWS-CE-Usage-Type-Tool
Lambda for pulling AWS Cost Explorer Records for Usage Type Groups

------
Summary
------
This toolset is useful for exporting AWS cost explorer USAGE TYPE GROUP data into JSON records. Each usage type group is dumped to a different JSON file in the specific S3 bucket. Data can be analysed by any data visualization tool supporting JSON (all of them). When using Quicksight, see my other project for parsing S3 files into corresponding dataset folders. 

By default, the script grabs the last year of data at monthly intervals

-------
Record Details
-------

Each record contains:
- Record Type
- Billing Month
- Region
- Usage Amount
- Usage Cost
- Account Number

