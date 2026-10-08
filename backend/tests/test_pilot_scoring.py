import unittest
from scripts.run_retrieval_pilot import coverage

class PilotScoringTests(unittest.TestCase):
    def test_partial_paragraph_hit_does_not_count_as_complete_clause(self):
        groups={'condition':{'source_evidence_ids':{'zh-Hant':['zh1','zh2'],'en':['en1','en2']}}}
        self.assertEqual(coverage(['condition'],groups,{'zh1','en2'}), [])
        self.assertEqual(coverage(['condition'],groups,{'en1','en2'}), ['condition'])
    def test_footnote_expansion_is_scored_separately(self):
        groups={'body':{'source_evidence_ids':{'zh-Hant':['zh-body'],'en':['en-body']}},
                'scope':{'source_evidence_ids':{'zh-Hant':['zh-note'],'en':['en-note']}}}
        direct={'en-body'}
        self.assertEqual(coverage(['body','scope'],groups,direct), ['body'])
        self.assertEqual(coverage(['body','scope'],groups,direct|{'en-note'}), ['body','scope'])
