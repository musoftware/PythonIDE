# DelphiBinaryDfm - Delphi project with a BINARY form file (test fixture)

`AboutBox.dfm` is in the old binary (TPF0) format, produced from `../DelphiVclDemo/AboutBox.dfm` with
Free Pascal's `ObjectTextToBinary`. RAD IDE converts it to text when opening (with a warning in the
Output window) and saves it as a text .dfm (Delphi reads both formats).
