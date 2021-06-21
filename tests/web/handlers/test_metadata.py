'''
    Test Metadata Endpoint

    GET /v1/metadata
    GET /v1/metadata/fields

'''

from biothings.tests.web import BiothingsWebAppTest
from setup import setup_es  # pylint: disable=unused-import


class TestMetadata(BiothingsWebAppTest):

    def test_00_meta(self):
        """ GET /v1/metadata
        {
            "biothing_type": "gene",
            "build_date": "2020-01-19T02:00:00.027534",
            "build_version": "20200119",
            "src": { ... },
            "stats": { ... }
        }
        """
        res = self.request('/v1/metadata').json()
        assert res['biothing_type'] == 'gene'

    def test_01_meta_dev(self):
        """ GET /v1/metadata?dev
        {
            "biothing_type": "gene",
            "build_date": "2020-01-19T02:00:00.027534",
            "build_version": "20200119",
            "software": {
                "biothings": {
                    "commit-hash": "705a19d62c62529826fc1316e4956acede9d3673",
                    "master-commits": "1894",
                    "repository-url": "https://github.com/biothings/biothings.api.git",
                    "version": "0.6.dev"
                },
                "codebase": { ... },
                "python-info": { ... },
                "python-package-info": [ ... ]
            },
            ...
        }
        """
        res = self.request('/v1/metadata?dev').json()
        assert 'software' in res

    def test_10_field(self):
        """ GET /v1/metadata/fields
        {
            ...
            "refseq": { ... }
            "refseq.genomic": {
                "type": "text",
                "index": false
            },
            ...
        }
        """
        res = self.request('/v1/metadata/fields').json()
        assert not res['refseq.genomic']['index']

    def test_11_field_search(self):
        """ GET /v1/metadata/fields?search=HGNC
        {
            "HGNC": { ... },
            "pantherdb.HGNC": { ... },
            "pantherdb.ortholog.HGNC": { ... }
        }
        """
        res = self.request('/v1/metadata/fields?search=HGNC').json()
        assert res
        for key in res:
            assert 'HGNC' in key

    def test_12_field_prefix(self):
        """ GET /v1/metadata/fields?prefix=accession
        {
            "accession": { ... },
            "accession.genomic": { ... },
            "accession.protein": { ... },
            "accession.rna": { ... },
            "accession.translation": { ... },
            "accession_agg": { ... }
        }
        """
        res = self.request('/v1/metadata/fields?prefix=accession').json()
        assert res
        for key in res:
            assert key.startswith('accession')
