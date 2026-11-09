import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import enrich_content as e


def response(text):
    return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':text}]},
        'groundingMetadata':{'groundingChunks':[{'web':{'uri':'https://example.com/facts','title':'官方資料'}}]}}]}

class EnrichmentTests(unittest.TestCase):
    def test_banned(self):
        self.assertEqual(e.banned_phrases('您可搭車，這是完美行程'),['完美','您'])
        caller=Mock(return_value=(response('白馬車程30分。'*100),None))
        body,inline=e.prepare_body('key','您搭車30分。'*100,caller)
        self.assertFalse(e.banned_phrases(body));self.assertFalse(inline)
        self.assertNotIn('tools',caller.call_args.args[1])

    def test_remaining_banned_warns_and_keeps_body(self):
        caller=Mock(return_value=(response('您到白馬30分。'*100),None))
        body,inline=e.prepare_body('key','您到白馬30分。'*100,caller)
        self.assertIn('您',body);self.assertEqual(caller.call_count,1)
        self.assertFalse(inline)

    def test_length_branches(self):
        for size,calls in [(299,0),(800,0),(1400,0),(1500,0),(1501,1)]:
            caller=Mock(return_value=(response('雪'*1200),None))
            if size<300:
                with self.assertRaises(ValueError):e.prepare_body('key','雪'*size,caller)
            else:
                body,inline=e.prepare_body('key','雪'*size,caller)
                self.assertEqual(inline,calls==0)
            self.assertEqual(caller.call_count,calls)
        for result in ('雪'*1601,'雪'*299):
            with self.assertRaises(ValueError):
                e.prepare_body('key','雪'*1700,Mock(return_value=(response(result),None)))

    def test_rewrite_preserves_metadata_and_cover(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'content/articles').mkdir(parents=True)
            (root/'content/covers').mkdir()
            article=root/'content/articles/first-trip.md';article.write_text('# 原標題\n白馬30分。')
            cover=root/'content/covers/first-trip.svg';cover.write_text('existing cover')
            entry={'slug':'first-trip','title':'原標題','category':'beginner','resort':'happo','date':'2020-01-01'}
            (root/'content/index.json').write_text(json.dumps({'articles':[entry]}))
            caller=Mock(return_value=(response('白馬車程30分。'*110),None))
            e.run(rewrite='first-trip',db_root=root,key='key',api_caller=caller,resolver=lambda url:url)
            new=json.loads((root/'content/index.json').read_text())['articles'][0]
            self.assertEqual(new['date'],'2020-01-01');self.assertEqual(new['updated'],e.today_jst())
            self.assertEqual(new['resort'],'happo');self.assertEqual(new['title'],'原標題')
            self.assertEqual(cover.read_text(),'existing cover');self.assertIn('## 來源',article.read_text())
            self.assertEqual(e.parse_args(['--rewrite','first-trip']).rewrite,'first-trip')

    def test_compression_has_sources_without_superscripts(self):
        candidate=response('雪'*1800)['candidates'][0]
        candidate['groundingMetadata']['groundingSupports']=[{'segment':{'endIndex':10,'text':'雪'*10},'groundingChunkIndices':[0]}]
        sources=e.extract_sources(candidate,lambda url:url)
        rendered=e.render_markdown('題目','雪'*1200,candidate,sources,'2026-11-09',inline=False)
        self.assertNotIn('<sup>',rendered);self.assertIn('https://example.com/facts',rendered)

if __name__=='__main__':unittest.main()
