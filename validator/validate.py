from argparse import ArgumentParser
from lxml import etree
from io import StringIO
from io import BytesIO
import json
import sys
import os
import logging
import re
import requests

token_file = os.path.join(os.path.dirname(__file__), "token.txt")
with open(token_file) as fp:
    TOKEN = fp.read()


def load_xsd_file(filename):
    """
    load XSD file and parse it as etree.XMLSchema
    """
    with open(filename, 'rb') as fp:
        doc = etree.parse(BytesIO(fp.read()))
        return etree.XMLSchema(doc)


def load_xml_file(filename):
    """
    load XML from file
    """
    with open(filename, 'rb') as fp:
        return etree.parse(BytesIO(fp.read()))


def classify_error(msg):
    """
    parse xml schema error and classify
    """
    regex_elem_content = re.compile('^<(.+)>.+' +
                                    'ERROR:SCHEMASV:SCHEMAV_ELEMENT_CONTENT:' +
                                    ' Element \\\'{.+}(.*?)\\\': +(.*?)\\. +' +
                                    'Expected[^(]+(\\((.*)\\))?.+$')

    regex_parse_ns_field = re.compile('^{.+}(.*)$')

    def classify_error_details(items):
        ret = []
        for item in items:
            item = item.strip()
            m2 = regex_parse_ns_field.match(item)
            if m2 is None:
                smsg = str(msg)
                raise RuntimeError('cannot deduce error type:\n{0}'.format(smsg))
            else:
                ret.append(m2.group(1))
        ret.sort()
        return ret

    m = regex_elem_content.match(str(msg))
    if m is None:
        smsg = str(msg)
        raise RuntimeError('cannot deduce error type:\n{0}'.format(smsg))
    else:
        return {
            'errtype': m.group(1),
            'element': m.group(2),
            'msg': m.group(3),
            'details': (classify_error_details(m.group(5).split(','))
                        if m.group(4)
                        else [])
        }


def validate_xml(schema, doc, community=None, name=None):
    """
    validate document against schema
    """
    ret = {
        'community': ('unknown' if community is None else community),
        'name': ('unknown' if name is None else name),
        'errtype': False,
        'element': '',
        'msg': '',
        'details': []
    }
    try:
        schema.assertValid(doc)
        return ret
    except etree.DocumentInvalid as err:
        log = schema.error_log
        for item in log:
            err = classify_error(item)
            ret.update(err)
            return ret
    except Exception as e:
        print('Unknown error, exiting:' + str(e))
        raise


def iterate_records(baseurl):
    """
    Iterate over all records exposed by the B2SHARE server
    """
    url = "{0}/api/records/?access_token={1}".format(baseurl, TOKEN)
    while url:
        r = requests.get(url)
        data = r.json()
        for hit in data.get('hits', {}).get('hits', []):
            yield hit
        url = data.get('links', {}).get('next', None)
        if url:
            url = '{0}?access_token={1}'.format(url, TOKEN)


def get_oai_pmh(baseurl, record_id, prefix):
    """
    retrieve OAI PMH xml
    """
    tmp_url = '{baseurl}/api/oai2d?verb=GetRecord&metadataPrefix={prefix}'
    tmp_url += '&identifier=oai:b2share.eudat.eu:b2rec/{record_id}'
    url = tmp_url.format(baseurl=baseurl,
                         prefix=prefix,
                         record_id=record_id)
    doc = etree.parse(url)
    return doc


def get_data_cite_resource(oai_xml):
    resource = oai_xml.find('.//ns:GetRecord/ns:record/ns:metadata/dc:resource',
                            {'ns': "http://www.openarchives.org/OAI/2.0/",
                             'dc': "http://datacite.org/schema/kernel-3"})
    return etree.ElementTree(resource)


def main():
    descr = 'Validate Datacite / OpenAire Schemas.'
    parser = ArgumentParser(description=descr)
    parser.add_argument('--schema', type=str, help='XSD file', required=True)
    parser.add_argument('--xmlfile', type=str, help='input file')
    parser.add_argument('--baseurl', type=str, help='url',
                        default="http://127.0.0.1:5000")
    args = parser.parse_args()
    schema = load_xsd_file(args.schema)
    print("i,community,name,errtype,element,details")
    if args.xmlfile is not None:
        doc = load_xml_file(args.xmlfile)
        result = validate_xml(schema, doc, name=args.xmlfile)
        print(json.dumps(result))
    else:
        baseurl = args.baseurl
        i = 1
        for record in iterate_records(baseurl):
            community = record.get('metadata', {}).get('community', '')
            oai_pmh = get_oai_pmh(baseurl, record['id'], 'oai_datacite')
            resource = get_data_cite_resource(oai_pmh)
            validation = validate_xml(schema,
                                      resource,
                                      community=community,
                                      name=record['id'])
            validation['details'] = "/".join(validation['details'])
            if not validation['errtype']:
                validation['errtype'] = '' 
            print("{i},{community},{name},{errtype},{element},{details}".
                  format(i=i, **validation))
            i += 1


if __name__ == "__main__":
    main()
