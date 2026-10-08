import copy,json,unittest
from evaluation.full_alignment import ROOT,load_full_review,validate_full_review
from backend.app.rag.preprocess import build,source_hash

class FullAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.review,_=load_full_review()
        self.sources={key:(ROOT/path).read_bytes() for key,path in {'pdf':'docs/FLEXI-ULife Prime Saver.pdf','evidence':'data/processed/knowledge/evidence.json','normalized':'data/processed/mineru/pages.json'}.items()}
        self.evidence={e['evidence_id']:e for e in json.loads(self.sources['evidence'])}
        self.pages=json.loads(self.sources['normalized'])
    def test_discarded_disclaimer_and_customer_address_survive_cleaning(self):
        config=json.loads((ROOT/'data/processed/mineru/corrections.json').read_text());config['original_pages']=self.pages
        result=build(self.pages,config,source_hash(self.sources['normalized']))
        evidence={e['evidence_id']:e for e in result['evidence']}
        self.assertIn('does not form part of the Policy',evidence['p019-d001']['text'])
        self.assertEqual(evidence['p019-d001']['source_pointer'],'/pdf_info/18/discarded_blocks/0')
        self.assertIn('Customer Service',evidence['p020-d001']['text'])
        self.assertTrue(any('p019-d001' in c['evidence_ids'] for c in result['chunks']))
        self.assertNotIn('first 14 years',evidence['p018-b001-t1-r2']['text'])
        self.assertNotIn('0-75',evidence['p018-b002-t1-r2']['text'])
    def test_missing_review_or_discarded_audit_is_rejected(self):
        review=copy.deepcopy(self.review);review['context_only'].pop()
        with self.assertRaisesRegex(ValueError,'no review disposition'):
            validate_full_review(review,self.evidence,self.sources,self.pages)
        review=copy.deepcopy(self.review);review['discarded_block_audit'].pop()
        with self.assertRaisesRegex(ValueError,'fully audited'):
            validate_full_review(review,self.evidence,self.sources,self.pages)
    def test_original_conflicts_and_visual_limits_remain_explicit(self):
        result=validate_full_review(self.review,self.evidence,self.sources,self.pages)
        self.assertEqual(result['status_counts']['CONFLICT'],2)
        self.assertFalse(result['all_pdf_visual_content_indexed'])
        self.assertIn('SOURCE_CONFLICT',self.evidence['p011-b015']['review_flags'])
        changed=dict(self.sources);changed['evidence']+=b' '
        with self.assertRaisesRegex(ValueError,'stale'):
            validate_full_review(self.review,self.evidence,changed,self.pages)
