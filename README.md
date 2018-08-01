## Dataset Directory Listing


A toolset to address [this question](https://datascience.stackexchange.com/questions/26725/rfc-data-set-metadata-standard-format).
Feel free to contribute!

The XML solution has a W3C XML Schema and looks like:

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

The YAML solution looks like:

```yaml
!dsdir
size: 21429
hash: {git-sha1: abf261edf031396dcc5a463c6c638c2ed6a6aba8}
contents:
- dsdir/:
    size: 21429
    hash: {git-sha1: 054d524a6b8ddb78f5888a390cbf75ddd2ef2cb6}
    contents:
    - __init__.py:
        size: 7527
        hash: {git-sha1: b7d1aceb2e4d3cc787a384e2d30550f42c7d6646}
    - __main__.py:
        size: 2859
        hash: {git-sha1: e614fd653bb12f2f17852a182fee8d46c0c37193}
    - xml/:
        size: 5933
        hash: {git-sha1: 37683ef68fa16d6c7dea515025ab6cb6d31a2085}
        contents:
        - __init__.py:
            size: 3629
            hash: {git-sha1: 596d79b69c6b7a7b8518936aeb4de518e46e201e}
        - schema-v1.xsd:
            size: 2304
            hash: {git-sha1: ced70b1c134abc3db312a4b70a81e0134a950c54}
    - yaml/:
        size: 5110
        hash: {git-sha1: 539599afda9069d07504ccd225412070d2ef6608}
        contents:
        - __init__.py:
            size: 5110
            hash: {git-sha1: 4352daed6c9059b1aab49a35a48809d81a8d1364}
```

Provided resources:

- W3C XML Schema `schema-v1.xsd`, which can be inspected for more information;
- Python tool/module `dsdir` that can create and validate records.

Considerations:

- When performing integrity testing, any stated information is validated;
- Hashes are optional;
- SHA1 file hashes;
- `git-sha1` file and tree hashes, using a SHA1-based hash as computed by git.

### Python dsdir usage

```sh
python -m dsdir create dsdir > dataset.xml
python -m dsdir validate dataset.xml

python -m dsdir --format yaml create dsdir --output dataset.yml
python -m dsdir --format yaml validate dataset.yml
```
