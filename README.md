## Dataset Directory Listing

An W3C XML Schema to address [this question](https://datascience.stackexchange.com/questions/26725/rfc-data-set-metadata-standard-format). Feel free to contribute!

```xml
<?xml version="1.0" encoding="utf-8"?>
<dataset
 xmlns="http://zougloub.github.io/dsdir/v1"
 >
 <rdf:RDF
  xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  >
  <dc:date>2018-01-16</dc:date>
  <dc:rights>Under the MIT License</dc:rights>
 </rdf:RDF>
 <contents>
  <file name="README.md" />
  <file name="schema-v1.xsd" hash="sha1:09e3a95bf9b019493cb239a0d993633462416ade" />
  <file name="_config.yml" hash="sha1:c4192631f25b34d77a7f159aa0da0e3ae99c4ef4" />
 </contents>
</dataset>
```

Provided resources:

- W3C XML Schema `schema-v1.xsd`, which can be inspected for more information;
- Python tool/module `dsdir.py` that can create and validate records.

Considerations:

- When performing integrity testing, any stated information is validated;
- Hashes are optional;
- SHA1 file hashes;
- `git-sha1` file and tree hashes, using a SHA1-based hash as computed by git.

